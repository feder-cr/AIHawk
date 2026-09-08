"""No test writes into the real machine's aihawk directory.

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
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _aihawk_home_is_disposable(tmp_path, monkeypatch):
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path / "aihawk-home"))
