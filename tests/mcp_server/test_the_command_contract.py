"""`invisible-playwright-mcp` is the one command this package declares.

The distribution and the command are `invisible-playwright-mcp`; the module is
`invisible_playwright_mcp`. The two spellings are one name to PyPI and two
different things to a reader: one is typed at a shell, the other is imported.
New registrations use `uvx invisible-playwright-mcp`, and the interface spawns
`python -m invisible_playwright_mcp`: the group with no subcommand serves over
stdio, `invisible-playwright-mcp ui` is the interface, and there is no second
script and no `invisible_playwright_mcp.mcp` command - pinned here.

⛔ THIS FILE'S STORY RAN THE OTHER WAY UNTIL 2026-09-23, AND THE RENAME MADE
EVERY WORD OF IT FALSE. `invisible-playwright-mcp` was a DIFFERENT
distribution: a shim, shipped from an archived repository since its 0.16.0,
whose modules re-exported this server and whose console script pointed at a
module path rather than at a command. Clients that had registered that name
reached the real package through it, the shim could not follow a rename, and
so the names it bound were pinned here.

⛔ AND AN EARLIER VERSION OF THIS PARAGRAPH SAID BOTH NAMES HAD BEEN DELETED
FROM THE INDEX. They had not: the index answered 404 for both on 2026-09-23, that
was read as a deletion, and PyPI does not let a deleted name be registered again,
so 87 versions under the old name and 19 under the shim's could not have come
back. Both are still there. The 404 was transient and the conclusion was not
checked.

What is true is smaller and still the point: the shim's last version is 0.16.0
and it depends on the old distribution, so a client that registered that name
gets the pre-rename product until this package publishes a version above it.
From that release on, `uvx invisible-playwright-mcp` resolves here, and with no
subcommand that is the stdio server, which is what those clients were being
handed through the shim all along.

So the three names below stay pinned for the reason they are ACTUALLY used,
which the old account hid behind the shim: `cli._serve` imports `main` from the
server module, and the server's own at-exit hook calls `work.close_all`. They
were a shim's bindings by accident of history; they are the CLI's contract by
design.
"""
import tomllib
from pathlib import Path

from click.testing import CliRunner


def test_the_names_the_cli_reaches_for_exist():
    from invisible_playwright_mcp.mcp import server

    assert callable(server.main)
    assert hasattr(server.mcp, "list_tools")
    assert hasattr(server.work, "close_all")


def test_one_command_is_all_this_package_declares():
    """⛔ AND ITS NAME IS THE DASHED ONE, BECAUSE A CONSOLE SCRIPT IS TYPED.

    `pyproject.toml` is the only house of the name, and every other surface in
    the repository is checked against it by `tests/test_publishing_surfaces.py`.
    This is the console script's half of that: the key is what lands on the
    PATH, so it is the distribution's spelling, and the value is an import
    path, so it is the module's.
    """
    root = Path(__file__).resolve().parents[2]
    with open(root / "pyproject.toml", "rb") as fh:
        scripts = tomllib.load(fh)["project"]["scripts"]
    assert scripts == {"invisible-playwright-mcp": "invisible_playwright_mcp.cli:main"}


def test_the_command_without_a_subcommand_serves_over_stdio(monkeypatch):
    from invisible_playwright_mcp import cli

    called = []
    monkeypatch.setattr(cli, "_serve", lambda: called.append(True))
    result = CliRunner().invoke(cli.main, [])
    assert result.exit_code == 0, result.output
    assert called == [True]


def test_the_ui_subcommand_does_not_start_the_server(monkeypatch):
    from invisible_playwright_mcp import cli

    called = []
    monkeypatch.setattr(cli, "_serve", lambda: called.append(True))
    result = CliRunner().invoke(cli.main, ["ui", "--help"])
    assert result.exit_code == 0, result.output
    assert called == []


def test_python_m_the_module_is_the_cli():
    import invisible_playwright_mcp.__main__ as entry
    from invisible_playwright_mcp import cli

    assert entry.main is cli.main
