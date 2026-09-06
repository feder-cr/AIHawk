"""The two-pane interface: conversation on the left, the live browser on the right.

This used to live inside the MCP server and reach the browser through a Python
object in the same process. It lives here now, and it reaches the browser the way
everybody else does: over MCP, calling the same tools any agent gets.
The server went back to being only a server.

That is not a tidier arrangement of the same code, it changes what is true about
each side. The MCP package now has no opinion about being looked at, so nothing
in it has to be kept working for the sake of a page. And this interface has no
privileged access, so anything it can do, somebody else's client can also do -
which is the strongest guarantee available that the tools are sufficient.

Three consequences, each handled rather than hidden:

  The live view cannot ask "is a browser running" without starting one, because
  `session_list_pages` calls `ensure`. `Link` remembers whether an instruction
  has been issued and the view stays quiet until then.

  Screenshots and actions now share one pipe. They are serialised in `Link`, and
  they would have been serialised by the browser anyway.

  The page URL is no longer free. It is fetched on its own slower timer rather
  than with every frame, so watching costs one cheap call every two seconds.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Dict, List, Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from .brain import Brain
from .link import Link, image_of

# A RAW string. The script below contains \n, \w and \s inside JavaScript
# literals and regular expressions; in an ordinary triple-quoted string Python
# would turn `'\n'` into a real newline before the browser ever saw it, and the
# regex would quietly mean something else. Same family as the rule about
# backslashes through a shell heredoc: nothing errors, the text is just no
# longer the text that was written.
PAGE = r"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AIHawk</title>
<style>
:root{
  color-scheme: dark;

  /* Surfaces as a ladder rather than two greys. The steps widen going up
     (5,7,7,8) because equal hex steps read as progressively smaller the lighter
     they get. */
  --well:   #0b0d10;   /* recessed: behind the screenshot, the deepest thing here */
  --base:   #101317;   /* the ground */
  --raised: #171b21;   /* composer, header, browser chrome, expanded output */
  --hover:  #1e232a;   /* row hover, and the user's own bubble */
  --top:    #262c34;   /* a control sitting on --hover */

  /* Edges are translucent white, never a hex: rgba composites correctly on
     every rung, so a component can move up the ladder without its border being
     picked again. */
  --line-1: rgba(255,255,255,.06);
  --line-2: rgba(255,255,255,.09);
  --line-3: rgba(255,255,255,.14);
  --lip:    inset 0 1px 0 rgba(255,255,255,.045);

  /* Ink, with the contrast each one carries against --base. */
  --fg:   #e8ebed;   /* 15.0:1  what the user typed, what the model answered */
  --fg-2: #a8b1b9;   /*  8.7:1  narration and chrome labels */
  --fg-3: #78828a;   /*  4.8:1  tool output and arguments */
  --fg-4: #4a545c;   /*  2.2:1  step numbers and placeholder: decorative only */

  --accent:    #e38a5d;
  --on-accent: #101317;
  --ok:  #6cc08b;
  --err: #e8836b;

  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, "Cascadia Mono", "SF Mono", Menlo, Consolas,
          "Liberation Mono", "DejaVu Sans Mono", monospace;
  --t-label:11px; --t-mono:13px; --t-ui:13px; --t-body:14px;

  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:20px; --s6:32px;
  --r-sm:4px; --r:8px; --r-lg:12px; --r-pill:999px;
  --gutter:1.75rem;                            /* three digits of 11px mono */
  --gap:.55rem;
  --indent:calc(var(--gutter) + var(--gap));   /* ONE source for the step indent */
}

*{ box-sizing:border-box }
body{ margin:0; height:100vh; display:flex; background:var(--base); color:var(--fg);
      font:var(--t-body)/1.55 var(--sans); }
code,pre,.g,.meta,.badge,#url,#tok{
  font-family:var(--mono);
  /* Not cosmetic: a step reads `#email <- ada@example.com`, and a mono face with
     contextual alternates draws `<-` as one arrow. The text on screen would stop
     being the text the model emitted. */
  font-variant-ligatures:none; }
.meta,.g,#tok{ font-variant-numeric:tabular-nums }
.label{ font-size:var(--t-label); font-weight:600; letter-spacing:.07em;
        text-transform:uppercase; color:var(--fg-4); line-height:1 }
.sr{ position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%) }
/* `hidden` must beat any display an id or class sets, or an element the script
   believes it has hidden stays on screen. This shipped once on the live image
   and again on the queued-message chip: both were "hidden" and both were
   visible, because a rule with an id selector outranks the user agent's
   [hidden]. One line, and the whole class is gone. */
[hidden]{ display:none !important }

/* ---------------- panes ---------------- */
#left { width:44%; min-width:380px; display:flex; flex-direction:column;
        position:relative; border-right:1px solid var(--line-1) }
#right{ flex:1; min-width:0; display:flex; flex-direction:column; background:var(--well) }
#head { display:flex; align-items:center; gap:10px; padding:var(--s3) var(--s4);
        border-bottom:1px solid var(--line-1) }
#head b{ font-size:var(--t-ui); font-weight:600 }
.badge{ margin-left:auto; font-size:var(--t-label); color:var(--fg-2);
        background:var(--raised); border:1px solid var(--line-2);
        padding:3px 9px; border-radius:var(--r-pill) }

#log{ flex:1; overflow:auto; padding:var(--s5) var(--s4); scrollbar-gutter:stable }
#thread{ max-width:680px; margin:0 auto }   /* cap the measure; prose does not stretch */

/* Bottom-pinning with no scroll handler and no epsilon: the sentinel is the only
   anchor the browser may keep, so content inserted before it pushes the view
   down, and a reader who has scrolled up is left alone because an anchor off
   screen is not chosen. */
#log > *{ overflow-anchor:none }
#anchor{ height:1px; overflow-anchor:auto }

#hint{ color:var(--fg-3); max-width:46ch; margin:var(--s6) auto 0; text-align:center }
#hint p{ margin:0 0 var(--s4) }
#hint .eg{ font:var(--t-mono)/1.9 var(--mono); color:var(--fg-2);
           background:var(--raised); border:1px solid var(--line-1);
           border-radius:var(--r); padding:var(--s3) var(--s4); text-align:left }
#hint .sm{ font-size:12px; color:var(--fg-4) }

#jump{ position:absolute; bottom:110px; left:50%; transform:translateX(-50%); z-index:2;
       background:var(--top); border:1px solid var(--line-2); color:var(--fg);
       font:var(--t-ui)/1 var(--sans); padding:7px 13px;
       border-radius:var(--r-pill); cursor:pointer }

/* ---------------- one turn ---------------- */
.turn + .turn{ margin-top:var(--s6) }   /* between turns */
.turn > * + *{ margin-top:var(--s3) }   /* inside a turn */
.ev + .ev    { margin-top:var(--s1) }   /* between steps: a continuation */

.you{ margin-left:auto; width:fit-content; max-width:88%;
      background:var(--hover); border:1px solid var(--line-1);
      border-radius:var(--r-lg) var(--r-lg) var(--r-sm) var(--r-lg);
      padding:9px 13px; white-space:pre-wrap; overflow-wrap:anywhere }
.say   { color:var(--fg-2); white-space:pre-wrap; padding-left:var(--indent) }
.answer{ color:var(--fg);   white-space:pre-wrap; padding-left:var(--indent) }
.orph  { display:flex; gap:8px; font-size:var(--t-mono); color:var(--err);
         background:rgba(232,131,107,.08); border-radius:var(--r-sm);
         box-shadow:inset 2px 0 0 var(--err); padding:6px 10px }

/* ONE grid: every row on the same rails, so nothing shifts as text changes. */
.row{ display:grid; grid-template-columns:var(--gutter) minmax(0,1fr) auto 1rem;
      column-gap:var(--gap); align-items:baseline; padding:3px 6px;
      list-style:none; cursor:pointer; user-select:none; border-radius:var(--r-sm);
      transition:background-color 120ms ease-out }
.row::-webkit-details-marker{ display:none }
.row:hover{ background:var(--raised) }
.g   { grid-column:1; justify-self:end; font-size:var(--t-label); color:var(--fg-4) }
.lab { grid-column:2; min-width:0; overflow:hidden; text-overflow:ellipsis;
       white-space:nowrap; font-size:var(--t-mono) }
.lab b   { font-family:var(--sans); font-weight:600; color:var(--fg) }  /* the verb */
.lab code{ color:var(--accent) }                                        /* the object */
.lab .inline{ color:var(--fg-3) }                    /* a short result, on the row */
.meta{ grid-column:3; white-space:nowrap; font-size:var(--t-label); color:var(--fg-4) }

/* The chevron is the row's own pseudo-element in its own track: no svg, no icon
   font, and it cannot shift the label when it turns. */
.row::after{ content:""; grid-column:4; justify-self:end; align-self:center;
             width:5px; height:5px; margin-top:-2px;
             border-right:1.5px solid var(--fg-4); border-bottom:1.5px solid var(--fg-4);
             transform:rotate(-45deg); transition:transform 150ms ease }
.ev[open] > .row::after{ transform:rotate(45deg); margin-top:-4px }
.ev[data-body="none"] > .row{ cursor:default }
.ev[data-body="none"] > .row::after{ visibility:hidden }

.ev[data-state="run"] .g{ color:transparent; position:relative }
.ev[data-state="run"] .g::after{ content:""; position:absolute; right:0; top:.45em;
  width:6px; height:6px; border-radius:50%; background:var(--accent);
  animation:breathe 1.4s ease-in-out infinite }
.ev[data-state="err"] .g{ color:var(--err) }
/* inset and not border-left: a border would shift all four tracks by two pixels */
.ev[data-state="err"] > .row{ background:rgba(232,131,107,.07);
                              box-shadow:inset 2px 0 0 var(--err) }

.out{ margin:2px 0 var(--s2) var(--indent);
      max-height:290px; max-height:15lh; overflow:auto; overscroll-behavior:contain;
      white-space:pre-wrap; overflow-wrap:anywhere;
      font:12px/1.5 var(--mono); color:var(--fg-3);
      background:var(--raised); border-left:2px solid var(--line-2);
      border-radius:0 var(--r-sm) var(--r-sm) 0; padding:8px 10px }

/* ---------------- composer ---------------- */
form{ padding:var(--s3) var(--s4) var(--s4); border-top:1px solid var(--line-1);
      background:var(--raised);
      box-shadow:0 -1px 0 rgba(0,0,0,.5), 0 -12px 28px -12px rgba(0,0,0,.65) }
.composer{ display:flex; align-items:flex-end; gap:var(--s2);
           background:var(--base); border:1px solid var(--line-2);
           border-radius:var(--r-lg); padding:10px 10px 10px var(--s3);
           box-shadow:var(--lip); transition:border-color 120ms ease-out }
.composer:focus-within{ border-color:var(--line-3) }
#i{ flex:1; background:transparent; border:0; outline:none; resize:none; color:var(--fg);
    font:var(--t-body)/1.55 var(--sans); min-height:24px; max-height:200px;
    overflow-y:hidden; padding:0; caret-color:var(--accent) }
#i::placeholder{ color:var(--fg-4) }
#go{ width:32px; height:32px; flex:none; border:0; border-radius:50%; display:grid;
     place-items:center; cursor:pointer; background:var(--accent);
     box-shadow:inset 0 1px 0 rgba(255,255,255,.22);
     transition:background 120ms ease-out, transform 80ms ease-out }
#go:active{ transform:scale(.92); box-shadow:none }
#go:disabled{ opacity:.3; cursor:default }
#go[data-mode="stop"]{ background:#d94f45 }
#go svg{ display:none }
#go[data-mode="send"] .s-send, #go[data-mode="stop"] .s-stop{ display:block }
#chip{ display:inline-flex; align-items:center; gap:6px; margin-bottom:var(--s2);
       background:var(--hover); border:1px solid var(--line-2); color:var(--fg-2);
       font-size:var(--t-label); padding:3px 9px; border-radius:var(--r-pill);
       cursor:pointer }
#under{ display:flex; align-items:center; justify-content:space-between;
        gap:var(--s2); padding:var(--s2) var(--s1) 0 }
#tok{ display:inline-flex; align-items:center; gap:6px;
      font-size:var(--t-label); color:var(--fg-3) }

/* ---------------- browser pane ---------------- */
/* The strip only exists when there is more than one tab: a single tab labelled
   with its own title is chrome that says nothing the address bar below it does
   not already say. */
#tabs{ flex:none; display:flex; gap:2px; padding:6px 8px 0; background:var(--raised);
       overflow-x:auto; scrollbar-width:none }
#tabs button{ flex:0 1 190px; min-width:80px; display:flex; align-items:center; gap:6px;
              border:0; border-radius:var(--r) var(--r) 0 0; cursor:pointer;
              background:transparent; color:var(--fg-3); padding:6px 10px;
              font:var(--t-label)/1.4 var(--sans); white-space:nowrap;
              overflow:hidden; text-overflow:ellipsis }
#tabs button:hover{ background:var(--hover); color:var(--fg-2) }
#tabs button[aria-selected="true"]{ background:var(--base); color:var(--fg) }
#tabs .t{ overflow:hidden; text-overflow:ellipsis }

#chrome{ flex:none; height:38px; display:flex; align-items:center; gap:var(--s2);
         padding:0 10px; background:var(--raised); border-bottom:1px solid var(--line-1) }
/* The honesty contract: nothing in here is interactive except what is, so
   nothing in here gets a pointer cursor except what does. */
#chrome, #chrome *{ cursor:default; user-select:none }
#url{ user-select:text }
#mode button{ cursor:pointer }
#dot{ width:7px; height:7px; flex:none; border-radius:50%; background:var(--fg-4) }
[data-state="live"]  #dot{ background:var(--ok); animation:breathe 1.8s ease-in-out infinite }
[data-state="busy"]  #dot{ background:var(--accent); animation:breathe .9s ease-in-out infinite }
[data-state="frozen"]#dot{ background:var(--fg-2) }
[data-state="offline"] #dot, [data-state="error"] #dot{ background:var(--err) }
#url{ flex:1; min-width:0; height:24px; line-height:24px; padding:0 10px;
      border-radius:var(--r-pill); background:var(--well); border:1px solid var(--line-1);
      font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis }
#url .dim{ color:var(--fg-4) }
#url .host{ color:var(--fg) }
#mode{ display:inline-flex; gap:2px; flex:none; background:var(--base);
       border-radius:var(--r); padding:3px }
#mode button{ border:0; background:transparent; color:var(--fg-3);
              border-radius:var(--r-sm); padding:2px 9px;
              font:500 var(--t-label)/1.5 var(--sans) }
#mode button[aria-selected="true"]{ background:var(--top); color:var(--fg);
                                    box-shadow:0 1px 2px rgba(0,0,0,.35) }

/* The frame is solved from the available height, so a wide shot fills the width
   and a tall one fills the height. What is left over is stage, never a hole
   inside the frame. object-fit stays underneath for the one frame where the
   ratio is still the previous page's. */
#stage{ flex:1; min-height:0; padding:14px; display:grid; place-items:center;
        container-type:size }
#browser{ --arn:1.6; --chrome:38px;
          width:min(100%, calc((100cqh - var(--chrome)) * var(--arn)));
          max-height:100%; display:flex; flex-direction:column;
          background:var(--raised); border:1px solid var(--line-2);
          border-radius:10px; overflow:hidden; box-shadow:0 18px 50px -22px #000 }
/* aspect-ratio and not flex:1. With flex the height came from the CONTENT, so
   before the first frame the whole browser collapsed to a 20px strip with the
   placeholder inside it, which reads as broken rather than as empty. Now the
   frame keeps a browser's shape from the first paint, and --arn moves it to the
   real one as soon as a screenshot lands. */
#shot{ aspect-ratio:var(--arn); min-height:0; position:relative;
       background:var(--well); display:grid; place-items:center }
#frame{ width:100%; height:100%; object-fit:contain; object-position:top center;
        display:block }
/* Visibility rides the `hidden` property. The version before this one set
   `style.display = ''` to show the image, which removes the inline value and
   falls back on a stylesheet rule hiding it: the pane stayed black with the
   pixels already decoded inside it, and every structural assertion passed. */
#frame[hidden]{ display:none }
#empty{ color:var(--fg-4); font-size:var(--t-ui) }

/* The small things whose absence is felt without being noticed. */
:focus{ outline:none }
:focus-visible{ outline:2px solid var(--accent); outline-offset:2px; border-radius:inherit }
::selection{ background:rgba(227,138,93,.30); color:#fff }
:root{ accent-color:var(--accent) }
*{ scrollbar-width:thin; scrollbar-color:#2f363e transparent }

@keyframes rise{ from{ opacity:0; transform:translateY(3px) } }
@keyframes breathe{ 0%,100%{opacity:1} 50%{opacity:.35} }
#thread .turn, #thread .ev, #thread .say, #thread .answer{
  animation:rise 140ms cubic-bezier(.2,.6,.3,1) both }
#thread [data-replay]{ animation:none }
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{ animation-duration:.01ms !important;
    animation-iteration-count:1 !important; transition-duration:.01ms !important }
}
</style>

<div id="left">
  <div id="head"><b>AIHawk</b><span class="badge" id="model">no model</span></div>
  <div id="log">
    <div id="thread">
      <div id="hint">
        <p>Tell it what to do, in a sentence. It opens the pages, reads them and
           clicks, and you watch on the right.</p>
        <p class="eg">Go to example.com and tell me the main heading.</p>
        <p class="sm">Plain language: the model works out the clicks. One
           instruction at a time works best.</p>
      </div>
    </div>
    <div id="anchor"></div>
  </div>
  <button id="jump" hidden type="button">jump to latest</button>
  <form id="f" autocomplete="off">
    <span id="chip" hidden>1 message queued <span aria-hidden="true">&#9998;</span></span>
    <div class="composer">
      <textarea id="i" rows="1" placeholder="What should the agent do?"></textarea>
      <button id="go" type="submit" data-mode="send" aria-label="Send" disabled>
        <svg class="s-send" width="14" height="14" viewBox="0 0 14 14" fill="none"
             stroke="#101317" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M7 12V2M2.5 6.5L7 2l4.5 4.5"/></svg>
        <svg class="s-stop" width="12" height="12" viewBox="0 0 12 12">
          <rect width="12" height="12" rx="2" fill="#fff"/></svg>
      </button>
    </div>
    <div id="under">
      <span class="label">agent</span>
      <span id="tok" hidden></span>
    </div>
  </form>
</div>

<div id="right" data-state="idle">
  <div id="tabs" hidden></div>
  <div id="chrome">
    <span id="dot"></span>
    <span id="url" class="dim">no page yet</span>
    <span id="mode" role="tablist">
      <button role="tab" aria-selected="true" data-v="live" type="button">Live</button>
      <button role="tab" aria-selected="false" data-v="hold" type="button">Frozen</button>
    </span>
    <span id="state" class="label" aria-live="polite">idle</span>
  </div>
  <div id="stage">
    <div id="browser">
      <div id="shot">
        <img id="frame" alt="live browser view" hidden>
        <span id="empty">nothing running yet</span>
      </div>
    </div>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);
const el = (t,c,x) => { const e = document.createElement(t);
                        if(c) e.className = c; if(x != null) e.textContent = x; return e; };

/* Raw tool names read as the machine's word order. One table, two tenses. */
const VERB = {
  browser_navigate:['Navigating','Navigated'], browser_click:['Clicking','Clicked'],
  browser_click_at:['Clicking','Clicked'],     browser_type:['Typing','Typed'],
  browser_press_key:['Pressing','Pressed'],    browser_read_text:['Reading','Read'],
  browser_read_html:['Reading','Read'],        browser_snapshot:['Inspecting','Inspected'],
  browser_evaluate:['Evaluating','Evaluated'], browser_take_screenshot:['Capturing','Captured'],
  browser_watch:['Watching','Watched'],
  browser_select_option:['Choosing','Chose'],
  session_new_page:['Opening tab','Opened tab'],   session_select_page:['Switching tab','Switched tab'],
  session_close_page:['Closing tab','Closed tab'], session_list_pages:['Listing tabs','Listed tabs'],
  session_start:['Starting browser','Started browser'],
  session_status:['Checking session','Checked session']
};
const LEAD = /^(I will |I'll |I am |I'm |Let me |Now I will |Now I'll )/i;
const LONG = 120;

const thread = $('thread'), anchor = $('anchor'), log = $('log');
let turn = null, live = null, hold = null, n = 0, t0 = 0, timer = 0;
let busyNow = false, queued = null, pinned = false, settle = 0;

const dur = ms => ms < 1000 ? Math.round(ms) + 'ms' : (ms/1000).toFixed(1) + 's';

function newTurn(){
  const hint = $('hint'); if(hint) hint.remove();
  n = 0; turn = el('section','turn'); thread.appendChild(turn); return turn;
}
function put(node, replay){ if(!turn) newTurn(); if(replay) node.dataset.replay = '1';
                            turn.appendChild(node); }

/* The narration is held for one event, so a sentence followed by tool calls
   reads as their lead-in and a sentence with nothing after it reads as the
   answer. One event of lookahead is all a stream allows and all this needs. */
function flush(asAnswer, replay){
  if(hold === null) return;
  const text = hold.replace(LEAD,'').replace(/^\w/, c => c.toUpperCase());
  hold = null;
  put(el('div', asAnswer ? 'answer' : 'say', text), replay);
}

function step(text, replay){
  const sp = text.indexOf(' ');
  const name = sp < 0 ? text : text.slice(0, sp);
  const arg  = sp < 0 ? ''   : text.slice(sp + 1);
  const d = el('details','ev'); d.dataset.state = 'run'; d.dataset.name = name;
  const s = el('summary','row');
  const lab = el('span','lab');
  lab.appendChild(el('b', null, (VERB[name] || ['Calling','Called'])[0]));
  if(arg){ lab.append(' ', el('code', null, arg)); }
  s.append(el('span','g', ++n), lab, el('span','meta'));
  d.appendChild(s);
  put(d, replay);
  live = d;
  clearInterval(timer);
  if(!replay){                       /* a replayed step has no live clock to run */
    t0 = performance.now();
    const meta = s.lastElementChild;
    timer = setInterval(() => meta.textContent = dur(performance.now() - t0), 100);
  }
}

/* A result or an error folds into the step above it, which is what makes a step
   one unit carrying its target, its timing, its state and its own disclosure. */
function land(kind, text, replay){
  clearInterval(timer);
  if(!live) return orphan(kind, text, replay);
  const d = live, s = d.firstElementChild;
  live = null;
  d.dataset.state = kind === 'err' ? 'err' : 'ok';
  s.querySelector('.lab b').textContent =
    (VERB[d.dataset.name] || ['Calling','Called'])[kind === 'err' ? 0 : 1];
  if(!replay) s.lastElementChild.textContent = dur(performance.now() - t0);
  /* Short output goes ON the row and the row stops being expandable. In an
     ordinary run most rows are then one line with the answer already visible,
     which is the difference between a list and a stack of accordions. */
  if(text.length <= LONG && text.indexOf('\n') < 0){
    d.dataset.body = 'none';
    s.querySelector('.lab').append(' ', el('span','inline', text));
  } else {
    d.appendChild(el('pre','out', text));
  }
}

function orphan(kind, text, replay){
  const p = el('div', kind === 'err' ? 'orph' : 'say');
  p.append(el('span','sr', kind === 'err' ? 'error ' : ''), el('span', null, text));
  put(p, replay);
}

/* Only the first settle. After that the CSS sentinel pins the view, and a reader
   who has scrolled up is never yanked because nothing here fires again. */
function settleOnce(){
  if(pinned) return;
  clearTimeout(settle);
  settle = setTimeout(() => { pinned = true; anchor.scrollIntoView({block:'end'}); }, 150);
}

const es = new EventSource('/chat/events');
es.onmessage = (e) => {
  const m = JSON.parse(e.data), r = m.replay;
  switch(m.kind){
    case 'model': $('model').textContent = m.text; break;
    case 'usage': meter(m.text); break;
    case 'busy':
      busyNow = m.text === '1';
      if(!busyNow){ flush(true, r); live = null; clearInterval(timer);
                    if(queued){ const t = queued; queued = null; send(t); } }
      paint(); break;
    case 'you':   flush(false, r); live = null; newTurn();
                  put(el('div','you', m.text), r); break;
    case 'said':  flush(false, r); hold = m.text; break;
    case 'tool':  flush(false, r); step(m.text, r); break;
    case 'result':
    case 'err':   flush(false, r); land(m.kind, m.text, r); break;
    /* Deliberately total: a kind this page has never heard of is still shown,
       for the same reason an unknown tool still renders its arguments. */
    default:      flush(false, r); orphan('said', m.text, r);
  }
  settleOnce();
};

new IntersectionObserver(([e]) => { $('jump').hidden = e.isIntersecting; },
                         {root: log}).observe(anchor);
$('jump').onclick = () => anchor.scrollIntoView({block:'end', behavior:'smooth'});

/* ---- the composer. It is never disabled: greying out the input the moment the
   run gets interesting is most of what reads as unfinished. ---- */
const i = $('i'), go = $('go'), f = $('f'), chip = $('chip');

function paint(){
  const typed = i.value.trim().length > 0;
  const stop = busyNow && !typed;
  go.dataset.mode = stop ? 'stop' : 'send';
  go.disabled = !stop && !typed;
  go.setAttribute('aria-label', stop ? 'Stop'
    : queued ? 'Replace queued message' : busyNow ? 'Queue for next turn' : 'Send');
  i.placeholder = queued ? 'Type to replace the queued message'
    : busyNow ? 'Type to queue a message' : 'What should the agent do?';
  chip.hidden = !queued;
}
i.addEventListener('input', () => {
  i.style.height = 'auto';
  i.style.height = Math.min(i.scrollHeight, 200) + 'px';
  i.style.overflowY = i.scrollHeight >= 200 ? 'auto' : 'hidden';
  paint();
});
i.addEventListener('keydown', e => {
  if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); f.requestSubmit(); }
});
/* A pencil and not a cross: a cross would read as "cancel the queued message".
   This returns it to the composer to be edited. */
chip.onclick = () => { i.value = queued; queued = null; i.focus();
                       i.dispatchEvent(new Event('input')); };

function send(text){
  fetch('/chat/send', {method:'POST', headers:{'Content-Type':'application/json'},
                       body: JSON.stringify({text})});
}
f.onsubmit = (e) => {
  e.preventDefault();
  const t = i.value.trim();
  if(!t){ if(busyNow) fetch('/chat/stop', {method:'POST'}); return; }
  i.value = ''; i.style.height = 'auto';
  if(busyNow){ queued = t; paint(); return; }
  send(t); paint();
};

/* The meter reads the LAST turn's prompt, never a sum: every turn is sent the
   whole transcript, so the newest prompt IS the current occupancy. */
function meter(json){
  let u; try { u = JSON.parse(json); } catch(err) { return; }
  const k = v => v >= 1000 ? (v/1000).toFixed(1) + 'k' : String(v);
  $('tok').hidden = false;
  $('tok').textContent = k(u.last_prompt || 0) + ' ctx  /  ' +
                         k((u.prompt || 0) + (u.completion || 0)) + ' total';
}

/* ---- the browser pane ---- */
const img = $('frame'), empty = $('empty'), right = $('right'), stateEl = $('state'),
      browser = $('browser'), urlEl = $('url');
let frozen = false;

function say(s){ right.dataset.state = s; stateEl.textContent = s; }

$('mode').onclick = (e) => {
  const b = e.target.closest('button'); if(!b) return;
  frozen = b.dataset.v === 'hold';
  for(const x of $('mode').children) x.setAttribute('aria-selected', String(x === b));
  say(frozen ? 'frozen' : 'live');
};

async function tick(){
  if(!frozen) try {
    const r = await fetch('/live/frame?t=' + Date.now(), {cache:'no-store'});
    if(r.status === 204){ img.hidden = true; empty.hidden = false; say('idle'); }
    else if(r.ok){
      const blob = await r.blob(), old = img.src;
      img.src = URL.createObjectURL(blob);
      if(old.startsWith('blob:')) URL.revokeObjectURL(old);
      img.hidden = false; empty.hidden = true; say('live');
      if(img.naturalWidth) browser.style.setProperty(
        '--arn', (img.naturalWidth / img.naturalHeight).toFixed(4));
    }
    /* Busy, not broken: a screenshot cannot be taken mid-navigation, and at this
       rate an ordinary navigation produces several in a row. The last frame
       stays on screen, because a stale picture of where the browser was beats a
       red word about where it is going. */
    else if(r.status === 503){ say('busy'); }
    else { say('error'); }
  } catch(err){ say('offline'); }
  /* Ask for the next frame only once this one has landed, or a browser slower
     than the interval accumulates requests it can never serve. */
  setTimeout(tick, 500);
}

/* Built from elements with textContent and never innerHTML: this string comes
   from whatever page is being automated. */
function paintUrl(u){
  urlEl.textContent = ''; urlEl.title = u || ''; urlEl.className = u ? '' : 'dim';
  if(!u){ urlEl.textContent = 'no page yet'; return; }
  let a; try { a = new URL(u); } catch(err) { urlEl.textContent = u; return; }
  const part = (t,c) => urlEl.appendChild(el('span', c, t));
  part(a.protocol + '//', 'dim'); part(a.host, 'host'); part(a.pathname + a.search, 'dim');
}
function paintTabs(rows){
  const box = $('tabs');
  /* One tab is not a strip. Showing it would be chrome repeating the address
     bar directly beneath it. */
  if(!rows || rows.length < 2){ box.hidden = true; box.textContent = ''; return; }
  box.hidden = false;
  box.textContent = '';
  for(const r of rows){
    const b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('aria-selected', String(!!r.active));
    b.title = (r.title || '') + (r.url ? '  -  ' + r.url : '');
    b.dataset.id = r.id;
    let host = '';
    try { host = new URL(r.url).host; } catch(err) { host = ''; }
    b.appendChild(el('span','t', r.title || host || r.id));
    box.appendChild(b);
  }
}
/* A tab DOES something, so it is the one thing in this chrome that may look
   clickable. Selecting is an action on the browser like any other, and it goes
   through the same tool an agent would call. */
$('tabs').onclick = (e) => {
  const b = e.target.closest('button'); if(!b) return;
  fetch('/live/select', {method:'POST', headers:{'Content-Type':'application/json'},
                         body: JSON.stringify({id: b.dataset.id})});
};

async function where(){
  try { const r = await fetch('/live/tabs', {cache:'no-store'});
        if(r.ok){ const j = await r.json(); paintUrl(j.url || ''); paintTabs(j.tabs); } }
  catch(err){}
  setTimeout(where, 2000);
}
paint(); tick(); where();
</script>
"""


class ChatService:
    """One conversation, its listeners, and the link it drives."""

    def __init__(self, link: Link, brain: Brain,
                 model_label: str = "no model") -> None:
        self._link = link
        self._brain = brain
        self._listeners: List[asyncio.Queue] = []
        self.history: List[Dict[str, str]] = []
        self.model_label = model_label
        self._busy = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._listeners.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._listeners:
            self._listeners.remove(q)

    async def emit(self, kind: str, text: str) -> None:
        event = {"kind": kind, "text": text}
        # `busy` and `usage` are STATE, not conversation: replaying them to
        # somebody who opens the page later would show a spinner for work that
        # finished an hour ago, and a meter for a turn nobody is watching.
        if kind not in ("busy", "usage"):
            self.history.append(event)
        for q in list(self._listeners):
            q.put_nowait(event)

    def start(self, text: str) -> None:
        """Run an instruction detached, keeping the handle so it can be stopped.

        The task is held for exactly that reason. Firing and forgetting is one
        line shorter and makes the stop button a decoration.
        """
        self._task = asyncio.create_task(self.send(text))

    def stop(self) -> bool:
        t = self._task
        if t is not None and not t.done():
            t.cancel()
            return True
        return False

    async def send(self, text: str) -> None:
        async with self._busy:
            # Emitted here and not added by the page, so the instruction is part
            # of the transcript: somebody opening the page mid-run sees what was
            # asked, and a reload does not lose it. The page adding it locally is
            # one line shorter and leaves a conversation with no questions in it.
            await self.emit("you", text)
            await self.emit("busy", "1")
            try:
                await self._brain.handle(text, self._link, self.emit)
            except asyncio.CancelledError:
                # The cancellation lands at the next await, which is the next
                # tool call: the request to the model itself is synchronous. So
                # stop means "after the step in flight", and the page is told
                # that rather than promising something faster.
                await self.emit("err", "stopped")
                raise
            except Exception as exc:
                await self.emit("err", f"{type(exc).__name__}: {exc}")
            finally:
                await self.emit("busy", "0")


def build_app(link: Link, service: ChatService) -> Starlette:
    async def root(_request: Request) -> HTMLResponse:
        return HTMLResponse(PAGE)

    async def send(request: Request) -> JSONResponse:
        body = await request.json()
        text = (body or {}).get("text", "")
        if not text:
            return JSONResponse({"error": "empty"}, status_code=400)
        service.start(text)
        return JSONResponse({"accepted": True})

    async def stop(_request: Request) -> JSONResponse:
        return JSONResponse({"stopped": service.stop()})

    async def events(_request: Request) -> StreamingResponse:
        q = service.subscribe()

        async def stream() -> AsyncIterator[bytes]:
            try:
                yield b"data: " + json.dumps(
                    {"kind": "model", "text": service.model_label}).encode() + b"\n\n"
                # Flagged as replay so the page does not animate forty rows at
                # once and does not start a stopwatch on work that finished
                # before this listener existed.
                for past in list(service.history):
                    yield b"data: " + json.dumps({**past, "replay": True}).encode() + b"\n\n"
                while True:
                    event = await q.get()
                    yield b"data: " + json.dumps(event).encode() + b"\n\n"
            finally:
                service.unsubscribe(q)

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store"})

    async def frame(_request: Request) -> Response:
        if not link.touched:
            # 204, not an error: nothing is wrong, there is simply nothing to
            # look at. Asking the server would START a browser, which is exactly
            # what a view is not allowed to cause.
            return Response(status_code=204)
        try:
            got = image_of(await link.call("browser_take_screenshot"))
        except Exception as exc:
            return JSONResponse({"error": str(exc)[:200]}, status_code=503)
        if got is None:
            return Response(status_code=204)
        png, mime = got
        return Response(png, media_type=mime, headers={"Cache-Control": "no-store"})

    async def tabs(_request: Request) -> JSONResponse:
        """Every tab, and which one is current.

        ONE call where there were two. It asks `session_list_pages`, which since
        0.9.0 of the server answers with id, title, url and active - the four
        fields its description had always promised and had never returned. While
        it returned ids only this had to ask `browser_evaluate` for
        `location.href` instead, which is script in the page to learn something
        the server already knew.

        A stale or older server is not an error here: anything that does not
        parse into those fields leaves the strip empty and the address blank,
        and the pane keeps working as a picture.
        """
        if not link.touched:
            return JSONResponse({"url": "", "tabs": []})
        try:
            raw = await link.call_text("session_list_pages")
            rows = json.loads(raw)
        except Exception:
            return JSONResponse({"url": "", "tabs": []})
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            return JSONResponse({"url": "", "tabs": []})
        here = next((r for r in rows if r.get("active")), rows[0] if rows else {})
        return JSONResponse({"url": here.get("url") or "", "tabs": rows})

    async def select(request: Request) -> JSONResponse:
        body = await request.json()
        page_id = (body or {}).get("id", "")
        if not page_id:
            return JSONResponse({"error": "no id"}, status_code=400)
        await link.call("session_select_page", {"page_id": page_id})
        return JSONResponse({"ok": True})

    return Starlette(routes=[
        Route("/", root),
        Route("/chat/send", send, methods=["POST"]),
        Route("/chat/stop", stop, methods=["POST"]),
        Route("/chat/events", events),
        Route("/live/frame", frame),
        Route("/live/tabs", tabs),
        Route("/live/select", select, methods=["POST"]),
    ])
