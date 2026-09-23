"""No test reads or writes the real machine's invisible_playwright_mcp directory.

⛔ MEASURED, BY DOING IT. Sessions became persistent on 2026-09-08, and the
first run of the tests that exercise them wrote three real files into
`%APPDATA%\\invisible_playwright_mcp\\sessions` on the developer's machine - and then the next
test read them back, so tests began contaminating each other through a
directory none of them had mentioned. One of them failed with six browsers it
never opened.

Redirected here rather than in each test for the reason the pollution happened
at all: the tests that touch this were written by somebody who knew about it,
and the ones written next year will not be. `INVISIBLE_MCP_HOME` is the single knob
`store.home()` reads first, so pointing it at a temporary directory for every
test closes the whole class rather than the two cases somebody remembered.

⛔ AND THE FIRST VERSION OF THAT ONLY COVERED TEST BODIES, WHICH LET THE SAME
DEFECT BACK IN THROUGH THE DOOR NEXT TO IT. A fixture runs when a test runs; a
module-level line runs when the file is IMPORTED, which is before any fixture
exists. `test_asking_who_you_are.py` asks the server one question at import
time, and that question reads the saved session - so on a machine where
somebody actually uses invisible_playwright_mcp, collection alone loaded the real one. Measured
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

import atexit
import importlib.util
import json
import os
import pathlib
import platform
import shutil
import sys
import tempfile

import pytest

#: Set at IMPORT, not in a fixture: conftest is imported before the test modules
#: are, so this is in place before any module-level line can ask the server a
#: question. `mkdtemp` and not `tmp_path`, which is a fixture and does not exist
#: yet at this point - and removed at exit for the same reason it is made here:
#: no fixture teardown covers a directory made at import, and by 2026-09-22
#: this machine held dozens of empty `invisible_playwright_mcp-tests-*` and `invisible_playwright_mcp-no-engine-*`
#: directories, one pair per run.
os.environ["INVISIBLE_MCP_HOME"] = tempfile.mkdtemp(prefix="invisible_playwright_mcp-tests-")
atexit.register(shutil.rmtree, os.environ["INVISIBLE_MCP_HOME"], True)


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


def _local_seal_beside(cache_dir: str):
    """A seal with no published assets, derived from the packaged one, written
    beside the throwaway cache. Returns its path, or None when there is no
    core to derive it from (the light jobs) or no leg for this host.

    ⛔ THE DEADLINE IS A CAP, NOT A PROHIBITION, AND ON 2026-09-21 IT LET A
    WHOLE ENGINE THROUGH. Since 0.69.0 every server this suite spawns starts
    its engine download the moment it starts, from `main()`; the one-second
    deadline below was meant to make that fail, and on the ubuntu runner a
    complete `firefox-34_...` tree appeared in the throwaway cache anyway -
    the archive arrived inside the second. A guard that depends on the
    network being slow is off on a fast one.

    The core has a word for "there is nothing to download": a LOCAL seal,
    one with no assets, on which `ensure_binary` refuses before it touches
    the network or the cache ("a LOCAL seal with no published assets, so
    there is nothing to download. Pass binary_path=..."). That is the
    declaration this run needs, in the product's own vocabulary, inherited
    by every child process through `INVISIBLE_SEAL_FILE`. Tag, version and
    the Playwright range stay those of the packaged seal, and the top-level
    build id is the host leg's, so a real binary named by `STEALTHFOX_BINARY`
    still verifies: the opt-in real-engine tests are gated on that variable
    and keep working under this seal.

    Derived without importing the core, because the light jobs install
    pytest and nothing else and this file is imported by every run.
    """
    spec = importlib.util.find_spec("invisible_core")
    if spec is None or not spec.origin:
        return None
    packaged = pathlib.Path(spec.origin).with_name("seal.json")
    if not packaged.is_file():
        return None
    data = json.loads(packaged.read_bytes())
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "x64": "x86_64", "aarch64": "arm64"}.get(machine, machine)
    build_id = ""
    for asset in (data.get("assets") or {}).values():
        if asset.get("platform") == sys.platform and asset.get("arch") == arch:
            build_id = asset.get("build_id") or ""
    if not build_id:
        return None
    local = {k: v for k, v in data.items() if k != "assets"}
    local["build_id"] = build_id
    local["comment"] = ("the packaged seal with its assets removed, written by "
                        "tests/conftest.py so that no process in this test run can "
                        "download an engine; a real binary still verifies against it")
    path = cache_dir + ".seal.json"
    pathlib.Path(path).write_bytes(json.dumps(local, indent=1).encode("utf-8"))
    return path


if _e2e_is_excluded(sys.argv):
    os.environ["INVISIBLE_PLAYWRIGHT_CACHE_DIR"] = _THROWAWAY = tempfile.mkdtemp(
        prefix="invisible_playwright_mcp-no-engine-")
    os.environ["INVISIBLE_DOWNLOAD_DEADLINE"] = "1"
    _NO_ENGINE_SEAL = _local_seal_beside(_THROWAWAY)
    if _NO_ENGINE_SEAL:
        os.environ["INVISIBLE_SEAL_FILE"] = _NO_ENGINE_SEAL
        atexit.register(os.remove, _NO_ENGINE_SEAL)
    # The throwaway cache is removed LAST (atexit runs last-registered first),
    # after the guard has read it; a run that fetched an engine into it is a
    # red test before it is a deleted directory.
    atexit.register(shutil.rmtree, _THROWAWAY, True)
else:
    _THROWAWAY = _NO_ENGINE_SEAL = None


@pytest.fixture(autouse=True)
def _the_home_is_disposable(tmp_path, monkeypatch):
    monkeypatch.setenv("INVISIBLE_MCP_HOME", str(tmp_path / "invisible_playwright_mcp-home"))


@pytest.fixture(autouse=True)
def _the_server_remembers_nothing_from_the_last_test():
    """The one thing the server module holds between calls, made new.

    Replaced, so a test that does not install its own `Work` gets an empty
    one instead of whatever the file before it left.

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
    server = sys.modules.get("invisible_playwright_mcp.mcp.server")
    if server is not None and hasattr(server, "Work"):
        # ⛔ ONE OBJECT, WHERE THIS CLEARED FOUR GLOBALS BY NAME. The server
        # holds its whole piece of work - registry, restored flag, pages seen
        # and pages owed - in one `Work`, so a clean server is a new one; a
        # test that installs its own through monkeypatch still gets its own.
        server.work = server.Work(server._SESSION_ID)
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
    for path in (os.environ.get("INVISIBLE_MCP_HOME"), _THROWAWAY):
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
