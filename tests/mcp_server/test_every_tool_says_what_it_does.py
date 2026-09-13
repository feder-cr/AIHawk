"""Every tool tells a client, before it is called, whether it only reads.

A client decides from the annotations whether a call needs the person's
confirmation: a tool marked read-only runs on its own, one marked destructive
asks first, and one that says neither is treated as the worst case by careful
clients and as the best case by careless ones. A directory review refuses a
server whose tools carry no title or no hint, and that is where this was first
asked of us (2026-09-13) - but the reason to keep it is the confirmation
prompt, which is decided by these flags and by nothing else.

Read from the server the way a client reads them, over `list_tools`, so what
is asserted is what goes out on the wire. No browser is started. The check is a
function over the tool list, and a second test feeds it known-bad tools: one
with no annotations, one with no title, one saying nothing about what it
does, and one saying both things at once.
"""
from __future__ import annotations

import asyncio

from mcp.types import Tool, ToolAnnotations

from aihawk.mcp import server


def findings(tools):
    """Why a client could not tell what a tool does, or nothing."""
    out = []
    for t in tools:
        a = t.annotations
        if a is None:
            out.append("%s: no annotations at all" % t.name)
            continue
        if not (a.title or "").strip():
            out.append("%s: no title" % t.name)
        if a.readOnlyHint and a.destructiveHint:
            out.append("%s: read-only and destructive at once" % t.name)
        elif not a.readOnlyHint and not a.destructiveHint:
            out.append("%s: neither read-only nor destructive, so a client "
                       "cannot tell whether to ask first" % t.name)
    return out


def _live_tools():
    tools = asyncio.run(server.mcp.list_tools())
    assert len(tools) >= 16, "found %d tools, so this is not looking at the server" % len(tools)
    return tools


def test_every_tool_carries_a_title_and_says_whether_it_only_reads():
    assert findings(_live_tools()) == []


def test_the_reading_tools_are_the_ones_that_read():
    """The flags are not decoration: a tool that can change the page is not
    marked read-only, and one that cannot is not marked destructive. Listed by
    name, so a new tool has to be placed on one side or the other here."""
    reads = {"browser_list", "browser_status", "browser_read_text", "browser_snapshot",
             "browser_read_html", "browser_take_screenshot", "browser_watch",
             "browser_evaluate"}
    acts = {"browser_open", "browser_close", "browser_navigate", "browser_click",
            "browser_click_at", "browser_type", "browser_select_option",
            "browser_press_key"}
    by_name = {t.name: t.annotations for t in _live_tools()}
    assert set(by_name) == reads | acts, sorted(set(by_name) ^ (reads | acts))
    for name in reads:
        assert by_name[name].readOnlyHint is True and not by_name[name].destructiveHint, name
    for name in acts:
        assert by_name[name].destructiveHint is True and not by_name[name].readOnlyHint, name


def _tool(name, annotations):
    return Tool(name=name, description="x", inputSchema={"type": "object"},
                annotations=annotations)


def test_the_check_refuses_known_bad_tools():
    assert findings(_live_tools()) == []
    assert findings([_tool("bare", None)]) == ["bare: no annotations at all"]
    assert findings([_tool("untitled", ToolAnnotations(readOnlyHint=True))]) == ["untitled: no title"]
    assert findings([_tool("mute", ToolAnnotations(title="Mute"))]) == [
        "mute: neither read-only nor destructive, so a client cannot tell whether to ask first"]
    assert findings([_tool("both", ToolAnnotations(title="Both", readOnlyHint=True,
                                                    destructiveHint=True))]) == [
        "both: read-only and destructive at once"]
    assert findings([_tool("fine", ToolAnnotations(title="Fine", destructiveHint=True))]) == []
