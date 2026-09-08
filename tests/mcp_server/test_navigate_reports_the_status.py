"""`browser_navigate` has to say what came back, not just that it went.

The tool answered `navigated to {url}` whatever happened. A model that asked for
a page and got 404, 403 or 500 was handed the same sentence as one that got 200,
and then read the error document as if it were content - there was nothing in
the reply to read differently. This is the defect `test_describe_pages.py` states
in general: a tool's reply is the API documentation handed to a MODEL, which
cannot go and check the code when it looks wrong.

The second half is quieter. After a redirect the url in that sentence was the
one ASKED FOR, so an agent that followed a shortener, hit a login wall, or was
sent to a regional domain was told it had arrived somewhere it had not.

Both halves are read off the Response now. That value only exists from
invisible-playwright 0.13.2: before it, `page.goto()` answered None on every
navigation, which is why the dependency floor moved in the same change and why
the None branch here must NOT be reachable by an ordinary page.

Known-bad inputs, each run against this file before it was trusted:

* the old `return f"navigated to {url}"` -> the status test and the redirect
  test go red;
* reporting `url` instead of `response.url` -> the redirect test goes red;
* dropping the None branch -> the same-document test raises AttributeError
  instead of answering;
* answering the None branch for every page (what an older wheel would do) ->
  the status test goes red, which is the point of the floor.
"""
from __future__ import annotations

import pytest

from aihawk.mcp import actions

pytestmark = pytest.mark.asyncio


class _Response:
    def __init__(self, url, status):
        self.url = url
        self.status = status


class _Page:
    """A page whose goto answers the way the real one does."""

    def __init__(self, response=None, landed=None):
        self._response = response
        self.url = landed or "about:blank"
        self.goto_calls = []

    async def goto(self, url, wait_until=None, timeout=None):
        self.goto_calls.append((url, wait_until, timeout))
        if self._response is not None:
            self.url = self._response.url
        return self._response


class _Session:
    def __init__(self, page):
        self._page = page
        self.new_pages = 0

    def list_pages(self):
        return ["tab-1"]

    async def new_page(self):
        self.new_pages += 1
        return self._page

    def page(self):
        return self._page


class _EmptySession(_Session):
    def __init__(self, page):
        super().__init__(page)
        self._opened = False

    def list_pages(self):
        return ["tab-1"] if self._opened else []

    async def new_page(self):
        self._opened = True
        self.new_pages += 1
        return self._page


async def test_the_status_is_in_the_answer():
    page = _Page(_Response("https://example.com/", 200))
    reply = await actions.navigate(_Session(page), "https://example.com/")
    assert "HTTP 200" in reply, reply
    assert "https://example.com/" in reply


@pytest.mark.parametrize("status", [301, 403, 404, 500, 503])
async def test_a_failing_page_does_not_read_like_a_working_one(status):
    """The whole point: two different outcomes must not produce one sentence."""
    ok = await actions.navigate(
        _Session(_Page(_Response("https://example.com/", 200))),
        "https://example.com/")
    bad = await actions.navigate(
        _Session(_Page(_Response("https://example.com/", status))),
        "https://example.com/")
    assert ok != bad, (
        "a %d answered exactly like a 200, which is what shipped" % status)
    assert str(status) in bad, bad


async def test_a_redirect_names_where_it_LANDED_not_where_it_was_sent():
    """`response.url` is the end of the redirect chain. Reporting the requested
    url instead tells an agent it is somewhere it is not - the case that matters
    is a login wall, where the difference decides the next move."""
    page = _Page(_Response("https://example.com/login", 200))
    reply = await actions.navigate(_Session(page), "https://example.com/account")
    assert "https://example.com/login" in reply, reply
    assert "account" not in reply, (
        "it named the url it was sent to, not the one it reached: %s" % reply)


async def test_a_same_document_navigation_says_so_instead_of_breaking():
    """Playwright answers None for an anchor, and that None is correct. The
    reply has to name the reason: an agent reading a bare 'no HTTP response'
    would take it for a failure and retry something that worked."""
    page = _Page(None, landed="https://example.com/#section")
    reply = await actions.navigate(_Session(page), "https://example.com/#section")
    assert "same-document" in reply, reply
    assert "https://example.com/#section" in reply, reply


async def test_it_still_opens_a_tab_when_there_is_none():
    """The behaviour that was already there, kept: this function is also the
    only path the built-in chat uses, so losing it would strand a fresh
    session with nowhere to navigate."""
    page = _Page(_Response("https://example.com/", 200))
    session = _EmptySession(page)
    reply = await actions.navigate(session, "https://example.com/")
    assert session.new_pages == 1
    assert "HTTP 200" in reply


async def test_the_engine_floor_is_high_enough_to_answer_at_all():
    """⛔ THE DEPENDENCY IS PART OF THE BEHAVIOUR HERE, so it is asserted.

    Everything above reads what `page.goto()` returns. invisible-playwright
    answered None there on every navigation until 0.13.2, so on an older wheel
    every one of these replies would be the same-document sentence - a
    confident, wrong statement about every page on the internet. A floor that
    permits that version makes this whole file describe something the installed
    code does not do.
    """
    import re
    import pathlib
    import tomllib

    root = pathlib.Path(__file__).resolve().parents[2]
    deps = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    pins = [d for d in deps["project"]["dependencies"]
            if d.replace(" ", "").startswith("invisible-playwright")]
    assert len(pins) == 1, pins
    floor = re.search(r">=\s*(\d+)\.(\d+)\.(\d+)", pins[0])
    assert floor, pins[0]
    assert tuple(int(g) for g in floor.groups()) >= (0, 13, 2), (
        "the floor is %s: below 0.13.2 goto answers None and this tool would "
        "report 'no HTTP response' for every page" % pins[0])


# --- against a real browser, gated the way this suite gates them ------------

BINARY = __import__("os").environ.get("STEALTHFOX_BINARY")


@pytest.mark.e2e
@pytest.mark.skipif(not BINARY,
                    reason="set STEALTHFOX_BINARY to a real patched Firefox binary")
async def test_the_status_is_real_and_not_just_a_fake_objects_attribute():
    """The fakes above prove the branching. They cannot prove that the object a
    real navigation hands back carries `status` and `url` at all, and that is
    the half the dependency floor is about."""
    import http.server
    import socket
    import threading

    from aihawk.mcp.session import StealthSession

    PAGE = b"<!doctype html><html><head><title>local</title></head><body>hi</body></html>"

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/redirect"):
                self.send_response(302)
                self.send_header("Location", "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            body, code = (b"gone", 404) if self.path.startswith("/missing") else (PAGE, 200)
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d/" % port

    session = StealthSession(binary_path=BINARY, headless=True)
    await session.start()
    try:
        ok = await actions.navigate(session, base)
        assert "HTTP 200" in ok, ok

        missing = await actions.navigate(session, base + "missing")
        assert "HTTP 404" in missing, missing
        assert missing != ok, "a 404 read exactly like a 200"

        redirected = await actions.navigate(session, base + "redirect")
        assert "HTTP 200" in redirected, redirected
        assert "redirect" not in redirected, (
            "it named the url it was sent to, not the one it reached: %s" % redirected)
    finally:
        await session.close()
        srv.shutdown()
