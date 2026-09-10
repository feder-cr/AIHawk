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


