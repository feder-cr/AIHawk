"""Closing stdin ends the server, browser included, within a bounded time.

Closing the input stream is the first step of the shutdown the MCP spec
prescribes to a stdio client (then SIGTERM, then SIGKILL). Measured on Linux
on 2026-09-06: with a page open, the server was still alive 180 seconds after
its stdin closed, and the browser with it, because the close of every browser
was left to an atexit hook that ran registry.close_all() in a NEW event loop
over Playwright objects born in the loop that had just finished; that await
never returned. With no page ever opened the process exited in 0.2 s, and on
SIGTERM it exited at once, which is why no client had noticed.

Skipped unless STEALTHFOX_BINARY points at a real patched Firefox build: the
page has to be real for the close to have anything to wait for.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

BINARY = os.environ.get("STEALTHFOX_BINARY")
pytestmark = [pytest.mark.e2e, pytest.mark.skipif(
    not BINARY, reason="set STEALTHFOX_BINARY to a real patched Firefox binary to run this")]

#: How long a client is expected to wait before escalating to a signal.
GRACE = 30


def _send(p, obj):
    p.stdin.write(json.dumps(obj) + chr(10))
    p.stdin.flush()


def _recv(p):
    line = p.stdout.readline()
    assert line, "the server closed its stdout before answering"
    return json.loads(line)


def _profiles():
    return {d.name for d in Path(tempfile.gettempdir()).glob("invisible_profile_*")}


def test_closing_stdin_with_a_page_open_ends_the_server_and_its_browser():
    env = dict(os.environ)
    env["STEALTHFOX_BINARY"] = BINARY
    before = _profiles()
    p = subprocess.Popen(
        [sys.executable, "-m", "aihawk.mcp"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, bufsize=1, env=env)
    try:
        _send(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                             "clientInfo": {"name": "shutdown-test", "version": "0"}}})
        assert "result" in _recv(p)
        _send(p, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(p, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": "session_new_page", "arguments": {}}})
        answer = _recv(p)
        assert not answer.get("result", {}).get("isError"), answer
        opened = _profiles() - before
        assert opened, "no browser profile appeared, so no browser was opened"

        p.stdin.close()
        started = time.time()
        try:
            code = p.wait(timeout=GRACE)
        except subprocess.TimeoutExpired:
            p.kill()
            pytest.fail("the server was still alive %d s after its stdin closed "
                        "with a page open" % GRACE)
        assert code == 0, "the server exited with %s after a clean stdin close" % code

        # A closed browser takes its temporary profile with it; a killed one
        # leaves it behind (7,308 of them were counted once on this machine).
        deadline = time.time() + 10
        while opened & _profiles() and time.time() < deadline:
            time.sleep(0.5)
        assert not (opened & _profiles()), (
            "the server exited in %.1f s but the browser's profile is still "
            "there: the browser was not closed, it was orphaned"
            % (time.time() - started))
    finally:
        if p.poll() is None:
            p.kill()
