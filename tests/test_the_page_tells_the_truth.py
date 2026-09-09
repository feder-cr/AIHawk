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
    assert "await fetch" in send, "the send does not wait for an answer"
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
    assert "inert = !show.length" in CODE, (
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
