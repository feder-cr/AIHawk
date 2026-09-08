"""A session holds several browsers: opening, closing, focusing, and the ceiling.

The addressing that makes this possible is pinned in `test_addressing.py`; this
file is about the layer above it, where a session owns browsers and has to say
how many, which one, and what happens when one is closed.

⛔ THE CEILING IS A MEASUREMENT AND THE TESTS TREAT IT AS ONE. Eight live
browsers were measured at 61 processes and about 6.5 GB on 2026-09-08, with the
eighth taking 13.6 s to start against the first one's 6.8. A refusal that only
said "no" would invite the next reader to raise the number, so the refusal
carries the cost and one test reads it.

No browser starts here. The registry gets a factory that launches nothing, so
what a tool did is observable as the keys the registry ends up holding.
"""
from __future__ import annotations

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
    reg = SessionRegistry(factory=_Recording,
                          defaults=lambda: {"seed": 7, "headless": True})
    monkeypatch.setattr(server, "registry", reg)
    # The focus is module state, so a test that set it must not reach the next.
    monkeypatch.setattr(server, "_focus", {})
    return reg


async def test_a_second_browser_is_its_own_browser(registry):
    """Opening one adds a browser rather than replacing the one there.

    Known-bad: `browser_open` calling `restart` on the focused key instead of
    the new one, which reads like opening and behaves like replacing.
    """
    await server.browser_open(browser_id="docs")
    await server.browser_open(browser_id="dash")

    assert server.browsers_in() == ["dash", "docs"]
    assert registry.peek("default/docs") is not registry.peek("default/dash")


async def test_the_one_just_opened_is_where_commands_go(registry):
    """Opening a browser to then address every command to it by hand would make
    the common case the tedious one.

    Known-bad: dropping the `_focus[...] = browser_id` line. The assertion on
    `addressed()` then still answers "main".
    """
    await server.browser_open(browser_id="docs")

    assert server.focused() == "docs"
    assert server.addressed() == "default/docs"
    # Naming one still reaches it whatever the focus is.
    assert server.addressed(browser_id="other") == "default/other"


async def test_the_ceiling_refuses_the_ninth_and_says_what_eight_cost(registry):
    """Eight is a measurement, and the refusal has to carry it.

    Known-bad, two of them: raising `MAX_BROWSERS_PER_SESSION` past eight, and
    a refusal reduced to "limit reached" - the second leaves the number looking
    arbitrary, which is how a ceiling gets raised by somebody who never saw
    what it cost.
    """
    for i in range(server.MAX_BROWSERS_PER_SESSION):
        await server.browser_open(browser_id="b%d" % i)
    assert len(server.browsers_in()) == 8

    said = await server.browser_open(browser_id="one-too-many")

    assert len(server.browsers_in()) == 8, "the ninth browser was opened anyway"
    assert "one-too-many" not in server.browsers_in()
    assert "6.5 GB" in said and "61 processes" in said, \
        "the refusal does not say what the ceiling costs: %r" % said


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
    await server.browser_open(browser_id="docs", seed=4242)
    assert registry.config("default/docs") is not None

    await server.browser_close(browser_id="docs")

    assert server.browsers_in() == []
    assert registry.config("default/docs") is None, \
        "the closed browser's identity is still remembered"


async def test_closing_the_focused_one_does_not_leave_commands_pointing_at_it(registry):
    """Known-bad: leaving `_focus` alone on close. Every later command then
    addresses a browser that is gone, and the registry quietly starts a new one
    under that name - a stranger wearing the name of somebody deliberately shut
    down.
    """
    await server.browser_open(browser_id="docs")
    await server.browser_close(browser_id="docs")

    assert server.focused() == server.DEFAULT_BROWSER_ID
    assert server.addressed() == "default/%s" % server.DEFAULT_BROWSER_ID


async def test_two_sessions_do_not_share_their_browsers_or_their_focus(registry):
    """The session is the container, so its browsers and its focus are its own.

    Known-bad: keeping the focus in one variable instead of one per session,
    which makes two sessions fight over where their commands land.
    """
    await server.browser_open(browser_id="docs", session_id="work")
    await server.browser_open(browser_id="mail", session_id="home")

    assert server.browsers_in("work") == ["docs"]
    assert server.browsers_in("home") == ["mail"]
    assert server.focused("work") == "docs"
    assert server.focused("home") == "mail"
    assert server.addressed("work") == "work/docs"
    assert server.addressed("home") == "home/mail"


async def test_the_count_is_read_from_the_registry_and_not_from_a_second_list(registry):
    """What frees a slot is the registry forgetting a browser, and nothing else.

    ⛔ THE TWO HALVES ARE THE `drop`/`forget` DISTINCTION, COUNTED. A `drop` is
    what a failed retry does: the engine is gone, the person is not, and the
    next command aimed at that name brings the SAME browser back with its seed,
    its exit and its profile. So it still holds its slot - eight slots that a
    dead engine vacated would let a session own nine identities and call it
    eight. Only `forget`, which is what closing a browser does, gives the slot
    back, because after it there is nobody left to come back.

    Known-bad, and it is the reason this test is phrased about the source of
    the count rather than about either verb: keep the browsers in a list beside
    the registry. The list has no idea what `forget` did, so the second half
    goes red - a slot whose owner was deliberately closed stays taken forever.
    """
    for i in range(server.MAX_BROWSERS_PER_SESSION):
        await server.browser_open(browser_id="b%d" % i)

    await registry.drop("default/b3")

    assert "b3" in server.browsers_in(), (
        "a browser whose engine died stopped being one of the session's "
        "browsers, so the identity it comes back as is now nobody's")
    refused = await server.browser_open(browser_id="one-too-many")
    assert "one-too-many" not in server.browsers_in(), (
        "a dead engine handed its slot away while its owner still had it: %r"
        % refused)

    await registry.forget("default/b3")

    assert "b3" not in server.browsers_in()
    said = await server.browser_open(browser_id="replacement")
    assert "replacement" in server.browsers_in(), \
        "a freed slot was still counted as taken: %r" % said


async def test_asking_what_a_session_holds_starts_nothing(registry):
    """A list that starts a browser is a list that cannot be asked casually,
    and the interface asks it to draw its panes.

    Known-bad: `browser_list` calling `ensure` instead of `peek`.
    """
    said = await server.browser_list()

    assert registry.ids() == [], "asking what a session holds started a browser"
    assert "no browser open yet" in said
