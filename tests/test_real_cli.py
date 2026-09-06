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
    from aihawk.agent import run_task
    from aihawk.link import Link
    from aihawk.llm import make_client, resolve_model

    key = os.environ["OPENROUTER_API_KEY"]
    link = await Link({"binary": os.environ["STEALTHFOX_BINARY"]}, key=key).open()
    try:
        answer = await run_task(
            link.session,
            "Open data:text/html,<h1>hello-cli</h1> and tell me the exact text "
            "of the h1.",
            client=make_client(key),
            model=resolve_model(None, os.environ),
        )
    finally:
        await link.close()

    assert "hello-cli" in answer.lower(), answer
