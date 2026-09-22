"""The archive check of scripts/pack_extension.py, fed the archives it must
refuse, and the packer run for real against this checkout.

The Gemini CLI extension installed from the git URL is the whole repository;
the archives this script builds are what a release carries instead, one per
platform name Gemini matches. Same shape as the bundle test: a clean listing
passes, every forbidden thing is refused by name, and the real packer's
output passes its own check.
"""
from __future__ import annotations

import importlib.util
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pack_extension", ROOT / "scripts" / "pack_extension.py")
pack_extension = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack_extension)

CLEAN = ["gemini-extension.json", "skills/setup/SKILL.md", "LICENSE", "README.md",
         "assets/icon-400.png"]


def test_a_clean_listing_passes():
    assert pack_extension.archive_findings(CLEAN) == []


def test_the_check_refuses_what_must_not_ship():
    for extra in ("src/invisible_playwright_mcp/__init__.py", "tests/test_engine.py", "docs/mcp-server.md",
                  ".env", "skills/setup/.env", ".git/config", "manifest.json", "scripts/pack_extension.py"):
        findings = pack_extension.archive_findings(CLEAN + [extra])
        assert findings, "%s was let through" % extra


def test_the_check_refuses_an_archive_without_the_manifest_at_the_root():
    rooted_down = ["invisible_playwright_mcp/gemini-extension.json", "invisible_playwright_mcp/skills/setup/SKILL.md", "invisible_playwright_mcp/LICENSE"]
    assert any("missing" in f for f in pack_extension.archive_findings(rooted_down))


def test_the_platform_names_are_the_ones_gemini_matches():
    assert pack_extension.PLATFORMS == ("darwin", "linux", "win32")
    assert pack_extension.asset_name("linux") == "linux.invisible_playwright_mcp-extension.zip"


def test_the_packer_builds_three_identical_archives_that_pass_their_own_check(tmp_path):
    made = pack_extension.pack(tmp_path)
    assert [p.name for p in made] == [pack_extension.asset_name(p) for p in pack_extension.PLATFORMS]
    listings = []
    for path in made:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        assert pack_extension.archive_findings(names) == []
        assert "gemini-extension.json" in names and "skills/setup/SKILL.md" in names
        listings.append(names)
    assert listings[0] == listings[1] == listings[2]
    assert max(p.stat().st_size for p in made) < 512 * 1024, "an extension archive is not small"
