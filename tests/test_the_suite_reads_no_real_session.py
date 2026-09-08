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
    when a test begins, and any test may rely on that.
    """
    from aihawk.mcp import server

    for held in ("_focus", "_loaded", "_seen_tabs", "_tabs_owed"):
        assert not getattr(server, held), (
            "server.%s arrived at this test with %r in it" % (held, getattr(server, held)))


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
