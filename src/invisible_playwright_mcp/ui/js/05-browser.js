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
/* ⛔ AND IT ONLY SPEAKS WHEN SOMETHING CHANGED. This rewrote a live region 25
   times a second while a browser was being watched, because the frame pump
   calls it on every pass. A screen reader announces every one of those writes:
   the word `live`, forever, with the queue never emptying, so the one
   transition that matters - live to error - could never be reached. Anybody
   using this product by ear was locked out of it while it worked.

   Guarded here rather than at the pump, because there are eight callers and
   the fact "the state changed" is one fact. The early return is safe because
   all three writes below are functions of the two arguments. */
/* ⛔ AGAINST WHAT THIS FUNCTION HAS DRAWN, NOT AGAINST THE ATTRIBUTE. The first
   version compared with `right.dataset.state`, which the MARKUP declares as
   `idle` before any script runs - so the very first call was swallowed as a
   repeat and the word never got the class that hides it. Caught by opening the
   page: IDLE in bright capitals in the corner of an empty room, which is the
   exact thing a rule deleted in the same change had been there to prevent. A
   guard that reads the DOM cannot tell "already drawn" from "never drawn". */
let shown = null;
function say(s, why){ if(shown === s && stateEl.title === (why || '')) return;
                      shown = s;
                      right.dataset.state = s; stateEl.textContent = s;
                      stateEl.classList.toggle('sr', s === 'live' || s === 'frozen' || s === 'idle');
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

   So the budget is spent deliberately and not to the limit: one screen gets
   the 25 the engine is asked to produce, two get 20 each - 40 requests a
   second at most, about a quarter of what the pipe can carry, leaving the
   rest to the agent whose clicks share it. */
/* And it is paced on the screens that are ACTUALLY on the stage, never on
   a layout: two browsers are two browsers. The ceiling below is the measured
   budget - 40 requests a second, about a quarter of the pipe - and the top
   rate is what the engine is asked to produce, so asking for more would make
   frames to throw away. */
const TOPRATE = 25, CEILING = 40;
const fps = (n) => Math.min(TOPRATE, Math.floor(CEILING / n));
const onScreen = () => Math.max(1, $('stage').children.length);
const pause = () => Math.round(1000 / (fps(onScreen()) * onScreen()));

/* ⛔ NOTHING IS POLLED WHILE NOBODY IS LOOKING. The loops ran flat out in a
   background tab: the frame pump at up to 40 requests a second, the address
   every two seconds, the fleet every three. That budget was measured against
   what the pipe can carry while the AGENT is using it - and the agent keeps
   working when the tab is hidden, which is exactly when the page was still
   spending its share on pictures nobody could see. The loops keep their rhythm
   so a page coming back is one tick away from current. */
/* ⛔ AND NOTHING IS POLLED FOR A CONVERSATION THAT NO LONGER EXISTS, which is
   the same gate because it is the same question: is there anything here worth
   asking about. See `vanish`. */
const looking = () => !document.hidden && !vanished;

/* ⛔ ONE SHAPE FOR EVERY PUMP ON THIS PAGE, AND THE SHAPE IS THE WHOLE
   CORRECTION. A pump that re-arms AFTER the work dies for good on the first
   exception: it does not skip a turn, it stops - and what you see then is a
   pane that never updates, which reads as a server that has stopped answering
   rather than as a page with a bug in it. Measured 2026-09-11 on the address
   bar, where the inner `try` had been taken away while rewriting the function,
   and the same shape was latent in two more pumps whose `try` covered the
   fetch and not the lines around it. So the re-arm sits in a `finally`: the
   empty `catch` keeps one turn quiet and the `finally` keeps the chain alive
   whatever the pass did.

   Written ONCE. Until 0.52.0 this shape was copied out four times, each copy a
   place to forget the `try` again, and the question "did I remember it?" was
   asked of every pass a pump called. `pause` is a number, or a function of the
   moment for the frame pump, whose pace follows how many screens are on the
   stage. The pass runs only while somebody is looking, see above. */
function every(pause, pass){
  (async function turn(){
    try { if(looking()) await pass(); }
    catch(err){}
    finally { setTimeout(turn, typeof pause === 'function' ? pause() : pause); }
  })();
}

/* And the moment it is looked at again, before the next tick lands. */
document.addEventListener('visibilitychange', () => {
  if(!looking()) return;
  onePass().catch(() => {});
  paintWhere(); drawFleet();
});

/* ⛔ ONLY THE CELLS THAT ARE SCREENS. The empty stage holds the placeholder
   that says "No browser open", and it is a child like any other: until 0.52.0
   this pump took it in turn, read no id off it, and asked the server for
   `/live/frame?b=undefined` twenty-five times a second - a tool call each,
   refused each, for a stage with nothing on it. Measured by starting the
   product and reading its log. */
async function onePass(){
  const cells = [...$('stage').children].filter(c => c.dataset.id);
  if(cells.length && !frozen){
    const cell = cells[stage.turn % cells.length];
    stage.turn++;
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

         And it is said for EVERY screen, not only the watched one: the one
         you are not following is exactly the one whose silence you would
         otherwise have to guess at. */
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
   healthy stage every screen is refreshed every 40 to 50 ms, so anything past
   a couple of seconds means that browser has stopped answering - and the last
   frame is still sitting there looking alive. Two seconds, because a hiccup
   of a few rounds is not news. */
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
       not anything had moved - for a label that is empty 99% of the time.
       Assigning '' to textContent still replaces the node's children. */
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
/* ⛔ THE TAB STRIP STOOD HERE AND IS GONE WITH THE TOOLS THAT FED IT. A
   browser drives one page, so there was never more than one chip to draw -
   this function already refused to draw a strip of one, calling it "chrome
   repeating the address bar directly beneath it". What it still carried was a
   CLICK: a way for the person to move the active page under the agent, which
   is the same second-control defect the open/close/focus/wake buttons were
   removed for. The address below is the half anybody read. */

/* ⛔ THE ADDRESS FOLLOWS THE SCREEN YOU ARE LOOKING AT, and with two of them
   there is a case where no single address is the honest answer: nobody has
   picked one, so the bar would be showing whichever browser the agent happens
   to be in while the other page sits beside it, unnamed. It says how many
   instead, and how to choose. Once a screen has been clicked the bar follows
   that one. */
function severalOpen(n){
  urlEl.textContent = ''; urlEl.className = 'dim'; urlEl.title = '';
  urlEl.append(el('span', null, n + ' pages open'),
               el('span', 'hint', 'click a screen to follow it'));
}

/* Which url the address bar says, given the rows the workspace already has.

   ⛔ PURE, AND THAT IS THE POINT: it is the one piece of this file a test can
   run without a browser, and the two ways of getting it wrong both look
   exactly right from the outside. Reading `urls[0]` agrees with `url` until a
   site opens a second page, and answering the FOCUSED row ignores a pinned
   pane, so the bar names a browser nobody is looking at.

   ⛔ IT ASKS FOR ONE BROWSER BY NAME AND HAS NO OTHER WAY IN. It used to fall
   back on a `focused` flag carried by every row, which was the row's id
   compared against the `focus` beside it - the same fact twice on one wire,
   and the flag went in 0.55.0. Who is being watched is `pinned || focus` and
   that is decided one line up, in the caller; with nobody to watch there is
   no address, which is what an empty answer says.

   ⛔ AND IT USED TO BE A ROUTE. `/live/address` asked `browser_list` a second
   time on a second timer for a field these rows already carry - a round trip
   every two seconds for something in memory here, and an answer that went
   stale the moment somebody pinned a pane, because the browser being watched
   is a fact of this page and not of the server. */
function addressOf(rows, who){
  if(!who) return '';
  const list = Array.isArray(rows) ? rows : [];
  const row = list.find(b => b && b.id === who);
  return (row && row.url) || '';
}

/* ⛔ THE WORK AND THE TIMER ARE SEPARATE. Clicking a screen changes what the
   address should say, and there is nothing to wait for; while this was one
   function with its pump the bar kept the old answer until the next poll
   landed. So this is a pass, called from the click and from its pump alike,
   and it is scheduled from exactly one place. */
function paintWhere(){
  const many = stage.grid > 1 && !stage.pinned && onStage().length > 1;
  if(many){ severalOpen(onStage().length); return; }
  const who = watched();
  /* A browser the fleet does not hold has no address, which is the
     difference between a blank bar and a stale one: the pinned pane survives
     the browser it was pinned to, so `watched()` can name one that has been
     closed or has gone. It asked `b.running` until 0.54.0, when that flag
     went - the rows are the open browsers, so being in them IS the question.
     It is no longer a SAFETY rule either: nothing is asked from here at all,
     where asking the tab tool once woke a stopped browser for a chip nobody
     clicked twice. */
  if(who && !stage.fleet.some(b => b.id === who)){ paintUrl(''); return; }
  paintUrl(addressOf(stage.fleet, who));
}
