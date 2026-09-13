"""The archive check of scripts/pack_bundle.py, fed the archives it must refuse.

The repository is the MCP bundle, and `.mcpbignore` says what stays out. An
ignore file is a list of what somebody thought to drop; the check in
`pack_bundle.py` is the other direction, a list of what may be IN, and it
refuses anything else. This test does not pack (that needs the mcpb CLI and
runs in the `bundle` CI job); it feeds the check the listings that matter: a
clean one, a `.env`, a test file, a doc, the icon's sibling assets, and a
secret hidden under an allowed prefix.
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pack_bundle", ROOT / "scripts" / "pack_bundle.py")
pack_bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack_bundle)

CLEAN = ["manifest.json", "pyproject.toml", "README.md", "LICENSE", "assets/aihawk-icon-400.png",
         "src/aihawk/__init__.py", "src/aihawk/__main__.py", "src/aihawk/mcp/server.py",
         "src/aihawk/ui/page.html"]


def test_a_clean_listing_passes():
    assert pack_bundle.archive_findings(CLEAN) == []


def test_the_check_refuses_what_must_not_ship():
    for extra, why in [
        (".env", "carries"),
        ("tests/test_x.py", "outside"),
        ("docs/page.md", "outside"),
        ("articles/a.md", "outside"),
        ("assets/laboro.png", "outside"),
        ("server.json", "outside"),
        (".github/workflows/ci.yml", "outside"),
        ("src/aihawk/.env", "carries"),
        ("src/aihawk/__pycache__/x.pyc", "carries"),
    ]:
        findings = pack_bundle.archive_findings(CLEAN + [extra])
        assert any(why in f for f in findings), (extra, findings)


def test_the_check_refuses_an_archive_missing_the_server():
    for gone in ("manifest.json", "pyproject.toml", "src/aihawk/__main__.py", "assets/aihawk-icon-400.png"):
        listing = [n for n in CLEAN if n != gone]
        assert any("missing" in f for f in pack_bundle.archive_findings(listing)), gone
