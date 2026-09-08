"""Waking a declared browser gives back the person AND the pages.

Slice 3 made a saved session give back WHO its browsers were. That is half of
what somebody reopens a session for: a browser that comes home as the right
person with nothing open is right about its identity and wrong about its work.
This file is the other half - where it was.

⛔ AND IT HAPPENS ONCE. A browser that kept reopening the tabs a file remembers
would fight whoever is using it, closing nothing and adding the same pages back
every time it was handed out. The tabs are OWED, and the wake that pays them
clears the debt.

No browser starts here: the registry is given a factory that launches nothing,
and its sessions record the pages they were asked to open.
"""
from __future__ import annotations

import json

import pytest

from aihawk.mcp import actions, server, store


class _Recording:
    """A session that launches nothing and records the pages it was given."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._browser = None
        self._context = object()
        self.closed = False
        self.pages = []

    async def start(self):
        pass

    async def close(self):
        self.closed = True

    async def new_page(self):
        self.pages.append("")
        return "tab-%d" % len(self.pages)

    def where_pages_are(self):
        # The cheap half, added in 0.20.1 when it turned out the server was
        # asking for page TITLES on every command. A stand-in without it makes
        # `ready` raise into a `try/except` and the tabs quietly go unnoted,
        # which reads as a browser that could not be read.
        return list(self.pages)

    async def describe_pages(self):
        return [{"id": "tab-%d" % (i + 1), "url": u, "title": "", "active": False}
                for i, u in enumerate(self.pages)]


@pytest.fixture
def registry(monkeypatch):
    reg = server.new_registry(factory=_Recording,
                              defaults=lambda: {"seed": 7, "headless": True})
    monkeypatch.setattr(server, "registry", reg)
    monkeypatch.setattr(server, "_focus", {})
    monkeypatch.setattr(server, "_loaded", set())
    monkeypatch.setattr(server, "_seen_tabs", {})
    monkeypatch.setattr(server, "_tabs_owed", {})

    async def _went(session, url, wait_until="domcontentloaded"):
        session.pages[-1] = url
        return "navigated to %s" % url

    monkeypatch.setattr(actions, "navigate", _went)
    return reg


async def test_where_a_browser_was_is_written_down_with_who_it_was(registry):
    """Known-bad: drop the `urls` line from `remember`. The session comes back
    with the right person and an empty window, which is the half of the promise
    nobody notices is missing until they look for their work.
    """
    await server.browser_open(browser_id="docs", seed=4242)
    session = await server.ready(browser_id="docs")
    await session.new_page()
    await actions.navigate(session, "http://example.test/one")
    # Any command aimed at it notes where it is; this is the one the interface
    # uses to draw its panes.
    await server.browser_list()

    saved = store.load("default")
    assert saved["browsers"]["docs"]["urls"] == ["http://example.test/one"]
    assert saved["browsers"]["docs"]["seed"] == 4242


async def test_a_browser_nobody_has_looked_at_does_not_report_an_empty_window(registry):
    """⛔ "NOBODY ASKED" IS NOT "IT HAD NO TABS", and writing the second would
    wipe the pages of a browser that is up and busy the moment anything saved
    the session for another reason.

    Known-bad: write `wrote["urls"] = been or []` instead of only when there is
    something.
    """
    await server.browser_open(browser_id="docs")

    saved = store.load("default")
    assert "urls" not in saved["browsers"]["docs"], saved["browsers"]["docs"]


async def test_waking_a_declared_browser_reopens_the_tabs_it_had(registry, monkeypatch):
    """The point of the whole slice.

    Known-bad, two: drop the reopen loop from `ready`, and have `restore` hand
    the urls to `registry.declare` as part of the identity - the registry would
    then pass `urls` to the session factory, which is a launch setting no
    browser has.
    """
    store.save("default", {"docs": {"seed": 4242, "headless": True,
                                    "urls": ["http://a.test/", "http://b.test/"]}},
               focus="docs")

    assert server.browsers_in() == ["docs"]
    assert registry.ids() == [], "reading a session back started a browser"

    session = await server.ready(browser_id="docs")

    assert session.kwargs.get("seed") == 4242, "it came back as somebody else"
    assert "urls" not in session.kwargs, (
        "the urls were handed to the browser as a launch setting: %r"
        % session.kwargs)
    assert session.pages == ["http://a.test/", "http://b.test/"]


async def test_the_tabs_are_reopened_once_and_not_on_every_command(registry):
    """⛔ OTHERWISE THE WAKE FIGHTS THE PERSON USING IT. A browser handed out
    twice would get the same two pages added twice, and a session used for an
    hour would end with a hundred copies of where it started.

    Known-bad: read `_tabs_owed` without removing the entry.
    """
    store.save("default", {"docs": {"seed": 1, "headless": True,
                                    "urls": ["http://a.test/"]}})

    first = await server.ready(browser_id="docs")
    await server.ready(browser_id="docs")
    await server.ready(browser_id="docs")

    assert first.pages == ["http://a.test/"], first.pages


async def test_a_url_that_will_not_load_does_not_cost_the_browser(registry, monkeypatch):
    """It is up and it is the right person. Refusing to hand it back over one
    stale bookmark turns a dead link into a session nobody can use.

    Known-bad: remove the try/except around the reopen loop.
    """
    async def _refuses(session, url, wait_until="domcontentloaded"):
        raise RuntimeError("NS_ERROR_UNKNOWN_HOST")

    monkeypatch.setattr(actions, "navigate", _refuses)
    store.save("default", {"docs": {"seed": 1, "headless": True,
                                    "urls": ["http://gone.test/"]}})

    session = await server.ready(browser_id="docs")

    assert session is not None
    assert session.kwargs.get("seed") == 1


async def test_a_browser_that_was_never_saved_is_woken_empty(registry):
    """Known-bad: default the owed tabs to something. A brand new browser then
    opens a page nobody asked for.
    """
    session = await server.ready(browser_id="fresh")
    assert session.pages == []


async def test_the_retry_path_wakes_the_same_way(registry):
    """`_retrying` rebuilds a browser that died mid-command, and that rebuild is
    a wake like any other: the same person, back where it was.

    Known-bad: have `_retrying` call `registry.ensure` directly again. The
    browser comes back correct and empty, and only a caller looking for its tabs
    would ever notice.
    """
    store.save("default", {"main": {"seed": 9, "headless": True,
                                    "urls": ["http://a.test/"]}})
    seen = {}

    async def _once(session, *a, **k):
        if "first" not in seen:
            seen["first"] = True
            raise RuntimeError("the browser died")
        return json.dumps([p["url"] for p in await session.describe_pages()])

    got = await server._retrying(_once)

    assert json.loads(got) == ["http://a.test/"], got


def test_the_server_only_asks_the_session_for_things_it_has():
    """⛔ THE `try/except` AROUND NOTING THE TABS HIDES A MISSING METHOD, and it
    has to: a tab mid-navigation legitimately refuses to be read, and one that
    does must not cost the caller their browser. But that same handler swallows
    an AttributeError, so a server calling a method the session does not have
    looks exactly like a browser that could not be read - measured here, on a
    stand-in that lacked `where_pages_are` and simply stopped noting anything.

    So the contract is asserted directly instead of being left to a runtime
    path that is designed not to complain.

    Known-bad: rename `where_pages_are` on `StealthSession`.
    """
    from aihawk.mcp.session import StealthSession

    for name in ("where_pages_are", "describe_pages", "new_page", "close"):
        assert callable(getattr(StealthSession, name, None)), (
            "the server calls session.%s() and the session has no such method; "
            "at runtime that is swallowed and reads as a browser that could "
            "not be read" % name)
