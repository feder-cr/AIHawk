"""A restart is not a reason to throw away a sentence somebody typed.

⛔ ONE WORD MEANT TWO THINGS. `fresh` is what the server sends when somebody
presses Clear, and it is also what it sends to a page that reconnects holding a
position from another transcript - which is what a restarted process looks like
from the outside. The page answered both by wiping, and wiping dropped the
queued message. So a follow-up typed while the agent was working disappeared on
the next restart, with nothing said: the one thing this interface argues
everywhere it must not do, on the feature built precisely because "a reload ate
it".

The reason travels in the TEXT rather than in a new kind, the way `busy`
already carries "1" and "0". That is not a shortcut: a page older than the
server would draw an event kind it has never heard of into the transcript as a
sentence, because the dispatcher is deliberately total. An older page seeing
`fresh` keeps doing exactly what it did before.

The same reasoning is why the server's build travels as a FIELD on a poll the
page already makes rather than as an event.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from invisible_playwright_mcp.ui import PAGE

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="needs node to EXECUTE the page")

CODE = PAGE[PAGE.index("<script"):]


def whole(start, end):
    src = CODE[CODE.index(start):]
    return src[:src.index(end) + len(end)]


def run(js):
    done = subprocess.run([NODE, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_a_reconnection_wipes_the_view_and_keeps_the_queue():
    """Known-bad, two: put `setQueued(null)` back inside `wipe`, and both
    reasons eat the sentence again; drop the test on the text, and a Clear
    stops clearing the queue, which is the other half of the same rule."""
    harness = [
        "let wiped = 0, dropped = 0;",
        # ⛔ THE REAL `wipe` IS SLICED IN BELOW, NOT STUBBED. A first version
        # of this doubled it and the known-bad - putting `setQueued(null)` back
        # inside `wipe` - SURVIVED: the mutation was right and the test never
        # ran the line it changed. A double standing in for the thing under
        # test is a gate that cannot see its own subject.
        "globalThis.setQueued = (v) => { if(v === null) dropped++; };",
        "globalThis.hintNode = {cloneNode: () => 'the guidance'};",
        "globalThis.thread = {setAttribute(){}, firstElementChild: null,",
        "                     set textContent(v){ wiped++; }, appendChild(){}};",
        "globalThis.clearTimeout = () => {}; globalThis.setTimeout = () => 1;",
        "globalThis.quiet = 0;",
        "for (const name of ['waiting','waited','flush','step','land','orphan',",
        "                    'paint','drawChats','newTurn','put','settleOnce',",
        "                    'close','send','clearInterval','seen'])",
        "  globalThis[name] = () => {};",
        "globalThis.$ = () => ({textContent:'', hidden:false, set textContent(v){}});",
        "globalThis.busyNow = false; globalThis.live = null; globalThis.timer = 0;",
        "globalThis.queued = null; globalThis.el = () => ({});",
        "WIPE",
        "HERE",
        "const feed = m => onEvent({data: JSON.stringify(m)});",
        "feed({kind:'fresh', text:'rewound'});",
        "const afterRestart = {wiped, dropped};",
        "feed({kind:'fresh', text:'1'});",
        "const afterClear = {wiped, dropped};",
        "process.stdout.write(JSON.stringify({afterRestart, afterClear}));",
    ]
    js = (chr(10).join(harness)
          .replace("WIPE", whole("function wipe()", chr(10) + "}"))
          .replace("HERE", whole("const onEvent =", chr(10) + "};")))
    got = run(js)

    assert got["afterRestart"] == {"wiped": 1, "dropped": 0}, (
        "a page reconnecting to a restarted server threw away the sentence "
        "somebody had typed and queued: %r" % (got,))
    assert got["afterClear"] == {"wiped": 2, "dropped": 1}, (
        "pressing Clear left the queued message standing, so the conversation "
        "somebody asked to empty sends one more thing: %r" % (got,))


def test_a_queued_message_dies_with_the_conversation_it_belongs_to():
    """Known-bad: drop the `removeItem`, and one key per conversation that ever
    had a queued message stays in this browser for as long as the browser
    does - holding text for something nobody can reach again."""
    harness = [
        "globalThis.here = 'mine';",
        "const store = {'invisible-playwright-mcp.queued.mine':'a', 'invisible-playwright-mcp.queued.other':'b'};",
        "globalThis.localStorage = {removeItem(k){ delete store[k]; }};",
        "HERE",
        "dropQueued('other');",
        "const afterOther = Object.keys(store).sort();",
        "dropQueued();",
        "process.stdout.write(JSON.stringify({afterOther, afterMine: Object.keys(store)}));",
    ]
    # ⛔ `STORE` IS SLICED IN, NOT RETYPED. `qkey` builds its key from it, so a
    # harness that defined the prefix itself would keep passing after the page
    # changed the real one - which is this file's own rule about doubles,
    # applied to a constant instead of a function.
    src = (whole("const STORE =", ";" + chr(10))
           + whole("const qkey = (who)", ";" + chr(10))
           + whole("function dropQueued(", chr(10) + "}"))
    got = run(chr(10).join(harness).replace("HERE", src))

    assert got["afterOther"] == ["invisible-playwright-mcp.queued.mine"], (
        "deleting another conversation did not take its queued message with "
        "it: %r" % (got,))
    assert got["afterMine"] == [], (
        "the key builder no longer answers for the conversation this page is "
        "in: %r" % (got,))


def test_the_page_says_so_when_the_server_moves_under_it():
    """⛔ A PAGE OLDER THAN THE SERVER WAS NOTICED ONLY BY A 404, which means
    only when a route it asks for had gone away entirely - and most versions do
    not remove a route. A tab left open across an upgrade went on running the
    script it was served against a server that had moved, in silence.

    Known-bad, three: never keep the first build, and every poll is a change;
    never compare, and nothing is ever said; say it on every poll instead of
    once, and a tab left open writes the same sentence every three seconds.
    """
    harness = [
        "let said = [];",
        "globalThis.outdated = false;",
        "globalThis.orphan = (kind, text) => said.push(text);",
        "globalThis.build = '';",
        "globalThis.stage = {fleet: [], focus: '', pinned: null, grid: 1, turn: 0};",
        "globalThis.drawStage = () => {};",
        "globalThis.paintWhere = () => {};",
        "let answers = [{browsers: [], focus: '', build: '0.59.0'},",
        "               {browsers: [], focus: '', build: '0.59.0'},",
        "               {browsers: [], focus: '', build: '0.60.0'},",
        "               {browsers: [], focus: '', build: '0.60.0'}];",
        "globalThis.door = async () => ({ok: true, json: async () => answers.shift()});",
        "HERE",
        "(async () => {",
        "  for (let i = 0; i < 4; i++) await drawFleet();",
        "  process.stdout.write(JSON.stringify({said, build}));",
        "})();",
    ]
    src = (whole("function newerServer(", chr(10) + "}") + chr(10)
           + whole("async function drawFleet()", chr(10) + "}"))
    got = run(chr(10).join(harness).replace("HERE", src))

    assert len(got["said"]) == 1, (
        "the page said nothing when the server moved under it, or said it on "
        "every poll: %r" % (got,))
    assert "0.59.0" in got["said"][0] and "0.60.0" in got["said"][0], (
        "the sentence does not name which version this page came from and "
        "which one is answering now: %r" % (got["said"],))
    assert "Reload" in got["said"][0], (
        "the sentence does not say what to do about it: %r" % (got["said"],))


def test_the_build_is_a_field_and_not_an_event():
    """⛔ THE SHAPE IS THE BACKWARD COMPATIBILITY. The page's dispatcher is
    deliberately total - a kind it has never heard of is still drawn - so a new
    EVENT would appear as a stray sentence in the transcript of every page
    still open from the version before. A field on an answer is ignored by a
    reader that does not know it.

    Known-bad: send the build as an event kind instead.
    """
    from invisible_playwright_mcp import routes

    source = re.sub(r"#.*", "", routes.__doc__ or "")
    del source
    import inspect

    stream = inspect.getsource(routes.events)
    assert '"build"' not in stream, (
        "the build was made an event, so every page open from the previous "
        "version draws it into the transcript as a sentence")
    listing = inspect.getsource(routes.browsers)
    assert '"build": __version__' in listing, (
        "the poll every page already makes does not carry the build")
