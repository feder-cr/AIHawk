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

from invisible_playwright_mcp.ui import PAGE

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
    twostep = (whole("const arming = new WeakMap();", ";" + chr(10))
               + whole("function dress(btn, how, armed){", chr(10) + "}") + chr(10)
               + whole("function confirms(btn, resting, asking){", chr(10) + "}") + chr(10)
               + whole("function disarm(btn){", chr(10) + "}"))
    click = whole("fresh.onclick = () => {", chr(10) + "};")
    harness = [
        "const what = {textContent:''};",
        "globalThis.chip = {hidden:true, querySelector: () => what};",
        "globalThis.i = {value:'', placeholder:''};",
        "globalThis.go = {disabled:false, dataset:{}, setAttribute(){}};",
        "globalThis.halt = {hidden:true};",
        "globalThis.fresh = {attrs:{}, dataset:{}, textContent:'Clear', title:'',",
        "                    listeners:[], addEventListener(k, fn){ this.listeners.push([k, fn]); },",
        "                    blur(){ for(const [k, fn] of this.listeners.splice(0)) if(k === 'blur') fn(); },",
        "                    setAttribute(k, v){ this.attrs[k] = v; }};",
        "let said = [], asked = [];",
        "globalThis.orphan = (k, t) => said.push(t);",
        "globalThis.ask = (path) => { asked.push(path); };",
        "globalThis.queued = null;",
        "globalThis.busyNow = true; paint();",
        "const look = fresh.attrs['aria-disabled'];",
        "fresh.onclick();",
        "const whileWorking = {said: said.slice(), asked: asked.slice(),",
        "                      armed: !!fresh.dataset.armed};",
        "said = []; asked = [];",
        "globalThis.busyNow = false; paint();",
        "fresh.onclick();",
        "const once = {asked: asked.slice(), word: fresh.textContent,",
        "              armed: !!fresh.dataset.armed, why: fresh.title};",
        "fresh.onclick();",
        "const twiceState = {asked: asked.slice(), word: fresh.textContent,",
        "                    armed: !!fresh.dataset.armed, disabled: !!fresh.disabled};",
        "asked = [];",
        "fresh.onclick(); fresh.blur(); fresh.onclick();",
        "const afterLeaving = {asked: asked.slice(), armed: !!fresh.dataset.armed};",
        "process.stdout.write(JSON.stringify({look, whileWorking, once,",
        "  twice: twiceState, afterLeaving}));",
    ]
    #: the stubs first, then the code that binds to them, then the actions:
    #: `fresh.onclick = ...` runs the moment the script is evaluated.
    at = harness.index("let said = [], asked = [];")
    got = run(chr(10).join(harness[:at]) + chr(10) + paint + chr(10) + twostep
              + chr(10) + click + chr(10) + chr(10).join(harness[at:]))
    assert got["look"] == "true", (
        "Clear does not say it is off while the agent works: %r" % (got,))
    assert got["whileWorking"]["asked"] == [], (
        "a press on Clear during a run clears the conversation the agent is "
        "still writing into: %r" % (got["whileWorking"],))
    assert len(got["whileWorking"]["said"]) == 1 and "stop the run" in got["whileWorking"]["said"][0], (
        "a press on Clear during a run does nothing and says nothing: %r"
        % (got["whileWorking"],))
    assert got["whileWorking"]["armed"] is False, (
        "a press during a run armed the control, so the next press after the "
        "run ends clears without asking: %r" % (got["whileWorking"],))
    # ⛔ TWO PRESSES, AND NO NATIVE DIALOG. `confirm` blocks the thread it is
    # called on: while it is up the frame pump stops, the transcript stops
    # drawing and the step clock freezes, on a product whose claim is that you
    # can watch the agent work. The sentence it carried is on the control.
    assert got["once"]["asked"] == [] and got["once"]["armed"] is True, (
        "one press clears the conversation, which is the guard being on the "
        "wrong control again: %r" % (got["once"],))
    assert got["once"]["word"] == "Clear?" and "forgets everything" in got["once"]["why"], (
        "the armed control does not say what the next press will do: %r"
        % (got["once"],))
    assert got["twice"]["asked"] == ["/chat/fresh"], (
        "the second press does not clear: %r" % (got["twice"],))
    assert got["twice"]["armed"] is False and got["twice"]["word"] == "Clear", (
        "the control stays armed after it has been used: %r" % (got["twice"],))
    assert got["twice"]["disabled"] is False, (
        "the control went dead rather than saying why")
    # ⛔ AND LEAVING IT IS WHAT DISARMS IT, NOT A TIMER. The first version gave
    # the armed state five seconds, and a press on a control that had quietly
    # disarmed ARMS IT AGAIN - so anybody slower than the timer could never
    # reach the second press. Measured on the running page: three presses,
    # nothing happened. Worse by ear: the armed label takes a screen reader
    # some seven seconds to say, so it disarmed itself midway through
    # announcing what the next press would do.
    assert got["afterLeaving"] == {"asked": [], "armed": True}, (
        "the control kept its armed state after the attention moved away, or "
        "lost it while the attention was still on it: %r" % (got["afterLeaving"],))

    assert "confirm(" not in CODE and "prompt(" not in CODE, (
        "a native dialog is back on this page, and it stops the live view, the "
        "transcript and the clocks for as long as it is up")


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
        "globalThis.railsay = () => {}; globalThis.isHere = (id) => id === 'default';",
        "let defaultId = '';",
        "globalThis.showRail = () => {}; globalThis.renameChat = () => {};",
        "globalThis.forgetChat = () => {};",
        "let answer = null;",
        "globalThis.door = async () => { if(answer === 'down') throw new Error('down');",
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
def test_jump_to_latest_lands_at_the_bottom_and_says_how_much_is_behind():
    """⛔ AN ANIMATION CANNOT ARRIVE AT A TARGET THAT MOVES.

    It asked for a SMOOTH scroll, which computes a destination and animates to
    it over a few hundred milliseconds - and every row that arrives during the
    animation pushes the anchor further down. Measured with the agent working:
    one press moved the view 2,700px and still left 303px to go, the anchor
    282px below the fold, the button still on screen; the content had grown
    283px while the animation ran, which is almost exactly the shortfall. Press
    again, same thing, one step behind forever. The same press with the run
    finished landed 20px from the bottom and the button went away.

    So it lands at once. And it carries the count, because while a reader is
    scrolled up every signal that the agent is alive is drawn at the BOTTOM of
    the transcript, which is where they are not: measured on a real run, 59
    steps while the owner watched the first 14.

    ⛔ THIS SAID "and the stylesheet keeps the view at the bottom from there",
    and that was measured false: `#anchor` is the only child the browser may
    anchor to and it will not choose one that is off screen, so the stylesheet
    holds a bottom something else has reached and holds nothing otherwise. What
    keeps the view there is `put`, which asks the observer whether the reader is
    following. See `test_the_transcript_follows_the_agent.py`.

    Known-bad, three: ask for a smooth scroll again; scroll to something other
    than the full height; leave the count standing after the press.
    """
    # `toBottom` joined the slice when the press stopped spelling the scroll out
    # for itself: one function now knows where the bottom is, because a row
    # arriving while the reader is following needs the same answer. Every
    # assertion below is unchanged - what moved is where the line lives.
    src = (whole("function toBottom()", "}") + chr(10)
           + whole("function paintJump()", chr(10) + "}") + chr(10)
           + whole("function seen()", "}" + chr(10))
           + whole("$('jump').onclick =", ";" + chr(10)))
    harness = [
        "let jump = null, said = [];",
        "const btn = {hidden:false, set textContent(v){ said.push(v); },",
        "             set onclick(fn){ jump = fn; }};",
        "globalThis.behind = 7;",
        "globalThis.log = {scrollTop: 300, scrollHeight: 4117};",
        "globalThis.$ = () => btn;",
        "HERE",
        "paintJump();",
        "jump();",
        "process.stdout.write(JSON.stringify({said, landed: log.scrollTop,",
        "                                     behind: globalThis.behind}));",
    ]
    got = run(chr(10).join(harness).replace("HERE", src))

    assert got["said"][0] == "jump to latest - 7 new", (
        "the one control on screen while a reader is scrolled up says nothing "
        "about what has arrived: %r" % (got,))
    assert got["landed"] == 4117, (
        "the press does not land at the bottom of what is there, so rows "
        "arriving during the move leave it short: %r" % (got,))
    assert got["behind"] == 0 and got["said"][-1] == "jump to latest", (
        "the count survives the press that answered it: %r" % (got,))

    assert "smooth" not in whole("$('jump').onclick =", ";" + chr(10)), (
        "the press asks for an animation again, and an animation cannot arrive "
        "at a target that moves")

    watcher = whole("new IntersectionObserver", "observe(anchor);")
    assert "seen()" in watcher, (
        "arriving at the bottom by scrolling does not clear the count, so the "
        "button goes on offering to take somebody where they already are")



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
