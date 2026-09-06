import pytest


@pytest.mark.asyncio
async def test_server_registers_expected_tools():
    from aihawk.mcp import server
    tools = await server.mcp.list_tools()
    names = {t.name for t in tools}
    expected = {
        "session_new_page", "session_list_pages", "session_select_page",
        "session_close_page", "browser_navigate", "browser_read_text",
        "browser_snapshot", "browser_read_html", "browser_click",
        "browser_click_at", "browser_type", "browser_press_key",
        "browser_evaluate", "browser_take_screenshot",
        # Added in 0.10.0. Its absence was not neutral: with no way to set a
        # dropdown, a model clicked it, pressed arrow keys blind, and ended up
        # injecting script to set the value - which changes the page without
        # it ever seeing a real interaction.
        "browser_select_option",
        # Added in 0.11.0, and they are one pair rather than two tools.
        # session_start chooses who is browsing; session_status is the only way
        # to ASK. Without the second, the identity was reported exactly once, in
        # the return value of a call the descriptions explicitly say you need
        # not make - so a model that skipped it, or whose browser was rebuilt
        # underneath it, had no way to find out who it had become.
        "session_start", "session_status",
        # Added in 0.15.0: the window as a person sees it, pointer included,
        # from the engine's screencast. It exists because every image the
        # server returned was the content viewport, and the pointer is drawn
        # outside the page on purpose - so nobody watching could see it.
        "browser_watch",
    }
    # EXACT, not a subset. `expected <= names` passed while a tool nobody
    # meant to publish sat in the list, and the surface of an MCP server is
    # exactly the thing a caller writes prompts against: it moves deliberately
    # or not at all.
    assert names == expected, {"missing": expected - names, "unexpected": names - expected}


@pytest.mark.asyncio
async def test_every_tool_description_is_english_and_ascii():
    """A tool description is not documentation, it is the prompt the model reads
    to decide whether to call the tool at all.

    The repository-wide language gate cannot protect this: it looks for PROSE,
    two Italian function words in the same file, and a one-line description is
    not prose. That limitation is real and documented, so the surface that
    matters most gets its own check rather than a longer word list, which would
    be chasing cases one at a time.
    """
    import importlib.util
    import pathlib
    import re

    from aihawk.mcp import server

    # The word list is IMPORTED from the repository gate rather than copied.
    # Copying it here had two costs at once: the list would drift from the one
    # that actually guards the repository, and this file, being a page of
    # Italian words, was itself flagged as Italian prose by that very gate.
    gate_path = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "check_english_only.py"
    spec = importlib.util.spec_from_file_location("_english_gate", gate_path)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    italian = gate.ITALIAN

    problems = {}
    for tool in await server.mcp.list_tools():
        text = tool.description or ""
        found = [w for w in italian if re.search(rf"\b{w}\b", text, re.I)]
        non_ascii = sorted({c for c in text if ord(c) > 127})
        if found or non_ascii:
            problems[tool.name] = {"italian": found, "non_ascii": non_ascii}
    assert not problems, problems


@pytest.mark.asyncio
async def test_every_tool_actually_has_a_description():
    """An undescribed tool is one the model will not choose, or will choose
    wrongly. Cheaper to assert than to debug from the other side."""
    from aihawk.mcp import server
    thin = {t.name: t.description for t in await server.mcp.list_tools()
            if not (t.description or "").strip()}
    assert not thin, thin
