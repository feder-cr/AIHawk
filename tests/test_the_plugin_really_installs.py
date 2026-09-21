"""The plugin is INSTALLED and asked what it delivers, by the real client.

⛔ THIS IS THE TEST THE 1.0.0 PLUGIN NEEDED AND DID NOT HAVE, and the reason
it is worth its cost. That revision declared its server with
`"mcpServers": "./mcp.json"` in the manifest, which the Claude Code
documentation describes as supported. `claude plugin validate` passed. Every
check we had passed, because every check we had compared our files against our
own belief about somebody else's loader. Installed, it delivered
`MCP servers (0)`: zero tools, to everyone who took it.

Worse, the suite ASSERTED the broken shape. `plugin_findings` failed unless
the manifest carried that pointer, so removing it - the fix - would have gone
red, and the known-bad battery listed the INLINE form, which the documentation
recommends, among the mutations to reject. A mutation test proves a gate sees
what you told it to see. It cannot tell you that what you told it is true.

Measured 2026-09-13 on Claude Code 2.1.258, four plugins with distinct names
in one marketplace so no cache entry could collide, each in a throwaway
`CLAUDE_CONFIG_DIR`:

    .mcp.json at the plugin root ......................... MCP servers (1)
    "mcpServers": "./mcp.json" in the manifest ........... MCP servers (0)
    "mcpServers": {...} inline in the manifest ........... MCP servers (0)
    both files, which is what we ship .................... MCP servers (1)

So the documentation is ahead of the product, or wrong, on two of the three
forms it describes. That is exactly why this file executes the client instead
of reading the docs.

WHAT THIS COSTS AND WHERE IT RUNS. It needs the `claude` CLI, which a CI
runner does not have, so it skips there and runs for anyone who has it.
`CLAUDE_CONFIG_DIR` points at a temporary directory, so nothing here touches
the person's own plugins, marketplaces or settings - checked, not assumed, by
the last test below.

WHAT IT DOES NOT COVER, said plainly: the marketplace is built from a COPY of
the files a Claude Code plugin consumes, not from the repository in place, so
that nothing here can register the real checkout anywhere. The copied set is
derived from `PLUGIN_SURFACE` below and asserted to exist, so a new component
directory that nobody adds there would be invisible to this test. The
marketplace file is the repository's own `.claude-plugin/marketplace.json`
with ONE field changed, its `name`, so that the cleanup test below can tell
the throwaway registration from a real one: the layout it describes - the
plugin at the marketplace root, `source` `./` - is the layout that ships, and
the layout the README's two lines install from. It also does not start the
server: `plugin details` reports the configuration, and what happens after a
client connects is `tests/mcp_server/test_stdio_e2e.py`.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Everything a Claude Code plugin of ours is made of. `.mcp.json` is the file
#: that carries the server; `mcp.json` is its Agent Plugins twin and rides
#: along because we ship it, and because the measurement above says a plugin
#: carrying both still delivers its server.
PLUGIN_SURFACE = (".claude-plugin", ".mcp.json", "mcp.json", "skills")

CLAUDE = shutil.which("claude")
needs_claude = pytest.mark.skipif(
    CLAUDE is None,
    reason="the claude CLI is not on this machine, so no client can be asked")


def _run(args, config_dir, timeout=180):
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(config_dir))
    done = subprocess.run([CLAUDE, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env,
                          timeout=timeout, cwd=str(config_dir))
    return done


@pytest.fixture()
def installed():
    """A throwaway config, a marketplace built from this checkout, installed.

    Yields `(details_text, config_dir)`. Everything is removed afterwards,
    including on failure.
    """
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="aihawk-plugin-"))
    try:
        config = tmp / "config"
        config.mkdir()
        # The marketplace root IS the plugin root, as in the repository.
        market = tmp / "market"
        market.mkdir()
        for name in PLUGIN_SURFACE:
            src = ROOT / name
            assert src.exists(), (
                "%s is named in PLUGIN_SURFACE and is not in the repository; "
                "this test would be measuring a plugin we do not ship" % name)
            if src.is_dir():
                shutil.copytree(src, market / name)
            else:
                shutil.copy2(src, market / name)
        shipped = json.loads((ROOT / ".claude-plugin" / "marketplace.json")
                             .read_text(encoding="utf-8"))
        assert shipped["plugins"][0]["source"] == "./", (
            "the shipped marketplace points somewhere other than the root; "
            "this test measures the root layout and would be measuring "
            "something else: %r" % shipped["plugins"][0])
        under_test = dict(shipped, name="aihawk-under-test")
        (market / ".claude-plugin" / "marketplace.json").write_bytes(
            json.dumps(under_test, indent=1).encode("utf-8"))

        added = _run(["plugin", "marketplace", "add", str(market)], config)
        assert added.returncode == 0, added.stdout + added.stderr
        got = _run(["plugin", "install", "aihawk@aihawk-under-test", "--yes"], config)
        assert got.returncode == 0, got.stdout + got.stderr
        shown = _run(["plugin", "details", "aihawk@aihawk-under-test"], config)
        assert shown.returncode == 0, shown.stdout + shown.stderr
        yield shown.stdout, config
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@needs_claude
def test_the_installed_plugin_delivers_its_mcp_server(installed):
    """The one number the 1.0.0 plugin got wrong."""
    details, _ = installed
    assert "MCP servers (1)" in details, (
        "the installed plugin does not deliver exactly one MCP server. This "
        "is the 1.0.0 defect, and no amount of validating files can see it.\n"
        + details)


@needs_claude
def test_the_installed_plugin_delivers_its_setup_skill(installed):
    """The skill is the other thing a directory review looks for, and it is
    discovered by directory convention (`skills/<name>/SKILL.md`), so a
    rename or a move breaks it silently the same way."""
    details, _ = installed
    assert "Skills (1)" in details, details


@needs_claude
def test_installing_touched_nothing_outside_its_own_config(installed):
    """⛔ THE CLEANUP IS PART OF THE TEST, not housekeeping around it.

    The first run of this experiment by hand left three installations behind
    in the real cache, orphaned rather than removed, and they were found days
    later. A test that installs software has to prove it installed it
    somewhere else.
    """
    _, config = installed
    real = pathlib.Path.home() / ".claude" / "plugins"
    known = real / "known_marketplaces.json"
    if known.exists():
        assert "aihawk-under-test" not in known.read_text(encoding="utf-8"), (
            "the test marketplace was registered in the real configuration")
    cache = real / "cache" / "aihawk-under-test"
    assert not cache.exists(), "the test plugin was cached in the real configuration"
    assert (config / ".claude.json").exists(), (
        "nothing was written to the throwaway config, so CLAUDE_CONFIG_DIR "
        "did not take effect and the assertions above prove nothing")
