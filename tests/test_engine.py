"""The engine is downloaded by this process, once, and what is said meanwhile.

No network here. The fetch is a stand-in shaped like `invisible_core
.ensure_binary` - a `downloading` phase, byte progress, then the two silent
phases - held open on an Event so a test can look at the engine mid-download.
"""
from __future__ import annotations

import threading
import time

from aihawk.engine import FETCH_BY_HAND, Abandoned, Engine


class _Fetch:
    """A fetch that reports 43% and then waits to be released."""

    def __init__(self, path="C:/cache/firefox.exe", fail=None):
        self.path = path
        self.fail = fail
        self.calls = 0
        self.started = threading.Event()
        self.release = threading.Event()

    def __call__(self, progress, status):
        self.calls += 1
        status("downloading")
        progress(0, 100 << 20)
        progress(43 << 20, 100 << 20)
        self.started.set()
        self.release.wait(5)
        if self.fail is not None:
            raise self.fail
        status("verifying")
        status("extracting")
        return self.path


def _until(predicate, seconds=5.0):
    deadline = time.monotonic() + seconds
    while not predicate():
        assert time.monotonic() < deadline, "did not happen within %s s" % seconds
        time.sleep(0.01)


def test_a_download_in_flight_is_described_with_its_progress_and_runs_once():
    fetch = _Fetch()
    engine = Engine(fetch=fetch)
    assert engine.start()
    assert fetch.started.wait(5)

    assert not engine.ready()
    said = engine.describe()
    assert "43% of 100 MB" in said and "browser_open" in said, said
    assert engine.start() is False, "a second start while one is in flight"

    fetch.release.set()
    _until(engine.ready)
    assert engine.path == "C:/cache/firefox.exe"
    assert fetch.calls == 1
    assert engine.start() is False, "a start once the engine is ready"


def test_settle_answers_as_soon_as_the_download_says_what_it_is():
    """A cache hit settles in milliseconds; a download settles before its
    first byte. Neither waits for a transfer."""
    fetch = _Fetch()
    engine = Engine(fetch=fetch)
    engine.start()
    assert engine.settle(5.0), "a download that has begun did not settle"
    assert engine.state == "downloading"
    fetch.release.set()
    _until(engine.ready)

    hit = Engine(fetch=lambda progress, status: "C:/cache/firefox.exe")
    hit.start()
    assert hit.settle(5.0) and hit.ready()


def test_a_given_binary_is_ready_at_once_and_never_downloaded():
    fetched = []
    engine = Engine(binary_path="C:/engines/firefox.exe",
                    fetch=lambda **kw: fetched.append(kw))
    assert engine.ready()
    assert engine.start() is False
    assert engine.run() == "C:/engines/firefox.exe"
    assert fetched == []
    assert "C:/engines/firefox.exe" in engine.describe()


def test_a_failed_download_is_said_with_its_reason_and_can_be_retried():
    fetch = _Fetch(fail=RuntimeError("no route to github.com"))
    engine = Engine(fetch=fetch)
    engine.start()
    fetch.release.set()
    _until(lambda: engine.state == "failed")

    said = engine.describe()
    assert "no route to github.com" in said and FETCH_BY_HAND in said, said
    assert "browser_open" in said

    fetch.fail = None
    fetch.release.clear()
    assert engine.start(), "a failed download could not be started again"
    fetch.release.set()
    _until(engine.ready)
    assert fetch.calls == 2


def test_an_unknown_total_is_described_in_bytes_so_far():
    fetch = _Fetch()

    def no_length(progress, status):
        status("downloading")
        progress(5 << 20, 0)
        fetch.started.set()
        fetch.release.wait(5)
        return fetch.path

    engine = Engine(fetch=no_length)
    engine.start()
    fetch.started.wait(5)
    assert "5 MB so far" in engine.describe()
    fetch.release.set()
    _until(engine.ready)


def test_abandon_stops_a_download_whose_loop_swallows_exceptions():
    """The core's loop wraps the progress callback in `except Exception:
    pass`, so only a BaseException can stop it from inside. The known-bad is
    the class itself: as an Exception it would be swallowed, the thread would
    run on, and the temporary directory would never unwind."""
    assert issubclass(Abandoned, BaseException) and not issubclass(Abandoned, Exception)
    reached = threading.Event()

    def swallowing(progress, status):
        status("downloading")
        for done in range(10_000):
            try:
                progress(done, 10_000)
            except Exception:
                pass
            reached.set()
            time.sleep(0.005)
        return "C:/cache/firefox.exe"

    engine = Engine(fetch=swallowing)
    engine.start()
    assert reached.wait(5)
    engine.abandon(timeout=5.0)
    assert engine.state == "abandoned", engine.state
    assert not engine._thread.is_alive(), "the download thread outlived abandon()"


def test_run_in_the_calling_thread_drives_the_listener_phase_by_phase():
    seen = []

    class _Line:
        def progress(self, done, total):
            seen.append(("progress", done, total))

        def status(self, phase):
            seen.append(("status", phase))

    fetch = _Fetch()
    fetch.release.set()
    engine = Engine(fetch=fetch, listener=_Line())
    assert engine.run() == "C:/cache/firefox.exe"
    assert [s[1] for s in seen if s[0] == "status"] == ["downloading", "verifying", "extracting"]
    assert ("progress", 43 << 20, 100 << 20) in seen


def test_describe_before_anything_started_asks_to_call_again():
    engine = Engine(fetch=_Fetch())
    assert not engine.ready()
    assert "browser_open" in engine.describe()
