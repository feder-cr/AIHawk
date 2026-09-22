"""A real browser, a real model, and one factual question about a page.

The loop, given a real browser and a real model, reads a page and answers
what is on it - the whole product in one assertion. It opens the same `Link`
the interface opens and runs the same loop the interface runs; the CLI wiring
around that is covered without a browser or a key in test_cli_surface.py.

Skipped unless both a real binary and a real key are present, because it spends
money and launches Firefox.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    not (os.environ.get("STEALTHFOX_BINARY") and os.environ.get("OPENROUTER_API_KEY")),
    reason="needs STEALTHFOX_BINARY + OPENROUTER_API_KEY (real browser + LLM)",
)


async def test_the_loop_reads_a_data_url_heading():
    from invisible_playwright_mcp.agent import Conversation
    from invisible_playwright_mcp.link import Link
    from invisible_playwright_mcp.llm import make_client, resolve_model

    key = os.environ["OPENROUTER_API_KEY"]
    link = await Link({"binary": os.environ["STEALTHFOX_BINARY"]}, key=key).open()
    try:
        # The canonical path, which is the one the product takes: the
        # conversation is handed `link.call` and `link.tools`. This used to
        # reach PAST the Link for `link.session` and drive the raw MCP
        # session shape through `agent.run_task`, so the one end-to-end
        # test of the loop exercised an entry point the product does not
        # have - and the wrapper it exists to go through was stepped over.
        convo = Conversation(make_client(key), resolve_model(None, os.environ))
        answer = await convo.run(
            "Open data:text/html,<h1>hello-cli</h1> and tell me the exact text "
            "of the h1.",
            link.call, link.tools, instructions=link.instructions,
        )
    finally:
        await link.close()

    assert "hello-cli" in answer.lower(), answer
