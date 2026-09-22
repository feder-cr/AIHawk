"""A connection is opened and closed by the same task, and closing one never
reaches into the task that opened it.

⛔ IT DID, AND IT KILLED THE INTERFACE. `Link.open` called `__aenter__` on
`stdio_client` and on `ClientSession` by hand, and `Link.close` called
`__aexit__` on them - from whatever task happened to be closing. Both are
anyio context managers, so each one owns a cancel scope, and a cancel scope has
to be exited in the task that entered it. Exiting it elsewhere delivers the
cancellation to the scope that ENCLOSES the entering task.

For the interface that is fatal in one exact case, and it is a case a person
can reach from the page. `cli.serve` opens the default conversation and then
runs uvicorn IN THE SAME TASK:

    default = await sessions.get(DEFAULT_CHAT_ID)
    ...
    await server.serve()

so pressing delete on that conversation - the sessions panel lists it with its
own `x` - closed its link from a request task, the cancellation landed on
`serve()`, and the whole interface exited 1. Measured over plain HTTP, no
browser: deleting any other conversation left it alive, deleting the default
killed it.

⛔ AND THE OTHER CONVERSATIONS WERE NOT FINE - THEY WERE QUIET. Their scopes
belong to request tasks that have already finished, so the same wrong exit
raises a `RuntimeError` that `Link.close` was swallowing by design, for a
reason written about teardown failures rather than about this. Every close was
wrong; exactly one of them had something alive to damage. A fix that only made
the default lazy would have removed the visible half and kept the defect.

So the connection now has an OWNER: one task opens it, publishes it, waits to
be told to stop, and closes it itself. Closing from another task is not
guarded against - it is made impossible, because no other task ever holds the
contexts.

These tests spawn the real server over stdio, because the defect is about task
ownership of a real transport and a double cannot have it.
"""
from __future__ import annotations

import asyncio

import pytest

from invisible_playwright_mcp.link import Link

from _stdio_helpers import server_params  # noqa: F401  (imported for its path setup)


def _link() -> Link:
    """A link to the real server, with the same options the product uses."""
    return Link({})


async def test_closing_from_another_task_does_not_disturb_the_opener():
    """⛔ THE KNOWN-BAD, IN THE SHAPE THE INTERFACE HAS. The opener goes on
    doing something afterwards - here a sleep, there uvicorn's main loop - and
    a different task closes the connection. The opener must be untouched.

    To watch this fail, put the `__aenter__` calls back in `open` and the
    `__aexit__` calls back in `close`: the sleep below dies with a
    `CancelledError` raised from a scope this task never entered.
    """
    link = await _link().open()
    still_running = []

    async def the_one_that_opened():
        # Stands in for `await server.serve()`: the task that opened the
        # connection stays alive and doing something.
        await asyncio.sleep(1.5)
        still_running.append(True)

    async def the_one_that_closes():
        await asyncio.sleep(0.3)
        await link.close()

    # ⛔ `gather` and not a bare await: the point is that the two run in
    # DIFFERENT tasks, which is what the interface does and what a single
    # coroutine would not reproduce.
    await asyncio.gather(the_one_that_opened(), the_one_that_closes())

    assert still_running == [True], (
        "the task that opened the connection was cancelled by somebody else "
        "closing it")


async def test_the_opener_survives_even_when_it_is_the_one_holding_the_scope():
    """The same thing said the other way round, and it is the interface's own
    shape: the opener opens FIRST and then blocks for a long time, so its scope
    is alive for the whole of the close."""
    opened: list = []
    ended: list = []

    async def owner_task():
        link = await _link().open()
        opened.append(link)
        try:
            await asyncio.sleep(2.0)
            ended.append("whole")
        except asyncio.CancelledError:
            ended.append("CANCELLED")
            raise

    async def closes_from_outside():
        while not opened:
            await asyncio.sleep(0.05)
        await asyncio.sleep(0.2)
        await opened[0].close()

    await asyncio.gather(owner_task(), closes_from_outside())
    assert ended == ["whole"], (
        "closing the connection from another task cancelled the task that "
        "opened it: %r" % ended)


async def test_an_open_connection_ANSWERS_until_it_is_closed():
    """⛔ THE CONTROL ARM, AND IT WAS MISSING: a known-bad that made the owner
    stop waiting - so the connection closed itself the instant after it was
    published - SURVIVED every other test in this file. They all opened a link
    and never asked it anything, so a link that was already dead read exactly
    like a live one.

    Calling a tool is what tells the two apart, and `browser_list` is the one
    to call because it starts nothing: it answers what is held.
    """
    link = await _link().open()
    try:
        first = await link.call_text("browser_list")
        assert first, "an open connection answered nothing"
        # And it is still answering while somebody else is busy, because the
        # owner's job is to hold it open across other work.
        await asyncio.sleep(0.5)
        again = await link.call_text("browser_list")
        assert again, "the connection stopped answering while nobody closed it"
    finally:
        await link.close()


async def test_a_connection_that_was_closed_says_so_instead_of_answering():
    """Closing has to actually close. A link whose owner has gone must refuse a
    call rather than hand back a session that cannot reach anything."""
    link = await _link().open()
    assert link.tools, "nothing was listed, so this proves nothing"
    await link.close()

    with pytest.raises(RuntimeError, match="not open"):
        link.session


async def test_closing_twice_is_not_an_error():
    """Shutdown paths close what they hold, and more than one of them can hold
    the same link: `close_all` at exit and `forget` on a conversation."""
    link = await _link().open()
    await link.close()
    await link.close()


class _ChildThatDies(Link):
    """A link whose child exits at once. Only `_params` differs, so everything
    about the lifetime under test is still the product's."""

    def _params(self):
        import sys as _sys

        from mcp import StdioServerParameters as _P
        return _P(command=_sys.executable, args=["-c", "raise SystemExit(3)"], env={})


async def test_an_open_that_fails_reports_it_and_leaves_nothing_running():
    """⛔ AN OWNER THAT OUTLIVES A FAILED OPEN IS A PROCESS NOBODY WILL CLOSE,
    and a failure before the connection was usable belongs to `open` rather
    than to whoever closes: it is the difference between being told the server
    did not start and a page that waits for one that never will.

    To watch this fail, drop the `set_exception` in `_hold`: `open` then waits
    on a future nobody will ever complete.
    """
    before = len(asyncio.all_tasks())

    with pytest.raises(BaseException) as caught:
        await asyncio.wait_for(_ChildThatDies({}).open(), timeout=20)

    # ⛔ AND IT MUST NOT BE THE TIMEOUT, WHICH IS THE WHOLE POINT. A known-bad
    # that removed the `set_exception` SURVIVED this test until this line
    # existed: `open` then waited on a future nobody would complete, the
    # `wait_for` fired, and `pytest.raises(BaseException)` accepted the very
    # hang the test is here to forbid. An assertion that cannot tell "it
    # reported" from "it never answered" is not asserting anything.
    assert not isinstance(caught.value, asyncio.TimeoutError), (
        "open did not report the failure, it hung until the test gave up")

    await asyncio.sleep(0.3)
    assert len(asyncio.all_tasks()) <= before, (
        "a failed open left its owner task running")
