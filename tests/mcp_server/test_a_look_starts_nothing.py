"""A question is not a command: looking at a browser must not create one.

⛔ THE DEFECT THIS EXISTS FOR SHIPPED IN 0.36.0, 0.37.0 AND 0.38.0, AND NOTHING
IN THE SUITE COULD SEE IT. Opening the interface drew its panes, the panes asked
`browser_watch` and `session_list_pages`, both resolved their browser through
`ready`, and `ready` STARTS what it resolves. Measured on 0.38.0 with a fresh
home and no instruction given: 9 firefox processes before, 16 after - roughly
800 MB and seven seconds - and `browser_watch` then answered an error, so the
engine the look had started was not even used for the look.

Every test that touched those tools built a registry whose factory launches
nothing, so "it started a browser" was invisible: nothing launched in the first
place. What IS visible, and is what these assert, is whether the registry ends
up holding a session it did not hold before. That is the same event one layer
up, and it is the layer where it can be proven without a browser.

The other half of the rule is asserted too, because a guard that never lets
anything through is not a guard: a browser that IS running is looked at exactly
as before.
"""
from __future__ import annotations

import json

import pytest

from aihawk.mcp import NOTHING_RUNNING, server
from aihawk.mcp.registry import DEFAULT_SESSION_ID

pytestmark = pytest.mark.asyncio


class _Recording:
    """A session that launches nothing and reports itself alive."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.closed = False

    async def start(self):
        pass

    async def close(self):
        self.closed = True

    async def describe_pages(self):
        return [{"id": "p-1", "title": "a tab", "url": "http://x/", "active": True}]

    def where_pages_are(self):
        return ["http://x/"]


@pytest.fixture
def registry(monkeypatch):
    reg = server.new_registry(factory=_Recording,
                              defaults=lambda: {"seed": 7, "headless": True})
    monkeypatch.setattr(server, "registry", reg)
    monkeypatch.setattr(server, "_focus", {})
    return reg


async def test_asking_for_the_tabs_of_a_browser_that_is_not_running_starts_nothing(registry):
    """Known-bad: `await actions.list_pages(await ready(...))`, which is what it
    said until 0.39.0. The registry then holds a session it did not hold, which
    on a real machine is an engine.
    """
    assert registry.ids() == [], "something was already running before the look"

    said = await server.session_list_pages()

    assert json.loads(said) == [], (
        "a browser that is not running has no tabs, and this said otherwise")
    assert registry.ids() == [], (
        "looking at the tabs built a browser: %r" % registry.ids())


async def test_asking_for_the_window_of_a_browser_that_is_not_running_starts_nothing(registry):
    """It refuses rather than answering a sentence, and the refusal is the
    shared one: the live pane compares against it to tell "nothing to look at"
    from "the capture is broken", and those are a quiet idle state and a
    sentence somebody reads.

    Known-bad: `await actions.watch_jpeg(await ready(...))`.
    """
    with pytest.raises(Exception) as refused:
        await server.browser_watch()

    assert NOTHING_RUNNING in str(refused.value), (
        "the refusal is not the sentence the pane reads: %s" % refused.value)
    assert registry.ids() == [], (
        "looking at the window built a browser: %r" % registry.ids())


async def test_a_browser_that_IS_running_is_still_looked_at(registry):
    """⛔ THE OTHER HALF, AND WITHOUT IT THIS FILE WOULD PASS ON A PANE THAT
    NEVER DRAWS ANYTHING. A guard that refuses everything satisfies both tests
    above.
    """
    await server.browser_open()                      # a COMMAND: this starts it
    before = registry.ids()
    assert before, "the command did not start a browser, so the rest proves nothing"

    rows = json.loads(await server.session_list_pages())

    assert [r["id"] for r in rows] == ["p-1"], (
        "a running browser's tabs were not read: %r" % rows)
    assert registry.ids() == before, "reading the tabs built a second browser"


async def test_a_command_still_starts_a_declared_browser(registry):
    """The promise `browser_list` makes to a model, kept: a browser that is not
    running is asleep rather than gone, and the next COMMAND aimed at it starts
    it as the same person. Only looking stopped waking it.
    """
    assert registry.ids() == []

    await server.browser_open()

    assert DEFAULT_SESSION_ID in registry.ids()[0], (
        "a command did not start the browser it was aimed at: %r" % registry.ids())
