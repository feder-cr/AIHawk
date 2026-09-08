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
from aihawk.web import DEFAULT_CHAT_ID, UNNAMED, ChatService, Sessions, build_app

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

    client.post("/chat/send?s=uno", json={"text": "primo"})
    client.post("/chat/send?s=due", json={"text": "secondo"})
    import asyncio
    await asyncio.sleep(0.05)

    assert [e["text"] for e in sessions.get("uno").history if e["kind"] == "you"] \
        == ["primo"]
    assert [e["text"] for e in sessions.get("due").history if e["kind"] == "you"] \
        == ["secondo"]


async def test_the_live_pane_of_a_conversation_that_has_done_nothing_asks_for_nothing():
    """⛔ OR OPENING A CHAT LAUNCHES A BROWSER. Over MCP there is no way to ask
    "is a browser running" without starting one, so the pane may only ask once
    this conversation has issued an instruction. If that question were asked of
    the shared connection, a second chat opened beside a working one would start
    an engine - 800 MB and seven seconds - to draw a picture of nothing.

    Known-bad: have the frame route read `link.touched` instead of the
    conversation's own.
    """
    link, sessions = _sessions()
    client = await _client(sessions, link)

    await sessions.get("vecchia").send("do something")
    calls_before = len(link.calls)

    assert client.get("/live/frame?s=nuova").status_code == 204
    assert len(link.calls) == calls_before, (
        "drawing a pane for an unused conversation reached the server: %r"
        % link.calls[calls_before:])


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
