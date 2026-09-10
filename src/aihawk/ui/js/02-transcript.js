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

