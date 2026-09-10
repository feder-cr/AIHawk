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

