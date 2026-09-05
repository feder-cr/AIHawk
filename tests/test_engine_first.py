"""The interface puts the browser on disk before it serves anything, and says
what it is doing while it does.

Until 0.7.0 `aihawk ui` printed "browser ready" with nothing downloaded: the
engine arrived inside the first message, invisibly, a minute of nothing moving.
These tests drive `engine_on_disk` with a fake fetch that behaves like
`invisible_core.ensure_binary` (byte progress, then the two silent phases) and
read what reached the terminal.
"""
from __future__ import annotations

import aihawk.cli as climod


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

    climod.engine_on_disk(None, echo=_echo_into(lines), fetch=fetch, tty=False)

    drawn = [line for line in lines if "downloading" in line]
    assert len(drawn) == 11, "%d redraws off a terminal" % len(drawn)


def test_on_a_terminal_every_percent_is_drawn():
    lines = []

    def fetch(progress, status):
        for done in range(101):
            progress(done, 100)

    climod.engine_on_disk(None, echo=_echo_into(lines), fetch=fetch, tty=True)

    assert sum("downloading" in line for line in lines) == 101


def test_an_unknown_total_does_not_divide_by_zero():
    lines = []

    def fetch(progress, status):
        progress(1 << 20, 0)

    climod.engine_on_disk(None, echo=_echo_into(lines), fetch=fetch, tty=False)

    assert any("downloading" in line for line in lines)
