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
* the capture not stopped in `close` -> the stop test goes red;
* the size bound dropped -> the first test goes red, and a real 1920x1080
  window would ship a JPEG four times larger than needed on every call.
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

from invisible_playwright_mcp.mcp.session import StealthSession


class _FakeScreencast:
    def __init__(self, page):
        self.page = page
        self.starts = []
        self.stops = 0
        self.on_frame = None

    async def start(self, on_frame=None, size=None, quality=None, path=None,
                    fps=None):
        # `fps` arrived in invisible-playwright 0.14.0 and the floor requires
        # it. A stand-in that did not take it made every test here fail with a
        # TypeError dressed up as "this engine has no screencast", which is the
        # stand-in being the wrong shape rather than the code being wrong.
        self.starts.append({"size": size, "quality": quality, "path": path,
                            "fps": fps})
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

    async def close(self):
        pass


async def test_the_capture_starts_once_and_answers_the_latest_frame():
    s = StealthSession()
    s._context = _FakeContext()
    page = await s.new_page()

    async def feed():
        await asyncio.sleep(0.05)
        page.screencast.deliver(b"\xff\xd8\xff frame-1")

    asyncio.create_task(feed())
    first = await s.watch_frame()
    assert first.startswith(b"\xff\xd8\xff"), first
    assert page.screencast.starts == [{"size": {"width": 1280, "height": 800},
                                       "quality": None, "path": None,
                                       "fps": StealthSession.WATCH_FPS}]
    page.screencast.deliver(b"\xff\xd8\xff frame-2")
    second = await s.watch_frame()
    assert second.endswith(b"frame-2"), "the LATEST frame, not the first"
    assert len(page.screencast.starts) == 1, "a second call must not start again"


async def test_closing_the_session_stops_its_capture():
    s = StealthSession()
    s._context = _FakeContext()
    page = await s.new_page()
    page.screencast.deliver  # the fake exists before any frame
    asyncio.get_running_loop().call_later(
        0.02, page.screencast.deliver, b"\xff\xd8\xff x")
    await s.watch_frame()
    await s.close()
    assert page.screencast.stops == 1
    assert id(page) not in s._watch


async def test_no_frame_in_time_is_said_in_words():
    s = StealthSession()
    s._context = _FakeContext()
    await s.new_page()
    with pytest.raises(RuntimeError) as told:
        await s.watch_frame(timeout=0.05)
    assert "no frame arrived" in str(told.value)


async def test_an_engine_without_a_screencast_is_named_not_leaked():
    """An older wrapper refuses `screencastStart` with a protocol sentence
    about a guid; the person reading this tool's error needs the feature and
    the version, not the guid."""
    s = StealthSession()
    s._context = _FakeContext()
    page = await s.new_page()

    class _Refusing:
        async def start(self, **kw):
            raise RuntimeError("no object 'artifact@3' to answer 'read'")

    page.screencast = _Refusing()
    with pytest.raises(RuntimeError) as told:
        await s.watch_frame()
    assert "page.screencast" in str(told.value)
    assert "firefox-28" in str(told.value)


def _timed(s: StealthSession):
    """A clock the test moves, in place of sleeping through STALE_AFTER."""
    now = [1000.0]
    s._clock = lambda: now[0]
    return now


async def test_a_capture_that_went_quiet_is_started_again():
    """⛔ A FRAME SERVED WITHOUT AN AGE IS A FROZEN PANE THAT LOOKS LIVE.

    The engine's window capture can end for good on its own - the WebRTC
    capturer reports a permanent error the first time a headed window is
    minimised, the capture timer is cancelled, and nothing says so - and this
    method answered the last frame it held, forever. Measured 2026-09-14: the
    pane showed a search page while the browser was two sites on, the capture
    thread at 0 ms of CPU over six seconds.

    Known-bad: the age check removed. The second look answers `one` with the
    capture never restarted, and this goes red on `two`.
    """
    s = StealthSession()
    s._context = _FakeContext()
    page = await s.new_page()
    now = _timed(s)

    asyncio.get_running_loop().call_later(
        0.02, page.screencast.deliver, b"\xff\xd8\xff one")
    assert (await s.watch_frame()).endswith(b"one")

    now[0] += StealthSession.STALE_AFTER + 0.5

    async def feed_the_restart():
        while len(page.screencast.starts) < 2:
            await asyncio.sleep(0.005)
        page.screencast.deliver(b"\xff\xd8\xff two")

    asyncio.create_task(feed_the_restart())
    got = await s.watch_frame()

    assert got.endswith(b"two"), got
    assert page.screencast.stops == 1, "the quiet capture was not stopped"
    assert len(page.screencast.starts) == 2, "the capture was not started again"


async def test_a_quiet_page_is_not_a_quiet_capture():
    """The counter-case: frames keep arriving on a page that never changes,
    so a young frame is served as it is. Restarting on every look would cost a
    capture thread twenty-five times a second."""
    s = StealthSession()
    s._context = _FakeContext()
    page = await s.new_page()
    now = _timed(s)

    asyncio.get_running_loop().call_later(
        0.02, page.screencast.deliver, b"\xff\xd8\xff still")
    await s.watch_frame()
    now[0] += StealthSession.STALE_AFTER / 2
    page.screencast.deliver(b"\xff\xd8\xff still")
    now[0] += StealthSession.STALE_AFTER / 2 + 0.2

    assert (await s.watch_frame()).endswith(b"still")
    assert len(page.screencast.starts) == 1, "a live capture was restarted"


async def test_a_restart_that_stays_silent_is_dropped_with_the_reason():
    """A capture started on a window that cannot be captured - minimised, say
    - delivers nothing, and keeping it would make every later look wait on it.
    It is stopped, the reason is said, and the next look starts its own."""
    s = StealthSession()
    s._context = _FakeContext()
    page = await s.new_page()
    now = _timed(s)

    asyncio.get_running_loop().call_later(
        0.02, page.screencast.deliver, b"\xff\xd8\xff one")
    await s.watch_frame()
    now[0] += StealthSession.STALE_AFTER + 0.5

    with pytest.raises(RuntimeError) as told:
        await s.watch_frame(timeout=0.05)

    assert "minimised" in str(told.value)
    assert id(page) not in s._watch, "a capture that never answered was kept"
    assert page.screencast.stops == 2, "the silent restart was not stopped"


BINARY = os.environ.get("STEALTHFOX_BINARY")


@pytest.mark.e2e
@pytest.mark.skipif(not BINARY, reason="set STEALTHFOX_BINARY to a patched Firefox")
async def test_the_frame_is_the_window_of_a_real_browser():
    """Against a real engine, in the server's default mode (headless, which on
    Windows is a real window on a hidden desktop and on Linux one on Xvfb):
    JPEG bytes, and TALLER than the content viewport, which is the chrome
    above it. The frame comes from the firefox-34 engine onward: the earlier
    capturer cropped the window from a screen that did not show it."""
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


@pytest.mark.e2e
@pytest.mark.skipif(not BINARY or sys.platform != "win32",
                    reason="a real engine on Windows, where a window can be minimised")
async def test_the_frame_comes_back_after_the_window_was_minimised():
    """⛔ THE ENGINE ENDS THE CAPTURE FOR GOOD WHEN THE WINDOW IS MINIMISED, and
    says nothing. Reproduced 2026-09-14 on firefox-29: minimise the window,
    restore it, navigate - one frame forever, the capture thread idle. The
    session now notices the silence and starts the capture again, and this is
    the arm that proves it against the real engine.

    Known-bad: `StealthSession.STALE_AFTER = 1e9` (no restart) - the frame
    after the restore is still the frame from before the minimise.
    """
    import ctypes

    user32 = ctypes.windll.user32
    s = StealthSession(binary_path=BINARY, headless=True)
    await s.start()
    try:
        await s.new_page()
        await s.page().goto("data:text/html,<title>invisible_playwright_mcp-minimise-probe</title>"
                            "<body style='background:%23fff'>before</body>")
        # The native window takes its title from the document a moment after
        # `goto` returns; on a build with the capture heartbeat it was not there
        # yet on the first look. Waited for, not assumed.
        hwnd = 0
        for _ in range(50):
            hwnd = _window_titled("invisible_playwright_mcp-minimise-probe")
            if hwnd:
                break
            await asyncio.sleep(0.1)
        assert hwnd, "the probe window was not found on screen within 5 s"
        before = await s.watch_frame(timeout=10.0)

        assert user32.ShowWindow(hwnd, 6)              # SW_MINIMIZE
        await asyncio.sleep(2.0)
        assert user32.ShowWindow(hwnd, 9)              # SW_RESTORE
        await s.page().goto("data:text/html,<title>invisible_playwright_mcp-minimise-probe</title>"
                            "<body style='background:%23000;color:%23fff'>after</body>")

        deadline = asyncio.get_running_loop().time() + 15.0
        latest = before
        while asyncio.get_running_loop().time() < deadline:
            try:
                latest = await s.watch_frame(timeout=3.0)
            except RuntimeError:
                pass
            if latest != before:
                break
            await asyncio.sleep(0.2)
        assert latest != before, (
            "after minimise and restore the capture still answers the frame "
            "from before the minimise")
    finally:
        await s.close()


def _window_titled(part: str):
    """The first top-level window whose title contains `part`, or 0."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def each(hwnd, _):
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if part in buf.value:
                found.append(hwnd)
        return True

    user32.EnumWindows(each, 0)
    return found[0] if found else 0


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


async def test_the_capture_is_asked_for_the_rate_somebody_watching_needs():
    """⛔ THE LAST LINK OF A CHAIN THAT WAS SLOW IN THREE PLACES. The engine
    makes what it is asked for, the wrapper passes the request on since 0.14.0,
    and this is where the number is chosen. Ten is the wrapper's default because
    a batch job that never looks at a frame should not pay for a live view -
    measured, ten costs 257 KB/s and twenty-five costs 629 - and here there IS
    somebody looking.

    Known-bad: drop `fps=self.WATCH_FPS` from the start call. Nothing fails, no
    test turns red without this one, and the pane silently goes back to ten
    frames a second while the page asks for twenty-five and gets duplicates.
    """
    s = StealthSession()
    s._context = _FakeContext()
    page = await s.new_page()
    # The frame can only be delivered once the capture has started, and the
    # capture starts inside `watch_frame` - so it is fed from a task, the way
    # the first test in this file does it.
    async def feed():
        await asyncio.sleep(0.02)
        page.screencast.deliver(bytes([0xFF, 0xD8, 0xFF]) + b" frame")

    asyncio.ensure_future(feed())
    await s.watch_frame()

    asked = page.screencast.starts[-1]
    assert asked["fps"] == StealthSession.WATCH_FPS, asked
    assert StealthSession.WATCH_FPS > 10, (
        "the live view is asking for the wrapper's default, which is the rate "
        "chosen for consumers that are not watching")
