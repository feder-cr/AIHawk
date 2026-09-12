"""What the interface must never do to the person watching it.

Every rule here comes from a defect that was on the screen when it was written,
found by an audit run against the live page rather than against an idea of it.
They have one shape in common: a stated rule that stopped being enforced one step
past where it was written down.
"""
from __future__ import annotations

import re

from pathlib import Path

from aihawk.web import PAGE

#: ⛔ BOTH COMMENT SYNTAXES. This page explains its own rules in prose
#: beside the code, so a scan that only strips `/* */` gets accused by the
#: `<!-- -->` that says why the thing it forbids is forbidden - which is the
#: defect this project has written down more than any other.
CODE = re.sub(r"/\*.*?\*/|<!--.*?-->", "", PAGE, flags=re.S)


def test_typed_text_is_not_thrown_away_before_the_server_has_it():
    """⛔ THE ONE THING THIS INTERFACE MUST NOT DO. The composer emptied itself
    and then fired a `fetch` nobody read: server restarting, port moved, laptop
    asleep, and the instruction was gone with the transcript never growing -
    which reads as the agent ignoring you. This page already argues exactly that
    about the QUEUED path, and hardened that one into localStorage; the primary
    path kept the old shape.

    Known-bad: drop the await, or the restore.
    """
    send = CODE[CODE.index("async function send(text)"):]
    send = send[:send.index("\n}")]
    assert re.search(r"await (door|fetch)\(", send), (
        "the send does not wait for an answer")
    assert "if(!r.ok) throw" in send, "an HTTP error is treated as a send"
    assert "i.value = text" in send, (
        "the sentence is not given back when it did not arrive, and this page "
        "holds the only copy of it")


def test_a_refused_delete_is_not_drawn_as_a_delete():
    """The server REFUSES to forget a session whose agent is mid-run and answers
    200 with `forgotten:false`. Ignoring the body meant confirming the delete,
    being navigated away, and leaving the session and its browsers exactly where
    they were - with every visible signal saying it had worked.

    Known-bad: stop reading the answer.
    """
    body = CODE[CODE.index("async function forgetChat"):]
    body = body[:body.index("\n}")]
    assert "forgotten" in body, "the answer to the delete is never read"
    assert "orphan(" in body, "a refused delete says nothing to the person who asked"


def test_every_event_the_server_can_send_is_drawn():
    """⛔ AN EVENT WITH NO CASE IS DRAWN AS RAW JSON, and the suite cannot see
    it. The page ends its switch with a `default` that appends the text to the
    transcript, which is right for a kind added on the server before the page
    learns it - a row of prose beats silence. It is wrong for a kind the page
    used to draw and stopped: removing the meter left `usage` falling through,
    and the transcript ended with
    `{"prompt": 2341240, "completion": 19714, "calls": 75, ...}` under the last
    answer. 528 tests were green. It was found by opening the page.

    So the two sides are compared here instead: whatever the server can emit,
    the page names.

    Known-bad: emit a kind the page does not name, or drop a case for one it
    does.
    """
    web = (Path(__file__).resolve().parents[1]
           / "src" / "aihawk" / "web.py").read_bytes().decode("utf-8")
    loop = (Path(__file__).resolve().parents[1]
            / "src" / "aihawk" / "agent.py").read_bytes().decode("utf-8")
    # Comments stripped from both sides, because this project has recorded the
    # gate-accused-by-a-comment defect more times than any other.
    server = re.sub(r"#[^\n]*", "", web + loop)
    sends = set(re.findall(r"(?:emit|say)\(\s*\"([a-z]+)\"", server))
    sends |= set(re.findall(r'"kind":\s*"([a-z]+)"', server))
    sends -= {"kind"}
    drawn = set(re.findall(r"case '([a-z]+)':", CODE))
    assert sends, "found no event kinds at all, so this gate is not looking"
    missing = sorted(sends - drawn)
    assert not missing, (
        "the server can send %s and the page names none of them, so each one "
        "lands in the transcript as raw JSON" % missing)


def test_dragging_the_pane_wider_widens_something():
    """⛔ A CONTROL THAT OFFERS A RANGE WHERE NOTHING HAPPENS IS A CONTROL THAT
    LIES. The measure cap sat on the whole transcript, so the separator could be
    dragged from 530px to 1440 and the conversation stopped growing at 534: the
    rest of the pane turned into margin. Reported by the owner as "the chat does
    not get wider", and measured exactly that.

    The cap belongs to the PROSE, which is unreadable at 200 characters a line
    whatever the window is. It does not belong to the step rows, which are
    monospace data already cut off at 48 characters with the rest behind a
    disclosure: measured after, the track goes from 416px at the default width to
    1326px dragged wide, and an address that was truncated fits whole.

    Known-bad, three: put the cap back on `#thread`; take it off the prose so a
    line runs the whole pane; pin the row's middle column to something fixed so
    the slack stops reaching it.
    """
    thread = re.search(r"#thread\{([^}]*)\}", CODE)
    assert thread, "the transcript has no rule of its own"
    assert "max-width" not in thread.group(1), (
        "the cap is back on the whole transcript, so widening the pane widens "
        "nothing: %s" % thread.group(1))

    # ⛔ AND NO CAP ON THE PROSE EITHER, WHICH IS WHERE THIS GATE FIRST LANDED.
    # Moving the cap off the transcript widened the step rows and left the
    # answer exactly where it was - the text a person actually reads - so the
    # report came back a second time, with a screenshot. The pane IS the
    # measure now; the default width is what keeps it sane, and that is
    # checked where it can be computed, in the workspace gate.
    assert not re.search(r"\.answer > \*[^}]*max-width", CODE), (
        "the prose is capped again, so the sentences wrap in the same place however wide the pane is dragged")

    row = re.search(r"\.row\{([^}]*)\}", CODE)
    assert row and "minmax(0,1fr)" in row.group(1), (
        "the step row no longer takes the slack, so the width the drag hands "
        "over stops before the one thing that was short: %s"
        % (row.group(1) if row else "no rule"))

def test_the_heading_survives_being_invisible():
    """⛔ IT READS AS DEAD MARKUP AND IT IS LOAD-BEARING. The product's name was
    taken off the screen because it said what the tab, the window and the
    address bar already said. The heading stayed, because the answers' own
    headings start at h3 on the reasoning that a name sits above them: delete it
    and every one of them hangs under nothing and the document has no outline at
    all. An h1 nobody can see is the single most deletable-looking line on this
    page, so it is held here.

    And it is hidden the ONE way that keeps it: `display:none` and
    `visibility:hidden` take an element out of the accessibility tree as well as
    off the screen, which would delete it in the only sense that still mattered.
    Same family as `pointer-events` versus `inert` elsewhere in this file - the
    property that hides has to be the one that hides only what was meant.

    Known-bad: drop the class and it is visible again; drop the heading and the
    outline goes; hide it with `display:none` and it is gone for a reader.
    """
    assert re.search(r'<h1[^>]*>', CODE), (
        "the page has no heading, so every answer's own headings hang under "
        "nothing")
    assert re.search(r'<h1 class="sr">', CODE), (
        "the heading is either back on the screen or hidden by some other means")
    assert "h3.md-h" in CODE, (
        "the answers no longer start at h3, so the reason this heading has to "
        "exist may have changed - check before touching it")
    rule = re.search(r"\.sr\{([^}]*)\}", CODE)
    assert rule, "the class that hides the heading is gone"
    for kills in ("display:none", "visibility:hidden"):
        assert kills not in rule.group(1).replace(" ", ""), (
            "`.sr` uses %r, which takes the heading out of the accessibility "
            "tree too: %r" % (kills, rule.group(1)))


def test_the_transcript_is_announced_and_not_only_drawn():
    """Everything the agent does arrives by appending a node. With one live
    region on the page - carrying the word `idle` - somebody who cannot see the
    screen was told nothing, ever, and the other channel is a screenshot with an
    empty alt on purpose.

    Known-bad: take the role off, or go back to hiding the state word with
    `hidden`, which is display:none and silences the announcement exactly when
    it stops being redundant.
    """
    assert re.search(r'id="thread"[^>]*role="log"', PAGE), (
        "the transcript is not a log for anything that is not a pair of eyes")
    assert re.search(r'id="thread"[^>]*aria-live', PAGE), "the log never announces"
    assert "stateEl.hidden" not in CODE, (
        "the state word is removed from the accessibility tree rather than from "
        "the screen")


def test_a_control_that_cannot_act_is_out_of_reach_of_the_keyboard_too():
    """`pointer-events:none` only stops the mouse: the buttons kept their place
    in the tab order, kept the focus ring, and Enter still fired the handler. So
    with nothing open a keyboard could work five controls that look dead, and a
    screen reader announced them as ordinary enabled buttons.

    Known-bad: go back to dimming them and nothing else.
    """
    assert "$('mode').inert = !anything" in CODE, (
        "the disarmed control is only dimmed, so it still answers the keyboard")


def test_nothing_hides_behind_a_role_it_does_not_implement():
    """`role="tablist"` promises panels this page does not have and a keyboard
    pattern it does not implement: arrow keys did nothing and `aria-controls`
    pointed at nothing, while a screen reader announced "tab, 1 of 2" for a
    two-state switch. Its neighbour, the layout picker, already had this right.

    Known-bad: put the tab roles back.
    """
    assert 'role="tablist"' not in CODE, "a switch is announced as a set of tabs"
    assert re.search(r'id="mode"[^>]*role="group"', PAGE), (
        "the pair has no role at all, so it is announced as two loose buttons")
    assert CODE.count('aria-pressed="true" data-v="live"') == 1, (
        "the switch does not say which side it is on")


def test_the_only_input_on_the_page_is_reachable_without_the_transcript():
    """Measured on a live run: 129 focusable elements, 108 of them transcript
    rows, and the composer at index 111. The count grows with every step of
    every run.

    Known-bad: remove the skip link.
    """
    assert re.search(r'<a class="skip" href="#i"', PAGE), (
        "the composer is still behind the whole transcript for a keyboard")
    assert PAGE.index('class="skip"') < PAGE.index('id="railtab"'), (
        "the skip link is not the first thing in the document, so it is not the "
        "first thing focus reaches")


def test_a_stopped_browser_is_never_asked_anything():
    """A stopped browser has no address, and the bar goes blank rather than
    keeping the last one.

    ⛔ THIS USED TO BE A SAFETY RULE AND IS NOT ANY MORE, which is worth
    saying because the reason it was written is the expensive one: asking a
    declared-but-stopped browser for its tabs STARTED it - the server
    resolved the id and the registry woke the engine - so clicking a stopped
    browser's chip spent 800 MB and seven seconds nobody asked for, and then
    kept asking every two seconds because the pin never cleared. `paintWhere`
    asks nothing at all now: it reads the fleet the workspace already holds.
    The safety version of the rule still binds the frame pump, the preview
    row and both cell builders, which are tested beside this.

    Known-bad: drop the guard from `paintWhere`.
    """
    where = CODE[CODE.index("function paintWhere"):]
    where = where[:where.index("\n}")]
    assert "b.running" in where, (
        "the address bar asks about a browser without checking it is running, "
        "which starts it")

def test_the_address_bar_says_where_the_browser_being_watched_is():
    """⛔ EXECUTED, NOT SCANNED, because the two ways to get this wrong both
    produce a url and both look right.

    This choice used to be a route, `/live/address`, with four tests on the
    server. It moved into the page when the route turned out to be asking
    `browser_list` a second time, on a second timer, for a field the rows
    `/live/browsers` already returns - and because which browser a person is
    WATCHING is a fact of the page: a pinned pane changes it instantly and a
    poll from three seconds ago cannot know.

    Moving it must not cost the two properties those tests held, so this
    runs the function rather than reading it. `node` is on this machine and
    on every CI runner, and the function is pure, so it needs no DOM at all.

    Known-bad, and both are one character away: read `urls[0]` instead of
    `url`, which agrees until a site opens a second page; or answer the
    focused row whatever was asked for, which names a browser nobody is
    looking at.
    """
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if not node:
        pytest.skip("needs node to EXECUTE the page's address choice")

    body = CODE[CODE.index("function addressOf"):]
    body = body[:body.index(chr(10) + "}") + 2]

    rows = [
        {"id": "main", "running": True, "focused": True,
         "url": "https://b.example/x",
         "urls": ["https://a.example/", "https://b.example/x"]},
        {"id": "support", "running": True, "focused": False,
         "url": "https://mail.example/", "urls": ["https://mail.example/"]},
    ]
    js = body + "%sconst rows = %s;%s" % (chr(10), json.dumps(rows), chr(10)) + """
const out = {
  focused: addressOf(rows, ''),
  watched: addressOf(rows, 'support'),
  unknown: addressOf(rows, 'nope'),
  empty: addressOf([], ''),
  notalist: addressOf(null, ''),
  nourl: addressOf([{id: 'x', focused: true}], ''),
};
process.stdout.write(JSON.stringify(out));
"""
    done = subprocess.run([node, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, done.stderr
    got = json.loads(done.stdout)

    assert got["focused"] == "https://b.example/x", (
        "the bar shows a page the browser is not on: with two pages open it read the first one in the list instead of the live one")
    assert got["watched"] == "https://mail.example/", (
        "a pinned pane was told the focused browser's address, which is a wrong answer that looks exactly like a right one")
    assert got["unknown"] == "", "a browser that is not in the fleet has no address"
    assert got["empty"] == "" and got["notalist"] == "" and got["nourl"] == "", (
        "an empty or unreadable fleet has to leave the bar blank rather than throw")



def test_a_frame_is_revoked_before_its_element_is_thrown_away():
    """Every frame is an object URL, and a blob is not collected with its
    element. The stage redraws whenever the agent moves to another browser -
    which it does on its own - so a long run leaked one full window capture per
    pane per switch, held until the tab closes.

    Known-bad: remove either call.
    """
    assert CODE.count("dropFrames(box);") == 2, (
        "one of the two rebuild paths throws its pictures away without revoking "
        "them")
    assert "URL.revokeObjectURL" in CODE[CODE.index("function dropFrames"):
                                         CODE.index("function blank")]


def test_a_password_is_not_written_into_the_transcript():
    """`Typed #passcode-input <- 434262` was on the screen and in the saved
    file: the line that exists so a person can follow along was also the line
    that kept the secret, and the transcript outlives the session.

    Known-bad: drop the masking, or the field vocabulary.
    """
    from aihawk.actions_help import summarise

    secret = summarise("browser_type", {"selector": "#passcode-input",
                                        "text": "434262"})
    assert "434262" not in secret, "the code typed into the page is printed back"
    assert "6 characters" in secret, (
        "the row says nothing at all, and then the reader cannot tell a typed "
        "field from a skipped one")

    ordinary = summarise("browser_type", {"selector": "input[type=email]",
                                          "text": "a@b.test"})
    assert "a@b.test" in ordinary, "an ordinary field is masked as well"


def test_a_step_says_support_when_the_call_went_to_the_helper():
    """A session drives `main` and, while it is needed, `support`, and 35 rows
    of a live transcript reading exactly `Read body` drop the one fact that
    tells them apart: whether the agent was working in the identity or in the
    helper beside it.

    It is named only when it is the HELPER. `main` is where a step goes unless
    it says otherwise, so writing it on every row is the same word repeated,
    which is how the useful one stops being noticed.

    Known-bad, two: discard `browser` and the rows are indistinguishable again;
    name `main` too, and the mark that means something is buried.
    """
    from aihawk.actions_help import summarise

    assert summarise("browser_read_text", {"selector": "body",
                                           "browser": "support"}) == "body in support"
    assert summarise("browser_read_text", {"selector": "body",
                                           "browser": "main"}) == "body"
    assert summarise("browser_read_text", {"selector": "body"}) == "body"
    assert "browser=" not in summarise("browser_open", {"browser": "support"}), (
        "opening a browser prints the name of an argument at the reader")


def test_every_request_that_can_fail_goes_through_one_door():
    """Six POSTs had no failure path at all, and the sharpest was the stop
    button: this page says elsewhere that it is the only thing that ends a run
    which will not converge, and a press that never reached the server looked
    exactly like a press that did.

    Two calls keep their own recovery because it is more than a message - the
    send puts the sentence back in the box, the delete reads whether the server
    refused - and both are tested above.

    Known-bad: add a bare `fetch(..., {method:'POST'})` anywhere else.
    """
    posts = re.findall(r"fetch\((?:at\()?'([^']+)'[^;]*?method:'POST'", CODE, re.S)
    bespoke = {"/chat/send", "/sessions/forget"}
    loose = [p for p in posts if p not in bespoke]
    assert loose == [], (
        "%d request(s) can fail silently: %s" % (len(loose), loose))
    assert "async function ask(path, body, whatFailed)" in CODE, (
        "the one door is gone, so every caller invents its own answer to a "
        "failure and most of them will not")


def test_every_question_this_page_asks_goes_through_one_of_two_doors():
    """⛔ AND ONE PLACE READS THE ANSWER FOR BOTH. Six fetches carried `?s=` and
    each asked on its own, so a page left open on a session somebody deleted
    went on asking forever - and every one of those questions declared the
    session again on the server, so the delete came back as an empty row for as
    long as that tab stayed open.

    ⛔ AND TWO MORE WERE OUTSIDE IT ALTOGETHER until 2026-09-12. `/sessions` and
    `/sessions/forget` are about the SET of conversations rather than one, so
    they must not have `?s=` appended - and they skipped the whole door to avoid
    it, which also skipped what a 404 and a 410 mean. Delete a session on a
    server that no longer serves that route and the page said `That session is
    still working`: a wrong explanation, which is worse than none, because it
    sends somebody to stop a run that is not running.

    Addressing and reading the answer are two jobs. `door` does both, `plainDoor`
    only the second, and `readStatus` is the one place that knows what an answer
    means.

    Known-bad: call `fetch` anywhere else, or take the 410 out of the reader.
    """
    assert len(re.findall(r"fetch\(at\(", CODE)) == 1, (
        "more than one place builds a session-scoped request, and the rest will "
        "not notice a conversation that no longer exists")
    assert len(re.findall(r"[^.\w]fetch\(", CODE)) == 2, (
        "%d places call fetch; there are two doors and everything else has to go "
        "through one of them, or it cannot be told the page is stale or the "
        "conversation gone" % len(re.findall(r"[^.\w]fetch\(", CODE)))
    body = CODE[CODE.index("function readStatus(path, r)"):]
    body = body[:body.index(chr(10) + "}")]
    assert "410" in body and "vanish()" in body, (
        "the reader does not read the one answer that will never stop being true")
    assert "404" in body and "outOfDate(" in body, (
        "the reader stopped noticing a route this server does not have")


def test_a_deleted_conversation_stops_the_page_asking_about_it():
    """The other half of the same defect: the server refuses now, and the page
    has to stop rather than retry a 410 four times a second in three loops.

    Known-bad: leave `looking` reading only `document.hidden`, or drop the
    `vanish` guard so the page keeps a live composer over a dead session.
    """
    assert "!document.hidden && !vanished" in CODE, (
        "the four loops go on polling a conversation that does not exist")
    body = CODE[CODE.index("function vanish()"):]
    body = body[:body.index("\n}")]
    assert "es.close()" in body, "the event stream is left open on a dead session"
    assert "box.inert = true" in body, (
        "the composer still answers the keyboard for a conversation that cannot "
        "receive anything")
    assert "orphan(" in body, "the page says nothing about why it went quiet"


def test_a_subtree_that_cannot_be_used_does_not_look_usable():
    """⛔ `inert` HAS NO LOOK. This page spells "cannot be used" as `opacity:.3`
    on a disabled button and then said the same thing about whole subtrees with
    `inert`, which draws them exactly as before. It was wrong before the case
    that found it: the Live/Frozen pair and the layout picker go inert whenever
    there is nothing to see, and stayed fully lit throughout. Seen on the running
    page: a deleted conversation left a composer inviting a sentence it could
    not send.

    Known-bad: drop the rule and let each caller remember to dim its own subtree.
    """
    css = CODE[CODE.index("<style>"):CODE.index("</style>")]
    assert re.search(r"\[inert\]\{[^}]*opacity", css), (
        "nothing makes an inert subtree look inert, so every control inside one "
        "keeps inviting an action it cannot perform")


def test_no_colour_is_typed_out_instead_of_named():
    """Seven surfaces carried `--err` and `--well` re-expanded as rgba by hand,
    plus a second orange one shade off the accent, a sixth grey, and two dead
    fallbacks that could never render. A token typed out is not that token: it
    is a colour that resembles it until somebody moves the token.

    Known-bad: put any of the hand-expanded values back.
    """
    css = CODE[CODE.index("<style>"):CODE.index("</style>")]
    ladder = {"--fg": "#dfe4e8", "--fg-2": "#a6b0b8", "--fg-3": "#8d98a1",
              "--accent": "#e0a35f", "--err": "#e88b76", "--well": "#0b0d10",
              "--base": "#101317", "--raised": "#171b21"}
    for name, value in ladder.items():
        # the declaration itself is the one legitimate occurrence
        assert css.count(value) == 1, (
            "%s is written out %d times; every use but the declaration should "
            "name the token" % (name, css.count(value)))
    channels = re.findall(r"rgba\((\d+),\s*(\d+),\s*(\d+)", css)
    for r, g, b in channels:
        assert r == g == b, (
            "rgba(%s,%s,%s) is a hue written by hand; the edges of this page are "
            "translucent WHITE by rule, and anything with a hue belongs to a "
            "token" % (r, g, b))


def test_nothing_is_polled_while_nobody_is_looking():
    """Four loops ran flat out in a background tab - the frame pump at up to
    forty requests a second - and that budget was measured against what the pipe
    can carry while the AGENT is using it. The agent keeps working when the tab
    is hidden, which is exactly when the page was still spending its share on
    pictures nobody could see.

    Known-bad: drop the guard from any of the four.
    """
    assert "const looking = () => !document.hidden" in CODE, (
        "nothing asks whether the page is being looked at")
    assert CODE.count("looking()") >= 5, (
        "only %d of the four loops check, plus the definition"
        % (CODE.count("looking()") - 1))
    assert "visibilitychange" in CODE, (
        "coming back to the tab waits for the next tick instead of catching up")


def test_the_parser_has_a_floor():
    """⛔ THE TEXT CAME FROM A MODEL THAT HAD JUST READ ARBITRARY WEB PAGES.
    Measured against the extracted parser: 20,000 `>` on one line, or a list
    indented 10,000 levels, threw RangeError - and the throw landed in the event
    handler, where it stranded the step clock, skipped the redraw and ate the
    queued instruction.

    Known-bad: remove the depth check, or the try around the render.
    """
    assert "const DEEP" in CODE, "the recursion has no floor"
    assert CODE.count("depth < DEEP") + CODE.count("(depth || 0) < DEEP") >= 3, (
        "the floor is declared and not applied at every recursion")
    flush = CODE[CODE.index("function flush(asAnswer, replay)"):]
    flush = flush[:flush.index(chr(10) + "}")]
    assert "try {" in flush and "catch" in flush, (
        "a defect inside one answer still takes the whole turn with it")


def test_a_row_is_only_collapsed_when_it_actually_fits():
    """The threshold was 120 characters into a track that shows about 48, so 43
    rows of a live transcript were cut off AND had their disclosure removed. A
    count in one unit standing in for a fit in another is the same defect this
    project recorded when `ch` was mistaken for a character.

    Known-bad: raise the threshold back above what the box holds.
    """
    got = re.search(r"const LONG = (\d+);", CODE)
    assert got, "the threshold is gone"
    assert int(got.group(1)) <= 60, (
        "a row keeps its whole output on one line up to %s characters, in a "
        "track that shows about 48" % got.group(1))
    assert ".lab').title = text" in CODE, (
        "a row that does not fit says nothing on hover either")
    assert "user-select:text; grid-column:2" in CODE, (
        "the label cannot be selected, so a truncated address cannot even be "
        "copied out")


def test_no_pump_of_the_page_can_be_killed_by_one_exception():
    """⛔ A PUMP THAT RE-ARMS AFTER THE WORK DIES FOR GOOD ON THE FIRST
    EXCEPTION: it does not skip a turn, it stops.

    Measured 2026-09-11 on the address bar. `paintWhere` had a `try` of its
    own; rewriting the function took it away, and from that moment any
    exception inside it would have stopped `where` for the life of the page -
    the bar keeps whatever it had, which at load is `no page yet`, and nothing
    says it is dead.

    The same shape was already latent in two more pumps: their `try` covered
    the fetch and not the lines around it, so a missing node or a fleet of an
    unexpected shape would stop them just as permanently. Only `tick` was
    safe.

    Fixed at the origin rather than function by function: the re-arm sits in a
    `finally`, so the chain no longer depends on what the pass does, and the
    question 'did I remember the try?' stops being asked of every function a
    pump calls.

    EXECUTED rather than scanned: a scan that finds `setTimeout` in the body
    cannot say whether it is REACHED when the pass throws, which is the only
    thing that matters here.

    Known-bad: move the `setTimeout` of any of the four back after the body
    instead of into the `finally`.
    """
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if not node:
        pytest.skip("needs node to EXECUTE the page's pumps")

    #: the pump, and the name of the pass it calls.
    pumps = {"tick": "onePass", "where": "paintWhere",
             "slowTick": "slowPass", "fleetPoll": "drawFleet"}

    dead = []
    for pump, pass_name in sorted(pumps.items()):
        src = CODE[CODE.index("async function %s(){" % pump):]
        src = src[:src.index(chr(10) + "}") + 2]
        js = (
            "let armed = 0;"
            + "globalThis.setTimeout = () => { armed++; return 0; };"
            + "globalThis.looking = () => true;"
            + "globalThis.pause = () => 100;"
            + "globalThis.SLOW_MS = 400;"
            + "globalThis.%s = async () => { throw new Error('boom'); };" % pass_name
            + chr(10) + src + chr(10)
            + "%s().catch(() => {}).then(() => " % pump
            + "process.stdout.write(JSON.stringify({armed})));"
        )
        done = subprocess.run([node, "-e", js], capture_output=True, text=True,
                              encoding="utf-8", timeout=30)
        assert done.returncode == 0, (pump, done.stderr)
        if json.loads(done.stdout)["armed"] != 1:
            dead.append(pump)

    assert not dead, (
        "these pumps do not re-arm when their pass throws, so they stop for the "
        "life of the page instead of skipping one turn: %s" % dead)


def test_a_page_older_than_the_server_says_so_instead_of_going_quiet():
    """⛔ A TAB LEFT OPEN ACROSS A DEPLOY ASKS FOR ROUTES THAT ARE GONE, AND
    until 2026-09-11 it did that in silence.

    Reported from a real session: the address bar said `no page yet` on a
    browser plainly sitting on a page. The server was answering correctly and
    a freshly loaded page showed the url; the open tab was older than the
    server, and the route it asked for had been removed that morning. The code
    read `if(r.ok)` and dropped the 404 without a word, so one part of the
    page quietly stopped being true while everything else kept working - which
    is the worst shape a defect can take, because nothing points at it.

    Every path this page asks for is a route the app declares, so a 404 cannot
    mean a missing row or a bad id. It can only mean the page and the server
    disagree about what exists.

    It SAYS it and changes nothing else. Going inert, the way a deleted
    conversation does, would take away more than the defect did: only the
    routes that went away stop answering, and the rest of the page is still
    live and still worth reading.

    Known-bad: drop the 404 branch from `door`, or let it speak every time -
    a pump asking every two seconds would write the same sentence thirty times
    a minute, which is a different way of being unreadable.
    """
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if not node:
        pytest.skip("needs node to EXECUTE the page's fetch funnel")

    def whole(name):
        src = CODE[CODE.index(name):]
        return src[:src.index(chr(10) + "}") + 2]

    js = (whole("async function door(") + chr(10)
          + whole("function readStatus(") + chr(10)
          + whole("function outOfDate(") + chr(10)
          + "let notices = [], vanished = false, outdated = false, status = 200;\nglobalThis.at = p => p;\nglobalThis.orphan = (kind, t) => notices.push(t);\nglobalThis.vanish = () => { vanished = true; };\nglobalThis.fetch = async () => ({status, ok: status >= 200 && status < 300});\n(async () => {\n  const out = {};\n  status = 200; await door('/live/browsers?s=x'); out.afterOk = notices.length;\n  status = 404; await door('/live/address?s=x');\n  out.afterFirst = notices.length; out.text = notices[0] || '';\n  await door('/live/address?s=x'); out.afterSecond = notices.length;\n  status = 410;\n  try { await door('/chat/send?s=x'); } catch (e) { out.threw = true; }\n  out.vanished = vanished;\n  process.stdout.write(JSON.stringify(out));\n})();")
    done = subprocess.run([node, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, done.stderr
    got = json.loads(done.stdout)

    assert got["afterOk"] == 0, "an answer that worked put a notice on the page"
    assert got["afterFirst"] == 1, (
        "a route this server does not have was dropped in silence, which is how "
        "a tab older than the server looks like a tab where one feature broke")
    assert "older than the server" in got["text"] and "Reload" in got["text"], (
        "the notice does not say what happened or what to do: %r" % got["text"])
    assert "/live/address" in got["text"] and "?s=" not in got["text"], (
        "the notice should name the path and not the conversation id: %r"
        % got["text"])
    assert got["afterSecond"] == 1, (
        "said twice, so a pump on a two second timer writes it thirty times a "
        "minute and the transcript becomes the notice")
    assert got.get("threw") and got["vanished"], (
        "the 410 path stopped working while the 404 one was added")


def test_opening_the_rail_moves_nothing_outside_it():
    """⛔ THE SESSION COLUMN LIVES OVER THE CONVERSATION, AND THE CONVERSATION
    KNOWS NOTHING ABOUT IT. Owner, looking at it: the bar has to live on top,
    and the chat must not know a thing.

    It did not. Measured in a real browser on 2026-09-11: opening the column
    moved `#left` from x=48 to x=0 and widened the browser pane by 48, because
    the spine left the flow to give its width back - and the transcript and the
    composer took a left padding at the same time, so every paragraph rewrapped
    while the panel appeared. Content height went 4234 to 4412. Somebody
    reading had the words move under their eyes to open a list.

    Now the spine belongs to the frame and stays, the drawer slides out beside
    it, and the same measurement gives identical boxes before and after.

    Two rules, and the second is the one that is easy to reintroduce:

    * nothing OUTSIDE the rail may be selected by the rail's open state;
    * the toggle may restyle itself - ink, background - but may not change its
      own BOX, because the spine is in the flow and its box is everybody
      else's position.

    Known-bad: put back either the rule that took the toggle out of the flow
    when open, or the one that padded the transcript to dodge the panel.
    """
    import re

    style = CODE[CODE.index("<style"):CODE.index("</style>")]
    #: what moves a box, as opposed to what colours it.
    #: ⛔ WIDENED 2026-09-12. The first list had position, the offsets, width,
    #: height, padding, margin, display, float and transform - and missed
    #: `flex`, the min/max pair and a custom property, each of which moves the
    #: spine just as surely. A list of what counts as moving is a list somebody
    #: has to keep, so it is written wide rather than tight.
    boxy = ("position", "top", "left", "right", "bottom", "inset", "width",
            "height", "padding", "margin", "display", "float", "transform",
            "flex", "min", "max", "gap", "order", "grid", "translate",
            "scale", "zoom", "contain", "aspect")

    outside, moved = [], []
    for selector, decls in re.findall(r"([^{}]+)\{([^{}]*)\}", style):
        sel = ' '.join(selector.split())
        if "#rail" not in sel and "aria-expanded" not in sel:
            continue
        keyed = "aria-expanded" in sel or ":not([hidden])" in sel
        if not keyed:
            continue
        #: ⛔ THE SUBJECT HAS TO BE THE RAIL, and the first version only looked
        #: for sibling combinators - so the deleted rule came straight back
        #: written as a descendant, or hung off `body:has(#rail:not([hidden]))`,
        #: and this said nothing. Two conditions instead: the selector STARTS at
        #: the rail, and it never steps sideways out of it. A descendant of the
        #: rail is the rail's own business and stays allowed.
        first = sel.replace(">", " ").split()[0] if sel.split() else ""
        if not first.startswith("#rail") or "~" in sel or "+" in sel:
            outside.append(sel)
            continue
        if "#railtab" in sel:
            for d in decls.split(';'):
                name = d.split(':')[0].strip().lower()
                if name.split('-')[0] in boxy or name in boxy:
                    moved.append('%s -> %s' % (sel, name))

    assert not outside, (
        "these rules make something outside the session column react to it being "
        "open, which is the column reaching into the conversation: %s" % outside)
    assert not moved, (
        "the toggle changes its own box when the column opens, and the spine is "
        "in the flow - so every pane beside it moves: %s" % moved)


def test_a_lead_in_is_not_drawn_and_the_answer_still_is():
    """⛔ THE SENTENCE THAT COMES WITH THE TOOL CALLS IS NOT DRAWN, and the
    one that comes instead of them is.

    Owner, reading a run whose narration was in Italian, translated here:
    `Site open. Let me see what is on the home page.` above a row that says
    `Inspected`, then `I will close the cookie banner first` above a row that
    says `Clicked`. The sentence announces what the row below it states, so
    the column spent three lines saying one thing and spaced the things worth
    reading out with the things that were not.

    The distinction needs no guessing, which is why this can be mechanical:
    `asAnswer` is true only when the run went idle still holding the text,
    which is the message the model sent with no tool calls. Every other path
    through the dispatcher is a sentence that had something after it.

    ⛔ AND THE ANSWER IS THE HALF THAT MATTERS HERE. Dropping the lead-in is
    one line, and the same line one character wrong drops the answer too - a
    run that works perfectly and ends with nothing on the page. So this runs
    the function both ways rather than checking that the branch exists.

    Known-bad: return before drawing whatever it is handed; or invert the
    test and draw only the lead-in.
    """
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if not node:
        pytest.skip("needs node to EXECUTE the transcript's narration path")

    src = CODE[CODE.index("function flush("):]
    src = src[:src.index(chr(10) + "}") + 2]
    done = subprocess.run([node, "-e", src + chr(10) + "let drawn = [];\nglobalThis.LEAD = /^(I will |I'll |Let me )/i;\nglobalThis.el = (tag, cls, t) => ({tag, cls, t, kids: [],\n                                   appendChild(k){ this.kids.push(k); }});\nglobalThis.rich = t => ({tag: 'rich', t});\nglobalThis.put = (node) => drawn.push(node);\nglobalThis.hold = null;\nconst out = {};\nhold = 'Let me close the cookie banner first.';\nflush(false); out.afterLeadIn = drawn.length; out.heldAfter = hold;\nhold = 'The cart has one item, 149,99 EUR.';\nflush(true); out.afterAnswer = drawn.length;\nout.cls = drawn.length ? drawn[0].cls : null;\nflush(false); flush(true); out.afterEmpty = drawn.length;\nprocess.stdout.write(JSON.stringify(out));"],
                          capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, done.stderr
    got = json.loads(done.stdout)

    assert got["afterLeadIn"] == 0, (
        "the sentence that came with the tool calls was drawn, which is the "
        "announcement of the row underneath it")
    assert got["heldAfter"] is None, (
        "the lead-in was dropped but left held, so the next flush draws it as "
        "though it were the answer")
    assert got["afterAnswer"] == 1, (
        "the ANSWER was not drawn: a run that worked ends with nothing on the "
        "page, which is the expensive half of getting this line wrong")
    assert got["cls"] == "answer", (
        "the answer was drawn in the lead-in's clothes: %r" % got["cls"])
    assert got["afterEmpty"] == 1, "an empty hold drew something"


def test_a_reopened_conversation_keeps_the_answer_of_every_turn():
    """⛔ THE GATE NEXT DOOR RAN `flush` BOTH WAYS AND STILL LET THIS THROUGH,
    which is the whole reason this one exists.

    Dropping the lead-in is decided by the argument the dispatcher passes, and
    `case 'you'` was passing the one that means `this had something after it`.
    It does not: a sentence still held when the PERSON speaks had nothing after
    it in its own turn, which is exactly what `busy 0` means.

    And `busy` is deliberately kept OUT of the history - replaying a spinner
    for work that finished an hour ago would be a lie - so on a reopened
    conversation that branch is the only one that can ever draw the answer of a
    turn that is not the last. Measured on a real transcript of three turns an
    hour after the change shipped: one answer drawn, two silently gone.

    So this replays a transcript through the DISPATCHER, which is where the
    argument is chosen, rather than through the function that receives it. A
    unit test of a function cannot see a caller passing the wrong thing, and
    that is not a gap in the other gate - it is a different question.

    Known-bad: hand `case 'you'` the lead-in argument again. One answer comes
    back instead of two.
    """
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if not node:
        pytest.skip("needs node to REPLAY a transcript through the dispatcher")

    def whole(start, end):
        src = CODE[CODE.index(start):]
        return src[:src.index(end) + len(end)]

    js = (whole("function flush(", chr(10) + "}") + chr(10)
          + whole("const onEvent =", chr(10) + "};") + chr(10)
          + "let drawn = [];\nglobalThis.hold = null; globalThis.busyNow = false;\nglobalThis.live = null; globalThis.timer = 0; globalThis.queued = null;\nglobalThis.LEAD = /^(I will |I'll |Let me )/i;\nglobalThis.el = (tag, cls, t) => ({tag, cls, t, kids: [],\n                                   appendChild(k){ this.kids.push(k); }});\nglobalThis.rich = t => ({tag: 'rich', t});\nglobalThis.put = n => drawn.push(n);\nglobalThis.$ = () => ({textContent: '', hidden: false});\nfor (const name of ['wipe','waiting','waited','drawChats','paint',\n                    'settleOnce','newTurn','step','land','orphan',\n                    'setQueued','send','clearInterval'])\n  globalThis[name] = () => {};\n\nconst feed = m => onEvent({data: JSON.stringify(m)});\nconst history = [\n  {kind:'you',    text:'first instruction',  replay:true},\n  {kind:'said',   text:'Let me open the page.', replay:true},\n  {kind:'tool',   text:'browser_navigate a', replay:true},\n  {kind:'result', text:'ok',                 replay:true},\n  {kind:'said',   text:'THE FIRST ANSWER.',  replay:true},\n  {kind:'you',    text:'second instruction', replay:true},\n  {kind:'tool',   text:'browser_navigate b', replay:true},\n  {kind:'result', text:'ok',                 replay:true},\n  {kind:'said',   text:'THE SECOND ANSWER.', replay:true},\n];\nhistory.forEach(feed);\n/* what the server sends after the replay, once it is idle */\nfeed({kind:'busy', text:'0'});\nconst answers = drawn.filter(d => d.cls === 'answer')\n                     .map(d => (d.kids[0] && d.kids[0].t) || '');\nprocess.stdout.write(JSON.stringify({answers, total: drawn.length}));")
    done = subprocess.run([node, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, done.stderr
    got = json.loads(done.stdout)

    assert got["answers"] == ["THE FIRST ANSWER.", "THE SECOND ANSWER."], (
        "a reopened conversation lost the answer of a turn that is not the "
        "last: %r" % (got["answers"],))
    #: and the lead-in is still dropped, which is the thing this must not undo.
    assert not any("open the page" in a for a in got["answers"]), (
        "the sentence that came with the tool calls came back as an answer")


def test_the_session_drawer_never_covers_the_input():
    """⛔ THE DRAWER COVERED HALF THE ONLY INPUT ON THE PAGE, and the gate
    written for the drawer could not see it.

    That gate asserts that nothing outside the rail reacts to the rail being
    open, which is true and was the defect of the day before. It is a scan over
    selectors, so it knows nothing about where a box ends up: the rail ran the
    full height of the window and lay over the composer. Measured 2026-09-11 in
    a real browser: 256px of the 530px input, and `elementFromPoint` on the
    corner of the textarea answered `chats`. Half of the only way to talk to
    the agent was dead, with nothing saying so.

    The rule that used to prevent it padded the transcript out of the way, and
    that rewrapped every paragraph as the panel appeared - which is what it was
    removed for. So the coupling runs the other way now: the CHAT still knows
    nothing, and the PANEL knows where the input begins.

    Measured and not declared, because the textarea grows with what is typed:
    a constant would be right until somebody wrote a third line.

    Known-bad: anchor the rail to the bottom of the window again, or publish a
    composer's HEIGHT instead of the distance to it: the same number only
    while the composer sits at the bottom of the window, and below 720px the
    panes stack and it does not.
    """
    import json
    import shutil
    import subprocess

    import pytest

    #: the panel has to stop at the variable, not at the window.
    style = CODE[CODE.index("#rail {"):]
    style = style[:style.index("}") + 1]
    assert "bottom:var(--rail-bottom" in style.replace(" ", ""), (
        "the drawer is anchored to the bottom of the window again, so it lies "
        "over the composer: %r" % " ".join(style.split()))

    node = shutil.which("node")
    if not node:
        pytest.skip("needs node to EXECUTE the publisher")

    src = CODE[CODE.index("function publishRailFloor("):]
    src = src[:src.index(chr(10) + "}") + 2]
    done = subprocess.run([node, "-e", src + chr(10) + "let set = {};\nglobalThis.window = {innerHeight: 900};\nglobalThis.innerHeight = 900;\nglobalThis.addEventListener = () => {};\nglobalThis.$ = id => id === 'f'\n  ? {getBoundingClientRect: () => ({top: 783.2, height: 83.4})}\n  : null;\nglobalThis.document = {documentElement: {style: {\n  setProperty(k, v){ set[k] = v; }}}};\nglobalThis.ResizeObserver = undefined;\npublishRailFloor();\nprocess.stdout.write(JSON.stringify({set}));"],
                          capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, done.stderr
    got = json.loads(done.stdout)["set"]

    assert got.get("--rail-bottom") == "117px", (
        "the floor the panel stops at is not the distance to the composer, "
        "so it is right until the panes stack and the input moves: %r" % got)
