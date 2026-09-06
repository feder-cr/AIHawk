"""The PyPI package invisible-playwright-mcp is a shim over this module.

Since 0.16.0 it ships three files that re-export `aihawk.mcp.server`, and its
console script points at `aihawk.mcp.server:main`; every client registered
with `uvx invisible-playwright-mcp` runs through those names. The shim lives
in an archived repository and cannot follow a rename, so the names are pinned
here: a rename that breaks them breaks every registered client at once.
"""
import importlib.metadata
import tomllib
from pathlib import Path


def test_the_names_the_shim_binds_exist():
    from aihawk.mcp import server

    assert callable(server.main)
    assert hasattr(server.mcp, "list_tools")
    assert hasattr(server.registry, "close_all")


def test_the_console_script_target_is_the_one_the_shim_declares():
    root = Path(__file__).resolve().parents[2]
    with open(root / "pyproject.toml", "rb") as fh:
        scripts = tomllib.load(fh)["project"]["scripts"]
    assert scripts["invisible-playwright-mcp"] == "aihawk.mcp.server:main"


def test_python_m_aihawk_mcp_is_the_entry_the_interface_spawns():
    import aihawk.mcp.__main__ as entry

    assert entry.main is importlib.import_module("aihawk.mcp.server").main
