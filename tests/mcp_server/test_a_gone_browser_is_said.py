"""A browser that REALLY dies says so, against a real engine.

⛔ THE SENTENCE A MODEL ACTS ON, PROVEN WHERE IT COMES FROM. `Work.acting`
turns a dead browser into `GONE`, and `test_open_first.py` proves that against
a stand-in whose `is_alive()` the test flips and whose action raises
`TargetClosedError` because the test made it. Neither of those is the thing
that happens in the world: what happens is that Firefox goes away - crashed,
or a window closed by hand - and what the wrapper raises then is a fact about
the wrapper, not about this package. Between the two halves, each tested
against a double, sat the join: if a killed engine surfaced as anything else,
every model driving this server would get a traceback where it needed an
instruction, and no test here would have moved.

So these kill the browser for real, and there are TWO of them because the
sentence has two paths and a killed process reaches them in a definite order.
Measured while writing this: with the engine ended from outside, an action
raises `TargetClosedError` and `acting` translates it - the aliveness check
does not fire first, and dropping it leaves the first test green. The second
test is the one that holds it, by asking a question that runs no action at
all. One path each, one mutation each.

⛔ AND THEY KILL ONLY WHAT THEY STARTED. This machine runs two Claude
sessions, each with its own MCP server and its own Firefox processes, and this
project has a rule about that written from an incident: record the pids that
are ALIVE before the launch and end only what was born after. Nothing else is
touched, and what these start is ended whether they pass or not.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import pytest

from invisible_playwright_mcp.mcp import GONE, NOT_OPEN, server

BINARY = os.environ.get("STEALTHFOX_BINARY")

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not BINARY or sys.platform != "win32",
                       reason="a real engine on Windows, where a process tree can be ended by pid"),
]


def _firefox_pids() -> set:
    """Every `firefox.exe` on this machine, by pid."""
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='firefox.exe'\" "
         "| Select-Object -ExpandProperty ProcessId"],
        capture_output=True, text=True)
    return {int(line) for line in out.stdout.split() if line.strip().isdigit()}


def _end(pids) -> None:
    for pid in pids:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % pid],
                       capture_output=True)


async def _open_and_kill(seed: int, before: set) -> None:
    """Open `main` on the real engine, put it on a page, and end the engine
    processes this started - and only those."""
    said = await server.browser_open(seed=seed)
    assert "seed %d" % seed in said, said
    mine: set = set()
    for _ in range(40):
        mine = _firefox_pids() - before
        if mine:
            break
        await asyncio.sleep(0.25)
    assert mine, "no engine process appeared, so nothing was really opened"
    await server.browser_navigate("data:text/html,<h1>alive</h1>")
    _end(mine)


async def _until_it_refuses(call) -> Exception:
    """What `call` finally raised, or nothing.

    The engine is ended from outside and the wrapper notices when its pipe
    goes, which is not instant. The window in which the browser is dead and
    the server has not noticed is exactly what these sentences exist for, so
    the wait is a bounded loop rather than a sleep.
    """
    for _ in range(40):
        try:
            await call()
        except Exception as raised:
            return raised
        await asyncio.sleep(0.25)
    return None


async def test_a_browser_killed_under_an_action_is_said_and_comes_back_as_the_same_person():
    """The path a killed engine actually takes: the action raises a closed
    target and `acting` turns it into the sentence.

    Known-bad: let `acting` re-raise instead, and the model gets `Target page,
    context or browser has been closed` where it needed an instruction.
    """
    before = _firefox_pids()
    try:
        await _open_and_kill(4242, before)

        told = await _until_it_refuses(
            lambda: server.browser_navigate("data:text/html,<h1>after</h1>"))

        assert told is not None, "the browser was killed and a navigation still succeeded"
        assert str(told) == GONE % "main", (
            "a killed engine reached the model as %r rather than as the sentence "
            "that tells it what to do" % str(told))

        # And it is forgotten, so the next open starts clean rather than
        # handing the same dead object out again.
        with pytest.raises(RuntimeError) as again:
            await server.browser_status()
        assert str(again.value) == NOT_OPEN % "main"

        await server.browser_open()
        assert "seed 4242" in await server.browser_status(), (
            "the browser that came back is not the person the session was")
    finally:
        await server.work.close_all()
        _end(_firefox_pids() - before)


async def test_a_browser_killed_between_calls_is_said_by_a_question_that_runs_nothing():
    """The other path, and the only one that can fire here: `browser_status`
    asks who is browsing and drives no page, so nothing raises a closed target
    - what notices is `session()` asking the browser whether it is still
    connected.

    Known-bad: drop the `is_alive()` check from `Work.session`. The test above
    stays green, because an action would still raise; this one goes red with
    the status answering as though the browser were there.
    """
    before = _firefox_pids()
    try:
        await _open_and_kill(31337, before)

        told = await _until_it_refuses(server.browser_status)

        assert told is not None, (
            "the browser was killed and the status still reported a person browsing")
        assert str(told) == GONE % "main", (
            "the status of a killed browser reached the model as %r" % str(told))
    finally:
        await server.work.close_all()
        _end(_firefox_pids() - before)
