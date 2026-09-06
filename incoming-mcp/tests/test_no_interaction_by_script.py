"""The page is acted on through the pointer and the keyboard, never from script.

⛔ WHY THIS FILE EXISTS, with the run that caused it. 2026-09-02, the first time
a real model drove this server: asked to pick an option from a dropdown, it
clicked the select, pressed ArrowDown twice, and then gave up and ran
`s.value='beta'` through `browser_evaluate`. It also read the form back the same
way, because nothing it could see reported what the controls were set to.

Neither was carelessness. Both were a capable model routing around a gap, and
routing around it landed on the one path this package exists to avoid: a value
set from script arrives with no keystroke, no focus and no trusted event, and
`isTrusted` is one property read away for any page that cares.

So the defect had two halves and the tests below cover both, because fixing
either alone leaves the behaviour reachable:

  * the model could not SEE the state (a `<select>`'s text is every option
    concatenated, a checkbox has no text at all), so it read it with script;
  * the model could not SET it (there was no select tool), so it wrote it with
    script.

The second half is a refusal, and a refusal has two failure modes, not one. It
can fail to refuse, and it can refuse a read - which would push a model straight
back to the workaround it is meant to prevent. Both are tested, and the
known-good half is the larger of the two on purpose.
"""
from __future__ import annotations

import http.server
import json
import socket
import threading

import pytest

from invisible_playwright_mcp import actions
from invisible_playwright_mcp.actions import _refuse_script_interaction as refuse

# The shapes a model actually writes. Every one of these was either observed in
# the run above or is the obvious next thing to try after the observed one is
# refused - `el['value']=` is what a model reaches for once `el.value=` fails,
# so a guard that misses it buys one turn and nothing more.
ACTING = [
    "() => { document.querySelector('#sala').value = 'beta' }",
    "() => { s.value='beta' }",
    "() => document.getElementById('proiettore').checked = true",
    "() => { el['value'] = 'x' }",
    '() => { el["checked"]=true }',
    "() => document.querySelector('#invia').click()",
    "() => el.dispatchEvent(new MouseEvent('click', {bubbles:true}))",
    "() => document.forms[0].submit()",
    "() => { i.value += 'coda' }",
    "() => { o.selected = true }",
    # ⛔ Measured 2026-09-04: thirteen of fifteen ordinary acting expressions
    # walked straight past this guard while the model was being told, in the
    # instructions block and in the tool's own docstring, that evaluate "will
    # not act on the page". These are the ordinary modern spellings of the same
    # acts - `requestSubmit` is simply what `submit()` became, and only the old
    # name was refused.
    "() => document.forms[0].requestSubmit()",
    "() => el.setAttribute('value', 'beta')",
    "() => el.setAttribute('checked', '')",
    "() => Object.assign(el, {value: 'beta'})",
    "() => Reflect.set(el, 'checked', true)",
    "() => document.execCommand('insertText', false, 'beta')",
]

# ⛔ KNOWN TO PASS, AND THE POINT IS THAT NOBODY CLAIMS OTHERWISE. This is a
# pattern check on the obvious road, not a sandbox: JavaScript has unlimited
# ways to say the same thing, and chasing them one at a time is how a guard
# grows until it starts refusing reads instead. What makes that acceptable is
# that the model-facing text now says so and asks for a report rather than
# implying the door is locked - so this list is the honest edge of the guard,
# not a backlog.
KNOWN_TO_PASS = [
    "() => HTMLElement.prototype.click.call(el)",
    "() => el.removeAttribute('disabled')",
]

# Reading is the whole point of the tool and must keep working. A guard that
# eats these is worse than no guard: the model loses the ability to check its
# own work, and the next thing it tries is the workaround again.
READING = [
    "() => ({nome: document.querySelector('#nome').value})",
    "() => document.querySelector('#sala').value",
    "() => document.querySelector('#x').value === 'beta'",
    "() => el.value !== '' && el.value >= 3",
    "() => [...document.querySelectorAll('option')].map(o => o.value)",
    "() => document.getElementById('esito').textContent",
    "() => Object.values(window.stato).length",
    "() => getComputedStyle(el).display",
    "() => el.checked",
    "() => typeof el.click",
]


@pytest.mark.parametrize("expression", ACTING)
def test_acting_on_the_page_from_script_is_refused(expression):
    with pytest.raises(ValueError) as caught:
        refuse(expression)
    # The refusal has to name the way forward. A model told only "no" retries;
    # a model told which tool to use switches, which is the entire objective.
    assert "browser_" in str(caught.value), (
        "the refusal does not name a tool to use instead: %s" % caught.value)


@pytest.mark.parametrize("expression", READING)
def test_reading_the_page_is_not_refused(expression):
    refuse(expression)


@pytest.mark.parametrize("expression", KNOWN_TO_PASS)
def test_what_the_guard_does_not_catch_is_recorded_rather_than_denied(expression):
    """A gap that is written down is a gap somebody can close. One that is
    denied in the model-facing text is a gap that gets used.

    If a change makes one of these refuse, delete it from KNOWN_TO_PASS and put
    it in ACTING. This failing is good news.
    """
    refuse(expression)  # does not raise today, and nothing pretends it does


def test_the_model_is_not_told_the_guard_is_complete():
    """⛔ The honesty half, and it is the half that makes the guard work.

    The instructions block said `browser_evaluate will not act on the page` and
    the docstring said `It will not act`, while the code's own comment said in
    capitals that it is a pattern check and "must not be described as" a
    sandbox. Measured 2026-09-04: thirteen of fifteen acting expressions passed.
    A model that believes the door is locked has no reason to avoid the handle.
    """
    import asyncio

    from invisible_playwright_mcp import server

    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    surfaces = [server.INSTRUCTIONS, tools["browser_evaluate"].description or ""]

    for text in surfaces:
        assert "will not act" not in text, (
            "the model is told the guard is a wall: %r" % text[:200])

    joined = " ".join(surfaces).lower()
    assert "not a wall" in joined or "not every possible" in joined, (
        "nothing tells the model the guard is partial")
    assert "report" in joined or "say so" in joined, (
        "the model is not asked to report a way around it")


def test_the_guard_is_on_the_action_not_on_the_tool():
    """The check lives in `actions.evaluate`, so it holds for every caller.

    Putting it in the tool function would leave it out of any other path into
    the same action, and the guard would be one refactor away from being a
    comment.
    """
    import inspect

    src = inspect.getsource(actions.evaluate)
    assert "_refuse_script_interaction" in src, (
        "actions.evaluate no longer consults the guard")


def test_the_description_does_not_invite_what_the_code_refuses():
    """It used to read "Prefer a named tool when one fits, because this one can
    change the page" - accurate then, an invitation, and ignored.

    A description that offers what the code refuses costs a turn every time and
    teaches nothing, so it is checked rather than remembered.
    """
    import asyncio

    from invisible_playwright_mcp import server

    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    text = (tools["browser_evaluate"].description or "")
    assert "can change the page" not in text
    assert "refused" in text.lower(), (
        "the description does not tell the model that acting is refused, so it "
        "will find out by being refused: %r" % text)


def test_every_tool_a_refusal_names_actually_exists():
    """A refusal that points at a tool which is not there is a dead end.

    Found by mutation: the test above only asks that the message contain
    "browser_", which a message naming `browser_pippo` satisfies just as well.
    The model would then call something that does not exist, get a second error
    unrelated to the first, and have every reason to go back to the workaround.
    """
    import asyncio
    import re

    from invisible_playwright_mcp import server

    real = {t.name for t in asyncio.run(server.mcp.list_tools())}
    for expression in ACTING:
        with pytest.raises(ValueError) as caught:
            refuse(expression)
        named = set(re.findall(r"browser_\w*", str(caught.value)))
        assert named, "refusal names no tool at all for %r" % expression
        assert not named - real, (
            "the refusal for %r sends the model to a tool that does not exist: "
            "%s" % (expression, sorted(named - real)))


def test_the_server_hands_the_model_the_ladder():
    """The order to try things in, delivered once by the server.

    Also found by mutation: dropping `instructions=` from the server left every
    other test green. Each tool describes itself, so nothing was missing from
    any one description - what was missing was the only statement of which to
    reach for FIRST, and that is precisely what the model got wrong.
    """
    from invisible_playwright_mcp import server

    text = server.mcp.instructions or ""
    assert text, "the server delivers no instructions, so the ladder is nowhere"
    for rung in ("browser_snapshot", "browser_click_at",
                 "browser_take_screenshot", "browser_evaluate"):
        assert rung in text, "the ladder does not mention %s" % rung

    # The ORDER is the content. A list of the same four tools in any order says
    # nothing, and would have prevented nothing.
    assert text.index("browser_click_at") < text.index("browser_evaluate"), (
        "the ladder puts evaluate before coordinates, which is the mistake it "
        "exists to prevent")
    assert text.index("browser_take_screenshot") < text.index("browser_evaluate")


# ── the other half: what the model can SEE ──────────────────────────────────

PAGE = b"""<!doctype html>
<html><head><title>state</title></head><body>
  <input id="nome" type="text" value="Federico">
  <select id="sala">
    <option value="">scegli</option>
    <option value="alfa">Sala Alfa - 4 posti</option>
    <option value="beta" selected>Sala Beta - 12 posti</option>
  </select>
  <input id="proiettore" type="checkbox" checked>
  <input id="schermo" type="checkbox">
  <button id="invia" type="button">Prenota</button>
</body></html>"""


def _serve():
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


@pytest.mark.e2e
def test_the_snapshot_reports_what_the_controls_are_set_to():
    """A real page, because this is JavaScript running in a browser and reading
    the source proves only that somebody typed the right thing.

    The select is the case worth having: its `text` used to be every option
    concatenated, so it read identically before and after a choice was made -
    present in the snapshot, and carrying no information about the one thing
    the caller needed.
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
            return json.loads(await actions.snapshot(session))
        finally:
            await session.close()

    try:
        snap = asyncio.run(run())
    finally:
        srv.shutdown()

    by_id = {e.get("id"): e for e in snap["interactive_elements"]}
    assert set(by_id) >= {"nome", "sala", "proiettore", "schermo"}, by_id

    assert by_id["sala"]["value"] == "beta", (
        "the snapshot does not say what the select is set to: %r" % by_id["sala"])
    assert by_id["sala"]["text"] == "Sala Beta - 12 posti", (
        "the select's text is not the chosen option: %r" % by_id["sala"]["text"])

    assert by_id["proiettore"]["checked"] is True
    assert by_id["schermo"]["checked"] is False, (
        "an unticked box must say so; absent is not the same as false, and a "
        "model cannot tell an unticked box from an unsupported field")

    # And a text field's content still arrives, which it already did.
    assert by_id["nome"]["text"] == "Federico"
