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
        for held in ("_focus", "_loaded", "_seen_tabs", "_tabs_owed"):
            got = getattr(server, held, None)
            if got is not None:
                got.clear()
    yield
