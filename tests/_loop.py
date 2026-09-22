"""What the suite needs to drive the agent loop, kept in the suite.

⛔ THESE FOUR LINES WERE PUBLIC API. `agent.run_task` lived in the product and
its own docstring said what it was: "not called by the product - kept because
the suite drives the loop through it, about twenty-five tests". It was a second
way to run the loop, and the second way is the one nobody ships.

It was worse than an unused function. It took an `mcp` object with `.list_tools()`
and `.call_tool()`, which is the shape the product used before `Link` existed;
the product passes `link.call` and `link.tools` to `Conversation.run` directly.
So a reader of `agent.py` met two entry points with two different ideas of how
tools are reached, and only one of them was real.

The convenience was genuine, so it moved here rather than being deleted: the
call sites in the tests are unchanged, and the product now has exactly one way
to run a turn.
"""
from __future__ import annotations

from invisible_playwright_mcp.agent import Conversation


async def run_task(mcp, task: str, *, client, model: str,
                   max_tokens: int = Conversation.MAX_TOKENS) -> str:
    """One instruction, one answer, no narration - for a test double that
    speaks the MCP session shape rather than the `Link` shape."""
    tools = (await mcp.list_tools()).tools
    convo = Conversation(client, model, max_tokens=max_tokens)
    return await convo.run(task, mcp.call_tool, tools)
