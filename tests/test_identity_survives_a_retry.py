"""A recovered session has to be the SAME person, not a fresh one from the shell.

⛔ THIS IS THE ONE THAT LEAKS. Every browsing tool runs through `_retrying`,
which on any exception drops the session and calls `ensure()` again. `ensure`
built the replacement from the environment, so a session started as

    session_start(seed=4242, proxy="socks5://...", profile="C:/tmp/acct-a")

came back after one timeout with none of those three. The seed changed, the
profile was gone, and - the part that matters for this product - the proxy was
gone too, so the traffic left from the host's own address. The tool returned
SUCCESS, because the second attempt worked.

A dead browser between two calls is the ordinary case here, not an exotic one.
That is exactly why recovery must not be allowed to change who is browsing: the
common path must not be the one that deanonymises the caller.

No browser starts here. The registry takes a factory, so the whole behaviour is
observable from the kwargs a rebuilt session was constructed with.
"""
from __future__ import annotations

import pytest

from invisible_playwright_mcp.registry import DEFAULT_SESSION_ID, SessionRegistry


class _Recording:
    """A session that records what it was built with and reports itself alive."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._browser = None
        self._context = object()
        self.closed = False

    async def start(self):
        pass

    async def close(self):
        self.closed = True


class _DiesOnce:
    """Alive until someone kills it, like a browser that goes away mid-task."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._browser = None
        self._context = object()

    async def start(self):
        pass

    async def close(self):
        pass


def _identity(session):
    """The three things that decide WHO is browsing and WHERE from."""
    return (
        session.kwargs.get("seed"),
        session.kwargs.get("proxy"),
        session.kwargs.get("profile_dir"),
    )


CHOSEN = {
    "seed": 4242,
    "proxy": {"server": "socks5://exit-a.invalid:1080"},
    "profile_dir": "C:/tmp/acct-a",
}


async def test_a_rebuilt_session_is_the_same_person():
    """The load-bearing one: drop then ensure must not change the identity.

    This is `_retrying`'s recovery path with the action removed. Known-bad is
    today's `ensure`, which calls the factory with no arguments at all.
    """
    registry = SessionRegistry(factory=_Recording)

    first = await registry.restart(**CHOSEN)
    assert _identity(first) == (4242, CHOSEN["proxy"], "C:/tmp/acct-a")

    await registry.drop()
    second = await registry.ensure()

    assert _identity(second) == _identity(first), (
        "recovery changed who is browsing: started as %r, came back as %r"
        % (_identity(first), _identity(second)))


async def test_a_rebuilt_session_still_goes_out_through_the_proxy():
    """Stated separately because it is the one with a consequence beyond a
    confusing answer: losing the proxy puts the traffic on the host's own
    address, which is the thing this product exists to prevent."""
    registry = SessionRegistry(factory=_Recording)

    await registry.restart(**CHOSEN)
    await registry.drop()
    recovered = await registry.ensure()

    assert recovered.kwargs.get("proxy") == CHOSEN["proxy"], (
        "the recovered session has no proxy, so it leaves from the host IP")


async def test_a_session_that_died_is_replaced_by_the_same_person():
    """The real shape of the failure: nobody calls `drop` on purpose. The
    browser dies on its own and the registry notices it is unusable."""
    registry = SessionRegistry(factory=_DiesOnce)

    started = await registry.restart(**CHOSEN)
    started._context = None          # what a dead browser looks like from here

    replacement = await registry.ensure()

    assert replacement is not started, "the dead session was handed back"
    assert _identity(replacement) == _identity(started), (
        "the browser died and came back as somebody else: %r -> %r"
        % (_identity(started), _identity(replacement)))


async def test_closing_a_session_forgets_who_it_was():
    """⛔ The counter-case, and it has to hold or the memory becomes a leak of
    its own: a session closed ON PURPOSE must not come back from the dead
    wearing the same identity. Remembering is for recovery, not for resurrection.

    Without this a caller who closed a proxied session, then let a later tool
    auto-start one, would silently get the old proxy and the old profile back.
    """
    registry = SessionRegistry(factory=_Recording,
                               defaults=lambda: {"seed": 7, "headless": True})

    await registry.restart(**CHOSEN)
    await registry.close_all()

    fresh = await registry.ensure()
    assert _identity(fresh) == (7, None, None), (
        "a deliberately closed session came back as %r" % (_identity(fresh),))


class _Numbering(_Recording):
    """A stand-in that numbers tabs the way the real session does."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._counter = 0

    def resume_numbering_after(self, highest):
        self._counter = max(self._counter, highest)

    def open_tab(self):
        self._counter += 1
        return "tab-%d" % self._counter


async def test_a_tab_id_from_before_a_rebuild_names_nothing_after_it():
    """⛔ Tab ids restarted at `tab-1` on every rebuild, so an id a caller was
    still holding resolved to a DIFFERENT page rather than erroring - which
    `session.page()` refuses to do for a named tab, on the stated grounds that
    acting on the wrong tab with nothing said is worse than an error.

    A rebuild is the common path, and the identity memory that keeps the same
    person across one also keeps the caller going, so the stale id got MORE
    reachable, not less. Numbering continues instead.
    """
    registry = SessionRegistry(factory=_Numbering)

    first = await registry.restart(**CHOSEN)
    before = [first.open_tab(), first.open_tab()]

    await registry.drop()
    second = await registry.ensure()
    after = second.open_tab()

    assert after not in before, (
        "the rebuilt session handed out %s again, which the caller may still be "
        "holding for another page" % after)


class _DeadProxy:
    """A browser that starts fine WITHOUT a proxy and not with one.

    ⛔ It has to be selective, and the first version of it was not. A stand-in
    that always raises makes the test below pass whether or not the refusal is
    remembered - the rebuild simply fails for its own reasons - so it proved
    nothing. Measured: with a factory that always raised, deleting the refusal
    check left all ten tests green. Failing only on the proxied config is what
    makes the unproxied fallback visible as a PASS where an error belongs.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._browser = None
        self._context = None

    async def start(self):
        if self.kwargs.get("proxy"):
            raise RuntimeError("proxy refused the connection")
        self._context = object()

    async def close(self):
        pass


async def test_a_failed_start_does_not_let_the_next_tool_go_out_unproxied():
    """⛔ THE SAME LEAK, ONE CALL LATER, ON THE LIKELIER PATH.

    A session_start that fails used to leave the id empty, and the very next
    browsing tool auto-started a browser from the environment: the caller asked
    for an exit, was told it failed, carried on, and went out from this
    machine's own address while every tool answered normally.

    Known-bad is an empty id plus lazy auto-start. The refusal is remembered
    instead, and it keeps being raised until a session_start works.
    """
    registry = SessionRegistry(factory=_DeadProxy,
                               defaults=lambda: {"seed": 7, "headless": True})

    with pytest.raises(RuntimeError):
        await registry.restart(**CHOSEN)

    # The default config has NO proxy, so it would start perfectly well. That is
    # the whole danger: the fallback succeeds, and it succeeds unproxied.
    with pytest.raises(RuntimeError, match="proxy refused"):
        await registry.ensure()

    assert registry.peek() is None, "a browser was started after a refused start"
    assert registry.config() is None, "a failed start armed recovery anyway"


async def test_a_working_start_clears_an_earlier_refusal():
    """The counter-case, and without it the refusal is a session nobody can
    recover: one bad proxy would wedge the id for the life of the process."""
    registry = SessionRegistry(factory=_DeadProxy)

    with pytest.raises(RuntimeError):
        await registry.restart(**CHOSEN)
    session = await registry.restart(seed=99, headless=True)
    assert session.kwargs["seed"] == 99

    # ⛔ DROPPED FIRST, or this proves nothing: `ensure` hands back a live
    # session without ever consulting the refusals, so with a session still up
    # the assertion below passes whether the refusal was cleared or not. The
    # recovery path is the one that has to be clean.
    await registry.drop()
    assert (await registry.ensure()).kwargs["seed"] == 99, (
        "a cleared refusal came back and wedged the id")


async def test_a_caller_that_never_said_anything_still_gets_a_browser():
    """The other counter-case: lazy auto-start is the whole default experience
    and must survive. Only a caller who ASKED and was refused is held."""
    registry = SessionRegistry(factory=_Recording,
                               defaults=lambda: {"seed": 7, "headless": True})

    assert (await registry.ensure()).kwargs["seed"] == 7


async def test_two_sessions_are_rebuilt_as_two_different_people():
    """⛔ THE MEMORY IS KEYED BY ID, AND WITHOUT THIS NOTHING SAYS SO.

    Every other test in this file passes against a memory that is ONE dict for
    the whole registry - measured, on a copy of the tree - and that wrong shape
    is the likeliest thing somebody writes, because with one client it behaves
    identically. It is not a nuisance: the registry keys sessions, locks and now
    configs by id precisely so more than one can exist, and the HTTP transport
    is there so more than one client can attach. Under a single dict, client B
    starting its own session means client A's next recovery rebuilds A wearing
    B's identity and B's exit - the deanonymisation this file exists to prevent,
    arriving through the fix for it.
    """
    registry = SessionRegistry(factory=_Recording)

    await registry.restart("a", seed=1, profile_dir="C:/tmp/acct-a")
    await registry.restart("b", seed=2, profile_dir="C:/tmp/acct-b")

    # BOTH are dropped, so both go through the rebuild. Dropping only one left
    # the other answering from its live session, and a memory that read the
    # FIRST entry instead of the one for this id then survived the test - a is
    # the first key, so the arm that was checked passed by accident.
    await registry.drop("a")
    await registry.drop("b")
    rebuilt_a = await registry.ensure("a")
    rebuilt_b = await registry.ensure("b")

    assert _identity(rebuilt_a) == (1, None, "C:/tmp/acct-a"), (
        "session 'a' came back as %r" % (_identity(rebuilt_a),))
    assert _identity(rebuilt_b) == (2, None, "C:/tmp/acct-b"), (
        "session 'b' came back as %r" % (_identity(rebuilt_b),))


async def test_a_second_start_replaces_the_remembered_identity():
    """Switching person has to actually switch, including on the recovery path.

    Known-bad is a memory that is written once and never updated: the caller
    moves to the second account, the browser dies, and recovery puts them back
    in the first one.
    """
    registry = SessionRegistry(factory=_Recording)

    await registry.restart(**CHOSEN)
    second = {"seed": 99, "profile_dir": "C:/tmp/acct-b"}
    await registry.restart(**second)

    await registry.drop()
    recovered = await registry.ensure()

    assert _identity(recovered) == (99, None, "C:/tmp/acct-b"), (
        "recovery went back to the previous identity: %r" % (_identity(recovered),))
