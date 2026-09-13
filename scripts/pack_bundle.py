"""Build the MCP bundle (.mcpb) from this repository, and refuse one that
carries what it must not.

The repository IS the bundle: `manifest.json` at the root (server.type "uv",
MCPB manifest 0.4), `pyproject.toml` with the dependencies, the package under
`src/`, the icon. That is the layout the MCPB spec gives for Python servers
whose dependencies cannot be bundled portably (pydantic, which the MCP SDK
needs), and it is what `uv run --directory <bundle> python -m aihawk` runs.
`.mcpbignore` keeps everything else out; this script packs with the official
CLI and then LISTS the archive against an allowed set, because an ignore file
is a list of what to drop and a secret is what nobody thought to list.

Two things are staged before packing, on purpose:

  * Only files git knows and does not ignore are copied into the staging
    directory. A `.env` beside the manifest, which .gitignore names, never
    reaches the archive whatever the ignore file says; and the archive check
    below refuses one anyway.
  * `--smithery` rewrites `server.type` to "python" in the staged manifest.
    Smithery's CLI recognises python, node and binary only (measured
    2026-09-12: a uv-type manifest is refused with "Could not determine
    bundle runtime"), so the variant it gets is the same bundle with the one
    word it can read. The repository keeps the spec's word.

    python scripts/pack_bundle.py                 # dist/aihawk-<version>.mcpb
    python scripts/pack_bundle.py --smithery      # dist/aihawk-<version>-smithery.mcpb
    python scripts/pack_bundle.py --output /tmp/b # somewhere else
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: The whole of what a bundle may hold, as archive paths or path prefixes.
ALLOWED = ("manifest.json", "pyproject.toml", "README.md", "LICENSE",
           "assets/aihawk-icon-400.png", "src/aihawk/")
#: Names that must not appear anywhere in an archive path, whatever the prefix.
FORBIDDEN_PARTS = (".env", ".git", "__pycache__", "tests", "docs", "articles")


def archive_findings(names):
    """Why the archive must not ship, or nothing.

    `names` are the entries of the zip. Every entry must sit under ALLOWED, and
    no entry may carry a forbidden part; both halves, because an allowed prefix
    with a forbidden name inside it (`src/aihawk/.env`) is the case the first
    half cannot see.
    """
    out = []
    for name in names:
        if name.endswith("/"):
            continue
        if not any(name == a or name.startswith(a) for a in ALLOWED):
            out.append("%s is outside the allowed set" % name)
        parts = name.split("/")
        bad = [p for p in parts if p in FORBIDDEN_PARTS or p.startswith(".env")]
        if bad:
            out.append("%s carries %s" % (name, ", ".join(bad)))
    for must in ("manifest.json", "pyproject.toml", "src/aihawk/__init__.py",
                 "src/aihawk/__main__.py", "assets/aihawk-icon-400.png"):
        if must not in names:
            out.append("%s is missing from the archive" % must)
    return out


def stage(smithery: bool) -> pathlib.Path:
    """A copy of the tracked tree, with the Smithery rewrite if asked."""
    # Tracked files plus untracked ones that git does not ignore: a manifest
    # edited but not yet committed is packed, a `.env` that .gitignore names
    # is not, and whatever slips through is caught by the archive check.
    tracked = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8").split("\0")
    staging = pathlib.Path(tempfile.mkdtemp(prefix="aihawk-mcpb-"))
    for rel in tracked:
        if not rel:
            continue
        src = ROOT / rel
        if not src.is_file():
            continue
        dst = staging / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    if smithery:
        manifest_path = staging / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes().decode("utf-8"))
        assert manifest["server"]["type"] == "uv", manifest["server"]["type"]
        manifest["server"]["type"] = "python"
        manifest_path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    return staging


def main(argv=None) -> int:
    # The CLI prints an emoji in its summary; on a cp1252 console that kills
    # this script AFTER the archive is written and BEFORE it is checked.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--output", default=str(ROOT / "dist"), help="directory for the .mcpb")
    ap.add_argument("--smithery", action="store_true",
                    help="server.type python in the staged manifest, for Smithery's CLI")
    args = ap.parse_args(argv)

    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    manifest = json.loads((ROOT / "manifest.json").read_bytes().decode("utf-8"))
    if manifest["version"] != version:
        print("manifest.json is %s, pyproject.toml is %s: not packing a bundle that lies"
              % (manifest["version"], version))
        return 2

    out_dir = pathlib.Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "-smithery" if args.smithery else ""
    out = out_dir / ("aihawk-%s%s.mcpb" % (version, suffix))

    staging = stage(args.smithery)
    try:
        npx = "npx.cmd" if sys.platform == "win32" else "npx"
        r = subprocess.run([npx, "-y", "@anthropic-ai/mcpb", "pack", str(staging), str(out)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        sys.stdout.write(r.stdout)
        if r.returncode != 0:
            sys.stdout.write(r.stderr)
            print("mcpb pack failed (%d)" % r.returncode)
            return r.returncode
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    names = zipfile.ZipFile(out).namelist()
    findings = archive_findings(names)
    if findings:
        out.unlink()
        print("REFUSED, and the archive is deleted:")
        for f in findings:
            print("  " + f)
        return 1
    print("bundle: %s (%d entries, %d bytes)" % (out, len(names), out.stat().st_size))
    for n in sorted(names):
        print("  " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
