"""A session outlives the server: what it held is written down and read back.

Until this, a session was a dictionary that died with the process. "Reopen the
one I was working in" meant nothing, and the identity a session had spent an
hour building - the seed, the exit, the profile with the logins in it - was
gone the moment the server stopped.

⛔ WHAT IS PROMISED IS THE DECLARATION, NOT EIGHT LIVE BROWSERS. Eight of those
were measured at 61 processes and about 6.5 GB, the eighth taking 13.6 s to
start, so a reopen that launched them all would spend a minute and most of the
machine to hand back something nobody has asked for yet. A reopened browser is
a promise about WHO it will be; the engine starts when a command is aimed at it.
Three tests below hold that line, because it is the kind of thing a later reader
"fixes" into eagerly starting them.

No browser starts here. The registry is built by the server's own constructor -
so the wiring that writes sessions down is the wiring under test - with a
factory that launches nothing.

`tests/conftest.py` points `AIHAWK_HOME` at a temporary directory for every
test in the package. Without it these write into the developer's real
`%APPDATA%`, which is not a hypothetical: they did, on the first run.
"""
from __future__ import annotations

import pytest

from aihawk.mcp import actions, server, store


class _Recording:
    """A session that launches nothing and reports itself alive."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._browser = None
        self._context = object()
        self.closed = False

    async def start(self):
        pass

    async def close(self):
        self.closed = True

    async def describe_pages(self):
        return []


def _fresh(monkeypatch, **kwargs):
    """A server with no memory of any session, as after a restart."""
    reg = server.new_registry(
        factory=_Recording,
        defaults=lambda: dict({"seed": 7, "headless": True}, **kwargs))
    monkeypatch.setattr(server, "registry", reg)
    monkeypatch.setattr(server, "_focus", {})
    monkeypatch.setattr(server, "_loaded", set())
    return reg


@pytest.fixture
def registry(monkeypatch):
    return _fresh(monkeypatch)


@pytest.fixture
def restarted(monkeypatch):
    """Restart the server: everything in memory goes, the disk stays."""
    return lambda **kw: _fresh(monkeypatch, **kw)


# --- what gets written ------------------------------------------------------

async def test_opening_a_browser_writes_the_session_down_immediately(registry):
    """Not on a timer and not at shutdown. A server that is killed - which is
    how a stdio server usually ends - never reaches its own shutdown, so a
    session saved there is a session saved never.

    Known-bad: move the save into the lifespan exit. Everything still passes
    that closes cleanly, and nothing that is killed.
    """
    await server.browser_open(browser_id="docs", seed=4242)

    saved = store.load("default")
    assert saved is not None, "opening a browser did not write the session down"
    assert sorted(saved["browsers"]) == ["docs"]
    assert saved["browsers"]["docs"]["seed"] == 4242
    assert saved["focus"] == "docs"


async def test_the_session_nobody_opened_a_browser_in_is_written_down_too(registry,
                                                                         monkeypatch):
    """⛔ THE ONE THE FIRST VERSION MISSED, AND IT IS THE COMMON CASE. Every
    client written before browsers had names opens none: the first tool that
    needs a page starts one lazily. Persistence hooked `browser_open`,
    `browser_close` and `browser_focus`, so the ONE session almost everybody
    has was the only one never saved.

    The identity is real and worth saving - a lazily started browser draws a
    concrete seed, so coming back to it is coming back to that person.

    Known-bad: drop the `on_change` line from `server.new_registry`. Every other
    test in this file still passes, because they all go through a tool that
    remembers by hand.
    """
    async def _nothing(session, *args, **kwargs):
        return "ok"

    monkeypatch.setattr(actions, "new_page", _nothing)
    await server.session_new_page()

    saved = store.load("default")
    assert saved is not None, (
        "a session whose browser started lazily was never written down, so the "
        "session almost every client has cannot be reopened")
    assert saved["browsers"]["main"]["seed"] == 7


async def test_a_profile_is_saved_because_it_is_what_carries_the_logins(registry,
                                                                       tmp_path):
    """⛔ MEASURED BY GETTING IT WRONG. The saved fields were named from the
    TOOL's vocabulary - `seed`, `proxy`, `profile` - and the launch kwarg is
    `profile_dir`, so the filter matched nothing and the profile was the single
    field never written. Nothing failed: every browser came back with the right
    seed and the right exit, and logged out, which is the one thing a person
    reopens a session for.

    Known-bad: put `profile` back in `WHO_A_BROWSER_IS` in place of
    `profile_dir`.
    """
    await server.browser_open(browser_id="mail", seed=11,
                              profile=str(tmp_path / "prof"))

    saved = store.load("default")
    assert saved["browsers"]["mail"].get("profile_dir"), (
        "the profile was not saved, so the reopened browser keeps the identity "
        "and loses the logins: %r" % saved["browsers"]["mail"])


async def test_the_saved_fields_are_the_launch_kwargs_and_not_a_second_vocabulary(
        registry, tmp_path):
    """The class the bug above belongs to, closed rather than the one case.

    A name in `WHO_A_BROWSER_IS` that no launch kwarg answers to filters nothing
    and says nothing, and a launch kwarg that describes this machine must not be
    written into a file another machine reads. So the list is checked against
    what the planner actually produces, in both directions.

    Known-bad, two: add `"profile"` to `WHO_A_BROWSER_IS`, and add
    `"binary_path"`.
    """
    from aihawk.mcp import plan

    produced = set(plan.plan_session(seed=1, proxy="socks5://127.0.0.1:1",
                                     profile=str(tmp_path / "prof")).kwargs)
    invented = sorted(set(server.WHO_A_BROWSER_IS) - produced)
    assert not invented, (
        "these are saved but no launch kwarg is called that, so they filter "
        "nothing: %r. The launch names are %r" % (invented, sorted(produced)))

    #: What is deliberately NOT saved, and why, so this test fails on a new
    #: kwarg instead of silently ignoring it.
    THIS_MACHINE = {"binary_path"}
    unclassified = sorted(produced - set(server.WHO_A_BROWSER_IS) - THIS_MACHINE)
    assert not unclassified, (
        "the planner produces settings this file has never decided about: %r. "
        "Either they say who a browser is, and belong in WHO_A_BROWSER_IS, or "
        "they describe this machine, and belong in THIS_MACHINE with a reason."
        % unclassified)


async def test_moving_the_focus_is_written_down(registry):
    """The focus is which browser unaddressed commands mean, and it is the
    registry's one blind spot: it lives in the server, so nothing the registry
    does can save it.

    Known-bad: delete the `remember(at_session)` from `browser_focus`. Every
    browser still comes back; the commands land on the wrong one.
    """
    await server.browser_open(browser_id="docs")
    await server.browser_open(browser_id="dash")
    await server.browser_focus(browser_id="docs")

    assert store.load("default")["focus"] == "docs"


# --- what gets read back ----------------------------------------------------

async def test_reopening_gives_the_browsers_back_without_starting_one(registry,
                                                                     restarted):
    """⛔ THE WHOLE SHAPE OF THE FEATURE, IN ONE ASSERTION PAIR. The browsers are
    there and the engines are not.

    Known-bad: make `restore` call `ensure` instead of `declare`. The first
    assertion still passes, the second reports eight browsers nobody asked to
    start - which on the real factory is 61 processes and about 6.5 GB.
    """
    await server.browser_open(browser_id="docs", seed=4242)
    await server.browser_open(browser_id="dash", seed=99)

    reg = restarted()
    assert reg.ids() == [], "a browser was running before anything was reopened"

    assert server.browsers_in() == ["dash", "docs"], (
        "the session came back without its browsers")
    assert reg.ids() == [], (
        "reopening a session STARTED its browsers: %r" % reg.ids())


async def test_a_reopened_browser_comes_back_as_the_person_it_was(registry, restarted):
    """A declaration that did not carry the identity would be a list of names.

    Known-bad, two: have `restore` declare `{}` instead of the saved config, and
    take the `in_session` out of `addressed` so the saved session is never read
    by a client that simply navigates.
    """
    await server.browser_open(browser_id="docs", seed=4242)

    reg = restarted(seed=1234)  # the environment would give a different person
    session = await reg.ensure(server.addressed(browser_id="docs"))

    assert session.kwargs["seed"] == 4242, (
        "the reopened browser was built from the environment instead of from "
        "who it was: %r" % session.kwargs)


async def test_the_focus_comes_back_with_the_session(registry, restarted):
    """Known-bad: drop the `_focus[at_session] = saved["focus"]` line in
    `restore`. The browsers come back and every unaddressed command goes to
    `main`, which is a browser this session may not even have.
    """
    await server.browser_open(browser_id="docs")
    await server.browser_open(browser_id="dash")
    await server.browser_focus(browser_id="docs")

    restarted()
    assert server.browsers_in() == ["dash", "docs"]
    assert server.focused() == "docs"
    assert server.addressed() == "default/docs"


async def test_two_saved_sessions_come_back_as_two(registry, restarted):
    """Known-bad: key the store by anything but the session id - a single file,
    say. One session then overwrites the other and the second one to be saved is
    the only one that exists.
    """
    await server.browser_open(browser_id="docs", session_id="work", seed=1)
    await server.browser_open(browser_id="mail", session_id="home", seed=2)

    restarted()
    assert server.browsers_in("work") == ["docs"]
    assert server.browsers_in("home") == ["mail"]

    listed = await server.session_list()
    assert "work" in listed and "home" in listed, listed


async def test_a_session_is_read_from_disk_once_and_not_on_every_command(registry,
                                                                        restarted,
                                                                        monkeypatch):
    """⛔ THE FIRST VERSION OF THIS TEST NAMED THE WRONG KNOWN-BAD, AND SAYING SO
    IS THE POINT. It claimed that without the `_loaded` guard a closed browser
    would come back on the next call. Run with the guard removed, it stayed
    green: every change is written down before the next read, so the file the
    re-read finds already agrees with memory. The guard was real and the test
    was measuring something else.

    What the guard actually holds is both halves below. `restore` runs from
    `in_session`, which every tool reaches, so without it the server reads a
    file from disk on every single command; and a session this server has
    already loaded must not be re-read from underneath, or a browser it
    deliberately closed comes back because something else wrote the file.

    Known-bad: drop the `if at_session in _loaded: return False` from `restore`.
    """
    await server.browser_open(browser_id="docs")
    await server.browser_open(browser_id="dash")

    restarted()
    reads = []
    real_load = store.load
    monkeypatch.setattr(store, "load",
                        lambda sid: (reads.append(sid), real_load(sid))[1])

    assert server.browsers_in() == ["dash", "docs"]
    for _ in range(5):
        server.browsers_in()
        server.addressed()
    assert len(reads) == 1, (
        "the saved session was read from disk %d times; `restore` runs from "
        "`in_session`, so that is once per command" % len(reads))

    # And a session already loaded is this server's to decide, not the file's.
    await server.browser_close(browser_id="docs")
    store.save("default", {"docs": {"seed": 1}, "dash": {"seed": 2}})

    assert server.browsers_in() == ["dash"], (
        "a browser this server closed came back because the file was read again")


# --- what must NOT get written ----------------------------------------------

async def test_shutting_the_process_down_does_not_erase_the_saved_sessions(registry):
    """⛔ THE ONE THAT WOULD DESTROY THE FEATURE WHILE LOOKING LIKE HOUSEKEEPING.
    `close_all` forgets every identity, on purpose, because the process is
    ending. If forgetting wrote the session down, every session would be saved
    as empty at shutdown - and `remember` erases a session with no browsers, so
    the last act of every server would be to delete everything it had saved.

    Known-bad: fire `_changed` from `close_all` too.
    """
    await server.browser_open(browser_id="docs", seed=4242)
    assert store.load("default") is not None

    await registry.close_all()

    saved = store.load("default")
    assert saved is not None, (
        "shutting down deleted the saved session, so nothing survives the "
        "process the persistence exists to survive")
    assert sorted(saved["browsers"]) == ["docs"]


async def test_a_browser_that_died_underneath_is_still_a_browser_of_the_session(registry):
    """`drop` is recovery, not a close: the engine is gone, the person is not.
    Writing the session down without it would lose an identity every time a
    retry failed.

    Known-bad: fire `_changed` from `drop`.
    """
    await server.browser_open(browser_id="docs", seed=4242)

    await registry.drop(server.addressed(browser_id="docs"))

    assert store.load("default")["browsers"]["docs"]["seed"] == 4242


async def test_a_write_that_fails_does_not_cost_the_caller_the_browser(registry,
                                                                      monkeypatch):
    """The browser is built and correct by the time anything is written. A full
    disk, or a home directory somebody made read-only, must cost a saved session
    and nothing else.

    Known-bad: remove the try/except from `remember`.
    """
    def _explode(*args, **kwargs):
        raise OSError("no space left on device")

    monkeypatch.setattr(store, "save", _explode)

    said = await server.browser_open(browser_id="docs", seed=4242)

    assert "could not start" not in said, said
    assert server.browsers_in() == ["docs"]


# --- forgetting one on purpose ----------------------------------------------

async def test_forgetting_a_session_closes_its_browsers_and_unlists_it(registry):
    """Known-bad: have `session_forget` erase the file without closing the
    browsers. They stay running, holding their memory and their profiles, with
    nothing left that names them - the leak being unreachable engines rather
    than a wrong answer.
    """
    await server.browser_open(browser_id="docs", session_id="work")
    running = registry.peek("work/docs")

    said = await server.session_forget(session_id="work")

    assert running.closed, "the session was forgotten with its browser still up"
    assert store.load("work") is None
    assert "work" in said
    assert server.browsers_in("work") == []


async def test_forgetting_a_session_that_was_never_saved_says_so(registry):
    """A tool that answers "done" to a session that never existed teaches a
    model that the name it used was right.

    Known-bad: return the same sentence in both branches.
    """
    said = await server.session_forget(session_id="never-existed")
    assert "no saved session" in said, said


async def test_closing_the_last_browser_stops_the_session_being_listed(registry):
    """A session here IS its browsers, so one with none left has nothing to
    reopen, and leaving it listed offers a reopen that gives back nothing.

    Known-bad: drop the `store.erase` from `remember`'s empty branch. The
    session list then fills with names that restore to nothing.
    """
    await server.browser_open(browser_id="docs")
    assert store.load("default") is not None

    await server.browser_close(browser_id="docs")

    assert store.load("default") is None
    assert "no saved sessions yet" in await server.session_list()
