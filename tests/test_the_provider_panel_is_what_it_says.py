"""The provider panel, executed: what it draws and what it releases.

The rules here are the ones a text scan cannot check, because they are about
what happens between two clicks rather than about what the file says. They are
run through `node` against the real source of `ui/js/11-provider.js` and
`ui/js/12-signin.js`, with the
handful of globals it reaches for stood in for - the same way the rest of this
suite drives the page.

Three of them come from defects this project has recorded in other files and
would have again here:

* **`pagehide` and the back-forward cache.** A page restored from the bfcache
  keeps its DOM and has lost whatever was in the air. A generation-guarded
  `finally` deliberately refuses to touch an attempt it no longer owns, so the
  restored page stays busy for ever unless the handler clears the state itself,
  synchronously, before the cancellation is sent.
* **A late answer landing on a newer sign-in.** The route refuses it with a 409
  and does not write the credential; the page must then draw the refusal rather
  than the success it was hoping for.
* **A model list that is not the server's.** The control is filled from an
  answer and from nothing else, and a refused model leaves the control empty
  rather than showing the id that was refused.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from aihawk import ui

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="needs node to EXECUTE the page")

PANEL = (ui._read("js", "11-provider.js") + ui._read("js", "12-modellist.js")
         + ui._read("js", "13-signin.js"))


def run(js: str):
    done = subprocess.run([NODE, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def whole(start: str, end: str = chr(10) + "}") -> str:
    """One top-level function, as it is written in the file."""
    src = PANEL[PANEL.index(start):]
    return src[:src.index(end) + len(end)]


#: The declarations the functions below close over. Taken from the file rather
#: than retyped, so a change to an initial value is a change this harness sees.
DECLS = PANEL[:PANEL.index("/* The card is built once")]

#: ⛔ THE REAL `drawProvider` RUNS IN THESE TESTS, with a wrapper in front of it
#: that records the call. A stub would make the assertions about what the control
#: holds meaningless - the thing under test is what that function writes.
SPY = whole("function drawProvider(state){") + """
const _realDraw = drawProvider;
drawProvider = function(state){ DRAWN.push(state); return _realDraw(state); };
"""

#: ⛔ THE ONE PLACE THE SIGN-IN GOES BACK TO REST, AND `pagehide` CALLS IT.
#: `clearSignIn` is written in terms of it, so the harness has to carry both or
#: the assembled script has a name with nothing behind it.
REST = whole("function signInDone(){") + "\n" + whole("function clearSignIn(){")

#: The model listbox, assembled the same way and for the same reason: the panel
#: draws the options, the list file moves a cursor over them, and the assertions
#: below are about both halves of one control.
LIST = ui._read("js", "12-modellist.js")

#: A DOM small enough to be obviously not one: an object per id, recording what
#: was written to it. The point is to observe the calls, not to render.
DOM = """
const ELS = {};
function box(extra){
  return Object.assign({hidden:false, disabled:false, textContent:'', value:'',
                        dataset:{}, attrs:{}, calls:[], children:[], inert:false,
                        setAttribute(k,v){ this.attrs[k]=v; },
                        removeAttribute(){}, focus(){}, scrollIntoView(){},
                        appendChild(c){ this.children.push(c); },
                        removeChild(c){ this.children = this.children.filter(k => k !== c); },
                        querySelector(){ return null; }, querySelectorAll(){ return []; }},
                       extra || {});
}
function get(id){ if(!ELS[id]) ELS[id] = box(); return ELS[id]; }
const $ = (id) => get(id);
globalThis.$ = $;
function el(tag, cls, text){ return box({tag, className: cls, textContent: text || ''}); }
globalThis.el = el;
globalThis.window = {addEventListener(){}, open(){}};
const SAID = [];
function providerSay(word, bad, good){
  SAID.push({word: word||'', bad: !!bad, good: !!good});
  get('provsay').textContent = word || '';
}
globalThis.providerSay = providerSay;
const DOORS = [];
function door(path, init){ DOORS.push({path, init}); return Promise.resolve({ok:true}); }
globalThis.door = door;
async function ask(path, body, whatFailed){
  DOORS.push({path, body, whatFailed});
  return ANSWERS[path] || null;
}
globalThis.ask = ask;
const DRAWN = [];
globalThis.DRAWN = DRAWN;
const ANSWERS = {};
globalThis.ANSWERS = ANSWERS;
/* ⛔ THE LIST'S ROWS, READ THE WAY THE CONTROL BUILDS THEM. A row is a button
   carrying the model id in its text and in `dataset.model`, so both are
   reported: an option whose id was written somewhere other than the row that
   shows it is a control that sends a different model than it names. */
const rows = (id) => get(id).children.map(c => ({id: c.textContent,
                                                value: c.dataset.model,
                                                picked: c.attrs['aria-selected'],
                                                here: c.dataset.here}));
const out = () => JSON.stringify({said: SAID, doors: DOORS, drawn: DRAWN,
                                  rows: rows('provlist'),
                                  els: Object.fromEntries(Object.entries(ELS).map(
                                    ([k,v]) => [k, {textContent:v.textContent, hidden:v.hidden,
                                                    disabled:v.disabled, value:v.value,
                                                    attrs:v.attrs, inert:v.inert}]))});
""" + LIST


def test_the_pagehide_handler_clears_the_busy_state_synchronously_and_cancels():
    """⛔ THE BACK-FORWARD CACHE, WHICH IS THE ONE PATH A GUARDED `finally`
    CANNOT COVER. The page is put away mid-sign-in and restored with the DOM it
    was frozen with; if the handler does not clear the busy flag and the hint
    itself, the restored page is busy for ever with a Cancel button that does
    nothing.

    Known-bad: rely on the request's `finally`, which correctly refuses to touch
    an attempt it no longer owns.
    """
    js = DECLS + DOM + REST + whole("function providerPageHide(){") + """
signInBusy = true;
signInAttempt = 7;
get('provconnect').disabled = true;
get('provcancel').hidden = false;
get('provmanual').hidden = false;
providerPageHide();
process.stdout.write(out());
"""
    got = run(js)
    assert got["els"]["provconnect"]["disabled"] is False, "the Connect button stays dead"
    assert got["els"]["provcancel"]["hidden"] is True, "the Cancel button stays on screen"
    assert got["els"]["provmanual"]["hidden"] is True
    assert got["els"]["provsay"]["textContent"] == ""
    # And the server is told, so the listener it holds is released.
    cancelled = [d for d in got["doors"] if d["path"] == "/provider/cancel"]
    assert len(cancelled) == 1
    assert json.loads(cancelled[0]["init"]["body"]) == {"attempt": 7}
    assert cancelled[0]["init"]["keepalive"] is True, (
        "the cancellation will not outlive the page it was sent from")


def test_pagehide_with_nothing_in_flight_cancels_nothing():
    """Known-bad: cancel unconditionally, which releases whatever attempt
    another tab is in the middle of."""
    js = DECLS + DOM + REST + whole("function providerPageHide(){") + """
providerPageHide();
process.stdout.write(out());
"""
    got = run(js)
    assert [d for d in got["doors"] if d["path"] == "/provider/cancel"] == []


def test_a_second_sign_in_can_start_after_pagehide_without_a_remount():
    """⛔ THE SHAPE THE bfcache DEFECT ACTUALLY HAS. Clear the state and the
    second attempt works; guard it wrongly and the second attempt inherits the
    first one's attempt number, so the server refuses its code as superseded.

    Known-bad: clear the UI but leave `signInAttempt` pointing at the abandoned
    attempt.
    """
    js = DECLS + DOM + REST + whole("function providerPageHide(){") + "\n" + SPY + \
        whole("async function connectProvider(){") + """
globalThis.connectProvider = connectProvider;
signInBusy = true;
signInAttempt = 7;
providerPageHide();
ANSWERS['/provider/connect'] = {json: async () => ({attempt: 9, url: 'https://www.orcarouter.ai/auth?x=1',
                                                    callback: 'http://127.0.0.1:1/callback'})};
ANSWERS['/provider/login'] = {json: async () => ({provider: 'orcarouter-oauth', model: 'orcarouter/auto',
                                                  credential: {set: true, masked: 'sk-orca-...CANARY',
                                                               method: 'pkce', needs_reauth: false},
                                                  models: [], source: 'seed'})};
connectProvider().then(() => {
  const starts = DOORS.filter(d => d.path === '/provider/connect');
  const logins = DOORS.filter(d => d.path === '/provider/login');
  process.stdout.write(JSON.stringify({starts: starts.length, logins: logins.length,
                                       attempt: logins[0] ? logins[0].body.attempt : null,
                                       disabled: get('provconnect').disabled,
                                       cancelHidden: get('provcancel').hidden}));
});
"""
    got = run(js)
    assert got["starts"] == 1
    assert got["logins"] == 1
    assert got["attempt"] == 9, "the second sign-in reused the abandoned attempt number"
    assert got["disabled"] is False, "the second sign-in left the button dead"
    assert got["cancelHidden"] is True, "the second sign-in left a stale Cancel button"


def test_a_superseded_attempt_draws_the_refusal_and_not_a_success():
    """⛔ THE LATE SUCCESS THAT MUST NOT LAND. The server refuses it with a 409
    and does not write the credential; the page must show the refusal rather
    than the state it hoped for, or the screen says signed in while the process
    holds nothing.

    Known-bad: read `error` as absent and draw the answer anyway.
    """
    js = DECLS + DOM + whole("async function submitProviderCode(){") + """
globalThis.submitProviderCode = submitProviderCode;
signInAttempt = 3;
get('provcode').value = 'code-CANARY';
ANSWERS['/provider/login'] = {json: async () => ({error: 'a newer sign-in replaced this one'})};
submitProviderCode().then(() => {
  process.stdout.write(JSON.stringify({drawn: DRAWN.length,
                                       said: SAID.map(s => s.word).join(' | '),
                                       field: get('provcode').value}));
});
"""
    got = run(js)
    assert got["drawn"] == 0, "a refused sign-in was drawn as the current state"
    assert "newer sign-in" in got["said"]
    assert got["field"] == "", "the pasted code was left in the field"


def test_the_model_control_is_filled_from_the_answer_and_never_from_free_text():
    """⛔ THE HARD REQUIREMENT FOR THIS PANEL: a list, from the server. A text
    box a model id could be typed into is a request that fails at the first
    turn with the reason nowhere near the cause.

    ⛔ AND THE LIST IS A THING ON SCREEN. The rows are the panel's own elements
    in a listbox, not the open state of a native `<select>`, which the operating
    system draws outside the document - so the options below are read out of the
    list the page built, which is also what a person and a photograph see.
    """
    js = DECLS + DOM + SPY + """
drawProvider({provider: 'orcarouter', model: 'deepseek/deepseek-v4-pro',
              credential: {set: true, masked: 'sk-orca-...CANARY', method: 'pkce',
                           needs_reauth: false},
              source: 'live',
              models: [{id: 'orcarouter/auto', endpoints: ['openai'], modalities: []},
                       {id: 'deepseek/deepseek-v4-pro', endpoints: ['openai'], modalities: []}]});
process.stdout.write(JSON.stringify({options: rows('provlist').map(r => r.value),
                                     value: get('provmodel').dataset.chosen,
                                     trigger: get('provchosen').textContent,
                                     src: get('provsrc').textContent,
                                     masked: get('provmasked').textContent,
                                     badge: get('model').textContent}));
"""
    got = run(js)
    assert got["options"] == ["orcarouter/auto", "deepseek/deepseek-v4-pro"]
    assert got["value"] == "deepseek/deepseek-v4-pro"
    assert got["trigger"] == "deepseek/deepseek-v4-pro"
    assert "2 models" in got["src"]
    assert got["masked"] == "sk-orca-...CANARY"
    assert got["badge"] == "deepseek/deepseek-v4-pro"
    # ⛔ AND NO TEXT BOX. The whole module is checked, not just this function.
    assert "input" in PANEL, "the key field is gone"
    assert "type = 'password'" in PANEL
    assert "list.appendChild(modelRow(id, chosen, n === providerPick))" in PANEL
    # And the control itself is not a select, so nothing can be typed into it.
    # The prose above it names the thing it is not, so the check is over the
    # code with the comments taken out.
    code = re.sub(r"/\*.*?\*/", "", PANEL, flags=re.S)
    assert "el('select')" not in code and "<select" not in code


def test_the_list_expands_and_the_open_rows_are_the_ones_that_were_sent():
    """⛔ THE OPEN STATE IS ON SCREEN. Known-bad: leave the list hidden and let
    the control's value be the only thing that says what is in it."""
    js = DECLS + DOM + SPY + """
drawProvider({provider: 'orcarouter', model: 'orcarouter/auto',
              credential: {set: true, masked: 'sk-orca-...CANARY', needs_reauth: false},
              source: 'live',
              models: [{id: 'orcarouter/auto', endpoints: ['openai'], modalities: []},
                       {id: 'deepseek/deepseek-v4-pro', endpoints: ['openai'], modalities: []}]});
const closed = {hidden: get('provlist').hidden,
                expanded: get('provmodel').attrs['aria-expanded'],
                count: rows('provlist').length};
toggleProviderModels();
const opened = {hidden: get('provlist').hidden,
                expanded: get('provmodel').attrs['aria-expanded'],
                count: rows('provlist').length,
                picked: rows('provlist').map(r => r.picked),
                here: rows('provlist').map(r => r.here)};
process.stdout.write(JSON.stringify({closed, opened}));
"""
    got = run(js)
    assert got["closed"] == {"hidden": True, "expanded": "false", "count": 2}
    assert got["opened"]["hidden"] is False
    assert got["opened"]["expanded"] == "true"
    assert got["opened"]["count"] == 2
    assert got["opened"]["picked"] == ["true", "false"], (
        "the list does not say which row is the model in use")
    assert got["opened"]["here"] == ["1", None], (
        "the cursor does not start on the model in use")


def test_the_arrows_move_the_cursor_and_enter_commits_it():
    """⛔ THE KEYBOARD IS PART OF THE CONTROL. It replaced a native select, which
    is expandable and committable without a mouse; a listbox that only answered
    clicks would be a control this page took away from the keyboard."""
    js = DECLS + DOM + SPY + whole("async function chooseProviderModel(wanted){") + """
globalThis.chooseProviderModel = chooseProviderModel;
drawProvider({provider: 'orcarouter', model: 'orcarouter/auto',
              credential: {set: true, masked: 'sk-orca-...CANARY', needs_reauth: false},
              source: 'live',
              models: [{id: 'orcarouter/auto', endpoints: ['openai'], modalities: []},
                       {id: 'deepseek/deepseek-v4-pro', endpoints: ['openai'], modalities: []}]});
const stop = () => ({stopped: false});
providerModelKey({key: 'ArrowDown', preventDefault(){}, ...stop()});
const first = rows('provlist').map(r => r.here);
providerModelKey({key: 'ArrowDown', preventDefault(){}, ...stop()});
const second = rows('provlist').map(r => r.here);
ANSWERS['/provider/choose'] = {json: async () => ({provider: 'orcarouter',
  model: 'deepseek/deepseek-v4-pro', refused: false,
  credential: {set: true, masked: 'sk-orca-...CANARY', needs_reauth: false},
  source: 'live', models: [{id: 'orcarouter/auto', endpoints: [], modalities: []},
                           {id: 'deepseek/deepseek-v4-pro', endpoints: [], modalities: []}]})};
providerModelKey({key: 'Enter', preventDefault(){}, ...stop()});
setTimeout(() => {
  const chooses = DOORS.filter(d => d.path === '/provider/choose');
  process.stdout.write(JSON.stringify({first, second,
    chosen: chooses.length ? chooses[0].body.model : null,
    hidden: get('provlist').hidden}));
}, 0);
"""
    got = run(js)
    assert got["first"] == ["1", None], "ArrowDown did not open the list on the first press"
    assert got["second"] == [None, "1"], "ArrowDown did not move the cursor"
    assert got["chosen"] == "deepseek/deepseek-v4-pro", (
        "Enter committed something other than the row under the cursor")
    assert got["hidden"] is True, "the list stayed open after a choice was made"


def test_escape_closes_the_list_and_not_the_card_behind_it():
    """⛔ THE INNERMOST THING THAT OWNS A KEY GETS IT. The sessions panel answers
    Escape by closing itself, one level out; while the list is open the key
    belongs to the list, or the key somebody presses to put a list away closes
    the whole panel under them."""
    js = DECLS + DOM + SPY + """
drawProvider({provider: 'orcarouter', model: 'orcarouter/auto',
              credential: {set: true, masked: 'sk-orca-...CANARY', needs_reauth: false},
              source: 'live',
              models: [{id: 'orcarouter/auto', endpoints: ['openai'], modalities: []}]});
toggleProviderModels();
let stopped = false;
providerModelKey({key: 'Escape', stopPropagation(){ stopped = true; }});
process.stdout.write(JSON.stringify({stopped, hidden: get('provlist').hidden,
                                     expanded: get('provmodel').attrs['aria-expanded']}));
"""
    got = run(js)
    assert got["stopped"] is True, "Escape was left to bubble to the card behind"
    assert got["hidden"] is True
    assert got["expanded"] == "false"


def test_a_seed_catalogue_says_so_and_an_empty_live_one_does_not_lie():
    """⛔ A SEED PRESENTED AS THE ACCOUNT'S OWN CATALOGUE IS A CLAIM NOBODY
    VERIFIED. Known-bad: draw the same sentence for both sources."""
    js = DECLS + DOM + SPY + """
drawProvider({provider: 'orcarouter', model: '', credential: {set: false, masked: '',
              method: '', needs_reauth: false}, source: 'seed',
              catalog_error: 'the model catalogue answered 503',
              models: [{id: 'orcarouter/auto', endpoints: ['openai'], modalities: []}]});
const seed = {src: get('provsrc').textContent, trigger: get('provchosen').textContent,
              options: rows('provlist').map(r => r.value)};
drawProvider({provider: 'orcarouter', model: '', credential: {set: false, masked: '',
              method: '', needs_reauth: false}, source: 'live', models: []});
process.stdout.write(JSON.stringify({seed, live: get('provsrc').textContent,
                                     empty: rows('provlist').length,
                                     trigger: get('provchosen').textContent}));
"""
    got = run(js)
    assert "verified short list" in got["seed"]["src"]
    assert "503" in got["seed"]["src"]
    assert got["seed"]["options"] == ["orcarouter/auto"]
    assert "verified" not in got["live"]
    assert got["empty"] == 0, "an empty catalogue drew a row anyway"
    assert got["trigger"] == "No model list yet"


def test_a_refused_model_is_drawn_as_empty_rather_than_as_chosen():
    """⛔ THE SERVER IS THE ONE THAT KNOWS whether the model is still in the
    compatible list. Known-bad: write the choice locally and hope."""
    js = DECLS + DOM + SPY + whole("async function chooseProviderModel(wanted){") + """
globalThis.chooseProviderModel = chooseProviderModel;
providerState = {provider: 'orcarouter'};
ANSWERS['/provider/choose'] = {json: async () => ({
  provider: 'orcarouter', model: '', refused: true,
  note: "That model is not in this provider's list, so it was not selected.",
  credential: {set: true, masked: 'sk-orca-...CANARY', needs_reauth: false},
  source: 'live', models: [{id: 'text/here', endpoints: ['openai'], modalities: []}]})};
chooseProviderModel('text/gone').then(() => {
  process.stdout.write(JSON.stringify({value: get('provmodel').dataset.chosen,
                                       trigger: get('provchosen').textContent,
                                       said: SAID.map(s => s.word).join(' | '),
                                       bad: SAID.map(s => s.bad)}));
});
"""
    got = run(js)
    assert got["value"] == "", "a refused model was left as the chosen one"
    assert got["trigger"] == "Choose a model"
    assert "not in this provider's list" in got["said"]
    assert True in got["bad"]


def test_the_key_field_is_emptied_before_the_answer_is_read():
    """⛔ A KEY LEFT IN A FIELD IS A KEY IN A SCREENSHOT, a screen-share and
    whatever the browser restores after a crash. Known-bad: clear it only on
    the success path."""
    js = DECLS + DOM + whole("async function saveProviderKey(){") + """
globalThis.saveProviderKey = saveProviderKey;
get('provinput').value = 'sk-orca-CANARY';
ANSWERS['/provider/key'] = {json: async () => ({error: 'no'})};
saveProviderKey().then(() => process.stdout.write(JSON.stringify({
  field: get('provinput').value})));
"""
    got = run(js)
    assert got["field"] == ""


def test_the_panel_carries_no_key_into_the_document_or_a_status_line():
    """⛔ THE PAGE IS A BROWSER. The module may SEND a key and may show a mask;
    it may never write a key into the document, a status sentence or the
    transcript.

    Known-bad: `providerSay('Saved ' + key)`.
    """
    assert "credential.masked" in PANEL
    # The key is read from the field, sent, and the field is emptied; there is
    # no path that puts the value anywhere else.
    assert PANEL.count("field.value") == 4, (
        "the two key fields are read somewhere other than the places that send "
        "them, or a new one appeared: %d" % PANEL.count("field.value"))
    # The value is used to build one request body and to test for emptiness.
    # Nothing concatenates it into a sentence.
    assert "providerSay(given" not in PANEL
    assert "+ given" not in PANEL and "given +" not in PANEL
    assert "providerSay('Saved ' +" not in PANEL
