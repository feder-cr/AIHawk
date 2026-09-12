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

/* ⛔ THE FLOOR AND THE CEILING COME FROM THE TOKENS, AND THE CEILING WAS 57px
   OPTIMISTIC WITHOUT THEM. It subtracted the picture's minimum from the whole
   WINDOW, while the spine and the separator sit outside the split: dragged to
   the end, the browser pane got 423px where the number promised 480, and the
   separator announced a ceiling it could not reach. Four places knew 420 and
   two knew 9; now one declaration has three readers - this, the pane's own
   clamp, and the separator's width. */
function limits(){
  const css = getComputedStyle(document.documentElement);
  const px = name => parseFloat(css.getPropertyValue(name)) || 0;
  const min = px('--pane-min');
  return {min, max: Math.max(min, window.innerWidth - px('--stage-min')
                                  - px('--spine') - px('--split'))};
}

function splitTo(px, remember){
  const {min, max} = limits();
  const w = Math.round(Math.min(max, Math.max(min, px)));
  $('left').style.width = w + 'px';
  $('split').setAttribute('aria-valuenow', String(w));
  $('split').setAttribute('aria-valuemin', String(min));
  $('split').setAttribute('aria-valuemax', String(max));
  if(remember){ try { localStorage.setItem(SPLITKEY, String(w)); } catch(e) {} }
}

function splitReset(){
  try { localStorage.removeItem(SPLITKEY); } catch(e) {}
  $('left').style.width = '';
  $('split').setAttribute('aria-valuenow',
                          String(Math.round($('left').getBoundingClientRect().width)));
  /* The ceiling too: this is the FIRST-RUN path, so without it a range widget
     was announced with a floor and a value and no top for every new user.
     And the floor, which was in the markup as a literal: three numbers
     describing one range, from one place. */
  const {min, max} = limits();
  $('split').setAttribute('aria-valuemin', String(min));
  $('split').setAttribute('aria-valuemax', String(max));
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
    /* ⛔ AND NOT ESCAPE. It reset the split here AND reached the document,
       where it stops the run: one key, two things, one of them the thing
       that ends the agent's work. Home is what returns a control to its
       default everywhere else, and Escape now means close the panel, or
       stop the run, and nothing at all when neither applies. */
    else if(e.key === 'Home'){ splitReset(); e.preventDefault(); }
  });
  /* A width saved on a wide monitor is not a width on a laptop: put it back
     through the same clamp whenever the window changes. */
  window.addEventListener('resize', () => {
    if($('left').style.width) splitTo(parseFloat($('left').style.width), false);
  });
}


paint(); listen(); tick(); where(); fleetPoll(); slowTick(); splitter();
if(!$('rail').hidden) drawChats();
