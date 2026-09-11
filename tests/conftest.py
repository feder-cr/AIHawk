"""No test reads or writes the real machine's aihawk directory.

⛔ MEASURED, BY DOING IT. Sessions became persistent on 2026-09-08, and the
first run of the tests that exercise them wrote three real files into
`%APPDATA%\\aihawk\\sessions` on the developer's machine - and then the next
test read them back, so tests began contaminating each other through a
directory none of them had mentioned. One of them failed with six browsers it
never opened.

Redirected here rather than in each test for the reason the pollution happened
at all: the tests that touch this were written by somebody who knew about it,
and the ones written next year will not be. `AIHAWK_HOME` is the single knob
`store.home()` reads first, so pointing it at a temporary directory for every
test closes the whole class rather than the two cases somebody remembered.

⛔ AND THE FIRST VERSION OF THAT ONLY COVERED TEST BODIES, WHICH LET THE SAME
DEFECT BACK IN THROUGH THE DOOR NEXT TO IT. A fixture runs when a test runs; a
module-level line runs when the file is IMPORTED, which is before any fixture
exists. `test_asking_who_you_are.py` asks the server one question at import
time, and that question reads the saved session - so on a machine where
somebody actually uses AIHawk, collection alone loaded the real one. Measured
on this machine: two tests in `test_addressing.py` went red because the
developer's live session had its focus on a browser called `b-kw-pharmacist`,
and the server module carried that, plus eight real URLs, into every test that
followed. Green in isolation, red in the suite, and green on CI - because CI
has no saved session to read. A suite whose verdict depends on what the
developer left open is not reporting on the product.

So the home is redirected TWICE, and the two are not redundant:

* at import, below, so no line that runs during collection can reach the real
  directory. This one is a single directory for the whole run, which is enough
  because its only job is to be empty;
* per test, in the fixture, so two tests cannot reach each other's.

And the module state the server keeps ACROSS calls is emptied per test for the
same reason the environment variable is set in one place: several test files
already reset those dicts by hand, which is the duplication that lets the next
file forget. What one test leaves behind is not an input to the next one.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

#: Set at IMPORT, not in a fixture: conftest is imported before the test modules
#: are, so this is in place before any module-level line can ask the server a
#: question. `mkdtemp` and not `tmp_path`, which is a fixture and does not exist
#: yet at this point.
os.environ["AIHAWK_HOME"] = tempfile.mkdtemp(prefix="aihawk-tests-")


def _e2e_is_excluded(argv) -> bool:
    """Whether this run has the engine tests DESELECTED.

    ⛔ THIS USED TO ASK THE OTHER QUESTION - "did somebody ask for an engine" -
    and both of its answers were wrong in a way that mattered.

    `-m "not (e2e or ui)"` deselects both and it answered YES, somebody asked:
    the parentheses were stripped before the walk, so the `not` landed on `e2e`
    alone and `ui` read as a bare request. The guard was then off for a run that
    could not start a browser at all - exactly the run it exists for. And
    `-m "not ui"` SELECTS the engine tests while answering no, so the guard
    armed and they died on the one second download deadline.

    One notion fixes both, and it is the one the guard actually needs: arm when
    the engine tests are not going to run. A plain `pytest -q` gets there
    through `addopts`, which never reaches argv - hence the default.

    A token walk and not a regular expression: the gate in
    `test_the_suite_reads_no_real_session.py` holds this file to the imports a
    `pip install pytest` job has, and `re` would pass on the merits - it is
    stdlib - but the cheapest way to keep a gate strict is to never ask it for
    an exception.
    """
    expression = ""
    for i, arg in enumerate(argv):
        if arg == "-m" and i + 1 < len(argv):
            expression = argv[i + 1]
        elif arg.startswith("-m") and len(arg) > 2:
            expression = arg[2:]
    if not expression.strip():
        #: no `-m` on the command line, so `addopts` decides, and it deselects
        #: both markers. That is the ordinary run and the one to guard.
        return True

    tokens = expression.replace("(", " ( ").replace(")", " ) ").split()
    negated, skipping = False, 0
    for token in tokens:
        if skipping:
            #: inside a group the `not` already applies to: everything in here
            #: is deselected, so an `e2e` found here is an exclusion.
            if token == "(":
                skipping += 1
            elif token == ")":
                skipping -= 1
            elif token == "e2e":
                return True
            continue
        if token == "not":
            negated = True
            continue
        if token == "(":
            if negated:
                skipping = 1
                negated = False
            continue
        if token == ")":
            continue
        if token in ("and", "or"):
            negated = False
            continue
        if token == "e2e":
            #: named without a `not` in front: those tests are going to run.
            if not negated:
                return False
            return True
        negated = False
    #: `e2e` never named, so the expression selects by something else and the
    #: engine tests are still in. `-m "not ui"` is the case that taught this.
    return False
if _e2e_is_excluded(sys.argv):
    os.environ["INVISIBLE_PLAYWRIGHT_CACHE_DIR"] = _THROWAWAY = tempfile.mkdtemp(
        prefix="aihawk-no-engine-")
    os.environ["INVISIBLE_DOWNLOAD_DEADLINE"] = "1"
else:
    _THROWAWAY = None


@pytest.fixture(autouse=True)
def _aihawk_home_is_disposable(tmp_path, monkeypatch):
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path / "aihawk-home"))


@pytest.fixture(autouse=True)
def _the_server_remembers_nothing_from_the_last_test():
    """The four things the server module holds between calls.

    Emptied rather than replaced: a test that monkeypatches one of them still
    gets its own, and a test that does not gets an empty one instead of
    whatever the file before it left.

    ⛔ LOOKED UP IN `sys.modules`, NEVER IMPORTED, and the first version got
    that wrong. An autouse fixture runs for EVERY test in the repository, so
    importing the server here made every test depend on the `mcp` package - and
    two CI jobs install pytest and nothing else, because what they check is a
    version number and a set of release pages. Both went red with
    `ModuleNotFoundError: No module named 'mcp'` at fixture setup, on tests that
    have no business knowing the server exists.

    Asking `sys.modules` is also the more honest question: this state can only
    be dirty if something imported the module, so if it is not there, there is
    nothing to clear.
    """
    server = sys.modules.get("aihawk.mcp.server")
    if server is not None:
        for held in ("_seen_tabs", "_tabs_owed"):
            got = getattr(server, held, None)
            if got is not None:
                got.clear()
        # ⛔ NOT A DICT SINCE 2026-09-11. `_restored` used to be `_loaded`, a
        # set keyed by session id, because one process could hold several. It
        # is a single flag now: one process, one piece of work, restored at
        # most once.
        if hasattr(server, "_restored"):
            server._restored = False
    yield


def pytest_sessionfinish(session, exitstatus):
    """The two throwaway directories go when the run does.

    ⛔ MEASURED, AND THEY HAD NEVER GONE. `mkdtemp` twice at import and nothing
    that removes either, so every pytest process on this machine left two
    directories in the temp folder for ever: counted 2026-09-11, **805** of the
    home and **88** of the engine cache - the home one leaking since sessions
    became persistent, the other since that morning. It is the same shape this
    project has already recorded about 7,308 abandoned browser profiles: not
    the space, the entries every later run walks past.

    A pytest hook and not `atexit`, so no import has to be added to a file a
    gate deliberately holds to what a `pip install pytest` job has. `os` walks
    it: `shutil` would be one more name on that list for one call.
    """
    for path in (os.environ.get("AIHAWK_HOME"), _THROWAWAY):
        if not path or not os.path.isdir(path):
            continue
        for here, dirs, files in os.walk(path, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(here, name))
                except OSError:
                    pass
            for name in dirs:
                try:
                    os.rmdir(os.path.join(here, name))
                except OSError:
                    pass
        try:
            os.rmdir(path)
        except OSError:
            #: something is still in it, which is worth leaving rather than
            #: forcing: a directory that will not empty is a test that left a
            #: file open, and deleting under it hides that.
            pass
