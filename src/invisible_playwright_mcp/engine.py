"""The engine on disk, once per process, and what to say while it is not.

The browser is a patched Firefox of roughly a quarter of a gigabyte that the
core downloads from a GitHub release (`invisible_core.ensure_binary`) and
caches on this machine. Until 0.69.0 that download happened in one of two
places: inside `uvx invisible-playwright fetch`, run by a person who had read
the README, or inside the first browser launch, which from an MCP client
looked like a tool call sitting there for minutes and, on a client with a
short tool timeout, died with an error that named the timeout and never the
download. The README's fetch line existed for that reason alone.

So the download is now a thing THIS PROCESS does, once, from the moment it
starts, and the two ways in use one object for it:

* `invisible-playwright-mcp ui` runs it in the foreground, before the port opens, with a
  terminal line that follows it: the person launches the download and
  watches it, which is the way the owner asked for it to be on 2026-09-06
  when the first version of this (0.7.0 / server 0.13.0) was withdrawn.
* the MCP server runs it in a daemon thread from `main()`, because a client
  starts its servers at session start and the minutes before the first page
  are download time for free. `browser_open` does not launch a browser while
  the engine is not there: it answers with how far the download is and asks
  to be called again, so no tool call ever blocks on it and no client
  timeout is ever reached. Every other tool already answers "not open".

⛔ A CALLER THAT BRINGS ITS OWN BINARY GETS NO DOWNLOAD. `--binary` on the
interface and `STEALTHFOX_BINARY` for the server (read by `plan.engine_here`,
the one reader of that variable) name an engine the person already has; the
launch still verifies it against the seal, as it always did.

⛔ TWO DOWNLOADS IN ONE PROCESS RACE ON THE SAME TEMPORARY TREE: the core's
`ensure_binary` names it `.tmp-<tag>-<pid>` and removes it at the start of
every download, so a second caller deletes the first one's extraction. The
server never launches while this is in flight, and the interface runs it to
completion before spawning anything, so there is exactly one caller per
process and the race cannot start. Measured on the first version, 2026-09-05.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

#: The command a person can run to do the download by hand, where they can
#: watch it. Named in one place so the answer below and the setup skill say
#: the same thing.
FETCH_BY_HAND = "uvx invisible-playwright fetch"


class Abandoned(BaseException):
    """Raised inside the download's progress callback when the process is
    leaving. A BaseException on purpose: the core's download loop wraps the
    callback in `except Exception: pass`, so an ordinary exception would be
    swallowed and the thread would go on downloading into a temporary
    directory nobody will ever clean. This one climbs out, the core's
    `TemporaryDirectory` unwinds, and nothing is left behind."""


class Engine:
    """Where the engine is, for this process: not yet, coming, here, or given.

    `state` is one of `pending` (nothing started), `downloading`, `verifying`,
    `extracting` (the core's three phases), `ready` (on disk, verified),
    `failed` (with `error`), `abandoned` (the process left mid-download) and
    `given` (a binary was named, nothing to download). `run()` does the work
    in the calling thread; `start()` does it in a daemon thread and is a no-op
    while one is in flight or once the engine is ready, so calling it from
    every `browser_open` costs nothing and is what retries a failed download.
    """

    def __init__(self, *, binary_path: Optional[str] = None,
                 fetch: Optional[Callable] = None, listener=None) -> None:
        self._fetch = fetch
        self._listener = listener
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._abandoned = False
        #: Set once a download has said what it is: a cache hit (`ready`), a
        #: transfer that has begun (`downloading`), or a failure. Cleared by
        #: `start`. `settle` waits on it, so a caller can tell "the engine is
        #: being looked for" from "the engine is being downloaded" without
        #: guessing, and a warm cache never reads as a download.
        self._settled = threading.Event()
        self._settled.set()
        self.state = "given" if binary_path else "pending"
        self.path: Optional[str] = binary_path
        self.error: Optional[str] = None
        self.done = 0
        self.total = 0

    # --- the answer --------------------------------------------------------------

    def ready(self) -> bool:
        return self.state in ("ready", "given")

    def settle(self, timeout: float) -> bool:
        """Wait until the download has said what it is, at most `timeout`
        seconds: the cache check and the release lookup before the first byte
        take a network round trip, not a transfer. True when it has."""
        return self._settled.wait(timeout)

    def describe(self) -> str:
        """One sentence for a tool answer: where the engine is and what to do,
        which is always "call browser_open again" and never a command."""
        if self.state == "given":
            return "the engine is %s." % self.path
        if self.state == "ready":
            return "the engine is on this machine."
        if self.state == "failed":
            return ("the engine download failed: %s. Call browser_open again to "
                    "retry, or run the download by hand where you can watch it, "
                    "in a terminal: %s" % (self.error, FETCH_BY_HAND))
        if self.state in ("verifying", "extracting"):
            return ("the engine has downloaded and is being %s, which takes a "
                    "moment. Call browser_open again shortly; nothing else needs "
                    "doing." % ("verified" if self.state == "verifying" else "extracted"))
        if self.state == "downloading" and (self.done or self.total):
            # Before the first byte the core has said "downloading" and no
            # size yet: that instant reads as "starting" below, not as
            # "0 MB so far", which was the first answer a person got.
            if self.total:
                far = "%d%% of %d MB" % (self.done * 100 // self.total, self.total >> 20)
            else:
                far = "%d MB so far" % (self.done >> 20)
            return ("the engine is not on this machine yet and is downloading now: "
                    "%s. Call browser_open again in a minute; nothing else needs "
                    "doing." % far)
        return ("the engine is not on this machine yet; its download is starting. "
                "Call browser_open again in a minute; nothing else needs doing.")

    # --- the work ------------------------------------------------------------------

    def _fetcher(self) -> Callable:
        if self._fetch is None:
            # The engine package re-exports the core's fetcher; the core is
            # not a dependency this package declares, and an import of it
            # would be the undeclared kind the import gate refuses.
            from invisible_playwright import ensure_binary
            self._fetch = ensure_binary
        return self._fetch

    def _progress(self, done: int, total: int) -> None:
        if self._abandoned:
            raise Abandoned()
        self.done, self.total = done, total
        self.state = "downloading"
        self._settled.set()
        if self._listener is not None:
            self._listener.progress(done, total)

    def _status(self, phase: str) -> None:
        self.state = phase
        self._settled.set()
        if self._listener is not None:
            self._listener.status(phase)

    def run(self) -> Optional[str]:
        """Download in the calling thread. Returns the path, or None with
        `state` and `error` saying why."""
        if self.state == "given":
            return self.path
        self.state = "starting"
        self.error = None
        self._settled.clear()
        try:
            try:
                path = self._fetcher()(progress=self._progress, status=self._status)
            except Abandoned:
                self.state = "abandoned"
                return None
            except Exception as exc:
                self.state = "failed"
                self.error = str(exc)
                return None
            self.path = str(path)
            self.state = "ready"
            return self.path
        finally:
            self._settled.set()

    def start(self) -> bool:
        """Download in a daemon thread. True when a download was started now;
        False when one is in flight, or there is nothing to download."""
        with self._lock:
            if self.state not in ("pending", "failed"):
                return False
            self.state = "starting"
            self._settled.clear()
            self._thread = threading.Thread(target=self.run, name="invisible_playwright_mcp-engine",
                                            daemon=True)
            self._thread.start()
            return True

    def abandon(self, timeout: float = 2.0) -> None:
        """Stop a download in flight because the process is leaving. The
        `verifying` and `extracting` phases report no progress and are not
        interrupted; a process killed there leaves its `.tmp-<tag>-<pid>`
        tree, which the core's next `ensure_binary` sweeps because the pid is
        dead."""
        self._abandoned = True
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout)
