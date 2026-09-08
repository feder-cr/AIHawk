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
"""


def clamp(asked, width=1920, remember=True):
    """What the page would set the conversation to, asked for `asked` pixels."""
    body = PAGE[PAGE.index(FIRST):PAGE.index(LAST)]
    js = (SHIM + body
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

    Known-bad: drop the `Math.min(max, ...)`.
    """
    assert clamp(5000)["px"] == 1920 - 480
    assert clamp(1900)["px"] == 1440


def test_a_width_saved_on_a_big_monitor_is_clamped_on_a_laptop():
    """The reason the ceiling is computed against the window every time rather
    than stored once: the same person opens the same page on a smaller screen.

    Known-bad: compute `max` from a constant.
    """
    assert clamp(1440, width=1280)["px"] == 1280 - 480
    assert clamp(1440, width=1920)["px"] == 1440


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
    assert clamp(700)["attrs"]["aria-valuemax"] == "1440"
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
