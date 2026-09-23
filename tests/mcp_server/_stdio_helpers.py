"""Shared plumbing for tests that spawn `python -m invisible_playwright_mcp` as a real subprocess.

⛔ A SUBPROCESS GETS ITS OWN sys.path, AND `pythonpath` IN pyproject.toml DOES
NOT REACH IT. That option only affects the pytest PROCESS itself - it makes
every IN-PROCESS `from invisible_playwright_mcp...` import in this test run resolve to this
checkout's own `src/`, which is exactly why it was added (see the comment
beside it). A subprocess launched with `sys.executable -m invisible_playwright_mcp` starts a
second interpreter that never sees that option: it resolves `invisible_playwright_mcp` the
ordinary way, through whatever site-packages' editable-install `.pth` file
names, which on this machine is a DIFFERENT, older checkout shared with
another session.

Measured 2026-09-11: a real `browser_open` call made over such a subprocess
answered with a ten-browser ceiling message that does not exist anywhere in
this tree - the subprocess was running 0.11.0 from
`C:/src/firefox-stealth/release/invisible_playwright_mcp`, while every in-process test in the
same run correctly saw this checkout's own code, because `pythonpath` covers
those and only those. A test built on `python -m invisible_playwright_mcp` proves nothing about
a change in this checkout until its subprocess is pointed here explicitly.

One function, so the fix is not retyped per file and left to drift the next
time a test needs a subprocess of its own.

⛔ AND THE FIX IS APPLIED AT IMPORT, TO `os.environ` ITSELF, BECAUSE THE TESTS
THAT NEED IT MOST NEVER CALL EITHER FUNCTION. A test of the server's own
plumbing spawns the child through `Link`, which is PRODUCT code: it builds its
own parameters and takes its environment from `child_env(opts, os.environ)`. No
test argument reaches that call, so a fix that lives only inside
`server_params` cannot cover it, and
`tests/mcp_server/test_a_connection_is_closed_by_its_owner.py` said
`# noqa: F401 (imported for its path setup)` over an import that did nothing
at all. It was a true statement of intent over an inert line.

Nothing noticed while the package was named `aihawk`, because the editable
install resolved that name anyway - to the other checkout, which is the very
thing this module exists to prevent. Renaming the package removed the name
from site-packages and five tests died with `No module named
invisible_playwright_mcp`: the rename did not break them, it revealed that
they had never been pointed here.

So the environment is fixed once, here, and the two functions below read it
instead of each recomputing the prefix. One place knows the rule, and a child
spawned by product code under test inherits it for free.
"""
from __future__ import annotations

import os
import pathlib
import sys

from mcp import StdioServerParameters

#: This checkout's own `src/`, prepended so it wins over whatever site-packages
#: resolves `invisible_playwright_mcp` to.
_SRC = str(pathlib.Path(__file__).resolve().parents[2] / "src")

# Idempotent: importing this module twice must not stack the prefix twice, and
# a PYTHONPATH the developer set for their own reasons is kept behind ours.
if _SRC not in os.environ.get("PYTHONPATH", "").split(os.pathsep):
    os.environ["PYTHONPATH"] = os.pathsep.join(
        p for p in (_SRC, os.environ.get("PYTHONPATH", "")) if p)


def server_params(env: dict | None = None) -> StdioServerParameters:
    """`StdioServerParameters` for `python -m invisible_playwright_mcp`, guaranteed to run the
    code in THIS checkout rather than whatever else happens to be installed.

    `env`, if given, is layered onto the current process's own environment,
    which already carries the path fix, so a caller's overrides - a session id,
    a real binary path, a headless flag - are never the thing undone by it.
    """
    return StdioServerParameters(command=sys.executable, args=["-m", "invisible_playwright_mcp"],
                                 env=dict(os.environ, **(env or {})))


def subprocess_env(env: dict | None = None) -> dict:
    """The same environment, as a plain dict, for callers that build their own
    `subprocess.Popen` instead of going through `StdioServerParameters`."""
    return dict(os.environ, **(env or {}))
