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


def test_only_a_real_request_for_those_markers_lifts_the_guard():
    """The guard has to read `-m` the way pytest does, or it is wrong twice.

    Known-bad, and the obvious first version: `"e2e" in expression`. The
    default selection IS `not ui and not e2e`, so that reading treats every
    plain run as a request for an engine and the guard is never in force. The
    other direction matters too: a path that happens to contain `e2e` -
    `tests/mcp_server/test_stdio_e2e.py` is one - is not a marker at all.
    """
    import conftest

    asks = conftest._asks_for_an_engine
    assert asks(["pytest", "-q"]) is False
    assert asks(["pytest", "-m", "not ui and not e2e"]) is False
    assert asks(["pytest", "-m", "not e2e"]) is False
    assert asks(["pytest", "tests/mcp_server/test_stdio_e2e.py"]) is False
    assert asks(["pytest", "-m", "e2e", "tests/mcp_server"]) is True
    assert asks(["pytest", "-m", "ui"]) is True
    assert asks(["pytest", "-me2e"]) is True
    assert asks(["pytest", "-m", "e2e and not ui"]) is True
