"""One screen, or two, and which browsers are on them.

⛔ THE NUMBER OF SCREENS IS A MEASURED DECISION AND NOT A PREFERENCE. Every
frame goes down the same stdio pipe as every action, behind the same lock, so a
screen is pipe time the agent does not have for clicking. Measured on
2026-09-09 with four real browsers over the Link the interface itself uses: a
frame costs 5 to 6 ms - not the 22 ms this project assumed for months, because
the capture already runs inside the engine and the server hands over the latest
picture rather than taking one - and four panes polled flat out delivered 80
frames a second in total, about 20 each, with an action still landing in 49 ms
against 40 with a single pane. Four is affordable; eight would saturate the
pipe.

⛔ AND THE MEASUREMENT IS WHY THE NUMBER IS NOT A CHOICE ANY MORE. It was taken
when a session could hold up to eight browsers and a picker offered 1 / 2 / 4;
a session is `main` plus, while it is needed, `support`, so the layout follows
the fleet - two screens when the helper is up, one when it is not - and there
is nothing for a person to set. The numbers stay because they are what says
two panes are affordable.

What is executed here is the part that decides WHICH browsers are on the stage
and in what order, because that is the half a string scan cannot see: it is
arithmetic over the fleet, and getting it wrong shows up as a screen that is
blank, or as two panes that swap places while somebody is watching them.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from invisible_playwright_mcp.ui import PAGE

NODE = shutil.which("node")
FIRST = "function onStage()"
LAST = "function blank(cell, why)"

SHIM = """
const stage = {fleet: %s, grid: %d, pinned: %s, focus: %s, turn: 0};
const watched = () => stage.pinned || stage.focus;
"""


def on_stage(browsers, grid=1, pinned=None, focus=""):
    """The ids the page would put on the stage, in order, for this fleet."""
    body = PAGE[PAGE.index(FIRST):PAGE.index(LAST)]
    js = (SHIM % (json.dumps(browsers), grid, json.dumps(pinned), json.dumps(focus))
          + body
          + "\nprocess.stdout.write(JSON.stringify(onStage().map(b => b.id)));")
    done = subprocess.run([NODE, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, "the stage chooser threw:\n%s" % done.stderr
    return json.loads(done.stdout)


def up(*ids):
    return [{"id": i, "urls": ["http://x/"]} for i in ids]


FIRST_CUT = "const CHROME ="
LAST_CUT = "function ageAll(cells)"

#: Four windows of different shapes in cells of different shapes, which is the
#: case the fingerprint guarantees: every browser here gets a window of its own.
CUT_PROBE = r"""
const shots = [];
for(const [w, h, bw, bh] of [[1280,800,600,400],[1024,768,600,400],
                             [1440,900,300,260],[800,600,520,300]]){
  const im = { naturalWidth:w, naturalHeight:h, style:{},
               getBoundingClientRect: () => ({width:bw, height:bh}) };
  cutTheChrome({dataset:{}}, im);
  const cut = Number(/inset\((\d+)px/.exec(im.style.clipPath)[1]);
  const move = Number(/translateY\((-?\d+)px/.exec(im.style.transform)[1]);
  const drawn = Math.min(bh, bw * h / w);
  const above = cut + move;
  shots.push({w, h, bw, bh, cut, drawn: Math.round(drawn), above,
              below: Math.round(bh - above - (drawn - cut))});
}
process.stdout.write(JSON.stringify(shots));
"""


pytestmark = pytest.mark.skipif(
    not NODE, reason="needs node to EXECUTE the stage chooser")


def test_one_screen_is_the_one_browser_there_is():
    """The layout follows the fleet - one browser, one screen - so at one-up
    there is never a choice to make about which one it is."""
    assert on_stage(up("a"), grid=1) == ["a"]
    assert on_stage(up("a"), grid=1, focus="a", pinned="a") == ["a"]


def test_the_order_is_the_server_s_and_does_not_move_with_who_is_watched():
    """⛔ THE WATCHED SCREEN IS MARKED, NEVER MOVED, AND THAT CHANGED IN
    0.55.0 WITH THE THING THAT MADE IT MATTER.

    It used to be sorted to the front, which meant something while a session
    held up to eight browsers and the stage showed fewer than all of them:
    clicking a chip brought that browser onto a screen. The stage now shows
    two screens exactly when there are two browsers, so the sort could only
    decide which of two equal cells sat on the left - and in this same version
    `focus` stopped being the constant `main` and became the browser the agent
    last acted in. Together those two would have swapped the panes under the
    eye of whoever was watching, every time the agent moved between them.

    Known-bad: put the watched one first again. The second assertion, and only
    the second, goes red - which is the shape of the defect: it is invisible
    while nobody is watching a second browser.
    """
    assert on_stage(up("main", "support"), grid=2, focus="main") == ["main", "support"]
    assert on_stage(up("main", "support"), grid=2, focus="support") == ["main", "support"]
    assert on_stage(up("main", "support"), grid=2, pinned="support") == ["main", "support"]


def test_every_browser_the_server_lists_gets_a_screen():
    """⛔ THE FILTER THIS PAGE USED TO CARRY IS GONE WITH THE FLAG IT READ.
    A `running: false` row meant a browser declared and not started, and
    drawing it would have asked for a picture and STARTED it - 800 MB and
    seven seconds for a tile nobody asked for. Since 0.53.0 there is no such
    row: the server lists what is open, drops what has gone, and the flag it
    still sent was true on every row it could produce until 0.54.0.

    So the page takes the rows as they come, and what keeps the expensive
    case away is the SERVER (`test_open_first.py`: the listing drops a
    browser whose engine is gone), not a filter here.

    Known-bad: filter the fleet on a field, any field, that the answer does
    not carry - every screen disappears.
    """
    assert on_stage(up("a", "b"), grid=2) == ["a", "b"]
    assert on_stage(up("a"), grid=2) == ["a"]


def test_the_stage_never_holds_more_than_the_layout_asks_for():
    """Known-bad: drop the slice. Eight live screens is the arithmetic that
    saturates the pipe, which is the thing the measurement forbids."""
    for n in (1, 2):
        assert len(on_stage(up("a", "b", "c", "d", "e", "f"), grid=n)) == n


def test_the_stage_follows_the_browsers_and_is_not_chosen():
    """⛔ THIS TEST USED TO ASSERT THAT THE LAYOUT WAS REMEMBERED, and it was
    right then: a session could hold eight browsers, so how many to watch at
    once was a choice a person made and the page kept.

    A session holds `main` and, while it is needed, `support`. Two screens when
    the helper is up, one when it is not, and nothing to choose - so the picker
    is gone, and with it the stored preference. What is held here instead is
    that the number FOLLOWS the running browsers rather than sitting in a
    variable somebody has to keep in step.

    Known-bad, two: pin `grid` to 1, and the helper never gets a screen; pin it
    to 2, and a session with only `main` draws an empty second cell.
    """
    code = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    assert "GRIDKEY" not in code and "setGrid" not in code, (
        "the layout picker is back, and there is nothing for it to choose")

    # Anchored on `stage.fleet`, because the declaration of the state object
    # sits earlier in the page and a looser pattern reads the declaration as
    # the decision - it answers 1 for every fleet, which looks like a stage
    # that never grows.
    line = re.search(r"stage\.grid = stage\.fleet[^;]+;", code)
    assert line, "nothing derives the number of screens from the fleet"

    js = ("const answers = [];"
          "const stage = {};"
          "for(const running of [0, 1, 2]){"
          "  stage.fleet = Array.from({length: running}, () => ({running: true}));"
          "  %s"
          "  answers.push(stage.grid);"
          "}"
          "process.stdout.write(JSON.stringify(answers));" % line.group(0))
    done = subprocess.run([NODE, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, "the layout decision threw: %s" % done.stderr

    assert json.loads(done.stdout) == [1, 1, 2], (
        "the stage does not follow the browsers that are running: %s"
        % done.stdout)


def test_the_template_follows_the_screens_that_exist():
    """⛔ A LAYOUT IS A CEILING, NOT A PROMISE. Two running browsers in a
    four-up layout were laid on a 2x2 whose second row was empty, so each of
    them drew at half the height for nothing: the person asked to watch up to
    four and got two small pictures instead of two large ones.

    Known-bad: write the chosen layout into the stage, which is what it did.
    """
    code = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    assert "box.dataset.grid = String(Math.min(stage.grid, Math.max(1, show.length)))" in code, (
        "the stage template is not solved from the screens actually drawn")
    # And no template for a third screen: a session holds two browsers, so a
    # rule for three or four is a rule no fleet can reach, kept for a layout
    # picker that is gone.
    assert '#stage[data-grid="3"]' not in PAGE and '#stage[data-grid="4"]' not in PAGE, (
        "the page carries templates for screens a session cannot have")


def test_the_state_word_says_nothing_when_it_would_repeat_the_tab():
    """The Live/Frozen tabs are a control that shows its own state, and the word
    beside them said `live` while Live was selected: one fact printed twice, the
    second time in the place the eye goes for news. `busy`, `offline` and `error`
    are news and still appear, and the dot goes on carrying live and frozen,
    which is what a dot is for.

    ⛔ `idle` JOINED THE QUIET THREE, AND IT WAS ALREADY QUIET THE WRONG WAY.
    A rule in the browser stylesheet clipped the WHOLE state box to one pixel
    whenever the pane was empty, which is right for `idle` - capitals, the
    brightest thing on a bar describing an empty room - and wrong for every
    other word that box can hold. Drop the stream on a first run and `offline`
    was written into a clipped box: a 7px dot changed colour and nobody got the
    word. Two places decided whether a word is worth showing; the one that knows
    WHICH word decides now, and the rule is gone.

    Known-bad, two: print every state, which is what it did; or add `offline` or
    `error` to this list, which hides the two words that exist to be read.
    """
    code = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    quiet = re.search(r"stateEl\.classList\.toggle\('sr',([^)]*)\)", code)
    assert quiet, "nothing decides whether the state word is worth showing"
    said = quiet.group(1)
    assert set(re.findall(r"'([a-z]+)'", said)) == {"live", "frozen", "idle"}, (
        "the states the word stays quiet for are %s: live and frozen repeat the "
        "switch beside them and idle names an empty room, and anything else in "
        "that list is a word somebody needs" % sorted(re.findall(r"'([a-z]+)'", said)))
    # ⛔ AND THE MARKUP STARTS THE WAY `say` WOULD DRAW IT. Nothing calls
    # `say('idle')` on a first load - the state only moves when a browser does -
    # so with the clipping rule gone the word came back on screen in capitals,
    # in the corner of an empty room. Found by opening the page after the rule
    # was deleted, not by any assertion here.
    state = re.search(r'<span id="state"[^>]*class="([^"]*)"', PAGE)
    assert state and "sr" in state.group(1).split(), (
        "the state box starts on screen carrying the one word that is never "
        "worth showing: %s" % (state.group(1) if state else "no span"))
    assert '#right[data-empty="1"] #state' not in code, (
        "the empty room clips the state box again, so the word that says the "
        "stream died lands in a box one pixel wide")
    # ⛔ AND IT GOES OFF-SCREEN, NOT AWAY. `hidden` is display:none, and a live
    # region mutated inside a display:none subtree announces nothing - so the one
    # transition that matters, live to error, was silent for a screen reader
    # exactly because the word had been redundant a moment before.
    #
    # Known-bad: go back to `stateEl.hidden = ...`.
    assert "stateEl.hidden" not in code, (
        "the state word is removed from the accessibility tree, so the change "
        "that matters is never announced")


def test_the_pump_cannot_be_killed_by_a_bad_pass():
    """⛔ IT WAS, THE FIRST TIME THIS RAN. `ageAll` reached for the age label on
    the placeholder cell, which has no caption, threw, and because the throw was
    outside the fetch's try the timer at the bottom was never reached: the pump
    stopped for good, in silence. A dead pump reads as a server that has stopped
    answering, not as a page with a bug in it.

    Known-bad: put the body back inside `tick` so a throw skips the timer.
    """
    code = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    pump = re.search(r"function every\(pause, pass\)\{(.*?)\n\}", code, re.S)
    assert pump, "the one pump shape is gone"
    assert "try" in pump.group(1) and "finally" in pump.group(1) \
        and "setTimeout(turn" in pump.group(1), (
        "the scheduler does not guard the pass it runs, so one bad frame ends "
        "the loop: %s" % pump.group(1))


def fleet_after(ok: bool, body: dict, before) -> dict:
    """What `drawFleet` leaves on the stage, given what the poll answered."""
    i = PAGE.index("async function drawFleet()")
    js = (
        "const stage = {fleet: %s, focus: 'main', pinned: null, grid: 2, turn: 0};\n"
        "function drawStage(){}\nfunction paintWhere(){}\n"
        "async function door(){ return {ok: %s, json: async () => (%s)}; }\n"
        % (json.dumps(before), "true" if ok else "false", json.dumps(body))
        + PAGE[i:PAGE.index(chr(10) + "}", i) + 2]
        + "\ndrawFleet().then(() => process.stdout.write(JSON.stringify("
          "{ids: stage.fleet.map(b => b.id), focus: stage.focus, grid: stage.grid})));")
    done = subprocess.run([NODE, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, "drawFleet threw:\n%s" % done.stderr
    return json.loads(done.stdout)


def test_a_poll_that_failed_leaves_the_workspace_it_already_has():
    """⛔ ONE UNANSWERED QUESTION USED TO TEAR DOWN EVERY SCREEN. The failure
    branch fell through with an empty fleet, so a server restarting or a link
    that dropped drew the empty room that says `No browser open` over browsers
    that were open the whole time - and the next poll three seconds later put
    them back. A workspace that blinks out and in is worse than either state,
    because nothing on screen says which one is true.

    It matters more since 0.55.0, when the route stopped smoothing an
    unreadable answer into an empty workspace and started saying 503: that
    status is exactly what arrives here as `!r.ok`.

    Known-bad: drop the `return` and let the old `{browsers: []}` default fall
    through. The first assertion goes red.
    """
    two = [{"id": "main", "urls": ["http://a/"]},
           {"id": "support", "urls": ["http://b/"]}]

    held = fleet_after(False, {}, two)
    assert held["ids"] == ["main", "support"], (
        "a failed poll emptied the stage: %r" % (held,))
    assert held["grid"] == 2, "and took the layout with it: %r" % (held,)

    moved = fleet_after(True, {"browsers": two[:1], "focus": "main"}, two)
    assert moved["ids"] == ["main"], (
        "an answer that DID arrive has to be believed: %r" % (moved,))


def big_for(fleet, pinned=None, focus="main"):
    """Which cell the stage marks as the one to give the room to."""
    i = PAGE.index("function drawStage()")
    body = PAGE[i:PAGE.index(chr(10) + "}", i) + 2]
    js = ("const box = {dataset:{}, style:{}, textContent:'', children:[],"
          "  appendChild(){}, querySelectorAll: () => []};\n"
          "const stage = {fleet: %s, grid: %d, pinned: %s, focus: %s, turn: 0};\n"
          "const watched = () => stage.pinned || stage.focus;\n"
          "function onStage(){ return stage.fleet.slice(0, stage.grid); }\n"
          "function dropFrames(){}\n"
          "function screenFor(){ return {}; }\n"
          "function setState(){}\n"
          "const emptyCell = {cloneNode: () => ({})};\n"
          "const right = {dataset:{}};\n"
          "const $ = () => box;\n"
          % (json.dumps(fleet), 2 if len(fleet) > 1 else 1,
             json.dumps(pinned), json.dumps(focus))
          + body
          + "\ndrawStage();"
            "\nprocess.stdout.write(JSON.stringify({big: box.dataset.big || null,"
            " grid: box.dataset.grid}));")
    done = subprocess.run([NODE, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, "drawStage threw:\n%s" % done.stderr
    return json.loads(done.stdout)


def test_the_screen_somebody_pinned_gets_the_room():
    """⛔ CLICKING A SCREEN MARKED IT AND LEFT IT THE SIZE OF THE OTHER ONE. With
    two browsers open you always watched at half width, and reading a form the
    agent is filling in is most of what watching IS.

    The other screen stays on the stage rather than going away: the agent may
    move to it at any moment, and losing sight of that is worse than a narrow
    picture. And it only happens when the PERSON has pinned one - the layout
    never moves on its own, which is the line this page draws everywhere
    between the agent's hand and the reader's eye.

    Known-bad, two: give the room to the FOCUSED screen, and the layout jumps
    every time the agent changes browser; number the cells from zero, and the
    stylesheet gives the room to the wrong one.
    """
    two = up("main", "support")

    assert big_for(two)["big"] is None, (
        "the stage gives one screen the room with nobody having asked")
    assert big_for(two, focus="support")["big"] is None, (
        "the agent moving browser resizes the panes under the person watching")
    assert big_for(two, pinned="main")["big"] == "1", (
        "the screen somebody pinned is not the one the stylesheet is told about")
    assert big_for(two, pinned="support")["big"] == "2", (
        "the cells are numbered from zero, so the room goes to the other one")

    rule = PAGE[PAGE.index('#stage[data-grid="2"][data-big="1"]'):]
    rule = rule[:rule.index("}") + 1]
    assert "2fr 1fr" in rule, (
        "the pinned screen is not given more of the stage: %s" % rule)
