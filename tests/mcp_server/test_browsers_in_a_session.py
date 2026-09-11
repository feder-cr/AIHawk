"""A session holds two browsers with fixed roles: opening, closing, the ceiling.

The addressing that makes this possible is pinned in `test_addressing.py`; this
file is about the layer above it, where a session owns browsers and has to say
how many, which one, and what happens when one is closed.

⛔ THE CEILING IS A DECISION AND THE TESTS TREAT IT AS ONE. It was eight and
eight was measured - 61 processes, 6.5 GB, the eighth taking twice as long to
start as the first - and none of that stopped being true. What changed is that
a session IS an identity, `main`, with one helper beside it, `support`, for
what must not touch that identity. So the refusal carries the way OUT rather
than the cost, and one test reads it.

No browser starts here. The registry gets a factory that launches nothing, so
what a tool did is observable as the keys the registry ends up holding.
"""
from __future__ import annotations

import json

import pytest

from aihawk.mcp import server
from aihawk.mcp.registry import DEFAULT_SESSION_ID, SessionRegistry


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


@pytest.fixture
def registry(monkeypatch):
    # The server's own constructor, not a bare one: a test that builds a
    # registry the product does not have is testing something else, and the
    # wiring that writes a session down would be exercised by nothing. Missed
    # here when the file was reconstructed after the checkout was deleted.
    reg = server.new_registry(factory=_Recording,
                              defaults=lambda: {"seed": 7, "headless": True})
    monkeypatch.setattr(server, "registry", reg)
    # The focus is module state, so a test that set it must not reach the next.
    monkeypatch.setattr(server, "_focus", {})
    return reg


async def test_the_helper_is_its_own_browser_and_not_the_identity(registry):
    """Opening the helper ADDS a browser beside the identity rather than
    replacing it, and the two share nothing - which is the whole reason the
    helper is a browser and not another tab. A tab would carry the identity's
    cookies and fingerprint onto the temp-mail site, and then the site the
    account is being made on and the site the verification arrives at are one
    person.

    Known-bad: `browser_open` calling `restart` on `main` whatever the role
    says, which reads like opening a helper and behaves like throwing the
    identity away.
    """
    await server.browser_open()
    await server.browser_open(browser="support")

    assert server.browsers_in() == ["main", "support"]
    assert registry.peek("default/main") is not registry.peek("default/support"), (
        "the helper and the identity are one browser, so the helper carries "
        "the identity's cookies")


async def test_opening_the_helper_does_not_move_where_commands_go(registry):
    """⛔ THIS TEST USED TO ASSERT THE OPPOSITE AND WAS RIGHT THEN. While a
    session could hold eight browsers under names a caller invented, opening
    one made it where unaddressed commands went, or every later call would have
    had to repeat its id.

    There are two fixed roles now, and a command is about `main` unless it says
    `support` - every time, on every tool. Opening the helper must NOT quietly
    redirect the next command into it: that is the shape where an instruction
    meant for the account lands in the temporary mailbox, and nothing raises.

    Known-bad: put `_focus[at_session] = role` back into `browser_open`.
    """
    await server.browser_open(browser="support")

    assert server.focused() == server.DEFAULT_BROWSER_ID
    assert server.addressed() == "default/main", (
        "opening the helper moved where an unaddressed command lands")
    assert server.addressed(browser_id=server.SUPPORT_BROWSER_ID) == "default/support"


async def test_a_third_browser_is_refused_and_the_refusal_says_where_to_go(registry):
    """A session is one identity plus one helper, and the refusal has to carry
    the way out.

    ⛔ THE REFUSAL USED TO CARRY A COST - 61 processes, 6.5 GB - because the
    ceiling was eight and eight was a measurement, and a refusal that only says
    "no" invites the reader to raise the number. The ceiling is two now and it
    is a DECISION, so what it must carry changed with it: not what a ninth
    browser would cost, but what to do instead. A model told only "no" spends a
    turn trying the same thing again.

    Written as a loop over the constant rather than against the number two, so
    it goes on testing the rule if the number ever moves.

    Known-bad, two: drop the ceiling guard, and a third browser is opened; cut
    the refusal down to "limit reached", and the model is left with nowhere to
    go.
    """
    for role in ("main", "support"):
        await server.browser_open(browser=role)
    held = server.browsers_in()
    assert len(held) == server.MAX_BROWSERS_PER_SESSION

    said = await server.browser_open(browser="one-too-many")

    assert server.browsers_in() == held, "a third browser was opened anyway"
    assert "session_start" in said, (
        "the refusal does not name what to do instead, so the next turn is "
        "another try at the same thing: %r" % said)


async def test_closing_forgets_who_that_browser_was(registry):
    """⛔ The difference between `drop` and `forget`, at the tool level.

    `drop` is recovery and keeps the identity so the replacement is the same
    person. Closing is deliberate, and a browser that came back wearing an
    identity its owner had shut down would hand the next caller somebody they
    never asked for.

    Known-bad: `browser_close` calling `registry.drop` instead of
    `registry.forget`. The configuration then survives and the next browser
    under that name is the same person resumed.
    """
    await server.browser_open(browser="support", seed=4242)
    assert registry.config("default/support") is not None

    await server.browser_close(browser="support")

    assert server.browsers_in() == []
    assert registry.config("default/support") is None, \
        "the closed browser's identity is still remembered"


async def test_closing_the_focused_one_does_not_leave_commands_pointing_at_it(registry):
    """Known-bad: leaving `_focus` alone on close. Every later command then
    addresses a browser that is gone, and the registry quietly starts a new one
    under that name - a stranger wearing the name of somebody deliberately shut
    down.
    """
    await server.browser_open(browser="support")
    await server.browser_close(browser="support")

    assert server.focused() == server.DEFAULT_BROWSER_ID
    assert server.addressed() == "default/%s" % server.DEFAULT_BROWSER_ID


async def test_two_sessions_do_not_share_their_browsers(registry):
    """The session is the container, so its browsers are its own.

    ⛔ AND IT IS A SHARPER TEST THAN IT WAS. Both sessions' browsers are called
    `main` now, so the NAME cannot tell them apart: the session is the only
    half of the key that can, which is exactly the half this is about.

    Known-bad: have `addressed` ignore `session_id`. Both callers then share one
    browser, which is one person's cookie jar handed to another.
    """
    await server.browser_open(session_id="work")
    await server.browser_open(session_id="home")

    main = server.DEFAULT_BROWSER_ID
    assert server.browsers_in("work") == [main]
    assert server.browsers_in("home") == [main]
    assert server.addressed("work") == "work/%s" % main
    assert server.addressed("home") == "home/%s" % main
    assert registry.peek("work/%s" % main) is not registry.peek("home/%s" % main), (
        "two sessions were served by one browser")


async def test_the_count_is_read_from_the_registry_and_not_from_a_second_list(registry):
    """What frees a role is the registry forgetting a browser, and nothing else.

    ⛔ THE TWO HALVES ARE THE `drop`/`forget` DISTINCTION, COUNTED. A `drop` is
    what a failed retry does: the engine is gone, the person is not, and the
    next command aimed at that role brings the SAME browser back with its seed,
    its exit and its profile. So it still holds its role. Only `forget`, which
    is what closing does, gives the role back, because after it there is nobody
    left to come back.

    Known-bad, and it is the reason this is phrased about the SOURCE of the
    count rather than about either verb: keep the browsers in a list beside the
    registry. The list has no idea what `forget` did, so the second half goes
    red - a role whose browser was deliberately closed stays taken forever.
    """
    await server.browser_open()
    await server.browser_open(browser="support")
    assert server.browsers_in() == ["main", "support"]

    await registry.drop("default/support")

    assert "support" in server.browsers_in(), (
        "a browser whose engine died stopped being one of the session's "
        "browsers, so the identity it comes back as is now nobody's")

    await registry.forget("default/support")

    assert server.browsers_in() == ["main"], (
        "a browser that was deliberately forgotten is still one of the "
        "session's, so the next helper would wear its identity")


async def test_asking_what_a_session_holds_starts_nothing(registry):
    """A list that starts a browser is a list that cannot be asked casually,
    and the interface asks it to draw its panes.

    Known-bad: `browser_list` calling `ensure` instead of `peek`.
    """
    said = await server.browser_list()

    assert registry.ids() == [], "asking what a session holds started a browser"
    # ⛔ ON THE SHAPE, NOT ON A SUBSTRING. This asserted `"no browser open yet"
    # in said` and stayed green through the change from prose to JSON, because
    # the sentence survived inside the `note` field: an assertion that passes on
    # both answers a tool can give is not checking the answer. Same family as
    # the 0.16.1 defect, caught this time before it shipped.
    answer = json.loads(said)
    assert answer["browsers"] == []
    assert answer["limit"] == server.MAX_BROWSERS_PER_SESSION
    assert "no browser open yet" in answer["note"]


async def test_the_helper_goes_out_through_the_same_exit_as_the_identity(registry):
    """⛔ SAME EXIT, DIFFERENT PERSON. The helper exists to do things the
    identity must not be connected to - collect a verification, look something
    up - so its fingerprint is its own. Its ADDRESS is not: a helper coming out
    of a different exit than the browser it is helping is the one thing on the
    wire that says these two are not the same person and yet are working
    together, which is exactly the inference the helper exists to prevent.

    Inherited only when the caller says nothing. An explicit `proxy` is a
    decision and beats it.

    ⛔ AND THE ABSENCE IS INHERITED TOO. A `main` that goes out direct has no
    `proxy` at all, so the helper must go out direct as well rather than pick
    up an environment proxy `main` never used - which would be the same leak
    with the roles reversed.

    Known-bad, three: drop the inheritance and the helper takes the
    environment's exit; copy it even when the caller passed one, and an
    explicit decision is silently overridden; copy the key without checking
    `main` has one, and a direct `main` gives the helper a `None` exit that is
    not the environment's either.
    """
    await server.browser_open(proxy="socks5://10.0.0.1:1080")
    mine = registry.peek("default/main").kwargs["proxy"]

    await server.browser_open(browser="support")

    helper = registry.peek("default/support").kwargs
    assert helper.get("proxy") == mine, (
        "the helper came out of a different exit than the identity it helps: "
        "%r against %r" % (helper.get("proxy"), mine))
    assert helper.get("seed") != registry.peek("default/main").kwargs.get("seed"), (
        "the helper wears the identity's fingerprint, so the two read as one "
        "browser however separate their cookies are")

    await server.browser_open(browser="support", proxy="socks5://10.0.0.9:1080")
    told = registry.peek("default/support").kwargs["proxy"]
    assert told != mine, (
        "an explicit exit for the helper was overridden by the identity's: %r"
        % (told,))
