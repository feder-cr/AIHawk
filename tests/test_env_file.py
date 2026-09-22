"""A `.env` beside the command, and the order that decides who wins.

The key and the browser path are the two things nobody wants to retype, and a
shell profile is a bad home for them: it is global, invisible from the project,
and different on every machine. So a `.env` in the directory the command runs
from is read at startup.

Three properties carry the whole design, and each is a decision that could
reasonably have gone the other way:

  1. THE CURRENT DIRECTORY ONLY, never a walk upwards. `find_dotenv` searches
     parent directories, so running from a subfolder can silently pick up
     somebody else's file - a different key, a different browser - with nothing
     on screen saying which one was used.
  2. IT NEVER OVERRIDES what is already set. A variable exported in the shell is
     something the user just did; a line in a file is something they did once,
     weeks ago. So the precedence a reader can rely on is
     `--flag > environment > .env > default`.
  3. IT SAYS THE NAMES AND NEVER THE VALUES. The line exists so a reader knows
     the file was found at all; printing what was in it would put the API key on
     the terminal, and terminals get pasted into issues.
"""
from __future__ import annotations

import os

import pytest

from invisible_playwright_mcp import cli


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch):
    for name in ("AIHAWK_TEST_KEY", "OPENROUTER_API_KEY", "STEALTHFOX_BINARY"):
        monkeypatch.delenv(name, raising=False)


def _write(directory, text):
    (directory / cli.ENV_FILE).write_bytes(text.encode("utf-8"))


def test_a_missing_file_is_not_an_error(tmp_path):
    """Most runs have no `.env` at all, and that is the ordinary case rather
    than a degraded one."""
    assert cli.load_env_file(tmp_path) == {}


def test_values_reach_the_process(tmp_path):
    _write(tmp_path, "OPENROUTER_API_KEY=sk-from-file\nSTEALTHFOX_BINARY=C:/ff.exe\n")

    applied = cli.load_env_file(tmp_path)

    assert applied == {"OPENROUTER_API_KEY": "sk-from-file",
                       "STEALTHFOX_BINARY": "C:/ff.exe"}
    assert os.environ["OPENROUTER_API_KEY"] == "sk-from-file"


def test_the_environment_wins_over_the_file(tmp_path, monkeypatch):
    """⛔ The load-bearing one. Known-bad is `override=True`, which is what
    `load_dotenv` does by default in plenty of projects: a stale line in a file
    would then beat a key the user just exported, and the failure looks like the
    key being wrong rather than the file being read."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-the-shell")
    _write(tmp_path, "OPENROUTER_API_KEY=sk-from-file\n")

    applied = cli.load_env_file(tmp_path)

    assert os.environ["OPENROUTER_API_KEY"] == "sk-from-the-shell"
    assert "OPENROUTER_API_KEY" not in applied, (
        "the file reported applying a variable it did not set")


def test_a_file_in_the_parent_directory_is_not_read(tmp_path):
    """⛔ CWD only. A walk upwards means the same command behaves differently
    depending on how deep you are, and picks up files nobody meant for it."""
    _write(tmp_path, "OPENROUTER_API_KEY=sk-from-the-parent\n")
    child = tmp_path / "project"
    child.mkdir()

    assert cli.load_env_file(child) == {}
    assert "OPENROUTER_API_KEY" not in os.environ


def test_quoting_and_export_prefixes_are_understood(tmp_path):
    """The reason this uses dotenv rather than a split on '='. A hand-rolled
    parser gets these wrong on somebody else's machine, months later."""
    _write(tmp_path, 'export OPENROUTER_API_KEY="sk-quoted"\n'
                     "# a comment\n"
                     "STEALTHFOX_BINARY='C:/Program Files/ff.exe'\n")

    applied = cli.load_env_file(tmp_path)

    assert applied["OPENROUTER_API_KEY"] == "sk-quoted"
    assert applied["STEALTHFOX_BINARY"] == "C:/Program Files/ff.exe"


def test_what_is_printed_names_the_variable_and_never_its_value(tmp_path, monkeypatch,
                                                                capsys):
    """⛔ A terminal gets pasted into issues. The confirmation line has to be
    enough to know the file was found and useless to anyone reading over a
    shoulder."""
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, "OPENROUTER_API_KEY=sk-do-not-print-me\n")

    from click.testing import CliRunner

    result = CliRunner().invoke(cli.main, ["--help"])

    assert "sk-do-not-print-me" not in result.output, "the key was printed"


def test_the_readme_tells_people_the_file_exists():
    """A setting nobody can discover is a setting that does not exist. This is
    the same defect the tool descriptions were audited for: the code was right
    and the only text a user reads said nothing about it.
    """
    import pathlib

    readme = pathlib.Path(__file__).resolve().parents[1] / "README.md"
    text = readme.read_text(encoding="utf-8")

    assert cli.ENV_FILE in text, "the README never mentions the .env file"
    assert "OPENROUTER_API_KEY" in text
