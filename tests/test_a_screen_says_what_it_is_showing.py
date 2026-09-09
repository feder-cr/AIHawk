"""What a screen looks like when it has nothing to show, and what shape it takes.

⛔ FOUR STATES USED TO DRAW ONE BLACK RECTANGLE. A pane waiting for its first
frame, a browser with no tab open, one that stopped answering and a capture that
failed were pixel-identical: an empty dark box with a name under it. Three of
those four are ordinary and one is a failure, and the product said the same
thing about all of them - which is how a pane that is simply patient came to
look like a pane that is broken.

⛔ AND THE CELL USED TO BE A CONTAINER, NOT A FRAME. Measured on the bench: a
1280x688 window in a one-up cell drew 40% of the card as black, and at two-up two
cards of equal size held pictures of unequal size, so the smaller one read as a
mistake rather than as a narrower window. The frame now takes the picture's own
shape, cropped of the browser chrome, and the whole of it is executed here
rather than described - it is arithmetic over two natural dimensions.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from aihawk.web import PAGE

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="needs node to EXECUTE the page")

#: A DOM small enough to print, with the four things this code touches:
#: children, a dataset, a style that remembers custom properties, and a
#: querySelector that understands a class or a tag.
SHIM = r"""
class N {
  constructor(tag){
    this.tag = tag; this.kids = []; this.className = ''; this.dataset = {};
    this.attrs = {}; this.hidden = false; this.title = ''; this._text = null;
    this.style = { _p:{}, setProperty(k,v){ this._p[k] = String(v) },
                   getPropertyValue(k){ return this._p[k] || '' } };
  }
  get textContent(){
    return this._text != null ? this._text : this.kids.map(k => k.textContent).join('');
  }
  set textContent(v){ this._text = String(v); this.kids = []; }
  appendChild(n){ this.kids.push(n); this._text = null; return n; }
  append(...xs){ for(const x of xs) this.appendChild(x); }
  setAttribute(k, v){ this.attrs[k] = String(v); }
  querySelector(sel){
    const hit = n => sel.startsWith('.') ? (' ' + n.className + ' ').includes(' ' + sel.slice(1) + ' ')
                                         : n.tag === sel;
    const walk = n => { for(const k of n.kids){ if(hit(k)) return k;
                                                const deep = walk(k); if(deep) return deep; }
                        return null; };
    return walk(this);
  }
}
const document = { createElement: t => new N(t), createTextNode: t => { const n = new N('#text'); n._text = t; return n; } };
const el = (t,c,x) => { const e = document.createElement(t);
                        if(c) e.className = c; if(x != null) e.textContent = x; return e; };
let focusHere = 'b-two';
let pinned2 = null;
const watched = () => pinned2 || focusHere;
function watchThis(){}
function tree(n){ return {tag: n.tag, cls: n.className, hidden: n.hidden,
                          data: n.dataset, text: n._text,
                          style: n.style._p, kids: n.kids.map(tree)}; }
"""

FIRST = "const CHROME = 0.083;"
LAST = "/* Built from elements with textContent and never innerHTML"
CELLS_FIRST = "function blank(cell, why){"
CELLS_LAST = "function drawStage(){"


def one(name: str) -> str:
    """One top-level function, from its `function` to its closing brace.

    Bounding a slice by "the next function" pulls in whatever sits between
    them - here a line that wires a click handler through `$` - and a slice
    that drags in the page's wiring stops being a unit and becomes half a page
    that will not run.
    """
    i = PAGE.index("function %s(" % name)
    j = PAGE.index("\n}", i) + 2
    return PAGE[i:j]


def run(extra: str, body: str = None) -> dict:
    if body is None:
        body = PAGE[PAGE.index(FIRST):PAGE.index(LAST)]
    js = SHIM + body + "\n" + extra
    done = subprocess.run([NODE, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, "the page threw:\n%s" % done.stderr
    return json.loads(done.stdout)


def cells(extra: str) -> dict:
    """Everything from the chrome crop down to the end of `screenFor`."""
    body = (PAGE[PAGE.index(FIRST):PAGE.index(LAST)]
            + PAGE[PAGE.index(CELLS_FIRST):PAGE.index(CELLS_LAST)])
    done = subprocess.run([NODE, "-e", SHIM + body + "\n" + extra],
                          capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert done.returncode == 0, "the page threw:\n%s" % done.stderr
    return json.loads(done.stdout)


def test_the_frame_takes_the_shape_of_the_window_it_shows():
    """⛔ THE FRAME IS THE PICTURE, NOT THE CELL. Two numbers do it: the crop,
    as a fraction of the picture's WIDTH because that is what a percentage
    margin resolves against, and the shape that is left after cropping. Both
    are set once per shape, so nothing is measured and nothing is recomputed on
    resize - the version before this one read the box on every frame.

    Known-bad, three: drop the crop, express it against the height instead of
    the width, or forget the ratio and leave every frame at 16:10 - which is
    the state this pane was in when a 4:3 window drew inside a 16:10 box.
    """
    shots = run("""
      const out = [];
      for(const [w, h] of [[1280,688],[1024,768],[1440,812],[800,600]]){
        const box = el('div','frame'), cell = el('div','screen');
        cell.appendChild(box);
        shapeFrom(cell, {naturalWidth: w, naturalHeight: h});
        out.push({w, h, arn: Number(box.style.getPropertyValue('--arn')),
                  cut: Number(box.style.getPropertyValue('--cut').replace('%','')),
                  shape: cell.dataset.shape});
      }
      process.stdout.write(JSON.stringify(out));
    """)
    for s in shots:
        w, h = s["w"], s["h"]
        seen = h * (1 - 0.083)
        assert abs(s["arn"] - w / seen) < 0.001, (
            "a %dx%d window is framed at %.3f, and cropped of its chrome it is "
            "%.3f wide for every one tall" % (w, h, s["arn"], w / seen))
        # The crop is a share of the HEIGHT, and a percentage margin resolves
        # against the WIDTH: the conversion is the whole point of the number.
        assert abs(s["cut"] - 0.083 * h / w * 100) < 0.01, (
            "%dx%d is cropped by %.2f%% of its width" % (w, h, s["cut"]))
        assert s["shape"] == "%dx%d" % (w, h), "the shape is not remembered"


def test_the_four_states_are_four_different_pictures():
    """⛔ THE DEFECT THIS FILE EXISTS FOR. Waiting, no tab, stopped and failed
    are four different facts, and a pane that draws them the same way is a pane
    that says nothing four times. The one that matters most is `error`: it
    carries the server's own sentence, on the screen, where the version before
    this one put it in a `title` attribute nobody hovers.

    Known-bad: make `setState` hide the veil for anything but `live`, or drop
    the detail line and leave the reason unsaid.
    """
    got = run("""
      const out = {};
      for(const [state, title, detail] of [['live','',''],
                                           ['waiting','waiting for the first frame',''],
                                           ['nopage','no tab open','ask the agent to open a page here'],
                                           ['error','the capture failed','no frame within 5s'],
                                           ['stale','','']]){
        const cell = el('div','screen');
        const box = el('div','frame'); box.appendChild(el('div','veil'));
        cell.appendChild(box);
        setState(cell, state, title, detail);
        const veil = cell.querySelector('.veil');
        out[state] = {state: cell.dataset.state, hidden: veil.hidden,
                      text: veil.textContent,
                      kids: veil.kids.map(k => k.className || k.tag)};
      }
      process.stdout.write(JSON.stringify(out));
    """)
    assert got["live"]["hidden"] is True, "a live screen still paints something over itself"
    seen = {}
    for name in ("waiting", "nopage", "error", "stale"):
        assert got[name]["hidden"] is False, "%s draws nothing over the picture" % name
        assert got[name]["state"] == name, "the state is not written on the cell"
        seen[name] = got[name]["text"] + "|" + ",".join(got[name]["kids"])
    assert len(set(seen.values())) == 4, (
        "two states draw the same thing, which is the defect this test exists "
        "for: %s" % seen)
    assert "pulse" in got["waiting"]["kids"], (
        "nothing says the pane is still trying, which is the only difference "
        "between waiting and stopped")
    assert "no frame within 5s" in got["error"]["text"], (
        "the reason the capture failed is not on the screen")
    assert got["stale"]["text"] == "", (
        "the stale scrim writes over the last picture instead of dimming it - "
        "that picture is the only evidence the pane has")


def test_a_screen_says_how_old_its_picture_is():
    """⛔ STALE HAS TO LOOK STALE. On a healthy stage every screen is refreshed
    every 40 to 100 ms, so a picture older than a couple of seconds means that
    browser has stopped answering - and the last frame is still sitting there
    looking alive. A control room's first rule, and a dashboard's fifth state
    after empty, loading, error and partial.

    Known-bad, two: drop the stamp, or stop moving the cell into `stale` when
    the number appears, which leaves a dimmed-looking pane with a red number
    and no reason.
    """
    got = run("""
      const mk = (agoMs) => { const cell = el('div','screen');
        const box = el('div','frame');
        box.appendChild(el('div','veil')); box.appendChild(el('span','stamp'));
        cell.appendChild(box);
        cell.dataset.state = 'live';
        // The same clock the page reads: monotonic, not the wall.
        cell.dataset.at = String(Math.round(performance.now()) - agoMs);
        return cell; };
      const fresh = mk(300), old = mk(4200);
      ageAll([fresh, old]);
      process.stdout.write(JSON.stringify({
        fresh: {stamp: fresh.querySelector('.stamp').textContent,
                hidden: fresh.querySelector('.stamp').hidden, state: fresh.dataset.state},
        old: {stamp: old.querySelector('.stamp').textContent,
              hidden: old.querySelector('.stamp').hidden, state: old.dataset.state}}));
    """)
    assert got["fresh"]["hidden"] is True and got["fresh"]["stamp"] == "", \
        "a screen that just got a picture is stamped as old"
    assert got["old"]["hidden"] is False and got["old"]["stamp"] == "4s", \
        "a screen with a four second old picture says %r" % got["old"]["stamp"]
    assert got["old"]["state"] == "stale", \
        "the picture is stamped old but the screen still reads as live"


def test_a_screen_is_built_as_a_frame_with_its_name_on_it():
    """The name used to be a 28px bar bolted under the card, which put the
    label of a thing outside the thing and cost a row of height in every cell
    of a 2x2. It rides on the picture now, with the dot that says the agent is
    working here beside it.

    Known-bad: go back to a caption element outside the frame.
    """
    got = cells("""
      const cell = screenFor({id: 'b-two', running: true, urls: ['http://x/']}, true);
      const empty = screenFor({id: 'b-three', running: true, urls: []}, false);
      process.stdout.write(JSON.stringify({one: tree(cell), none: tree(empty)}));
    """)
    frame = got["one"]["kids"][0]
    assert frame["cls"] == "frame", "the screen no longer holds a frame"
    inside = [k["cls"] or k["tag"] for k in frame["kids"]]
    assert inside == ["img", "veil", "tag", "stamp"], \
        "the frame holds %s" % inside
    assert got["one"]["data"]["state"] == "waiting", \
        "a screen with a page starts in %r" % got["one"]["data"]["state"]
    assert got["none"]["data"]["state"] == "nopage" and got["none"]["data"]["blank"] == "1", \
        "a browser with no tab is asked for a picture anyway"
    tag = frame["kids"][2]
    assert [k["cls"] for k in tag["kids"]] == ["id", "dot"], \
        "the name on the picture lost the mark that says the agent is here"


def test_a_browser_with_no_picture_is_a_name_and_not_a_picture_frame():
    """⛔ SIX STOPPED BROWSERS DREW SIX EMPTY PICTURE FRAMES. 168 by 133 each,
    the words `not up` in the middle, 133px of the pane spent on a gallery of
    things that are not there. A thing with no image is a name, and a name is a
    chip.

    Known-bad: give a stopped browser a `.thumb` again.
    """
    got = run("""
      const stopped = thumbFor({id: 'b-off', running: false, urls: []});
      const running = thumbFor({id: 'b-two', running: true, urls: ['http://x/']});
      process.stdout.write(JSON.stringify({stopped: tree(stopped), running: tree(running)}));
    """, one("thumbFor"))
    assert got["stopped"]["cls"] == "chip", \
        "a stopped browser is drawn as %r" % got["stopped"]["cls"]
    assert got["stopped"]["kids"][1]["text"] == "b-off", "the chip does not carry the name"
    assert got["running"]["cls"] == "thumb", "a running browser lost its preview"
    assert got["running"]["kids"][0]["kids"][0]["tag"] == "img", \
        "a running browser with a page is not given somewhere to draw it"


def test_an_empty_stage_says_what_to_do_about_being_empty():
    """There is no button that opens a browser - they are opened by asking, on
    purpose - so the empty stage is the one place that has to say so, and to
    show the shape of the sentence that does it.

    Known-bad: go back to naming the condition and stopping.
    """
    code = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    assert "el('div','empty')" in code, "the empty stage is a screen with no picture again"
    assert "Ask in the chat and one opens here" in PAGE, \
        "the empty stage no longer says how a browser gets opened"
    assert "open a browser and go to example.com" in PAGE, \
        "the empty stage says to ask but not what asking looks like"
