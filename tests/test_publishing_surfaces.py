"""The two listings this package publishes to describe the version that ships.

Two files in this repository are read by somebody else's machine, not by ours:

  1. `server.json` at the root is what `mcp-publisher` sends to the Official
     MCP Registry, and the registry checks the PyPI package it names for a
     `mcp-name: <server name>` token in the published description, which is
     README.md. A version in server.json that is not the version on the index
     is refused by the registry; a missing token is refused too, with
     "Registry validation failed for package".
  2. `mcpb/` is the source of the MCP bundle that Smithery distributes for
     local execution. Its manifest carries a version, and its pyproject pins
     the published package exactly, so a bundle at 0.43.0 installs aihawk
     0.43.0 and nothing else.

That is four copies of one number (pyproject, server.json, manifest, the pin)
and one token that must match a name. Each pair was written by hand on
2026-09-12 and they agreed; nothing made them agree. The registry job in
publish.yml runs on the tag, which is after the bump, and would only find out
at the end of a release. This test finds out on the pull request.

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
        "manifest": json.loads((ROOT / "mcpb" / "manifest.json").read_text(encoding="utf-8")),
        "bundle_pyproject": tomllib.loads((ROOT / "mcpb" / "pyproject.toml").read_text(encoding="utf-8")),
    }


def registry_findings(package_name, version, readme, server):
    """Why the registry would refuse server.json, or nothing."""
    out = []
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


def bundle_findings(package_name, version, manifest, bundle_pyproject):
    """Why the bundle would ship the wrong package, or nothing."""
    out = []
    if manifest.get("version") != version:
        out.append("manifest is %r, pyproject is %r" % (manifest.get("version"), version))
    if manifest.get("name") != package_name:
        out.append("manifest name is %r, the project is %r" % (manifest.get("name"), package_name))
    if "tools" in manifest:
        # smithery-ai/cli#787: a manifest that declares tools is refused by
        # Smithery's registry with a 400, because MCPB tool entries carry no
        # inputSchema and the CLI forwards them as MCP tools that require one.
        out.append("manifest declares tools, which Smithery refuses")
    server = manifest.get("server") or {}
    # "python", not "uv": Smithery's CLI recognises python, node and binary
    # only (measured 2026-09-12: a uv-type manifest is refused with "Could not
    # determine bundle runtime"). The entry point copes with either host.
    if server.get("type") != "python":
        out.append("server type is %r, Smithery accepts python" % server.get("type"))
    entry = server.get("entry_point")
    if not entry or not (ROOT / "mcpb" / entry).is_file():
        out.append("entry_point %r is not a file in mcpb/" % entry)
    deps = (bundle_pyproject.get("project") or {}).get("dependencies") or []
    want = "%s==%s" % (package_name, version)
    if deps != [want]:
        out.append("bundle dependencies are %r, expected [%r]" % (deps, want))
    if (bundle_pyproject.get("project") or {}).get("version") != version:
        out.append("bundle pyproject is %r, pyproject is %r" % (bundle_pyproject["project"].get("version"), version))
    return out


def test_the_registry_entry_describes_the_package_that_ships():
    d = _load()
    assert registry_findings(d["package_name"], d["version"], d["readme"], d["server"]) == []


def test_the_bundle_installs_the_version_that_ships():
    d = _load()
    assert bundle_findings(d["package_name"], d["version"], d["manifest"], d["bundle_pyproject"]) == []


def test_the_checks_refuse_known_bad_input():
    d = _load()
    good = registry_findings(d["package_name"], d["version"], d["readme"], d["server"])
    assert good == [], good

    s = copy.deepcopy(d["server"]); s["version"] = "0.0.1"
    assert registry_findings(d["package_name"], d["version"], d["readme"], s)

    s = copy.deepcopy(d["server"]); s["packages"][0]["identifier"] = "somebody-else"
    assert registry_findings(d["package_name"], d["version"], d["readme"], s)

    stripped = d["readme"].replace("mcp-name: " + REGISTRY_NAME, "mcp-name: io.github.someone/else")
    assert registry_findings(d["package_name"], d["version"], stripped, d["server"])

    glued = d["readme"].replace("mcp-name: " + REGISTRY_NAME + " -->", "mcp-name: " + REGISTRY_NAME + ".-->")
    assert glued != d["readme"]
    assert registry_findings(d["package_name"], d["version"], glued, d["server"])

    m = copy.deepcopy(d["manifest"]); m["version"] = "0.0.1"
    assert bundle_findings(d["package_name"], d["version"], m, d["bundle_pyproject"])

    m = copy.deepcopy(d["manifest"]); m["tools"] = [{"name": "browser_click", "description": "x"}]
    assert bundle_findings(d["package_name"], d["version"], m, d["bundle_pyproject"])

    m = copy.deepcopy(d["manifest"]); m["server"]["entry_point"] = "src/missing.py"
    assert bundle_findings(d["package_name"], d["version"], m, d["bundle_pyproject"])

    p = copy.deepcopy(d["bundle_pyproject"]); p["project"]["dependencies"] = ["aihawk>=0.1"]
    assert bundle_findings(d["package_name"], d["version"], d["manifest"], p)
