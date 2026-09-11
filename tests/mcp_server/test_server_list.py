import pytest


@pytest.mark.asyncio
async def test_server_registers_expected_tools():
    from aihawk.mcp import server
    tools = await server.mcp.list_tools()
    names = {t.name for t in tools}
    expected = {
        "browser_navigate", "browser_read_text",
        "browser_snapshot", "browser_read_html", "browser_click",
        "browser_click_at", "browser_type", "browser_press_key",
        "browser_evaluate", "browser_take_screenshot",
        # Added in 0.10.0. Its absence was not neutral: with no way to set a
        # dropdown, a model clicked it, pressed arrow keys blind, and ended up
        # injecting script to set the value - which changes the page without
        # it ever seeing a real interaction.
        "browser_select_option",
        # Added in 0.15.0: the window as a person sees it, pointer included,
        # from the engine's screencast. It exists because every image the
        # server returned was the content viewport, and the pointer is drawn
        # outside the page on purpose - so nobody watching could see it.
        "browser_watch",
        # Added in 0.15.0 with the rest of the multi-browser work: a session
        # held several browsers, so it needed a way to open one, close it, ask
        # what it holds, and say which one the unaddressed commands mean.
        "browser_open", "browser_close", "browser_list",
        # ⛔ RENAMED ON 2026-09-11, WHEN MCP STOPPED HAVING A SESSION CONCEPT AT
        # ALL: this process serves exactly one piece of work, told which by
        # `AIHAWK_SESSION_ID` at spawn time, never by a tool argument - so the
        # tools that used to say "session" now say "browser", because there is
        # no second one here to distinguish it from.
        #
        # `session_status` -> `browser_status`. `session_start` is GONE, folded
        # entirely into `browser_open`, which already had to open the FIRST
        # browser and only ever differed from a restart by name.
        #
        # ⛔ AND THE FOUR TAB TOOLS ARE GONE ENTIRELY (2026-09-11). They were
        # briefly renamed `browser_tab_*` to match Microsoft's Playwright MCP,
        # and then removed: a browser drives ONE page here, and the answer to
        # "I need a second page" is the `support` browser, which is a better
        # answer than a tab because a tab carries the identity's cookies and
        # fingerprint to the second site. Nothing replaced them - `browser_
        # navigate` opens the first page by itself.
        #
        # `session_list` and `session_forget` are GONE with no replacement:
        # enumerating or deleting another piece of work is precisely the
        # capability MCP no longer has. Listing THIS process's own two
        # browsers is still `browser_list`; deleting a whole piece of work is
        # done by whoever spawned this process closing it, not by a tool call.
        "browser_status",
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
