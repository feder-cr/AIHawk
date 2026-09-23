"""A rule about how a file reaches the disk is written once, where it happens.

⛔ `store.save` CARRIED THE BYTES-NOT-TEXT RULE IN FULL AND DOES NOT APPLY IT.
It calls `storage.write_atomically`, which is where the rule lives and where it
is documented. So the copy in `save` was a rule written where it is not
applied: a reader fixing it there would have changed nothing, and the two were
free to drift into two accounts of one decision.

Two things make this worth a gate rather than a quiet edit. `store.load`, five
lines below, already did it right - it names `storage.read_json` and says the
reason is not repeated here. And `storage.py` opens by arguing that the atomic
write was once copied into both files "with only one of the two carrying the
comment explaining why", and that two copies is the arrangement where a fix
reaches one of them. The module that removed the duplicated CODE kept a
duplicate of its own headline rule in prose.

Found by a scan for prose repeated across modules, which is the detector worth
keeping: eight-word runs of comment or docstring text appearing in more than
one file.
"""
from __future__ import annotations

import ast
import pathlib

from invisible_playwright_mcp import storage
from invisible_playwright_mcp.mcp import store

#: The rule's own words. Held as the phrase rather than as an idea, because a
#: phrase is what gets copied.
RULE = "never `write_text`"


def sources():
    root = pathlib.Path(storage.__file__).resolve().parent
    return {p: p.read_text(encoding="utf-8") for p in sorted(root.rglob("*.py"))}


def test_the_rule_about_bytes_is_written_in_exactly_one_place():
    """Known-bad: paste the paragraph back into `store.save`, or into any other
    docstring that writes a file through the same helper."""
    carriers = [p.name for p, text in sources().items() if RULE in text]
    assert carriers == [pathlib.Path(storage.__file__).name], (
        "the rule about writing bytes is in %s; it belongs to the function "
        "that does the writing, and a second copy is free to disagree with it"
        % carriers)


def test_the_place_that_owns_it_still_states_it():
    """The half that matters when a sentence is removed somewhere: it has to
    still exist where it was kept.

    Known-bad: delete the paragraph from `write_atomically` - the rule is then
    nowhere and this file is the only thing that notices.
    """
    doc = storage.write_atomically.__doc__ or ""
    assert RULE in doc, (
        "`write_atomically` no longer says why it writes bytes, and it is the "
        "only place that was left saying it")


def test_save_points_at_the_owner_instead_of_restating_it():
    """A pointer, not a copy. `store.load` was already written this way about
    the same file, which is why this is a repair rather than a new convention.

    Known-bad: drop the reference and leave `save` silent about where its
    durability comes from - a reader then has no way from here to the rule.
    """
    doc = store.save.__doc__ or ""
    assert "write_atomically" in doc, (
        "`save` neither states the rule nor names where it lives, so the "
        "reason its write survives a crash is unreachable from here")
    assert RULE not in doc, "the copy is back in `save`"


def test_no_docstring_states_a_rule_about_a_call_it_does_not_make():
    """The class, narrowly. A ⛔ paragraph naming `write_bytes` or
    `write_atomically` belongs to a function that calls one of them.

    Deliberately limited to these two names rather than every backticked
    identifier: a scan over all of them accused four healthy docstrings out of
    five, because naming a thing by CONTRAST - "never `write_text`", "no longer
    the constant `main`" - is exactly how a rule explains itself.

    Known-bad: put a ⛔ note about `write_bytes` on a function that delegates.
    """
    watched = ("write_bytes", "write_atomically")
    guilty = []
    for path, text in sources().items():
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            doc = ast.get_docstring(node)
            if not doc:
                continue
            body = node.body[1:] if ast.get_docstring(node) else node.body
            calls = {n.id for n in ast.walk(ast.Module(body=body, type_ignores=[]))
                     if isinstance(n, ast.Name)}
            calls |= {n.attr for n in ast.walk(ast.Module(body=body, type_ignores=[]))
                      if isinstance(n, ast.Attribute)}
            for line in doc.splitlines():
                if "⛔" not in line:
                    continue
                for name in watched:
                    if ("`%s`" % name) in line and name not in calls:
                        guilty.append("%s::%s names %s" % (path.name, node.name, name))
    assert not guilty, (
        "a rule about writing is stated by a function that does not write: %s"
        % guilty)
