import pytest
from mcp import ClientSession
from mcp.client.stdio import stdio_client

from aihawk.mcp import store

from _stdio_helpers import server_params


@pytest.mark.asyncio
async def test_stdio_lists_tools():
    async with stdio_client(server_params()) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            names = {t.name for t in (await mcp.list_tools()).tools}
            assert {"browser_navigate", "browser_take_screenshot"} <= names


async def _open_main(session_id):
    """Spawn a real server told which piece of work it is, open its own
    browser, and hand back what it was declared with."""
    params = server_params({"AIHAWK_SESSION_ID": session_id})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            await mcp.call_tool("browser_open", {"seed": 4242})


@pytest.mark.asyncio
# ⛔ AND `e2e`, BECAUSE `browser_open` STARTS A REAL ENGINE. That is what the
# marker means, and this test was missing it: measured 2026-09-11, the two
# servers below downloaded and extracted 665 MB of Firefox and launched it,
# in the fast job whose contract is that it has no engine. Green here in
# thirty seconds because the engine was already on this machine; on CI it hung
# the whole suite to the six-hour ceiling, three pushes running, reported as
# `in_progress` rather than as a failure. The `e2e` job runs it with the
# engine named, which is where a test that needs one belongs.
@pytest.mark.e2e
async def test_two_real_processes_with_two_session_ids_persist_to_two_files():
    """⛔ THE BLACK-BOX PROOF THAT `AIHAWK_SESSION_ID` ACTUALLY WORKS, with real
    subprocesses rather than a monkeypatched module attribute. This is the
    ONLY place a second session id can still be reached from outside this
    process at all: not a tool argument any MCP client can send, but an
    environment variable whoever SPAWNS the process sets, exactly like
    `STEALTHFOX_SEED` a few lines above it in `mcp/server.py`.

    Known-bad: read `AIHAWK_SESSION_ID` into a name that collides with another
    env var, or key the saved file by anything else. Both files would then be
    the same file, or the wrong one.
    """
    await _open_main("work")
    await _open_main("home")

    saved_work = store.load("work")
    saved_home = store.load("home")
    assert saved_work is not None and saved_home is not None, (
        "one process's file overwrote the other's: work=%r home=%r"
        % (saved_work, saved_home))
    assert saved_work["browsers"]["main"]["seed"] == 4242
    assert saved_home["browsers"]["main"]["seed"] == 4242
    assert saved_work is not saved_home
