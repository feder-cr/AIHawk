import pytest
from mcp import ClientSession
from mcp.client.stdio import stdio_client

from invisible_playwright_mcp.mcp import store
from invisible_playwright_mcp.mcp import __version__ as package_version

from _stdio_helpers import server_params


async def test_stdio_lists_tools():
    async with stdio_client(server_params()) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            names = {t.name for t in (await mcp.list_tools()).tools}
            assert {"browser_navigate", "browser_take_screenshot"} <= names


async def test_the_handshake_says_which_build_this_is():
    """⛔ THE VERSION ON THE WIRE IS OURS, NOT THE SDK'S.

    `initialize` answers with a serverInfo, and a client uses it to say what
    it connected to and to tie a defect to a release. `FastMCP` accepts no
    `version=`, so the low-level server fell back to
    `importlib.metadata.version("mcp")` and every build of this package
    announced itself as the version of the SDK. Measured 2026-09-13 before the
    fix: `1.28.0`.

    Asserted here rather than in-process because this is a fact about the
    HANDSHAKE, and the handshake only happens over a transport.
    """
    async with stdio_client(server_params()) as (read, write):
        async with ClientSession(read, write) as mcp:
            got = await mcp.initialize()
            info = got.serverInfo
            assert info.name == "stealth", info.name
            assert info.version == package_version, (
                "the handshake says %r; this package is %r. A client cannot "
                "tell which build it is driving." % (info.version, package_version))
            from importlib.metadata import version as _installed
            sdk = _installed("mcp")
            assert info.version != sdk or package_version == sdk, (
                "the handshake is announcing %s, which is the installed mcp "
                "SDK's version. That is the defect this test exists for: the "
                "low-level server falls back to the library's version when "
                "nobody sets its own." % info.version)

            # ⛔ AND THE ASSERTION ABOVE CANNOT SEE THE SECOND DEFECT, BECAUSE
            # BOTH OF ITS SIDES READ THE SAME SOURCE. `info.version` and
            # `package_version` were equal all through the months the handshake
            # announced an install record fourteen releases behind the code:
            # equal, and both wrong. An assertion that cannot separate the two
            # answers of its instrument is checking that a value was echoed.
            #
            # So the expected value is computed here WITHOUT the module under
            # test: the install record, and the version declared by the tree
            # that record points at. When those disagree - an editable install
            # whose tree has moved, which is what CI and every developer
            # machine is - the wire must carry the TREE.
            import json
            import tomllib
            from importlib.metadata import distribution
            from pathlib import Path
            from urllib.parse import urlparse
            from urllib.request import url2pathname

            dist = distribution("invisible_playwright_mcp")
            written = dist.read_text("direct_url.json")
            recorded = json.loads(written) if written else {}
            if (recorded.get("dir_info") or {}).get("editable"):
                tree = Path(url2pathname(urlparse(recorded["url"]).path))
                declared = tomllib.loads(
                    (tree / "pyproject.toml").read_text(encoding="utf-8")
                )["project"]["version"]
                assert info.version.startswith(declared), (
                    "the handshake says %r while the code it is running "
                    "declares %r; the install record says %r and that is what "
                    "it used to announce" % (info.version, declared,
                                             dist.version))
                assert info.version.endswith("+editable"), (
                    "an editable tree announced itself as the published "
                    "release %r" % info.version)


async def test_a_refused_open_reaches_the_client_as_an_error():
    """⛔ A REFUSAL RETURNED AS A SUCCESSFUL RESULT IS A LIE THE PROTOCOL TELLS.

    `browser_open` had three failure paths that ended in `return`: a browser
    name that is not one of the two, a plan it would not make, and an engine
    that would not start. All three reached a client with `isError` false, so
    a careful one recorded a browser that had opened and a careless one went
    on to drive it. The sentences were always right; the flag was not.

    Driven over a real pipe rather than in-process, because `isError` is a
    property of the RESULT a client receives, and calling the function
    directly never builds one. This path needs no engine: the plan is refused
    before anything is launched.
    """
    async with stdio_client(server_params()) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            got = await mcp.call_tool("browser_open", {"profile": "none"})
    assert got.isError, (
        "the server refused to open a browser and told the client it had "
        "succeeded: %r" % got.content)
    said = " ".join(getattr(c, "text", "") for c in got.content)
    assert "refused" in said, said


async def test_every_tool_reaches_the_wire_with_its_hints():
    """⛔ WHAT IS REGISTERED IS NOT NECESSARILY WHAT GOES OUT.

    Every other check on the tool surface calls `server.mcp.list_tools()` in
    this process, which reads the registry rather than the protocol. If
    FastMCP ever stopped carrying a field, twelve green tests would say
    nothing and a client would see the loss. This one asks a real server over
    a real stdio pipe, and it asks about ALL of them: the sibling above
    checked two names out of sixteen.

    The three groups are the ones `_says` declares, and the reason five tools
    are additive rather than read-only is written where they are annotated.
    """
    read_only = {"browser_list", "browser_status", "browser_watch",
                 "browser_read_text", "browser_snapshot", "browser_read_html",
                 "browser_take_screenshot", "browser_evaluate"}
    additive = set()
    acts = {"browser_open", "browser_close", "browser_navigate", "browser_click",
            "browser_click_at", "browser_type", "browser_select_option",
            "browser_press_key"}
    async with stdio_client(server_params()) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            tools = (await mcp.list_tools()).tools
    by_name = {t.name: t for t in tools}
    assert set(by_name) == read_only | additive | acts, sorted(
        set(by_name) ^ (read_only | additive | acts))
    for name, t in sorted(by_name.items()):
        a = t.annotations
        assert a is not None, "%s reached the wire with no annotations" % name
        assert (a.title or "").strip(), "%s reached the wire with no title" % name
        assert (t.description or "").strip(), "%s has no description" % name
        assert t.inputSchema.get("type") == "object", name
    for name in read_only:
        assert by_name[name].annotations.readOnlyHint is True, name
    for name in additive:
        a = by_name[name].annotations
        assert a.readOnlyHint is False and a.destructiveHint is False, name
    for name in acts:
        assert by_name[name].annotations.destructiveHint is True, name


async def _open_main(session_id):
    """Spawn a real server told which piece of work it is, open its own
    browser, and hand back what it was declared with."""
    params = server_params({"INVISIBLE_MCP_SESSION_ID": session_id})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as mcp:
            await mcp.initialize()
            await mcp.call_tool("browser_open", {"seed": 4242})


# ⛔ AND `e2e`, BECAUSE `browser_open` STARTS A REAL ENGINE. That is what the
# marker means, and this test was missing it: measured 2026-09-11, the two
# servers below downloaded and extracted 665 MB of Firefox and launched it,
# in the fast job whose contract is that it has no engine. Green here in
# thirty seconds because the engine was already on this machine; on CI it hung
# the whole suite to the six-hour ceiling, three pushes running, reported as
# `in_progress` rather than as a failure. The `e2e` job runs it with the
# engine named, which is where a test that needs one belongs.
@pytest.mark.e2e
async def test_two_real_processes_with_two_session_ids_persist_to_two_files():
    """⛔ THE BLACK-BOX PROOF THAT `INVISIBLE_MCP_SESSION_ID` ACTUALLY WORKS, with real
    subprocesses rather than a monkeypatched module attribute. This is the
    ONLY place a second session id can still be reached from outside this
    process at all: not a tool argument any MCP client can send, but an
    environment variable whoever SPAWNS the process sets, exactly like
    `STEALTHFOX_SEED` a few lines above it in `mcp/server.py`.

    Known-bad: read `INVISIBLE_MCP_SESSION_ID` into a name that collides with another
    env var, or key the saved file by anything else. Both files would then be
    the same file, or the wrong one.
    """
    await _open_main("work")
    await _open_main("home")

    saved_work = store.load("work")
    saved_home = store.load("home")
    assert saved_work is not None and saved_home is not None, (
        "one process's file overwrote the other's: work=%r home=%r"
        % (saved_work, saved_home))
    assert saved_work["browsers"]["main"]["seed"] == 4242
    assert saved_home["browsers"]["main"]["seed"] == 4242
    assert saved_work is not saved_home
