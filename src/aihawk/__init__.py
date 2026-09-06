"""aihawk: drive a stealth browser with an LLM from one command."""
from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("aihawk")
except PackageNotFoundError:  # a checkout on sys.path with nothing installed
    __version__ = "0+unknown"

__all__ = ["__version__"]
