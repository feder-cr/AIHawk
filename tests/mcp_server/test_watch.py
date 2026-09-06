"""`browser_watch`: the window as a person sees it, from a live capture.

Every image this server returned was `page.screenshot()`, the content
viewport, and the pointer is drawn outside the page on purpose - so whoever
was watching an agent work never saw where the pointer was. The engine's
screencast captures the WINDOW; the session keeps one running per tab and
answers the latest frame.

Unit half, no browser: a fake page whose `screencast` records what it was
asked. Known-bad inputs run before this file was trusted:

* `watch_frame` starting the capture on EVERY call -> the "started once" test
  goes red (and a real engine would refuse the second start);
* the capture not stopped in `close_page` -> the stop test goes red;
* the size bound dropped -> the first test goes red, and a real 1920x1080
  window would ship a JPEG four times larger than needed on every call.
"""
from __future__ import annotations

import asyncio
import os

import pytest

from aihawk.mcp.session import StealthSession


class _FakeScreencast:
    def __init__(self, page):
        self.page = page
        self.starts = []
        self.stops = 0
        self.on_frame = None

    async def start(self, on_frame=None, size=None, quality=None, path=None):
        self.starts.append({"size": size, "quality": quality, "path": path})
        self.on_frame = on_frame

    async def stop(self):
        self.stops += 1
        self.on_frame = None

    def deliver(self, data: bytes):
        self.on_frame({"data": data, "timestamp": 1.0,
                       "viewportWidth": 1270, "viewportHeight": 922})


class _FakePage:
    def __init__(self):
        self.closed = False
        self.screencast = _FakeScreencast(self)

    def is_closed(self):
        return self.closed

    async def close(self):
        self.closed = True


class _FakeContext:
    def __init__(self):
        self.pages = []

    async def new_page(self):
        p = _FakePage()
        self.pages.append(p)
        return p


@pytest.mark.asyncio
async def test_the_capture_starts_once_and_answers_the_latest_frame():
    s = StealthSession()
    s._context = _FakeContext()
    pid = await s.new_page()
    page = s.page(pid)

    async def feed():
        await asyncio.sleep(0.05)
        page.screencast.deliver(b"\xff\xd8\xff frame-1")

    asyncio.create_task(feed())
    first = await s.watch_frame()
    assert first.startswith(b"\xff\xd8\xff"), first
    assert page.screencast.starts == [{"size": {"width": 1280, "height": 800},
                                       "quality": None, "path": None}]
    page.screencast.deliver(b"\xff\xd8\xff frame-2")
    second = await s.watch_frame()
    assert second.endswith(b"frame-2"), "the LATEST frame, not the first"
    assert len(page.screencast.starts) == 1, "a second call must not start again"


@pytest.mark.asyncio
async def test_closing_the_tab_stops_its_capture():
    s = StealthSession()
    s._context = _FakeContext()
    pid = await s.new_page()
    page = s.page(pid)
    page.screencast.deliver  # the fake exists before any frame
    asyncio.get_running_loop().call_later(
        0.02, page.screencast.deliver, b"\xff\xd8\xff x")
    await s.watch_frame()
    await s.close_page(pid)
    assert page.screencast.stops == 1
    assert pid not in s._watch


@pytest.mark.asyncio
async def test_no_frame_in_time_is_said_in_words():
    s = StealthSession()
    s._context = _FakeContext()
    await s.new_page()
    with pytest.raises(RuntimeError) as told:
        await s.watch_frame(timeout=0.05)
    assert "no frame arrived" in str(told.value)


@pytest.mark.asyncio
async def test_an_engine_without_a_screencast_is_named_not_leaked():
    """An older wrapper refuses `screencastStart` with a protocol sentence
    about a guid; the person reading this tool's error needs the feature and
    the version, not the guid."""
    s = StealthSession()
    s._context = _FakeContext()
    pid = await s.new_page()

    class _Refusing:
        async def start(self, **kw):
            raise RuntimeError("no object 'artifact@3' to answer 'read'")

    s.page(pid).screencast = _Refusing()
    with pytest.raises(RuntimeError) as told:
        await s.watch_frame()
    assert "page.screencast" in str(told.value)
    assert "firefox-28" in str(told.value)


BINARY = os.environ.get("STEALTHFOX_BINARY")


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.skipif(not BINARY, reason="set STEALTHFOX_BINARY to a patched Firefox")
async def test_the_frame_is_the_window_of_a_real_browser():
    """Against a real engine, in the server's default mode (headless, which on
    Windows is a cloaked window): JPEG bytes, and TALLER than the content
    viewport, which is the chrome above it."""
    s = StealthSession(binary_path=BINARY, headless=True)
    await s.start()
    try:
        await s.new_page()
        await s.page().set_viewport_size({"width": 800, "height": 600})
        await s.page().goto("about:blank")
        jpeg = await s.watch_frame(timeout=10.0)
        assert jpeg[:3] == b"\xff\xd8\xff", "not a JPEG"
        # SOF0/SOF2 markers carry the frame height; read it rather than trust.
        height = _jpeg_height(jpeg)
        assert height > 600, "%d px tall: no chrome above the 600 px viewport" % height
    finally:
        await s.close()


def _jpeg_height(data: bytes) -> int:
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(data[i + 5:i + 7], "big")
        length = int.from_bytes(data[i + 2:i + 4], "big")
        i += 2 + length
    raise AssertionError("no SOF marker in the JPEG")
