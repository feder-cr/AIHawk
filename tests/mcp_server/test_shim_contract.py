"""`aihawk` with no subcommand is the server, and the old name is a shim over it.

The PyPI package invisible-playwright-mcp ships, since its 0.16.0, three files
that re-export `aihawk.mcp.server` and a console script that points at
`aihawk.mcp.server:main`; every client that registered
`uvx invisible-playwright-mcp` runs through those names. The shim lives in an
archived repository and cannot follow a rename, so the names are pinned here.

New registrations use `uvx aihawk`, and the interface spawns `python -m aihawk`:
the group with no subcommand serves over stdio, which is the second contract
pinned here. It is the one command this package declares.
"""
import tomllib
from pathlib import Path

from click.testing import CliRunner


def test_the_names_the_shim_binds_exist():
    from aihawk.mcp import server

    assert callable(server.main)
    assert hasattr(server.mcp, "list_tools")
    assert hasattr(server.registry, "close_all")


def test_aihawk_is_the_only_command_this_package_declares():
    root = Path(__file__).resolve().parents[2]
    with open(root / "pyproject.toml", "rb") as fh:
        scripts = tomllib.load(fh)["project"]["scripts"]
    assert scripts == {"aihawk": "aihawk.cli:main"}


def test_aihawk_without_a_subcommand_serves_over_stdio(monkeypatch):
    from aihawk import cli

    called = []
    monkeypatch.setattr(cli, "_serve", lambda: called.append(True))
    result = CliRunner().invoke(cli.main, [])
    assert result.exit_code == 0, result.output
    assert called == [True]


def test_aihawk_ui_does_not_start_the_server(monkeypatch):
    from aihawk import cli

    called = []
    monkeypatch.setattr(cli, "_serve", lambda: called.append(True))
    result = CliRunner().invoke(cli.main, ["ui", "--help"])
    assert result.exit_code == 0, result.output
    assert called == []


def test_python_m_aihawk_is_the_cli():
    import aihawk.__main__ as entry
    from aihawk import cli

    assert entry.main is cli.main
