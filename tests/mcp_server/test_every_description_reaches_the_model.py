"""Every tool description is read by the model in full, and the one about
`support` says who closes it.

The loop hands the API each tool's description cut at 1024 characters, because
a longer one is rejected rather than trimmed. `browser_open` was 1996: the model
read it ending mid-word inside the paragraph about profiles, and the sentence
that told it to close the helper was past the cut. Measured 2026-09-12 with the
real model, six runs of a task that needs both browsers, `support` left open in
six. No browser is started here: the descriptions are read from the server the
same way the loop reads them.
"""
from __future__ import annotations

import asyncio

from aihawk.agent import mcp_tools_to_openai
from aihawk.mcp import server

#: The API's ceiling, and the loop's cut. Written once here and once in the
#: loop, and this file is the one that says why.
LIMIT = 1024


def descriptions():
    tools = asyncio.run(server.mcp.list_tools())
    assert len(tools) >= 16, "found %d tools, so this is not looking at the server" % len(tools)
    return {t.name: (t.description or "") for t in tools}


def test_no_description_is_longer_than_the_model_can_read():
    """Known-bad: give any tool a description over the limit - the loop cuts
    it and nothing says so."""
    over = {n: len(d) for n, d in descriptions().items() if len(d) > LIMIT}
    assert not over, (
        "these descriptions are cut before the model reads them, and whatever "
        "is past the cut is a rule the model has never been told: %s" % over)


def test_the_loop_sends_what_the_server_wrote():
    """The cut in the loop is the fact the gate above defends; this holds that
    the two agree, so the limit cannot quietly move in one place."""
    tools = asyncio.run(server.mcp.list_tools())
    sent = {d["function"]["name"]: d["function"]["description"]
            for d in mcp_tools_to_openai(tools)}
    for name, description in descriptions().items():
        assert sent[name] == description, (
            "the model reads a different description of %s than the server "
            "wrote" % name)


def test_the_tool_that_opens_support_says_who_closes_it():
    """⛔ THE ONLY SENTENCE ABOUT CLOSING WAS PAST THE CUT. Now it is in the
    first paragraph, where a model that reads nothing else still meets it.

    Known-bad: move the sentence below the parameters again, or drop it.
    """
    text = descriptions()["browser_open"]
    first = text[:LIMIT // 2]
    assert "browser_close" in first and "support" in first, (
        "the description of browser_open does not say, early, that support is "
        "closed with browser_close: %r" % text[:200])
