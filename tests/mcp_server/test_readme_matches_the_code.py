"""The README describes this package. These check that it still describes THIS one.

Written 2026-09-02, after finding that the HTTP transport, the live view and the
two-pane chat had shipped in 0.4.0 and were named nowhere in the README: not
broken, just invisible, which is the same thing from the outside. The view and
the chat left for `aihawk` the same day, so the drift to watch for here is now
the opposite one - a README still offering pages this package stopped serving.

Documentation drift is silent by construction. Nothing fails, nothing is red, and
the gap only surfaces when somebody asks for a feature that has been there for a
month. So the two facts most likely to drift are checked against the code that
defines them rather than against anybody's memory.
"""
from __future__ import annotations

import pathlib
import re

README = pathlib.Path(__file__).resolve().parents[2] / "docs" / "mcp-server.md"
SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "aihawk" / "mcp"


def test_the_readme_does_not_describe_an_interface_this_package_no_longer_has():
    """The page and the chat moved to `aihawk` in 0.9.0.

    A README that still offers them is worse than one that never mentioned them:
    it sends a reader to a URL that answers 404 and makes the split look like a
    regression. Checked against the code rather than against the prose, so this
    goes red the day either comes back without the README being told.
    """
    text = README.read_text(encoding="utf-8")
    assert not (SRC / "chat.py").exists(), "chat.py is back; this test is now wrong"
    assert not (SRC / "live.py").exists(), "live.py is back; this test is now wrong"

    # What is forbidden is OFFERING the pages, not naming them: the README has
    # to be able to say they moved, and the first version of this check went red
    # on that very sentence. A rule that forbids the vocabulary rather than the
    # claim is a rule somebody deletes instead of obeying.
    offered = re.findall(r"https?://[^\s`)]*:\d+/\S*", text)
    bad = [u for u in offered if u.rstrip("/.").endswith(("/live", ":8765"))
           or "/live" in u or "/chat" in u]
    assert not bad, f"the README points at pages this package no longer serves: {bad}"


def test_every_environment_variable_the_code_reads_is_documented():
    """Three of these were undocumented for a release: the HTTP transport and
    its host and port, which is the whole multi-client story.

    Reads the source rather than importing, because the variables are consulted
    at call time in several modules and a name that no test path reaches would
    otherwise be invisible here too.
    """
    used = set()
    for path in sorted(SRC.glob("*.py")):
        body = path.read_text(encoding="utf-8")
        used |= set(re.findall(r"""["'](STEALTHFOX_[A-Z0-9_]+)["']""", body))
    assert used, "no STEALTHFOX_* variable found in the source; has the prefix changed?"

    text = README.read_text(encoding="utf-8")
    missing = sorted(name for name in used if name not in text)
    assert not missing, f"read by the code, absent from the README: {missing}"


def _listed_tools() -> set:
    """The names in the LIST, not the names in the section.

    Two versions of this survived their mutation before this one killed it.
    Searching the whole README failed because a deleted tool was still named in
    a paragraph further down. Narrowing to the Tools section failed for the same
    reason at a smaller scale: that section holds the list AND the prose about
    it. A name mentioned in passing is not a listed tool, and the only thing
    that separates the two is looking at the list itself.
    """
    text = README.read_text(encoding="utf-8")
    start = text.index("## Tools")
    rest = text[start + len("## Tools"):]
    end = rest.find(chr(10) + "## ")
    section = rest if end < 0 else rest[:end]
    # The list is the paragraph with the most TOOL names in it. Tool names,
    # not any backticked word: since 2026-09-06 the section carries tables of
    # arguments, and a table with `url`, `selector` and `max_chars` in every
    # row out-counted the list of eighteen tools, so the list was never the
    # paragraph this looked at. A tool is what the server registers, and every
    # one of those is session_* or browser_*.
    tool = r"`((?:session|browser)_\w+)`"
    best = max((p for p in section.split(chr(10) * 2)),
               key=lambda p: len(re.findall(tool, p)), default="")
    return set(re.findall(tool, best))


def test_the_readme_names_every_tool_the_server_registers():
    """A tool nobody can find is a tool nobody uses.

    That is how the last two were noticed - one by hand, and one because a model
    with no way to set a dropdown clicked it, pressed arrow keys, and finally
    injected script to set the value. An undocumented tool and a missing one
    look the same from where the model sits."""
    import asyncio

    from aihawk.mcp import server

    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    listed = _listed_tools()
    missing = sorted(names - listed)
    assert not missing, f"registered but not in the tool list under ## Tools: {missing}"

    # ⛔ AND THE OTHER DIRECTION, WHICH IS THE ONE THAT SHIPPED A DEFECT. Only
    # the check above existed, so it could see a tool added and never a tool
    # REMOVED - and removing four is exactly what happened on 2026-09-11. The
    # list here was corrected by hand; six other published pages were not, and
    # nothing complained, because a name in a doc that the server no longer
    # registers is invisible to a subtraction that runs the other way.
    #
    # The project already enforces both directions one file over, for the
    # page's verb table, with a docstring saying why the second one exists.
    # This is that assertion, on the tool list.
    stale = sorted(listed - names)
    assert not stale, (
        f"the tool list names tools the server does not register: {stale}. A "
        "reader following this page calls a tool that does not exist.")


def test_the_engine_floor_covers_the_wait_this_package_relies_on():
    """`browser_click_at` holds a button down with `wait_for_timeout`, and in
    invisible-playwright before 0.9.0 that wait returned instantly: `hold_seconds`
    never held, on the one tool that exists for sliders and press-and-hold
    challenges, and the screenshot it returns was taken before the click had any
    effect.

    A floor that allows an older engine ships that behaviour to anyone whose
    resolver picks one. This is not a style preference: the shipped code calls
    the method, so the floor is part of the contract.
    """
    import pathlib
    import re
    import tomllib

    root = pathlib.Path(__file__).resolve().parents[2]
    deps = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    declared = [d for d in deps["project"]["dependencies"] if "invisible-playwright" in d]
    assert declared, "the engine dependency is gone"
    floor = re.search(r">=\s*(\d+)\.(\d+)\.(\d+)", declared[0])
    assert floor, f"no floor on the engine: {declared[0]!r}"
    major, minor, _ = (int(g) for g in floor.groups())
    assert (major, minor) >= (0, 9), (
        f"{declared[0]!r} allows an engine whose wait_for_timeout does nothing, "
        "so hold_seconds in browser_click_at would silently not hold")

    # And the code really does depend on it, so this floor is not superstition.
    source = (root / "src" / "aihawk" / "mcp" / "actions.py").read_text(encoding="utf-8")
    assert "wait_for_timeout" in source, (
        "nothing calls wait_for_timeout any more; if that is deliberate, this "
        "floor can come down and this test should say so")
