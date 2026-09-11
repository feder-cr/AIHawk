"""Shared plumbing for tests that spawn `python -m aihawk` as a real subprocess.

⛔ A SUBPROCESS GETS ITS OWN sys.path, AND `pythonpath` IN pyproject.toml DOES
NOT REACH IT. That option only affects the pytest PROCESS itself - it makes
every IN-PROCESS `from aihawk...` import in this test run resolve to this
checkout's own `src/`, which is exactly why it was added (see the comment
beside it). A subprocess launched with `sys.executable -m aihawk` starts a
second interpreter that never sees that option: it resolves `aihawk` the
ordinary way, through whatever site-packages' editable-install `.pth` file
names, which on this machine is a DIFFERENT, older checkout shared with
another session.

Measured 2026-09-11: a real `browser_open` call made over such a subprocess
answered with a ten-browser ceiling message that does not exist anywhere in
this tree - the subprocess was running 0.11.0 from
`C:/src/firefox-stealth/release/aihawk`, while every in-process test in the
same run correctly saw this checkout's own code, because `pythonpath` covers
those and only those. A test built on `python -m aihawk` proves nothing about
a change in this checkout until its subprocess is pointed here explicitly.

One function, so the fix is not retyped per file and left to drift the next
time a test needs a subprocess of its own.
"""
from __future__ import annotations

import os
import pathlib
import sys

from mcp import StdioServerParameters

#: This checkout's own `src/`, prepended so it wins over whatever site-packages
#: resolves `aihawk` to.
_SRC = str(pathlib.Path(__file__).resolve().parents[2] / "src")


def server_params(env: dict | None = None) -> StdioServerParameters:
    """`StdioServerParameters` for `python -m aihawk`, guaranteed to run the
    code in THIS checkout rather than whatever else happens to be installed.

    `env`, if given, is layered onto the current process's own environment
    before the path fix is applied, so a caller's overrides - a session id, a
    real binary path, a headless flag - are never the thing undone by it.
    """
    full = dict(os.environ, **(env or {}))
    full["PYTHONPATH"] = _SRC + os.pathsep + full.get("PYTHONPATH", "")
    return StdioServerParameters(command=sys.executable, args=["-m", "aihawk"], env=full)


def subprocess_env(env: dict | None = None) -> dict:
    """The same fix, as a plain env dict, for callers that build their own
    `subprocess.Popen` instead of going through `StdioServerParameters`."""
    full = dict(os.environ, **(env or {}))
    full["PYTHONPATH"] = _SRC + os.pathsep + full.get("PYTHONPATH", "")
    return full
