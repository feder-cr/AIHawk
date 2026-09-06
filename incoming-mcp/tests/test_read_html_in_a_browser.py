"""`browser_read_html`, run in a browser instead of read as a string.

⛔ WHY THIS FILE EXISTS. `read_html` is two halves: `VISIBLE_HTML_JS` decides in
the BROWSER what is painted, because computed style and layout exist only there,
and `clean_page` reduces the result in Python. The Python half has 28 tests. The
browser half had one, and it did not run it:

    js = clean.VISIBLE_HTML_JS
    assert "cloneNode(true)" in js
    for write in ("setAttribute", ...):
        assert write not in js

That is a substring scan of source text. It passes on JavaScript that does not
parse, on a clone that is built and then never used, on `cloneNode` called on the
wrong node, and on any write performed by a method absent from that list -
`el.remove()`, `replaceWith`, `textContent =`. It is the project's most repeated
defect written down in a test: checking the code's spelling rather than what it
does. Nothing here replaces it; it is a cheap structural guard and it stays.

What follows runs the real function against a real page and asks the page what
happened. The load-bearing claims, each with its own test:

  * the LIVE document is not modified - the whole reason for the clone, and the
    one failure that would create the detection surface this product exists not
    to have;
  * what the browser is not painting comes out;
  * a zero-area WRAPPER whose children are painted stays, which is an explicit
    carve-out in the code and the kind of rule a rewrite silently loses;
  * the three modes differ, in the direction their docstring claims.
"""
from __future__ import annotations

import pytest

from invisible_playwright_mcp import actions

PAGE = b"""<!doctype html>
<html><head><title>reading</title>
<style>
  .gone     { display: none }
  .invisible{ visibility: hidden }
  .ghost    { opacity: 0 }
  /* No box of its own, and a painted child inside it. */
  .wrapper  { width: 0; height: 0 }
  .wrapper > p { position: absolute; width: 200px; height: 40px }
</style>
</head><body>
  <h1>VISIBLE-HEADING</h1>
  <p id="prose">VISIBLE-PROSE that a reader would want.</p>

  <div class="gone">HIDDEN-BY-DISPLAY</div>
  <span class="invisible">HIDDEN-BY-VISIBILITY</span>
  <div class="ghost">HIDDEN-BY-OPACITY</div>

  <div class="wrapper"><p>INSIDE-A-ZERO-AREA-WRAPPER</p></div>
  <i id="empty-and-flat"></i>

  <form id="booking">
    <label for="who">Who is coming</label>
    <input id="who" name="who" type="text" value="FIELD-VALUE">
    <select id="room">
      <option value="a">Alpha room</option>
      <option value="b" selected>Beta room</option>
    </select>
    <button id="go" type="button">CONFIRM-BUTTON</button>
  </form>

  <script>window.__loaded = true;</script>
</body></html>"""


def _serve():
    import http.server
    import socket
    import threading

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)

        def log_message(self, *a):
            pass

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d/" % port


@pytest.fixture(scope="module")
def read():
    """One browser for the whole file, and every mode read from the same page.

    Reading is a pure observation, so the modes cannot interfere with each other,
    and a browser launch costs more than every assertion here put together.
    """
    import asyncio

    from invisible_playwright_mcp.plan import plan_session
    from invisible_playwright_mcp.session import StealthSession

    srv, url = _serve()

    async def run():
        # ⛔ THROUGH plan_session, NOT a bare StealthSession(). The session no
        # longer falls back to the environment - deciding is the planner's job
        # and only its job - so a bare one carries no `headless` at all and
        # launches HEADED. That passes on a desktop and dies on a runner with
        # `no DISPLAY environment variable specified`, which is how it reached
        # CI. Building the way production builds is also the honest test.
        session = StealthSession(**plan_session().kwargs)
        try:
            await session.start()
            await actions.navigate(session, url)
            before = await session.page().evaluate(
                "() => document.documentElement.outerHTML")
            out = {m: await actions.read_html(session, m)
                   for m in ("form", "text", "full")}
            after = await session.page().evaluate(
                "() => document.documentElement.outerHTML")
            return out, before, after
        finally:
            await session.close()

    try:
        yield asyncio.run(run())
    finally:
        srv.shutdown()


@pytest.mark.e2e
def test_the_live_page_is_not_touched(read):
    """The clone is the whole design, and this is the only test that can see it.

    Reading three times, in three modes, must leave the document byte-identical.
    A version that removed hidden elements from the live tree would pass every
    other test in this file and every test in test_clean.py, and would leave a
    page a detector can compare against its own copy.
    """
    _, before, after = read
    assert after == before, (
        "the document changed while it was being read; the removals are landing "
        "on the live tree instead of the clone")


@pytest.mark.e2e
def test_what_the_browser_paints_survives(read):
    """Every mode keeps the content, whatever else it drops."""
    out, _, _ = read
    for mode, html in out.items():
        for wanted in ("VISIBLE-HEADING", "VISIBLE-PROSE"):
            assert wanted in html, "%s lost %s" % (mode, wanted)


@pytest.mark.e2e
def test_what_the_browser_does_not_paint_comes_out(read):
    """The three ways a page hides something, each present on the page.

    They are separate branches in the JS - `display`, `visibility`, `opacity` -
    and a rewrite that keeps two of the three fails here and nowhere else.
    """
    out, _, _ = read
    for mode, html in out.items():
        for hidden in ("HIDDEN-BY-DISPLAY", "HIDDEN-BY-VISIBILITY",
                       "HIDDEN-BY-OPACITY"):
            assert hidden not in html, "%s kept %s" % (mode, hidden)


@pytest.mark.e2e
def test_a_zero_area_wrapper_keeps_what_is_inside_it(read):
    """An explicit carve-out in the code, and the kind a rewrite loses quietly.

    A wrapper can have no box of its own while its children are painted. Strip
    on zero area alone and the content inside vanishes - which reads exactly
    like a page that had nothing in it.
    """
    out, _, _ = read
    for mode, html in out.items():
        assert "INSIDE-A-ZERO-AREA-WRAPPER" in html, (
            "%s dropped a painted child because its wrapper had no box" % mode)


@pytest.mark.e2e
def test_an_empty_zero_area_element_does_come_out(read):
    """The other half of the same rule, so the test above cannot pass by
    disabling the zero-area branch altogether."""
    out, _, _ = read
    assert "empty-and-flat" not in out["full"], (
        "an element with no box, no children and no text was kept, so the "
        "zero-area rule is not firing at all")


@pytest.mark.e2e
def test_the_three_modes_differ_the_way_they_promise(read):
    """`form` the interactive surface, `text` the prose without markup, `full`
    the structure. Three names for one output would be three lies."""
    out, _, _ = read

    assert "<" not in out["text"], "text mode returned markup: %r" % out["text"][:120]
    assert "VISIBLE-PROSE" in out["text"]

    for mode in ("form", "full"):
        assert "who" in out[mode], "%s lost the input" % mode
        assert "room" in out[mode], "%s lost the select" % mode
        assert "CONFIRM-BUTTON" in out[mode], "%s lost the button" % mode

    assert "Who is coming" in out["form"], (
        "form mode dropped the label, which is the text that explains the field")


@pytest.mark.e2e
def test_the_script_does_not_come_back_as_content(read):
    """A page's own script is not something a reader or a model needs, and it is
    the largest thing on many real pages."""
    out, _, _ = read
    for mode, html in out.items():
        assert "__loaded" not in html, "%s returned the page's script" % mode
