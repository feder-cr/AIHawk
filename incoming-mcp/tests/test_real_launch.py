"""Gated integration tests: drive a REAL patched Firefox binary, both in
ephemeral mode (Browser + new_context, the common path) and in persistent
-context mode (profile_dir set, the exact path C1 crashed on). Also drives
the stdio MCP server end to end once, to confirm a screenshot tool call
actually returns image content and not text.

Skipped unless STEALTHFOX_BINARY points at a real patched Firefox build.
Real browser launches are slow: timeouts here are generous on purpose.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

from invisible_playwright_mcp.session import StealthSession

BINARY = os.environ.get("STEALTHFOX_BINARY")

pytestmark = pytest.mark.skipif(
    not BINARY, reason="set STEALTHFOX_BINARY to a real patched Firefox binary to run this"
)


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_ephemeral_launch_navigate_and_screenshot():
    s = StealthSession(binary_path=BINARY, headless=True)
    await s.start()
    try:
        await s.new_page()
        await s.page().goto(
            "data:text/html,<h1>ok-ephemeral</h1>", timeout=45_000
        )
        text = await s.page().evaluate("() => document.body.innerText")
        assert "ok-ephemeral" in text
        png = await s.page().screenshot()
        assert len(png) > 0
    finally:
        await s.close()


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_persistent_context_launch_is_the_c1_path():
    """This is exactly the path C1 crashed on: __aenter__() returns a
    BrowserContext (no .new_context()) when profile_dir is set."""
    with tempfile.TemporaryDirectory(prefix="stealthfox-mcp-profile-") as profile_dir:
        s = StealthSession(binary_path=BINARY, headless=True, profile_dir=profile_dir)
        await s.start()
        try:
            await s.new_page()
            await s.page().goto(
                "data:text/html,<h1>ok-persistent</h1>", timeout=45_000
            )
            text = await s.page().evaluate("() => document.body.innerText")
            assert "ok-persistent" in text
        finally:
            await s.close()


@pytest.mark.asyncio
@pytest.mark.timeout(150)
async def test_stdio_drive_screenshot_is_image_content():
    """Realness check (rule 12): drive the browser via the MCP tools over
    the real stdio server, not just via the library API, and confirm the
    screenshot tool actually returns image bytes."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import ImageContent

    env = dict(os.environ)
    env["STEALTHFOX_BINARY"] = BINARY
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "invisible_playwright_mcp"], env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            await client.call_tool("session_new_page", {})
            await client.call_tool(
                "browser_navigate", {"url": "data:text/html,<h1>ok-stdio</h1>"}
            )
            read_result = await client.call_tool(
                "browser_read_text", {"selector": "body"}
            )
            assert "ok-stdio" in read_result.content[0].text

            shot_result = await client.call_tool("browser_take_screenshot", {})
            assert len(shot_result.content) == 1
            assert isinstance(shot_result.content[0], ImageContent)
            assert shot_result.content[0].data  # non-empty base64 image payload
