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

