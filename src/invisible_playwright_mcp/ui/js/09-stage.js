/* ---- the stage: one screen, or two ----
   The browsers the server lists, in the order it lists them. */
/* ⛔ NO FILTER ON THE ROWS: EVERY BROWSER THE SERVER LISTS IS ONE THAT IS
   OPEN. There used to be a `running` flag and this filtered on it, from the
   days when a session could hold a browser that was declared and not
   started. Since 0.53.0 there is no such thing, the flag was `true` on every
   row the server could produce, and it went in 0.54.0 - so a filter here
   would be a branch on a case the answer cannot contain. */
/* ⛔ AND NO REORDERING EITHER, WHICH WENT IN 0.55.0 WITH THE REASON IT WAS
   WRITTEN FOR. It used to put the watched browser first so that clicking a
   screen brought it to the front, which meant something while a session held
   up to eight of them and the stage showed fewer. It cannot now: the stage
   shows two screens exactly when there are two browsers, so the only thing
   the sort could still do was decide which of two equal cells sat on the
   left - and the moment `focus` became a real fact, in this same version,
   that would have swapped the two panes under the eye of whoever was
   watching every time the agent moved between them. The watched screen is
   MARKED, not moved. */
function onStage(){
  return stage.fleet.slice(0, stage.grid);
}

/* ⛔ A BLOB URL IS NOT GARBAGE-COLLECTED WITH ITS ELEMENT. Every frame is
   an object URL, and the rebuild path threw its <img> away without revoking:
   the stage redraws whenever the agent moves to another browser - which it
   does on its own - so a long run leaked one full window capture per pane per
   switch, held until the tab closes. */
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
  /* The NAME is the action and the state is the description. With the name
     taken from the contents, a screen reader heard the address, the tag and
     the veil's sentence run together, and `title` was never the name. */
  cell.title = 'Watch ' + b.id;
  cell.setAttribute('aria-label', 'Watch ' + b.id);
  const box = el('div','frame');
  const im = document.createElement('img'); im.alt = ''; im.hidden = true;
  const tag = el('span','tag');
  tag.appendChild(el('span','id', b.id));
  /* The one the agent is driving, marked rather than selected: the person's
     eye and the agent's hand are two different things and the tag says both. */
  if(b.id === stage.focus){
    const dot = el('span','dot');
    dot.title = 'the agent is working here';
    tag.appendChild(dot);
  }
  const stamp = el('span','stamp'); stamp.hidden = true;
  const veil = el('div','veil'); veil.id = 'veil-' + b.id;
  cell.setAttribute('aria-describedby', veil.id);
  box.append(im, veil, tag, stamp);
  cell.appendChild(box);
  /* Three states and not two, and the third is the one that reads as a
     failure: a browser that is RUNNING WITH NO TAB cannot be captured - the
     engine refuses, saying it has no page open - and asking anyway spends a
     round trip to be told so. The tabs are already in the answer this was
     built from, so the question is asked of data rather than of the pipe. */
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
  /* The template follows the cells that exist: `grid` is derived from the
     running browsers in `drawFleet`, so this is one or two, never a promise of
     more cells than there are. */
  box.dataset.grid = String(Math.min(stage.grid, Math.max(1, show.length)));
  /* ⛔ AND THE SCREEN THE PERSON CHOSE GETS THE ROOM. Clicking a screen marked
     it and left it exactly the size of the other one, so with two browsers open
     you always watched at half width - and reading a form the agent is filling
     is most of what watching IS. The other screen stays on the stage rather
     than going away: the agent may move to it at any moment, and losing sight
     of that is worse than a narrow picture.

     Only when the PERSON has pinned one. The layout never moves on its own,
     which is the same line this page draws everywhere between the agent's hand
     and the reader's eye. */
  const big = stage.pinned ? show.findIndex(b => b.id === stage.pinned) + 1 : 0;
  if(big) box.dataset.big = String(big); else delete box.dataset.big;
  /* Only when the SET changes, or every poll would throw away the pictures and
     make the whole stage flash once a second for no new fact. */
  const sig = show.map(b => b.id + ((b.urls || []).length ? 'p' : '')
                            + (b.id === stage.focus ? 'a' : '')).join(',')
              + '|' + stage.grid + '|' + watched();
  if(box.dataset.sig === sig) return;
  box.dataset.sig = sig;
  dropFrames(box);
  box.textContent = '';
  stage.turn = 0;
  /* ⛔ THE QUESTION IS 'IS THERE ANYTHING TO SEE', NOT 'ARE THERE
     BROWSERS'. With a browser running and no tab open, the bar stayed fully
     armed - address, Live/Frozen and the word IDLE - over a stage whose own
     words were `no tab open`. A screen with nothing on it is the same empty
     room to the person looking at it. */
  const anything = show.some(b => (b.urls || []).length);
  right.dataset.empty = anything ? '' : '1';
  /* Not decoration: `inert` removes them from the tab order and from the
     accessibility tree, which is what 'this control cannot do anything right
     now' has to mean for somebody who is not using a mouse. */
  $('mode').inert = !anything;
  if(!show.length){
    /* An empty state that only reports the emptiness leaves the person to
       guess where the button is. There is no button - browsers are opened by
       asking - so this is the one place that has to say so, and to show the
       shape of the sentence that does it. */
    box.appendChild(emptyCell.cloneNode(true));
    return;
  }
  for(const b of show) box.appendChild(screenFor(b, b.id === watched()));
}

/* Taken before anything can empty the stage: the same three lines used to be
   built here AND described in the markup, which is one sentence in two
   places waiting to disagree. */
const emptyCell = $('stage').firstElementChild.cloneNode(true);

/* ⛔ A POLL THAT FAILED LEAVES THE STAGE ALONE. It used to fall through with
   an empty fleet, so one unanswered question - the server restarting, a link
   that dropped - tore down every screen and drew the empty room that says
   `No browser open`, over browsers that were open the whole time. The next
   poll three seconds later put them back, which is worse than either state on
   its own: the workspace blinked out and in for a reason nobody could see.
   The pictures keep their own age (`ageAll`), so a stage held through a
   failure says so by itself. */
async function drawFleet(){
  let got;
  try { const r = await door('/live/browsers', {cache:'no-store'});
        if(!r.ok) return;
        got = await r.json(); }
  catch(err){ return; }
  stage.fleet = got.browsers || [];
  stage.focus = got.focus || '';
  /* The build the server is running, kept the first time and compared every
     time after. See `newerServer`. */
  if(got.build){ if(!build) build = got.build;
                 else if(build !== got.build) newerServer(build, got.build); }
  /* ⛔ THE LAYOUT IS NOT CHOSEN ANY MORE, IT FOLLOWS THE BROWSERS. There was a
     picker - one, two or four screens - because a session could hold eight and
     which ones to watch was a decision. A session holds `main` and, while it is
     needed, `support`: two screens when the helper is up, one when it is not,
     and nothing for a person to set. A control that chose between layouts of
     the same single screen is the defect this page has written down twice. */
  stage.grid = stage.fleet.length >= 2 ? 2 : 1;
  drawStage();
  /* Whoever changed the fleet says so to the bar that reads it: see the boot
     line in the splitter for the clock this replaced. */
  paintWhere();
}

/* Whatever was waiting when the page went away comes back into the composer
   rather than into the queue: the run it was queued behind is over, so the
   honest place for it is where somebody can read it and press send. */
const waiting_text = queuedFromBefore();
if(waiting_text){ i.value = waiting_text; setQueued(null);
                  i.style.height = 'auto';
                  i.style.height = Math.min(i.scrollHeight, 200) + 'px'; }
