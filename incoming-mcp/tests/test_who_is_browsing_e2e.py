"""The identity tools, driven through the protocol with a real browser.

⛔ EVERYTHING ELSE ABOUT THIS FEATURE IS TESTED WITHOUT A BROWSER, and that was
the gap. `plan_session` is a pure function and the registry takes a stand-in, so
both are covered fast and offline - which is why they were written that way. But
nothing had ever asked the question that matters: does the seed a caller passes
actually reach the engine and change what a page sees?

A test that only asks "did it launch" cannot tell a working identity from a
constant one. So the shape here is the one this project calls realness rather
than absence:

  * the SAME seed twice must produce the SAME fingerprint, and
  * a DIFFERENT seed must produce a DIFFERENT one.

The second half is what makes the first meaningful. A build that ignored the seed
entirely would pass determinism perfectly and fail here, and a build that
randomised every launch would fail the first. Neither could pass both.

Skipped unless a real binary is present, because it launches Firefox three times.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.environ.get("STEALTHFOX_BINARY"),
        reason="set STEALTHFOX_BINARY to a real patched Firefox to run this",
    ),
]

#: What the page is asked about. Every one of these is decided by the seed, and
#: together they are wide enough that two identities cannot collide by luck the
#: way a single integer could.
FINGERPRINT_JS = """() => JSON.stringify({
  hardwareConcurrency: navigator.hardwareConcurrency,
  deviceMemory: navigator.deviceMemory,
  width: screen.width,
  height: screen.height,
  dpr: window.devicePixelRatio,
  platform: navigator.platform,
})"""


def _text(result) -> str:
    return "".join(c.text for c in result.content if getattr(c, "text", None))


async def _fingerprint(mcp) -> dict:
    await mcp.call_tool("browser_navigate", {"url": "about:blank"})
    raw = _text(await mcp.call_tool("browser_evaluate", {"expression": FINGERPRINT_JS}))
    # evaluate returns the value JSON-encoded, and the value is itself a JSON
    # string, so it comes back doubly encoded.
    return json.loads(json.loads(raw))


def _server():
    """The server under test is THIS checkout, not whatever is installed.

    ⛔ `pythonpath` in the pytest config does not reach here. The server runs as
    a SUBPROCESS, and a subprocess gets its own sys.path, so without this the
    test drives the copy in site-packages while standing in the checkout - the
    same defect `pythonpath` was added to close, one layer further out.

    It passed anyway when this was written, because the venv in use happened to
    hold an editable install pointing at this tree. That is luck of the venv,
    not a property of the test, and on a machine with an ordinary install the
    mutations that validated this file would have gone uncaught.
    """
    env = dict(os.environ)
    env.setdefault("STEALTHFOX_HEADLESS", "1")
    src = str(pathlib.Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return StdioServerParameters(
        command=sys.executable, args=["-m", "invisible_playwright_mcp"], env=env)


async def test_the_seed_decides_what_the_page_sees():
    """⛔ THE LOAD-BEARING ONE, and it needs both halves to mean anything.

    Same seed twice, then a different seed. A build that ignored the seed passes
    the first comparison and fails the second; one that randomised every launch
    fails the first. Only a working identity passes both.
    """
    async with stdio_client(_server()) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()

            first = _text(await mcp.call_tool("session_start", {"seed": 4242}))
            assert "4242" in first, first
            first_run = await _fingerprint(mcp)

            _text(await mcp.call_tool("session_start", {"seed": 4242}))
            same_seed_again = await _fingerprint(mcp)

            _text(await mcp.call_tool("session_start", {"seed": 987654}))
            other_seed = await _fingerprint(mcp)

    assert first_run == same_seed_again, (
        "the same seed produced two identities, so the seed is not deciding: "
        "%r then %r" % (first_run, same_seed_again))
    assert first_run != other_seed, (
        "two different seeds produced the SAME identity, so the seed reaches "
        "nothing: %r" % (first_run,))


async def test_status_reports_the_person_actually_browsing():
    """Not just that it answers: that what it answers matches the engine.

    The seed in the sentence has to be the seed the page is running under, or
    `session_status` is a label rather than a reading.
    """
    async with stdio_client(_server()) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()

            before = _text(await mcp.call_tool("session_status", {}))
            assert "no browser is running" in before, before

            _text(await mcp.call_tool("session_start", {"seed": 31337}))
            after = _text(await mcp.call_tool("session_status", {}))
            fingerprint = await _fingerprint(mcp)

    assert "31337" in after, after
    assert "headless" in after
    assert fingerprint["width"] > 0, "the page answered nothing usable: %r" % (fingerprint,)


async def test_a_profile_keeps_its_person_across_two_sessions(tmp_path):
    """The coupling the whole module exists for, end to end.

    A profile is asked for because somebody wants to stay logged in. If the seed
    is redrawn each visit the same cookie jar comes back wearing different
    hardware, which is a stronger signal than either half alone. Here that is
    checked against what the PAGE sees rather than against the file on disk.
    """
    profile = str(tmp_path / "person")

    async with stdio_client(_server()) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            _text(await mcp.call_tool("session_start", {"profile": profile}))
            before = await _fingerprint(mcp)

            _text(await mcp.call_tool("session_start", {"profile": profile}))
            after = await _fingerprint(mcp)

    assert before == after, (
        "the same profile came back on different hardware: %r then %r"
        % (before, after))
