"""The suite must not be able to see the session the person using AIHawk has.

⛔ A VERDICT THAT DEPENDS ON WHAT THE DEVELOPER LEFT OPEN IS NOT A VERDICT.
`tests/conftest.py` has pointed `AIHAWK_HOME` at a temporary directory since
sessions became persistent, and that covered every test BODY - but a fixture
runs when a test runs, and a module-level line runs when the file is IMPORTED,
which is earlier. One test module asks the server a question at import time,
that question reads the saved session, and so collection alone loaded the real
one: measured on the developer's machine, two tests in `test_addressing.py`
were red because the live session had its focus on a browser named after a job
search, and eight real URLs were carried into every test that followed. In
isolation they passed. On CI they passed, because CI has nothing saved to read.

This file is the gate for that, and it is deliberately not a scan for
module-level calls: it measures the property those calls depend on, which is
the same on every machine.

Known-bad: delete the `os.environ["AIHAWK_HOME"] = ...` line at the top of
`tests/conftest.py`. AT_IMPORT below then resolves to the platform's real
directory - `%APPDATA%/aihawk`, `~/.local/share/aihawk` - and the first
assertion goes red whether or not that directory happens to hold anything
today.
"""
from __future__ import annotations

import os

from aihawk.mcp import store

#: What a line running at import time sees. Captured HERE, at module level, on
#: purpose: read inside a test it would show the per-test directory and prove
#: nothing about the moment the defect lives in.
AT_IMPORT = store.home()


def _the_real_one():
    """Where sessions would be kept with nothing redirecting them."""
    keep = os.environ.pop("AIHAWK_HOME", None)
    try:
        return store.home()
    finally:
        if keep is not None:
            os.environ["AIHAWK_HOME"] = keep


def test_importing_a_test_module_cannot_reach_the_real_directory():
    real = _the_real_one()
    assert AT_IMPORT != real, (
        "at import time the tests read %s, which is where the person using "
        "AIHawk keeps their sessions: collecting the suite loads whatever they "
        "left open, and the run reports on that as much as on the product" % real)


def test_and_neither_can_a_test_body():
    """The fixture's half of the same promise, and the older one."""
    real = _the_real_one()
    assert store.home() != real
    assert os.environ.get("AIHAWK_HOME"), "the redirection is not in place"


def test_the_server_starts_each_test_holding_nothing():
    """The state the server keeps between calls is emptied per test, so what one
    test leaves behind is not an input to the next.

    Known-bad: drop the second autouse fixture from `conftest.py`. This stays
    green on its own - the poison needs another test to run first - so it is
    written as the contract rather than as a reproduction: these four are empty
    - or, for `_restored`, false - when a test begins, and any test may rely on
    that.
    """
    from aihawk.mcp import server

    for held in ("_seen_tabs", "_tabs_owed"):
        assert not getattr(server, held), (
            "server.%s arrived at this test with %r in it" % (held, getattr(server, held)))
    assert server._restored is False, (
        "server._restored arrived at this test already true")


def test_the_conftest_imports_nothing_the_light_jobs_do_not_have():
    """⛔ AN AUTOUSE FIXTURE RUNS FOR EVERY TEST IN THE REPOSITORY, so anything
    it imports becomes a dependency of every test - including the ones in jobs
    that deliberately install almost nothing.

    Measured on 2026-09-08: the fixture next door imported `aihawk.mcp.server`
    to clear four dicts, and the `version` and `releases` jobs, which run
    `pip install pytest` and nothing else because what they check is a version
    number and a set of release pages, both went red with `ModuleNotFoundError:
    No module named 'mcp'` at fixture setup - on tests that have no business
    knowing the server exists. Six matrix jobs were green at the same time.

    The state can only be dirty if something imported the module, so
    `sys.modules.get` answers the question without creating the dependency.

    Known-bad: put `from aihawk.mcp import server` back in the fixture. Costs a
    CI round trip to find out otherwise.
    """
    import pathlib
    import re

    source = (pathlib.Path(__file__).parent / "conftest.py").read_text(encoding="utf-8")
    code = re.sub(r'"""(?:.|\n)*?"""', "", source)
    reached = re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", code, re.M)
    allowed = {"__future__", "os", "sys", "tempfile", "pytest", "pathlib"}
    assert set(reached) <= allowed, (
        "conftest.py imports %s, and every test in the repository then needs "
        "it: the two jobs that install pytest alone would fail at fixture "
        "setup, on tests that never touch it"
        % sorted(set(reached) - allowed))


def test_a_run_that_did_not_ask_for_an_engine_cannot_reach_one():
    """⛔ THE FAST JOB HAS NO ENGINE, AND UNTIL 2026-09-11 NOTHING HELD IT TO IT.

    A test in the default selection spawned a real server and called
    `browser_open`, which downloaded and extracted 665 MB of Firefox plus a
    52 MB geoip database and launched the browser. It was green on the
    developer machine in thirty seconds, because the engine was already there,
    and on CI it took the suite from two minutes to the six-hour job ceiling,
    on three pushes running, without ever going red: a job that hangs reports
    `in_progress`, and `in_progress` reads as slow rather than as broken.

    The missing `e2e` marker was the defect; this is the guard, because a
    marker is the thing the next author forgets too. Same shape as the home
    above and for the same reason: measure the property, not the calls.

    Known-bad: delete the `INVISIBLE_PLAYWRIGHT_CACHE_DIR` block from
    `tests/conftest.py`. The first assertion then goes red on every machine,
    including one whose cache is warm and would otherwise never notice.
    """
    import pathlib

    cache = os.environ.get("INVISIBLE_PLAYWRIGHT_CACHE_DIR")
    assert cache, (
        "nothing points the engine cache away from the real one, so a test in "
        "the fast selection can download an engine and nobody will know until "
        "a CI job stops answering")
    where = pathlib.Path(cache)
    assert where.name.startswith("aihawk-no-engine-"), (
        "the cache points at %r, which is not the throwaway the conftest makes"
        % cache)
    assert os.environ.get("INVISIBLE_DOWNLOAD_DEADLINE") == "1", (
        "without the deadline a test that reaches for an engine still gets one, "
        "slowly, which is exactly the failure this exists to stop")
    # And it stayed empty, which is the claim itself rather than a proxy for it.
    # Order-dependent by construction: a test running after this one could still
    # fetch, and would be caught by the deadline instead.
    assert not list(where.iterdir()), (
        "a test in the fast selection fetched an engine into %s" % cache)


def test_the_guard_arms_exactly_when_the_engine_tests_are_deselected():
    """⛔ THE FIRST VERSION ASKED THE OTHER QUESTION AND WAS WRONG BOTH WAYS.

    It asked "did somebody request an engine". `-m "not (e2e or ui)"` requests
    neither, and it answered yes: the parentheses were stripped before the walk,
    so the `not` landed on `e2e` alone and `ui` read as a bare request. The
    guard was off for a run that cannot start a browser at all - the run it
    exists for. And `-m "not ui"` SELECTS the engine tests while answering no,
    so the guard armed and they died on the one second download deadline.

    The question that is actually needed is whether those tests are going to
    run. A plain `pytest -q` gets there through `addopts`, which never reaches
    argv, so the absence of `-m` is the ordinary run and the one to guard.

    Known-bad, and it is the shipped bug rather than an invented one: strip the
    parentheses before walking.
    """
    import conftest

    off = conftest._e2e_is_excluded
    #: deselected, so the guard belongs on.
    assert off(["pytest", "-q"]) is True
    assert off(["pytest", "-m", "not ui and not e2e"]) is True
    assert off(["pytest", "-m", "not (e2e or ui)"]) is True
    assert off(["pytest", "-m", "not(e2e or ui)"]) is True
    assert off(["pytest", "tests/mcp_server/test_stdio_e2e.py"]) is True, (
        "a path that happens to contain the marker name is not a marker")
    #: selected, or possibly selected, so the guard must stay out of the way.
    assert off(["pytest", "-m", "e2e", "tests/mcp_server"]) is False
    assert off(["pytest", "-me2e"]) is False
    assert off(["pytest", "-m", "e2e and not ui"]) is False
    assert off(["pytest", "-m", "not ui"]) is False, (
        "this one deselects `ui` and leaves the engine tests IN, so arming the "
        "guard kills them on the download deadline")


def test_only_one_place_knows_where_the_interface_is_stopped():
    """⛔ A TEST THAT DRIVES `aihawk ui` CAN SERVE FOREVER, AND ON 2026-09-11
    one did.

    `cli.ui` builds a `Sessions` registry and asks it for a conversation, so
    the only name worth patching is `aihawk.sessions.Link`. A test that
    patched `aihawk.link.Link` instead stopped nothing: the command ran on,
    uvicorn served the interface with no end, and all six CI matrix jobs hung
    to GitHub's six-hour ceiling on four pushes while reporting `in_progress`
    rather than failing. It was green on the developer machine only because
    that machine's own interface held port 8765, so the bind failed there.

    `_cli_brake` owns all three defences now - the seam, the proof that the
    brake fired, and an address nothing can bind - and this keeps them from
    being written a second time somewhere else, which is how the first one
    came to be wrong. The scan covers `test_*.py` only, so the module itself
    is out of scope by construction rather than by an exception: widen the
    glob and the gate starts accusing the one file allowed to do this.

    ⛔ READ FROM THE PARSE TREE, NOT FROM THE TEXT, and the first version was
    not: it stripped `#` comments and then failed on this very docstring,
    because the sentence naming the known-bad contains the call it forbids.
    That is a defect this project has measured twice before. Python's own
    parser is installed by definition here, so the gate uses it and the
    whole class - comments, docstrings, a string that merely looks like
    code - stops existing.

    `--help` is exempt: it prints and exits before anything is served.
    """
    import ast
    import pathlib

    here = pathlib.Path(__file__).parent
    offenders = []
    for path in sorted(here.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called = (node.func.attr if isinstance(node.func, ast.Attribute)
                      else getattr(node.func, "id", ""))
            if called != "invoke":
                continue
            words = [n.value for n in ast.walk(node)
                     if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            if "ui" in words and "--help" not in words:
                offenders.append("%s:%d" % (path.name, node.lineno))

    assert not offenders, (
        "these drive the interface command without going through _cli_brake, "
        "so nothing guarantees they ever stop: %s" % offenders)


def test_the_brake_module_still_carries_all_three_defences():
    """And the module has to still BE the three things, or the gate above is
    enforcing an import and nothing else.

    ⛔ RUN, NOT READ, AND THE FIRST VERSION READ. It asserted that the source
    CONTAINED `monkeypatch.setattr(sessions_mod, "Link", rec)` and the word
    `UNBINDABLE_HOST`, as substrings of the raw file - so a comment saying what
    the module must do satisfied it, and an import of the wrong module under
    the right spelling would too. That is the defect this project has recorded
    more than any other, and I wrote it into a gate about brakes on the same
    day I wrote another one that went red on its own docstring.

    Known-bad: aim the brake at the module that only DEFINES `Link`, or drop
    the reserved address from the runner. Both are invisible to a substring
    and both fail here.
    """
    import aihawk.sessions as sessions_mod

    import _cli_brake

    assert _cli_brake.UNBINDABLE_HOST.startswith("203.0.113."), (
        "the reserved address is gone, so a brake that goes inert can bind and "
        "serve: %r" % _cli_brake.UNBINDABLE_HOST)

    class _Recorder:
        """Enough of monkeypatch to see WHERE the brake is put."""

        def __init__(self):
            self.calls = []

        def setattr(self, target, name, value):
            self.calls.append((target, name, value))

    mp = _Recorder()
    rec = _cli_brake.brake(mp)
    assert mp.calls == [(sessions_mod, "Link", rec)], (
        "the brake is not put on the name the command reads: %r"
        % [(getattr(t, "__name__", t), n) for t, n, _ in mp.calls])

    seen = {}

    class _Runner:
        def invoke(self, app, argv, **kwargs):
            seen["argv"] = list(argv)
            return None

    monkey = getattr(_cli_brake, "CliRunner")
    try:
        _cli_brake.CliRunner = _Runner
        _cli_brake.run_cli("ui")
        imposed = list(seen["argv"])
        _cli_brake.run_cli("ui", "--host", "127.0.0.1")
        left_alone = list(seen["argv"])
    finally:
        _cli_brake.CliRunner = monkey

    assert imposed[:3] == ["ui", "--host", _cli_brake.UNBINDABLE_HOST], (
        "the runner let `ui` reach an address it could bind: %r" % imposed)
    assert left_alone.count("--host") == 1 and "127.0.0.1" in left_alone, (
        "a caller naming its own host had a second one imposed on it: %r"
        % left_alone)
