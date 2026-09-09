"""One screen, or two, or four, and which browsers are on them.

⛔ THE NUMBER OF SCREENS IS A MEASURED DECISION AND NOT A PREFERENCE. Every
frame goes down the same stdio pipe as every action, behind the same lock, so a
screen is pipe time the agent does not have for clicking. Measured on
2026-09-09 with four real browsers over the Link the interface itself uses: a
frame costs 5 to 6 ms - not the 22 ms this project assumed for months, because
the capture already runs inside the engine and the server hands over the latest
picture rather than taking one - and four panes polled flat out delivered 80
frames a second in total, about 20 each, with an action still landing in 49 ms
against 40 with a single pane. Four is affordable; eight would saturate the
pipe. That is why the control room's vocabulary, 1 / 2 / 4, is the one on
offer.

What is executed here is the part that decides WHICH browsers are on the stage
and in what order, because that is the half a string scan cannot see: it is
arithmetic over the fleet, and getting it wrong shows up as a screen that is
blank, or as the browser you clicked never coming to the front.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from aihawk.web import PAGE

NODE = shutil.which("node")
FIRST = "function onStage()"
LAST = "function blank(cell, why)"

SHIM = """
let fleet = %s;
let grid = %d;
const pinned2 = %s;
const focusHere = %s;
const watched = () => pinned2 || focusHere;
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
    return [{"id": i, "running": True, "urls": ["http://x/"]} for i in ids]


def up(*ids):
    return [{"id": i, "running": True, "urls": ["http://x/"]} for i in ids]


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


def test_one_screen_shows_the_one_being_watched():
    assert on_stage(up("a", "b", "c"), grid=1, focus="b") == ["b"]
    assert on_stage(up("a", "b", "c"), grid=1, focus="b", pinned="c") == ["c"]


def test_the_watched_one_comes_first_so_clicking_brings_it_to_the_front():
    """⛔ THE POINT OF THE WHOLE THING. Clicking a screen sets who is watched,
    and at one-up that has to be the screen that fills the stage - which only
    works if the order puts it first.

    Known-bad: return the fleet in server order and slice it.
    """
    assert on_stage(up("a", "b", "c", "d"), grid=4, focus="c")[0] == "c"
    assert on_stage(up("a", "b", "c", "d"), grid=2, pinned="d") == ["d", "a"]


def test_a_browser_that_is_not_running_is_never_given_a_screen():
    """Asking a declared browser for a picture STARTS it - 800 MB and seven
    seconds to fill a tile nobody asked for. The rule the single pane already
    followed, kept now that there are four of them.

    Known-bad: drop the `b.running` filter.
    """
    fleet = up("a") + [{"id": "z", "running": False, "urls": []}] + up("b")
    assert on_stage(fleet, grid=4) == ["a", "b"]


def test_the_stage_never_holds_more_than_the_layout_asks_for():
    """Known-bad: drop the slice. Eight live screens is the arithmetic that
    saturates the pipe, which is the thing the measurement forbids."""
    for n in (1, 2, 4):
        assert len(on_stage(up("a", "b", "c", "d", "e", "f"), grid=n)) == n


def test_the_strip_carries_what_the_stage_does_not():
    """Otherwise a browser shows twice at four-up, or vanishes at one-up.

    Read from the code rather than executed: it is one line, and what it has to
    be is a set difference against the stage.
    """
    code = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    assert re.search(r"const up = new Set\(onStage\(\)\.map\(b => b\.id\)\);", code), (
        "the strip is no longer built from what the stage is showing")
    assert re.search(r"fleet\.filter\(b => !up\.has\(b\.id\)\)", code), (
        "the strip does not exclude the browsers already on screen")


def test_the_layout_is_remembered_and_read_back_through_one_door():
    """A choice made once is a choice made once. And the saved value goes
    through `setGrid`, so there is a single path that sets the layout rather
    than a boot that duplicates what the buttons do.

    Known-bad: write the layout straight into `grid` at boot.
    """
    code = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    assert "localStorage.setItem(GRIDKEY" in code, "the layout is not remembered"
    assert re.search(r"setGrid\(LAYOUTS\.includes\(Number\(sawGrid\)\) \? Number\(sawGrid\) : 1\)",
                     code), (
        "the saved layout is not restored through setGrid, or is trusted "
        "without checking it is one of the layouts on offer")


def test_the_template_follows_the_screens_that_exist():
    """⛔ A LAYOUT IS A CEILING, NOT A PROMISE. Two running browsers in a
    four-up layout were laid on a 2x2 whose second row was empty, so each of
    them drew at half the height for nothing: the person asked to watch up to
    four and got two small pictures instead of two large ones.

    Known-bad: write the chosen layout into the stage, which is what it did.
    """
    code = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    assert "box.dataset.grid = String(Math.min(grid, Math.max(1, show.length)))" in code, (
        "the stage template is not solved from the screens actually drawn")
    assert '#stage[data-grid="3"]' in PAGE, (
        "three screens have no template, so a four-up layout with three "
        "browsers running falls back on whichever rule happens to match")


def test_the_state_word_says_nothing_when_it_would_repeat_the_tab():
    """The Live/Frozen tabs are a control that shows its own state, and the word
    beside them said `live` while Live was selected: one fact printed twice, the
    second time in the place the eye goes for news. `idle`, `busy` and `error`
    are news and still appear, and the dot goes on carrying live and frozen,
    which is what a dot is for.

    Known-bad: print every state, which is what it did.
    """
    code = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    assert "stateEl.classList.toggle('sr', s === 'live' || s === 'frozen')" in code, (
        "the state word is shown even when it only repeats the selected switch")
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
    tick = re.search(r"async function tick\(\)\{(.*?)\n\}", code, re.S)
    assert tick, "the pump is gone"
    assert "try" in tick.group(1) and "setTimeout(tick" in tick.group(1), (
        "the scheduler does not guard the pass it runs, so one bad frame ends "
        "the loop: %s" % tick.group(1))
