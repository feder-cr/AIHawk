"""One conversation gets one server, however many requests arrive at once.

⛔ IT GOT ONE PER REQUEST, AND THE DEFECT IS A CHECK-THEN-ACT ACROSS AN AWAIT.
`Sessions.get` looked in `_live`, found nothing, awaited `_open_link` - which
spawns `python -m invisible_playwright_mcp` and shakes hands with it - and only then wrote the
service into `_live`. Every request that arrived inside that window found
nothing too, and spawned its own.

Measured through the seam this class declares for exactly this purpose, with an
`open_link` that takes half a second: SIX concurrent calls for ONE conversation
opened SIX connections and returned SIX DISTINCT services.

The process leak is the smaller half. The larger half is that a conversation is
a piece of STATE - a transcript, whether a run is in flight, the listeners an
open page is subscribed to - and six services for one conversation means six
copies of it. A page handed a losing service watches a conversation that will
never advance, because the events are emitted on a different object. And
`close_all` iterates `_live.values()`, so it closes the one that won and cannot
close what it never learned about.

The page produces the concurrency without trying: opening a saved conversation
fires `/chat/events`, `/live/browsers`, `/live/frame` and `/sessions` at once,
and after a restart none of them is live. It did not reproduce over HTTP on an
idle machine, because the window is only as wide as the spawn is slow - which
is why it is measured here, where the spawn's duration is a parameter, and not
by hoping a production race fires.
"""
from __future__ import annotations

import asyncio

import pytest

from invisible_playwright_mcp.sessions import Sessions


class _Link:
    """A connection that records nothing but its own closing."""

    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def _sessions(open_link):
    return Sessions({}, None, lambda: object(), open_link=open_link)


async def test_many_requests_at_once_open_ONE_connection():
    """⛔ THE KNOWN-BAD. To watch this fail, move `self._live[at] = service`
    back below the await without holding anything: the count becomes the number
    of callers.

    The sleep is what holds the window open. It is not a timing assertion -
    nothing here asserts how long anything took - it is the spawn's duration
    made into a parameter, because on an idle machine the real one is short
    enough to hide the window without closing it.
    """
    opened_for = []

    async def slow(session_id):
        opened_for.append(session_id)
        await asyncio.sleep(0.2)
        return _Link()

    sessions = _sessions(slow)
    services = await asyncio.gather(*[sessions.get("one") for _ in range(6)])

    assert len(opened_for) == 1, (
        "one conversation opened %d connections; %d of them are orphans that "
        "close_all cannot see" % (len(opened_for), len(opened_for) - 1))
    assert len({id(s) for s in services}) == 1, (
        "one conversation produced %d distinct services, so its transcript, "
        "its busy flag and its listeners are split across objects"
        % len({id(s) for s in services}))


async def test_different_conversations_still_get_their_own():
    """The control arm, and it is not a formality: a single lock around the
    whole of `get` would make this pass while collapsing nothing, but a lock
    that also keyed on nothing - or a registry that memoised the first service
    for every id - would satisfy the test above and break this one. One
    conversation, one server; two conversations, two."""
    opened_for = []

    async def slow(session_id):
        opened_for.append(session_id)
        await asyncio.sleep(0.2)
        return _Link()

    sessions = _sessions(slow)
    a, b = await asyncio.gather(sessions.get("uno"), sessions.get("due"))

    assert sorted(opened_for) == ["due", "uno"]
    assert a is not b
    assert a.session_id == "uno" and b.session_id == "due"


async def test_a_second_ask_after_it_is_open_costs_no_connection():
    """The fast path stays fast: a conversation already open is handed back
    without going near whatever guards the making of one."""
    opened_for = []

    async def counter(session_id):
        opened_for.append(session_id)
        return _Link()

    sessions = _sessions(counter)
    first = await sessions.get("one")
    again = await sessions.get("one")

    assert first is again
    assert len(opened_for) == 1


async def test_a_spawn_that_fails_does_not_poison_the_next_try():
    """⛔ A GUARD THAT REMEMBERS A FAILURE IS A CONVERSATION NOBODY CAN OPEN
    AGAIN. The first attempt raises - a proxy that is down, a binary that is
    not there - and the second must be allowed to make a real one, not to
    inherit the exception or wait on a dead promise."""
    attempts = []

    async def broken_once(session_id):
        attempts.append(session_id)
        if len(attempts) == 1:
            raise RuntimeError("the server did not start")
        return _Link()

    sessions = _sessions(broken_once)
    with pytest.raises(RuntimeError, match="did not start"):
        await sessions.get("one")

    service = await sessions.get("one")
    assert service is not None
    assert len(attempts) == 2


async def test_every_connection_it_opened_is_closed_on_shutdown():
    """⛔ THE LEAK, ASSERTED FROM THE OTHER END. Whatever `get` opens,
    `close_all` must close. With one connection per conversation this is
    simply true; it was not, and the ones it could not see were still holding
    a process and, if the agent had got that far, a browser."""
    links = []

    async def opener(session_id):
        # ⛔ THE SLEEP IS WHAT MAKES THIS ARM REAL. Without a suspension point
        # inside the opening, `get` runs to completion before the next caller
        # starts, the race never happens, and this passes on the very defect it
        # is here to catch.
        await asyncio.sleep(0.2)
        link = _Link()
        links.append(link)
        return link

    sessions = _sessions(opener)
    await asyncio.gather(*[sessions.get("one") for _ in range(4)])
    await sessions.get("two")
    await sessions.close_all()

    assert links, "nothing was opened, so this proves nothing"
    still_open = [n for n, link in enumerate(links) if not link.closed]
    assert not still_open, (
        "%d of %d connections survived the shutdown" % (len(still_open), len(links)))


async def test_two_new_conversations_at_once_are_two_conversations():
    """⛔ THE SAME DEFECT ONE METHOD ALONG, AND THE GUARD ON `get` DOES NOT
    COVER IT. `new` picked an id from the clock in milliseconds, found it free
    and then awaited: two callers in the same millisecond computed the SAME id,
    and a conversation being made is in neither `_live` nor on disk, so both
    found it free. The second was handed the first one's conversation - with
    its transcript.

    To watch this fail, put the id back outside the lock.
    """
    async def slow(session_id):
        await asyncio.sleep(0.2)
        return _Link()

    sessions = _sessions(slow)
    a, b = await asyncio.gather(sessions.new(), sessions.new())

    assert a.session_id != b.session_id, (
        "two new conversations share the id %r" % a.session_id)
    assert a is not b, "somebody who asked for a new conversation got another's"


async def test_a_new_conversation_is_reachable_by_its_own_id():
    """The other half: claiming an id is worth nothing if the conversation is
    not then findable under it."""
    async def opener(session_id):
        return _Link()

    sessions = _sessions(opener)
    made = await sessions.new()
    again = await sessions.get(made.session_id)
    assert again is made


async def test_deleting_while_one_is_being_opened_leaves_nothing_behind():
    """⛔ THE THIRD PLACE THE SAME ASSUMPTION LIVED. `forget` did not wait
    for a creation in flight, so a conversation being made registered itself
    into `_live` AFTER its files had been erased: alive, unreachable by name,
    and holding a process nobody would ever close.

    To watch this fail, take `forget` out from under the lock.
    """
    links = []

    async def slow(session_id):
        await asyncio.sleep(0.2)
        link = _Link()
        links.append(link)
        return link

    sessions = _sessions(slow)
    opening = asyncio.ensure_future(sessions.get("one"))
    await asyncio.sleep(0.05)          # the opening is in flight
    await sessions.forget("one")
    with __import__("contextlib").suppress(Exception):
        await opening

    assert "one" not in sessions._live, (
        "a conversation whose files were erased is still live")
    still_open = [n for n, link in enumerate(links) if not link.closed]
    assert not still_open, (
        "%d connection(s) opened for a deleted conversation were never closed"
        % len(still_open))


async def test_nobody_is_handed_a_conversation_whose_link_is_already_closed():
    """⛔ THE OTHER WINDOW IN THE SAME METHOD: the link was closed first and
    the service dropped after, so a request arriving between the two got a
    conversation that could not reach its browsers.

    To watch this fail, move the `pop` back below the `await`.
    """
    closed_while_still_reachable = []

    class _Watchful(_Link):
        def __init__(self, sessions):
            super().__init__()
            self.sessions = sessions

        async def close(self):
            # At the moment of closing, is the service still in the registry?
            if "one" in self.sessions._live:
                closed_while_still_reachable.append(True)
            await super().close()

    sessions = _sessions(lambda session_id: None)

    async def opened(session_id):
        return _Watchful(sessions)

    sessions._open_link = opened
    await sessions.get("one")
    await sessions.forget("one")

    assert not closed_while_still_reachable, (
        "the link was closed while the conversation was still in the registry, "
        "so a request in that window would get a service that cannot reach "
        "anything")
