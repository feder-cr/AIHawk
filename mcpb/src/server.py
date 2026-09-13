"""Entry point of the MCP bundle: the server over stdio.

Two hosts run this file two ways. One honours `mcp_config` and runs
`uv run --directory <bundle> src/server.py`, so the bundle's pyproject has
already installed the pinned package and the import below succeeds. The other
runs `python src/server.py` on its own, with nothing installed, and for that
one the import fails and the process becomes `uvx aihawk==<pin>` instead, with
the same stdio and the same arguments. The pin is read from the pyproject next
to this file rather than written here, so the bundle carries the number once.

With no arguments this is `aihawk` with no subcommand, which is the MCP server.
"""

import os
import pathlib
import sys
import tomllib

try:
    from aihawk.cli import main
except ImportError:
    main = None


def _pinned_requirement() -> str:
    pyproject = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
    deps = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["dependencies"]
    return next(d for d in deps if d.startswith("aihawk=="))


if __name__ == "__main__":
    if main is not None:
        main()
    else:
        os.execvp("uvx", ["uvx", _pinned_requirement(), *sys.argv[1:]])
