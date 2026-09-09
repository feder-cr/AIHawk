"""What the interface must never do to the person watching it.

Every rule here comes from a defect that was on the screen when it was written,
found by an audit run against the live page rather than against an idea of it.
They have one shape in common: a stated rule that stopped being enforced one step
past where it was written down.
"""
from __future__ import annotations

import re

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
    assert "box.inert = !anything" in CODE, (
        "the disarmed controls are only dimmed, so they still answer the keyboard")


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
    """Asking a declared-but-stopped browser for its tabs STARTS it - the server
    resolves the id and the registry wakes the engine. Clicking a stopped
    browser's chip therefore spent 800 MB and seven seconds nobody asked for,
    and then kept asking every two seconds because the pin never cleared. Four
    places in this file already knew the rule; this was the fifth.

    Known-bad: drop the guard from `paintWhere`.
    """
    where = CODE[CODE.index("async function paintWhere"):]
    where = where[:where.index("\n}")]
    assert "b.running" in where, (
        "the address bar asks about a browser without checking it is running, "
        "which starts it")


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


def test_a_step_names_the_browser_when_the_call_named_one():
    """A session holds up to eight browsers, and 35 rows of a live transcript
    read exactly `Read body` or `Inspected`: the one fact that distinguishes
    this product from a single-browser agent was the fact the log dropped. It is
    named when the CALL names it - inventing a default would say more than the
    call said.

    Known-bad: go back to discarding `browser_id`.
    """
    from aihawk.actions_help import summarise

    assert summarise("browser_read_text", {"selector": "body",
                                           "browser_id": "b-tech"}).endswith("b-tech")
    assert "browser_id=" not in summarise("browser_open", {"browser_id": "walmart-jobs"}), (
        "opening a browser still prints the name of an argument at the reader")
    assert summarise("browser_open", {"browser_id": "walmart-jobs"}) == "walmart-jobs"
    # And it stays quiet when the call was quiet.
    assert summarise("browser_read_text", {"selector": "body"}) == "body"


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


def test_every_question_about_this_conversation_goes_through_one_door():
    """⛔ AND THAT DOOR IS WHERE THE PAGE LEARNS THE CONVERSATION IS GONE. Six
    fetches carried `?s=`, and while they each asked on their own, a page left
    open on a session somebody deleted went on asking forever - and every one of
    those questions declared the session again on the server, so the delete came
    back as an empty row for as long as that tab stayed open.

    Known-bad: put `fetch(at(...))` back into any of the six callers, or take
    the 410 out of `door`.
    """
    doors = re.findall(r"fetch\(at\(", CODE)
    assert len(doors) == 1, (
        "%d places build a session-scoped request; one of them is `door` and "
        "the rest will not notice a conversation that no longer exists"
        % len(doors))
    body = CODE[CODE.index("async function door(path, init)"):]
    body = body[:body.index("\n}")]
    assert "410" in body and "vanish()" in body, (
        "the door does not read the one answer that will never stop being true")


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

