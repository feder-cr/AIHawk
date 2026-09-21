"""The two listings this package publishes to describe the version that ships.

Two files in this repository are read by somebody else's machine, not by ours:

  1. `server.json` at the root is what `mcp-publisher` sends to the Official
     MCP Registry, and the registry checks the PyPI package it names for a
     `mcp-name: <server name>` token in the published description, which is
     README.md. A version in server.json that is not the version on the index
     is refused by the registry; a missing token is refused too, with
     "Registry validation failed for package".
  2. `manifest.json` at the root makes the repository itself the MCP bundle
     (MCPB manifest 0.4, server.type "uv"): `scripts/pack_bundle.py` zips
     the tracked tree minus `.mcpbignore`, and a host runs the server from
     the archive with `uv run --directory <bundle> python -m aihawk`, which
     installs the package from the bundle's own `pyproject.toml`. Until
     2026-09-13 the bundle was a separate `mcpb/` folder whose pyproject
     pinned the published package - a pointer to PyPI, spec-valid but not
     the layout the spec describes, and `type: python` with nothing bundled,
     which the spec forbids. Now the manifest carries a copy of the version
     and the archive carries the source.

That is three copies of one number (pyproject, server.json, the manifest)
and one token that must match a name. Each pair was written by hand on
2026-09-12 and they agreed; nothing made them agree. The registry job in
publish.yml runs on the tag, which is after the bump, and would only find out
at the end of a release. This test finds out on the pull request.

  3. Since 2026-09-13, five manifests at the root are read by plugin loaders
     and directory crawlers: `.claude-plugin/plugin.json` (the Claude Code
     plugin), `.mcp.json` (the only file Claude Code actually reads the server
     from - see MCP_FILES), `plugin.json` and `mcp.json` (the Agent Plugins
     standard, which cursor.directory scans for) and `gemini-extension.json`
     (the Gemini CLI gallery, which crawls the `gemini-cli-extension` topic).
     None of them carries the package version - a manifest that just says `uvx
     aihawk` does not change per release - but every one of them repeats the
     package name, the one-line description and the launch command, and the
     bundle manifest repeats the description too. Those are the copies this
     file makes agree.

     ⛔ THIS PARAGRAPH SAID SOMETHING ELSE UNTIL 2026-09-13 EVENING, AND IT
     CONTRADICTED THE CODE TEN LINES BELOW IT. It named `.cursor-plugin/
     plugin.json`, removed in #1316, and said the Claude manifest "points at
     `mcp.json`", which is the arrangement that shipped a plugin with no
     tools. `PLUGIN_FILES` had been right the whole time. A docstring that
     disagrees with the constant under it is how the next reader learns the
     wrong thing from the file that exists to teach the right one.

Every check is a function over strings and dicts, and a second test feeds them
known-bad input: a check that has only ever said "consistent" is not a check.
"""
from __future__ import annotations

import copy
import json
import pathlib
import re
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]

REGISTRY_NAME = "io.github.feder-cr/aihawk"


def _load():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return {
        "package_name": pyproject["project"]["name"],
        "version": pyproject["project"]["version"],
        "readme": (ROOT / "README.md").read_text(encoding="utf-8"),
        "server": json.loads((ROOT / "server.json").read_text(encoding="utf-8")),
        "requires_python": pyproject["project"]["requires-python"],
        "manifest": json.loads((ROOT / "manifest.json").read_text(encoding="utf-8")),
        "mcpbignore": (ROOT / ".mcpbignore").read_text(encoding="utf-8"),
        "plugins": {rel: json.loads((ROOT / rel).read_text(encoding="utf-8")) for rel in PLUGIN_FILES},
        "mcp_bytes": {rel: (ROOT / rel).read_bytes() for rel in MCP_FILES},
        "marketplace": json.loads((ROOT / MARKETPLACE).read_text(encoding="utf-8")),
    }


#: No `.cursor-plugin/plugin.json` since 2026-09-13 night: Cursor's own docs say
#: "A plugin that follows the Agent Plugins specification loads in Cursor
#: without changes", and that manifest is their format for rules, agents,
#: commands and hooks, none of which this plugin has. cursor.directory's scan
#: read `plugin.json` and `mcp.json` and never the logo that file carried.
PLUGIN_FILES = (".claude-plugin/plugin.json", "plugin.json", "mcp.json", ".mcp.json",
                "gemini-extension.json")
#: The setup skill Anthropic's submission guide recommends for a plugin whose
#: MCP server needs a one-time step ("Plugins can include a SETUP.md skill to
#: guide Claude through configuring and connecting any MCP servers bundled in
#: the plugin"). Ours is the engine download, and a plugin installed from the
#: directory never shows the README where that block lives. The block itself
#: is held identical to the README's by scripts/check_content.py, which scans
#: skills/ like a wiki page.
SETUP_SKILL = "skills/setup/SKILL.md"
#: ⛔ TWO NAMES FOR ONE CONFIGURATION, AND NEITHER IS OPTIONAL. Measured
#: 2026-09-13 by installing the plugin in this machine's Claude Code from a
#: local marketplace: with `mcp.json` and `"mcpServers": "./mcp.json"` in the
#: manifest, `claude plugin details aihawk` reports **MCP servers (0)** - the
#: plugin installs, validates, and delivers no tools at all. So does the
#: inline form. Only a file named `.mcp.json` at the plugin root is read, with
#: or without the manifest field, and it is read even carrying the Agent
#: Plugins `$schema` and `type` keys. Meanwhile the Agent Plugins spec (§7.2.1)
#: says the MCP configuration path is `mcp.json` and MUST NOT be loaded from an
#: alternative path, which is what cursor.directory scans for.
#:
#: Hence both names, byte-identical, held equal here. `claude plugin validate`
#: passed on the broken arrangement: a manifest that validates is not a
#: manifest that works, and only running the thing said so.
MCP_FILES = ("mcp.json", ".mcp.json")
LAUNCH = {"command": "uvx", "args": ["aihawk"]}
#: The marketplace this repository IS, so `claude plugin marketplace add
#: feder-cr/AIHawk` needs no catalog kept by anybody else: one entry, whose
#: source is the repository root, because the plugin is the repository. Held
#: here because it repeats the package name, the description and the author,
#: and because the README's install line names `<plugin>@<marketplace>`: the
#: marketplace's name is declared in that file and nowhere else, and the
#: README is held to it, so a rename there is a red README until the line a
#: reader copies follows. (The wiki is held to the README's line in turn, by
#: scripts/check_content.py.)
MARKETPLACE = ".claude-plugin/marketplace.json"


def _one_fact_many_files(manifest, plugins):
    """The facts that are stated in more than one manifest and were checked in
    none of them.

    ⛔ AN AUDIT ON 2026-09-13 COUNTED 24 DUPLICATED FACTS AND FOUND 9 WITH
    NOTHING HOLDING THEM TOGETHER: the licence in four files, the author in
    three, the keyword list in three, the repository url in four, the display
    title in three, and the registry's own description. Each is a hand-copy,
    each is invisible when it drifts, and a directory shows whichever copy it
    happened to read. The name, the description and the launch command were
    already held; these are the rest.

    Two differences are DELIBERATE and are asserted as differences, not
    smoothed away, because an unexplained difference is how the next reader
    decides one of them is a bug:

    * `homepage`. The bundle manifest has `homepage`, `documentation` and
      `support` as separate fields, so its homepage is the repository and its
      documentation is the wiki. A plugin manifest has only `homepage`, so it
      points at the wiki page for this server, which is the more useful of the
      two for somebody who just installed a plugin. Same fact, different field
      sets, and each file uses the most specific field it has.
    * the PyPI summary in `pyproject.toml`. It addresses somebody choosing a
      command to install, not somebody browsing a directory of MCP servers,
      and it is tuned for that. It is not a copy of the directory description
      and is not asserted to be one.
    """
    out = []
    title = manifest.get("display_name")
    for rel, doc in plugins.items():
        if rel.endswith("plugin.json"):
            if doc.get("license") != manifest.get("license"):
                out.append("%s licenses the package as %r, the bundle manifest says %r"
                           % (rel, doc.get("license"), manifest.get("license")))
            if (doc.get("author") or {}).get("name") != (manifest.get("author") or {}).get("name"):
                out.append("%s credits somebody other than the bundle manifest" % rel)
            if doc.get("keywords") != manifest.get("keywords"):
                out.append("%s carries different keywords from the bundle manifest, so the "
                           "directories that read them describe the package differently" % rel)
        shown = doc.get("displayName") if rel.endswith("plugin.json") else None
        if shown is not None and shown != title:
            out.append("%s shows the package as %r, the bundle manifest as %r"
                       % (rel, shown, title))
    repo = ((manifest.get("repository") or {}).get("url") or "").removesuffix(".git")
    for rel, doc in plugins.items():
        if rel.endswith("plugin.json"):
            theirs = doc.get("repository")
            if isinstance(theirs, dict):
                theirs = theirs.get("url")
            if (theirs or "").removesuffix(".git") != repo:
                out.append("%s points at a different repository from the bundle manifest" % rel)
    return out


def plugin_findings(package_name, manifest, plugins):
    """Why a plugin loader or a crawler would read something other than what
    ships, or nothing. `manifest` is the bundle's, whose description is the
    one the others must repeat."""
    out = []
    description = manifest.get("description")
    for rel in PLUGIN_FILES:
        if rel not in plugins:
            out.append("%s is missing" % rel)
    for rel, doc in plugins.items():
        if rel.endswith("plugin.json") or rel == "gemini-extension.json":
            if doc.get("name") != package_name:
                out.append("%s names %r, the project is %r" % (rel, doc.get("name"), package_name))
            if doc.get("description") != description:
                out.append("%s describes the package differently from the bundle manifest" % rel)
    out += _one_fact_many_files(manifest, plugins)
    claude = plugins.get(".claude-plugin/plugin.json") or {}
    if "mcpServers" in claude:
        out.append("the Claude plugin manifest declares mcpServers; measured, Claude Code ignores "
                   "both the path form and the inline form and reads only `.mcp.json` at the root, "
                   "so the field promises something it does not deliver")
    agent = plugins.get("plugin.json") or {}
    if agent.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
        out.append("plugin.json does not declare the Agent Plugins 1.0.0 schema, and a client rejects it")
    for rel, key in (("mcp.json", "aihawk"), (".mcp.json", "aihawk"), ("gemini-extension.json", "aihawk")):
        servers = (plugins.get(rel) or {}).get("mcpServers") or {}
        entry = servers.get(key) or {}
        if {k: entry.get(k) for k in LAUNCH} != LAUNCH:
            out.append("%s launches the server with %r, the README launches it with `uvx aihawk`"
                       % (rel, entry))
    for rel in MCP_FILES:
        mcp = plugins.get(rel) or {}
        if mcp.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json":
            out.append("%s does not declare the Agent Plugins 1.0.0 schema" % rel)
        if ((mcp.get("mcpServers") or {}).get("aihawk") or {}).get("type") != "stdio":
            out.append("%s does not say the transport is stdio, which the Agent Plugins schema requires" % rel)
    # The two manifests that carry a version carry the MANIFEST's version, not
    # the package's: `uvx aihawk` does not change per release. One number in
    # two files, so they are held equal here; bump both when the config changes.
    gemini = plugins.get("gemini-extension.json") or {}
    if not gemini.get("version"):
        out.append("gemini-extension.json has no version, which the gallery requires")
    if claude.get("version") != gemini.get("version"):
        out.append("the Claude plugin is at %r and the Gemini extension at %r; one config, one version"
                   % (claude.get("version"), gemini.get("version")))
    if claude.get("version") == "1.0.0":
        out.append("plugin version 1.0.0 is the one that shipped with no MCP server; a pinned "
                   "version only updates when it changes, so it must be past 1.0.0")
    return out


def marketplace_findings(package_name, manifest, market, readme):
    """Why `claude plugin marketplace add` plus `claude plugin install` would
    deliver something other than this plugin, or nothing.

    The marketplace file is read by Claude Code when a person registers the
    repository, and the entry's `source` is where the plugin is fetched from:
    anything but the root would install a directory that carries no
    `.mcp.json`, which is the zero-server plugin all over again by another
    route. The README is held to the marketplace name because that line is
    what a reader copies, and `aihawk@<old name>` after a rename fails with a
    message about a marketplace the reader never heard of."""
    out = []
    name = market.get("name") or ""
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        out.append("the marketplace name %r is not kebab-case, which Claude Code requires"
                   % name)
    if (market.get("owner") or {}).get("name") != (manifest.get("author") or {}).get("name"):
        out.append("the marketplace credits somebody other than the bundle manifest")
    entries = market.get("plugins") or []
    if len(entries) != 1:
        out.append("the marketplace lists %d plugins; this repository is one" % len(entries))
        return out
    entry = entries[0]
    if entry.get("name") != package_name:
        out.append("the marketplace entry names %r, the project is %r"
                   % (entry.get("name"), package_name))
    if entry.get("source") != "./":
        out.append("the marketplace entry's source is %r; the plugin is the repository "
                   "root, and a source anywhere else installs a plugin with no server"
                   % entry.get("source"))
    if entry.get("description") != manifest.get("description"):
        out.append("the marketplace entry describes the package differently from the "
                   "bundle manifest")
    install = "claude plugin install %s@%s" % (package_name, name)
    if install not in readme:
        out.append("the README does not install `%s`, so the marketplace and the "
                   "README disagree on where the plugin comes from" % install)
    return out


def setup_skill_findings(text):
    """Why the setup skill would not do its job, or nothing: a `name` and a
    `description` in the frontmatter (the Agent Skills format both Claude Code
    and Agent Plugins read), and the one command the whole skill exists for."""
    out = []
    if not text.startswith("---\n"):
        out.append("SKILL.md has no frontmatter")
    head = text.split("---")[1] if text.count("---") >= 2 else ""
    if not re.search(r"^name:\s*setup\s*$", head, re.M):
        out.append("the skill is not named setup")
    if not re.search(r"^description:\s*\S", head, re.M):
        out.append("the skill has no description")
    if "uvx invisible-playwright fetch" not in text:
        out.append("the skill does not run the engine download, which is its one job")
    return out


def registry_findings(package_name, version, readme, server, description=None):
    """Why the registry would refuse server.json, or nothing.

    ⛔ `description` WAS THE ONE DUPLICATED FACT THIS FUNCTION NEVER LOOKED AT.
    An audit on 2026-09-13 listed the registry's own description among the
    facts written in several files and checked in none, and the first pass at
    closing that gap covered the plugin manifests and left this one out - the
    registry is the single most visible listing we have. It is compared
    against the bundle manifest's, which is the authority the plugin manifests
    are already held to, so all six say one thing.
    """
    out = []
    if description is not None and server.get("description") != description:
        out.append("server.json describes the package differently from the bundle "
                   "manifest, and the registry is the listing most people see")
    if server.get("name") != REGISTRY_NAME:
        out.append("server.json names %r, the namespace is %r" % (server.get("name"), REGISTRY_NAME))
    if server.get("version") != version:
        out.append("server.json is %r, pyproject is %r" % (server.get("version"), version))
    packages = server.get("packages") or []
    if len(packages) != 1:
        out.append("expected one package entry, found %d" % len(packages))
    else:
        pkg = packages[0]
        if pkg.get("registryType") != "pypi":
            out.append("the package is not a pypi entry")
        if pkg.get("identifier") != package_name:
            out.append("the package identifier is %r, the project is %r" % (pkg.get("identifier"), package_name))
        if pkg.get("version") != version:
            out.append("the package entry says %r, pyproject is %r" % (pkg.get("version"), version))
        if (pkg.get("transport") or {}).get("type") != "stdio":
            out.append("the transport is not stdio")
    # The token must be followed by a boundary: whitespace, a tag, or the
    # comment close. Glued to a period it does not match on the registry side.
    if not re.search(r"mcp-name:\s*" + re.escape(REGISTRY_NAME) + r"(?=\s|-->|<)", readme):
        out.append("README.md carries no `mcp-name: %s` token" % REGISTRY_NAME)
    return out


#: What a host runs from the unpacked bundle. Measured 2026-09-13 on a fresh
#: copy of the tracked tree: `uv run` installs the project from the bundle's
#: pyproject (50 packages, 3.6 s) and `python -m aihawk` is the server;
#: `src/aihawk/__main__.py` run as a FILE fails on its relative import, which
#: is why the args say `python -m` and not the entry point's path.
BUNDLE_LAUNCH = {"command": "uv", "args": ["run", "--directory", "${__dirname}", "python", "-m", "aihawk"]}

#: Paths the bundle must not carry, each named in .mcpbignore. The archive
#: check in scripts/pack_bundle.py is the second wall; this is the first.
MUST_IGNORE = (".git/", ".github/", ".env", "tests/", "skills/", "docs/", "articles/", "scripts/",
               "assets/*", "!assets/aihawk-icon-400.png", "plugin.json", "mcp.json",
               ".mcp.json", "gemini-extension.json", "server.json")


def bundle_findings(package_name, version, requires_python, manifest, mcpbignore):
    """Why the bundle would not be the one the MCPB spec describes, or nothing.

    The spec (MANIFEST.md, "UV Runtime (v0.4+)") for a Python server whose
    dependencies cannot be bundled portably: manifest 0.4, server.type "uv", a
    pyproject.toml with the dependencies, no server/lib or server/venv; and
    the CLI's schema (mcpb-manifest-v0.4.schema.json) adds that `server`
    needs `type`, `entry_point` AND `mcp_config`, and that the root admits no
    field it does not list.
    """
    out = []
    if manifest.get("manifest_version") != "0.4":
        out.append("manifest_version is %r; server.type uv exists from 0.4" % manifest.get("manifest_version"))
    if manifest.get("version") != version:
        out.append("manifest is %r, pyproject is %r" % (manifest.get("version"), version))
    if manifest.get("name") != package_name:
        out.append("manifest name is %r, the project is %r" % (manifest.get("name"), package_name))
    for key in ("name", "version", "description", "author", "server"):
        if key not in manifest:
            out.append("manifest lacks %r, which the schema requires" % key)
    if not (manifest.get("author") or {}).get("name"):
        out.append("author.name is missing")
    if "tools" in manifest:
        # smithery-ai/cli#787: a manifest that declares tools is refused by
        # Smithery's registry with a 400, because MCPB tool entries carry no
        # inputSchema and the CLI forwards them as MCP tools that require one.
        # The field is optional in the spec, so leaving it out costs nothing.
        out.append("manifest declares tools, which Smithery refuses")
    server = manifest.get("server") or {}
    if server.get("type") != "uv":
        out.append("server type is %r, the spec's type for a Python server with compiled "
                   "dependencies is uv (Smithery's python variant is DERIVED by pack_bundle.py)"
                   % server.get("type"))
    entry = server.get("entry_point")
    if not entry or not (ROOT / entry).is_file():
        out.append("entry_point %r is not a file in the repository" % entry)
    if server.get("mcp_config") != BUNDLE_LAUNCH:
        out.append("mcp_config is %r, the host must run %r" % (server.get("mcp_config"), BUNDLE_LAUNCH))
    icon = manifest.get("icon")
    if not icon or icon.startswith("http") or not (ROOT / icon).is_file():
        out.append("icon %r is not a local file in the repository (Claude Desktop reads local icons only)" % icon)
    runtime = ((manifest.get("compatibility") or {}).get("runtimes") or {}).get("python")
    if runtime != requires_python:
        out.append("compatibility.runtimes.python is %r, pyproject requires %r" % (runtime, requires_python))
    if not manifest.get("privacy_policies") or "#privacy-policy" not in manifest["privacy_policies"][0]:
        out.append("the manifest does not point at the README's Privacy Policy section")
    for pattern in MUST_IGNORE:
        if pattern not in mcpbignore.splitlines():
            out.append(".mcpbignore does not name %r" % pattern)
    return out


def test_the_registry_entry_describes_the_package_that_ships():
    d = _load()
    assert registry_findings(d["package_name"], d["version"], d["readme"], d["server"],
                      d["manifest"]["description"]) == []


def test_the_bundle_is_the_one_the_spec_describes():
    d = _load()
    assert bundle_findings(d["package_name"], d["version"], d["requires_python"],
                           d["manifest"], d["mcpbignore"]) == []


def test_the_plugin_manifests_launch_the_package_that_ships():
    d = _load()
    assert plugin_findings(d["package_name"], d["manifest"], d["plugins"]) == []


def test_the_marketplace_installs_this_plugin_from_the_root():
    d = _load()
    assert marketplace_findings(d["package_name"], d["manifest"], d["marketplace"],
                                d["readme"]) == []


def test_the_marketplace_check_refuses_known_bad_input():
    d = _load()
    good = marketplace_findings(d["package_name"], d["manifest"], d["marketplace"], d["readme"])
    assert good == [], good

    # Renamed here and not in the README: the line a reader copies now names
    # a marketplace that does not exist.
    m = copy.deepcopy(d["marketplace"]); m["name"] = "aihawk"
    assert marketplace_findings(d["package_name"], d["manifest"], m, d["readme"])

    m = copy.deepcopy(d["marketplace"]); m["name"] = "Feder CR"
    assert marketplace_findings(d["package_name"], d["manifest"], m, d["readme"])

    m = copy.deepcopy(d["marketplace"]); m["owner"]["name"] = "somebody"
    assert marketplace_findings(d["package_name"], d["manifest"], m, d["readme"])

    m = copy.deepcopy(d["marketplace"]); m["plugins"].append(dict(m["plugins"][0]))
    assert marketplace_findings(d["package_name"], d["manifest"], m, d["readme"])

    m = copy.deepcopy(d["marketplace"]); m["plugins"][0]["name"] = "ai-hawk"
    assert marketplace_findings(d["package_name"], d["manifest"], m, d["readme"])

    # The one that ships a plugin with no server: a source that is not the root.
    m = copy.deepcopy(d["marketplace"]); m["plugins"][0]["source"] = "./plugins/aihawk"
    assert marketplace_findings(d["package_name"], d["manifest"], m, d["readme"])

    m = copy.deepcopy(d["marketplace"]); m["plugins"][0]["description"] = "something else"
    assert marketplace_findings(d["package_name"], d["manifest"], m, d["readme"])

    # The README installing from a marketplace name this file does not carry.
    stale = d["readme"].replace("aihawk@" + d["marketplace"]["name"], "aihawk@somewhere-else")
    assert stale != d["readme"]
    assert marketplace_findings(d["package_name"], d["manifest"], d["marketplace"], stale)


def test_the_setup_skill_is_there_and_does_its_one_job():
    text = (ROOT / SETUP_SKILL).read_text(encoding="utf-8")
    assert setup_skill_findings(text) == []


def test_the_setup_skill_check_refuses_known_bad_input():
    text = (ROOT / SETUP_SKILL).read_text(encoding="utf-8")
    assert setup_skill_findings(text) == []
    assert setup_skill_findings(text.replace("name: setup", "name: install"))
    assert setup_skill_findings(re.sub(r"^description:.*$", "description:", text, flags=re.M))
    assert setup_skill_findings(text.replace("uvx invisible-playwright fetch", "uvx aihawk"))
    assert setup_skill_findings(text.split("---", 2)[2])


def test_the_two_mcp_configurations_are_the_same_bytes():
    """`mcp.json` for Agent Plugins, `.mcp.json` for Claude Code: two names
    because two specifications demand two paths, one content because a second
    source of truth diverges. Byte equality, not "equivalent JSON", so a change
    to one is a change to both or it is a red test.

    ⛔ MEASURED, SO THE TWIN IS NOT A GUESS. Claude Code 2.1.258, four plugins
    with distinct names in one marketplace so no cache entry could collide,
    each installed into a throwaway `CLAUDE_CONFIG_DIR`: `.mcp.json` alone
    delivers the server, the manifest pointer delivers none, the inline form
    delivers none, and BOTH FILES TOGETHER - what we ship - delivers one. The
    documentation describes all three forms; two of them do not work. So the
    duplication is imposed on us, not chosen, and the twin is proven harmless.

    ⛔ AND `.mcp.json` CARRYING THE AGENT PLUGINS `$schema` IS DELIBERATE.
    Claude Code asks for no `$schema` and ignores fields it does not know,
    which the measurement above confirms. Dropping it from that copy would buy
    a tidier file and cost the strongest property this pair has: that the two
    are the same bytes, which is what makes drift between them impossible to
    miss. A field a loader ignores is a smaller price than a second content to
    keep in step by hand.
    """
    d = _load()
    a, b = d["mcp_bytes"]["mcp.json"], d["mcp_bytes"][".mcp.json"]
    assert a == b, ("mcp.json and .mcp.json differ; they are one configuration under "
                    "two names that two different loaders require")


def test_the_readme_has_the_privacy_section_the_bundle_points_at():
    """The bundle manifest's `privacy_policies` URL is the README anchor; a
    heading renamed or removed leaves the bundle pointing at nothing, and a
    directory review rejects it outright."""
    d = _load()
    assert re.search(r"^## Privacy Policy\s*$", d["readme"], re.M), "README.md has no `## Privacy Policy` heading"


def test_the_checks_refuse_known_bad_input():
    d = _load()
    good = registry_findings(d["package_name"], d["version"], d["readme"], d["server"],
                      d["manifest"]["description"])
    assert good == [], good

    s = copy.deepcopy(d["server"]); s["description"] = "something else entirely"
    assert registry_findings(d["package_name"], d["version"], d["readme"], s,
                             d["manifest"]["description"])

    s = copy.deepcopy(d["server"]); s["version"] = "0.0.1"
    assert registry_findings(d["package_name"], d["version"], d["readme"], s,
                             d["manifest"]["description"])

    s = copy.deepcopy(d["server"]); s["packages"][0]["identifier"] = "somebody-else"
    assert registry_findings(d["package_name"], d["version"], d["readme"], s,
                             d["manifest"]["description"])

    stripped = d["readme"].replace("mcp-name: " + REGISTRY_NAME, "mcp-name: io.github.someone/else")
    assert registry_findings(d["package_name"], d["version"], stripped, d["server"],
                             d["manifest"]["description"])

    glued = d["readme"].replace("mcp-name: " + REGISTRY_NAME + " -->", "mcp-name: " + REGISTRY_NAME + ".-->")
    assert glued != d["readme"]
    assert registry_findings(d["package_name"], d["version"], glued, d["server"],
                             d["manifest"]["description"])

    def bundle(m=None, ignore=None):
        return bundle_findings(d["package_name"], d["version"], d["requires_python"],
                               m if m is not None else d["manifest"],
                               ignore if ignore is not None else d["mcpbignore"])

    m = copy.deepcopy(d["manifest"]); m["version"] = "0.0.1"
    assert bundle(m)

    m = copy.deepcopy(d["manifest"]); m["manifest_version"] = "0.3"
    assert bundle(m)

    m = copy.deepcopy(d["manifest"]); m["tools"] = [{"name": "browser_click", "description": "x"}]
    assert bundle(m)

    m = copy.deepcopy(d["manifest"]); m["server"]["type"] = "python"
    assert bundle(m)

    m = copy.deepcopy(d["manifest"]); m["server"]["entry_point"] = "src/missing.py"
    assert bundle(m)

    m = copy.deepcopy(d["manifest"]); m["server"]["mcp_config"]["args"] = ["run", "--directory", "${__dirname}", "src/aihawk/__main__.py"]
    assert bundle(m)

    m = copy.deepcopy(d["manifest"]); m["icon"] = "https://example.com/icon.png"
    assert bundle(m)

    m = copy.deepcopy(d["manifest"]); m["compatibility"]["runtimes"]["python"] = ">=3.8"
    assert bundle(m)

    m = copy.deepcopy(d["manifest"]); del m["author"]["name"]
    assert bundle(m)

    assert bundle(ignore=d["mcpbignore"].replace(".env\n", ""))
    assert bundle(ignore=d["mcpbignore"].replace("tests/\n", ""))

    assert plugin_findings(d["package_name"], d["manifest"], d["plugins"]) == []

    g = copy.deepcopy(d["plugins"]); del g["gemini-extension.json"]
    assert plugin_findings(d["package_name"], d["manifest"], g)

    # The six facts that were stated in several files and held by nothing.
    # Each drifts silently in a directory nobody re-reads, so each gets its
    # own mutation rather than one that moves them together.
    g = copy.deepcopy(d["plugins"]); g["plugin.json"]["license"] = "Apache-2.0"
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); g[".claude-plugin/plugin.json"]["author"]["name"] = "somebody"
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); g["plugin.json"]["keywords"] = ["browser"]
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); g[".claude-plugin/plugin.json"]["displayName"] = "Ai Hawk"
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"])
    g["plugin.json"]["repository"] = "https://github.com/somebody/else"
    assert plugin_findings(d["package_name"], d["manifest"], g)

    # ⛔ AND THE ONE THAT MUST NOT FIRE: the `.git` suffix is how the bundle
    # manifest spells the same repository, and a check that cannot see through
    # it would refuse a correct tree. Measured against the real files.
    g = copy.deepcopy(d["plugins"])
    g["plugin.json"]["repository"] = d["manifest"]["repository"]["url"]
    assert plugin_findings(d["package_name"], d["manifest"], g) == []

    g = copy.deepcopy(d["plugins"]); g["plugin.json"]["description"] = "something else"
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); g["gemini-extension.json"]["name"] = "ai-hawk"
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); g[".claude-plugin/plugin.json"]["version"] = "1.0.0"; g["gemini-extension.json"]["version"] = "1.0.0"
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); g["mcp.json"]["mcpServers"]["aihawk"]["command"] = "python"
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); g["gemini-extension.json"]["mcpServers"]["aihawk"]["args"] = ["aihawk", "ui"]
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); g["mcp.json"]["mcpServers"]["aihawk"].pop("type")
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); g[".claude-plugin/plugin.json"]["mcpServers"] = {"aihawk": LAUNCH}
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); g[".claude-plugin/plugin.json"]["mcpServers"] = "./mcp.json"
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); del g[".mcp.json"]
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); g[".mcp.json"]["mcpServers"]["aihawk"]["command"] = "python"
    assert plugin_findings(d["package_name"], d["manifest"], g)

    g = copy.deepcopy(d["plugins"]); g["gemini-extension.json"]["version"] = "9.9.9"
    assert plugin_findings(d["package_name"], d["manifest"], g)

    m = copy.deepcopy(d["manifest"]); m.pop("privacy_policies")
    assert bundle(m)
