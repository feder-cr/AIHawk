"""invisible-playwright-mcp: a stealth Firefox browser exposed over MCP."""
from importlib.metadata import PackageNotFoundError, version as _version

# Derived, never typed. This line said "0.1.0" through four releases - 0.2.0,
# 0.3.0, 0.4.0 and into 0.5.0 - because a hand-written literal is a second place
# the version lives, and the second place is the one nobody remembers to move.
# No test could see it either: every test imports the checkout, where the number
# is whatever the file says. It took installing the built wheel into an empty
# environment and asking the package what version it was.
try:
    __version__ = _version("invisible-playwright-mcp")
except PackageNotFoundError:  # running from a source tree, not installed
    __version__ = "0+unknown"

__all__ = ["__version__"]
