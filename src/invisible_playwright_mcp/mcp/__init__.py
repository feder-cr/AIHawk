"""invisible_playwright_mcp.mcp: a stealth Firefox browser exposed over MCP, shipped inside invisible_playwright_mcp."""
# Derived, never typed, and derived in ONE place. This line said "0.1.0"
# through four releases - 0.2.0, 0.3.0, 0.4.0 and into 0.5.0 - because a
# hand-written literal is a second place the version lives, and the second
# place is the one nobody remembers to move. No test could see it either: every
# test imports the checkout, where the number is whatever the file says. It
# took installing the built wheel into an empty environment and asking the
# package what version it was.
#
# ⛔ THE REMEDY THEN PUT THE LOOKUP HERE *AND* IN THE PARENT, which is the same
# defect in a politer shape: two places computing one fact, free to disagree the
# day one of them changes. It now comes from the parent, which is where the
# question of what this code is belongs. And the answer changed: see
# `_version.py` for why an install record does not describe an editable tree.
from .. import __version__

#: The browser a caller means when it names nothing.
DEFAULT_BROWSER_ID = "main"

#: The other one: the helper beside the identity. See `work.py` for why there
#: are exactly two.
SUPPORT_BROWSER_ID = "support"

#: ⛔ THE TWO SENTENCES EVERY TOOL CAN ANSWER INSTEAD OF WORKING, AND THEY LIVE
#: HERE RATHER THAN BESIDE THE CODE THAT SAYS THEM, because their readers are
#: far apart and only one of them is a person. A model acts on the words. The
#: live pane has to tell "there is nothing to look at" - draw the idle state,
#: quietly - apart from "something is wrong", which is a sentence somebody
#: reads; it compares against the first sentence, so the two cannot drift, and
#: put in `work.py` it would drag the engine's wrapper into the interface's
#: process just to read a string.
#:
#: Until 0.53.0 there were five sentences for "nothing is running" and none
#: for "it died", because a tool would START a browser when none was running
#: and REBUILD one that had died. Neither happens now: a browser is opened
#: with `browser_open` and with nothing else, and when it is gone the model is
#: told so and told what to do. That is the whole lifecycle.
NOT_OPEN = "the %s browser is not open. Call browser_open to open it."
GONE = ("the %s browser is gone: it closed or crashed. Call browser_open to "
        "open it again; it comes back as the same person.")

__all__ = ["__version__", "DEFAULT_BROWSER_ID", "SUPPORT_BROWSER_ID", "NOT_OPEN", "GONE"]
