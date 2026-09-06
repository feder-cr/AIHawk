"""UI-level drive: a real local page, a real MCP server, a real browser.

Every test here serves its own page over http from 127.0.0.1, spawns
`invisible_playwright_mcp` exactly the way `aihawk.runner.drive` spawns it
(same `child_env`, same `StdioServerParameters`), and then checks what
happened INSIDE the page rather than what the tool said about itself. A tool
that answers "clicked #go" while nothing moved is the failure this file exists
to catch, so the tool's own success string is never the assertion.

No model is involved. The LLM half needs an OpenRouter key, there is none on
this machine, and a faked one would prove nothing about the browser. What is
exercised is the half a model never sees directly: the tools it is handed, and
what they actually do to a page.

RUN THEM WITH (they are deselected by default, see `addopts` in pyproject):

    C:/tmp/venv_aihawk/Scripts/python -m pytest -m ui -q C:/src/firefox-stealth/release/aihawk/pkg-cli/tests/test_ui_drive.py

Serially, and on a machine with no other browser bench running: they launch ONE
browser for the whole module and reuse it, which is also why each test starts
with its own navigation instead of trusting the page left behind by the last.

Set `STEALTHFOX_BINARY` to pin the engine. If that binary was built locally
after the last tag, set `INVISIBLE_SEAL_FILE` too or the session dies on
`EngineMismatch` and every test below reports a failure that has nothing to do
with the page.
"""
from __future__ import annotations

import asyncio
import functools
import http.server
import json
import os
import sys
import threading
import time
from datetime import timedelta

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from aihawk.agent import _result_text, mcp_tools_to_openai
from aihawk.runner import child_env

# Every test in this file drives a browser. The per-test decorators below say
# so one by one; this line is the safety net, so a test added later without the
# decorator still cannot be picked up by a default `pytest` run.
pytestmark = pytest.mark.ui


# --- the pages -------------------------------------------------------------
# Served from a temp directory over http. Never a data: URL: a data: URL is not
# a secure context, has no origin, and cannot host a form that navigates, so it
# would quietly change what several of these tests are measuring.

BLANK_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>blank</title></head>
<body><p>warmup</p></body></html>
"""

INPUT_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>input</title></head>
<body>
<h1>input page</h1>
<label for="name">Name</label>
<input id="name" name="name" type="text" value="">
<div id="mirror"></div>
<button id="greet" type="button">Greet</button>
<div id="out"></div>
<script>
window.greetCount = 0;
document.querySelector('#name').addEventListener('input', function (ev) {
  document.querySelector('#mirror').textContent = 'mirror:' + ev.target.value;
});
document.querySelector('#greet').addEventListener('click', function () {
  window.greetCount = window.greetCount + 1;
  document.querySelector('#out').textContent = 'clicked ' + window.greetCount;
});
</script>
</body></html>
"""

CONTROLS_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>controls</title></head>
<body>
<h1>controls page</h1>
<label for="fruit">Fruit</label>
<select id="fruit" name="fruit">
  <option value="apple" selected>Apple</option>
  <option value="pear">Pear</option>
  <option value="plum">Plum</option>
</select>
<label for="agree">Agree</label>
<input id="agree" name="agree" type="checkbox">
<div id="state">unset</div>
<script>
function render() {
  var fruit = document.querySelector('#fruit');
  var agree = document.querySelector('#agree');
  document.querySelector('#state').textContent =
    'fruit=' + fruit.value + ' agree=' + (agree.checked ? 'yes' : 'no');
}
document.querySelector('#fruit').addEventListener('change', render);
document.querySelector('#agree').addEventListener('change', render);
render();
</script>
</body></html>
"""

SUBMIT_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>submit</title></head>
<body>
<h1>submit page</h1>
<form id="f" action="done.html" method="get">
  <label for="q">Query</label>
  <input id="q" name="q" type="text">
  <button id="go" type="submit">Search</button>
</form>
</body></html>
"""

DONE_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>done</title></head>
<body><h1 id="done">arrived</h1></body></html>
"""

# The delay is long on purpose. The early read has to happen before the timer
# fires or the test proves nothing, and a 500 ms window would turn one slow
# round trip into a red that says "the tool returns a stale snapshot" when it
# says nothing of the kind.
TIMER_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>timer</title></head>
<body>
<h1>timer page</h1>
<div id="early">EARLY-CONTENT</div>
<script>
setTimeout(function () {
  var node = document.createElement('div');
  node.id = 'late';
  node.textContent = 'LATE-CONTENT-4000';
  document.body.appendChild(node);
}, 4000);
</script>
</body></html>
"""

HIDDEN_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>hidden</title></head>
<body>
<h1>hidden page</h1>
<button id="visible-btn" type="button">Visible</button>
<input id="visible-input" name="visible" type="text">
<button id="display-none" type="button" style="display:none">Display none</button>
<button id="visibility-hidden" type="button" style="visibility:hidden">Visibility hidden</button>
<button id="zero-opacity" type="button" style="opacity:0">Zero opacity</button>
<button id="off-canvas" type="button" style="position:absolute;left:-9999px;top:0;width:120px;height:30px">Off canvas</button>
<button id="disabled-btn" type="button" disabled>Disabled</button>
<a id="skip-link" href="/skip" style="position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)">Skip to content</a>
</body></html>
"""

DUP_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>duplicates</title></head>
<body>
<h1>duplicates page</h1>
<div id="log">none</div>
<button type="button" name="dup">Same one</button>
<button type="button" name="dup">Same one</button>
<button type="button" name="dup">Same one</button>
<button type="button" name="dup">Same one</button>
<button type="button" name="dup">Same one</button>
<script>
window.clicked = [];
var all = document.querySelectorAll("button[name='dup']");
for (var i = 0; i < all.length; i++) {
  (function (index) {
    all[index].addEventListener('click', function () {
      window.clicked.push(index + 1);
      document.querySelector('#log').textContent = 'clicked ' + window.clicked.join(',');
    });
  })(i);
}
</script>
</body></html>
"""

# One paragraph over the cleaner's 200-character label limit, so `form` mode
# drops it and `full` mode keeps it. That difference is what makes the three
# modes distinguishable instead of three names for one output.
_LONG_PROSE = (
    "LONGPROSE-MARKER this paragraph exists to be longer than the two hundred "
    "characters the cleaner treats as a label, so that it survives the full mode "
    "and is dropped by the form mode, which is the only observable difference "
    "between those two modes on a small page like this one."
)

NOISE_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>noise</title>
<style>.mt-4 { margin-top: 4px; } /* STYLENOISE-TOKEN */</style>
</head>
<body>
<h1>noise page</h1>
<script>
var scriptNoise = 'SCRIPTNOISE-TOKEN inline script bytes that no reader ever needs';
window.noiseData = { a: 1, b: 2 };
</script>
<img id="noise-img" alt="pixel" src="data:image/png;base64,IMGNOISETOKENAAAAAAAAAAAAAAAAAA">
<svg width="24" height="24"><a href="/svg-link"><path id="svgpath-token" d="M0 0 L10 10"></path></a></svg>
<div style="display:none">HIDDENINLINE-TOKEN</div>
<p id="prose">__LONG_PROSE__</p>
<div class="mt-4 px-2 JUNKCLASS-TOKEN wrapper"><div class="px-2"><div>
<form id="nz-form" action="done.html" method="get">
  <label for="nz-text">Your name</label>
  <input id="nz-text" name="nzname" type="text" placeholder="type here">
  <select id="nz-select" name="nzfruit">
    <option value="a">Apple</option>
    <option value="p">Pear</option>
  </select>
  <button id="nz-btn" type="submit">Submit application</button>
</form>
</div></div></div>
<a id="plain-link" href="/details-page">Details</a>
</body></html>
""".replace("__LONG_PROSE__", _LONG_PROSE)

PAGES = {
    "blank.html": BLANK_HTML,
    "input.html": INPUT_HTML,
    "controls.html": CONTROLS_HTML,
    "submit.html": SUBMIT_HTML,
    "done.html": DONE_HTML,
    "timer.html": TIMER_HTML,
    "hidden.html": HIDDEN_HTML,
    "dup.html": DUP_HTML,
    "noise.html": NOISE_HTML,
}

# The tools the server at the floor in pyproject offers, which the agent hands
# to the model. A rename upstream has to fail here rather than in a prompt.
# Eighteen since invisible-playwright-mcp 0.15.0: session_start and
# session_status arrived with 0.11.0 and browser_watch with 0.15.0, and this
# set stood at fifteen through all three because it is opt-in and nothing in
# CI runs it - measured 2026-09-06, the day the pane moved to browser_watch.
EXPECTED_TOOLS = {
    "session_start", "session_status",
    "session_new_page", "session_list_pages", "session_select_page",
    "session_close_page", "browser_navigate", "browser_read_text",
    "browser_snapshot", "browser_read_html", "browser_take_screenshot",
    "browser_watch",
    "browser_click", "browser_click_at", "browser_type", "browser_press_key",
    "browser_evaluate", "browser_select_option",
}


# --- the local site --------------------------------------------------------

class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler without the request log on stderr."""

    def log_message(self, fmt, *args):  # noqa: A003 - the base class name
        return


@pytest.fixture(scope="session")
def site(tmp_path_factory):
    """A local http server on a free port, serving the pages above.

    Port 0 rather than a fixed one: a hard-coded port turns "something else is
    listening" into a page that loads and is not ours, which reads as a
    browser failure.
    """
    root = tmp_path_factory.mktemp("aihawk_ui_pages")
    for name, html in PAGES.items():
        # write_bytes, never write_text: on Windows the text mode rewrites
        # every newline, and a page whose bytes changed under the test is not
        # the page the test describes.
        (root / name).write_bytes(html.encode("utf-8"))

    handler = functools.partial(_QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, name="aihawk-ui-http", daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d/" % server.server_address[1]
    try:
        yield base
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


# --- the MCP child ---------------------------------------------------------

class _McpDriver:
    """A synchronous handle on one stdio MCP session.

    The async half lives in ONE task on ONE loop in a worker thread, and calls
    are submitted to it. That is not decoration: `stdio_client` and
    `ClientSession` are anyio context managers, and entering them in one task
    and leaving them in another is exactly the shape anyio refuses. Holding the
    whole session inside a single coroutine removes the question, and lets
    every test below be an ordinary synchronous function.
    """

    def __init__(self, env):
        self._env = dict(env)
        self._loop = None
        self._session = None
        self._thread = None
        self._ready = threading.Event()
        self._stopped = None
        self._error = None
        self.tools = []

    # -- lifecycle
    def start(self, timeout=240.0):
        self._thread = threading.Thread(target=self._thread_main, name="aihawk-mcp", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout):
            raise RuntimeError("the MCP server was not ready after %.0fs" % timeout)
        if self._error is not None:
            raise RuntimeError("the MCP server failed to start: %r" % (self._error,))
        if self._session is None:
            raise RuntimeError("the MCP server exited before the session opened")

    def _thread_main(self):
        try:
            asyncio.run(self._serve())
        except BaseException as exc:  # noqa: BLE001 - reported to the main thread
            self._error = exc
        finally:
            self._ready.set()

    async def _serve(self):
        self._loop = asyncio.get_running_loop()
        self._stopped = asyncio.Event()
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "invisible_playwright_mcp"],
            env=self._env,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self.tools = list((await session.list_tools()).tools)
                self._session = session
                self._ready.set()
                await self._stopped.wait()

    def stop(self, timeout=120.0):
        if self._loop is not None and self._stopped is not None:
            try:
                self._loop.call_soon_threadsafe(self._stopped.set)
            except RuntimeError:
                pass
        if self._thread is not None:
            self._thread.join(timeout)

    # -- calling
    def call_result(self, name, arguments=None, timeout=90.0):
        """The raw CallToolResult, errors included. For asserting on failures."""
        if self._session is None:
            raise RuntimeError("the MCP session is not running")
        coro = self._session.call_tool(
            name, arguments or {}, read_timeout_seconds=timedelta(seconds=timeout),
        )
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout + 30.0)

    def call(self, name, _timeout=90.0, **arguments):
        """The text of a call that must succeed."""
        result = self.call_result(name, arguments, timeout=_timeout)
        text = _result_text_all(result)
        assert not result.isError, "%s(%r) failed: %s" % (name, arguments, text)
        return text

    def js(self, expression, timeout=60.0):
        """browser_evaluate, decoded. Always pass an arrow function.

        The expression reaches Playwright, which calls a function and evaluates
        anything else, so `() => { ... }` is the one form that never depends on
        that guess.
        """
        return json.loads(self.call("browser_evaluate", _timeout=timeout, expression=expression))

    def snapshot(self):
        return json.loads(self.call("browser_snapshot"))

    def goto(self, url, timeout=120.0):
        return self.call("browser_navigate", _timeout=timeout, url=url)


def _result_text_all(result):
    """Every text part of a result, not just the first.

    Deliberately NOT `aihawk.agent._result_text`: that one returns
    `content[0]` only, which is what the model sees and is a thing under test
    below, not a thing to test with.
    """
    parts = []
    for item in result.content or []:
        value = getattr(item, "text", None)
        if value is not None:
            parts.append(value)
    return "\n".join(parts)


@pytest.fixture(scope="session")
def browser():
    """One browser for the module, spawned the way the interface spawns it.

    `child_env` comes from the package rather than being rebuilt here, so a
    change to the option mapping shows up as a broken drive instead of passing
    unnoticed under a private copy of the same dictionary.
    """
    env = child_env(
        {
            "proxy": None,
            "seed": 20260902,
            "headed": False,
            "binary": os.environ.get("STEALTHFOX_BINARY"),
            "profile_dir": None,
        },
        os.environ,
    )
    # `child_env` writes STEALTHFOX_HEADLESS only to turn headless OFF, so an
    # inherited "0" survives `headed: False` and would open a window here. The
    # workbench rule is that browser tests are headless, so it is forced.
    env["STEALTHFOX_HEADLESS"] = "1"

    driver = _McpDriver(env)
    driver.start()
    try:
        # Warmup, with a long ceiling: the first navigation is the one that
        # launches Firefox, and every timing assertion below assumes that cost
        # has already been paid.
        driver.call("session_new_page", _timeout=300.0)
        driver.goto("about:blank", timeout=300.0)
        yield driver
    finally:
        driver.stop()


# --- helpers ---------------------------------------------------------------

def _wait_until(browser, expression, what, timeout=25.0):
    """Poll a truthy JavaScript expression. Errors count as not-yet.

    An evaluate issued while a navigation is in flight can fail on a destroyed
    execution context, which is a race and not an answer.
    """
    deadline = time.monotonic() + timeout
    last = "<never ran>"
    while time.monotonic() < deadline:
        result = browser.call_result("browser_evaluate", {"expression": expression})
        last = _result_text_all(result)
        if not result.isError:
            try:
                value = json.loads(last)
            except ValueError:
                value = None
            if value:
                return value
        time.sleep(0.25)
    raise AssertionError(
        "timed out after %.0fs waiting for %s; last answer was %r" % (timeout, what, last)
    )


def _ids(snapshot):
    return {e.get("id") for e in snapshot.get("interactive_elements", []) if e.get("id")}


# --- the tools the model is handed -----------------------------------------

@pytest.mark.ui
def test_the_live_server_exposes_exactly_the_documented_tools(browser):
    """The tool set the agent converts is the one the README promises.

    Known-bad: rename `browser_read_text` upstream, or add a nineteenth tool,
    and this fails. It matters because the system prompt in `agent.py` names
    tools in prose ("Inspect pages with browser_read_text / browser_snapshot"),
    and prose does not break when a name moves.
    """
    names = {t.name for t in browser.tools}
    assert names == EXPECTED_TOOLS, "tool set drifted: %r" % (names ^ EXPECTED_TOOLS,)

    defs = mcp_tools_to_openai(browser.tools)
    # Derived, not typed. The literal here said 14 while the set above said
    # what it said, so adding a tool meant editing a number in a second
    # place - and the number is the half nobody remembers.
    assert len(defs) == len(EXPECTED_TOOLS)
    for one in defs:
        assert one["type"] == "function"
        assert one["function"]["name"] in EXPECTED_TOOLS
        params = one["function"]["parameters"]
        # An OpenAI tool definition with a non-object schema is rejected by the
        # API, so this is the shape the whole loop depends on.
        assert params.get("type") == "object", one["function"]["name"]
        assert isinstance(params.get("properties"), dict), one["function"]["name"]

    by_name = {d["function"]["name"]: d["function"] for d in defs}
    navigate = by_name["browser_navigate"]
    assert "url" in navigate["parameters"]["properties"]
    assert navigate["parameters"].get("required") == ["url"]
    # Empty descriptions would leave the model choosing tools by name alone.
    assert all(d["description"].strip() for d in by_name.values())


# --- typing, clicking, reading ---------------------------------------------

@pytest.mark.ui
def test_typing_into_a_text_input_sets_the_value_and_fires_an_input_event(browser, site):
    """browser_type must reach the page, not just the DOM property.

    Two assertions, and the second is the one with teeth. `value` alone would
    still pass if the tool assigned the property directly, and half the web
    (any framework-controlled field) ignores a value that arrives without an
    `input` event. The page mirrors the event into #mirror, so a silent
    assignment shows up as an empty mirror next to a correct value.
    """
    browser.goto(site + "input.html")
    assert browser.js("() => { return document.querySelector('#name').value; }") == ""

    browser.call("browser_type", selector="#name", text="Ada Lovelace")

    assert browser.js("() => { return document.querySelector('#name').value; }") == "Ada Lovelace"
    assert browser.call("browser_read_text", selector="#mirror") == "mirror:Ada Lovelace"


@pytest.mark.ui
def test_clicking_a_button_runs_its_javascript_and_changes_the_dom(browser, site):
    """The changed node is the evidence, never the tool's "clicked #greet".

    Known-bad: a click that lands on the wrong element, or is swallowed by an
    overlay, leaves #out empty and the tool still answers successfully.
    """
    browser.goto(site + "input.html")
    assert browser.call("browser_read_text", selector="#out") == ""

    browser.call("browser_click", selector="#greet")

    assert browser.call("browser_read_text", selector="#out") == "clicked 1"
    assert browser.js("() => { return window.greetCount; }") == 1


@pytest.mark.ui
def test_read_text_says_so_when_the_selector_matches_nothing(browser, site):
    """A miss must be legible to a model, not an empty string.

    Known-bad: return "" for a missing element and the model reads an empty
    page instead of a wrong selector, then keeps going.
    """
    browser.goto(site + "input.html")
    answer = browser.call("browser_read_text", selector="#does-not-exist")
    assert "no element matches" in answer
    assert "#does-not-exist" in answer


# --- select and checkbox ---------------------------------------------------

@pytest.mark.ui
def test_a_checkbox_and_a_select_reach_the_page_state(browser, site):
    """Set both, then read the state the page itself computed.

    The page recomputes #state from its own `change` handlers, so this asserts
    the page agrees, not just that two DOM properties were written. Known-bad:
    setting `select.value` without dispatching `change` leaves #state saying
    apple while the property says pear, which is the state a real site's
    validation would act on.
    """
    browser.goto(site + "controls.html")
    assert browser.call("browser_read_text", selector="#state") == "fruit=apple agree=no"

    browser.call("browser_click", selector="#agree")
    assert browser.js("() => { return document.querySelector('#agree').checked; }") is True
    assert browser.call("browser_read_text", selector="#state") == "fruit=apple agree=yes"

    # ⛔ A SELECT IS SET WITH THE SELECT TOOL, and this assertion used to say the
    # opposite. It read "There is no select_option tool, so a select is set the
    # only way the tool set allows: through browser_evaluate" - true when it was
    # written, and it meant the suite was pinning the exact behaviour that got a
    # real model into trouble. `s.value = 'pear'` reaches the page with no
    # keystroke and no trusted event, which is the one thing this stack exists to
    # avoid, and browser_evaluate refuses it now.
    #
    # The tool is asked for the option by its LABEL here, because that is what a
    # model reads off a screenshot or a snapshot. Matching by value is checked
    # elsewhere; what matters here is that the humanised path is the one taken.
    browser.call("browser_select_option", selector="#fruit", value="Pear")
    assert browser.call("browser_read_text", selector="#state") == "fruit=pear agree=yes"
    assert browser.js(
        "() => { return document.querySelector('#fruit').selectedOptions[0].textContent; }"
    ) == "Pear"

    # And the shortcut is now closed rather than merely unused: a model that
    # tries it is told so, and told what to use instead.
    with pytest.raises(Exception) as refused:
        browser.js("() => { document.querySelector('#fruit').value = 'apple'; }")
    assert "browser_select_option" in str(refused.value), refused.value
    assert browser.call("browser_read_text", selector="#state") == "fruit=pear agree=yes", (
        "the refused expression changed the page anyway")


@pytest.mark.ui
def test_browser_type_cannot_set_a_select_and_leaves_it_untouched(browser, site):
    """The gap an agent has to know about, asserted rather than assumed.

    browser_type is `page.fill`, which refuses anything that is not an input, a
    textarea or a contenteditable. The important half is the second assertion:
    the failure is CLEAN, the select keeps its old value, so a model that
    retries has not half-changed the form underneath itself.

    Known-bad, and it is the reason this is a test and not a comment: if a
    future version made fill silently no-op instead of raising, the tool would
    answer "typed into #fruit" and the page would still say apple.
    """
    browser.goto(site + "controls.html")
    result = browser.call_result("browser_type", {"selector": "#fruit", "text": "pear"})
    text = _result_text_all(result)

    assert result.isError, "browser_type on a <select> reported success: %r" % text
    assert "not an <input>" in text.lower(), text
    assert browser.js("() => { return document.querySelector('#fruit').value; }") == "apple"
    assert browser.call("browser_read_text", selector="#state") == "fruit=apple agree=no"


# --- navigation ------------------------------------------------------------

@pytest.mark.ui
def test_submitting_a_form_navigates_and_the_next_page_loads(browser, site):
    """A submit is not done when the click returns: the new page has to be there.

    Asserted in three parts because they fail differently: the url changed, it
    carries what was typed, and the new document actually rendered. Known-bad:
    a click that submits nothing leaves the url on submit.html; a navigation
    that starts and dies leaves the url right and #done unreadable.
    """
    browser.goto(site + "submit.html")
    browser.call("browser_type", selector="#q", text="hello-form")
    assert browser.js("() => { return location.pathname; }").endswith("/submit.html")

    browser.call("browser_click", selector="#go")
    _wait_until(
        browser,
        "() => { return location.pathname.indexOf('done.html') >= 0; }",
        "the submit navigation to reach done.html",
        timeout=30.0,
    )

    url = browser.js("() => { return location.href; }")
    assert "done.html" in url
    assert "q=hello-form" in url, "the typed value did not travel with the form: %r" % url
    assert browser.call("browser_read_text", selector="#done") == "arrived"


# --- live DOM vs a snapshot of load time -----------------------------------

@pytest.mark.ui
def test_a_read_sees_the_live_dom_and_not_the_page_as_it_loaded(browser, site):
    """Content added 4 s after load must be absent early and present late.

    This is the test that separates "reads the DOM now" from "returns whatever
    was captured at navigation". Known-bad: cache the document at goto time and
    the two reads become byte-identical, which is exactly what an agent
    watching a slow page would experience as a page that never updates.

    A machine too slow to take the early read inside the page's own 4 s window
    cannot prove the point, and says so rather than reporting a defect it did
    not measure.
    """
    browser.goto(site + "timer.html")
    started = time.monotonic()
    early = browser.call("browser_read_text", selector="body")
    elapsed = time.monotonic() - started

    if elapsed >= 3.5:
        pytest.skip(
            "the early read took %.1fs, too close to the page's own 4s timer to "
            "prove anything; rerun on an idle machine" % elapsed
        )
    assert "LATE-CONTENT-4000" not in early, (
        "the late node was already there after %.1fs, which the timer cannot explain" % elapsed
    )
    assert "EARLY-CONTENT" in early

    _wait_until(
        browser,
        "() => { return document.querySelector('#late') !== null; }",
        "the timer to add #late",
        timeout=30.0,
    )
    late = browser.call("browser_read_text", selector="body")
    assert "LATE-CONTENT-4000" in late
    assert late != early


# --- what a snapshot must not offer ----------------------------------------

@pytest.mark.ui
def test_the_snapshot_leaves_out_controls_that_are_present_but_invisible(browser, site):
    """A snapshot that lists an unreachable control sends an agent to click it.

    The trap is asserted, not described: the six hidden controls are confirmed
    to BE in the DOM in the same run, so a passing test cannot be explained by
    a page that failed to load. Known-bad: drop the visibility filter and all
    six appear, each with a selector the click tool will spend its full timeout
    failing to use.
    """
    browser.goto(site + "hidden.html")
    present = browser.js(
        "() => { var ids = ['display-none', 'visibility-hidden', 'zero-opacity',"
        " 'off-canvas', 'disabled-btn', 'skip-link'];"
        " return ids.filter(function (id) { return document.getElementById(id) !== null; }).length; }"
    )
    assert present == 6, "the page under test did not load as written"

    snapshot = browser.snapshot()
    ids = _ids(snapshot)
    assert "visible-btn" in ids
    assert "visible-input" in ids
    for hidden in ("display-none", "visibility-hidden", "zero-opacity",
                   "off-canvas", "disabled-btn", "skip-link"):
        assert hidden not in ids, "%s is invisible on the page and was offered anyway" % hidden

    # The snapshot reports what it could not measure. A page where every
    # element is unmeasurable returns an empty list that looks identical to a
    # page with no controls, so a clean run has to say zero.
    assert not snapshot.get("unmeasurable")


# --- the ambiguous selector ------------------------------------------------

@pytest.mark.ui
def test_an_ambiguous_selector_silently_clicks_the_first_match(browser, site):
    """Five identical buttons, one bare selector: the first one is clicked.

    Documented behaviour (Playwright is non-strict here and the README says
    so), asserted because it is silent: the tool answers "clicked
    button[name='dup']" whichever element it hit, and a model aiming at the
    third has no way to learn it hit the first.

    Known-bad in both directions: if clicking became strict this fails with an
    error instead, and if it started hitting every match the list would not be
    [1].
    """
    browser.goto(site + "dup.html")
    answer = browser.call("browser_click", selector="button[name='dup']")

    assert browser.js("() => { return window.clicked; }") == [1]
    assert browser.call("browser_read_text", selector="#log") == "clicked 1"
    # The tool's own answer names the selector and nothing about which of the
    # five it reached. That is the whole finding.
    assert "dup" in answer


@pytest.mark.ui
def test_the_snapshot_hands_out_a_selector_that_reaches_the_right_one(browser, site):
    """The mitigation for the test above, exercised end to end.

    The snapshot disambiguates with `:nth-match`, and the value of that is
    entirely in whether browser_click can then USE the string it was given. So
    the third button's own selector is passed back verbatim, and the third
    button is the one that must react.

    Known-bad: hand back `button[name='dup']` for all five (the obvious
    selector) and the click lands on the first, so window.clicked is [1].
    """
    browser.goto(site + "dup.html")
    snapshot = browser.snapshot()
    dups = [e for e in snapshot["interactive_elements"] if e.get("name") == "dup"]
    assert len(dups) == 5, "expected five duplicate buttons, saw %d" % len(dups)

    third = dups[2]
    assert "selector" in third, "no selector offered for an addressable button: %r" % third
    assert ":nth-match(" in third["selector"], (
        "an ambiguous button was given the unqualified selector %r" % third["selector"]
    )
    assert third["selector"].endswith(", 3)"), third["selector"]

    browser.call("browser_click", selector=third["selector"])
    assert browser.js("() => { return window.clicked; }") == [3], (
        "the selector the snapshot offered reached the wrong element"
    )
    assert browser.call("browser_read_text", selector="#log") == "clicked 3"


# --- read_html, three modes ------------------------------------------------

@pytest.mark.ui
def test_read_html_keeps_every_interactive_control_in_form_and_full_modes(browser, site):
    """The cleaner's one stated invariant: no interactive element is removed.

    Checked on a page built to be worth cleaning - inline script, stylesheet,
    a base64 image, framework class soup, svg geometry, a nested wrapper chain
    - so a mode that kept everything would fail the noise half and a mode that
    pruned too hard would fail the controls half.

    Known-bad: strip `<svg>` wholesale, or dedupe by signature, or apply a
    character cap, and one of the four handles below disappears while the
    output still looks like a reasonable page.
    """
    browser.goto(site + "noise.html")

    for mode in ("form", "full"):
        html = browser.call("browser_read_html", mode=mode)
        for handle in ("nz-text", "nzname", "nz-select", "nzfruit", "nz-btn",
                       "plain-link", "/details-page", "Submit application", "Your name"):
            assert handle in html, "%s mode dropped %r" % (mode, handle)
        for noise in ("SCRIPTNOISE-TOKEN", "STYLENOISE-TOKEN", "IMGNOISETOKEN",
                      "JUNKCLASS-TOKEN", "svgpath-token", "HIDDENINLINE-TOKEN"):
            assert noise not in html, "%s mode kept %r" % (mode, noise)

    # The one difference between the two modes on this page: form mode prunes
    # prose that explains no control, full mode keeps the structure.
    form_html = browser.call("browser_read_html", mode="form")
    full_html = browser.call("browser_read_html", mode="full")
    assert "LONGPROSE-MARKER" not in form_html
    assert "LONGPROSE-MARKER" in full_html


@pytest.mark.ui
def test_read_html_text_mode_returns_prose_without_the_markup(browser, site):
    """text mode is prose only, and that is a real boundary worth pinning.

    The captions of the controls survive because captions are text, but the
    HANDLES do not: an agent cannot click anything it learned from this mode.
    Asserted in both directions so the boundary cannot move unnoticed - if a
    later version started leaking ids into text mode, the last two assertions
    fail and someone gets to decide whether that is wanted.
    """
    browser.goto(site + "noise.html")
    text = browser.call("browser_read_html", mode="text")

    assert "Submit application" in text
    assert "Your name" in text
    assert "Details" in text
    assert "LONGPROSE-MARKER" in text
    for noise in ("SCRIPTNOISE-TOKEN", "STYLENOISE-TOKEN", "IMGNOISETOKEN",
                  "JUNKCLASS-TOKEN", "HIDDENINLINE-TOKEN"):
        assert noise not in text, "text mode kept %r" % noise

    assert "nz-text" not in text, "text mode leaked a markup handle"
    assert "<button" not in text, "text mode leaked markup"


@pytest.mark.ui
def test_read_html_refuses_an_unknown_mode(browser, site):
    """A model that invents a mode gets told, not given a silent default.

    Known-bad: fall back to "form" on an unknown mode and the model believes it
    is reading prose while reading markup.
    """
    browser.goto(site + "noise.html")
    result = browser.call_result("browser_read_html", {"mode": "prose"})
    text = _result_text_all(result)
    assert result.isError, "an unknown mode was accepted: %r" % text[:200]
    assert "mode" in text.lower()


# --- what the model actually receives --------------------------------------

@pytest.mark.ui
def test_a_click_at_coordinates_lands_but_reaches_the_model_as_no_content(browser, site):
    """Two facts in one run, because they only matter together.

    browser_click_at works: the click lands and the page reacts. What comes
    back is an Image, and `aihawk.agent._result_text` reads `content[0].text`,
    which an ImageContent does not have - so the model driving this tool is
    told "[non-text result]" and never sees the screenshot the tool exists to
    return. Same for browser_take_screenshot, which then carries nothing else.

    Known-bad: this passes today. If a later version encoded the image for the
    model, the last assertions fail and that is the point at which someone
    should notice the agent changed.
    """
    browser.goto(site + "input.html")
    snapshot = browser.snapshot()
    greet = [e for e in snapshot["interactive_elements"] if e.get("id") == "greet"]
    assert greet, "the snapshot did not offer the button to click"
    x, y = greet[0]["at"]

    result = browser.call_result("browser_click_at", {"x": x, "y": y}, timeout=60.0)
    assert not result.isError, _result_text_all(result)

    # The click really landed: the page counted it.
    assert browser.call("browser_read_text", selector="#out") == "clicked 1"

    # And what the agent would put in the model's transcript for that call.
    assert _result_text(result) == "[non-text result]"

    shot = browser.call_result("browser_take_screenshot", {}, timeout=60.0)
    assert not shot.isError, _result_text_all(shot)
    assert _result_text(shot) == "[non-text result]"


# --- what the live pane receives --------------------------------------------

@pytest.mark.ui
def test_the_window_capture_is_a_jpeg_that_the_pane_can_show(browser, site):
    """The live pane is `browser_watch` since 2026-09-06, so what the pane
    receives is checked here against a real server and a real browser, not
    against a double: one image part, JPEG by type and by its first bytes, of
    a size that is a picture and not a placeholder, and the same call answers
    twice, which is what a pane asking five times a second relies on.

    The route itself is covered in test_web_service.py with a double; this is
    the half a double cannot prove - that the server the floor names really
    answers this tool with a frame.
    """
    import base64

    browser.goto(site + "input.html")
    first = browser.call_result("browser_watch", {}, timeout=60.0)
    assert not first.isError, _result_text_all(first)
    images = [c for c in first.content if getattr(c, "data", None) is not None]
    assert len(images) == 1, "one picture, and nothing else in the result"
    assert images[0].mimeType == "image/jpeg"
    jpeg = base64.b64decode(images[0].data)
    assert jpeg[:3] == b"\xff\xd8\xff", "not a JPEG by its first bytes"
    assert len(jpeg) > 4000, "a window with a tab strip and a page is more than this"

    second = browser.call_result("browser_watch", {}, timeout=60.0)
    assert not second.isError, _result_text_all(second)
