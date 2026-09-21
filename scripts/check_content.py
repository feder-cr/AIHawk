"""Content gates for this repository's published surface.

Checks over docs/, articles/, assets/ and the README, each born from a real
incident rather than a hypothetical. How many there are is deliberately not
written here: this file said "five" while running six, and a hand-written count
inside the file that exists to catch stale numbers is the joke telling itself.
Count the numbered entries.

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
     in every fence that installs uv (one per system), the run from the
     installer line to the end of the fence, PATH line included, minus the
     line that runs the product (the interface fence ends with it); the
     first fenced line that runs `aihawk` names the launcher in front of
     every command (`uvx` today; until 0.69.0 the fetch line did, and the
     fetch line left the README when the server began downloading the engine
     itself); and the lines that tell a client the server exists, one per client
     (`claude plugin install aihawk@feder-cr`, `gemini extensions install
     ...`, `codex mcp add ...`). A page that carries the uv installer carries
     the install lines verbatim, every code block runs `aihawk` (the server,
     or `aihawk ui`) and the fetch with the README's launcher, a page that
     tells a client the server exists says it with the README's line or names
     the route bare, and no page teaches a way in that the README does not
     (`pip install aihawk`; `claude mcp add`, once the README moved to the
     plugin). On 2026-09-06 the route went uv, pip, uv in one day, and each
     flip touched the README plus twenty-odd wiki pages by hand; on
     2026-09-21 Claude Code moved from `claude mcp add` to the plugin and
     Gemini CLI from `gemini mcp add` to the extension, and five pages went
     on teaching the old lines with this check green, because it read only
     the installer lines.
  6. MCP-tool scan. Every `browser_*` or `session_*` tool a page teaches must
     be declared in the server. 0.39.0 and 0.41.0 between them removed nine
     tools, and four published pages went on teaching them - one told the
     reader to set the proxy at a tool that no longer exists.
  7. Tool-surface size. A page that publishes how big this server's tool
     surface is must publish the live figure. On 2026-09-13 eleven pages
     quoted a character count that was stale AND had been measured the wrong
     way, and nothing could go red about it: a number copied into prose has
     no link back to what it measured. This check is that link.

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
CMD_RE = re.compile(r"(?:uvx[ \t]+|[\"'`])aihawk[\"', \t]+([a-z][a-z-]*)")


# The way in is written once, in the README: the install block, and the
# launcher in front of every command. A page repeats them verbatim or not at
# all. Born 2026-09-06, when the route went uv, pip, uv in one day and each
# flip touched the README plus twenty-odd wiki pages by hand.
# `aihawk` alone is the server, `aihawk ui` the interface: one token covers
# both, matched as a whole word (never inside aihawk.mcp or a path).
WAY_IN = ("aihawk", "invisible-playwright fetch")
INSTALLER = "astral.sh/uv/install"
OTHER_WAYS = ("pip install aihawk", "pip install invisible-playwright-mcp",
              "pipx install aihawk", "pipx run aihawk")
#: How a client is told the server exists: the start of one line per client
#: in the README, and every form a README of this project has taught. A page
#: repeats the README's whole line, names the route bare in prose (`claude
#: plugin install`, as a noun), or says nothing; a route the README no longer
#: teaches is a way in the README does not, whichever form it takes.
CLIENT_WAYS = ("claude mcp add", "claude plugin marketplace add",
               "claude plugin install", "gemini mcp add",
               "gemini extensions install", "codex mcp add",
               "codex plugin marketplace add", "codex plugin add")
FENCE = chr(96) * 3


#: The languages in which a page can actually teach the way in: a shell, or a
#: client's config block. A `python` block cannot - there `aihawk` is a string
#: inside an argument list, not a command - and reading one as shell accuses
#: healthy code. Happened 2026-09-13 on `args=["-m", "aihawk"]` in a thirty-line
#: MCP client: the gate reported that the page runs `" aihawk`. A block with no
#: declared language stays in, because that is the form shell blocks use most.
WAY_IN_LANGUAGES = ("", "text", "sh", "bash", "shell", "console",
                    "powershell", "ps1", "json", "toml", "jsonc")


def fenced_blocks(text, only_languages=None):
    """The lines of every fenced code block, block by block, fences excluded.

    `only_languages` keeps just the blocks whose fence declares one of those
    languages, so a caller that reads blocks AS SHELL does not also read
    Python source as shell.
    """
    blocks, current, language = [], None, ""
    for line in text.split(chr(10)):
        stripped = line.lstrip()
        if stripped.startswith(FENCE):
            if current is None:
                current = []
                language = stripped[len(FENCE):].strip().lower()
            else:
                if only_languages is None or language in only_languages:
                    blocks.append(current)
                current = None
            continue
        if current is not None:
            current.append(line)
    return blocks


def runs(line, cmd):
    """Where `line` runs `cmd` as a command: (text before it, the word in the
    launcher slot) for each place. A URL or path segment (`.../aihawk`) is not
    one, and neither is a plugin id (`aihawk@feder-cr`, which `claude plugin
    install` takes: a name, not a command run). The launcher word is the last
    word before the command, stripped of `=` and `/` prefixes, so
    `ExecStart=/usr/bin/uvx aihawk ui` reads as `uvx`."""
    found = []
    pattern = r"(?<![\w./-])" + re.escape(cmd) + r"(?![\w./@-])"
    for m in re.finditer(pattern, line):
        before = line[:m.start()]
        if before.endswith("/"):
            continue
        words = before.split()
        found.append((before, re.split(r"[/=]", words[-1])[-1] if words else ""))
    return found


def way_in(readme_text):
    """(launcher, install lines, client lines) as the README teaches them.

    The README keeps one complete fence per system. In each fence that carries
    the uv installer, the install lines are the run from the installer line to
    the end of the fence, minus a line that runs the product: the installer
    itself asks for a PATH line before `uvx` works in the same shell, and a
    page that copies the installer without it teaches a command that fails.
    Collected in order and once across fences. The launcher is the word in
    front of the first fenced `aihawk` command. The client lines are every
    fenced line that starts with one of `CLIENT_WAYS`, stripped, in order and
    once. (None, None, None) when no fence runs the product, which is a README
    with nothing to derive from."""
    install, launcher, client = [], None, []
    for block in fenced_blocks(readme_text):
        taking = False
        for line in block:
            product = runs(line, WAY_IN[0])
            if product and launcher is None:
                launcher = product[0][1]
            if INSTALLER in line:
                taking = True
            if taking and line.strip() and not product and line.rstrip() not in install:
                install.append(line.rstrip())
            told = line.strip()
            if told.startswith(CLIENT_WAYS) and told not in client:
                client.append(told)
    if launcher is None:
        return None, None, None
    return launcher, install, client


def code_spans(text):
    """Every line of a shell or config fence, and every inline code span, as
    the strings a reader would copy."""
    spans = [line for lines in fenced_blocks(text, WAY_IN_LANGUAGES)
             for line in lines]
    spans.extend(re.findall(r"`([^`\n]+)`", text))
    return spans


def check_client_lines(rel, text, client):
    """Findings for one page against the lines that tell a client the server
    exists, as the README teaches them.

    Three cases per route. The route is not in the README at all: any mention
    of it, in code or in prose, teaches a way in the README does not. The
    route is in the README and the page says the whole line: it is the
    README's line or it is a finding. The route is in the README and the page
    names it bare, as a noun: fine, that is how prose refers to a command.
    """
    out = []
    for way in CLIENT_WAYS:
        taught = [line for line in client if line.startswith(way)]
        if way in text and not taught:
            out.append("%s: teaches `%s`, a way in that the README does not"
                       % (rel, way))
            continue
        for span in code_spans(text):
            said = span.strip()
            if said.startswith(way) and said != way and said not in client:
                finding = ("%s: teaches `%s`, the README's line is `%s`"
                           % (rel, said, "` or `".join(taught)))
                if finding not in out:
                    out.append(finding)
    return out


def check_way_in(rel, text, launcher, block, client, readme_text):
    """Findings for one page against the README's way in."""
    out = []
    for other in OTHER_WAYS:
        if other in text and other not in readme_text:
            out.append("%s: teaches `%s`, a way in that the README does not"
                       % (rel, other))
    if rel != "README.md":
        out.extend(check_client_lines(rel, text, client))
    if INSTALLER in text and rel != "README.md":
        for want in block:
            if want not in text:
                out.append("%s: carries the uv installer but not the README's "
                           "line `%s`" % (rel, want.strip()))
    command_key = re.compile(r'command[\s"]*[:=]\s*"$')
    launcher_key = re.compile(r'command[\s"]*[:=]\s*"%s"' % re.escape(launcher))
    for lines in fenced_blocks(text, WAY_IN_LANGUAGES):
        joined = chr(10).join(lines)
        for line in lines:
            for cmd in WAY_IN:
                for before, got in runs(line, cmd):
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


#: The MCP TOOL NAMES a page teaches, read from the server instead of
#: remembered. Twin of the CLI check above, born of the same failure a release
#: later: 0.39.0 and 0.41.0 between them removed the session tools, the focus
#: tool and the `session_id` parameter, and FOUR already published pages went
#: on teaching them - one told the reader to set the proxy "at `session_start`",
#: that is, to call a tool that no longer exists. The CLI check could not see
#: it: it looks at `aihawk <subcommand>`, and an MCP tool is not a subcommand.
#: The first draft accused THREE healthy lines out of seven, which is how a
#: gate goes red for the wrong reason and then gets switched off. All three
#: causes were legitimate: a PARAMETER shaped like a tool (`session_id`); the
#: historical note in `mcp-server.md`, which names removed tools precisely to
#: say they are gone; and ANOTHER server's tools - `browser_install` is
#: Microsoft's, on a page about theirs. The first two are handled here, the
#: third by the allowlist below, which like the banned-topic one carries its
#: reason beside each entry rather than being a mute list.
NON_TOOL = {"session_id", "browser_id", "session_name", "browser_name"}
TOOL_RE = re.compile(r"`((?:browser|session)_[a-z_]+)`")

#: (path, name) -> why that name may appear there without being one of ours.
TOOL_MENTIONS_ALLOWED = {
    ("docs/mcp-server.md", "browser_focus"):
        "the historical note saying it has not existed since 0.39.0",
    ("docs/playwright-mcp-browser-already-in-use.md", "browser_install"):
        "a tool of Microsoft's server, which is what the page is about",
    ("docs/how-to-build-an-mcp-server.md", "session_forget"):
        "cited as the defect of a test that could not tell that tool's two "
        "replies apart: a case told in the past tense, not an instruction "
        "to call it",
}


def tool_defs(server_path):
    """(name, docstring) of every function the server decorates with `.tool`.

    `ast` rather than a regex or an import. An import needs the server's
    dependencies, which the content gate may not have. A regex was what this
    used until 2026-09-13, `@\\w+\\.tool\\([^)]*\\)`, and it stopped at the
    first `)` inside the decorator's arguments: the day the decorators gained
    `annotations=ToolAnnotations(...)` it found no tool at all, and an empty
    set reads downstream as "no server to check against", which switched the
    tool-name check OFF without a word. A docstring is a literal in the file
    either way, and the decorator is a node with or without nested calls.
    """
    import ast

    tree = ast.parse(server_path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == "tool":
                out.append((node.name, ast.get_docstring(node, clean=False) or ""))
                break
    return out


def mcp_tools(server_path):
    """The tools the server actually declares."""
    return {name for name, _ in tool_defs(server_path)}


#: ⛔ A PUBLISHED NUMBER GOES STALE AND NOTHING SAYS SO, which is the failure
#: this whole check exists for. On 2026-09-13 eleven live pages quoted "8,639
#: characters" and "16 tools" for this server's tool surface. Both had to be
#: corrected by hand, and the only reason anybody looked was that a new page
#: needed the figure. Two independent errors were sitting there: the count was
#: stale (a release had lengthened descriptions), and it had been measured the
#: natural wrong way, by summing docstrings while what the protocol sends is a
#: name, a description AND a JSON schema per tool.
#:
#: The pattern is worth naming because the project keeps meeting it: a measured
#: number copied into prose has no link back to the thing it measured, so it
#: cannot go red. A gate is the link.
#:
#: What this checks: the TOOL COUNT and the TOTAL DESCRIPTION CHARACTERS, both
#: recomputed from the server's source with `ast` - no imports, no dependencies,
#: and verified on 2026-09-13 to agree with the running registry to the
#: character (16 tools, 9,145). A page may state them or not; if it states them,
#: they must be right.
#:
#: ⛔ What it does NOT see, said plainly so nobody trusts it wider than it is:
#: the TOKEN figure. Counting tokens needs a tokenizer this gate does not have
#: and should not grow a dependency for. The token count rides in the same
#: sentences as the character count, so a stale one is caught by its neighbour.
#:
#: ⛔ THAT USED TO READ "very likely caught", AND THE HEDGE WAS MEASURABLE.
#: Measured 2026-09-15, while moving the figure for real: of the fourteen pages
#: publishing the token count, TWO published it with no character count beside
#: it, so on those two the neighbour protected nothing and a stale number would
#: have shipped. The two were given the character figure they were missing, and
#: `check_token_has_a_neighbour` below now holds the arrangement instead of
#: hoping for it - which costs no tokenizer, because it checks that the guarded
#: number is present rather than that the unguarded one is right.
TOKENS_RE = re.compile(r"\*{0,2}([\d,]{3,})\*{0,2}\s+tokens\b")
SURFACE_TOOLS_RE = re.compile(r"\*{0,2}(\d+)\*{0,2}\s+tools\b")
#: Two shapes, because the corpus writes it two ways and the gate reads what
#: the corpus writes rather than demanding the corpus write what the gate
#: reads. The second shape was found by a surviving mutation on
#: `how-many-mcp-tools-is-too-many.md` - the one page whose whole subject IS
#: this number publishes it as a table row, which the prose pattern cannot see.
#: Being blind exactly there would have been the worst possible place.
SURFACE_CHARS_RE = re.compile(
    r"([\d,]+)\s+characters of (?:description|docstring)"
    r"|\|[^|]*\bcharacters\b[^|]*\|\s*\*{0,2}([\d,]+)\*{0,2}\s*\|")


def _surface_number(match):
    """The captured figure, whichever of the two shapes matched."""
    return match.group(1) or match.group(2)


def check_token_has_a_neighbour(rel, text, count):
    """A page publishing this server's TOKEN figure must publish the character
    figure too, because the character figure is the one this gate can check.

    ⛔ THE POINT IS NOT THE TOKEN NUMBER, WHICH NOTHING HERE CAN VERIFY. It is
    that a page carrying an unverifiable number should carry a verifiable one
    beside it, so moving the measurement cannot leave a stale figure behind
    with nothing to say so. Two pages published the token count alone until
    2026-09-15 and were exactly that hole.

    Scoped to pages that are talking about THIS server, by the same anchor the
    rest of this check uses: the tool count in bold beside the claim. A page
    quoting somebody else's token figure is not making this claim and is not
    accused of it.

    ⛔ AND THE ANCHOR IS ONLY THAT, because a looser one accused a healthy
    paragraph on the first run: `which-model-to-use-with-aihawk.md` says "our
    own" while talking about a MODEL's context window of 1,310,720 tokens,
    which is a token figure this gate has no business having an opinion about.
    A gate that is red on a correct line teaches people to route around it.
    """
    out = []
    ours = "**%d tools" % count
    for para in re.split(r"\n\s*\n", text):
        flat = " ".join(para.split())
        if ours not in flat:
            continue
        if not TOKENS_RE.search(flat):
            continue
        if SURFACE_CHARS_RE.search(flat):
            continue
        out.append(
            "%s: publishes a token figure for this server with no character "
            "figure beside it, and the character figure is the only one this "
            "gate can check: %s" % (rel, flat[:120]))
    return out


def tool_surface(server_path):
    """(tool count, total description characters) read from the source, by
    the same walk `mcp_tools` uses, so the two cannot disagree about what a
    tool is."""
    defs = tool_defs(server_path)
    return len(defs), sum(len(doc) for _, doc in defs)


def check_surface(rel, text, count, chars):
    """Findings for one page that publishes this server's tool-surface size.

    ⛔ THE CHARACTER COUNT IS THE ANCHOR, and the tool count is only checked
    beside it. The first draft checked every "N tools" in the corpus and
    accused FOUR healthy lines out of four: "around 15-25 tools from one server
    is workable" (a general guideline), "we shipped 24 tools and now ship 16"
    (true, and about the past), and twice "29 tools" about somebody else's
    product. That is how a gate goes red for the wrong reason and then gets
    switched off - the failure this file already records once.

    A tool count appears in prose for a dozen honest reasons. "N characters of
    description" appears for exactly one: describing THIS server, because
    nobody publishes a competitor's docstring byte count. So the character
    figure decides whether a paragraph is making the claim at all, and the
    tool count is verified only where it sits beside one. Nothing is lost by
    the narrowing: adding or removing a tool moves the character total too, so
    the anchor sees every change the tool count would have seen.

    Paragraph-scoped rather than line-scoped because the two numbers routinely
    land on different lines of the same sentence after wrapping.
    """
    out = []
    for para in re.split(r"\n\s*\n", text):
        flat = " ".join(para.split())
        m_chars = list(SURFACE_CHARS_RE.finditer(flat))
        if not m_chars:
            continue
        for m in m_chars:
            got = _surface_number(m)
            if int(got.replace(",", "")) != chars:
                out.append("%s: says %s characters of description, the server "
                           "declares %s" % (rel, got, format(chars, ",")))
        for m in SURFACE_TOOLS_RE.finditer(flat):
            if int(m.group(1)) != count:
                out.append("%s: says %s tools beside a description-size claim, "
                           "the server declares %d" % (rel, m.group(1), count))
    return out


def content_files(root):
    # `skills` since 2026-09-13: a plugin skill is a page a model reads, and
    # the setup skill carries the README's install block, so the fifth check
    # holds it to the README's lines like any wiki page.
    files = []
    for base in ("docs", "articles", "skills"):
        files.extend(sorted((root / base).rglob("*.md")))
    if (root / "README.md").exists():
        files.append(root / "README.md")
    return files


def check_tree(root):
    findings = []
    valid = cli_commands(root / "src" / "aihawk" / "cli.py") \
        if (root / "src" / "aihawk" / "cli.py").exists() else None

    server = root / "src" / "aihawk" / "mcp" / "server.py"
    tools = mcp_tools(server) if server.exists() else None
    surface = tool_surface(server) if server.exists() else None

    docs_names = {f.stem for f in (root / "docs").glob("*.md")} | {"Home"}
    readme_text = (root / "README.md").read_text(encoding="utf-8") \
        if (root / "README.md").exists() else ""
    launcher, block, client = way_in(readme_text)

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

        if tools:
            for m in TOOL_RE.finditer(text):
                name = m.group(1)
                if name in tools or name in NON_TOOL:
                    continue
                if (rel, name) in TOOL_MENTIONS_ALLOWED:
                    continue
                findings.append(
                    "%s: teaches the MCP tool `%s`, which the server does "
                    "not expose" % (rel, name))

        if f.parent == root / "docs":
            for m in re.finditer(r"\]\(([^)#\s]+?)\.md(#[^)]*)?\)", text):
                target = m.group(1)
                if "/" not in target and ":" not in target \
                        and target not in docs_names:
                    findings.append("%s: dead link -> %s.md" % (rel, target))

        if surface is not None:
            findings.extend(check_surface(rel, text, surface[0], surface[1]))
            findings.extend(check_token_has_a_neighbour(rel, text, surface[0]))

        if launcher is not None:
            findings.extend(check_way_in(rel, text, launcher, block, client,
                                         readme_text))

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
        # Il server, per il controllo sui tool MCP: due dichiarati e basta.
        (root / "src" / "aihawk" / "mcp").mkdir(parents=True)
        # The docstrings have a KNOWN length, because the seventh check
        # compares published numbers against this measurement: 2 tools, 8
        # characters. One decorator carries a nested call, the shape the
        # real file has had since the tools gained annotations: a reader that
        # stops at the first `)` sees one tool here, and the "removed MCP
        # tool" mutation below is then caught for the wrong reason or not at
        # all - the surface figures ("2 tools", 8 characters) are what pin it.
        (root / "src" / "aihawk" / "mcp" / "server.py").write_bytes(
            b'@mcp.tool(annotations=_says("Open", destructive=True))\n'
            b'async def browser_open(url):\n    """One."""\n'
            b'@mcp.tool()\ndef browser_click(selector):\n    """Two."""\n')
        # The README is the source the fifth check reads: one block, one
        # launcher, the same shape as the real page.
        (root / "README.md").write_bytes(
            b"# AIHawk\n\nWindows, in PowerShell:\n\n```powershell\n"
            b'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"\n'
            b'$env:Path = "$env:USERPROFILE\\.local\\bin;$env:Path"\n'
            b"uvx aihawk ui --openrouter-key sk-or-...\n"
            b"```\n\nLinux:\n\n```bash\n"
            b"curl -LsSf https://astral.sh/uv/install.sh | sh\n"
            b"source $HOME/.local/bin/env\n"
            b"uvx aihawk ui --openrouter-key sk-or-...\n"
            b"```\n\n"
            # The client lines, one route per client, as the real page has
            # them: what the eighth part of the fifth check reads.
            b"```bash\nclaude plugin marketplace add feder-cr/AIHawk\n"
            b"claude plugin install aihawk@feder-cr\n```\n\n"
            b"```bash\ncodex plugin marketplace add feder-cr/AIHawk\n"
            b"codex plugin add aihawk@feder-cr\n```\n\n"
            b"```bash\ngemini extensions install https://github.com/feder-cr/AIHawk\n```\n")

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
            # The real failure: a page teaching a tool a release removed.
            "removed MCP tool": ("docs/tool.md",
                                 b"set the proxy at `session_start`\n"),
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
            "the installer and the fetch without the PATH line between them": (
                "docs/nopath.md",
                b"```powershell\n"
                b'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"\n'
                b"uvx invisible-playwright fetch\n"
                b"```\n```bash\n"
                b"curl -LsSf https://astral.sh/uv/install.sh | sh\n"
                b"uvx invisible-playwright fetch\n"
                b"```\n"),
            "config block with another launcher": (
                "docs/cfg.md",
                b'```json\n{"command": "python", '
                b'"args": ["aihawk"]}\n```\n'),
            # The three shapes of the drift measured 2026-09-21, when the
            # README moved two clients to their install routes and the wiki
            # did not follow: the line the README dropped, the README's route
            # with a different line, and the dropped route named in prose.
            "a client line the README dropped": (
                "docs/dropped.md",
                b"```bash\nclaude mcp add --scope user stealth -- uvx aihawk\n```\n"),
            "the README's route with a line that is not the README's": (
                "docs/elsewhere.md",
                b"```bash\nclaude plugin install aihawk@somewhere-else\n```\n"),
            "a dropped route named bare, in prose": (
                "docs/named.md", b"one `gemini mcp add` command, once\n"),
            # The seventh check: a published number that no longer matches the
            # live measurement. The real failure of 2026-09-13, where eleven
            # pages carried a stale figure and nothing could notice.
            "stale description size, in prose": (
                "docs/size.md", b"ours is 8,639 characters of description\n"),
            "stale description size, in a table": (
                "docs/tbl.md",
                b"| | |\n|---|---|\n| Description characters | 8,639 |\n"),
            "stale tool count beside a size claim": (
                "docs/both.md",
                b"**24 tools**, 8 characters of description, resent every turn\n"),
            # The hole measured 2026-09-15: a token figure with nothing
            # checkable beside it. Two real pages were exactly this, and a
            # stale number there would have shipped without a word.
            "a token figure with no character figure beside it": (
                "docs/lonely.md",
                b"**2 tools**, 3,159 tokens, resent on every single turn\n"),
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
            # The three cases the first draft wrongly accused: a tool that
            # exists, a PARAMETER shaped like one, and a name that is not our
            # tool but another server's.
            "a tool that exists": ("docs/ok-tool.md",
                                   b"call `browser_open` then `browser_click`\n"),
            "a parameter shaped like a tool": ("docs/param.md",
                                               b"pass a `session_id` to it\n"),
            # The two the first draft of the seventh check wrongly accused: a
            # tool count that is not a claim about our surface, and one that
            # talks about the past.
            "a tool count that is a general guideline": (
                "docs/guide.md",
                b"around 15-25 tools from one server is workable\n"),
            "a tool count about the past, with no size claim": (
                "docs/past.md", b"we shipped 24 tools and now ship 2\n"),
            "the right figures": (
                "docs/right.md",
                b"**2 tools**, 8 characters of description, every turn\n"),
            "a token figure WITH the checkable one beside it": (
                "docs/pair.md",
                b"**2 tools**, 8 characters of description, 3,159 tokens "
                b"resent every turn\n"),
            # The healthy line the first draft accused: a token count about a
            # MODEL, on a page that also says "our own".
            "somebody else's token figure, on a page that says our own": (
                "docs/ctx.md",
                b"our own default model has a 1,310,720 token context window, "
                b"which is what stops a run\n"),
            "the README's install lines, verbatim": (
                "docs/same.md",
                b"```powershell\n"
                b'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"\n'
                b'$env:Path = "$env:USERPROFILE\\.local\\bin;$env:Path"\n'
                b"uvx invisible-playwright fetch\n"
                b"```\n```bash\n"
                b"curl -LsSf https://astral.sh/uv/install.sh | sh\n"
                b"source $HOME/.local/bin/env\n"
                b"uvx invisible-playwright fetch\n"
                b"```\n"),
            "config block with the README's launcher": (
                "docs/okcfg.md",
                b'```json\n{\n  "command": "uvx",\n'
                b'  "args": ["aihawk"]\n}\n```\n'),
            "a unit file with a full path to the launcher": (
                "docs/unit.md",
                b"```ini\nExecStart=/usr/bin/uvx aihawk ui\n```\n"),
            # The README's own client lines, verbatim. The word after
            # `install` is a plugin id, and reading it as the launcher slot
            # accused the README of running `install aihawk`.
            "the README's client lines, verbatim": (
                "docs/plugin.md",
                b"```bash\nclaude plugin marketplace add feder-cr/AIHawk\n"
                b"claude plugin install aihawk@feder-cr\n```\n"
                b"```bash\ngemini extensions install https://github.com/feder-cr/AIHawk\n```\n"),
            "a route the README teaches, named bare in prose": (
                "docs/noun.md",
                b"one `claude plugin install` command, once, and the tools are there\n"),
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
