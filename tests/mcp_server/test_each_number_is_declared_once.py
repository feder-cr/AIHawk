"""A number the model is told is the number the code uses.

⛔ THE CAP WAS WRITTEN THREE TIMES: `DEFAULT_MAX_CHARS` in `actions.py`, the
default in `browser_read_text`'s signature, and the digit in its description.
The signature was a copy nothing read back, so it could drift from the constant
in silence and the tool would honour a number its own module did not declare.
It reads the constant now.

The DIGIT in the prose stays, and a draft that deleted it was wrong: the schema
does publish the default, but `test_the_two_readers_do_not_pretend_to_share_a
_cap` holds that this description declares its cap while `browser_read_html`
declares it has none, because a reader shown one and not the other assumes
symmetry and the two differ by 34x on a large page. A number with a reason to
be written twice gets a gate rather than a deletion.
"""
from __future__ import annotations

import asyncio
import re

from invisible_playwright_mcp.mcp import actions, server


def tools() -> dict:
    return {t.name: t for t in asyncio.run(server.mcp.list_tools())}


def test_the_cap_in_the_prose_is_the_cap_the_tool_uses():
    """Known-bad: change `DEFAULT_MAX_CHARS` and leave the sentence alone, or
    type a different digit into the sentence."""
    text = tools()["browser_read_text"].description or ""
    said = re.findall(r"\b(\d{3,6})\b", text)
    assert said, "the description stopped naming a cap at all: %r" % text
    assert str(actions.DEFAULT_MAX_CHARS) in said, (
        "the description tells the model %s while the tool cuts at %d"
        % (" and ".join(said), actions.DEFAULT_MAX_CHARS))


def test_the_schema_publishes_the_same_cap():
    """The third reader. A client that renders the argument shows this number,
    and it must be the constant rather than a literal somebody retyped in the
    signature.

    Known-bad: put `max_chars: int = 6000` back in the signature and move the
    constant - the schema then disagrees with the module that owns it.
    """
    schema = tools()["browser_read_text"].inputSchema
    field = (schema.get("properties") or {}).get("max_chars") or {}
    assert field.get("default") == actions.DEFAULT_MAX_CHARS, (
        "the schema publishes %r as the default while the module declares %d"
        % (field.get("default"), actions.DEFAULT_MAX_CHARS))


def test_a_measurement_is_not_repeated_in_a_tool_description():
    """⛔ THE EVIDENCE BELONGS BESIDE THE CODE IT JUSTIFIES, NOT IN THE PROMPT.

    `browser_snapshot` carried the 958-element selector study and the
    two-hundred-option count, both of which are also written in `actions.py`
    beside the code they explain. A measurement in two places is one that gets
    re-run once and updated once, and the copy left wrong is the one a model
    reads - out of the 1024 characters the description is cut at.

    Held as a property rather than on those two numbers: no tool description
    carries a figure that reads as a study. The rules those paragraphs stated
    are checked below, so this cannot pass by saying less.

    Known-bad: put either measurement back into a description.
    """
    guilty = []
    for name, tool in tools().items():
        text = tool.description or ""
        for m in re.finditer(r"\b(\d{2,4})%|\bacross (\d{3,})\b|\b(\d{3,}) elements\b",
                             text):
            guilty.append("%s: %s" % (name, m.group(0)))
    assert not guilty, (
        "a description carries evidence rather than a rule, which belongs in "
        "the module beside the code it justifies: %s" % guilty)


def test_the_snapshot_still_states_every_rule_it_used_to():
    """The half that stops the cut above from being a loss. Dropping the
    numbers must not drop what a caller has to DO.

    Known-bad: delete any of these sentences along with the evidence.
    """
    text = (tools()["browser_snapshot"].description or "").lower()
    for rule, why in (
            ("verbatim", "pass the selector as given"),
            ("one element", "it is built to reach exactly one"),
            ("first match", "the driver takes the first when it does not"),
            ("`at`", "elements with no selector carry coordinates"),
            ("accessibility tree", "this is not that tree, and why"),
    ):
        assert rule in text, (
            "the snapshot no longer tells a caller that %s (%r missing)"
            % (why, rule))


def test_the_measurements_are_still_written_where_the_code_is():
    """The other half: moved, not deleted. A reader of `actions.py` still finds
    why the selector is built and why the inventory is not the a11y tree.

    Known-bad: delete them from `actions.py` too, and the reason is nowhere.
    """
    source = open(actions.__file__, encoding="utf-8").read()
    assert "958" in source, "the selector study is gone from the module too"
    assert "two hundred" in source, (
        "the option-count measurement is gone from the module too")
