
const $ = id => document.getElementById(id);
/* ---- markdown, and the gate lifts everything down to the end of `rich` ----
   These lines are the only ones in this file a JavaScript engine runs during
   the tests: `test_the_answer_pane_draws_markdown.py` cuts the region out and
   executes it against a DOM small enough to print. The markers exist so that
   cut is exact - moving them means moving what is under test. */
const el = (t,c,x) => { const e = document.createElement(t);
                        if(c) e.className = c; if(x != null) e.textContent = x; return e; };

/* Markdown to NODES, never to a string of HTML.
   The text arriving here was written by a model that has just read arbitrary
   web pages, so it is chosen by whoever wrote the last page it visited. Putting
   it through innerHTML is the documented road to exfiltration by injected
   image, and no amount of sanitising makes that road shorter than this one.
   So: the marks become elements, built by hand, and the text between them stays
   text. A `<script>` in the answer is still drawn as the characters of a
   script, because it never stops being a text node.
   Images are absent on purpose - they are the exfiltration vector itself, and
   an `<img>` fetches its source the instant it enters the document, with no
   click and no error needed. A link is drawn but never made clickable, and its
   destination is PRINTED rather than hidden behind words, so an injected
   address is legible instead of invisible. */
function inline(text, into){
  for(const part of text.split(/(\*\*[^*\n]+\*\*|`[^`\n]+`|\*[^*\n]+\*|!?\[[^\]\n]*\]\([^()\s]*\))/)){
    if(!part) continue;
    const two = part.length > 4 && part.startsWith('**') && part.endsWith('**');
    const tick = part.length > 2 && part.startsWith('`') && part.endsWith('`');
    const one = part.length > 2 && !two && part.startsWith('*') && part.endsWith('*');
    const link = /^!?\[([^\]\n]*)\]\(([^()\s]*)\)$/.exec(part);
    if(two)       into.appendChild(el('strong', null, part.slice(2, -2)));
    else if(tick) into.appendChild(el('code', null, part.slice(1, -1)));
    else if(one)  into.appendChild(el('em', null, part.slice(1, -1)));
    else if(link){ if(link[1]) into.appendChild(el('span','lk', link[1]));
                   if(link[2]) into.appendChild(el('span','href', link[2])); }
    else          into.appendChild(document.createTextNode(part));
  }
}

/* The block marks, which are most of what a model writes: it answers in
   headings and lists far more often than in the three inline marks this pane
   understood until now, and every one of them was drawn as its own characters -
   `## Roles` arrived on screen as a hash, a hash and a space. */
const HEAD   = /^(#{1,6})\s+(.*)$/;
const BULLET = /^(\s*)[-*+]\s+(.*)$/;
const NUMBER = /^(\s*)\d+[.)]\s+(.*)$/;
const QUOTE  = /^\s*>\s?(.*)$/;
const RULE   = /^\s*([-*_])\s*(?:\1\s*){2,}$/;
const CELLS  = /\|/;
const DASHES = /^[\s:|-]*-[\s:|-]*$/;

/* ⛔ A FLOOR ON THE RECURSION, because this text was written by a model
   that had just read arbitrary web pages. Measured against the extracted
   parser: 20,000 `>` on one line, or a list indented 10,000 levels, throws
   RangeError - and the throw does not land in the parser, it lands in the
   event handler, where it strands the step clock, skips the redraw and eats
   the queued instruction. Past this depth the marks are drawn as the text
   they are, which is what nesting that deep actually is. */
const DEEP = 24;
function blocks(text, into, depth){
  depth = depth || 0;
  const lines = text.split('\n');
  let i = 0;
  while(i < lines.length){
    const line = lines[i];
    if(!line.trim()){ i++; continue; }
    const head = HEAD.exec(line);
    if(head){
      /* `#` lands on h3: the page's own title is above this pane, and an answer
         that opened at h1 would outrank it in the document outline. */
      const h = el('h' + Math.min(head[1].length + 2, 6), 'md-h');
      inline(head[2], h); into.appendChild(h); i++; continue;
    }
    if(RULE.test(line)){ into.appendChild(el('hr','md-hr')); i++; continue; }
    if(QUOTE.test(line) && depth < DEEP){
      const held = [];
      while(i < lines.length && QUOTE.test(lines[i])) held.push(QUOTE.exec(lines[i++])[1]);
      const q = el('blockquote','md-q');
      blocks(held.join('\n'), q, depth + 1); /* a quote holds blocks like any other */
      into.appendChild(q); continue;
    }
    if(CELLS.test(line) && i + 1 < lines.length && DASHES.test(lines[i + 1])
       && lines[i + 1].includes('-')){ i = tableAt(lines, i, into); continue; }
    if((BULLET.test(line) || NUMBER.test(line)) && depth < DEEP){
      i = listAt(lines, i, into, depth); continue;
    }
    /* ⛔ THE FIRST LINE IS TAKEN WITHOUT ASKING, and that is what makes this
       loop finish. Every branch above consumes; this one is the floor, so if
       its condition ever excluded the line that got here the walker would sit
       on it forever building empty paragraphs - a hung tab, not a bad render.
       Measured while mutating the list branch away: the browser stops. */
    const held = [lines[i++]];
    while(i < lines.length && lines[i].trim() && !HEAD.test(lines[i])
          && !RULE.test(lines[i]) && !QUOTE.test(lines[i])
          && !BULLET.test(lines[i]) && !NUMBER.test(lines[i])) held.push(lines[i++]);
    const p = el('p','md-p');
    inline(held.join('\n'), p);
    into.appendChild(p);
  }
}

/* Both of these return the line to carry on from, so the walker above never has
   to guess how much they ate - a block parser that advances by one and hopes is
   how a list ends up inside itself. */
function listAt(lines, i, into, depth){
  const first = BULLET.exec(lines[i]) || NUMBER.exec(lines[i]);
  const base = first[1].length;
  const ordered = !BULLET.test(lines[i]);
  const box = el(ordered ? 'ol' : 'ul', 'md-l');
  let item = null;
  while(i < lines.length && lines[i].trim()){
    const mark = BULLET.exec(lines[i]) || NUMBER.exec(lines[i]);
    if(!mark){
      /* A line under an item and not marked is the rest of that item. */
      if(!item) break;
      item.appendChild(document.createTextNode('\n' + lines[i].trim()));
      i++; continue;
    }
    if(mark[1].length > base && (depth || 0) < DEEP){
      i = listAt(lines, i, item || box, (depth || 0) + 1); continue;
    }
    if(mark[1].length < base || !BULLET.test(lines[i]) !== ordered) break;
    item = el('li','md-i');
    inline(mark[2], item);
    box.appendChild(item);
    i++;
  }
  into.appendChild(box);
  return i;
}

function tableAt(lines, i, into){
  const cells = row => row.replace(/^\s*\|/,'').replace(/\|\s*$/,'').split('|');
  const box = el('table','md-t');
  const head = el('tr','md-r');
  for(const c of cells(lines[i])) inline(c.trim(), head.appendChild(el('th')));
  box.appendChild(head);
  i += 2;                                   /* the header row and its dashes */
  while(i < lines.length && lines[i].trim() && CELLS.test(lines[i])){
    const tr = el('tr','md-r');
    for(const c of cells(lines[i])) inline(c.trim(), tr.appendChild(el('td')));
    box.appendChild(tr); i++;
  }
  into.appendChild(box);
  return i;
}

function rich(text){
  const frag = document.createDocumentFragment();
  /* An odd number of fences means the last block never closed, which is what a
     half-written answer looks like. It is still shown as code: the alternative
     is prose that changes shape when the closing fence arrives. */
  text.split('```').forEach((block, i) => {
    if(i % 2) frag.appendChild(el('pre','out', block.replace(/^[a-z]*\n/i, '')));
    else if(block.trim()) blocks(block, frag, 0);
  });
  return frag;
}
/* ---- end markdown ---- */

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
  browser_open:['Opening browser','Opened browser'],
  browser_close:['Closing browser','Closed browser'],
  browser_list:['Listing browsers','Listed browsers'],
  browser_focus:['Switching browser','Switched browser'],
  session_list:['Listing sessions','Listed sessions'],
  session_forget:['Deleting session','Deleted session'],
  session_status:['Checking session','Checked session']
};
const LEAD = /^(I will |I'll |I am |I'm |Let me |Now I will |Now I'll )/i;
/* ⛔ MEASURED IN CHARACTERS, SPENT IN PIXELS - the same defect this project
   recorded when `ch` was mistaken for a character, one surface later. The
   label track is 416px wide at the default split, the mono face is 7.15px a
   character at 13px and the verb in front eats about 67, so the row shows
   about FORTY-EIGHT. The branch accepted a hundred and twenty. Counted on a
   live transcript: 43 rows of 108 were cut off AND had their disclosure
   removed, so the one thing that could have shown the rest was gone. */
const LONG = 48;

const thread = $('thread'), anchor = $('anchor'), log = $('log');
let turn = null, live = null, hold = null, n = 0, t0 = 0, timer = 0;
let busyNow = false, queued = null, pinned = false, settle = 0;

/* ---------------- the queued message ----------------
   ⛔ IT WAS A VARIABLE, AND A RELOAD ATE IT. Somebody types a follow-up while
   the agent is working, the page reloads - a refresh, a crash, a laptop lid -
   and the sentence they wrote is gone with nothing said. That is the one thing
   this interface must not do to typed text: the transcript is saved, the
   answer is saved, and the instruction that was waiting to run was the only
   thing held in a variable.

   Kept per conversation, because it belongs to one: switching sessions must
   not carry somebody's pending sentence into another chat. Written through ONE
   function rather than beside each of the five places that assign it - that is
   how it went unsaved in the first place, and a sixth assignment somewhere
   would go unsaved the same way.

   Storage can refuse (a private window, site data blocked) and the page has to
   work when it does: the queue simply goes back to being a variable. */
/* ⛔ A FUNCTION AND NOT A CONSTANT, because a constant here read `here`
   before `here` was declared - and a top-level binding used in its own dead
   zone throws at parse time, which kills the WHOLE script: no event stream, no
   session column, no workspace, and the page still renders. 440 tests green
   with the page dead, for the second time in two days and by a different
   mechanism than the first. Computed when called, the order of the lines stops
   being something anybody has to keep right. */
const qkey = () => 'aihawk.queued.' + here;
function setQueued(text){
  queued = text || null;
  try {
    if(queued) localStorage.setItem(qkey(), queued);
    else localStorage.removeItem(qkey());
  } catch(err){}
  paint();
}
function queuedFromBefore(){
  try { return localStorage.getItem(qkey()); } catch(err){ return null; }
}
let pend = null, pendTimer = 0;

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
  const box = el('div', asAnswer ? 'answer' : 'say');
  /* ⛔ A DEFECT INSIDE ONE ANSWER MUST NOT TAKE THE TURN WITH IT. This runs
     from the event handler, and the caller goes on to clear the step clock,
     redraw the column and send whatever was queued - so a throw here stranded
     a 10 Hz timer for the life of the page and silently swallowed an
     instruction somebody had typed. The text is shown as text rather than
     lost: the same shape as the scheduler, which keeps doing its own job when
     a pass inside it fails. */
  try {
    box.appendChild(rich(text));
  } catch(err){
    box.appendChild(el('pre','out', text));
  }
  put(box, replay);
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
    /* Anything that does not fit keeps a body, so the chevron is present for
       exactly the rows that need it. */
    d.appendChild(el('pre','out', text));
    /* And the row says it on hover too: nobody should have to open a
       disclosure to find out whether it is worth opening. */
    s.querySelector('.lab').title = text.slice(0, 400);
  }
}

function orphan(kind, text, replay){
  const p = el('div', kind === 'err' ? 'orph' : 'say');
  p.append(el('span','sr', kind === 'err' ? 'error ' : ''), el('span', null, text));
  put(p, replay);
}

/* The wait, made visible. Measured on this interface: the instruction reaches
   the screen 23 ms after the click and the server accepts it in 2, but the
   first thing the AGENT does lands 4 to 7 seconds later, because the model has
   to read the whole transcript before it can act - and the pane said nothing at
   all in between. That silence is what "everything freezes for a second" was
   describing: not a blocked page, an unlit one.

   A running clock and not a spinner, because the number is the honest part:
   it says the machine is alive AND how long this is taking, and it is the same
   clock a step already shows, so the wait reads as part of the same sequence. */
function waiting(){
  if(pend) return;
  pend = el('div','pend');
  const lab = el('span','lab');
  lab.append(el('b', null, 'Thinking'));
  pend.append(el('span','g', ''), lab, el('span','meta'));
  put(pend, false);
  const meta = pend.lastElementChild, from = performance.now();
  pendTimer = setInterval(() => meta.textContent = dur(performance.now() - from), 100);
}

function waited(){
  if(!pend) return;
  clearInterval(pendTimer);
  pend.remove();
  pend = null;
}

/* Only the first settle. After that the CSS sentinel pins the view, and a reader
   who has scrolled up is never yanked because nothing here fires again. */
function settleOnce(){
  if(pinned) return;
  clearTimeout(settle);
  settle = setTimeout(() => { pinned = true; anchor.scrollIntoView({block:'end'}); }, 150);
}

/* ---------------- which conversation this page is in ----------------
   ⛔ ONE PLACE, AND EVERY REQUEST GOES THROUGH IT. The server routes all read
   `?s=`, so a fetch that forgets it acts on the DEFAULT conversation while the
   page shows another - and the way that shows up is the picture on the right
   belonging to somebody else's browser, with nothing red anywhere. `at()` is
   the only thing that writes the parameter, so there is one place to be wrong
   and it is covered by a test that reads this file.

   The id is kept in the URL rather than in a variable, so a reload, a bookmark
   and a second tab all land in the same conversation instead of silently
   dropping to the default one. */
let here = new URLSearchParams(location.search).get('s') || 'default';
const at = (path) => path + (path.includes('?') ? '&' : '?') + 's=' + encodeURIComponent(here);

let es = null;
function listen(){
  if(es) es.close();
  es = new EventSource(at('/chat/events'));
  es.onmessage = onEvent;
  /* ⛔ A STREAM THAT DIED LOOKS EXACTLY LIKE AN AGENT WITH NOTHING TO SAY.
     EventSource reconnects on its own, so this is not a retry - it is the
     only signal that the silence is the connection and not the work. The dot
     and the word beside it describe the BROWSER, and said `live` throughout. */
  es.onerror = () => {
    if(es.readyState === EventSource.CONNECTING) say('offline', 'reconnecting');
    if(es.readyState === EventSource.CLOSED) say('offline', 'the stream closed');
  };
  es.onopen = () => { if(right.dataset.state === 'offline') say(frozen ? 'frozen' : 'live'); };
}
const onEvent = (e) => {
  const m = JSON.parse(e.data), r = m.replay;
  switch(m.kind){
    case 'model': $('model').textContent = m.text; break;
    /* Sent to every listener, so a second tab clears too instead of showing a
       transcript the server has already forgotten. */
    case 'fresh': wipe(); break;
    case 'busy':
      busyNow = m.text === '1';
      /* Not on a replay: those events describe a wait that is over. */
      if(busyNow && !r) waiting(); else waited();
      if(!busyNow){ flush(true, r); live = null; clearInterval(timer);
                    /* The name of a conversation is decided by its FIRST
                       instruction, on the server, so the column is stale from
                       the moment a new session is used until it is redrawn.
                       Redrawn on the end of a turn and not on its start: the
                       turn count beside the name is only right once. */
                    if(!r) drawChats();
                    if(queued){ const t = queued; setQueued(null); send(t); } }
      paint(); break;
    case 'you':   flush(false, r); live = null; newTurn();
                  put(el('div','you', m.text), r); break;
    case 'said':  waited(); flush(false, r); hold = m.text; break;
    case 'tool':  waited(); flush(false, r); step(m.text, r); break;
    case 'result':
    case 'err':   flush(false, r); land(m.kind, m.text, r);
                  /* The step is done and the model is reading its result, which
                     is another wait of the same kind: the loop asks again before
                     anything else can appear. */
                  if(busyNow && !r) waiting();
                  break;
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
const i = $('i'), go = $('go'), halt = $('halt'), f = $('f'), chip = $('chip'),
      fresh = $('fresh');

function paint(){
  const typed = i.value.trim().length > 0;
  /* Shown for as long as work is in flight and for no other reason: it is tied
     to the run, never to what the composer happens to contain. */
  halt.hidden = !busyNow;
  /* Refused while a run is in flight, and shown as refused rather than left to
     fail at the server: dropping a transcript something is still writing into
     is not undoable. */
  fresh.disabled = busyNow;
  go.disabled = !typed;
  go.setAttribute('aria-label',
    queued ? 'Replace queued message' : busyNow ? 'Queue for next turn' : 'Send');
  i.placeholder = queued ? 'Type to replace the queued message'
    : busyNow ? 'Type to queue a message' : 'What should the agent do?';
  chip.hidden = !queued;
}
i.addEventListener('input', () => {
  /* ⛔ ONE FORCED LAYOUT PER KEYSTROKE, NOT TWO. Reading scrollHeight after
     writing height forces the layout; reading it a SECOND time after the
     second write forces another, over a document holding the whole
     transcript. The one number is enough to decide both. */
  i.style.height = 'auto';
  const wants = i.scrollHeight;
  i.style.height = Math.min(wants, 200) + 'px';
  i.style.overflowY = wants >= 200 ? 'auto' : 'hidden';
  paint();
});
i.addEventListener('keydown', e => {
  if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); f.requestSubmit(); }
});
/* Escape stops the run, from anywhere on the page. The button is the visible
   way and this is the one a hand already on the keyboard reaches first, which
   matters more now that the loop has no ceiling of its own. Not while typing
   into the composer with something in it: there Escape belongs to the draft. */
document.addEventListener('keydown', e => {
  if(e.key !== 'Escape' || !busyNow) return;
  if(document.activeElement === i && i.value.trim()) return;
  /* Through the same door as the button: a hoisted declaration, so calling it
     from above where it is written is safe and nothing here depends on the
     order of the lines. */
  ask('/chat/stop', undefined,
      'The stop did not reach the agent - it is still running');
});
/* A pencil and not a cross: a cross would read as "cancel the queued message".
   This returns it to the composer to be edited. */
chip.onclick = () => { i.value = queued; setQueued(null); i.focus();
                       i.dispatchEvent(new Event('input')); };

/* ⛔ THE BOX IS NOT EMPTIED UNTIL THE SERVER HAS THE SENTENCE. This page
   already argues, about the QUEUED path, that losing typed text with nothing
   said is the one thing it must not do - and then the primary path cleared
   the box first and fired a fetch nobody read. Server restarting, port
   changed, laptop asleep: the instruction was gone and the transcript never
   grew, which reads as the agent ignoring you. */
async function send(text){
  try {
    const r = await door('/chat/send', {method:'POST',
                         headers:{'Content-Type':'application/json'},
                         body: JSON.stringify({text})});
    if(!r.ok) throw new Error('HTTP ' + r.status);
  } catch(err){
    /* Give it back, exactly as it was, and say why - the sentence is the
       person's work and this is the only copy of it. */
    i.value = text;
    i.dispatchEvent(new Event('input'));
    if(vanished) return;
    orphan('err', 'That instruction did not reach the server (' + err.message
           + '). It is back in the box - try again.');
  }
}
/* Clearing the page is NOT what this does, and the difference is the point:
   it asks the server to forget the transcript, because the transcript is what
   every turn resends and therefore what the wait and the bill are made of. The
   page is wiped only when the server says it has forgotten. */
function wipe(){
  waited();
  thread.textContent = '';
  turn = null; live = null; hold = null; n = 0;
  clearInterval(timer);
  /* Idle until told otherwise. On a reconnection the server sends this wipe
     first and the run state after it, so a page that reconnects to a RESTARTED
     process stops believing in a run that died with the old one - which
     otherwise left the composer saying "queue for next turn" forever. */
  busyNow = false;
  setQueued(null);
}
let vanished = false;
/* ⛔ ONE PLACE ASKS THIS CONVERSATION FOR ANYTHING, so one place can notice
   that it is not there any more. Six fetches carry `?s=`, and each of them
   would otherwise need the same three lines - written six times, the seventh
   is where a page goes on talking to a session somebody deleted. Which is not
   hypothetical: every one of those questions used to DECLARE the session again
   on the server, so a delete that had already closed the browsers and erased
   the transcript came straight back as an empty row, for as long as one tab
   stayed open on it. */
async function door(path, init){
  const r = await fetch(at(path), init);
  /* 410 and nothing else. Every other failure is worth trying again; this one
     is the only one that will never stop being true. */
  if(r.status === 410){ vanish(); throw new Error('this conversation was deleted'); }
  return r;
}

/* Deleted from the other tab, or from another window. The page says so and
   stops asking, in that order. It does NOT navigate anywhere: the column
   beside it still works, and where to go next is not this page's decision to
   make for somebody who is in the middle of reading. */
function vanish(){
  if(vanished) return;
  vanished = true;
  if(es) es.close();
  say('offline', 'deleted');
  orphan('err', 'This conversation was deleted. Nothing here is live any more '
         + '- open another one from Sessions, or start a new one.');
  /* Everything goes inert EXCEPT the way out. `inert` rather than `disabled`
     because these are subtrees and not single controls, and it takes them out
     of the pointer AND the tab order - a composer that answers the keyboard
     while it cannot send is the same lie in a different place. The column of
     sessions keeps its full contrast, because the sentence above tells the
     person to use it. */
  for(const box of [f, $('right'), $('fresh')]) box.inert = true;
  drawChats();
}

/* ⛔ ONE PLACE KNOWS WHAT TO DO WHEN A REQUEST DOES NOT ARRIVE. Six
   `fetch` calls had no failure path at all, and the sharpest of them is the
   stop button: this file says elsewhere that it is the only thing that ends a
   run which will not converge, and a press that never reached the server
   looked exactly like a press that did. `ask` returns the response when it
   worked and says so on the page when it did not. */
async function ask(path, body, whatFailed){
  try {
    const r = await door(path, body === undefined
      ? {method:'POST'}
      : {method:'POST', headers:{'Content-Type':'application/json'},
         body: JSON.stringify(body)});
    if(!r.ok) throw new Error('HTTP ' + r.status);
    return r;
  } catch(err){
    /* The one failure that already said its piece, and says it once. */
    if(!vanished) orphan('err', whatFailed + ' (' + err.message + ').');
    return null;
  }
}

/* ⛔ THE ONLY UNGUARDED DESTRUCTIVE CONTROL, AND IT SAT IN THE PERMANENT
   HEADER. Deleting a whole session - rarer, and behind a closed panel - asked
   first and named what went with it; clearing the transcript, which also
   makes the model forget everything it has been told, went on one click. The
   guard was on the wrong control. Named on the message, and named again on
   the button. */
fresh.onclick = () => {
  if(!confirm('Clear this conversation? The agent forgets everything you have told it. Its browsers stay open.')) return;
  ask('/chat/fresh', undefined, 'Could not clear this conversation');
};

halt.onclick = () => ask('/chat/stop', undefined,
                         'The stop did not reach the agent - it is still running');
f.onsubmit = (e) => {
  e.preventDefault();
  const t = i.value.trim();
  if(!t){ return; }
  i.value = ''; i.style.height = 'auto';
  if(busyNow){ setQueued(t); return; }
  send(t); paint();
};


/* ---- the browser pane ---- */
const right = $('right'), stateEl = $('state'), urlEl = $('url');
let frozen = false;

/* The second argument is the sentence behind a one-word state, shown on hover:
   an "error" with no reason is a thing to restart, an "error" that says the
   engine has no screencast is a thing to upgrade. */
/* ⛔ AND IT SAYS NOTHING WHEN IT WOULD ONLY REPEAT THE TAB NEXT TO IT.
   `Live` selected with the word `live` printed beside it is one fact twice,
   one of them in the place the eye goes for news. `idle`, `busy` and `error`
   are news, and they are now the only things that appear there; the dot keeps
   carrying live and frozen, which is what a dot is for. */
/* ⛔ HIDDEN FROM THE EYE, NOT FROM THE EAR. `hidden` is display:none, and a
   live region mutated inside a display:none subtree announces nothing - so the
   one transition that matters, live to error, was silent for a screen reader
   precisely because the word had been redundant a moment earlier. Off-screen
   instead: the eye sees the tab it repeats, the ear still hears the change. */
function say(s, why){ right.dataset.state = s; stateEl.textContent = s;
                      stateEl.classList.toggle('sr', s === 'live' || s === 'frozen');
                      stateEl.title = why || ''; }
async function reason(r){ try { return (await r.json()).error || ''; } catch(err) { return ''; } }

$('mode').onclick = (e) => {
  const b = e.target.closest('button'); if(!b) return;
  frozen = b.dataset.v === 'hold';
  for(const x of $('mode').children) x.setAttribute('aria-pressed', String(x === b));
  say(frozen ? 'frozen' : 'live');
};


/* ⛔ FRAMES A SECOND EACH, BY HOW MANY SCREENS ARE ON THE STAGE, and every one
   of these numbers is measured rather than chosen. Four real browsers, this
   same pipe, 2026-09-09: a frame costs 5 to 6 ms - not the 22 ms this file
   assumed for months - because the capture already runs inside the engine and
   the server hands over the latest picture instead of taking one. Polling as
   fast as the answers came back, each pane got about 20 frames a second
   whether there was one of them or four, so four panes moved 80 frames a
   second and an action still landed in 49 ms against 40 with a single pane.
   The pipe is the constraint at eight, not at four.

   So the budget is spent deliberately and not to the limit: one screen gets
   the 25 the engine is asked to produce, two get 20 each, four get 10 each -
   40 requests a second at most, about a quarter of what the pipe can carry,
   leaving the rest to the agent whose clicks share it. */
/* And it is paced on the screens that are ACTUALLY on the stage, never on
   the layout picked. Two browsers in a four-up layout are two browsers: the
   table this used to be gave them 10 frames a second each because the
   BUTTON said four, halving the thing the person asked for by reading the
   wrong number. The ceiling below is the measured budget - 40 requests a
   second, about a quarter of the pipe - and the top rate is what the engine
   is asked to produce, so asking for more would make frames to throw away. */
const LAYOUTS = [1, 2, 4];
const TOPRATE = 25, CEILING = 40;
const fps = (n) => Math.min(TOPRATE, Math.floor(CEILING / n));
const onScreen = () => Math.max(1, $('stage').children.length);
const pause = () => Math.round(1000 / (fps(onScreen()) * onScreen()));

/* One scheduler for the whole stage. It used to be two - a fast one for the
   single live pane and a slow one for the previews - and with a grid that
   would be two numbers describing one rate, which is how a pace stops being
   something anybody can read off the page. */
/* ⛔ THE SCHEDULER CANNOT BE ALLOWED TO DIE, and it died the first time this
   ran. `ageAll` reached for the age label on the placeholder cell, which has
   no caption, threw a TypeError, and because the throw was outside the fetch's
   try the timer at the bottom was never reached: the pump stopped for good, in
   silence, and what you see then is a pane that never updates - which reads as
   a server that has stopped answering rather than as a page with a bug in it.
   The body is a separate function now and the scheduling is the only thing
   this one does, so no defect inside a pass can take the loop with it. */
/* ⛔ NOTHING IS POLLED WHILE NOBODY IS LOOKING. Four loops ran flat out in
   a background tab: the frame pump at up to 40 requests a second, the address
   every two, the fleet every three, a preview every four hundred
   milliseconds. That budget was measured against what the pipe can carry
   while the AGENT is using it - and the agent keeps working when the tab is
   hidden, which is exactly when the page was still spending its share on
   pictures nobody could see. The loops keep their rhythm so a page coming
   back is one tick away from current. */
/* ⛔ AND NOTHING IS POLLED FOR A CONVERSATION THAT NO LONGER EXISTS, which is
   the same gate because it is the same question: is there anything here worth
   asking about. See `vanish`. */
const looking = () => !document.hidden && !vanished;

async function tick(){
  if(looking()){ try { await onePass(); } catch(err) {} }
  setTimeout(tick, pause());
}

/* And the moment it is looked at again, before the next tick lands. */
document.addEventListener('visibilitychange', () => {
  if(!looking()) return;
  onePass().catch(() => {});
  paintWhere(); drawFleet();
});

async function onePass(){
  const cells = [...$('stage').children];
  if(cells.length && !frozen){
    const cell = cells[turnOf % cells.length];
    turnOf++;
    const id = cell.dataset.id;
    if(cell.dataset.blank === '1'){ say(cells.length > 1 ? 'live' : 'idle'); }
    else try {
      const r = await door('/live/frame?b=' + encodeURIComponent(id)
                           + '&t=' + Date.now(), {cache:'no-store'});
      if(r.status === 204){ blank(cell, 'no page yet'); if(id === watched()) say('idle'); }
      else if(r.ok){
        const im = cell.querySelector('img'), blob = await r.blob(), old = im.src;
        im.src = URL.createObjectURL(blob);
        if(old && old.startsWith('blob:')) URL.revokeObjectURL(old);
        im.hidden = false;
        shapeFrom(cell, im);
        setState(cell, 'live');
        /* The monotonic clock, like the step timer and the thinking timer:
           a wall clock corrected by NTP or a DST step marks every screen
           stale at once, or hides one that really is. */
        cell.dataset.at = String(Math.round(performance.now()));
        if(id === watched()) say('live');
      }
      /* The capture could not answer, and the body says why: no frame within
         the server's wait (a minimised window is captured as nothing), or an
         engine without the screencast. The last frame stays on screen - a
         picture of where the browser was beats a blank pane - and the reason
         goes ON the screen rather than into a tooltip nobody hovers: this
         used to leave the same black rectangle as a pane that had simply not
         drawn yet, which is how a failure got to look like patience.
         
         And it is said for EVERY screen, not only the watched one. On a 2x2
         the three you are not following are exactly the ones whose silence
         you would otherwise have to guess at. */
      else {
        const why = r.status === 503 ? await reason(r) : '';
        setState(cell, 'error', 'the capture failed',
                 why || 'the server answered ' + r.status);
        if(id === watched()) say('error', why);
      }
    } catch(err){ if(id === watched()) say('offline'); }
    ageAll(cells);
  }
}

/* ⛔ THE BROWSER'S OWN CHROME IS CUT OFF THE TOP OF EVERY SCREEN. The capture
   is a picture of a window, and the tab strip and the address bar in it are a
   second address bar under the one this page already draws - the same fact
   twice, in the place where the eye goes for the page itself. Measured on
   three captures: 57/688, 43/515 and 57/688, so the chrome is 8.3% of the
   window's height and that is a proportion rather than a number of pixels.

   ⛔ AND IT IS CUT WITH A MARGIN IN PERCENT, NOT WITH MEASURED PIXELS. A
   percentage margin resolves against the containing block's width, so the
   chrome expressed as a fraction of the picture's WIDTH crops the same slice at
   any size, and the frame - which shrink-wraps the picture - ends up the
   cropped height by construction. The version before this one read the box with
   getBoundingClientRect on every frame, cached two numbers to avoid a reflow,
   and had to be told again on every resize. */
const CHROME = 0.083;
function shapeFrom(cell, im){
  if(!im.naturalWidth) return;
  const key = im.naturalWidth + 'x' + im.naturalHeight;
  if(cell.dataset.shape === key) return;
  cell.dataset.shape = key;
  const box = cell.querySelector('.frame');
  if(!box) return;
  const seen = im.naturalHeight * (1 - CHROME);
  box.style.setProperty('--cut',
    (CHROME * im.naturalHeight / im.naturalWidth * 100).toFixed(3) + '%');
  box.style.setProperty('--arn', (im.naturalWidth / seen).toFixed(4));
}

/* ⛔ ONE PLACE DECIDES WHAT A SCREEN IS SHOWING, because four states used to
   draw one black rectangle: no frame yet, no tab, stopped answering, and a
   capture that failed were pixel-identical, and all four read as a product
   that is broken. `data-blank` is a different question - whether to ASK for a
   picture at all - and it stays where it was: a browser with no tab is not
   asked, because asking spends a round trip to be told there is nothing. */
function setState(cell, state, title, detail){
  cell.dataset.state = state;
  const veil = cell.querySelector('.veil');
  if(!veil) return;
  veil.hidden = state === 'live';
  veil.textContent = '';
  if(state === 'live') return;
  if(state === 'waiting') veil.appendChild(el('span','pulse'));
  if(title) veil.appendChild(el('b', null, title));
  if(detail) veil.appendChild(el('span', null, detail));
}

/* ⛔ A PICTURE THAT HAS STOPPED MUST NOT READ AS ONE THAT IS RUNNING. On a
   healthy stage every screen is refreshed every 40 to 100 ms, so anything past
   a couple of seconds means that browser has stopped answering - and the last
   frame is still sitting there looking alive. Two seconds, because at four
   screens a round is 100 ms and a hiccup of three or four rounds is not news. */
function ageAll(cells){
  const now = performance.now();
  for(const c of cells){
    /* The empty stage has no stamp to write into, which is how this function
       killed the pump the first time it ran. */
    const lab = c.querySelector('.stamp');
    if(!lab) continue;
    const at2 = Number(c.dataset.at || 0), old = at2 && (now - at2) > 2000;
    /* ⛔ ONLY WHEN IT CHANGES. This runs at the end of every pass, so up to
       forty times a second, and it wrote three properties per cell whether or
       not anything had moved - about 480 DOM writes a second at four screens,
       for a label that is empty 99% of the time. Assigning '' to textContent
       still replaces the node's children. */
    const says = old ? Math.round((now - at2) / 1000) + 's' : '';
    if(lab.textContent !== says){
      lab.textContent = says;
      lab.title = old ? 'no frame for this long' : '';
    }
    /* Guarded separately: the text is unchanged between two fresh passes but
       the visibility still has to be right the first time. */
    if(lab.hidden !== !old) lab.hidden = !old;
    if(old && c.dataset.state === 'live') setState(c, 'stale');
    else if(!old && c.dataset.state === 'stale') setState(c, 'live');
  }
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
  ask('/live/select', {id: b.dataset.id}, 'Could not switch to that tab');
};

/* ⛔ THE ADDRESS FOLLOWS THE SCREEN YOU ARE LOOKING AT, and with four of them
   there is a case where no single address is the honest answer: nobody has
   picked one, so the bar would be showing whichever browser the agent happens
   to be in while three other pages sit beside it, unnamed. It says how many
   instead, and how to choose. Once a screen has been clicked the bar follows
   that one, at any layout. */
function severalOpen(n){
  urlEl.textContent = ''; urlEl.className = 'dim'; urlEl.title = '';
  urlEl.append(el('span', null, n + ' pages open'),
               el('span', 'hint', 'click a screen to follow it'));
}

/* ⛔ THE WORK AND THE TIMER ARE SEPARATE, for the reason the strip beside it
   was: changing the layout changes what the address should say, and there is
   nothing to wait for. While this was one function the bar kept the old answer
   until the next poll landed - two seconds showing one page's address over four
   screens. Calling `where` itself from a click would start a SECOND timer
   chain, which is how a pace stops being one number. */
async function where(){ if(looking()) await paintWhere(); setTimeout(where, 2000); }

async function paintWhere(){
  const many = grid > 1 && !pinned2 && onStage().length > 1;
  if(many){ severalOpen(onStage().length); paintTabs([]); }
  else try {
    const who = watched();
    /* ⛔ AND NEVER OF A BROWSER THAT IS NOT RUNNING. Asking for the tabs of a
       declared-but-stopped browser STARTS it - the server resolves the id and
       the registry wakes the engine - so clicking a stopped browser's chip
       spent 800 MB and seven seconds nobody asked for, and then kept asking
       every two seconds because the pin never cleared. The frame pump, the
       preview row and both cell builders already know this rule; this was the
       fifth place that had to and did not. */
    if(who && !fleet.some(b => b.id === who && b.running)){
      paintUrl(''); paintTabs([]); return;
    }
    /* `at`, inside `door`, is what adds the question mark, so the browser goes
       in as one too and it appends its own with an ampersand. */
    const r = await door(who ? '/live/tabs?b=' + encodeURIComponent(who)
                             : '/live/tabs', {cache:'no-store'});
    if(r.ok){ const j = await r.json(); paintUrl(j.url || ''); paintTabs(j.tabs); }
  } catch(err){}
}
/* ---------------- the session column ----------------
   Drawn from the server every time it changes rather than kept in step by hand:
   a name is set by the FIRST INSTRUCTION of a conversation, which happens on
   the server, so a column the page maintained locally would be right until
   somebody actually used a session. */
async function drawChats(){
  let rows = [];
  try { const r = await fetch('/sessions', {cache:'no-store'});
        if(r.ok) rows = (await r.json()).sessions || []; }
  catch(err){ return; }
  const box = $('chats');
  box.textContent = '';
  /* An empty column is a state, not a blank: on a first run there is exactly
     one conversation and it is this one, so the panel would otherwise open on
     nothing at all. */
  if(!rows.length){
    const none = el('p','none', 'No saved conversations yet. This one is saved '
                    + 'as soon as you send an instruction.');
    box.appendChild(none);
  }
  for(const s of rows){
    const row = el('div','chat');
    row.setAttribute('role','listitem');
    if(s.id === here) row.setAttribute('aria-current','true');
    const open = el('button', 'nm', s.name || s.id);
    open.type = 'button';

    /* Switching is a NAVIGATION, not a repaint: the transcript, the picture and
       the stream all belong to the conversation, and the server hands back the
       whole of it for an id. Rebuilding that by hand would be a second
       implementation of what a page load already does correctly. */
    open.onclick = () => { if(s.id !== here) location.search = '?s=' + encodeURIComponent(s.id); };
    open.ondblclick = () => renameChat(s.id, s.name || s.id);
    /* ⛔ AND A KEY, because a double click is not a keyboard path and nothing
       on the screen advertises it. F2 is what renames a thing in a list
       everywhere else on this machine. */
    open.onkeydown = (e) => { if(e.key === 'F2') renameChat(s.id, s.name || s.id); };
    open.title = (s.name || s.id) + ' - F2 to rename';
    row.appendChild(open);
    if(s.turns) row.appendChild(el('span','cnt', String(s.turns)));
    const kill = el('button','x','x');
    kill.type = 'button';
    kill.title = 'Delete this session and close its browsers';
    kill.setAttribute('aria-label', 'Delete ' + (s.name || s.id));
    kill.onclick = (e) => { e.stopPropagation(); forgetChat(s.id, s.name || s.id); };
    row.appendChild(kill);
    box.appendChild(row);
  }
}

/* ---------------- showing and hiding the column ----------------
   Closed until asked for, and it remembers: a panel that reopens itself every
   time the page loads is a panel that ignores what you told it. Per browser
   rather than per conversation - which panels you keep open is a habit, not a
   property of the work. */
const RAILKEY = 'aihawk.rail';
function showRail(open){
  $('rail').hidden = !open;
  $('railtab').setAttribute('aria-expanded', open ? 'true' : 'false');
  /* ⛔ AND NO aria-label ANY MORE. It used to say "Show sessions" / "Hide
     sessions", which was right while the control was three lines and nothing
     else. Now the button says Sessions in words, and an aria-label REPLACES
     that name: a screen reader would read a word that is not on the button,
     and somebody driving by voice who says "Sessions" would find nothing to
     click. The open state is already carried by aria-expanded, which is the
     attribute for it. Found by reading the live DOM after the change, not the
     source: removing the attribute from the markup left this line putting it
     back. */
  try { localStorage.setItem(RAILKEY, open ? '1' : '0'); } catch(err){}
  if(open) drawChats();
}
$('railtab').onclick = () => showRail($('rail').hidden);
try { showRail(localStorage.getItem(RAILKEY) === '1'); } catch(err){ showRail(false); }

async function renameChat(id, was){
  const name = prompt('Name this session', was);
  if(name === null) return;
  /* The server refuses a name that is only spaces and says so with
     `renamed:false`; without reading it the column simply redrew the old
     name, which reads as the rename having been ignored. */
  const r = await ask('/sessions/rename', {id, name}, 'Could not rename it');
  if(r && !(await r.json()).renamed){
    orphan('err', 'A session needs a name with something in it.');
  }
  drawChats();
}

async function forgetChat(id, name){
  /* The browsers go with it, and that is worth saying before it happens rather
     than after: a session can be holding eight logged-in engines. */
  if(!confirm('Delete "' + name + '"? Its conversation and its browsers go with it.')) return;
  /* ⛔ AND THE ANSWER IS READ. The server REFUSES to delete a session whose
     agent is mid-run, and answers 200 with `forgotten:false`. Ignoring the
     body meant confirming a delete, being navigated away, and leaving the
     session and its browsers exactly where they were: every visible signal
     said it had worked. */
  let gone = false;
  try {
    const r = await fetch('/sessions/forget', {method:'POST',
                          headers:{'Content-Type':'application/json'},
                          body: JSON.stringify({id})});
    gone = r.ok && (await r.json()).forgotten;
  } catch(err){ gone = false; }
  if(!gone){
    orphan('err', 'That session is still working, so it was not deleted. '
           + 'Stop its run first, then delete it.');
    drawChats();
    return;
  }
  if(id === here){ location.search = ''; return; }
  drawChats();
}

$('newchat').onclick = async (e) => {
  /* ⛔ AND ONLY ONCE. Two fast clicks made two sessions, the second
     navigation won, and the first stayed behind as an empty conversation
     nobody asked for and nobody would ever open. */
  const b = e.currentTarget;
  if(b.disabled) return;
  b.disabled = true;
  const r = await ask('/sessions/new', undefined, 'Could not start a session');
  if(!r){ b.disabled = false; return; }
  const j = await r.json();
  location.search = '?s=' + encodeURIComponent(j.id);
};

/* ---------------- the workspace ----------------
   ⛔ THE COST OF THE PREVIEWS DOES NOT GROW WITH THE NUMBER OF THEM, and that
   is the whole design rather than a detail. A frame costs about 22 ms on the
   pipe that ACTIONS share, and the pipe is serialised: eight panes each asking
   thirteen times a second would want 2.3 seconds of pipe per second, so the
   picture would be behind and every click would queue behind the pictures.

   So there is ONE live pane - the focused one, at the full rate, in `tick` -
   and ONE slow loop that refreshes a single other pane every 400 ms, taking
   them in turn. Seven others therefore refresh about every three seconds, and
   whether there are two panes or eight the previews cost the same two and a
   half requests a second. A loop per pane would have been the obvious way to
   write it and its cost would be the thing the measurement forbids. */
const SLOW_MS = 400;
let fleet = [], nextPane = 0, focusHere = '';
let grid = 1, turnOf = 0;

/* ⛔ TWO DIFFERENT THINGS, AND THEY USED TO BE ONE. `focusHere` is the browser
   the AGENT drives - it lives on the server and only the agent moves it, by
   being asked. `pinned2` is the pane the PERSON is looking at, which is this
   page's own business and nobody else's.

   They were the same value until somebody said everything should be commanded
   from the chat, and folding them together is what made clicking a pane a
   COMMAND. Now the big pane follows the agent, which is what you want while it
   works, and looking somewhere else is a choice that sticks until you undo it. */
let pinned2 = null;
const watched = () => pinned2 || focusHere;

function thumbFor(b){
  /* ⛔ A BROWSER WITH NO PICTURE DOES NOT GET A PICTURE FRAME. Six declared
     but stopped browsers drew six 168x133 cards, each with the words `not up`
     in the middle of an empty rectangle - a gallery of failures under the
     stage, 133px tall, in the place the running ones live. A thing with no
     image is a NAME: it gets a chip, and the row becomes a list of what this
     session holds. Clicking one still asks to watch it, exactly as before. */
  if(!b.running){
    const chip = document.createElement('button');
    chip.type = 'button'; chip.className = 'chip'; chip.dataset.id = b.id;
    chip.title = 'Watch ' + b.id;
    /* Clicking a chip changes what the address bar and the stage follow, and
       nothing said so: the identical control one row up, the preview card,
       has carried this mark from the start. */
    chip.setAttribute('aria-current', String(b.id === watched()));
    chip.append(el('span','off'), el('span','id', b.id));
    chip.onclick = () => watchThis(b.id);
    return chip;
  }
  const el2 = document.createElement('button');
  el2.type = 'button'; el2.className = 'thumb'; el2.dataset.id = b.id;
  el2.title = 'Watch ' + b.id;
  const pic = el('div','pic');
  /* Three states, not two, and the third is the one that read as a failure.
     A browser that is RUNNING WITH NO TAB cannot be captured - the engine
     answers "no such tab" - and asking anyway spends a round trip to be told
     so, then paints ERROR over something that is simply empty. The tabs are
     already in the answer this pane was built from, so the question is asked
     of data rather than of the pipe. */
  if((b.urls || []).length){
    const im = document.createElement('img'); im.alt = ''; pic.appendChild(im);
  } else {
    pic.appendChild(el('span', null, 'no tab open'));
  }
  const cap = el('div','cap');
  cap.appendChild(el('span','id', b.id));
  cap.appendChild(el('span','st', ''));
  if(b.id === focusHere){
    const dot = el('span','dot');
    dot.title = 'the agent is working here';
    cap.appendChild(dot);
  }
  el2.append(pic, cap);
  el2.onclick = () => watchThis(b.id);
  return el2;
}

/* ⛔ THE WAIT IS SHOWN, because it is seven to fourteen seconds - measured, and
   the eighth browser takes twice the first. An interface that goes quiet for
   fourteen seconds is the defect this project fixed elsewhere with the Thinking
   clock, and a pane that simply does not change is indistinguishable from a
   click that did nothing. */
/* Looking, not commanding. Clicking the pane you are already watching gives
   the view back to the agent, so there is a way out of a choice as well as in. */
function watchThis(id){
  pinned2 = (pinned2 === id) ? null : id;
  drawStage(); drawStrip(); paintWhere();
}

/* ---- the stage: one screen, or two, or four ----
   Which browsers are on it and in what order: the one being watched first,
   then the rest as the server lists them. So clicking any screen or any
   preview brings that browser to the front, and at one-up that means it fills
   the stage - which is what "click it and go to another screen" means. */
function onStage(){
  const w = watched();
  const live = fleet.filter(b => b.running);
  const first = live.filter(b => b.id === w);
  return first.concat(live.filter(b => b.id !== w)).slice(0, grid);
}

/* ⛔ A BLOB URL IS NOT GARBAGE-COLLECTED WITH ITS ELEMENT. Every frame is
   an object URL, and the two rebuild paths threw their <img> away without
   revoking: the stage redraws whenever the agent moves to another browser -
   which it does on its own - so a long run leaked one full window capture per
   pane per switch, held until the tab closes. */
function dropFrames(box){
  for(const im of box.querySelectorAll('img')){
    if(im.src && im.src.startsWith('blob:')) URL.revokeObjectURL(im.src);
  }
}

function blank(cell, why){
  const im = cell.querySelector('img'); if(im) im.hidden = true;
  setState(cell, 'nopage', why || 'no tab open',
           'ask the agent to open a page here');
  cell.dataset.blank = '1';
  cell.dataset.at = '';
}

/* One screen: a frame that wraps the picture, the name written on it, and
   whatever the picture cannot say written over it. */
function screenFor(b, current){
  const cell = document.createElement('button');
  cell.type = 'button'; cell.className = 'screen'; cell.dataset.id = b.id;
  cell.setAttribute('aria-current', String(current));
  cell.title = 'Watch ' + b.id;
  const box = el('div','frame');
  const im = document.createElement('img'); im.alt = ''; im.hidden = true;
  const tag = el('span','tag');
  tag.appendChild(el('span','id', b.id));
  /* The one the agent is driving, marked rather than selected: the person's
     eye and the agent's hand are two different things and the tag says both. */
  if(b.id === focusHere){
    const dot = el('span','dot');
    dot.title = 'the agent is working here';
    tag.appendChild(dot);
  }
  const stamp = el('span','stamp'); stamp.hidden = true;
  box.append(im, el('div','veil'), tag, stamp);
  cell.appendChild(box);
  /* Three states and not two, and the third is the one that reads as a
     failure: a browser that is RUNNING WITH NO TAB cannot be captured - the
     engine answers "no such tab" - and asking anyway spends a round trip to be
     told so. The tabs are already in the answer this was built from, so the
     question is asked of data rather than of the pipe. */
  const has = (b.urls || []).length > 0;
  if(has) setState(cell, 'waiting', 'waiting for the first frame');
  else { setState(cell, 'nopage', 'no tab open',
                  'ask the agent to open a page here');
         cell.dataset.blank = '1'; }
  cell.onclick = () => watchThis(b.id);
  return cell;
}

function drawStage(){
  const box = $('stage'), show = onStage();
  /* ⛔ THE TEMPLATE FOLLOWS THE CELLS THAT EXIST. Two running browsers in
     a four-up layout used to be laid on a 2x2 whose second row was empty, so
     each of them got half the height for nothing - the layout control is a
     ceiling on how many you watch at once, not a promise that there are that
     many. */
  box.dataset.grid = String(Math.min(grid, Math.max(1, show.length)));
  /* Only when the SET changes, or every poll would throw away the pictures and
     make the whole stage flash once a second for no new fact. */
  const sig = show.map(b => b.id + ((b.urls || []).length ? 'p' : '')
                            + (b.id === focusHere ? 'a' : '')).join(',')
              + '|' + grid + '|' + watched();
  if(box.dataset.sig === sig) return;
  box.dataset.sig = sig;
  dropFrames(box);
  box.textContent = '';
  turnOf = 0;
  /* ⛔ THE QUESTION IS 'IS THERE ANYTHING TO SEE', NOT 'ARE THERE
     BROWSERS'. With a browser running and no tab open, the bar stayed fully
     armed - address, Live/Frozen, layout picker and the word IDLE - over a
     stage whose own words were `no tab open`. A screen with nothing on it is
     the same empty room to the person looking at it. */
  const anything = show.some(b => (b.urls || []).length);
  right.dataset.empty = anything ? '' : '1';
  /* Not decoration: `inert` removes them from the tab order and from the
     accessibility tree, which is what 'this control cannot do anything right
     now' has to mean for somebody who is not using a mouse. */
  for(const box of [$('mode'), $('grid')]) box.inert = !anything;
  if(!show.length){
    /* An empty state that only reports the emptiness leaves the person to
       guess where the button is. There is no button - browsers are opened by
       asking - so this is the one place that has to say so, and to show the
       shape of the sentence that does it. */
    const cell = el('div','empty');
    cell.append(el('b', null, 'No browser open'),
                el('span', null, 'Ask in the chat and one opens here. There is no button for it, on purpose.'),
                el('code', null, 'open a browser and go to example.com'));
    box.appendChild(cell);
    return;
  }
  for(const b of show) box.appendChild(screenFor(b, b.id === watched()));
}

const GRIDKEY = 'aihawk.grid';
function setGrid(n){
  grid = n;
  for(const b of $('grid').children)
    b.setAttribute('aria-pressed', String(Number(b.dataset.n) === n));
  try { localStorage.setItem(GRIDKEY, String(n)); } catch(err){}
  drawStage(); drawStrip(); paintWhere();
}
$('grid').onclick = (e) => {
  const b = e.target.closest('button');
  if(b) setGrid(Number(b.dataset.n));
};

async function drawFleet(){
  let got = {browsers: []};
  try { const r = await door('/live/browsers', {cache:'no-store'});
        if(r.ok) got = await r.json(); }
  catch(err){ return; }
  fleet = got.browsers || [];
  focusHere = got.focus || '';
  drawStage();
  drawStrip();
}

/* ⛔ SEPARATE FROM THE POLL, because changing the layout changes what the strip
   holds and there is nothing to ask the server about it. While this lived
   inside `drawFleet` the strip stayed wrong until the next poll landed - up to
   three seconds showing browsers that were already on the stage, or missing the
   ones that had just left it. It reads the fleet that is already here. */
function drawStrip(){
  /* The strip carries what the stage does not, so at four-up with four
     browsers it is empty and at one-up with eight it holds seven. */
  const up = new Set(onStage().map(b => b.id));
  const others = fleet.filter(b => !up.has(b.id));
  const box = $('thumbs');
  /* Only when the SET changes. Redrawing on every poll would throw away the
     preview images and make the row flash once a second for no new fact. */
  const sig = others.map(b => b.id + (b.running ? '1' : '0') + (b.id === focusHere ? 'a' : ''))
                    .join(',') + '|' + watched() + '|' + grid;
  if(box.dataset.sig !== sig){
    box.dataset.sig = sig;
    dropFrames(box);
    box.textContent = '';
    for(const b of others) box.appendChild(thumbFor(b));
    nextPane = 0;
  }
  /* The row of previews disappears with one browser; the button to open
     another does not, or a session could never grow past its first. */
  box.hidden = others.length === 0;
}

async function slowTick(){
  const box = $('thumbs');
  /* Only running browsers are asked for a picture. A declared browser that has
     not started is not a slow pane, it is a browser that does not exist yet,
     and asking would START it - 800 MB and seven seconds to fill a thumbnail
     nobody asked for. Same rule the live pane follows. */
  const shown = [...box.children].filter(t => t.querySelector('img'));
  if(shown.length && looking()){
    const t = shown[nextPane % shown.length];
    nextPane++;
    try {
      const r = await door('/live/frame?b=' + encodeURIComponent(t.dataset.id)
                           + '&t=' + Date.now(), {cache:'no-store'});
      if(r.ok && r.status !== 204){
        const im = t.querySelector('img'), blob = await r.blob(), was = im.src;
        im.src = URL.createObjectURL(blob);
        if(was && was.startsWith('blob:')) URL.revokeObjectURL(was);
      }
    } catch(err){}
  }
  setTimeout(slowTick, SLOW_MS);
}

async function fleetPoll(){ if(looking()) await drawFleet(); setTimeout(fleetPoll, 3000); }

/* Whatever was waiting when the page went away comes back into the composer
   rather than into the queue: the run it was queued behind is over, so the
   honest place for it is where somebody can read it and press send. */
const waiting_text = queuedFromBefore();
if(waiting_text){ i.value = waiting_text; setQueued(null);
                  i.style.height = 'auto';
                  i.style.height = Math.min(i.scrollHeight, 200) + 'px'; }

/* ---- the split between the two panes ----
   ⛔ THE RATIO IS A PROPERTY OF THE TASK, NOT OF THIS FILE. Reading a long
   answer wants one, watching a form get filled wants another, and the ratio
   this page picks is right for neither for very long. The measured default is
   still a default - the conversation stops at its reading measure and the rest
   goes to the picture - and from there it is dragged, with the arrow keys, or
   double-clicked back to the default. Remembered per browser, because somebody
   who has set it once has said what they want.

   Everything here is a FUNCTION called from the boot line below: nothing at
   the top level of this script may depend on the order of the lines. */
const SPLITKEY = 'aihawk.split';

function splitTo(px, remember){
  /* The floor is the narrowest the conversation stays usable at; the ceiling
     leaves the browser pane enough to be a picture rather than a strip. Both
     are recomputed against the window, so a value dragged wide on a big
     monitor does not strand the right pane on a laptop. */
  const min = 420, max = Math.max(min, window.innerWidth - 480);
  const w = Math.round(Math.min(max, Math.max(min, px)));
  $('left').style.width = w + 'px';
  $('split').setAttribute('aria-valuenow', String(w));
  $('split').setAttribute('aria-valuemax', String(max));
  if(remember){ try { localStorage.setItem(SPLITKEY, String(w)); } catch(e) {} }
}

function splitReset(){
  try { localStorage.removeItem(SPLITKEY); } catch(e) {}
  $('left').style.width = '';
  $('split').setAttribute('aria-valuenow',
                          String(Math.round($('left').getBoundingClientRect().width)));
  /* The ceiling too: this is the FIRST-RUN path, so without it a range widget
     was announced with a floor and a value and no top for every new user. */
  $('split').setAttribute('aria-valuemax',
                          String(Math.max(420, window.innerWidth - 480)));
}

function splitter(){
  const bar = $('split');
  let saved = null;
  try { saved = localStorage.getItem(SPLITKEY); } catch(e) {}
  if(saved) splitTo(parseInt(saved, 10), false);
  else splitReset();

  bar.addEventListener('pointerdown', e => {
    bar.setPointerCapture(e.pointerId);
    bar.dataset.drag = '1';
    edge = $('left').getBoundingClientRect().left;
    /* ⛔ FOCUS BY HAND, BECAUSE THE LINE BELOW TAKES IT AWAY. preventDefault on
       pointerdown stops the drag from selecting the text beside it, and it also
       stops the browser from focusing what was pressed - so the separator could
       be dragged and then not moved with the arrow keys, which is the half of
       this control that exists for people who do not drag. Found by clicking
       it: nothing in the suite clicks. */
    bar.focus();
    e.preventDefault();
  });
  /* ⛔ ONE WRITE PER FRAME, AND ONE TO DISK PER DRAG. Every pointermove read
     the pane's box and then wrote a width and a value to localStorage: at a
     120 Hz pointer that is 120 forced layouts and 120 synchronous storage
     writes per second of dragging, for a number nobody reads until the drag
     ends. The left edge does not move while dragging, so it is measured once
     when the drag starts. */
  let edge = 0, pending = 0;
  bar.addEventListener('pointermove', e => {
    if(!bar.dataset.drag) return;
    const x = e.clientX;
    if(pending) return;
    pending = requestAnimationFrame(() => { pending = 0; splitTo(x - edge, false); });
  });
  bar.addEventListener('pointerup', e => {
    delete bar.dataset.drag;
    if(pending){ cancelAnimationFrame(pending); pending = 0; }
    /* Remembered once, at the end: the value it lands on is the choice. */
    splitTo($('left').getBoundingClientRect().width, true);
    bar.releasePointerCapture(e.pointerId);
  });
  bar.addEventListener('dblclick', splitReset);
  bar.addEventListener('keydown', e => {
    const step = e.shiftKey ? 64 : 16;
    const now = $('left').getBoundingClientRect().width;
    if(e.key === 'ArrowLeft'){ splitTo(now - step, true); e.preventDefault(); }
    else if(e.key === 'ArrowRight'){ splitTo(now + step, true); e.preventDefault(); }
    else if(e.key === 'Home' || e.key === 'Escape'){ splitReset(); e.preventDefault(); }
  });
  /* A width saved on a wide monitor is not a width on a laptop: put it back
     through the same clamp whenever the window changes. */
  window.addEventListener('resize', () => {
    if($('left').style.width) splitTo(parseFloat($('left').style.width), false);
  });
}

let sawGrid = null;
try { sawGrid = localStorage.getItem(GRIDKEY); } catch(err){}
setGrid(LAYOUTS.includes(Number(sawGrid)) ? Number(sawGrid) : 1);

paint(); listen(); tick(); where(); fleetPoll(); slowTick(); splitter();
if(!$('rail').hidden) drawChats();
