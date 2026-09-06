import sys
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_stdio_lists_tools():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "invisible_playwright_mcp"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            names = {t.name for t in (await mcp.list_tools()).tools}
            assert {"browser_navigate", "browser_take_screenshot"} <= names
