"""Start an unpacked bundle the way its manifest says, and speak MCP to it.

⛔ WHY THIS EXISTS: THE CI RAN `--help` AND CALLED IT PROOF. The `bundle` job
packed the archive, unpacked it and ran
`uv run --directory <unpacked> python -m invisible_playwright_mcp --help`, which prints click's
help text. A bundle whose server could not start, could not complete
`initialize`, or answered `tools/list` with nothing would have been green all
the way to a directory review, because `--help` never reaches any of that.

What this does instead, in the order a host does it:

1. reads `manifest.json` from the unpacked bundle, so the command under test
   is the one the manifest DECLARES rather than one written here a second
   time. `${__dirname}` is substituted the way the MCPB spec says a host
   substitutes it, with the bundle's own directory.
2. spawns that command as a subprocess over stdio.
3. completes the MCP handshake and reads `serverInfo`.
4. lists the tools and checks the set is the one the package registers.

Exit 0 on success, 1 with the reason on failure. It prints what it found, so
a CI log says which build and how many tools rather than nothing.

Run it with the bundle's own interpreter, so the `mcp` client library resolves
from the bundle's dependencies:

    uv run --directory /tmp/unpacked python scripts/bundle_speaks_mcp.py /tmp/unpacked
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import sys


def declared_command(bundle: pathlib.Path) -> tuple[str, list[str], dict]:
    """The command the manifest tells a host to run, with `${__dirname}` filled.

    The MCPB spec substitutes a small set of variables in `mcp_config`; the
    only one this bundle uses is `${__dirname}`, the extension's directory.
    Anything else is left alone and will simply fail to start, which is the
    honest outcome for a manifest asking for something a host does not supply.
    """
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    server = manifest["server"]
    config = server["mcp_config"]
    here = str(bundle)

    def fill(value: str) -> str:
        return value.replace("${__dirname}", here)

    command = fill(config["command"])
    args = [fill(a) for a in config.get("args", [])]
    env = {k: fill(v) for k, v in (config.get("env") or {}).items()}
    print("manifest: %s %s, server type %r, entry point %r"
          % (manifest["name"], manifest["version"], server["type"],
             server["entry_point"]))
    print("launching: %s %s" % (command, " ".join(args)))
    return command, args, env


async def handshake(bundle: pathlib.Path) -> int:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    command, args, env = declared_command(bundle)
    import os
    params = StdioServerParameters(command=command, args=args,
                                   env=dict(os.environ, **env))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            got = await asyncio.wait_for(session.initialize(), 120)
            info = got.serverInfo
            print("serverInfo: %s %s" % (info.name, info.version))
            tools = (await asyncio.wait_for(session.list_tools(), 60)).tools
            names = sorted(t.name for t in tools)
            print("tools (%d): %s" % (len(names), ", ".join(names)))
            if not names:
                print("FAIL: the bundle started and offered no tools")
                return 1
            missing = [t for t in tools if not (t.description or "").strip()]
            if missing:
                print("FAIL: tools with no description: %s"
                      % ", ".join(t.name for t in missing))
                return 1
            if not info.version:
                print("FAIL: the handshake carried no server version")
                return 1
    print("OK: the bundle starts from its own manifest and answers MCP")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    bundle = pathlib.Path(sys.argv[1]).resolve()
    if not (bundle / "manifest.json").is_file():
        print("no manifest.json under %s" % bundle)
        return 2
    try:
        return asyncio.run(handshake(bundle))
    except asyncio.TimeoutError:
        print("FAIL: the bundle did not answer in time")
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
