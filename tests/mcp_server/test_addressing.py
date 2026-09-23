"""Every tool that touches a browser goes through one funnel and can say which
browser it means.

Read from the SOURCE with `ast`, because the defect this guards does not fail:
a tool that reached the piece of work some other way - `work._open[...]`, a
`work.session(...)` of its own - would act on `main` whatever the caller asked,
or skip the sentence that says the browser is gone, and every test that drives
it with `main` open would stay green.
"""
from __future__ import annotations

import ast
import asyncio
import inspect

from invisible_playwright_mcp.mcp import server

#: The tools that act on the piece of work rather than on a page: they call
#: `work.open`, `work.close`, `work.listing`, `work.status`.
NOT_DRIVING_A_PAGE = {"browser_open", "browser_close", "browser_list", "browser_status"}

#: What a tool may reach on `work`. Everything that drives a page goes through
#: `acting`; nothing reaches the sessions or the dicts behind it.
ALLOWED = {"acting", "open", "close", "listing", "status"}


def _tools():
    tree = ast.parse(inspect.getsource(server))
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
               and d.func.attr == "tool" for d in node.decorator_list):
            yield node


def _reaches(node):
    """Every `work.<attr>` a tool body touches, with the call if it is one."""
    for inner in ast.walk(node):
        if (isinstance(inner, ast.Attribute) and isinstance(inner.value, ast.Name)
                and inner.value.id == "work"):
            yield inner.attr, inner


def _acting_calls(node):
    for inner in ast.walk(node):
        if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
                and isinstance(inner.func.value, ast.Name)
                and inner.func.value.id == "work" and inner.func.attr == "acting"):
            yield inner


def test_every_tool_that_drives_a_page_goes_through_the_funnel_and_names_its_browser():
    """Known-bad, two: have a tool call `actions.click(work._open["main"], ...)`;
    drop `role=browser` from one `acting` call."""
    driving = []
    for tool in _tools():
        if tool.name in NOT_DRIVING_A_PAGE:
            continue
        calls = list(_acting_calls(tool))
        assert len(calls) == 1, (
            "%s drives a page through %d `work.acting` calls; the funnel is one"
            % (tool.name, len(calls)))
        given = {k.arg: k.value for k in calls[0].keywords}
        assert isinstance(given.get("role"), ast.Name) and given["role"].id == "browser", (
            "%s does not hand `role=browser` to the funnel, so it acts on `main` "
            "whatever the caller asked" % tool.name)
        driving.append(tool.name)
    assert len(driving) >= 12, "only %d tools drive a page: %r" % (len(driving), driving)


def test_no_tool_reaches_past_the_funnel():
    for tool in _tools():
        for attr, _ in _reaches(tool):
            assert attr in ALLOWED, (
                "%s reaches `work.%s`, which is not one of the five doors" % (tool.name, attr))


def test_the_tools_that_act_on_the_piece_of_work_name_a_browser_too():
    """`browser_open`, `browser_close` and `browser_status` take the role from
    the caller and fall back to `main`; `browser_list` asks about the set and
    takes none."""
    for tool in _tools():
        if tool.name not in NOT_DRIVING_A_PAGE or tool.name == "browser_list":
            continue
        calls = [c for c in ast.walk(tool)
                 if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                 and isinstance(c.func.value, ast.Name) and c.func.value.id == "work"]
        assert len(calls) == 1, tool.name
        first = calls[0].args[0]
        assert isinstance(first, ast.BoolOp) and any(
            isinstance(v, ast.Name) and v.id == "browser" for v in first.values), (
            "%s does not pass `browser or DEFAULT_BROWSER_ID`" % tool.name)


def test_every_tool_that_reaches_a_browser_offers_a_way_to_name_it():
    """Checked against the SCHEMA the server publishes, not the Python
    signature: a parameter the client cannot see does not exist.

    Known-bad: delete `browser` from any tool but `browser_list`.
    """
    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    needing = {t.name for t in _tools()} - {"browser_list"}
    assert len(needing) >= 15, sorted(needing)
    mute = sorted(n for n in needing
                  if "browser" not in (tools[n].inputSchema.get("properties") or {}))
    assert mute == [], (
        "these tools reach a browser and offer no way to say which: %s" % mute)
