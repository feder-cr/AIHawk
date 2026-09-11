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
    """A server with no memory of what it held, as after a restart."""
    reg = server.new_registry(
        factory=_Recording,
        defaults=lambda: dict({"seed": 7, "headless": True}, **kwargs))
    monkeypatch.setattr(server, "registry", reg)
    monkeypatch.setattr(server, "_restored", False)
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
    await server.browser_open(seed=4242)

    saved = store.load("default")
    assert saved is not None, "opening a browser did not write the session down"
    assert sorted(saved["browsers"]) == ["main"]
    assert saved["browsers"]["main"]["seed"] == 4242
    assert saved["focus"] == "main"


async def test_the_session_nobody_opened_a_browser_in_is_written_down_too(registry,
                                                                         monkeypatch):
    """⛔ THE ONE THE FIRST VERSION MISSED, AND IT IS THE COMMON CASE. Every
    client written before browsers had names opens none: the first tool that
    needs a page starts one lazily. Persistence hooked `browser_open`,
    `browser_close` and the focus, so the ONE session almost everybody
    has was the only one never saved.

    The identity is real and worth saving - a lazily started browser draws a
    concrete seed, so coming back to it is coming back to that person.

    Known-bad: drop the `on_change` line from `server.new_registry`. Every other
    test in this file still passes, because they all go through a tool that
    remembers by hand.
    """
    async def _nothing(session, *args, **kwargs):
        return "ok"

    monkeypatch.setattr(actions, "navigate", _nothing)
    await server.browser_navigate("http://127.0.0.1/")

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
    await server.browser_open(seed=11,
                              profile=str(tmp_path / "prof"))

    saved = store.load("default")
    assert saved["browsers"]["main"].get("profile_dir"), (
        "the profile was not saved, so the reopened browser keeps the identity "
        "and loses the logins: %r" % saved["browsers"]["main"])


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


async def test_the_helper_is_never_written_down(registry):
    """⛔ THE HELPER IS NOT AN IDENTITY, AND THE FILE IS WHERE THAT IS DECIDED.
    `support` exists for what must not touch the session's identity - a
    temporary mailbox, a lookup - and a helper that came back after a restart
    would be a second identity the session carries, which is the thing two
    fixed roles exist to rule out. It lives for the task and dies with the
    process.

    This test used to be `test_moving_the_focus_is_written_down`, about a field
    that is now always `main`: with two fixed roles there is nothing to focus,
    and a command is about `main` unless it says `support`.

    Known-bad: drop the `continue` for `SUPPORT_BROWSER_ID` in `remember`. The
    helper is written into the file, and the first assertion goes red.
    """
    await server.browser_open(seed=4242)
    await server.browser_open(browser="support", seed=99)

    saved = store.load("default")
    assert sorted(saved["browsers"]) == ["main"], (
        "the helper was written into the session file: %r" % saved["browsers"])
    assert saved["browsers"]["main"]["seed"] == 4242, (
        "the helper was written down UNDER the identity's name, which is worse "
        "than saving it: %r" % saved["browsers"]["main"])
    assert saved["focus"] == "main"


# --- what gets read back ----------------------------------------------------

async def test_reopening_gives_the_browsers_back_without_starting_one(registry,
                                                                     restarted):
    """⛔ THE WHOLE SHAPE OF THE FEATURE, IN ONE ASSERTION PAIR. The browsers are
    there and the engines are not.

    Known-bad: make `restore` call `ensure` instead of `declare`. The first
    assertion still passes, the second reports eight browsers nobody asked to
    start - which on the real factory is 61 processes and about 6.5 GB.
    """
    await server.browser_open(seed=4242)
    await server.browser_open(browser="support", seed=99)

    reg = restarted()
    assert reg.ids() == [], "a browser was running before anything was reopened"

    # The identity comes back; the helper does not, and that is the promise
    # rather than a gap - a helper that survived a restart would be a second
    # identity the session carries.
    assert server.browsers_in() == ["main"], (
        "the session came back without its browser, or came back with the "
        "helper too: %r" % server.browsers_in())
    assert reg.ids() == [], (
        "reopening a session STARTED its browsers: %r" % reg.ids())


async def test_a_reopened_browser_comes_back_as_the_person_it_was(registry, restarted):
    """A declaration that did not carry the identity would be a list of names.

    Known-bad, two: have `restore` declare `{}` instead of the saved config, and
    take the `in_session` out of `addressed` so the saved session is never read
    by a client that simply navigates.
    """
    await server.browser_open(seed=4242)

    reg = restarted(seed=1234)  # the environment would give a different person
    session = await reg.ensure(server.addressed())

    assert session.kwargs["seed"] == 4242, (
        "the reopened browser was built from the environment instead of from "
        "who it was: %r" % session.kwargs)


async def test_a_session_saved_under_other_names_comes_back_as_main(registry,
                                                                   restarted):
    """⛔ THE ONLY DOOR LEFT THAT A BROWSER WITH ANOTHER NAME CAN COME THROUGH,
    and it is not a tool: it is a FILE. Nothing in this process makes a browser
    outside the two roles since 0.40.0, but a session written by 0.38.0 can
    name eight and call them `b-tech` or `walmart-jobs`, and it is sitting on
    somebody's disk waiting to be restored. Restore them as they are and every
    rule written since is true of every session except the ones that existed
    before - the worst kind of exception, because nobody meets it until they
    upgrade.

    What comes back is ONE browser as `main`: the one the file says was in
    focus, because that is the browser the person was left in front of. The two
    halves are asserted together, because the NAME says the renaming happened
    and the SEED says it renamed the right one - and it is the identity that
    matters, since that is the browser with the logins in it.

    This test used to be `test_the_focus_comes_back_with_the_session`. The
    focus is always `main` now, so what is worth holding is the migration.

    Known-bad, two: keep `held[keep]` under `keep`, and it comes back as
    `b-tech`; drop the focus from the choice, and `sorted()` hands back
    `b-corporate`, which is somebody else.
    """
    store.save("default", {"b-corporate": {"seed": 1, "headless": True},
                           "b-tech": {"seed": 2, "headless": True}},
               focus="b-tech")

    reg = restarted()
    assert server.browsers_in() == ["main"], (
        "a session saved before the change came back holding %r"
        % server.browsers_in())
    assert server.addressed() == "default/main"
    assert (reg.config("default/main") or {}).get("seed") == 2, (
        "it came back under the right name and as the wrong person: %r"
        % reg.config("default/main"))


async def test_which_file_this_process_persists_to_comes_from_the_environment(
        registry, restarted, monkeypatch):
    """⛔ THIS IS THE ONLY PLACE "WHICH SESSION" STILL EXISTS, AND IT IS NOT A
    TOOL ARGUMENT. No tool here takes a session id, lists saved sessions, or
    deletes one - a model working through this server cannot enumerate or
    reach a second piece of work, by design. What used to be `session_id` on
    every call is now `_SESSION_ID`, read from `AIHAWK_SESSION_ID` once, at
    import, by whoever SPAWNS the process - the interface, spawning one server
    per conversation, or nobody at all for a standalone client, which lands on
    `default` exactly as every caller did before this had a name.

    Monkeypatching the read value stands in for a second process reading a
    second one: the module-level read happens once, at import, so within one
    test process the only way to exercise a different value is to set it
    directly - which is the same effect a real second process gets from a
    real second environment variable. `tests/mcp_server/test_stdio_e2e.py`
    proves the environment variable itself works, with two real subprocesses.

    Known-bad: key the store by anything but `_SESSION_ID` - a single file,
    say. The second `browser_open` then overwrites the first one's file and
    only one of the two survives.
    """
    monkeypatch.setattr(server, "_SESSION_ID", "work")
    await server.browser_open(seed=1)

    monkeypatch.setattr(server, "_SESSION_ID", "home")
    await server.browser_open(seed=2)

    saved_work = store.load("work")
    saved_home = store.load("home")
    assert saved_work is not None and saved_home is not None, (
        "one file overwrote the other: work=%r home=%r" % (saved_work, saved_home))
    assert saved_work["browsers"]["main"]["seed"] == 1
    assert saved_home["browsers"]["main"]["seed"] == 2

    # And a restart reads back whichever one this process is told it is.
    reg = restarted()
    monkeypatch.setattr(server, "_SESSION_ID", "work")
    assert server.browsers_in() == ["main"]
    assert reg.config("work/main")["seed"] == 1, (
        "restoring \"work\" came back as somebody else: %r"
        % reg.config("work/main"))


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
    `addressed`, which every tool reaches, so without it the server reads a
    file from disk on every single command; and a session this server has
    already loaded must not be re-read from underneath, or a browser it
    deliberately closed comes back because something else wrote the file.

    Known-bad: drop the `if _restored: return False` from `restore`.
    """
    await server.browser_open()

    restarted()
    reads = []
    real_load = store.load
    monkeypatch.setattr(store, "load",
                        lambda sid: (reads.append(sid), real_load(sid))[1])

    assert server.browsers_in() == ["main"]
    for _ in range(5):
        server.browsers_in()
        server.addressed()
    assert len(reads) == 1, (
        "the saved session was read from disk %d times; `restore` runs from "
        "`in_session`, so that is once per command" % len(reads))

    # And a session already loaded is this server's to decide, not the file's.
    # The file is rewritten from underneath naming the browser that was just
    # closed, which is the shape of the defect: something else writes, and the
    # server re-reads a session it has already made up its mind about.
    await server.browser_close()
    store.save("default", {"main": {"seed": 1}})

    assert server.browsers_in() == [], (
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
    await server.browser_open(seed=4242)
    assert store.load("default") is not None

    await registry.close_all()

    saved = store.load("default")
    assert saved is not None, (
        "shutting down deleted the saved session, so nothing survives the "
        "process the persistence exists to survive")
    assert sorted(saved["browsers"]) == ["main"]


async def test_a_browser_that_died_underneath_is_still_a_browser_of_the_session(registry):
    """`drop` is recovery, not a close: the engine is gone, the person is not.
    Writing the session down without it would lose an identity every time a
    retry failed.

    Known-bad: fire `_changed` from `drop`.
    """
    await server.browser_open(seed=4242)

    await registry.drop(server.addressed())

    assert store.load("default")["browsers"]["main"]["seed"] == 4242


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

    said = await server.browser_open(seed=4242)

    assert "could not start" not in said, said
    assert server.browsers_in() == ["main"]


# --- closing the last browser on purpose ------------------------------------

async def test_closing_the_last_browser_closes_it_and_erases_the_file(registry):
    """⛔ THIS USED TO BE `session_forget`'S JOB, AND THE TOOL IS GONE - not
    replaced, because there is nothing left for it to do that `browser_close`
    does not already do from inside the one process a model can reach.
    `remember`'s empty branch already erases the file the moment the last
    browser goes, so "delete this saved identity" falls out of "close the
    browser" for free, with no second tool and no way to name a DIFFERENT
    process's identity to delete - which is exactly the operation the owner
    ruled out.

    ⛔ AND THE ASSERTION ON WHAT IT SAYS IS WHERE THE OLD TOOL'S BUG LIVED. The
    first version of `session_forget` answered "there is no saved session
    called X" for a deletion that HAD just happened, because both of its
    branches shared one sentence with the id spliced in - so `"work" in said`
    passed on both answers and the wrong one shipped for a release. The two
    branches here already say different things; this pins that they still do.

    Known-bad, two: have `browser_close` erase the file without closing the
    live browser - it stays running, holding its memory and its profile, with
    nothing left that names it; or collapse its two return sentences into one.
    """
    await server.browser_open(seed=4242)
    running = registry.peek("default/main")
    assert store.load("default") is not None

    closed = await server.browser_close()

    assert running.closed, "the browser was reported closed while still running"
    assert store.load("default") is None
    assert closed == "the main browser is closed. Still open: none.", closed

    said_again = await server.browser_close()
    assert said_again == "the main browser is not open.", (
        "closing a browser that was already gone is answered the same as "
        "closing one that just was: %r" % said_again)


async def test_a_restored_browser_runs_on_the_engine_this_build_was_given(
        registry, monkeypatch):
    """⛔ THE ENGINE IS A PROPERTY OF THE PROCESS, NOT OF THE SESSION, and
    leaving it out of the FILE was read as leaving it out of the BROWSER.

    `WHO_A_BROWSER_IS` keeps `binary_path` out of what a session writes down,
    and rightly: it is a path on THIS machine, and a session carried to another
    one must resolve an engine rather than insist on a path that means nothing
    there. But a browser restored from that file was then declared without an
    engine at all, so it came back on whatever the seal resolved instead of on
    the one the person had named.

    Measured 2026-09-09, and not only a developer's problem: somebody running
    `aihawk ui --binary <their build>` and reopening a session got browsers on a
    DIFFERENT engine, silently. On a locally built one - a seal with no
    published assets - they got no browser at all, because there was nothing to
    download and nothing to run. The interface's own agent hit it live and
    worked around it by closing and reopening every browser under the same name,
    which works precisely because `browser_open` goes through the launch plan
    and a restore does not.

    Same shape as the system prompt a saved conversation used to carry back in
    place of the current one: the file says what happened, the build says what
    it runs on.

    Known-bad: `registry.declare(key, config)` without the engine.
    """
    monkeypatch.setenv("STEALTHFOX_BINARY", "C:/an/engine/firefox.exe")
    store.save("default", {"main": {"seed": 4242, "headless": True}})

    session = await server.ready()

    assert session.kwargs.get("seed") == 4242, "it came back as somebody else"
    assert session.kwargs.get("binary_path") == "C:/an/engine/firefox.exe", (
        "the browser came back without the engine this process was told to "
        "run, so it resolved one from the seal instead: %r" % session.kwargs)


async def test_and_the_engine_is_still_never_written_into_the_file(registry,
                                                                  monkeypatch):
    """The other half, and the reason the first half is not simply adding
    `binary_path` to what a session saves. A path on this machine written into a
    session file is a session that only opens here.

    Known-bad: put "binary_path" into WHO_A_BROWSER_IS.
    """
    monkeypatch.setenv("STEALTHFOX_BINARY", "C:/an/engine/firefox.exe")
    await server.browser_open(seed=4242)

    saved = store.load("default")
    assert "binary_path" not in saved["browsers"]["main"], (
        "the session file carries a path that means nothing on another "
        "machine: %r" % saved["browsers"]["main"])
