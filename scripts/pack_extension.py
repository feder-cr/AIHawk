"""Build the Gemini CLI extension archives from this repository, and refuse
one that carries what it must not.

Installed from the git URL, the extension is a clone of the whole repository:
measured 2026-09-21, `gemini extensions install https://github.com/feder-cr/aihawk_mcp_server`
put docs, articles, tests and src on the person's disk to deliver two files,
`gemini-extension.json` and the setup skill. Gemini CLI installs from a
GitHub release instead when the Latest release carries an asset it can pick:
`{platform}.{name}.{extension}` per platform, or a single asset as the
fallback. Ours carry two MCP bundles already, so the fallback never applies
and the per-platform names are the road: three identical archives, one per
platform Gemini names (`darwin`, `linux`, `win32`), each fully contained,
with `gemini-extension.json` at its root. An archive is listed against an
allowed set before it ships, for the same reason the bundle is: an ignore
file is a list of what to drop, and a secret is what nobody thought to list.

    python scripts/pack_extension.py                # dist/<platform>.aihawk-extension.zip x3
    python scripts/pack_extension.py --output /tmp/e
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: The whole of what an extension archive may hold: the manifest Gemini reads,
#: the skill it lists, and the three files a person expects to find beside any
#: package. Nothing that runs: the server comes from the index, `uvx aihawk`.
ALLOWED = ("gemini-extension.json", "skills/", "LICENSE", "README.md",
           "assets/aihawk-icon-400.png")
#: Names that must not appear anywhere in an archive path, whatever the prefix.
FORBIDDEN_PARTS = (".env", ".git", "__pycache__", "tests", "docs", "articles", "src", "scripts")
#: The platform names Gemini CLI matches assets on (Node's `process.platform`).
PLATFORMS = ("darwin", "linux", "win32")


def asset_name(platform: str) -> str:
    return "%s.aihawk-extension.zip" % platform


def archive_findings(names):
    """Why the archive must not ship, or nothing.

    `names` are the entries of the zip. Every entry must sit under ALLOWED, no
    entry may carry a forbidden part, and the manifest must be at the root -
    Gemini requires it there, and an archive rooted one directory down installs
    nothing.
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
    for must in ("gemini-extension.json", "skills/setup/SKILL.md", "LICENSE"):
        if must not in names:
            out.append("%s is missing from the archive" % must)
    return out


def members() -> list[pathlib.Path]:
    """The files to pack: tracked, not ignored, and inside the allowed set."""
    tracked = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=ROOT, capture_output=True, check=True).stdout
    chosen = []
    for rel in tracked.decode("utf-8").split("\0"):
        if rel and any(rel == a or rel.startswith(a) for a in ALLOWED) and (ROOT / rel).is_file():
            chosen.append(pathlib.Path(rel))
    return sorted(chosen)


def pack(output: pathlib.Path) -> list[pathlib.Path]:
    output.mkdir(parents=True, exist_ok=True)
    files = members()
    names = [f.as_posix() for f in files]
    findings = archive_findings(names)
    if findings:
        for line in findings:
            print("[extension] " + line, file=sys.stderr)
        raise SystemExit(1)
    made = []
    for platform in PLATFORMS:
        path = output / asset_name(platform)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                zf.write(ROOT / f, f.as_posix())
        with zipfile.ZipFile(path) as zf:
            again = archive_findings(zf.namelist())
        if again:
            raise SystemExit("the packed archive %s fails its own check: %s" % (path, again))
        made.append(path)
    return made


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--output", default=str(ROOT / "dist"))
    args = ap.parse_args(argv)
    for path in pack(pathlib.Path(args.output)):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
