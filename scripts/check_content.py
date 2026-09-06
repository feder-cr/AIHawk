"""Content gates for this repository's published surface.

Five checks over docs/, articles/, assets/ and the README, each born from a
real incident rather than a hypothetical:

  1. Banned-topic scan. Pages on retired topics must not come back; a stale
     branch once squash-merged five of them straight onto main. Historical
     one-line mentions are pinned in an explicit allowance table.
  2. Dash and invisible-Unicode scan. No em/en dashes, and none of the
     invisible or formatting codepoints that text pipelines can smuggle in
     (zero-width, bidi controls, variation selectors, tag block).
  3. CLI-surface scan. Every `aihawk <subcommand>` a page teaches must exist
     in src/aihawk/cli.py. A release once removed a subcommand while 13 wiki
     pages still taught it.
  4. Internal links. Every `](page.md)` in docs/ must point at a page that
     exists, and image assets must carry no metadata chunks.
  5. The way in is written once. The README's code blocks are the source:
     the lines that install uv (one fence per system) and the line that
     fetches the engine, whose leading word is the launcher in front of every
     command (`uvx` today). A page that carries the uv installer carries
     those lines verbatim, every code block runs `aihawk ui`, the server and
     the fetch with the README's launcher, and no page teaches a way in that
     the README does not (`pip install aihawk`). On 2026-09-06 the route went
     uv, pip, uv in one day, and each flip touched the README plus twenty-odd
     wiki pages by hand.

Run: python scripts/check_content.py            (from the repo root)
     python scripts/check_content.py --selftest (prove the gate on known-bad)

Exit 0 clean, 1 findings, 2 usage error.
"""

import argparse
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BANNED_TERMS = [
    "job application", "job-application", "job applications",
    "apply to jobs", "job board", "cover letter", "job hunt", "job search",
]

# Path suffix -> max total banned-term hits allowed there, with the reason.
# A historical one-liner is allowed; a page ABOUT the topic is not.
ALLOWED_MENTIONS = {
    "docs/ai-browser-agent-open-source.md": 1,   # one line of project history
    "docs/openai-operator-open-source.md": 1,    # one line of project history
    "README.md": 1,                              # press-coverage link
}

INVISIBLE = {
    0x00A0, 0x00AD, 0x034F, 0x061C, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x180E,
    0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x202F, 0x205F, 0x2060, 0x2061,
    0x2062, 0x2063, 0x2064, 0x3164, 0xFEFF, 0xFFA0, 0xFFF9, 0xFFFA, 0xFFFB,
}
INVISIBLE_RANGES = [(0x2000, 0x200A), (0x202A, 0x202E), (0x2066, 0x2069),
                    (0xFE00, 0xFE0F), (0xE0000, 0xE007F), (0xE0100, 0xE01EF)]

PNG_OK = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM",
          b"sRGB", b"iCCP", b"sBIT", b"bKGD", b"hIST", b"pHYs", b"sPLT",
          b"tIME", b"acTL", b"fcTL", b"fdAT"}

# `aihawk <token>` counts as a command reference only in code-shaped contexts:
# after `uvx `, inside backticks, or in a quoted argv list.
CMD_RE = re.compile(r"(?:uvx\s+|[\"'`])aihawk[\"',\s]+([a-z][a-z-]*)")


# The way in is written once, in the README: the install block, and the
# launcher in front of every command. A page repeats them verbatim or not at
# all. Born 2026-09-06, when the route went uv, pip, uv in one day and each
# flip touched the README plus twenty-odd wiki pages by hand.
WAY_IN = ("aihawk ui", "invisible-playwright-mcp", "invisible-playwright fetch")
INSTALLER = "astral.sh/uv/install"
OTHER_WAYS = ("pip install aihawk", "pip install invisible-playwright-mcp",
              "pipx install aihawk", "pipx run aihawk")
FENCE = chr(96) * 3


def fenced_blocks(text):
    """The lines of every fenced code block, block by block, fences excluded."""
    blocks, current = [], None
    for line in text.split(chr(10)):
        if line.lstrip().startswith(FENCE):
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
            continue
        if current is not None:
            current.append(line)
    return blocks


def way_in(readme_text):
    """(launcher, install lines) as the README teaches them: every fenced line
    that installs uv, in order and once, plus the first fenced line that
    fetches the engine, whose leading word is the launcher. The README keeps
    one fence per system for the installer and a shared fence for the rest, so
    the lines are collected across fences rather than read from one block.
    (None, None) without a fetch line."""
    installer, fetch, launcher = [], None, None
    for block in fenced_blocks(readme_text):
        for line in block:
            if INSTALLER in line and line.rstrip() not in installer:
                installer.append(line.rstrip())
            if fetch is None and "invisible-playwright fetch" in line:
                before = line.split("invisible-playwright fetch")[0].split()
                launcher = before[-1] if before else ""
                fetch = line.rstrip()
    if fetch is None:
        return None, None
    return launcher, installer + [fetch]


def check_way_in(rel, text, launcher, block, readme_text):
    """Findings for one page against the README's way in."""
    out = []
    for other in OTHER_WAYS:
        if other in text and other not in readme_text:
            out.append("%s: teaches `%s`, a way in that the README does not"
                       % (rel, other))
    if INSTALLER in text and rel != "README.md":
        for want in block:
            if want not in text:
                out.append("%s: carries the uv installer but not the README's "
                           "line `%s`" % (rel, want.strip()))
    command_key = re.compile(r'command[\s"]*[:=]\s*"$')
    launcher_key = re.compile(r'command[\s"]*[:=]\s*"%s"' % re.escape(launcher))
    for lines in fenced_blocks(text):
        joined = chr(10).join(lines)
        for line in lines:
            for cmd in WAY_IN:
                for m in re.finditer(re.escape(cmd), line):
                    before = line[:m.start()]
                    if before.endswith("/"):
                        continue                      # a URL or a path
                    if command_key.search(before):
                        # `"command": "aihawk"`: the command IS the launcher slot
                        if launcher:
                            out.append("%s: config block starts `%s` directly, the "
                                       "README goes through `%s`" % (rel, cmd, launcher))
                        continue
                    if before.rstrip().endswith("[" + chr(34)):
                        # a JSON or TOML argv: the launcher sits on the command line
                        if launcher and not launcher_key.search(joined):
                            out.append("%s: config block runs `%s` with a command "
                                       "other than `%s`" % (rel, cmd, launcher))
                        continue
                    words = before.split()
                    got = re.split(r"[/=]", words[-1])[-1] if words else ""
                    if got != launcher:
                        out.append("%s: code block runs `%s %s`, the README runs "
                                   "`%s %s`" % (rel, got, cmd, launcher, cmd))
    return out


def cli_commands(cli_path):
    """Subcommands actually declared in cli.py (click's @main.command())."""
    src = cli_path.read_text(encoding="utf-8")
    cmds = set()
    # Non-greedy across the option decorators (which span multiple lines)
    # to the def that carries the command's name.
    for m in re.finditer(r"@main\.command\(\)[\s\S]*?def\s+(\w+)", src):
        cmds.add(m.group(1).replace("_", "-"))
    return cmds


def content_files(root):
    files = []
    for base in ("docs", "articles"):
        files.extend(sorted((root / base).rglob("*.md")))
    if (root / "README.md").exists():
        files.append(root / "README.md")
    return files


def check_tree(root):
    findings = []
    valid = cli_commands(root / "src" / "aihawk" / "cli.py") \
        if (root / "src" / "aihawk" / "cli.py").exists() else None

    docs_names = {f.stem for f in (root / "docs").glob("*.md")} | {"Home"}
    readme_text = (root / "README.md").read_text(encoding="utf-8") \
        if (root / "README.md").exists() else ""
    launcher, block = way_in(readme_text)

    for f in content_files(root):
        rel = f.relative_to(root).as_posix()
        raw = f.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        low = text.lower()

        hits = sum(low.count(t) for t in BANNED_TERMS)
        allowed = ALLOWED_MENTIONS.get(rel, 0)
        if hits > allowed:
            findings.append("%s: %d banned-topic mention(s), %d allowed"
                            % (rel, hits, allowed))

        for tell, name in ((b"\xe2\x80\x94", "em-dash"),
                           (b"\xe2\x80\x93", "en-dash")):
            if tell in raw:
                findings.append("%s: %s x%d" % (rel, name, raw.count(tell)))

        for ch in set(text):
            cp = ord(ch)
            if cp in INVISIBLE or any(lo <= cp <= hi
                                      for lo, hi in INVISIBLE_RANGES):
                findings.append("%s: invisible codepoint U+%04X" % (rel, cp))

        if valid is not None:
            for m in CMD_RE.finditer(text):
                token = m.group(1)
                if token not in valid:
                    findings.append(
                        "%s: teaches `aihawk %s`, which cli.py does not "
                        "define (valid: %s)"
                        % (rel, token, ", ".join(sorted(valid))))

        if f.parent == root / "docs":
            for m in re.finditer(r"\]\(([^)#\s]+?)\.md(#[^)]*)?\)", text):
                target = m.group(1)
                if "/" not in target and ":" not in target \
                        and target not in docs_names:
                    findings.append("%s: dead link -> %s.md" % (rel, target))

        if launcher is not None:
            findings.extend(check_way_in(rel, text, launcher, block, readme_text))

    for img in sorted((root / "assets").glob("*.png")) if (root / "assets").exists() else []:
        raw = img.read_bytes()
        if raw[:8] != b"\x89PNG\r\n\x1a\n":
            findings.append("%s: not a PNG" % img.name)
            continue
        off = 8
        while off + 8 <= len(raw):
            (length,) = struct.unpack(">I", raw[off:off + 4])
            ctype = raw[off + 4:off + 8]
            if ctype not in PNG_OK:
                findings.append("assets/%s: metadata chunk %s"
                                % (img.name, ctype.decode("latin1")))
            if ctype == b"IEND":
                break
            off += 8 + length + 4

    return findings


def selftest():
    import tempfile
    failures = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "docs").mkdir()
        (root / "articles").mkdir()
        (root / "assets").mkdir()
        (root / "src" / "aihawk").mkdir(parents=True)
        # Mirrors the real file's shape: multi-line option decorators
        # between the command decorator and the def.
        (root / "src" / "aihawk" / "cli.py").write_bytes(
            b"@main.command()\n"
            b'@click.option("--model", default=None,\n'
            b'              help="Model id.")\n'
            b"def ui(model):\n    pass\n")
        # The README is the source the fifth check reads: one block, one
        # launcher, the same shape as the real page.
        (root / "README.md").write_bytes(
            b"# AIHawk\n\nWindows:\n\n```powershell\n"
            b'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"\n'
            b"```\n\nLinux:\n\n```bash\n"
            b"curl -LsSf https://astral.sh/uv/install.sh | sh\n"
            b"```\n\nThen, in a new terminal, on either:\n\n```bash\n"
            b"uvx invisible-playwright fetch\n"
            b"uvx aihawk ui --openrouter-key sk-or-...\n"
            b"```\n")

        bad = {
            "banned topic": ("docs/spam.md",
                             b"How to automate your job application flow\n"),
            "em-dash": ("docs/dash.md", "text \u2014 more\n".encode()),
            "invisible codepoint": ("docs/zw.md",
                                    "wor\u200bd\n".encode("utf-8")),
            "removed command": ("docs/old.md",
                                b'run `uvx aihawk do "task"` daily\n'),
            "argv-list command": ("docs/argv.md",
                                  b'subprocess.run(["uvx", "aihawk", "do"])\n'),
            "dead link": ("docs/link.md", b"see [x](missing-page.md)\n"),
            "bare launcher in a code block": (
                "docs/bare.md", b"```bash\naihawk ui --openrouter-key x\n```\n"),
            "a way in the README does not teach": (
                "docs/pip.md", b"run `pip install aihawk` first\n"),
            "installer without the README's block": (
                "docs/inst.md",
                b"```bash\ncurl -LsSf https://astral.sh/uv/install.sh | sh   "
                b"# Linux: uv, once\n```\n"),
            "one system's installer line, exact, without the rest": (
                "docs/onlyone.md",
                b"```bash\ncurl -LsSf https://astral.sh/uv/install.sh | sh\n```\n"),
            "config block with another launcher": (
                "docs/cfg.md",
                b'```json\n{"command": "python", '
                b'"args": ["invisible-playwright-mcp"]}\n```\n'),
        }
        for label, (rel, content) in bad.items():
            p = root / rel
            p.write_bytes(content)
            if not check_tree(root):
                failures.append("mutation not seen: " + label)
            p.unlink()

        import zlib
        def chunk(ctype, data):
            return (struct.pack(">I", len(data)) + ctype + data +
                    struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF))
        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0))
               + chunk(b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00x")
               + chunk(b"IDAT", zlib.compress(b"\x00\x00"))
               + chunk(b"IEND", b""))
        (root / "assets" / "meta.png").write_bytes(png)
        if not check_tree(root):
            failures.append("mutation not seen: png metadata chunk")
        (root / "assets" / "meta.png").unlink()

        good = {
            "clean page": ("docs/fine.md",
                           b"plain page, `uvx aihawk ui`, a - dash\n"),
            "allowed history line": ("docs/ai-browser-agent-open-source.md",
                                     b"it began as a job-application bot\n"),
            "prose verb": ("docs/verb.md",
                           b"what can AIHawk do for research\n"),
            "the README's install lines, verbatim": (
                "docs/same.md",
                b"```powershell\n"
                b'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"\n'
                b"```\n```bash\n"
                b"curl -LsSf https://astral.sh/uv/install.sh | sh\n"
                b"```\n```bash\n"
                b"uvx invisible-playwright fetch\n"
                b"```\n"),
            "config block with the README's launcher": (
                "docs/okcfg.md",
                b'```json\n{\n  "command": "uvx",\n'
                b'  "args": ["invisible-playwright-mcp"]\n}\n```\n'),
            "a unit file with a full path to the launcher": (
                "docs/unit.md",
                b"```ini\nExecStart=/usr/bin/uvx aihawk ui\n```\n"),
        }
        for label, (rel, content) in good.items():
            p = root / rel
            p.write_bytes(content)
            got = check_tree(root)
            if got:
                failures.append("false positive on %s: %s" % (label, got))
            p.unlink()

    if failures:
        for f in failures:
            print("SELFTEST FAIL: " + f)
        return 1
    print("selftest: %d mutations caught, %d clean cases pass"
          % (len(bad) + 1, len(good)))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    findings = check_tree(ROOT)
    if findings:
        for line in findings:
            print("[content] " + line)
        print("[content] %d finding(s)" % len(findings))
        sys.exit(1)
    print("[content] clean")
    sys.exit(0)


if __name__ == "__main__":
    main()
