"""The Codex plugin is INSTALLED and asked what it delivers, by the real client.

Same reason as `test_the_plugin_really_installs.py`: the Claude Code plugin
1.0.0 validated against every document and delivered zero servers, and only
running the client said so. Measured by hand on 2026-09-21 with codex-cli
0.155.1 (through `npx -y @openai/codex@latest`, in a throwaway `CODEX_HOME`):
`plugin marketplace add <this checkout>` registers `feder-cr`, `plugin add
invisible-playwright-mcp@feder-cr` installs, `mcp list` shows
`invisible_playwright_mcp  uvx invisible-playwright-mcp  enabled`, the cache
carries `skills/setup`, and the listed version is `1.0.0` whatever the manifest
says - so the version is not asserted here.

That row was measured under the package's PREVIOUS name, and the two columns
are written here in today's spelling because they are two different names and
reading them as one is the mistake to avoid: the first is the mcpServers key,
which is the module, and the second is the command, which is the distribution.

It needs a `codex` on PATH, which a CI runner does not have and this machine
reaches only through npx, so it skips there and runs for anyone who has the
client installed. `CODEX_HOME` points at a temporary directory, so nothing
here touches the person's own marketplaces or plugins.
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

#: What a Codex plugin of ours is made of: the manifest, the marketplace it is
#: listed in, the server file its manifest points at, and the skills.
PLUGIN_SURFACE = (".codex-plugin", ".agents", ".mcp.json", "skills")

#: The names this test asks a real `codex` for, read from the manifests that
#: ship rather than typed. ⛔ THEY WERE TYPED, and the package rename on
#: 2026-09-23 left the Claude twin of this file asking for a plugin its
#: marketplace no longer carried. Two spellings are in play and they are not
#: interchangeable: the PLUGIN is the distribution's dashed name, and the row
#: `codex mcp list` prints is the mcpServers KEY, which is the module's.
SHIPPED_MARKETPLACE = json.loads(
    (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
PLUGIN = SHIPPED_MARKETPLACE["plugins"][0]["name"]
MARKET_UNDER_TEST = "%s-under-test" % PLUGIN
COORDINATE = "%s@%s" % (PLUGIN, MARKET_UNDER_TEST)
SERVER_KEY = next(iter(json.loads(
    (ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]))

CODEX = shutil.which("codex")
needs_codex = pytest.mark.skipif(
    CODEX is None, reason="the codex CLI is not on PATH, so no client can be asked")


def _run(args, home, timeout=180):
    env = dict(os.environ, CODEX_HOME=str(home))
    return subprocess.run([CODEX, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=timeout, cwd=str(home))


@pytest.fixture()
def installed():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="invisible_playwright_mcp-codex-plugin-"))
    try:
        home = tmp / "home"
        home.mkdir()
        market = tmp / "market"
        market.mkdir()
        for name in PLUGIN_SURFACE:
            src = ROOT / name
            assert src.exists(), "%s is named in PLUGIN_SURFACE and is not in the repository" % name
            if src.is_dir():
                shutil.copytree(src, market / name)
            else:
                shutil.copy2(src, market / name)
        under_test = dict(SHIPPED_MARKETPLACE, name=MARKET_UNDER_TEST)
        (market / ".agents" / "plugins" / "marketplace.json").write_bytes(
            json.dumps(under_test, indent=1).encode("utf-8"))

        added = _run(["plugin", "marketplace", "add", str(market)], home)
        assert added.returncode == 0, added.stdout + added.stderr
        got = _run(["plugin", "add", COORDINATE], home)
        assert got.returncode == 0, got.stdout + got.stderr
        servers = _run(["mcp", "list"], home)
        assert servers.returncode == 0, servers.stdout + servers.stderr
        listing = _run(["plugin", "list"], home)
        yield servers.stdout, listing.stdout, home
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@needs_codex
def test_the_installed_plugin_delivers_its_mcp_server(installed):
    servers, _, _ = installed
    row = [line for line in servers.splitlines() if line.startswith(SERVER_KEY)]
    assert row and "uvx" in row[0] and "enabled" in row[0], servers


@needs_codex
def test_the_installed_plugin_carries_the_setup_skill(installed):
    _, listing, home = installed
    assert COORDINATE in listing and "installed" in listing, listing
    cached = list((home / "plugins" / "cache" / MARKET_UNDER_TEST / PLUGIN).glob("*/skills/setup/SKILL.md"))
    assert cached, "the setup skill is not in the installed plugin"
