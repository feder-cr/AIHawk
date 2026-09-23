"""The server downloads the engine from the moment it starts, and no browser
is launched while it is not on disk: `browser_open` answers with the
download's progress instead.

No browser and no network. The piece of work gets a factory that records what
it was handed and an engine whose fetch is a stand-in held open on an Event.
"""
from __future__ import annotations

import threading
import time

import pytest

from invisible_playwright_mcp.engine import Engine
from invisible_playwright_mcp.mcp import server
from invisible_playwright_mcp.mcp.work import Work


class _Built:
    """A session that launches nothing and records that it was built."""

    built: list = []

    def __init__(self, **kwargs):
        _Built.built.append(kwargs)
        self.closed = False
        self.urls: list = []

    async def start(self):
        pass

    async def close(self):
        self.closed = True

    def is_usable(self):
        return not self.closed

    def pages(self):
        return list(self.urls)

    def where_pages_are(self):
        return list(self.urls)


class _Fetch:
    def __init__(self, fail=None):
        self.fail = fail
        self.calls = 0
        self.started = threading.Event()
        self.release = threading.Event()

    def __call__(self, progress, status):
        self.calls += 1
        status("downloading")
        progress(30 << 20, 100 << 20)
        self.started.set()
        self.release.wait(5)
        if self.fail is not None:
            raise self.fail
        return "C:/cache/firefox.exe"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    for name in ("STEALTHFOX_SEED", "STEALTHFOX_PROXY", "STEALTHFOX_PROFILE_DIR",
                 "STEALTHFOX_HEADLESS", "STEALTHFOX_BINARY", "STEALTHFOX_NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(server.store, "load", lambda session_id: None)
    monkeypatch.setattr(server.store, "save", lambda *a, **k: None)
    _Built.built = []


def _until(predicate, seconds=5.0):
    deadline = time.monotonic() + seconds
    while not predicate():
        assert time.monotonic() < deadline
        time.sleep(0.01)


async def test_open_answers_with_the_download_and_launches_nothing_meanwhile():
    fetch = _Fetch()
    engine = Engine(fetch=fetch)
    work = Work("default", factory=_Built, engine=engine)

    said = await work.open("main")
    assert "30% of 100 MB" in said and "browser_open" in said, said
    assert _Built.built == [], "a browser was built while the engine was downloading"
    assert fetch.calls == 1, "open did not start the download it answered about"

    fetch.release.set()
    _until(engine.ready)
    said = await work.open("main")
    assert said.startswith("the main browser is open"), said
    assert len(_Built.built) == 1


async def test_a_warm_cache_opens_on_the_first_call():
    """The engine says it is a cache hit in milliseconds, and the wait in
    `open` is for that word, not for a transfer: a person with the engine on
    disk must never be told to call again.

    The cache check takes a moment on purpose - the core reads a stamp,
    sweeps orphans and verifies the tree - because an instant one let the
    known-bad survive: without the wait in `open`, the thread finished
    before `ready()` was asked and the test went green anyway.
    """
    def cache_hit(progress, status):
        time.sleep(0.3)
        return "C:/cache/firefox.exe"

    engine = Engine(fetch=cache_hit)
    work = Work("default", factory=_Built, engine=engine)
    said = await work.open("main")
    assert said.startswith("the main browser is open"), said


async def test_a_failed_download_is_said_and_the_next_open_retries_it():
    fetch = _Fetch(fail=RuntimeError("no route to github.com"))
    engine = Engine(fetch=fetch)
    engine.start()
    fetch.release.set()
    _until(lambda: engine.state == "failed")
    work = Work("default", factory=_Built, engine=engine)

    fetch.fail = None
    fetch.release.clear()
    said = await work.open("main")
    assert fetch.calls == 2, "open did not retry the failed download"
    assert "downloading" in said or "starting" in said, said
    assert _Built.built == []


async def test_a_given_binary_launches_at_once():
    fetched = []
    engine = Engine(binary_path="C:/engines/firefox.exe",
                    fetch=lambda **kw: fetched.append(kw))
    work = Work("default", factory=_Built, engine=engine)
    said = await work.open("main")
    assert said.startswith("the main browser is open"), said
    assert fetched == []


async def test_a_piece_of_work_without_an_engine_asks_nothing():
    """Tests that build a `Work` to exercise its decisions pass no engine, and
    must not be told to call again."""
    work = Work("default", factory=_Built)
    said = await work.open("main")
    assert said.startswith("the main browser is open"), said


def test_the_server_starts_the_download_before_it_serves(monkeypatch):
    """The order is the design: the minutes between a client starting its
    servers and the first page are the download's. Recorded, because `main`
    without `engine.start()` is a one-line mutation nothing else would see."""
    order = []
    monkeypatch.setattr(server.engine, "start", lambda: order.append("start"))
    monkeypatch.setattr(server.mcp, "run", lambda *a, **k: order.append("run"))
    monkeypatch.setattr(server, "_close_on_lifespan_exit", False)
    monkeypatch.delenv("STEALTHFOX_MCP_TRANSPORT", raising=False)
    server.main()
    assert order == ["start", "run"]


async def test_leaving_over_stdio_abandons_the_download(monkeypatch):
    calls = []
    monkeypatch.setattr(server.engine, "abandon", lambda *a, **k: calls.append("abandon"))

    async def _closed():
        calls.append("close_all")

    monkeypatch.setattr(server.work, "close_all", _closed)
    monkeypatch.setattr(server, "_close_on_lifespan_exit", True)
    async with server._lifespan(None):
        pass
    assert calls == ["abandon", "close_all"]


def test_the_server_engine_reads_the_binary_the_planner_reads():
    """One reader of STEALTHFOX_BINARY: the engine the server builds at
    import names whatever `plan.engine_here` names, so the two cannot
    disagree on where a binary comes from."""
    assert server.engine.path == server.plan.engine_here().get("binary_path")
