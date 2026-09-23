"""The transcript follows the agent, and leaves a reader who scrolled up alone.

⛔ IT NEVER FOLLOWED, AND THAT IS NOT WHAT IT LOOKED LIKE. Measured on the real
page before this file existed: the view sat at the bottom for 24 rows and then
fell behind by exactly the height added, 623 px per 20 rows, for as long as the
agent kept working. It reads as "the scrolling stops after a while". It was not
stopping: for those 24 rows the transcript was shorter than the window, so there
was nothing to scroll and every distance to the bottom was trivially zero.

Two separate things were wrong, and the second only became visible once the
first was fixed.

⛔ ONE: THE PAGE HAD TWO ANSWERS TO "IS THE READER FOLLOWING". `settleOnce()`
scrolled once, 150 ms after the first event, and set a latch so nothing would
scroll again - and at 150 ms the transcript is empty, so that one scroll had
nothing to do. Meanwhile an IntersectionObserver knew the answer continuously
and was used only to show a button. The latch drove the scrolling.

The rest was left to `#anchor` and `overflow-anchor:auto`, which can only hold a
bottom something else has reached: the browser will not choose an anchor that is
off screen. Measured, because the alternative reading was that anchoring is
suppressed at scroll offset zero: with the scroller ONE pixel from the top,
374 px of rows arrived and it moved by zero. One pixel is not zero, so the
offset is not the reason.

⛔ TWO: A SCROLL SCHEDULED WHILE APPENDING RUNS BEFORE THE LAYOUT OF WHAT WAS
APPENDED. With the latch gone and `put` scrolling on a frame, a live run
followed perfectly and a REOPENED conversation still opened at the top, three
times out of three, 2084 px from the bottom. Instrumented from inside that
callback: the DOM already held all 65 rows and the scroller still reported a
height of 808, its own window. It scrolled to 808, which clamps to zero. No
choice of target fixes it - `scrollIntoView` on the sentinel reads the same
layout - and checking whether the scroll arrived does not either, because the
check reads that layout too and concludes it did.

So the scroll is triggered by a ResizeObserver on the transcript, which is
delivered AFTER layout. That is the only moment the bottom is knowable, and it
also covers every other way the transcript can grow: a picture that loads, a
font that swaps, a row expanded, the window resized.

⛔ AND THE OTHER HALF IS THE REGRESSION THIS FILE EXISTS TO PREVENT. The old
design bought "never yank a reader who scrolled up" by never scrolling at all. A
fix that follows the bottom and drags a reader back every time a row lands is
worse than the defect it replaces, so both halves are asserted here, and the
"left alone" half is asserted TWICE in a row: a latch would pass it once.
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

#: The mechanism, sliced whole: `toBottom`, the trigger, `put`, and the counter
#: it feeds. Bounded by the comment that opens the narration, which keeps the
#: page's wiring out and lets it run under a shim this small.
FIRST = "/* The one thing that knows where the bottom is."
LAST = "/* The narration is held for one event"

#: A scroller, a way back, and the two observations the browser delivers.
#: Nothing here decides anything: every decision under test is the page's.
SHIM = r"""
const jump = { hidden: true, textContent: '' };

/* ⛔ THE SETTER COUNTS, BECAUSE COUNTING FRAMES COUNTED THE WRONG THING. An
   earlier shim counted its own ticks, so a page that scrolled sixty times
   inside one of them reported one and passed. What is promised is one scroll
   per arrival, so scrolls are what is counted. It clamps like a real scroller
   too, or `toBottom` would leave the offset past the end and every distance
   would read negative. */
let scrolls = 0;
const log = { _top: 0, scrollHeight: 0, clientHeight: 800,
              get scrollTop(){ return this._top; },
              set scrollTop(v){ scrolls++;
                this._top = Math.max(0, Math.min(v, this.scrollHeight - this.clientHeight)); },
              get below(){ return this.scrollHeight - this._top - this.clientHeight; } };
const $ = id => id === 'jump' ? jump : null;
let behind = 0;
let turn = { kids: [], appendChild(n){ this.kids.push(n); } };
function newTurn(){}

/* ⛔ THE TWO OBSERVATIONS, IN THE ORDER THE BROWSER DELIVERS THEM. A resize
   observation comes after layout, an intersection observation after that, so
   the trigger runs while the button still answers about the READER rather than
   about the rows that have just landed. A shim that flipped the button first
   would let a page pass that cannot work in a browser. */
function layout(){
  grew();
  jump.hidden = (log.scrollHeight - log.scrollTop - log.clientHeight) <= 0;
}
function append(){ log.scrollHeight += 30; put({dataset:{}}, false); }
/* One row, laid out on its own: the ordinary rhythm of a run. */
function arrive(){ append(); layout(); }
/* A whole transcript at once, laid out ONCE after every row: what a reopened
   conversation does, and the case a scroll scheduled at append time gets wrong
   because it runs before this. */
function burst(n){ for(let k=0;k<n;k++) append(); layout(); }
function readerScrollsTo(top){
  log.scrollTop = top;
  jump.hidden = (log.scrollHeight - log.scrollTop - log.clientHeight) <= 0;
}
function state(){ return {top: log.scrollTop, below: log.below,
                          jump: jump.hidden ? '' : jump.textContent,
                          behind: behind, scrolls: scrolls}; }
"""


def run(extra: str) -> dict:
    body = PAGE[PAGE.index(FIRST):PAGE.index(LAST)]
    done = subprocess.run([NODE, "-e", SHIM + body + "\n" + extra],
                          capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert done.returncode == 0, "the page threw:\n%s" % done.stderr
    return json.loads(done.stdout)


def test_the_view_follows_while_the_reader_is_at_the_bottom():
    """Known-bad: make `grew` scroll never, and the gap grows by the height of
    every row that lands."""
    got = run("for(let k=0;k<60;k++) arrive();"
              "console.log(JSON.stringify(state()));")
    assert got["below"] <= 0, (
        "the view fell %d px behind the bottom while the reader was following"
        % got["below"])
    assert got["behind"] == 0, (
        "rows were counted as unread while the reader was watching them: %d" % got["behind"])


def test_a_whole_transcript_landing_at_once_ends_at_the_bottom():
    """⛔ THE CASE THAT WAS BROKEN IN A BROWSER, AND THAT NO APPEND-TIME HOOK CAN
    SERVE. Every row is appended and the layout happens once, after them all.

    Known-bad: scroll from `put` instead of from `grew`. Under this shim that
    runs while `scrollHeight` is still the window's own height, so it scrolls to
    a place that clamps to zero - which is exactly what the browser did."""
    got = run("scrolls = 0; burst(60); console.log(JSON.stringify(state()));")
    assert got["below"] <= 0, "the replay did not end at the bottom: %r" % got
    assert got["scrolls"] == 1, (
        "sixty rows laid out once cost %d scrolls" % got["scrolls"])


def test_a_reader_who_scrolled_up_is_left_alone_and_told_what_arrived():
    """⛔ THE HALF THE OLD DESIGN GOT RIGHT, AND THE ONE A FIX CAN BREAK.

    Known-bad: drop the condition in `grew`, and the reader is dragged back
    every time the transcript grows.
    """
    got = run("for(let k=0;k<60;k++) arrive();"
              "readerScrollsTo(log.scrollHeight - log.clientHeight - 400);"
              "const before = state();"
              "for(let k=0;k<10;k++) arrive();"
              "console.log(JSON.stringify({before: before, after: state()}));")
    assert got["before"]["below"] > 100, (
        "the reader never actually scrolled up, so this arm proves nothing: %r" % got["before"])
    assert got["after"]["top"] == got["before"]["top"], (
        "the reader was dragged from %d to %d" % (got["before"]["top"], got["after"]["top"]))
    assert got["after"]["behind"] == 10, (
        "the way back does not say what arrived: %r" % got["after"])


def test_pressing_the_way_back_resumes_following_and_it_can_be_left_again():
    """⛔ ASSERTED TWICE ON PURPOSE. A latch that is set once passes "left
    alone" the first time and never again, which is exactly the shape of the
    defect this file replaces. Following has to be a question the page can ask
    at any moment, so it is asked after a return to the bottom and after a
    second scroll up."""
    got = run("for(let k=0;k<60;k++) arrive();"
              "readerScrollsTo(log.scrollHeight - log.clientHeight - 400);"
              "for(let k=0;k<5;k++) arrive();"
              "toBottom(); seen(); readerScrollsTo(log.scrollHeight - log.clientHeight);"
              "for(let k=0;k<5;k++) arrive();"
              "const following = state();"
              "readerScrollsTo(log.scrollHeight - log.clientHeight - 300);"
              "const wentUp = state();"
              "for(let k=0;k<8;k++) arrive();"
              "console.log(JSON.stringify({following: following, wentUp: wentUp,"
              " ending: state()}));")
    assert got["following"]["below"] <= 0, (
        "after the way back was pressed the view did not resume following: %r" % got["following"])
    assert got["following"]["behind"] == 0, "the counter was not cleared: %r" % got["following"]
    assert got["ending"]["top"] == got["wentUp"]["top"], (
        "the SECOND scroll up was not respected: %d -> %d"
        % (got["wentUp"]["top"], got["ending"]["top"]))
    assert got["ending"]["behind"] == 8, (
        "the counter did not restart from the second scroll up: %r" % got["ending"])


def test_the_scroll_is_triggered_after_layout_and_by_nothing_else():
    """The mechanisms that were tried and measured wrong, asserted as absent.

    `settleOnce` scrolled once and set `pinned`, so the page had two answers to
    one question and the wrong one won. Scheduling on a frame runs before the
    layout of what was just appended. Both are gone; the trigger is the resize
    observation, which is delivered after it.
    """
    # ⛔ THE COMMENTS COME OUT FIRST. The tombstones that record these removals
    # name the things they removed, so a scan over the raw page is satisfied by
    # its own explanation - this repository's most-recorded gate defect, in the
    # direction where it ACCUSES rather than passes.
    code = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    code = re.sub(r"^\s*//.*$", "", code, flags=re.M)
    # ⛔ AND EVERY TERM IS AS NARROW AS THE THING IT MEANS, which took three
    # tries. `pinned` alone accuses `stage.pinned`, the pane the PERSON chose to
    # watch - correct code with a different meaning, and the workspace even
    # carries a comment about the two having clashed by name. And
    # `requestAnimationFrame` over the whole page accuses `fitOrOpen`, which
    # uses one to batch layout READS and has nothing to do with scrolling. So
    # the frame scheduling is asserted absent from THE MECHANISM, and only
    # there.
    for gone in ("settleOnce", "pinned = true"):
        assert gone not in code, (
            "the page still carries %r outside a comment" % gone)
    mechanism = PAGE[PAGE.index(FIRST):PAGE.index(LAST)]
    mechanism = re.sub(r"/\*.*?\*/", "", mechanism, flags=re.S)
    assert "requestAnimationFrame" not in mechanism, (
        "the scroll is scheduled on a frame again, which runs before the layout "
        "of the rows that were just appended")
    assert "new ResizeObserver(grew)" in code, (
        "nothing triggers the scroll after layout any more")
