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

from invisible_playwright_mcp.link import text_of
from invisible_playwright_mcp.routes import build_app
from invisible_playwright_mcp.sessions import Sessions
from invisible_playwright_mcp.ui import PAGE

pytestmark = [pytest.mark.filterwarnings("ignore")]


class _Tool:
    def __init__(self, name, props):
        self.name = name
        self.inputSchema = {"type": "object", "properties": {p: {} for p in props}}


#: ⛔ NO `session` KEY. MCP stopped having a session concept on 2026-09-11:
#: `browser_list` answers `focus`, `browsers` and `note`, never which piece of
#: work it is - that is decided by which PROCESS answered, not by a field in
#: the reply. `limit` went in 0.55.0 with the per-row `focused`: the first was
#: the constant 2 and no reader in this product ever read it, the second was
#: the row id compared against the `focus` on the line above.
FLEET = {
    "focus": "main",
    "browsers": [
        {"id": "main", "urls": ["http://a/"]},
        {"id": "posta", "urls": ["http://b/"]},
    ],
    "note": "2 of 2 browsers. Commands that name none go to main.",
}


class _Text:
    """A tool result shaped the way one arrives over MCP.

    ⛔ NOT a bare string. `Link.call_text` is `text_of(await call(...))`, so a
    stand-in whose `call` answers None makes every text read come back empty -
    which reads as a server that answered nothing rather than as a stand-in
    that was the wrong shape.
    """

    def __init__(self, text):
        self.content = [type("Item", (), {"text": text})()]
        self.isError = False


class FakeLink:
    """One conversation's own connection - not shared with any other, exactly
    as `Sessions` now spawns one real server per conversation. Every test in
    this file drives a single conversation, so one instance is enough; a test
    that needed two would give each its own, the way `test_the_session_column.py`
    does.

    ⛔ NO TOOL TAKES `session_id`. It never did once MCP stopped having a
    session concept: `browser_watch` and `browser_list` are addressed by
    which PROCESS answers, never by an argument on the wire. And there is no
    tab tool to advertise since 2026-09-11 - a browser drives one page.
    """

    def __init__(self):
        self.touched = False
        self.tools = [_Tool("browser_watch", ["browser"]),
                      _Tool("browser_list", []),
                      ]
        self.calls = []
        self.answers = {"browser_list": json.dumps(FLEET)}

    async def call(self, name, arguments=None):
        self.touched = True
        self.calls.append((name, dict(arguments or {})))
        return _Text(self.answers[name]) if name in self.answers else None

    async def call_text(self, name, arguments=None) -> str:
        return text_of(await self.call(name, arguments))


class Brain:
    messages: list = []
    usage: dict = {}

    async def handle(self, text, link, say):
        await link.call("browser_navigate", {"url": "http://x/"})


def _app():
    """One conversation, its own `FakeLink`, and the app built around it.

    `open_link=` is the seam `Sessions` declares for exactly this: a
    conversation's connection without a real subprocess behind it. Every
    test here drives one conversation, so the same link answers whichever
    id is asked for.
    """
    from starlette.testclient import TestClient
    link = FakeLink()

    async def open_link(session_id):
        return link

    sessions = Sessions({}, None, Brain, open_link=open_link)
    return link, sessions, TestClient(build_app(sessions))


# --- what the page is told to draw ------------------------------------------

async def test_the_workspace_is_read_from_the_server_like_any_other_client():
    """The interface has no privileged path to the browsers: it asks the same
    tool an agent would.

    Known-bad: have the route keep its own list of browsers. It is right until
    the model opens one, which is the case the workspace exists for.
    """
    link, sessions, client = _app()
    await (await sessions.get("lavoro")).send("start something")

    got = client.get("/live/browsers?s=lavoro").json()

    assert [b["id"] for b in got["browsers"]] == ["main", "posta"]
    assert got["focus"] == "main"
    assert any(name == "browser_list" for name, _ in link.calls)


async def test_the_workspace_asks_the_one_question_that_starts_nothing():
    """⛔ THE GUARD THAT BELONGS ON THE PICTURE DOES NOT BELONG HERE, and putting
    it here cost the feature its whole point. The frame and the tab strip may not
    ask before an instruction because asking STARTS a browser. `browser_list`
    starts nothing - that is its promise and there is a test for it in the
    server - so the workspace asks always.

    Copying the guard looked prudent and was a bug: it made the workspace empty
    for a conversation that had opened a browser and then been reloaded - the
    browsers are the SERVER's and outlive the page, so what this conversation
    has asked for is not what it holds.

    ⛔ THE CASE IT WAS FIRST WRITTEN FOR IS GONE, and the test is kept for the
    one that remains. It used to be about a session reopened after a restart,
    whose browsers were DECLARED and not started: since 0.53.0 there is no
    such state, a browser is open or it is not there. What is still true, and
    still worth a test, is that drawing the workspace asks exactly one
    question and that question starts nothing.

    Known-bad: put `if not seen.link.touched: return empty` back at the top of
    the browsers route.
    """
    link, sessions, client = _app()
    # Opened, and nothing asked of it: that is the case under test. It has to be
    # opened rather than only named, because a request may no longer bring a
    # conversation into being - see `Sessions.knows`.
    await sessions.get("mai-usata")

    got = client.get("/live/browsers?s=mai-usata").json()

    assert [b["id"] for b in got["browsers"]] == ["main", "posta"], (
        "a conversation that has asked nothing was shown no panes, while the "
        "server holds browsers it opened before the page was reloaded")
    assert [name for name, _ in link.calls] == ["browser_list"], (
        "drawing the workspace called something other than the question that "
        "starts nothing: %r" % link.calls)


async def test_an_unreadable_answer_says_so_instead_of_drawing_an_empty_room():
    """⛔ A FAILURE THAT LOOKS LIKE AN EMPTY WORKSPACE IS THE WORST OF THE
    THREE STATES. This used to answer 200 with an empty fleet, for a server
    older than 0.18.0 that replied in prose - and there is no such server to
    talk to: the interface spawns the one it ships with, out of this same
    package. What the smoothing still did was hide a link that had stopped
    answering behind the picture of a session where nobody had opened
    anything, which is exactly the shape of [B202] one layer up.

    Known-bad, two: answer 200 with an empty fleet again, or let the route
    raise so the pane gets a 500 with no sentence in it.
    """
    link, sessions, client = _app()
    await (await sessions.get("lavoro")).send("start something")

    link.answers["browser_list"] = "the main browser is open, one of two."
    got = client.get("/live/browsers?s=lavoro")

    assert got.status_code == 503, (
        "an answer the route could not read was drawn as an empty workspace")
    assert "the main browser is open" in got.json()["error"], (
        "the 503 does not carry what the tool actually said")


# --- which browser a pane is watching ---------------------------------------

async def test_a_pane_asks_for_its_own_browser_and_not_for_the_focused_one():
    """Without this the workspace is one picture drawn several times.

    Known-bad: drop `browser_id` from the frame route. Every thumbnail then
    shows whatever the focused browser is looking at, which is a wrong answer
    that looks exactly like a right one.
    """
    link, sessions, client = _app()
    await (await sessions.get("lavoro")).send("start something")

    client.get("/live/frame?s=lavoro&b=posta")

    watched = [args for name, args in link.calls if name == "browser_watch"]
    assert watched and watched[-1].get("browser") == "posta", watched
    # ⛔ NO `session_id` TO ASSERT ON. Which conversation a request belongs to
    # is no longer an argument on the wire at all - it is which conversation's
    # own connection answered, and that guarantee is structural since 0.41.0:
    # `test_the_session_column.py` proves it with two conversations, each its
    # own `FakeLink`, which is a link this single-conversation setup cannot
    # even pose the question to.
    assert "session_id" not in watched[-1], (
        "a pane still sends session_id, which no tool accepts any more: %r"
        % watched[-1])


async def test_the_live_pane_still_asks_for_the_focused_browser_when_none_is_named():
    """The single-browser case is the common one and must not have gained an
    argument it does not need.

    Known-bad: make `browser_id` required in the frame route.
    """
    link, sessions, client = _app()
    await (await sessions.get("lavoro")).send("start something")

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

    Two different things, and they used to be one value. `stage.focus` is the
    browser the agent drives - it lives on the server and only the agent moves
    it. `stage.pinned` is the pane the person is looking at, which is this
    page's own business. Folding them together is what made a click a command.

    Known-bad: have `watchThis` POST anywhere.
    """
    import re

    script = PAGE[PAGE.index("<script"):]
    code = re.sub(r"/\*.*?\*/", "", script, flags=re.S)
    watch = code[code.index("function watchThis"):code.index("async function drawFleet")]

    assert "fetch" not in watch, (
        "clicking a pane sends something to the server, so looking at a browser "
        "moves the agent's hand: %s" % watch.strip()[:120])
    assert "stage.pinned" in watch, "the page has no idea of its own of what it is watching"
    assert "const watched = () => stage.pinned || stage.focus;" in code, (
        "the big pane does not follow the agent when nothing is pinned, so it "
        "stops showing the work while the work is happening")


# --- the arithmetic, read out of the page -----------------------------------

def test_the_workspace_has_no_strip_and_no_pump_of_its_own():
    """⛔ THE STRIP OF OTHER BROWSERS IS GONE BECAUSE IT WAS EMPTY BY
    CONSTRUCTION. It held the browsers not on the stage; the stage holds every
    open browser, up to the two a session can have, and since 0.53.0 a browser
    is either open or not there at all - nothing is "declared and not
    started" to draw a chip for. Before that a preview loop refreshed pictures
    in the same row, one pane every 400 ms, over an equally empty set.

    What has to stay true is the shape: the page's pumps are started from one
    place through one scheduler, and nothing in the workspace draws a second
    row or starts a timer of its own.

    Known-bad, two: put `#thumbs` back with a builder that fetches a picture;
    start a fourth pump.
    """
    code = re.sub(r"/\*.*?\*/", "", PAGE[PAGE.index("<script"):], flags=re.S)

    assert "thumbs" not in code and "chipFor" not in code and "drawStrip" not in code, (
        "the strip of other browsers is back, for a set that is empty by construction")
    assert 'id="thumbs"' not in PAGE, "the markup still holds the strip's box"

    # Three pumps, one shape, started from one line.
    started = re.findall(r"every\(([^,]+), (\w+)\);", code)
    # ⛔ TWO, AND IT WAS THREE. The address bar had a clock of its own at two
    # seconds, reading a fleet that a different clock refreshed at three: it
    # could only ever redraw the same answer between two arrivals. Whoever
    # changes the fleet tells it now, and the one moment it has to be quick - a
    # screen being clicked - already called it directly. Same shape as the
    # `/live/address` route, removed for the same reason.
    assert sorted(p for _, p in started) == ["drawFleet", "onePass"], (
        "the page's pumps are not the two started through `every`: %r" % started)
    assert "paintWhere();" in code[code.index("async function drawFleet()"):], (
        "nothing tells the address bar when the fleet changed, so it is only "
        "as fresh as the next thing that happens to call it")
    assert "slowTick" not in code and "SLOW_MS" not in code, (
        "the preview loop is back, refreshing a row that cannot hold a picture")


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

    Known-bad: declare `let turn` again in the workspace.
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
    BUILT_IN = {"fetch", "alert", "confirm", "prompt", "parseInt", "parseFloat",
                "getComputedStyle", "String",
                "Number", "JSON", "Math", "Object", "Array", "setTimeout",
                "clearTimeout", "setInterval", "clearInterval", "el", "$"}

    missing = sorted(n for n in wired if n not in defined and n not in BUILT_IN)
    assert not missing, (
        "the page wires these to an event and nothing defines them, so the "
        "handler throws the first time somebody uses it: %s" % missing)


def test_the_answer_measure_is_inside_the_range_every_source_agrees_on():
    """⛔ THIS NUMBER HAS BEEN WRONG THREE TIMES, TWICE THE SAME WAY: computed
    in `ch` and read as characters.

    `ch` is the advance width of the digit zero. In a proportional font that is
    much wider than an average letter, so a cap written in `ch` looks like a
    character count and is not one. Measured on this font with a canvas: `0` is
    7.55px at 14px system-ui and the average character of a sentence is 6.11px,
    so one `ch` is 1.24 characters. First the cap was 72ch believing it was 72
    characters, and was 83; then 84ch to make up for an indent, and was 98.

    ⛔ THE THIRD TIME THERE WAS NO CAP LEFT TO CHECK. It came off: the measure
    is the width of the pane now and the separator is the control that sets it,
    because a fixed number widened nothing when somebody dragged the pane in
    order to read more - reported twice, the second time with a screenshot.

    What still has to hold is the DEFAULT, the width the pane opens at for
    anybody who never drags. So that is what this computes, from the pane's own
    declared ceiling rather than from a number written down anywhere.

    Known-bad, three: widen the default pane past what the measure allows; put a
    cap back on the transcript; drop the log's padding so the text runs to the
    edge.
    """
    import re

    #: ⛔ THE FLOOR IS A TOKEN NOW, so the rule no longer spells three pixel
    #: literals and a regex pinned to that shape stopped matching at all -
    #: which is an AttributeError, not a red assertion, and reads as the gate
    #: being broken rather than as the page having changed. The only pixel
    #: literal left in the rule is the ceiling, which is the number this
    #: whole calculation is about.
    rule = PAGE[PAGE.index("#left {"):]
    rule = " ".join(rule[:rule.index("}")].split())
    pane = float(re.search(r"([\d.]+)px", rule).group(1))
    assert re.search(r"#log\{[^}]*padding:var\(--s5\) var\(--s4\)", PAGE), (
        "the transcript no longer states its own padding, so this cannot be "
        "computed from the file")
    pad = float(re.search(r"--s4:([\d.]+)px", PAGE).group(1))
    gutter = float(re.search(r"--gutter:([\d.]+)rem", PAGE).group(1))
    gap = float(re.search(r"--gap:([\d.]+)rem", PAGE).group(1))
    body = float(re.search(r"--t-body:([\d.]+)rem", PAGE).group(1))

    #: Measured in the browser on the face this page declares, at 14px.
    AVG_AT_14, ROOT_PX = 6.11, 16.0
    avg = AVG_AT_14 * (body * ROOT_PX) / 14.0     # same face, one size up

    indent = (gutter + gap) * ROOT_PX             # --indent, which an answer carries
    chars = (pane - pad * 2 - indent) / avg
    assert 65 <= chars <= 80, (
        "the answer opens at %.0f characters a line, outside the 65 to 80 that "
        "chat design guidance, Baymard and WCAG 2.1 AAA all land inside" % chars)

    # And nothing pins it there once somebody drags, which is the whole point of
    # the pane being the control.
    assert not re.search(r"#thread\{[^}]*max-width", PAGE), (
        "the transcript is capped again, so dragging the pane widens nothing")

