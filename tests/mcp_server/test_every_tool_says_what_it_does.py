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

from invisible_playwright_mcp.mcp import server


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
        elif not (a.readOnlyHint is True or a.destructiveHint is True
                  or (a.readOnlyHint is False and a.destructiveHint is False)):
            out.append("%s: says nothing about whether it only reads, so a "
                       "client cannot tell whether to ask first" % t.name)
    return out


def _live_tools():
    tools = asyncio.run(server.mcp.list_tools())
    assert len(tools) >= 16, "found %d tools, so this is not looking at the server" % len(tools)
    return tools


def test_every_tool_carries_a_title_and_says_whether_it_only_reads():
    assert findings(_live_tools()) == []


def test_the_reading_tools_are_the_ones_that_read():
    """The flags are not decoration, and there are THREE groups, not two.

    ⛔ `reads` used to hold eight names and five of them were a lie. A tool
    marked read-only promises it changes nothing; `browser_read_text`,
    `browser_snapshot`, `browser_read_html`, `browser_take_screenshot` and
    `browser_evaluate` all go through `ready()`, which STARTS a real Firefox
    when none is running, and can reopen the url a restored session was owed.
    A client that trusted the flag to run them unattended was being told it
    could spawn a browser for free.

    The honest third group is the one the MCP hints already have: not
    read-only, and explicitly NOT destructive. It means additive - this may
    bring something into being, it will not wreck anything. Nothing on the
    page is changed by any of the five.

    Why they are not simply made read-only by refusing to start, which would
    be the other way to make the flag true: the server's own INSTRUCTIONS
    promise the opposite, "There is nothing to list, start or choose before
    acting ... or browser_snapshot to see what it is already on". Lazy start
    is the contract, so the declaration moves, not the behaviour. Whether
    that contract is the right one is a product question, recorded as such.

    `browser_watch` and `browser_list` stay read-only because they really are:
    they go through the peeking path and refuse instead of opening anything.
    """
    reads = {"browser_list", "browser_status", "browser_watch",
             "browser_read_text", "browser_snapshot", "browser_read_html",
             "browser_take_screenshot", "browser_evaluate"}
    additive = set()
    acts = {"browser_open", "browser_close", "browser_navigate", "browser_click",
            "browser_click_at", "browser_type", "browser_select_option",
            "browser_press_key"}
    by_name = {t.name: t.annotations for t in _live_tools()}
    assert set(by_name) == reads | additive | acts, sorted(
        set(by_name) ^ (reads | additive | acts))
    for name in reads:
        assert by_name[name].readOnlyHint is True and not by_name[name].destructiveHint, name
    for name in additive:
        a = by_name[name]
        assert a.readOnlyHint is False and a.destructiveHint is False, name
    for name in acts:
        assert by_name[name].destructiveHint is True and not by_name[name].readOnlyHint, name


def test_a_tool_that_can_start_a_browser_is_not_marked_read_only():
    """The rule behind the three groups, checked against the CODE rather than
    against the list above, so a new tool cannot be filed in the wrong group.

    A tool whose body calls `work.open(...)` can start a browser. Read straight
    from the source with `ast`, because a name lookup would also match the
    word in a docstring, and that is how a gate ends up agreeing with a
    comment. Since 0.53.0 exactly one tool does, `browser_open`; a second one
    calling it - a read that opens a browser to answer - turns this red.
    """
    import ast
    import inspect

    src = inspect.getsource(server)
    tree = ast.parse(src)
    starts = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for inner in ast.walk(node):
                if (isinstance(inner, ast.Call)
                        and isinstance(inner.func, ast.Attribute)
                        and isinstance(inner.func.value, ast.Name)
                        and inner.func.value.id == "work"
                        and inner.func.attr == "open"):
                    starts.add(node.name)
    assert starts == {"browser_open"}, (
        "the tools that can start a browser are %r; browser_open is the only "
        "one that may" % sorted(starts))
    by_name = {t.name: t.annotations for t in _live_tools()}
    wrong = sorted(n for n in starts
                   if n in by_name and by_name[n].readOnlyHint is True)
    assert wrong == [], (
        "these tools start a browser through ready() and still promise they "
        "only read: %s" % wrong)


def _tool(name, annotations):
    return Tool(name=name, description="x", inputSchema={"type": "object"},
                annotations=annotations)


def test_the_check_refuses_known_bad_tools():
    assert findings(_live_tools()) == []
    assert findings([_tool("bare", None)]) == ["bare: no annotations at all"]
    # States both hints, so the only thing wrong with it is the missing title
    # and the finding isolates that. With `destructiveHint` left out it would
    # also be mute, and the mutation would be testing two defects at once.
    assert findings([_tool("untitled", ToolAnnotations(
        readOnlyHint=True, destructiveHint=False))]) == ["untitled: no title"]
    assert findings([_tool("mute", ToolAnnotations(title="Mute"))]) == [
        "mute: says nothing about whether it only reads, so a client cannot "
        "tell whether to ask first"]
    # ⛔ ABSENT IS NOT THE SAME AS FALSE, and conflating them is what made the
    # five reading tools claim to be read-only. A tool that states both hints
    # and says false to both has told a client exactly where it stands:
    # additive. One that states neither has told it nothing.
    assert findings([_tool("additive", ToolAnnotations(
        title="Additive", readOnlyHint=False, destructiveHint=False))]) == []
    assert findings([_tool("half", ToolAnnotations(
        title="Half", readOnlyHint=False))]) == [
        "half: says nothing about whether it only reads, so a client cannot "
        "tell whether to ask first"]
    assert findings([_tool("both", ToolAnnotations(title="Both", readOnlyHint=True,
                                                    destructiveHint=True))]) == [
        "both: read-only and destructive at once"]
    assert findings([_tool("fine", ToolAnnotations(title="Fine", destructiveHint=True))]) == []
