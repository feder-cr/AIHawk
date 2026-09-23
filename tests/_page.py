"""The page's own source, sliced, for the benches that EXECUTE it in node.

Those benches run the REAL functions rather than doubles, which is the rule this
suite already argues for elsewhere: a double passes while the page does something
else. The cost is that a slice has to carry whatever the sliced code reads, and
that is a fact about the page, not about any one bench.

⛔ IT IS ONE MODULE BECAUSE THREE BENCHES LEARNED IT THE SAME DAY. On 2026-09-23
the three storage keys started being built from one prefix, and every harness
that ran a function touching storage died with `STORE is not defined` - a message
that reads as the harness being WRONG rather than incomplete. Fourteen tests, one
missing line, three files that each had their own way of slicing. The slice lives
here now, so the next thing the page hoists is added in one place.
"""
from __future__ import annotations

from invisible_playwright_mcp.ui import PAGE

#: Everything from the opening tag on, which is what a harness executes.
SCRIPT = PAGE[PAGE.index("<script"):]


def slice_of(start: str, end: str) -> str:
    """The page's source from `start` through the first `end` after it."""
    src = SCRIPT[SCRIPT.index(start):]
    return src[:src.index(end) + len(end)]


#: What every key on the page is built from, plus the read that carries a value
#: across from the retired key. First in the script by construction, so a harness
#: can always put it at the top of what it runs.
CARRIED = slice_of("const STORE =", "\n}\n")
