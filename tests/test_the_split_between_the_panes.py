"""Dragging the divider, and the arithmetic that keeps both panes usable.

⛔ WHICH PANE DESERVES THE ROOM IS A PROPERTY OF THE TASK. Reading a long answer
wants one ratio, watching a form get filled wants another, and a ratio this file
picks is right for neither for long. So the page ships a measured default and
lets it be dragged - which is the change the project's own layout research rated
first, on the grounds that the audience for this tool is closer to an editor
than to a consumer chat.

The part worth executing is the CLAMP. A width dragged wide on a big monitor and
remembered would strand the right pane down to nothing on a laptop, and nothing
about that failure is visible in a string scan: the page still parses, the
handler still exists, and the browser view is simply gone. So the two functions
that compute it are lifted out and run, the same way the renderer is.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from aihawk.web import PAGE

NODE = shutil.which("node")
FIRST = "const SPLITKEY ="
LAST = "function splitter()"

#: Enough DOM for two functions: an element with a style and a width, one that
#: records attributes, and a store that behaves like localStorage.
SHIM = r"""
const KEPT = {};
const localStorage = {
  getItem: k => (k in KEPT ? KEPT[k] : null),
  setItem: (k, v) => { KEPT[k] = String(v); },
  removeItem: k => { delete KEPT[k]; },
};
const LEFT = {
  style: {width: ''},
  getBoundingClientRect: () => ({width: parseFloat(LEFT.style.width) || 530, left: 0}),
};
const SPLIT = {attrs: {}, setAttribute(k, v){ this.attrs[k] = v; }};
const $ = id => (id === 'left' ? LEFT : SPLIT);
const window = {innerWidth: 1920};
/* ⛔ THE LIMITS COME FROM THE STYLESHEET NOW, so the harness has to serve
   them: the floor, the picture's minimum, and the two strips that sit OUTSIDE
   the split. That is the whole point of what is being tested - the ceiling
   used to subtract the picture's minimum from the WHOLE window and promise
   57px it could not give - and a shim inventing its own numbers would be
   testing the shim. They are read from the page's own token block. */
const document = {documentElement: {}};
const TOKENS = %s;
const getComputedStyle = () => ({getPropertyValue: n => TOKENS[n] || ''});
"""


#: One reader for the numbers, used by the shim and by the arithmetic in the
#: assertions: a gate that retypes them is a second place to be wrong.
def PX(name):
    return float(re.search(name + r":\s*([\d.]+)px", PAGE).group(1))


#: The four numbers the split is made of, read from the page that declares
#: them rather than repeated here, which is the defect this change removes.
TOKENS = {name: re.search(name + r":\s*([\d.]+px)", PAGE).group(1)
          for name in ("--pane-min", "--stage-min", "--spine", "--split")}


def clamp(asked, width=1920, remember=True):
    """What the page would set the conversation to, asked for `asked` pixels."""
    body = PAGE[PAGE.index(FIRST):PAGE.index(LAST)]
    js = ((SHIM % json.dumps(TOKENS)) + body
          + "\nwindow.innerWidth = %d;" % width
          + "\nsplitTo(%s, %s);" % (json.dumps(asked), "true" if remember else "false")
          + "\nprocess.stdout.write(JSON.stringify({width: LEFT.style.width,"
            " attrs: SPLIT.attrs, kept: KEPT}));")
    done = subprocess.run([NODE, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, "the splitter threw:\n%s" % done.stderr
    got = json.loads(done.stdout)
    got["px"] = float(str(got["width"]).replace("px", "") or 0)
    return got


pytestmark = pytest.mark.skipif(
    not NODE, reason="needs node to EXECUTE the page's splitter")


def test_a_width_that_is_asked_for_is_the_width_that_is_set():
    got = clamp(700)
    assert got["px"] == 700
    assert got["attrs"]["aria-valuenow"] == "700", got["attrs"]


def test_the_conversation_cannot_be_dragged_to_nothing():
    """Known-bad: drop the `Math.max(min, ...)`. A drag to the left edge leaves
    a column too narrow to read a sentence in, and it is remembered."""
    assert clamp(0)["px"] == 420
    assert clamp(-500)["px"] == 420


def test_the_browser_pane_cannot_be_dragged_to_nothing_either():
    """⛔ THE HALF THAT WOULD BE INVISIBLE. A conversation dragged over the
    whole window leaves no picture at all, and the page still parses, the
    handler still exists, and nothing is red anywhere.

    ⛔ AND THE CEILING WAS 57px OPTIMISTIC, which is what these numbers used
    to encode: they subtracted the picture's minimum from the WHOLE window,
    while the spine and the separator sit outside the split. Dragged to the
    end the browser pane got 423px where the control announced 480, and the
    separator reported a ceiling it could not reach. The arithmetic here is
    built from the same tokens the page reads, so it cannot drift from it
    again.

    Known-bad, two: drop the `Math.min(max, ...)`; compute the ceiling from
    the window without taking off the two strips beside the split.
    """
    room = lambda w: w - PX("--stage-min") - PX("--spine") - PX("--split")
    assert clamp(5000)["px"] == room(1920)
    assert clamp(1900)["px"] == room(1920)


def test_a_width_saved_on_a_big_monitor_is_clamped_on_a_laptop():
    """The reason the ceiling is computed against the window every time rather
    than stored once: the same person opens the same page on a smaller screen.

    Known-bad: compute `max` from a constant.
    """
    room = lambda w: w - PX("--stage-min") - PX("--spine") - PX("--split")
    assert clamp(1440, width=1280)["px"] == room(1280)
    #: the same number on a wide window is inside the range, so it survives
    assert clamp(1200, width=1920)["px"] == 1200


def test_the_floor_wins_when_the_window_is_too_small_for_both():
    """A window narrow enough that floor and ceiling cross: the conversation
    keeps its floor rather than collapsing below it, because a browser pane
    with nothing readable beside it is the worse of the two."""
    assert clamp(600, width=700)["px"] == 420


def test_a_drag_is_remembered_and_a_restore_is_not():
    """The page reads a saved width back through the same clamp on load, and
    that pass must not write it again: nothing the person did, nothing saved.

    Known-bad: ignore the `remember` argument and always write.
    """
    assert clamp(700, remember=True)["kept"] == {"aihawk.split": "700"}
    assert clamp(700, remember=False)["kept"] == {}


def test_the_separator_says_what_it_is_and_where_it_is():
    """A divider that only a mouse can find is a divider half the people using
    this cannot move. The page declares the role and the bounds; the value
    moves with every drag, which is what a screen reader reads out.
    """
    assert 'role="separator"' in PAGE
    assert 'aria-orientation="vertical"' in PAGE
    assert 'tabindex="0"' in PAGE
    #: announced from the same arithmetic the control obeys, or the range a
    #: screen reader reads out is a range the drag will not honour
    assert clamp(700)["attrs"]["aria-valuemax"] == str(int(
        1920 - PX("--stage-min") - PX("--spine") - PX("--split")))
    assert "ArrowLeft" in PAGE and "ArrowRight" in PAGE, (
        "the arrow keys do not move it, so it can only be dragged")


def test_pressing_the_separator_leaves_it_focused():
    """⛔ preventDefault ON pointerdown TAKES THE FOCUS AWAY, and that turns the
    keyboard half of this control off without breaking anything visible.

    The handler calls preventDefault so a drag does not select the text beside
    it. The browser's default action for pressing an element is also what
    focuses it, so cancelling one cancels the other: the divider dragged fine
    and then the arrow keys did nothing, because what had focus was the
    document. Measured by clicking it in a real browser and reading
    `document.activeElement` - no test in this suite clicks anything, and the
    page parses, draws and drags with the defect in place.

    Known-bad: remove the `bar.focus()` line.
    """
    import re

    body = PAGE[PAGE.index("function splitter()"):]
    body = body[:body.index("\npaint();")]
    down = re.search(r"addEventListener\('pointerdown'.*?\n  \}\);", body, re.S)
    assert down, "the separator has no pointerdown handler at all"
    handler = down.group(0)
    if "preventDefault" in handler:
        assert ".focus()" in handler, (
            "the pointerdown handler cancels the default action, which is what "
            "focuses the element, and never focuses it itself: the separator "
            "can be dragged and then not moved with the arrow keys")


def test_the_numbers_the_split_is_made_of_live_in_one_place():
    """⛔ THE SAME FOUR NUMBERS WERE WRITTEN IN FIVE PLACES AND ONE OF THEM
    WAS WRONG. 420 was in the pane's clamp, in the drag code and in the
    markup's `aria-valuemin`; 9 was in the separator's rule and again in the
    ceiling that forgot it; 480 was in the drag code only, subtracted from the
    whole window rather than from the room the two panes share - so the
    control announced a ceiling 57px above the one it would honour, and the
    browser pane bottomed out at 423px where it promised 480.

    Tokens, read by the stylesheet and by the code and announced from the same
    read. What this holds is the property, not the values: no pixel literal in
    the drag code, and the floor a screen reader is told matches the floor the
    drag obeys.

    Known-bad, two: type a number back into the drag code; announce a floor
    from anywhere but the same read.
    """
    body = PAGE[PAGE.index(FIRST):PAGE.index(LAST)]
    code = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    typed = re.findall(r"\b(4[0-9]{2}|530|9)\b", code)
    assert not typed, (
        "the drag code types the layout's numbers again instead of reading "
        "them, so the stylesheet and the control can disagree: %s" % typed)

    got = clamp(700)["attrs"]
    assert got["aria-valuemin"] == str(int(PX("--pane-min"))), (
        "the floor announced to a screen reader is not the floor the drag "
        "obeys: %r" % (got,))
