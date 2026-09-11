"""Where `aihawk ui` is stopped inside a test, and the proof that it stopped.

⛔ ONE PLACE, BECAUSE TWO COST FOUR CI PUSHES AND A DAY OF RUNNER TIME.
`cli.ui` does not import `Link`. It builds a `Sessions` registry and asks it
for a conversation, and `Sessions._spawn_link` is where `Link(...)` is actually
called, bound there by `sessions.py`'s own `from .link import Link` at import
time. So the seam is `aihawk.sessions.Link` and nothing else: patching
`aihawk.link.Link` rebinds a name the command never reads.

That was worked out once and written down in `test_cli_surface.py`, and the
file next door went on patching `aihawk.link.Link` anyway - the same fact in
two places, corrected in one. Measured 2026-09-11: the brake reached nothing,
the command ran on, and uvicorn served the interface with no end inside a unit
test. Every CI matrix job hung to GitHub's six-hour ceiling on four pushes, and
not one of them went red, because a job that hangs reports `in_progress`.
Locally it was green in milliseconds, for a reason no test could state: the
developer's own interface held port 8765, so uvicorn could not bind and exited.

Three things, and each covers what the others cannot:

* the brake goes at the one seam (`brake`);
* it has to PROVE it fired (`stopped_at_link`), because a brake that no longer
  reaches the code looks exactly like one that works;
* and the command is given an address nothing can bind (`run_cli`), because an
  assertion can only speak once the command has RETURNED, so on its own it
  saves nothing from a run that never returns.
"""
from __future__ import annotations

from click.testing import CliRunner

import aihawk.cli as climod
import aihawk.sessions as sessions_mod

#: 203.0.113.0/24 is TEST-NET-3, reserved by RFC 5737 and routed nowhere, so
#: the bind fails on every platform. Nothing here is about the address: it is
#: the floor under every other guarantee in this module.
UNBINDABLE_HOST = "203.0.113.1"


class Stop(Exception):
    """Raised by the recorder so the command stops before it serves anything."""


class LinkRecorder:
    """Stands in for `Link`: records how it was constructed, then stops.

    `ui` decides which key, which model and which browser options, and then
    hands them to `Link`. Recording that hand-over is the last point where the
    decisions are visible and the first point where a real browser would be
    launched, so it is where the command is stopped.

    ⛔ `opts` CARRIES ONE MORE KEY THAN THE CLI BUILT: `Sessions._spawn_link`
    adds `session_id` before constructing `Link`, and since 2026-09-11 that is
    the only way a conversation's saved browsers are told apart at all. No
    caller reads the whole dict, so the extra key changes nothing.
    """

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, opts=None, *, key=None):
        self.calls.append({"opts": dict(opts or {}), "key": key})
        raise Stop

    @property
    def call(self) -> dict:
        assert len(self.calls) == 1, f"expected one Link, got {len(self.calls)}"
        return self.calls[0]


def brake(monkeypatch) -> LinkRecorder:
    """Install the brake at the one seam the command actually reaches."""
    rec = LinkRecorder()
    monkeypatch.setattr(sessions_mod, "Link", rec)
    return rec


def run_cli(*args, **kwargs):
    """Invoke the CLI, and never let `ui` reach an address it could bind.

    The host is added rather than demanded of every caller, so a test written
    next year gets the floor without knowing it exists. A caller that names its
    own `--host` is left alone: that one is testing the option.
    """
    argv = list(args)
    if argv[:1] == ["ui"] and "--host" not in argv:
        argv = [argv[0], "--host", UNBINDABLE_HOST] + argv[1:]
    return CliRunner().invoke(climod.main, argv, **kwargs)


def stopped_at_link(result) -> bool:
    """The command got as far as connecting, which is as far as we let it."""
    return isinstance(result.exception, Stop)
