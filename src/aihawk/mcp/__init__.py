"""aihawk.mcp: a stealth Firefox browser exposed over MCP, shipped inside aihawk."""
from importlib.metadata import PackageNotFoundError, version as _version

# Derived, never typed. This line said "0.1.0" through four releases - 0.2.0,
# 0.3.0, 0.4.0 and into 0.5.0 - because a hand-written literal is a second place
# the version lives, and the second place is the one nobody remembers to move.
# No test could see it either: every test imports the checkout, where the number
# is whatever the file says. It took installing the built wheel into an empty
# environment and asking the package what version it was.
try:
    __version__ = _version("aihawk")
except PackageNotFoundError:  # running from a source tree, not installed
    __version__ = "0+unknown"

#: What a LOOK at a browser that is not running is refused with.
#:
#: ⛔ ONE SENTENCE IN ONE PLACE, AND IT LIVES HERE RATHER THAN BESIDE THE TOOL
#: THAT SAYS IT, because its two readers are far apart and only one of them is
#: a person. A model acts on the words; the live pane has to tell "there is
#: nothing to look at" - draw the idle state, quietly - apart from "the capture
#: is broken", which is a sentence somebody needs to read. The pane compares
#: against this, so the two cannot drift; put in `server.py` it would drag the
#: whole server object into the interface's process just to read a string.
#:
#: Interface and server are always the same build: the link launches
#: `sys.executable -m aihawk`, so there is no version skew to defend against.
NOTHING_RUNNING = ("no browser is running here, so there is no window to "
                   "watch. browser_list says which browsers this session has, "
                   "and any command aimed at one starts it.")

__all__ = ["__version__", "NOTHING_RUNNING"]
