"""The interface puts the browser on disk before it serves anything, and says
what it is doing while it does.

`invisible-playwright-mcp ui` used to print "server connected" with nothing downloaded: the
engine arrived inside the first message, invisibly, a minute of nothing
moving (0.7.0 had this, 0.8.0 withdrew it in favour of a fetch by hand, 0.69.0
brings it back with the server downloading on its own as well). These tests
drive `engine_on_disk` with a fake fetch that behaves like
`invisible_core.ensure_binary` (byte progress, then the two silent phases) and
read what reached the terminal; the last three drive the command itself,
braked, and read the ORDER: after the key is refused, before the link.
"""
from __future__ import annotations

import click
import pytest

import invisible_playwright_mcp.cli as climod
from _cli_brake import brake, run_cli, stopped_at_link

FAKE_KEY = "sk-or-v1-CANARY-engine-first"


def _echo_into(lines):
    def echo(text, nl=True):
        lines.append(text)
    return echo


def test_the_download_is_shown_phase_by_phase_and_ends_in_ready():
    lines = []

    def fetch(progress, status):
        status("downloading")
        progress(0, 100 << 20)
        progress(50 << 20, 100 << 20)
        status("verifying")
        status("extracting")
        return "C:/cache/firefox.exe"

    climod.engine_on_disk(None, echo=_echo_into(lines), fetch=fetch, tty=False)

    joined = "".join(lines)
    for word in ("downloading", "50%", "50 MB", "verifying", "extracting", "ready"):
        assert word in joined, "%r never reached the terminal: %r" % (word, lines)
    assert lines[-1] == "", "the line was left without a newline after ready"


def test_a_given_binary_is_named_and_not_downloaded():
    lines, fetched = [], []

    climod.engine_on_disk("C:/engines/firefox.exe", echo=_echo_into(lines),
                          fetch=lambda **kw: fetched.append(kw), tty=False)

    assert fetched == [], "a given binary was downloaded over"
    assert "C:/engines/firefox.exe" in "".join(lines)


def test_off_a_terminal_only_every_tenth_percent_is_drawn():
    """A pipe or a CI log gets eleven lines, not a hundred and one."""
    lines = []

    def fetch(progress, status):
        for done in range(101):
            progress(done, 100)
        return "x"

    climod.engine_on_disk(None, echo=_echo_into(lines), fetch=fetch, tty=False)

    drawn = [line for line in lines if "downloading" in line]
    assert len(drawn) == 11, "%d redraws off a terminal" % len(drawn)


def test_on_a_terminal_every_percent_is_drawn():
    lines = []

    def fetch(progress, status):
        for done in range(101):
            progress(done, 100)
        return "x"

    climod.engine_on_disk(None, echo=_echo_into(lines), fetch=fetch, tty=True)

    assert sum("downloading" in line for line in lines) == 101


def test_an_unknown_total_does_not_divide_by_zero():
    lines = []

    def fetch(progress, status):
        progress(1 << 20, 0)
        return "x"

    climod.engine_on_disk(None, echo=_echo_into(lines), fetch=fetch, tty=False)

    assert any("downloading" in line for line in lines)


def test_a_failed_download_is_one_line_and_an_exit_and_names_the_fetch_by_hand():
    lines = []

    def fetch(progress, status):
        raise RuntimeError("no route to github.com")

    with pytest.raises(click.ClickException) as refused:
        climod.engine_on_disk(None, echo=_echo_into(lines), fetch=fetch, tty=False)
    assert "no route to github.com" in str(refused.value)
    assert "uvx invisible-playwright fetch" in str(refused.value)


@pytest.fixture(autouse=True)
def _no_key_from_the_machine(monkeypatch, tmp_path):
    for name in ("OPENROUTER_API_KEY", "AIHAWK_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)


def test_the_engine_step_comes_after_the_key_and_before_the_link(monkeypatch):
    rec = brake(monkeypatch)
    result = run_cli("ui", "--openrouter-key", FAKE_KEY)
    assert stopped_at_link(result), result.output
    assert rec.engine_calls == [None], "the engine step did not run once, with no binary"
    assert rec.calls, "the link was never reached after the engine step"


def test_no_key_means_no_download(monkeypatch):
    """A refusal must not cost anybody a quarter of a gigabyte."""
    rec = brake(monkeypatch)
    result = run_cli("ui")
    assert result.exit_code != 0
    assert rec.engine_calls == [], "the engine step ran before the key was refused"


def test_a_given_binary_reaches_the_engine_step(monkeypatch):
    rec = brake(monkeypatch)
    result = run_cli("ui", "--openrouter-key", FAKE_KEY, "--binary", "C:/engines/firefox.exe")
    assert stopped_at_link(result), result.output
    assert rec.engine_calls == ["C:/engines/firefox.exe"]
