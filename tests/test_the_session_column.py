"""Several conversations, each with its own transcript and its own browsers.

⛔ WHAT MAKES THIS REAL RATHER THAN DECORATION is that a conversation drives its
OWN browsers. The server has addressed browsers per session since 0.15.0, and a
tool call that names no session lands on the default one - so a column that only
swapped transcripts would have shown two chats quietly sharing one browser, with
the second finding the first one's tabs, cookies and identity. The addressing
itself is pinned in `test_a_session_reaches_only_its_own_browsers.py`; this file
is about the layer above, where conversations are made, listed, saved, reopened
and deleted.

No browser, no model and no server: the link records what it was asked, the
brain answers without thinking, and `AIHAWK_HOME` points at a temporary
directory for every test (see `tests/conftest.py`), so what a conversation did
is observable as the files and the calls it left behind.
"""
from __future__ import annotations

import json

import pytest

from aihawk.mcp import store
from aihawk.web import (PAGE, DEFAULT_CHAT_ID, UNNAMED, ChatService, Sessions,
                        build_app)

pytestmark = pytest.mark.asyncio


class _Tool:
    def __init__(self, name, props):
        self.name = name
        self.inputSchema = {"type": "object", "properties": {p: {} for p in props}}


class FakeLink:
    """Shaped like `Link`, recording every call."""

    def __init__(self):
        self.touched = False
        self.tools = [_Tool("browser_navigate", ["url", "session_id", "browser_id"]),
                      _Tool("session_forget", ["session_id"]),
                      _Tool("session_list_pages", ["session_id", "browser_id"])]
        self.calls = []

    async def call(self, name, arguments=None):
        self.touched = True
        self.calls.append((name, dict(arguments or {})))
        return None

    async def call_text(self, name, arguments=None):
        await self.call(name, arguments)
        return "[]"


class Quiet:
    """A brain with a transcript, so saving and restoring have something to do."""

    def __init__(self):
        self.messages = [{"role": "system", "content": "you are a browser"}]
        self.usage = {"prompt": 0, "completion": 0, "calls": 0, "last_prompt": 0}

    def remember(self, messages, usage=None):
        self.messages = list(messages)
        if usage:
            self.usage.update(usage)

    async def handle(self, text, link, say):
        self.messages.append({"role": "user", "content": text})
        # It TOUCHES the browser, because a brain that never calls a tool does
        # not exercise the paths that depend on a browser having been reached -
        # and one of them, the live pane's, had a mutation survive on exactly
        # that: the shared connection stayed untouched, so reading it answered
        # the same as reading the conversation's own.
        await link.call("browser_navigate", {"url": "http://127.0.0.1/"})
        await say("said", "done: " + text)


def _sessions():
    link = FakeLink()
    return link, Sessions(link, Quiet, model_label="a model")


# --- making and finding them ------------------------------------------------

async def test_a_page_that_names_nothing_is_in_the_conversation_it_always_was():
    """⛔ THE PROMISE OF THE WHOLE CHANGE, and it is the same one slice 1 made
    about browsers. Every page and every client written before sessions existed
    names none, and must land where it always did - one conversation, driving
    the default session's browser.

    Known-bad: give the default conversation an invented id such as `main`. The
    chat then talks to session `main` while every tool default is `default`, so
    the interface and any other client stop sharing a browser.
    """
    _, sessions = _sessions()

    assert sessions.get() is sessions.get(None) is sessions.get(DEFAULT_CHAT_ID)
    assert sessions.get().session_id == DEFAULT_CHAT_ID
    assert DEFAULT_CHAT_ID == "default", (
        "the interface's default conversation and the server's default session "
        "must be the same id, or they are two sessions wearing one name")


async def test_a_new_conversation_is_its_own_and_does_not_touch_the_others():
    """Known-bad: return the same service from `new`. Two rows appear in the
    column and both show one transcript.
    """
    _, sessions = _sessions()
    first, second = sessions.new(), sessions.new()

    assert first.session_id != second.session_id
    assert first is not second
    assert first.name == second.name == UNNAMED

    await first.send("go to example.com")

    assert second.history == [], "a new conversation was given somebody else's"
    assert first.name.startswith("go to example.com"), (
        "a conversation is named by what it was first asked: %r" % first.name)


async def test_the_column_shows_conversations_that_have_not_been_saved_yet():
    """A session opened a moment ago has nothing on disk. Leaving it out makes
    the column disagree with the page drawn beside it.

    Known-bad: build `listing` from `store.known_chats()` alone.
    """
    _, sessions = _sessions()
    fresh = sessions.new()

    ids = [r["id"] for r in sessions.listing()]
    assert fresh.session_id in ids, ids


# --- surviving the process --------------------------------------------------

async def test_a_conversation_comes_back_with_both_of_its_transcripts():
    """⛔ BOTH, AND SAVING ONLY ONE WOULD BE A LIE THE OTHER HALF CANNOT KEEP.
    The page draws `history`; the model holds `messages`. Restoring only the
    first gives somebody a conversation they can read and cannot continue, under
    a follow-up box that still looks like "and now sort them by price" will work.

    Known-bad, two: drop `messages` from `save_chat`, and drop the `remember`
    call from `ChatService.restore`. The first assertion survives both.
    """
    _, sessions = _sessions()
    mine = sessions.get("lavoro")
    await mine.send("open the dashboard")

    # The process ends. Nothing in memory survives; the disk does.
    _, again = _sessions()
    back = again.get("lavoro")

    assert [e["text"] for e in back.history if e["kind"] == "you"] == \
        ["open the dashboard"]
    assert any(m.get("content") == "open the dashboard"
               for m in back._brain.messages), (
        "the page can read the conversation and the model cannot continue it")
    assert back.name.startswith("open the dashboard")


async def test_a_conversation_is_written_down_when_a_turn_ends_not_on_a_timer():
    """A server that is killed never reaches a timer's next tick, and killing it
    is how a person stops it.

    Known-bad: move `save()` out of the `finally` in `send`.
    """
    _, sessions = _sessions()
    mine = sessions.get("lavoro")
    assert store.load_chat("lavoro") is None

    await mine.send("do the thing")

    saved = store.load_chat("lavoro")
    assert saved is not None and saved["name"].startswith("do the thing")


async def test_a_run_that_failed_is_saved_too():
    """What was asked and how far it got is exactly what somebody reopens a
    session to look at, and a turn that failed is the one they reopen soonest.

    Known-bad: save only when the turn succeeded.
    """
    class Boom(Quiet):
        async def handle(self, text, link, say):
            raise RuntimeError("the model refused")

    link = FakeLink()
    sessions = Sessions(link, Boom)
    await sessions.get("lavoro").send("do the impossible")

    saved = store.load_chat("lavoro")
    assert saved is not None
    assert any("the model refused" in e["text"] for e in saved["history"])


async def test_a_conversation_nobody_saved_reads_back_as_empty_and_not_as_an_error():
    """Known-bad: let `restore` raise when there is no file. The first time
    anybody opens a new session the interface answers 500.
    """
    _, sessions = _sessions()
    assert sessions.get("mai-vista").history == []


# --- deleting one -----------------------------------------------------------

async def test_deleting_a_conversation_closes_the_browsers_that_belonged_to_it():
    """⛔ ONE SESSION, BOTH HALVES. Erasing only the chat file would leave up to
    eight engines running with nothing left that names them: 6.5 GB, measured,
    unreachable except through the task manager.

    Known-bad: drop the `session_forget` call. Every other assertion here still
    passes and the leak is invisible from the page.
    """
    link, sessions = _sessions()
    mine = sessions.get("lavoro")
    await mine.send("log in somewhere")

    assert await sessions.forget("lavoro") is True

    assert ("session_forget", {"session_id": "lavoro"}) in link.calls, (
        "the conversation is gone and its browsers are still running: %r"
        % link.calls)
    assert store.load_chat("lavoro") is None
    assert "lavoro" not in [r["id"] for r in sessions.listing()]


async def test_a_deleted_conversation_stays_deleted_while_a_page_is_still_open_on_it():
    """⛔ THE DELETE WORKED AND CAME BACK ON ITS OWN. Every route resolved the id
    with `get`, which BUILDS what it does not find, so one poll from a tab left
    open on the deleted session declared it again - `/live/browsers` every three
    seconds, `/live/frame` up to twenty-five times a second. Measured against
    the running server: `forgotten:true`, the browsers closed, the file erased,
    and the row back in the column a moment later, empty and unnamed, for as
    long as that tab stayed open. Every visible signal said the delete had
    failed.

    Known-bad: have `named` fall back to `sessions.get` when `knows` says no.
    """
    link, sessions = _sessions()
    client = await _client(sessions, link)
    await sessions.get("lavoro").send("log in somewhere")

    assert await sessions.forget("lavoro") is True

    # The three questions a page left open on it goes on asking.
    for path in ("/live/browsers?s=lavoro", "/live/tabs?s=lavoro",
                 "/live/frame?s=lavoro"):
        assert client.get(path).status_code == 410, (
            "%s answered a conversation that does not exist" % path)
    assert client.post("/chat/send?s=lavoro", json={"text": "ciao"}).status_code == 410
    assert client.post("/sessions/rename",
                       json={"id": "lavoro", "name": "x"}).status_code == 410, (
        "the rename carries the id in the BODY, so it is the one route that "
        "would go on resurrecting sessions after the eight beside it stopped")

    assert "lavoro" not in [r["id"] for r in sessions.listing()], (
        "asking about a deleted conversation brought it back")
    assert store.load_chat("lavoro") is None


async def test_deleting_one_that_is_already_gone_is_not_reported_as_a_refusal():
    """⛔ `forgotten:false` HAS ONE MEANING AND IT IS "IT IS STILL RUNNING". It
    also used to mean "there was nothing there", and the page reads it to say
    "that session is still working, so it was not deleted" - which for a session
    somebody else deleted a moment ago is the wrong sentence in both halves. The
    column does not poll, so a panel left open in another tab shows that row for
    as long as it stays open, and its cross is what the person clicks.

    Known-bad: answer `store.erase_chat(...) or service is not None` again.
    """
    link, sessions = _sessions()
    await sessions.get("lavoro").send("log in somewhere")

    assert await sessions.forget("lavoro") is True
    assert await sessions.forget("lavoro") is True, (
        "deleting one that is already gone was reported as a refusal, and the "
        "page has exactly one sentence for a refusal")
    assert await sessions.forget("mai-esistita") is True


async def test_a_session_known_only_by_its_browsers_can_still_be_opened():
    """⛔ A SESSION IS A CONVERSATION AND ITS BROWSERS, AND EITHER HALF CAN BE THE
    ONLY ONE ON DISK. An agent client that opens a browser in session `work` and
    never touches this interface writes the browsers file and no transcript.
    Refusing what has no transcript would have answered 410 to a session that
    plainly exists - the same defect one step further along.

    Known-bad: drop the `store.load(at)` half of `Sessions.knows`.
    """
    link, sessions = _sessions()
    client = await _client(sessions, link)
    store.save("work", {"docs": {"running": False}}, focus="docs")

    assert sessions.knows("work") is True
    assert client.get("/live/browsers?s=work").status_code == 200


async def test_deleting_a_conversation_that_is_mid_run_is_refused():
    """The same reason clearing one is: throwing away a transcript something is
    still writing into is a surprise nobody can undo.

    Known-bad: delete regardless of `busy`.
    """
    import asyncio

    class Hanging(Quiet):
        async def handle(self, text, link, say):
            await asyncio.sleep(3600)

    link = FakeLink()
    sessions = Sessions(link, Hanging)
    mine = sessions.get("lavoro")
    mine.start("something slow")
    await asyncio.sleep(0.05)

    assert await sessions.forget("lavoro") is False
    assert mine.stop()


# --- the routes the column calls --------------------------------------------

async def _client(sessions, link):
    """The app over the SAME connection the conversations use.

    ⛔ MEASURED, BY GETTING IT WRONG. This handed `build_app` a second, untouched
    `FakeLink`, so the mutation that makes the live pane read the shared
    connection instead of the conversation's own SURVIVED: it read a link
    nothing had ever called, which answers exactly like a conversation that has
    done nothing. The gate was not blind and the mutation was not wrong - the
    test was exercising a path it did not think it was on, which is the third
    possibility and the one that looks like the other two.
    """
    from starlette.testclient import TestClient
    return TestClient(build_app(link, sessions))


async def test_the_routes_act_on_the_conversation_the_page_names():
    """⛔ EVERY ROUTE, THE LIVE ONES INCLUDED. A route that read the id and one
    that did not would act on two conversations while the page showed one, and
    the way that shows is the picture on the right belonging to another
    session's browser.

    Known-bad: leave `/chat/send` reading a fixed service.
    """
    link, sessions = _sessions()
    client = await _client(sessions, link)

    sessions.get("uno"), sessions.get("due")  # both opened, as `/sessions/new` would
    client.post("/chat/send?s=uno", json={"text": "primo"})
    client.post("/chat/send?s=due", json={"text": "secondo"})
    import asyncio
    await asyncio.sleep(0.05)

    assert [e["text"] for e in sessions.get("uno").history if e["kind"] == "you"] \
        == ["primo"]
    assert [e["text"] for e in sessions.get("due").history if e["kind"] == "you"] \
        == ["secondo"]


async def test_the_live_pane_of_a_conversation_that_has_done_nothing_starts_nothing():
    """⛔ OR OPENING A CHAT LAUNCHES A BROWSER. A second chat opened beside a
    working one would start an engine - 800 MB and seven seconds - to draw a
    picture of nothing, and the person who opened it asked for a conversation.

    What holds it is that `browser_watch` refuses a browser that is not
    running instead of starting one, which is gated where it can be proven -
    `tests/mcp_server/test_a_look_starts_nothing.py`, against a real registry
    that can be asked how many sessions it built. Here the link is a double
    with no registry behind it, so the only honest claim left is the one below:
    the pane draws idle and asks for exactly the one thing, so nothing else can
    be reaching for a browser on the way.

    Known-bad: have the pane fall back to a second question when the first
    answers nothing. That is the shape the removed guard had, and it is how
    both of these came to cost an engine.
    """
    link, sessions = _sessions()
    client = await _client(sessions, link)

    await sessions.get("vecchia").send("do something")
    sessions.get("nuova")  # opened beside it, and told nothing
    before = len(link.calls)

    assert client.get("/live/frame?s=nuova").status_code == 204
    after = [n for n, _ in link.calls[before:]]
    assert after == ["browser_watch"], (
        "drawing a pane for an unused conversation asked for more than the "
        "picture it draws: %r" % after)


async def test_the_column_can_be_listed_renamed_and_emptied_over_http():
    """The three things the column does, through the routes it actually calls.

    Known-bad: have `/sessions/rename` answer ok without writing anything. The
    name is right until the page is reloaded.
    """
    link, sessions = _sessions()
    client = await _client(sessions, link)

    made = client.post("/sessions/new").json()
    assert made["id"] and made["name"] == UNNAMED

    client.post("/sessions/rename", json={"id": made["id"], "name": "  la mia  "})
    assert sessions.get(made["id"]).name == "la mia"
    assert store.load_chat(made["id"])["name"] == "la mia", (
        "the new name lives only in memory, so a reload loses it")

    rows = client.get("/sessions").json()
    assert rows["default"] == DEFAULT_CHAT_ID
    assert made["id"] in [r["id"] for r in rows["sessions"]]

    client.post("/sessions/forget", json={"id": made["id"]})
    assert made["id"] not in [r["id"] for r in client.get("/sessions").json()["sessions"]]


async def test_forgetting_without_an_id_refuses_rather_than_deleting_the_default():
    """Known-bad: default the id to the current conversation. A page with a bug
    in it then deletes the session somebody is sitting in.
    """
    link, sessions = _sessions()
    client = await _client(sessions, link)
    sessions.get()  # the default exists

    assert client.post("/sessions/forget", json={}).status_code == 400


# --- the page ---------------------------------------------------------------

@pytest.mark.filterwarnings("ignore")
async def test_every_request_the_page_makes_carries_the_conversation():
    """⛔ READ OUT OF THE PAGE, because this is the failure with no symptom: a
    fetch that forgets the id acts on the DEFAULT conversation while the page
    shows another, and the picture on the right is then somebody else's browser
    with nothing red anywhere.

    Known-bad: change any one `at('/live/tabs')` back to `'/live/tabs'`.
    """
    import re

    from aihawk.web import PAGE

    script = PAGE[PAGE.index("<script"):]
    # Every fetch of a route that reads `?s=` must go through `at()`. The three
    # session routes are deliberately NOT addressed: they are about the set of
    # conversations, not about one, and they carry their id in the body.
    ABOUT_THE_SET = ("/sessions", "/sessions/new", "/sessions/rename",
                     "/sessions/forget")
    bare = [p for p in re.findall(r"""fetch\(\s*['"]([^'"]+)""", script)
            if p.split("?")[0] not in ABOUT_THE_SET]
    assert not bare, (
        "these requests do not carry the conversation, so they act on the "
        "default one whatever the page is showing: %s" % bare)

    assert "new EventSource(at('/chat/events'))" in script, (
        "the event stream is not addressed, so every page listens to the "
        "default conversation")


@pytest.mark.filterwarnings("ignore")
async def test_a_queued_message_is_not_lost_when_the_page_goes_away():
    """⛔ TYPED TEXT MUST NOT VANISH SILENTLY, and this was the one thing in the
    interface that did. The transcript is saved, the answer is saved, and the
    instruction somebody wrote while the agent was working was held in a
    JavaScript variable: a refresh, a crash or a closed laptop and the sentence
    was gone with nothing said about it.

    It is kept per conversation - switching sessions must not carry a pending
    sentence into another chat - and it comes back into the COMPOSER rather than
    into the queue, because the run it was waiting behind is over by then.

    Read out of the page, and on the SHAPE rather than on the wording: what has
    to stay true is that one function writes it and nothing else does, which is
    exactly what went wrong when it was assigned in five places and saved in
    none.

    Known-bad: assign `queued = ...` anywhere outside `setQueued`.
    """
    import re

    from aihawk.web import PAGE

    script = PAGE[PAGE.index("<script"):]
    code = re.sub(r"/\*.*?\*/", "", script, flags=re.S)

    assert "function setQueued(" in code, "the queue has no single writer"
    # ⛔ THE WHOLE LINE, NOT THE CALL. Asserting that `localStorage.setItem`
    # appears passed a mutation that turned its condition into `if(false)`: the
    # call was still there and wrote nothing. A source scan that cannot tell a
    # reachable write from an unreachable one is not checking the write. Exact
    # enough to break on reformatting, which is the trade being made knowingly:
    # a page cannot be executed here, so the text is the only evidence.
    assert "if(queued) localStorage.setItem(qkey(), queued);" in code, (
        "the queued message is not written down where it can be read back, so "
        "a reload loses it")
    assert "localStorage.getItem(qkey())" in code, (
        "nothing reads the queued message back, so saving it changes nothing")
    assert "'aihawk.queued.' + here" in code, (
        "the queue is not kept per conversation, so switching sessions carries "
        "somebody's pending sentence into another chat")

    # One writer. The declaration is the only other place the name may be
    # assigned, and it is on the `let` line.
    writes = [line.strip() for line in code.split(chr(10))
              if re.search(r"(?<![.\w])queued\s*=(?!=)", line)]
    stray = [w for w in writes if not w.startswith("let ") and "queued = text" not in w]
    assert not stray, (
        "these assign the queue outside its single writer, so they do not save "
        "it: %s" % stray)


def test_the_sessions_control_says_the_same_word_it_is_called():
    """⛔ A NAME AND A LABEL MAY NEVER DISAGREE, and which of the two is the
    defect depends on what is drawn.

    First the control was three lines with an `aria-label` reading "Show
    sessions", which was the only name it had. Then it became a bar with the
    word Sessions written on it, and the label became the defect: a screen
    reader announced a word that was not on the button and a voice user saying
    "Sessions" found nothing to click. WCAG 2.5.3, Label in Name.

    On 2026-09-10 the word came off the wall - it was the only thing on the page
    a person had to tilt their head for - and an `aria-label` stopped being a
    defect the moment there was no visible word left to contradict. So this gate
    asks the question that survives both shapes: is there a name, and does
    everything that says a name say the SAME one.

    Known-bad, four: drop the label from an icon-only button; drop the tip so
    the word is never on screen; make the two say different words; put the
    `setAttribute('aria-label', ...)` line back in `showRail`, where it wrote a
    changing name over a fixed one on every open and close.
    """
    import re

    button = re.search(r"<button id=\"railtab\"[^>]*>(.*?)</button>", PAGE, re.S)
    assert button, "the sessions control is gone"
    whole, inside = button.group(0), button.group(1)
    visible = re.sub(r"<[^>]+>", "", inside).strip()
    label = re.search(r'aria-label="([^"]*)"', whole)
    tip = re.search(r'data-tip="([^"]*)"', whole)

    if visible:
        assert not label, (
            "the control has the word %r on it AND an aria-label, and the label "
            "is what a screen reader reads instead of the word" % visible)
    else:
        assert label, (
            "the control draws an icon and carries no name at all, so it is "
            "announced as `button` and cannot be reached by voice")
        assert tip, (
            "the name exists only for a screen reader: nothing puts the word on "
            "screen for a pointer or the keyboard")
        assert label.group(1) == tip.group(1), (
            "the control is called %r and shows %r"
            % (label.group(1), tip.group(1)))
        assert "Sessions" in label.group(1), (
            "the name is not the word the column is called: %r" % label.group(1))

    assert "aria-expanded" in whole, "nothing says whether the column is open"

    script = PAGE[PAGE.index("<script"):]
    code = re.sub(r"/\*.*?\*/", "", script, flags=re.S)
    # Every place the script names this control, and not the 400 characters
    # after the first one: the first `$('railtab')` in the file is not the one
    # in `showRail`, so that window read the wrong code and the known-bad
    # walked straight through it.
    sets = re.findall(r"\$\('railtab'\)\s*\.setAttribute\(\s*'aria-label'", code)
    assert not sets, (
        "the script writes an aria-label on every open and close, so the name "
        "changes under the word that is meant to be fixed")


def test_the_spine_is_part_of_the_frame_and_is_the_only_way_in():
    """The control is the leftmost thing on the screen and the first thing in
    the document, ahead of the conversation pane: it belongs to the room rather
    than to the panel beside it, which is what a drawing on 2026-09-09 asked
    for after a bar in the header turned out not to be it.

    And there is ONE of them. A second control that opens the same column is a
    second thing to keep in step with the first, and the header carried exactly
    that for half an hour.

    Known-bad, three: move the button after `<div id="left"`; add a second
    control with `aria-controls="rail"`; put a word back on the wall instead of
    a drawn icon.
    """
    import re

    spine = PAGE.index('id="railtab"')
    assert spine < PAGE.index('id="left"'), (
        "the control sits inside or after the conversation pane, so it reads as "
        "one of that pane's buttons rather than as part of the frame")
    opens = re.findall(r'aria-controls="rail"', PAGE)
    assert len(opens) == 1, (
        "%d controls open the sessions column; two of them can disagree about "
        "whether it is open" % len(opens))
    # ⛔ IT DRAWS, IT DOES NOT SET TYPE SIDEWAYS. The word used to run bottom
    # to top down the strip, and that rotation was the whole reason it went: the
    # only thing on this page a reader had to tilt their head for. What replaces
    # it has to be a drawn mark, not the same word turned some other way.
    style = PAGE[PAGE.index("#railtab{"):PAGE.index("/* Open: the rail lifts")]
    assert "writing-mode" not in style, (
        "the rail sets type sideways again")
    assert "<svg" in PAGE[PAGE.index('id="railtab"'):PAGE.index("</button>",
                                                                PAGE.index('id="railtab"'))], (
        "the rail carries no drawn mark, so there is nothing on it to press")

    # ⛔ AND IT IS NEVER HIDDEN. The panel and its only opener used to be
    # dropped by the same media query, and `#newchat` lives inside the panel: a
    # window snapped to half a 1366-wide laptop lost every session control at
    # once, and the only route left was hand-editing `?s=` in the address bar.
    # The panel is an overlay, so folding it costs nothing at any width.
    #
    # Known-bad: hide `#railtab` or `#rail` at any breakpoint.
    hidden = re.findall(r"#rail(?:tab)?\{[^}]*display:\s*none", PAGE)
    assert not hidden, (
        "%d rule(s) hide the sessions column or the only way into it: %s"
        % (len(hidden), hidden))
