"""The commands CI runs on every push, runnable from a checkout.

⛔ A GREEN ON CI IS NOT A GREEN HERE, AND THE GAP IS WHERE THINGS ROT. This
repository runs four checks before it looks at a test: the language gate, the
lint job, the content gates and the wiki render. Three of them are a command in
a workflow file and nothing else, so a change can be pushed, sit green in a job
nobody reads, and only be discovered by whoever opens the run - which is the
shape this project has already recorded twice (a workflow that never triggered,
and a lint rule that reached CI as a NameError).

What this file does is not a second copy of those rules: it RUNS the same
commands, in the same order, from the same checkout, and reports what they said.
The rules stay in one place; only the moment they are asked moves earlier.

⛔ AND IT SKIPS RATHER THAN GUESSES WHEN A TOOL IS NOT INSTALLED. `ruff` and
`invisible-core` are what CI installs for these jobs; a developer who has run
`pip install -e ".[test]"` has the core and not ruff. Failing there would be a
red gate on a correct line, which is how a gate teaches people to work around
it, so each one is asked for by name and left alone when it is absent.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]


def _run(argv, why):
    """One CI command, run where CI runs it, with its output kept on failure."""
    done = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True,
                          encoding="utf-8", timeout=300)
    assert done.returncode == 0, (
        "%s failed here; CI runs the same command:\n%s%s"
        % (why, done.stdout, done.stderr))
    return done.stdout


def test_the_language_gate_ci_runs_passes():
    """`python -m invisible_core.english`, the `english` job."""
    if not shutil.which("invisible-core") and not _has_core():
        pytest.skip("invisible-core is not installed in this environment")
    out = _run([sys.executable, "-m", "invisible_core.english"],
               "the language gate")
    assert "english only: clean" in out, out


def test_the_lint_ci_runs_passes():
    """`ruff check src tests scripts`, the `lint` job.

    ⛔ THE RULE SET IS THE REPOSITORY'S, NOT THIS FILE'S. `select = ["F"]` lives
    in pyproject and the command carries no opinions of its own, so this cannot
    drift into a formatting argument.
    """
    if not _module("ruff"):
        pytest.skip("ruff is not installed in this environment")
    out = _run([sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"],
               "the lint gate")
    assert "All checks passed" in out or "passed" in out, out


def test_the_content_gates_ci_runs_pass():
    """`python scripts/check_content.py`, the `gate` job of content-gates.yml.

    Both halves: the selftest first, which proves the gate on known-bad input
    before it judges anything, exactly as the workflow does.
    """
    _run([sys.executable, "scripts/check_content.py", "--selftest"],
         "the content gate selftest")
    out = _run([sys.executable, "scripts/check_content.py"],
               "the content gates")
    assert "[content] clean" in out, out


def test_the_wiki_renders_end_to_end(tmp_path):
    """`python scripts/build_wiki.py docs <out>`, the last step of that job.

    It renders rather than checks, which is exactly why nothing else would
    notice it breaking: a converter that throws produces no failing test, only
    a wiki that stopped being rebuilt.
    """
    out = tmp_path / "wiki"
    _run([sys.executable, "scripts/build_wiki.py", "docs", str(out)],
         "the wiki render")
    assert (out / "_Sidebar.md").is_file(), "no sidebar was written"
    assert (out / "Home.md").is_file(), "no landing page was written"


def _has_core():
    return _module("invisible_core")


def _module(name):
    import importlib.util

    return importlib.util.find_spec(name) is not None
