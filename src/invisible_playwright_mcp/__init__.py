"""invisible_playwright_mcp: drive a stealth browser with an LLM from one command."""
# `__version__` describes the CODE that is about to run; the install record is
# a different fact and keeps a name that says so. Why the two can disagree, and
# what was advertising the wrong one: `_version.py`.
from ._version import __install_record_version__, __version__

__all__ = ["__version__", "__install_record_version__"]
