"""The Codex plugin is INSTALLED and asked what it delivers, by the real client.

Same reason as `test_the_plugin_really_installs.py`: the Claude Code plugin
1.0.0 validated against every document and delivered zero servers, and only
running the client said so. Measured by hand on 2026-09-21 with codex-cli
0.155.1 (through `npx -y @openai/codex@latest`, in a throwaway `CODEX_HOME`):
`plugin marketplace add <this checkout>` registers `feder-cr`, `plugin add
aihawk@feder-cr` installs, `mcp list` shows `aihawk  uvx  aihawk  enabled`,
the cache carries `skills/setup`, and the listed version is `1.0.0` whatever
the manifest says - so the version is not asserted here.

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

CODEX = shutil.which("codex")
needs_codex = pytest.mark.skipif(
    CODEX is None, reason="the codex CLI is not on PATH, so no client can be asked")


def _run(args, home, timeout=180):
    env = dict(os.environ, CODEX_HOME=str(home))
    return subprocess.run([CODEX, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=timeout, cwd=str(home))


@pytest.fixture()
def installed():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="aihawk-codex-plugin-"))
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
        shipped = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        under_test = dict(shipped, name="aihawk-under-test")
        (market / ".agents" / "plugins" / "marketplace.json").write_bytes(
            json.dumps(under_test, indent=1).encode("utf-8"))

        added = _run(["plugin", "marketplace", "add", str(market)], home)
        assert added.returncode == 0, added.stdout + added.stderr
        got = _run(["plugin", "add", "aihawk@aihawk-under-test"], home)
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
    row = [line for line in servers.splitlines() if line.startswith("aihawk")]
    assert row and "uvx" in row[0] and "enabled" in row[0], servers


@needs_codex
def test_the_installed_plugin_carries_the_setup_skill(installed):
    _, listing, home = installed
    assert "aihawk@aihawk-under-test" in listing and "installed" in listing, listing
    cached = list((home / "plugins" / "cache" / "aihawk-under-test" / "aihawk").glob("*/skills/setup/SKILL.md"))
    assert cached, "the setup skill is not in the installed plugin"
