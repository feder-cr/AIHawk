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


async def test_the_workspace_asks_the_one_question_that_starts_nothing():
    """⛔ THE GUARD THAT BELONGS ON THE PICTURE DOES NOT BELONG HERE, and putting
    it here cost the feature its whole point. The frame and the tab strip may not
    ask before an instruction because asking STARTS a browser. `browser_list`
    starts nothing - that is its promise and there is a test for it in the
    server - so the workspace asks always.

    Copying the guard looked prudent and was a bug: a session reopened after a
    restart has browsers it DECLARED and no instruction yet, so the workspace
    would have been empty in exactly the case the declarations exist for, and
    the panes offering to wake them would never have been drawn.

    Known-bad: put `if not seen.link.touched: return empty` back at the top of
    the browsers route.
    """
    link, sessions, client = _app()

    got = client.get("/live/browsers?s=mai-usata").json()

    assert [b["id"] for b in got["browsers"]] == ["docs", "posta", "dormiente"], (
        "a session that has issued no instruction was shown no panes, so a "
        "reopened session cannot offer to wake the browsers it declared")
    assert [name for name, _ in link.calls] == ["browser_list"], (
        "drawing the workspace called something other than the question that "
        "starts nothing: %r" % link.calls)


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


async def test_the_page_cannot_open_close_or_redirect_a_browser():
    """⛔ EVERYTHING IS COMMANDED FROM THE CHAT, and this is where that stops
    being a slogan. The interface used to carry four controls that acted on
    browsers - open one, close one, move the agent's focus, wake a declared one -
    and every one of them was a second way to do something the agent already
    does when asked. Two ways to move the same thing is two things that can
    disagree about which browser is current, and the one the person clicked is
    not the one the model believes it is driving.

    The routes are gone, not hidden: a route nothing calls is surface anybody
    can call.

    Known-bad: put `/live/open` back and give the page a button for it.
    """
    _, sessions, client = _app()

    for path in ("/live/open", "/live/close", "/live/watch", "/live/wake"):
        assert client.post(path + "?s=lavoro", json={"id": "posta"}).status_code == 404, (
            "%s still exists, so the page can command a browser without saying "
            "it in the conversation" % path)


async def test_looking_at_a_pane_tells_the_agent_nothing():
    """The other half of the same decision, read out of the page: clicking a
    pane changes what YOU see and sends nothing.

    Two different things, and they used to be one value. `focusHere` is the
    browser the agent drives - it lives on the server and only the agent moves
    it. `pinned2` is the pane the person is looking at, which is this page's own
    business. Folding them together is what made a click a command.

    Known-bad: have `watchThis` POST anywhere.
    """
    import re

    script = PAGE[PAGE.index("<script"):]
    code = re.sub(r"/\*.*?\*/", "", script, flags=re.S)
    watch = code[code.index("function watchThis"):code.index("async function drawFleet")]

    assert "fetch" not in watch, (
        "clicking a pane sends something to the server, so looking at a browser "
        "moves the agent's hand: %s" % watch.strip()[:120])
    assert "pinned2" in watch, "the page has no idea of its own of what it is watching"
    assert "const watched = () => pinned2 || focusHere;" in code, (
        "the big pane does not follow the agent when nothing is pinned, so it "
        "stops showing the work while the work is happening")


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
    #
    # ⛔ BOUNDED BY BRACES, not by "up to the next function". The first version
    # cut from `function thumbFor` to the name of whatever came next, so a
    # function written between them was read as part of the builder: the wake's
    # stopwatch tripped it, and a stopwatch that ticks during one click is not
    # a pane refreshing itself. A slice that moves when unrelated code moves is
    # a gate that goes red for the wrong reason, which teaches people to widen
    # it - and the widened version would have stopped seeing the real thing.
    start = script.index("function thumbFor")
    depth, end = 0, start
    for i in range(script.index("{", start), len(script)):
        if script[i] == "{":
            depth += 1
        elif script[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    builder = script[start:end]
    assert "setTimeout" not in builder and "setInterval" not in builder, (
        "a pane schedules its own refresh, so the cost of the previews grows "
        "with the number of panes - which is the thing the arithmetic forbids")

    # And nothing in the WORKSPACE starts a repeating timer: the previews are
    # paced by one self-rescheduling loop and nothing else. Scoped to those
    # functions rather than to the whole page, because the step list and the
    # Thinking clock legitimately tick and a gate that forbade every interval
    # would be red on code it was never about.
    fleet = script[script.index("function thumbFor"):script.index("async function fleetPoll")]
    assert "setInterval" not in fleet, (
        "a workspace function repeats on an interval, so the cost of the "
        "previews grows with what is on screen")


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


def test_no_top_level_declaration_uses_a_name_declared_later():
    """⛔ THE SAME DAMAGE BY A DIFFERENT MECHANISM, and the duplicate-name gate
    above did not see it. `const QKEY = 'aihawk.queued.' + here;` was written
    forty lines above `let here`, and a top-level binding read inside its own
    dead zone throws when the script is evaluated - which kills the whole file:
    no event stream, no session column, no workspace, and the page still
    renders. All 440 tests were green with the page dead, the second time in
    two days that a suite could not see a page a browser cannot run.

    Both gates check the same thing from two sides: nothing at the top level of
    this script may depend on the ORDER of the lines being right. The real fix
    for a value that needs another is a function, which is evaluated when it is
    called.

    Only initialisers are read, not function bodies: a function may use anything
    declared anywhere, because it runs after the script has finished.
    """
    script = PAGE[PAGE.index("<script"):]
    lines = script.split(chr(10))

    declared, order = {}, []
    for n, line in enumerate(lines):
        if line[:1] not in ("l", "c", "v"):
            continue
        m = re.match(r"(?:let|const|var)\s+(.+?)\s*=", line)
        if not m:
            continue
        for part in m.group(1).split(","):
            name = part.split("=")[0].strip()
            if re.fullmatch(r"[A-Za-z_$][\w$]*", name or "") and name not in declared:
                declared[name] = n
                order.append((n, name, line))

    early = []
    for n, name, line in order:
        init = line.split("=", 1)[1]
        # ⛔ NOT INSIDE STRINGS AND REGEXES. The first version read the `i` of
        # `/^(I will |...)/i` as the variable `i` and accused a line that is
        # correct: a scan that cannot tell code from text is a gate that goes
        # red for the wrong reason, which is how gates get widened until they
        # see nothing.
        init = re.sub(r"'[^']*'|\"[^\"]*\"|`[^`]*`", "''", init)
        init = re.sub(r"/(?:[^/\
]|\.)+/[gimsuy]*", "RE", init)
        if "=>" in init or init.strip().startswith("function"):
            # A function value: its body runs later, so it may name anything.
            continue
        for other, where in declared.items():
            if where > n and re.search(r"(?<![.\w])%s(?![\w])" % re.escape(other), init):
                early.append("%s uses %s, declared %d lines later" % (name, other, where - n))
    assert not early, (
        "these read a top-level name before it is declared, which throws when "
        "the script is evaluated and stops the whole page from running: %s"
        % early)


def test_every_handler_the_page_wires_up_exists():
    """⛔ A FUNCTION THAT VANISHES IS ONLY FOUND BY CLICKING, and nothing in this
    suite clicks. Removing a block of the script took `watchThis` with it - it
    sat between two functions that were going away - and the page still loaded,
    still drew, still ran: only a click on a pane would have thrown, and no test
    clicks anything.

    Third time in three days that this page broke in a way a green suite could
    not see, and the third different mechanism: a duplicate name, an order, and
    now a missing definition behind an event handler.

    Known-bad: delete any `function` the page assigns to an `onclick`.
    """
    import re

    script = PAGE[PAGE.index("<script"):]
    code = re.sub(r"/\*.*?\*/", "", script, flags=re.S)

    wired = set(re.findall(r"on(?:click|dblclick|input|submit)\s*=\s*([A-Za-z_$][\w$]*)\s*;",
                           code))
    wired |= set(re.findall(r"=>\s*([A-Za-z_$][\w$]*)\(", code))
    defined = set(re.findall(r"(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", code))
    defined |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=", code))
    # Things the language and the document provide.
    BUILT_IN = {"fetch", "alert", "confirm", "prompt", "parseInt", "String",
                "Number", "JSON", "Math", "Object", "Array", "setTimeout",
                "clearTimeout", "setInterval", "clearInterval", "el", "$"}

    missing = sorted(n for n in wired if n not in defined and n not in BUILT_IN)
    assert not missing, (
        "the page wires these to an event and nothing defines them, so the "
        "handler throws the first time somebody uses it: %s" % missing)
