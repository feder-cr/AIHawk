"""Every control on the page says what it will do, before it is pressed and
after, and one rule says "this cannot be used".

Found by the UX audit of 2026-09-12, all on the running page: Enter queued a
sentence while the button looked exactly like Send; Clear went grey for a whole
run and never said why; the first-run example was drawn as a chip and did
nothing when clicked; a failed load of the session list looked like an empty
one; the largest motion on the page ignored the reduced-motion setting because
it was asked for in script; and four rules spelled "cannot be used" with two
different numbers.

Executed rather than read wherever a fact is about what a handler DOES: the
text of `paint` says nothing about which mode it will pick, and the text of a
click handler says nothing about whether it fires the request.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from aihawk.web import PAGE

NODE = shutil.which("node")
CODE = re.sub(r"/\*.*?\*/|<!--.*?-->", "", PAGE, flags=re.S)
CSS = re.sub(r"/\*.*?\*/", "", PAGE[PAGE.index("<style>"):PAGE.index("</style>")], flags=re.S)


def run(js):
    done = subprocess.run([NODE, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def whole(start, end):
    src = CODE[CODE.index(start):]
    return src[:src.index(end) + len(end)]


needs_node = pytest.mark.skipif(not NODE, reason="needs node to EXECUTE the page")


@needs_node
def test_the_send_button_says_when_enter_will_queue():
    """⛔ NOTHING VISIBLE SAID THAT ENTER WOULD QUEUE. The placeholder said it,
    and a placeholder disappears at the first keystroke: the moment somebody
    had typed a follow-up while the agent worked, the one control in front of
    them looked exactly like Send. The three-way choice was also written twice,
    once for the label and once for the placeholder.

    The mode is decided once, published on the button, and the stylesheet draws
    the queue as the same shape held back - outlined, not filled.

    Known-bad, three: stop publishing the mode; publish it and give it no rule;
    let the ordinary hover rule fill the outlined button back in.
    """
    paint = whole("function paint(){", chr(10) + "}")
    harness = [
        "const what = {textContent:''};",
        "globalThis.chip = {hidden:true, querySelector: () => what};",
        "globalThis.i = {value:'a follow-up', placeholder:''};",
        "globalThis.go = {disabled:false, dataset:{}, setAttribute(){}};",
        "globalThis.halt = {hidden:true};",
        "globalThis.fresh = {attrs:{}, setAttribute(k, v){ this.attrs[k] = v; }};",
        "const seen = {};",
        "globalThis.busyNow = false; globalThis.queued = null; paint(); seen.idle = go.dataset.mode;",
        "globalThis.busyNow = true; paint(); seen.working = go.dataset.mode;",
        "globalThis.queued = 'the first one'; paint(); seen.held = go.dataset.mode;",
        "process.stdout.write(JSON.stringify(seen));",
    ]
    got = run(paint + chr(10) + chr(10).join(harness))
    assert got == {"idle": "send", "working": "queue", "held": "replace"}, (
        "the button does not publish what Enter will do: %r" % (got,))

    #: and the stylesheet draws the difference, and keeps drawing it on hover.
    queue = re.search(r'#go\[data-mode="queue"\][^{]*\{([^}]*)\}', CSS)
    assert queue and "background:transparent" in queue.group(1).replace(" ", ""), (
        "queue mode is published and drawn like Send, so the signal exists only "
        "in the DOM")
    assert re.search(r'#go\[data-mode="queue"\]:hover[^{]*\{[^}]*background', CSS), (
        "the ordinary hover rule fills the outlined button back in, undoing the "
        "signal at the exact moment the pointer arrives")


@needs_node
def test_clear_explains_itself_instead_of_going_dead():
    """⛔ CLEAR WENT GREY FOR THE WHOLE RUN AND NEVER SAID WHY. A `disabled`
    button fires no events - no hover, no click, and in this engine no tooltip -
    so there was nowhere to hang the explanation. It carries `aria-disabled`
    now, keeps the same look through the shared rule, and a press while the
    agent works says what to do.

    Known-bad, three: set `disabled` again; drop the sentence; let the press
    clear anyway.
    """
    paint = whole("function paint(){", chr(10) + "}")
    click = whole("fresh.onclick = () => {", chr(10) + "};")
    harness = [
        "const what = {textContent:''};",
        "globalThis.chip = {hidden:true, querySelector: () => what};",
        "globalThis.i = {value:'', placeholder:''};",
        "globalThis.go = {disabled:false, dataset:{}, setAttribute(){}};",
        "globalThis.halt = {hidden:true};",
        "globalThis.fresh = {attrs:{}, setAttribute(k, v){ this.attrs[k] = v; }};",
        "let said = [], asked = [];",
        "globalThis.orphan = (k, t) => said.push(t);",
        "globalThis.ask = (path) => { asked.push(path); };",
        "globalThis.confirm = () => true;",
        "globalThis.queued = null;",
        "globalThis.busyNow = true; paint();",
        "const look = fresh.attrs['aria-disabled'];",
        "fresh.onclick();",
        "const whileWorking = {said: said.slice(), asked: asked.slice()};",
        "said = []; asked = [];",
        "globalThis.busyNow = false; paint(); fresh.onclick();",
        "process.stdout.write(JSON.stringify({look, whileWorking,",
        "  idle: {said, asked, disabled: !!fresh.disabled}}));",
    ]
    #: the stubs first, then the code that binds to them, then the actions:
    #: `fresh.onclick = ...` runs the moment the script is evaluated.
    at = harness.index("let said = [], asked = [];")
    got = run(chr(10).join(harness[:at]) + chr(10) + paint + chr(10) + click
              + chr(10) + chr(10).join(harness[at:]))
    assert got["look"] == "true", (
        "Clear does not say it is off while the agent works: %r" % (got,))
    assert got["whileWorking"]["asked"] == [], (
        "a press on Clear during a run clears the conversation the agent is "
        "still writing into: %r" % (got["whileWorking"],))
    assert len(got["whileWorking"]["said"]) == 1 and "stop the run" in got["whileWorking"]["said"][0], (
        "a press on Clear during a run does nothing and says nothing: %r"
        % (got["whileWorking"],))
    assert got["idle"] == {"said": [], "asked": ["/chat/fresh"], "disabled": False}, (
        "Clear at rest no longer clears, or explains something to nobody: %r"
        % (got["idle"],))


@needs_node
def test_the_first_run_example_fills_the_box_and_sends_nothing():
    """⛔ THE EXAMPLE WAS DRAWN AS A CHIP AND DID NOTHING WHEN CLICKED, on the
    first screen a new user sees. It fills the composer and does not send - the
    words are put where they can be read and changed. Wired by class on the
    transcript, because the node is cloned back after Clear and a handler on the
    original would not travel with the clone.

    And there is ONE first instruction on the page. The stage's empty state
    carried a second, different one, so the two halves of the page taught two
    different sentences.

    Known-bad, three: make it a paragraph again; send on click; put a second
    example back on the stage.
    """
    assert '<button type="button" class="eg">' in PAGE, (
        "the first-run example is not a button, so it looks pressable and is not")
    stage = PAGE[PAGE.index('id="stage"'):]
    stage = stage[:stage.index("</div>")]
    assert "<code>" not in stage, (
        "the stage teaches a second first instruction beside the one in the hint")

    src = whole("thread.addEventListener('click'", chr(10) + "});")
    harness = [
        "let handler = null, sent = [];",
        "globalThis.thread = {addEventListener(t, fn){ handler = fn; }};",
        "globalThis.i = {value:'', focused:false, events:[],",
        "  dispatchEvent(e){ this.events.push(e.type); }, focus(){ this.focused = true; }};",
        "globalThis.Event = function(type){ this.type = type; };",
        "globalThis.send = (t) => sent.push(t);",
        "HERE",
        "const eg = {textContent: ' Go to example.com and tell me the main heading. ',",
        "            closest: sel => sel === '.eg' ? eg : null};",
        "handler({target: eg});",
        "const other = {closest: () => null};",
        "const before = i.value; handler({target: other});",
        "process.stdout.write(JSON.stringify({value: i.value, focused: i.focused,",
        "  events: i.events, sent, untouched: i.value === before}));",
    ]
    got = run(chr(10).join(harness).replace("HERE", src))
    assert got["value"] == "Go to example.com and tell me the main heading.", (
        "clicking the example does not put its sentence in the box: %r" % (got,))
    assert got["sent"] == [] and got["focused"] and got["events"] == ["input"], (
        "the example sends, or fills the box without handing it the keyboard: %r"
        % (got,))
    assert got["untouched"], "a click anywhere in the transcript rewrites the box"


@needs_node
def test_the_session_list_tells_a_failed_load_from_an_empty_one():
    """⛔ A LIST THAT COULD NOT BE LOADED LOOKED LIKE AN EMPTY ONE. The fetch
    failing returned early and left whatever was drawn before - or, on a first
    open, the sentence `No saved conversations yet`, which was a lie in the
    shape of an empty state. Three outcomes now, and `null` is the answer for
    "I do not know".

    Known-bad: return early in the catch again, or fold the two cases back
    into one sentence.
    """
    src = whole("async function drawChats(){", chr(10) + "}")
    harness = [
        "const made = () => ({kids:[], attrs:{}, dataset:{}, textContent:'',",
        "  appendChild(k){ this.kids.push(k); }, append(...k){ this.kids.push(...k); },",
        "  setAttribute(k, v){ this.attrs[k] = v; }, removeAttribute(k){ delete this.attrs[k]; }});",
        "const box = made();",
        "globalThis.$ = () => box;",
        "globalThis.el = (tag, cls, t) => Object.assign(made(), {tag, cls, t});",
        "globalThis.railsay = () => {}; globalThis.here = 'default';",
        "globalThis.showRail = () => {}; globalThis.renameChat = () => {};",
        "globalThis.forgetChat = () => {};",
        "let answer = null;",
        "globalThis.plainDoor = async () => { if(answer === 'down') throw new Error('down');",
        "  return {ok: true, json: async () => ({sessions: answer})}; };",
        "HERE",
        "(async () => {",
        "  const out = {};",
        "  answer = 'down'; box.kids = []; await drawChats();",
        "  out.down = box.kids.map(k => k.t || k.cls);",
        "  answer = []; box.kids = []; await drawChats();",
        "  out.empty = box.kids.map(k => k.t || k.cls);",
        "  answer = [{id:'a', name:'first'}, {id:'b', name:'second'}]; box.kids = [];",
        "  await drawChats();",
        "  out.rows = box.kids.map(k => k.cls);",
        "  out.role = box.attrs.role;",
        "  process.stdout.write(JSON.stringify(out));",
        "})();",
    ]
    got = run(chr(10).join(harness).replace("HERE", src))
    assert len(got["down"]) == 1 and "could not be loaded" in got["down"][0], (
        "a failed load of the session list is drawn as something else: %r" % (got,))
    assert len(got["empty"]) == 1 and "No saved conversations" in got["empty"][0], (
        "an empty list lost its own sentence: %r" % (got,))
    assert got["rows"] == ["chat", "chat"] and got["role"] == "list", (
        "a list that arrived is not drawn as a list: %r" % (got,))


@needs_node
def test_jump_to_latest_respects_the_reduced_motion_setting():
    """⛔ THE LARGEST MOTION ON THE PAGE WAS THE ONE THE REDUCED-MOTION BLOCK
    COULD NOT REACH: a smooth scroll asked for in script is outside every CSS
    rule. Read at click time, not at load, because the setting can change while
    the tab is open.

    Known-bad: hardcode `smooth`, or read the setting once at load.
    """
    src = whole("$('jump').onclick =", ";" + chr(10))
    harness = [
        "let jump = null, calls = [], reduce = false;",
        "globalThis.$ = () => ({set onclick(fn){ jump = fn; }});",
        "globalThis.anchor = {scrollIntoView(o){ calls.push(o.behavior); }};",
        "globalThis.matchMedia = (q) => ({matches: reduce && q.indexOf('reduce') >= 0});",
        "HERE",
        "jump(); reduce = true; jump();",
        "process.stdout.write(JSON.stringify(calls));",
    ]
    got = run(chr(10).join(harness).replace("HERE", src))
    assert got == ["smooth", "auto"], (
        "jump to latest does not follow the reduced-motion setting at the time "
        "of the click: %r" % (got,))


def test_one_rule_says_a_control_cannot_be_used():
    """⛔ FOUR RULES SAID IT WITH TWO DIFFERENT NUMBERS. .3 on two disabled
    buttons and on inert subtrees, .4 on the empty room's picker, and the
    newest control left out altogether. One rule owns the look, whatever the
    mechanism - `disabled`, `inert` or `aria-disabled`.

    Known-bad: give any control its own opacity back.
    """
    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", CSS)
    own = [sel.strip() for sel, decl in rules
           if re.search(r"opacity:\s*\.[34]\b", decl)
           and not sel.strip().startswith(":disabled")
           and "@keyframes" not in sel and "breathe" not in sel]
    assert own == [], (
        "%d rule(s) say 'cannot be used' with their own number instead of the "
        "shared one: %s" % (len(own), own))
    shared = [sel for sel, decl in rules if sel.strip().startswith(":disabled")]
    assert shared and all(k in shared[0] for k in ("[inert]", '[aria-disabled="true"]')), (
        "the shared rule does not cover every mechanism the page uses: %s" % shared)


def test_a_drawn_word_has_one_look_wherever_it_hangs():
    """The rail's tip carried nine declarations of its own; the second tip - F2
    on a session row, for the keyboard the native tooltip never serves - would
    have copied all nine. The look belongs to the attribute, and each element
    keeps only where the word goes and when it shows.

    Known-bad: give either placement rule a background or padding of its own.
    """
    look = re.search(r"\[data-tip\]::after\{([^}]*)\}", CSS)
    assert look and "content:attr(data-tip)" in look.group(1).replace(" ", ""), (
        "no shared rule draws a data-tip")
    for placed in ("#railtab::after", ".chat::after"):
        rule = re.search(re.escape(placed) + r"\{([^}]*)\}", CSS)
        assert rule, "%s has no placement" % placed
        assert not re.search(r"background|padding", rule.group(1)), (
            "%s re-declares the look instead of only placing the word: %s"
            % (placed, rule.group(1)))
