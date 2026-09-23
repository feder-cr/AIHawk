"""The lifecycle of a browser, which since 0.53.0 is short enough to test in
one file: `browser_open` opens, every other tool needs an open browser and says
so when there is none, a browser that died is said and not brought back, and
what survives a process is who `main` was.

No browser starts here. The piece of work gets a factory that launches nothing
and records what it was handed, and `actions.navigate` is a stub that writes
the url down - so what is under test is the decisions, never the engine.
"""
from __future__ import annotations

import pytest
from invisible_playwright.async_api import TargetClosedError

from invisible_playwright_mcp.mcp import GONE, NOT_OPEN, actions, server, store
from invisible_playwright_mcp.mcp.work import REMEMBERED, Work


class _Recording:
    """A session that launches nothing and remembers what it was built with."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.closed = False
        self.alive = True
        #: ⛔ THE ENGINE IS GONE AND THE OBJECT DOES NOT KNOW, which is what a
        #: killed Firefox really looks like: measured against firefox-30 in
        #: `test_a_gone_browser_is_said.py`, `is_connected()` answers true for
        #: at least six seconds and `page.url` answers from cache. So this
        #: stays `usable` and only the ROUND TRIP raises, exactly as there.
        self.dead = False
        self.urls: list = []

    async def start(self):
        pass

    async def close(self):
        self.closed = True

    def is_usable(self):
        return self.alive and not self.closed

    def pages(self):
        return list(self.urls)

    async def new_page(self):
        self.urls.append("about:blank")
        return self.urls[-1]

    def page(self):
        if not self.urls:
            raise RuntimeError("this browser has no page open; browser_navigate opens one")
        return self.urls[-1]

    def where_pages_are(self):
        return list(self.urls)

    async def describe_pages(self):
        if self.dead:
            raise TargetClosedError("Target page, context or browser has been closed")
        return [{"url": u, "title": "", "active": i == len(self.urls) - 1}
                for i, u in enumerate(self.urls)]

    async def watch_frame(self, timeout=3.0):
        return b"\xff\xd8\xff frame"


class _NeverStarts(_Recording):
    async def start(self):
        raise RuntimeError("the proxy refused the connection")


@pytest.fixture
def work(monkeypatch):
    """The server's piece of work, with a factory that launches nothing and an
    environment that decides nothing, so the planner draws a fresh person."""
    for name in ("STEALTHFOX_SEED", "STEALTHFOX_PROXY", "STEALTHFOX_PROFILE_DIR",
                 "STEALTHFOX_HEADLESS", "STEALTHFOX_BINARY", "STEALTHFOX_NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
    w = Work("default", factory=_Recording)
    monkeypatch.setattr(server, "work", w)

    async def _went(session, url, wait_until="domcontentloaded"):
        if not session.urls:
            session.urls.append(url)
        else:
            session.urls[-1] = url
        return "navigated to %s (HTTP 200)" % url

    monkeypatch.setattr(actions, "navigate", _went)
    return w


def _session(work, role="main") -> _Recording:
    return work._open[role]


# --- open first -----------------------------------------------------------------

#: Every tool that touches a browser, with the least it accepts. `browser_list`
#: is not here: it asks about the set, and answers about an empty one.
EVERY_TOOL = [
    ("browser_navigate", {"url": "https://example.com/"}),
    ("browser_read_text", {}),
    ("browser_snapshot", {}),
    ("browser_read_html", {}),
    ("browser_take_screenshot", {}),
    ("browser_watch", {}),
    ("browser_click", {"selector": "#go"}),
    ("browser_click_at", {"x": 1.0, "y": 1.0}),
    ("browser_type", {"selector": "#q", "text": "hi"}),
    ("browser_select_option", {"selector": "#s", "value": "a"}),
    ("browser_press_key", {"key": "Enter"}),
    ("browser_evaluate", {"expression": "1"}),
    ("browser_status", {}),
]


@pytest.mark.parametrize("name,args", EVERY_TOOL, ids=[n for n, _ in EVERY_TOOL])
async def test_before_browser_open_every_tool_says_so_and_names_the_call(work, name, args):
    """⛔ THE WHOLE SENTENCE, NOT A SUBSTRING: a tool can say two things when
    the browser is missing - not open, or gone - and an assertion that matched
    the role name would pass on either. And it STARTS NOTHING: the sentence is
    the answer, the factory is never called.

    Known-bad: have any tool call `work.open` when its browser is missing.
    """
    with pytest.raises(RuntimeError) as told:
        await getattr(server, name)(**args)

    assert str(told.value) == NOT_OPEN % "main", (
        "%s answered something other than the one sentence: %s" % (name, told.value))
    assert work.roles() == [], "%s started a browser" % name

    with pytest.raises(RuntimeError) as told:
        await getattr(server, name)(browser="support", **args)
    assert str(told.value) == NOT_OPEN % "support"


async def test_browser_open_then_the_tool_works(work):
    said = await server.browser_open(seed=4242)

    assert said.startswith("the main browser is open. identity: seed 4242")
    assert work.roles() == ["main"]
    assert "navigated to https://example.com/" in await server.browser_navigate("https://example.com/")
    assert _session(work).urls == ["https://example.com/"]


async def test_a_browser_that_died_is_said_and_forgotten_not_brought_back(work):
    """⛔ NO REBUILD. Until 0.53.0 an action on a dead browser closed it and
    started another as the same person, silently at first and then with a
    sentence prefixed to the answer. Now the model is told, told what to call,
    and the dead one is forgotten so the next open starts clean.

    Known-bad: start a replacement inside `session()` when `is_alive` is false.
    """
    await server.browser_open(seed=4242)
    first = _session(work)
    first.alive = False

    with pytest.raises(RuntimeError) as told:
        await server.browser_navigate("https://example.com/")

    assert str(told.value) == GONE % "main"
    assert work.roles() == [], "the dead browser is still held"

    await server.browser_open()
    assert _session(work) is not first, "the dead session was handed out again"
    assert _session(work).kwargs["seed"] == 4242, "the reopened browser is not the same person"


async def test_a_browser_closing_under_an_action_is_the_same_sentence(work, monkeypatch):
    """The window shut by hand, the engine crashed mid-call: the action raises a
    closed target, and that is the same fact as a browser found dead beforehand.
    """
    await server.browser_open(seed=4242)

    async def _closed(session, url, wait_until="domcontentloaded"):
        raise TargetClosedError("Target page, context or browser has been closed")

    monkeypatch.setattr(actions, "navigate", _closed)
    with pytest.raises(RuntimeError) as told:
        await server.browser_navigate("https://example.com/")

    assert str(told.value) == GONE % "main"
    assert work.roles() == []


async def test_a_page_that_refuses_is_the_page_answering_and_the_browser_stays(work, monkeypatch):
    """The case that must NOT be read as a dead browser: a domain that does not
    resolve, a timeout, a selector that matches nothing. The refusal passes
    through as it is and the browser, with its cookies, stays."""
    await server.browser_open(seed=4242)
    before = _session(work)

    async def _refused(session, url, wait_until="domcontentloaded"):
        raise RuntimeError("NS_ERROR_UNKNOWN_HOST")

    monkeypatch.setattr(actions, "navigate", _refused)
    with pytest.raises(RuntimeError, match="NS_ERROR_UNKNOWN_HOST"):
        await server.browser_navigate("https://nope.invalid/")

    assert _session(work) is before and not before.closed


# --- who main is, across processes ------------------------------------------------

async def test_open_with_no_arguments_reopens_the_person_this_session_was(work, monkeypatch):
    """⛔ THE WHOLE OF WHAT SURVIVES A PROCESS: three fields in a file, read by
    `browser_open` and by nothing else. A conversation reopened tomorrow calls
    `browser_open` and is the same person without having to know the seed.

    Known-bad: plan afresh when no argument is given, and every reopened
    conversation is a stranger.
    """
    await server.browser_open(seed=4242, proxy="socks5://10.0.0.1:1080")

    restarted = Work("default", factory=_Recording)
    monkeypatch.setattr(server, "work", restarted)
    said = await server.browser_open()

    launched = restarted._open["main"].kwargs
    assert launched["seed"] == 4242
    assert launched["proxy"]["server"] == "socks5://10.0.0.1:1080"
    assert REMEMBERED in said, said
    assert "headless" in launched, "the launch flags of THIS process are not applied"


async def test_close_keeps_who_it_was(work):
    """Decided 2026-09-14: closing frees the engine, it does not forget the
    person. Somebody else is asked for with an argument."""
    await server.browser_open(seed=4242)
    said = await server.browser_close()

    assert said == "the main browser is closed. Still open: none."
    assert work.roles() == []
    await server.browser_open()
    assert _session(work).kwargs["seed"] == 4242


async def test_an_argument_is_a_decision_and_replaces_the_remembered_person(work):
    await server.browser_open(seed=4242)
    await server.browser_open(seed=7)

    assert _session(work).kwargs["seed"] == 7
    assert store.load("default")["browsers"]["main"]["seed"] == 7


async def test_the_file_holds_who_main_is_and_never_the_helper_or_this_launch(work):
    await server.browser_open(seed=4242)
    await server.browser_open(browser="support")

    saved = store.load("default")
    assert sorted(saved["browsers"]) == ["main"], saved
    assert saved["browsers"]["main"]["seed"] == 4242
    for launch_only in ("headless", "binary_path"):
        assert launch_only not in saved["browsers"]["main"], (
            "%s is this launch's to decide, not the file's" % launch_only)
    # ⛔ THE WHOLE DOCUMENT, for the reason the listing's rows are asserted
    # whole: a field nobody needs is a field somebody will read. `name` sat
    # here until 0.56.0 holding a copy of `id`, kept on the argument that an
    # older build would expect it - and the only thing that ever read it,
    # `known()`, went with the `session_list` tool. Nothing asserted the set
    # of keys, so nothing noticed.
    assert set(saved) == {"id", "saved", "focus", "browsers"}, (
        "the saved session carries something nobody reads: %r" % sorted(saved))


async def test_the_file_is_written_at_open_and_not_on_every_command(work, monkeypatch):
    writes = []
    real = store.save
    monkeypatch.setattr(store, "save", lambda *a, **k: (writes.append(a), real(*a, **k))[1])

    await server.browser_open(seed=4242)
    for url in ("https://a.test/", "https://b.test/", "https://c.test/"):
        await server.browser_navigate(url)

    assert len(writes) == 1, "the file was written %d times for one open" % len(writes)


# --- the helper --------------------------------------------------------------------

async def test_the_helper_inherits_the_exit_and_not_the_person(work):
    """Same exit, different person: a colleague at the next desk. An explicit
    exit for the helper is a decision and beats it."""
    await server.browser_open(seed=4242, proxy="socks5://10.0.0.1:1080")
    await server.browser_open(browser="support")

    helper = _session(work, "support").kwargs
    assert helper["proxy"] == _session(work).kwargs["proxy"]
    assert helper["seed"] != 4242

    await server.browser_open(browser="support", proxy="socks5://10.0.0.9:1080")
    assert _session(work, "support").kwargs["proxy"]["server"] == "socks5://10.0.0.9:1080"


async def test_opening_the_helper_does_not_touch_the_identity(work):
    await server.browser_open(seed=4242)
    identity = _session(work)
    await server.browser_open(browser="support")

    assert _session(work) is identity and not identity.closed
    assert work.roles() == ["main", "support"]


async def test_a_third_browser_is_refused_with_the_two_that_exist(work):
    with pytest.raises(ValueError) as refused:
        await work.open("b3")
    assert "main" in str(refused.value) and "support" in str(refused.value)
    assert work.roles() == []


# --- what can go wrong at open ------------------------------------------------------

async def test_a_failed_start_leaves_nothing_open_and_says_so(work, monkeypatch):
    monkeypatch.setattr(work, "_factory", _NeverStarts)

    with pytest.raises(RuntimeError, match="did NOT start"):
        await server.browser_open(seed=4242)

    assert work.roles() == []
    with pytest.raises(RuntimeError) as told:
        await server.browser_navigate("https://example.com/")
    assert str(told.value) == NOT_OPEN % "main", "a failed start left a browser behind"


async def test_a_refused_plan_leaves_the_running_browser_alone(work):
    """`profile="none"` is the echoed word the planner refuses. The refusal
    must not cost the browser already open."""
    await server.browser_open(seed=4242)
    before = _session(work)

    with pytest.raises(ValueError, match="refused"):
        await server.browser_open(profile="none")

    assert _session(work) is before and not before.closed


# --- looking -------------------------------------------------------------------------

async def test_the_listing_says_what_is_open_and_the_sentence_when_nothing_is(work):
    import json

    empty = json.loads(await server.browser_list())
    assert empty["browsers"] == [] and empty["note"] == NOT_OPEN % "main"
    assert empty["focus"] == "", "nothing is open, so no browser is being worked in"

    await server.browser_open(seed=4242)
    await server.browser_navigate("https://example.com/")
    await server.browser_open(browser="support")
    answer = json.loads(await server.browser_list())
    rows = answer["browsers"]

    assert [r["id"] for r in rows] == ["main", "support"]
    assert rows[0]["url"] == "https://example.com/" and rows[0]["urls"] == ["https://example.com/"]
    assert rows[1]["urls"] == []
    # ⛔ THE WHOLE ROW, BECAUSE A FIELD NOBODY NEEDS IS A BRANCH SOMEBODY WILL
    # WRITE. `running` sat here until 0.54.0 saying `true` on every row this
    # can produce - only open browsers are listed, and one whose engine has
    # gone is dropped - and the page branched on it in three places, over a
    # case the answer cannot contain. `focused` followed it in 0.55.0: it was
    # `id == focus`, and `focus` is two lines above it in the same answer.
    assert set(rows[0]) == {"id", "url", "urls"}, (
        "a row carries something other than what a reader needs: %r" % rows[0])
    # ⛔ AND THE NOTE STILL NAMES `main`, WHICH IS NOT WHERE THE AGENT IS. The
    # helper was opened last, so the focus is on it; where a command that names
    # no browser LANDS is a constant of the two roles and did not move. They
    # were the same string until 0.55.0, which is exactly why one line used to
    # serve both.
    assert answer["focus"] == "support"
    assert "go to main." in answer["note"]


async def test_the_focus_is_the_browser_the_last_command_acted_in(work):
    """⛔ IT WAS THE CONSTANT `main` UNTIL 0.55.0, AND THE INTERFACE DREW IT AS
    A FACT: a dot on that browser reading `the agent is working here`. With the
    helper open the dot sat on `main` while the agent typed into `support`.

    Known-bad, and it is the whole change: drop the line in `Work.acting` that
    records the role. Every assertion below that names `support` then answers
    `main`.
    """
    import json

    async def focus() -> str:
        return json.loads(await server.browser_list())["focus"]

    await server.browser_open()
    await server.browser_open(browser="support")
    assert await focus() == "support", "opening a browser is working in it"

    await server.browser_navigate("https://example.com/", browser="main")
    assert await focus() == "main", "a command names its browser and the focus follows"

    await server.browser_navigate("https://mail.test/", browser="support")
    assert await focus() == "support"

    # A command that names nothing goes to `main`, so the focus goes with it.
    await server.browser_navigate("https://example.com/second")
    assert await focus() == "main"

    # ⛔ AND A COMMAND THAT FAILED STILL HAPPENED THERE. The focus is recorded
    # once the browser has answered for itself and BEFORE the action runs,
    # because the moment a click goes wrong is exactly the moment somebody
    # watching wants to be looking at the screen it went wrong on.
    # Known-bad: record after `fn` returns, and this reads `main`.
    async def refuses(_session):
        raise ZeroDivisionError("the page refused")

    with pytest.raises(ZeroDivisionError):
        await work.acting(refuses, role="support")
    assert await focus() == "support"


async def test_the_focus_never_names_a_browser_that_is_not_open(work):
    """⛔ A FOCUS IS A PLACE TO DRAW A DOT, and a dot on a screen the stage no
    longer holds is worse than no dot. The helper can be closed, or found gone,
    after it was the last thing acted in.

    Known-bad: answer `self._acted` without asking whether it is still open.
    The first assertion then reads `support` over a stage that draws `main`
    alone.
    """
    import json

    async def focus() -> str:
        return json.loads(await server.browser_list())["focus"]

    await server.browser_open()
    await server.browser_open(browser="support")
    await server.browser_close(browser="support")
    assert await focus() == "main"

    await server.browser_close()
    assert await focus() == "", "nothing is open, so nobody is being worked in"


async def test_status_reports_the_person_and_the_page_or_the_sentence(work):
    with pytest.raises(RuntimeError) as told:
        await server.browser_status()
    assert str(told.value) == NOT_OPEN % "main"

    await server.browser_open(seed=4242, proxy="socks5://user:secret@10.0.0.1:1080")
    await server.browser_navigate("https://example.com/")
    said = await server.browser_status()

    assert "seed 4242" in said and "page: https://example.com/." in said
    assert "socks5://10.0.0.1:1080" in said and "secret" not in said

    _session(work).alive = False
    with pytest.raises(RuntimeError) as told:
        await server.browser_status()
    assert str(told.value) == GONE % "main"


async def test_watching_an_open_browser_answers_a_frame(work):
    await server.browser_open(seed=4242)
    await server.browser_navigate("https://example.com/")
    got = await server.browser_watch()
    assert got.data, "no frame came back"


async def test_close_all_closes_both_and_forgets_neither_person(work):
    await server.browser_open(seed=4242)
    await server.browser_open(browser="support")
    both = [_session(work), _session(work, "support")]

    await work.close_all()

    assert all(s.closed for s in both) and work.roles() == []
    assert store.load("default")["browsers"]["main"]["seed"] == 4242


async def test_a_browser_whose_engine_is_gone_is_dropped_by_the_listing_and_said_by_the_status(work):
    """⛔ THE ROUND TRIP IS WHAT NOTICES, AND BOTH READERS HAVE TO ACT ON IT.
    Nothing local can see a process that has gone - the stand-in above stays
    `usable` for that reason, because a real one does - so the listing and the
    status meet a browser that answers everything from memory until the moment
    they ask it something. What they must not do is answer anyway: a row that
    says `running` and a status that names the person are both the picture of
    a browser that is not there.

    Known-bad, two: have the listing keep the row; have the status report the
    identity it holds in `_launched`.
    """
    import json

    await server.browser_open(seed=4242)
    await server.browser_navigate("https://example.com/")
    await server.browser_open(browser="support")
    _session(work).dead = True

    listed = json.loads(await server.browser_list())

    assert [r["id"] for r in listed["browsers"]] == ["support"], (
        "a browser whose engine is gone is still listed as open: %s" % listed)
    assert work.roles() == ["support"], "the dead browser is still held"

    # And it comes back as the same person, which is what the sentence promises.
    await server.browser_open()
    assert _session(work).kwargs["seed"] == 4242
    _session(work).dead = True
    with pytest.raises(RuntimeError) as told:
        await server.browser_status()
    assert str(told.value) == GONE % "main", (
        "the status answered over a browser that is not there: %s" % told.value)
