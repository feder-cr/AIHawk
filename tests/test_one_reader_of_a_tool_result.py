"""A tool result is read in one place, and this is how that stays true.

⛔ THE GATE NEXT DOOR CANNOT SEE THIS ONE. `test_the_product_surface_is_what
_the_product_uses` asks whether a name has a caller in the product, which
catches a surface that is dead. A DUPLICATED surface answers yes: both copies
are named, both are called, both have tests, and the suite is green whichever
one drifts.

What was actually there, until this file existed: three readers of one wire
format.

  * `link.text_of` - the text of a result, with a docstring saying it was
    "shared with the agent loop rather than written twice: a tool result is
    read in two places now, and two readers of one wire format drift".
  * `agent._result_text` - the same five lines written out again, the
    `[non-text result]` literal included, importing nothing from `link`. The
    sentence above was not describing the code; it was describing an intention.
  * `routes.frame` - `text_of(result) if getattr(result, "isError", False)
    else ""`, reading the flag for itself beside a call to the shared reader.

So the question here is structural rather than nominal: WHO KNOWS what an MCP
tool result looks like? The answer has to be `link.py`, and one module is a
thing that can be asserted.

⛔ AND IT READS THE SYNTAX, NOT THE TEXT, because this project has recorded the
gate-accused-by-a-comment defect more times than any other and the prose here is
full of the very words being searched for - this docstring included. `isError`
inside a sentence is not an attribute access and not a string equal to
"isError", so an AST walk cannot be fooled by either, in either direction: it
also cannot be SATISFIED by a comment mentioning the name.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "invisible_playwright_mcp"

#: The module that is allowed to know the shape of a tool result.
THE_READER = "link.py"

#: What knowing that shape looks like in code. `isError` is the failure flag as
#: an attribute or as the name handed to `getattr`; the literal is the answer
#: for a result whose first block carries no text, and a second copy of it is
#: the clearest possible sign that the reading was written out again.
FLAG = "isError"
NO_TEXT = "[non-text result]"


def readers(tree: ast.AST) -> list[str]:
    """Every place in this module that reads a tool result's own fields.

    Attribute access (`result.isError`), the same name as the string `getattr`
    is given, and the literal answer. A docstring mentioning any of them is a
    Constant that is not EQUAL to them, so it never lands here.
    """
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == FLAG:
            found.append("." + FLAG)
        elif isinstance(node, ast.Constant) and node.value in (FLAG, NO_TEXT):
            found.append(repr(node.value))
    return found


def modules():
    return sorted(SRC.rglob("*.py"))


def test_one_module_knows_what_a_tool_result_looks_like():
    """Known-bad: put `getattr(result, "isError", False)` back in agent.py."""
    guilty = {}
    for path in modules():
        if path.name == THE_READER:
            continue
        got = readers(ast.parse(path.read_bytes().decode("utf-8")))
        if got:
            guilty[str(path.relative_to(SRC))] = sorted(set(got))
    assert not guilty, (
        "these modules read a tool result for themselves instead of asking "
        "`link.answer_of`, which is how three readers of one wire format happened: "
        "%s" % guilty)


def test_the_reader_is_actually_in_that_module():
    """⛔ THE GATE ABOVE PASSES ON AN EMPTY PACKAGE, so it is worth nothing
    until something says the reading exists at all. Delete `answer_of` from
    `link.py` and the first test goes GREEN - there would be nobody left
    reading the flag anywhere."""
    got = readers(ast.parse((SRC / THE_READER).read_bytes().decode("utf-8")))
    assert "." + FLAG in got or repr(FLAG) in got, (
        "%s no longer reads the failure flag, so the gate above is asserting "
        "that nothing does" % THE_READER)
    assert repr(NO_TEXT) in got, (
        "%s no longer carries the answer for a result with no text" % THE_READER)


def test_the_loop_and_the_route_go_through_that_one_reader():
    """The structural test says nobody else reads the fields. This says the two
    callers that used to read them are reading the shared one now, by NAME, so
    a module that quietly stopped calling it would not pass by simply having
    deleted its copy."""
    for name in ("agent.py", "routes.py"):
        tree = ast.parse((SRC / name).read_bytes().decode("utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("link")
            for alias in node.names
        }
        assert "answer_of" in imported, (
            "%s does not import `answer_of` from link: it either reads the result "
            "itself again, or it stopped reporting a failed tool" % name)


@pytest.mark.parametrize("mutant, why", [
    ('def peek(result):\n    return getattr(result, "isError", False)\n',
     "the flag read through getattr"),
    ('def peek(result):\n    return result.isError\n',
     "the flag read as an attribute"),
    ('def peek(result):\n    return "[non-text result]"\n',
     "the answer for a result with no text, written out again"),
])
def test_the_scan_sees_a_second_reader(mutant, why):
    """The known-bad, run rather than described: each of these is how a second
    reader has actually been spelled in this repository."""
    assert readers(ast.parse(mutant)), why


@pytest.mark.parametrize("innocent", [
    '"""A docstring about isError and the [non-text result] answer."""\n',
    '# isError, and "[non-text result]", in a comment\nx = 1\n',
    'async def f(msg):\n    return msg.content or ""\n',
])
def test_the_scan_does_not_accuse_prose_or_the_model_message(innocent):
    """⛔ THE THIRD CASE IS NOT PADDING. `agent.py` reads `msg.content` on every
    turn - the MODEL's message, not a tool result - and a scan written against
    the word `content` instead of against these two fields would have accused
    the loop for doing its job."""
    assert not readers(ast.parse(innocent))
