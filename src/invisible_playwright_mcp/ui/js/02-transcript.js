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
// The value here is an UNSENT DRAFT: `carried` is what stops the rename
// from throwing away text somebody typed.
const qkey = (who) => STORE + 'queued.' + (who || here);
/* ⛔ AND IT GOES WHEN THE CONVERSATION GOES. Deleting a conversation erased
   its transcript on the server and its browsers with it, and left the sentence
   somebody had typed into it sitting in this browser's storage - one key per
   conversation that ever had one, kept for as long as the browser does, for
   something nobody can ever reach again. */
function dropQueued(who){
  try { localStorage.removeItem(qkey(who)); } catch(err){}
}
function setQueued(text){
  queued = text || null;
  try {
    if(queued) localStorage.setItem(qkey(), queued);
    else localStorage.removeItem(qkey());
  } catch(err){}
  paint();
}
function queuedFromBefore(){
  return carried(qkey());
}
let pend = null, pendTimer = 0;

const dur = ms => ms < 1000 ? Math.round(ms) + 'ms' : (ms/1000).toFixed(1) + 's';

/* ⛔ THE GUIDANCE IS KEPT, BECAUSE CLEAR USED TO DELETE IT FOR GOOD. It lives
   in the markup and the first turn removes it, which is right - and `wipe()`
   then left an empty pane with nothing in it at all, on a page whose entire
   first-run explanation was those three sentences. Press Clear on a finished
   conversation and the product forgot how to introduce itself until the tab was
   reloaded.

   A clone taken before anything can remove it, rather than the same words
   written a second time in a builder: one declaration, and it is the markup. */
const hintNode = $('hint').cloneNode(true);

function newTurn(){
  const hint = $('hint'); if(hint) hint.remove();
  n = 0; turn = el('section','turn'); thread.appendChild(turn); return turn;
}
/* The one thing that knows where the bottom is. Two callers ask for it - a row
   arriving while the reader is following, and the way back being pressed - and
   before this they were two different expressions in two files. */
function toBottom(){ log.scrollTop = log.scrollHeight; }

/* ⛔ THE TRANSCRIPT CHANGED SIZE, WHICH IS THE ONLY MOMENT THE BOTTOM IS
   KNOWABLE. Wired to a ResizeObserver on the thread in `03-which-session.js`.

   Scheduling the scroll instead - on a frame, after appending - was tried and
   measured, and it is wrong for a reason no choice of target can fix: the
   callback runs against the layout of the frame it is in, and that layout can
   still be the one from before the rows arrived. On a reopened conversation,
   inside that callback, the DOM already held all 65 rows while the scroller
   still reported a height of 808 - its own window - so it scrolled to 808,
   which clamps to zero, and the conversation opened at the TOP with 2084 px
   below, three times out of three. `scrollIntoView` on the sentinel reads the
   same layout and lands in the same place. Checking whether the scroll arrived
   does not help either, because the check reads that layout too and concludes
   it did.

   A resize observation is delivered AFTER layout, so the height it reports is
   the one the rows make. It also covers what an append-time hook never could:
   a picture that finishes loading, a font that swaps, a row expanded, the
   window resized. One trigger for every way the transcript can grow. */
function grew(){ if($('jump').hidden) toBottom(); }

/* ⛔ WHETHER THE READER IS FOLLOWING IS ASKED OF THE OBSERVER, AND IT IS THE
   ONLY THING THAT KNOWS. `#jump` is hidden exactly when `#anchor` is on screen,
   which is exactly when the reader is at the bottom, and that is already
   computed continuously in `03-which-session.js`. This function used to read it
   for the counter and nothing else, while the SCROLLING was decided by a
   one-shot latch that fired 150 ms after the first event and never again.

   Measured on this page before the change: the view followed for 24 rows and
   then fell behind by exactly the height added, 623 px per 20 rows, forever.
   It had not stopped following - it had never followed. For those 24 rows the
   transcript was shorter than the window, so there was nothing to scroll and
   the latch had fired against an empty page; by the time content passed the
   fold, `#anchor` was below it, and the stylesheet cannot choose an anchor it
   cannot see. Nudging the scroller by one pixel does not wake it either: the
   anchor has to be ON SCREEN, which is what made "the sentinel pins the view"
   read as a mechanism when it is only an assist for a bottom something else
   has to reach first.

   The answer is the OBSERVER'S and not geometry read here, and that is the
   load-bearing part: an IntersectionObserver delivers asynchronously, so
   `hidden` describes the moment before this row whichever side of the append it
   is read on - which is the question being asked. It is written above the
   append so that a reader does not have to know that to trust the line.

   ⛔ MOVING IT BELOW THE APPEND WAS RUN AS A KNOWN-BAD AND SURVIVED, correctly:
   the two orderings are the same behaviour. Said here because a comment
   claiming the placement is load-bearing would send the next reader looking for
   a defect that is not there. What IS load-bearing is asking the observer at
   all: recomputing the geometry on this line would answer about the row that
   has just landed instead of about the reader. */
function put(node, replay){ if(!turn) newTurn(); if(replay) node.dataset.replay = '1';
                            const following = $('jump').hidden;
                            turn.appendChild(node);
                            /* Counted only while the way back is on screen,
                               which is exactly when it is worth counting. */
                            if(!following){ behind++; paintJump(); } }

/* ⛔ WHILE A READER IS SCROLLED UP, NOTHING ON SCREEN SAYS THE AGENT IS ALIVE.
   Every signal of life is drawn at the BOTTOM of the transcript - the clock on
   the running step, the `Thinking` row, the time climbing - which is precisely
   where the reader is not when they need one. Measured on a real run: the
   agent took 59 steps while the owner watched the first 14, with nothing on
   screen to say the thing was working.

   The count goes on the one control that IS on screen, because that is where
   the eye already is. Not a live region: the transcript is already one, so a
   screen reader hears every row arrive. This is for the eye. */
function paintJump(){
  $('jump').textContent = behind ? 'jump to latest - ' + behind + ' new'
                                 : 'jump to latest';
}
function seen(){ behind = 0; paintJump(); }

/* The narration is held for one event, so a sentence followed by tool calls
   reads as their lead-in and a sentence with nothing after it reads as the
   answer. One event of lookahead is all a stream allows and all this needs. */
function flush(asAnswer, replay){
  if(hold === null) return;
  const text = hold.replace(LEAD,'').replace(/^\w/, c => c.toUpperCase());
  hold = null;
  /* ⛔ A LEAD-IN IS NOT DRAWN AT ALL, AND THAT IS A DECISION. The owner,
     reading a run whose narration was in Italian, translated here: `Site
     open. Let me see what is on the home page.` above the row that says
     `Inspected`, then `I will close the cookie banner first` above the row
     that says `Clicked`. The sentence announces what the row below it
     states, so the column carried three lines to say one thing, and the
     things worth reading were spaced out by the things that were not.

     What it costs, said plainly rather than discovered later: a lead-in
     sometimes carries a measurement that appears nowhere else - `474
     products, I will look at the LEGO collection` - and that number is now
     off the page. The text is NOT lost: `ChatService.emit` keeps every event
     in the history and the saved file has it, so this is a drawing decision
     and a later one can show it again without anything to recover.

     The distinction is exact and costs no guessing: `asAnswer` is true only
     when the run went idle holding this text, which is the message the model
     sent with no tool calls. Every other path through the dispatcher is a
     sentence that had something after it. */
  if(!asAnswer) return;
  const box = el('div', 'answer');
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

/* ⛔ THE THREE THINGS THAT SETTLE A STEP, IN ONE PLACE, because the end of a
   turn has to settle a step that nobody landed. Press Stop with a click in
   flight and no result ever arrives, so that row kept `data-state="run"` and
   its breathing dot for the life of the page, under a verb in the present
   tense saying it was still happening.

   ⛔ AND THE OUTCOME IS A WORD, NOT A TINT. A failed row was marked by colour
   alone - `--err` mixed at 8% against the row, 1.12:1 - and carried the SAME
   present-tense verb as a row still running, so scrolling back through a ten
   minute run to find what went wrong there was nothing to look for. In
   greyscale, or for anybody who does not separate amber from salmon, the
   failure was not marked at all.

   Past tense only when it finished. `Navigated <address>` on a row that never
   navigated is the worst kind of line a log can carry. */
function close(d, state, word){
  clearInterval(timer);
  const s = d.firstElementChild;
  d.dataset.state = state;
  s.querySelector('.lab b').textContent =
    (VERB[d.dataset.name] || ['Calling','Called'])[state === 'ok' ? 1 : 0];
  if(word) s.querySelector('.lab').append(' ', el('span','mark', word));
  return s;
}

/* Whether a result says nothing the row does not already say: the settled
   verb plus the target, compared by words, case and a trailing full stop
   aside. Read from the row itself rather than recomputed from the tool name,
   so the two cannot disagree about what the row says. */
function echoes(s, text){
  const lab = s.querySelector('.lab');
  const code = lab.querySelector('code');
  const said = lab.querySelector('b').textContent + ' ' + (code ? code.textContent : '');
  const flat = (x) => { x = x.toLowerCase().split(' ').filter(Boolean).join(' ');
                        return x.endsWith('.') ? x.slice(0, -1) : x; };
  return flat(text) === flat(said);
}

/* A result or an error folds into the step above it, which is what makes a step
   one unit carrying its target, its timing, its state and its own disclosure. */
function land(kind, text, replay){
  clearInterval(timer);
  if(!live) return orphan(kind, text, replay);
  const d = live;
  live = null;
  const s = close(d, kind === 'err' ? 'err' : 'ok', kind === 'err' ? 'failed' : '');
  if(!replay) s.lastElementChild.textContent = dur(performance.now() - t0);
  /* Output that fits goes ON the row and the row stops being expandable. In an
     ordinary run most rows are then one line with the answer already visible,
     which is the difference between a list and a stack of accordions.
     The row says its whole result on hover whatever it does with it, so a
     result cut by the ellipsis is readable without opening anything - and
     hovering is a path for a pointer and for nobody else, which is why the
     disclosure below is decided by measurement and not by a guess. */
  const lab = s.querySelector('.lab');
  lab.title = text.slice(0, 400);
  const oneLine = text.indexOf('\n') < 0;
  /* ⛔ NOT WHEN IT ONLY REPEATS THE ROW. A click answers `clicked <target>`
     and the row already reads `Clicked <target>`, so the most frequent line in
     the product said the same four words twice - eighteen times in a row on a
     real run, and in the owner's own screenshot. An echo is not information. A
     result that says anything more than the row does, an address with a
     status, a heading that was read, is still shown. */
  if(oneLine && !echoes(s, text)) lab.append(' ', el('span','inline', text));
  /* Anything with a line break in it cannot go on a row at all. */
  if(!oneLine) return d.appendChild(el('pre','out', text));
  /* ⛔ AND IT LEAVES THE TAB ORDER WITH THE SAME STATEMENT THAT DECIDES IT HAS
     NO BODY. Every finished step stayed a focusable disclosure, so a keyboard
     user crossing a fifty step run pressed Tab fifty times through rows where
     Enter opens nothing - the transcript between the sessions button and the
     composer was a minefield of controls that do not control anything. Still
     reachable by click and in a screen reader's browse mode; only the
     sequential order gives it up.

     Assumed here and corrected by the measurement below, so the common row -
     the one that fits - never grows a chevron for a frame and then loses it. */
  d.dataset.body = 'none'; s.tabIndex = -1;
  fitOrOpen(d, s, lab, text);
}

/* ⛔ THE ROW IS MEASURED, NOT COUNTED. The threshold was a number of CHARACTERS
   of the RESULT, while the row also carries the verb and the argument, in a
   track the stylesheet sizes: measured 266px on some rows and 376 on others,
   against the 416 the old comment assumed. So a row could be cut off by the
   ellipsis AND have had its disclosure removed for being short. Measured on a
   real transcript of 82 rows: 39 had no chevron, 29 were cut, and THIRTEEN were
   both - their text reachable only by resting a pointer on it, which is no path
   at all from a keyboard or a touchscreen.

   The same defect was recorded at 120 characters and the fix was to lower the
   number. Lowering it reduced the count and could not remove it, because the
   criterion is wrong in KIND: a count in characters standing in for a fit in
   pixels. The row is asked the same question the eye asks.

   ⛔ AND THE READS ARE BATCHED, WHICH IS WHY THIS IS NOT A MEASUREMENT PER ROW.
   Reading `scrollWidth` flushes layout, and a row is appended just before, so
   measuring inside `land` would force one full layout per row - which a replay
   of a long transcript pays all at once on load. Every read happens first and
   every write after, so a burst of two hundred rows costs ONE layout instead of
   two hundred. */
let toFit = [];
function fitOrOpen(d, s, lab, text){
  toFit.push({d: d, s: s, lab: lab, text: text});
  if(toFit.length > 1) return;
  requestAnimationFrame(() => {
    const rows = toFit; toFit = [];
    for(const r of rows) r.fits = r.lab.scrollWidth <= r.lab.clientWidth;
    for(const r of rows){
      if(r.fits) continue;
      delete r.d.dataset.body;
      r.s.removeAttribute('tabindex');
      r.d.appendChild(el('pre','out', r.text));
    }
  });
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

/* ⛔ `settleOnce` STOOD HERE AND IT IS GONE, NOT REPAIRED. It scrolled once,
   150 ms after the first event, and latched `pinned` so that nothing would ever
   scroll again - the reasoning being that the stylesheet would hold the bottom
   from then on and a reader who had scrolled up would never be yanked.

   The second half of that was right and is kept, by asking the observer instead
   of a latch. The first half was not: the one scroll it allowed happened while
   the transcript was still shorter than the window, where there is nothing to
   scroll, and a timer cannot be at the moment content first passes the fold
   because that moment is not 150 ms after anything.

   What replaces it is not another scroll somewhere else: it is that `put` -
   the one function every row goes through - asks whether the reader is
   following and acts on the answer. A latch that can only be set is not a
   question anybody can ask twice. */

