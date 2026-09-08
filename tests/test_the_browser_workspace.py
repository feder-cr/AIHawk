"""Several browsers, one live pane, and the arithmetic that decides it.

⛔ THE SHAPE OF THIS FEATURE COMES FROM A NUMBER, NOT FROM TASTE. A frame costs
about 22 ms on the stdio pipe, the pipe is serialised, and actions share it with
pictures. Eight panes each asking thirteen times a second is 104 requests a
second at 22 ms, which is 2.3 seconds of pipe for every second that passes: the
picture falls behind and every click queues behind the pictures. So there is one
live pane and one slow loop that takes the others in turn at a FIXED rate, and
the test below reads that out of the page - because the obvious way to write it
is a loop per pane, whose cost is exactly what the measurement forbids.

No browser and no server: the link records what it was asked.
"""
from __future__ import annotations

import json
import re

import pytest

from aihawk.web import PAGE, Sessions, build_app

pytestmark = [pytest.mark.asyncio, pytest.mark.filterwarnings("ignore")]


class _Tool:
    def __init__(self, name, props):
        self.name = name
        self.inputSchema = {"type": "object", "properties": {p: {} for p in props}}


FLEET = {
    "session": "lavoro", "focus": "docs", "limit": 8,
    "browsers": [
        {"id": "docs", "running": True, "focused": True, "urls": ["http://a/"]},
        {"id": "posta", "running": True, "focused": False, "urls": ["http://b/"]},
        {"id": "dormiente", "running": False, "focused": False, "urls": []},
    ],
    "note": "3 of 8 browsers.",
}


class _Text:
    """A tool result shaped the way one arrives over MCP.

    ⛔ NOT a bare string. `SessionLink.call_text` is `text_of(await call(...))`,
    so a stand-in whose `call` answers None makes every text read come back
    empty - which reads as a server that answered nothing rather than as a
    stand-in that was the wrong shape.
    """

    def __init__(self, text):
        self.content = [type("Item", (), {"text": text})()]
        self.isError = False


class FakeLink:
    def __init__(self):
        self.touched = False
        self.tools = [_Tool("browser_watch", ["session_id", "browser_id"]),
                      _Tool("browser_list", ["session_id"]),
                      _Tool("browser_focus", ["browser_id", "session_id"]),
                      _Tool("session_list_pages", ["session_id", "browser_id"])]
        self.calls = []
        self.answers = {"browser_list": json.dumps(FLEET),
                        "browser_focus": "commands now go to it",
                        "session_list_pages": "[]"}

    async def call(self, name, arguments=None):
        self.touched = True
        self.calls.append((name, dict(arguments or {})))
        return _Text(self.answers[name]) if name in self.answers else None


class Brain:
    messages: list = []
    usage: dict = {}

    async def handle(self, text, link, say):
        await link.call("browser_navigate", {"url": "http://x/"})


def _app():
    from starlette.testclient import TestClient
    link = FakeLink()
    sessions = Sessions(link, Brain)
    return link, sessions, TestClient(build_app(link, sessions))


# --- what the page is told to draw ------------------------------------------

async def test_the_workspace_is_read_from_the_server_like_any_other_client():
    """The interface has no privileged path to the browsers: it asks the same
    tool an agent would.

    Known-bad: have the route keep its own list of browsers. It is right until
    the model opens one, which is the case the workspace exists for.
    """
    link, sessions, client = _app()
    await sessions.get("lavoro").send("start something")

    got = client.get("/live/browsers?s=lavoro").json()

    assert [b["id"] for b in got["browsers"]] == ["docs", "posta", "dormiente"]
    assert got["focus"] == "docs" and got["limit"] == 8
    assert any(name == "browser_list" for name, _ in link.calls)


async def test_a_conversation_that_has_done_nothing_draws_no_panes_and_asks_nothing():
    """⛔ OR OPENING A CHAT COSTS AN ENGINE. Over MCP there is no way to ask "is
    a browser running" without starting one, so a workspace drawn for a session
    that has issued no instruction must answer from what it already knows.

    Known-bad: drop the `touched` guard from the browsers route.
    """
    link, sessions, client = _app()

    got = client.get("/live/browsers?s=mai-usata").json()

    assert got["browsers"] == []
    assert link.calls == [], (
        "drawing an empty workspace reached the server: %r" % link.calls)


async def test_an_older_server_leaves_the_workspace_empty_instead_of_breaking_the_pane():
    """`browser_list` answered prose before 0.18.0. A page that cannot parse it
    draws no previews and keeps the single live pane working, which is the half
    that does not depend on this.

    Known-bad: let the route raise on unparsable output.
    """
    link, sessions, client = _app()
    await sessions.get("lavoro").send("start something")

    link.answers["browser_list"] = "session lavoro holds 3 of 8 browsers."
    got = client.get("/live/browsers?s=lavoro").json()

    assert got == {"browsers": [], "focus": "", "limit": 0}


# --- which browser a pane is watching ---------------------------------------

async def test_a_pane_asks_for_its_own_browser_and_not_for_the_focused_one():
    """Without this the workspace is one picture drawn several times.

    Known-bad: drop `browser_id` from the frame route. Every thumbnail then
    shows whatever the focused browser is looking at, which is a wrong answer
    that looks exactly like a right one.
    """
    link, sessions, client = _app()
    await sessions.get("lavoro").send("start something")

    client.get("/live/frame?s=lavoro&b=posta")

    watched = [args for name, args in link.calls if name == "browser_watch"]
    assert watched and watched[-1].get("browser_id") == "posta", watched
    assert watched[-1].get("session_id") == "lavoro", (
        "a pane reached into another session: %r" % watched[-1])


async def test_the_live_pane_still_asks_for_the_focused_browser_when_none_is_named():
    """The single-browser case is the common one and must not have gained an
    argument it does not need.

    Known-bad: make `browser_id` required in the frame route.
    """
    link, sessions, client = _app()
    await sessions.get("lavoro").send("start something")

    assert client.get("/live/frame?s=lavoro").status_code in (200, 204, 503)
    watched = [args for name, args in link.calls if name == "browser_watch"]
    assert "browser_id" not in watched[-1], watched[-1]


async def test_clicking_a_pane_moves_the_focus_the_agent_uses():
    """⛔ ONE FOCUS, NOT TWO. The pane a person clicks becomes the browser the
    session's unaddressed commands go to. A second idea of "current" kept by the
    page would disagree with the server the first time the model opened a
    browser, and the disagreement shows as commands landing in a pane nobody is
    watching.

    Known-bad: have the route remember the choice locally instead of calling
    `browser_focus`.
    """
    link, sessions, client = _app()
    await sessions.get("lavoro").send("start something")

    said = client.post("/live/watch?s=lavoro", json={"id": "posta"})

    assert said.status_code == 200 and said.json()["focused"] == "posta"
    assert ("browser_focus", {"browser_id": "posta", "session_id": "lavoro"}) \
        in link.calls, link.calls


async def test_focusing_nothing_refuses():
    """Known-bad: treat a missing id as the focused browser, which makes a bug
    in the page silently a no-op instead of an error somebody can see."""
    _, sessions, client = _app()
    assert client.post("/live/watch?s=lavoro", json={}).status_code == 400


# --- the arithmetic, read out of the page -----------------------------------

def test_the_previews_cost_the_same_whether_there_are_two_or_eight():
    """⛔ THE MEASUREMENT, AS A PROPERTY OF THE CODE. One slow loop taking the
    panes in turn costs a fixed number of requests a second; a loop per pane
    costs that many times N, and at eight panes N is what the pipe cannot pay.

    Read out of the page because this is a shape, not a value: what has to stay
    true is that the number of timers does not depend on the number of browsers.

    Known-bad: start a `setTimeout` inside the loop that builds the thumbnails.
    """
    script = PAGE[PAGE.index("<script"):]

    # The slow loop reschedules ITSELF, once, at a fixed interval.
    assert re.search(r"setTimeout\(slowTick,\s*SLOW_MS\)", script), (
        "the slow loop does not reschedule itself at a fixed rate")
    assert len(re.findall(r"setTimeout\(slowTick", script)) == 1, (
        "the slow loop is scheduled from more than one place, so its rate is "
        "no longer one thing")

    # And the function that BUILDS a pane starts no timer of its own.
    builder = script[script.index("function thumbFor"):script.index("async function watchThis")]
    assert "setTimeout" not in builder and "setInterval" not in builder, (
        "a pane schedules its own refresh, so the cost of the previews grows "
        "with the number of panes - which is the thing the arithmetic forbids")


def test_a_pane_that_is_not_running_is_never_asked_for_a_picture():
    """A declared browser that has not started is not a slow pane: asking would
    START it, 800 MB and seven seconds, to fill a thumbnail nobody asked for.

    Known-bad: drop the filter on `img` in `slowTick` and ask for every pane.
    """
    script = PAGE[PAGE.index("<script"):]
    slow = script[script.index("async function slowTick"):script.index("async function fleetPoll")]

    assert "filter(t => t.querySelector('img'))" in slow, (
        "the slow loop asks for a picture of every pane, including the ones "
        "that are only declared - which starts them")


def test_the_page_declares_no_identifier_twice():
    """⛔ A DUPLICATE `let` IS A SYNTAX ERROR, AND A SYNTAX ERROR KILLS THE WHOLE
    SCRIPT - not the line, the file. Nothing runs: no event stream, no session
    column, no workspace, and the page still renders, so it looks like a server
    that has stopped answering rather than like a page that never started.

    Measured by shipping it for ten minutes. The workspace declared `let fleet =
    [], turn = 0` and `turn` was already a top-level variable of the step list.
    The whole suite was green - 426 tests - because every test reads the page as
    a STRING or drives the routes, and neither notices that a browser cannot
    parse it. It was found by opening the page and asking it whether its own
    helper existed.

    Checked with a scan rather than by parsing JavaScript, because the scan is
    the shape of the defect: two declarations of one name at the top level of
    one script. A real parser would be better and needs a JavaScript engine in
    the test environment.

    Known-bad: rename `nextPane` back to `turn`.
    """
    script = PAGE[PAGE.index("<script"):]
    seen, twice = {}, []
    for line in script.split("\n"):
        if line[:1] not in ("l", "c", "v"):
            # Top level only: an indented declaration is inside something, where
            # shadowing is legal and common.
            continue
        m = re.match(r"(?:let|const|var)\s+(.+?);\s*$", line)
        if not m:
            continue
        for part in m.group(1).split(","):
            name = part.split("=")[0].strip()
            if not re.fullmatch(r"[A-Za-z_$][\w$]*", name or ""):
                continue
            if name in seen:
                twice.append(name)
            seen[name] = True
    assert not twice, (
        "declared twice at the top level of the page's script, which is a "
        "syntax error that stops the whole file from running: %s" % sorted(set(twice)))
