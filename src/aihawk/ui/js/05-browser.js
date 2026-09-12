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

/* ⛔ THE RE-ARM SITS IN A `finally`, AND IT IS NOT ONE BELT TOO MANY. A pump
   that re-arms AFTER the work dies for good on the first exception: it does
   not skip a turn, it stops. Measured 2026-09-11 on the address bar, where the
   inner `try` had been taken away while rewriting the function - and the same
   shape was already latent in two more pumps, whose `try` covered the fetch
   and not the lines around it. The empty `catch` keeps one turn quiet; the
   `finally` keeps the chain alive whatever happens, and together they take the
   question "did I remember the try?" out of every function a chain calls. */
async function tick(){
  try { if(looking()) await onePass(); }
  catch(err){}
  finally { setTimeout(tick, pause()); }
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
/* ⛔ THE TAB STRIP STOOD HERE AND IS GONE WITH THE TOOLS THAT FED IT. A
   browser drives one page, so there was never more than one chip to draw -
   this function already refused to draw a strip of one, calling it "chrome
   repeating the address bar directly beneath it". What it still carried was a
   CLICK: a way for the person to move the active page under the agent, which
   is the same second-control defect the open/close/focus/wake buttons were
   removed for. The address below is the half anybody read. */

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

/* ⛔ THE WORK AND THE TIMER ARE SEPARATE. Changing the layout changes what the address should say, and there is
   nothing to wait for. While this was one function the bar kept the old answer
   until the next poll landed - two seconds showing one page's address over four
   screens. Calling `where` itself from a click would start a SECOND timer
   chain, which is how a pace stops being one number. */
async function where(){
  try { if(looking()) await paintWhere(); }
  catch(err){}
  finally { setTimeout(where, 2000); }
}

/* Which url the address bar says, given the rows the workspace already has.

   ⛔ PURE, AND THAT IS THE POINT: it is the one piece of this file a test can
   run without a browser, and the two ways of getting it wrong both look
   exactly right from the outside. Reading `urls[0]` agrees with `url` until a
   site opens a second page, and answering the FOCUSED row ignores a pinned
   pane, so the bar names a browser nobody is looking at.

   ⛔ AND IT USED TO BE A ROUTE. `/live/address` asked `browser_list` a second
   time on a second timer for a field these rows already carry - a round trip
   every two seconds for something in memory here, and an answer that went
   stale the moment somebody pinned a pane, because the browser being watched
   is a fact of this page and not of the server. */
function addressOf(rows, who){
  const list = Array.isArray(rows) ? rows : [];
  const row = list.find(b => b && (who ? b.id === who : b.focused));
  return (row && row.url) || '';
}

function paintWhere(){
  const many = grid > 1 && !pinned2 && onStage().length > 1;
  if(many){ severalOpen(onStage().length); return; }
  const who = watched();
  /* A browser that is not running has no address, and `fleet` already says
     which ones are running, so this is the difference between a blank bar
     and a stale one. It is NO LONGER A SAFETY RULE here, and it was: when
     this asked the tab tool, that tool resolved its browser through `ready`
     and so woke a stopped one - 800 MB and seven seconds for a chip nobody
     clicked twice. Nothing is asked from here at all now. The safety version
     of the rule still binds the frame pump, the preview row and both cell
     builders, which ask tools that DO wake. */
  if(who && !fleet.some(b => b.id === who && b.running)){ paintUrl(''); return; }
  paintUrl(addressOf(fleet, who));
}
