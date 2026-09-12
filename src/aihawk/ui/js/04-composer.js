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
  /* ⛔ `aria-disabled`, NOT `disabled`, BECAUSE A DEAD BUTTON CANNOT SAY
     WHY. Clear greyed out for the whole of a run and never explained itself,
     and a `disabled` control fires no events - no hover, no click, and in this
     engine no tooltip either - so there was no way to hang the explanation on
     it. It keeps the same look through the shared rule, stays reachable, and a
     press while the agent works says what to do instead of doing nothing. */
  fresh.setAttribute('aria-disabled', busyNow ? 'true' : 'false');
  go.disabled = !typed;
  /* ⛔ THE MODE IS DECIDED ONCE AND DRAWN, because nothing visible said that
     Enter would QUEUE rather than send. The placeholder said it, and a
     placeholder disappears at the first keystroke - so the moment a person had
     typed a follow-up while the agent worked, the one control in front of them
     looked exactly like Send. The same three-way choice was also written twice,
     once for the label and once for the placeholder, which is how the two
     drift. `data-mode` on the button is what the stylesheet draws. */
  const mode = queued ? 'replace' : busyNow ? 'queue' : 'send';
  go.dataset.mode = mode;
  go.setAttribute('aria-label', {replace: 'Replace queued message',
                                 queue: 'Queue for next turn', send: 'Send'}[mode]);
  i.placeholder = {replace: 'Type to replace the queued message',
                   queue: 'Type to queue a message',
                   send: 'What should the agent do?'}[mode];
  chip.hidden = !queued;
  /* ⛔ AND IT SAYS WHAT IT IS HOLDING. The chip read `1 message queued` and
     the queued words were never drawn anywhere, so a second Enter replaced a
     sentence nobody could see with another one, silently and with no way back.
     Typed work destroyed by a keystroke that looks like sending. With the
     words on screen the replacement is visible, and what was lost can at least
     be read off the row before it goes. */
  if(queued) chip.querySelector('.what').textContent = queued;
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
  /* ⛔ THE BUTTON'S OWN HANDLER, NOT A SECOND COPY OF IT. The same request with
     the same failure sentence was written out twice, here and on the button, so
     the half added to either one - reading the answer, saying that nothing was
     running - reached whichever path the reader happened to be looking at. The
     key IS the button, so it presses it. */
  halt.onclick();
});
/* A pencil and not a cross: a cross would read as "cancel the queued message".
   This returns it to the composer to be edited.

   ⛔ AND IT DOES NOT EAT WHAT IS IN THE BOX. It assigned over `i.value`, so
   clicking the chip to see what was queued destroyed whatever was being typed
   - the same loss as the silent replacement above, in the other direction, and
   from a control whose whole purpose is to get typed words back. Both survive:
   the queued sentence arrives above the draft, and what to do with the two of
   them is a decision for the person rather than for this line. */
chip.onclick = () => { const draft = i.value.trim();
                       i.value = draft ? queued + '\n' + i.value : queued;
                       setQueued(null); i.focus();
                       i.dispatchEvent(new Event('input')); };

/* ⛔ THE EXAMPLE IS A BUTTON THAT DOES WHAT IT LOOKS LIKE IT DOES. It was
   drawn as a suggestion chip - a bordered mono line in the empty transcript -
   and clicking it did nothing, on the first screen a new user sees. It fills
   the composer and does not send, the same shape as the queued-message chip:
   the words are put where the person can read them and change them. Wired by
   class on the transcript rather than on the node, because the node is cloned
   back after Clear and a handler on the original would not travel with it. */
thread.addEventListener('click', (e) => {
  const eg = e.target.closest('.eg'); if(!eg) return;
  i.value = eg.textContent.trim();
  i.dispatchEvent(new Event('input'));
  i.focus();
});

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
  /* And the page can introduce itself again. Clear emptied the pane to
     nothing at all, on a product whose whole first-run explanation was
     those three sentences: press it on a finished conversation and it
     had forgotten how to say what it is until the tab was reloaded. */
  if(!thread.firstElementChild) thread.appendChild(hintNode.cloneNode(true));
}
let vanished = false;
let outdated = false;
/* ⛔ ONE PLACE ASKS THIS CONVERSATION FOR ANYTHING, so one place can notice
   that it is not there any more. Six fetches carry `?s=`, and each of them
   would otherwise need the same three lines - written six times, the seventh
   is where a page goes on talking to a session somebody deleted. Which is not
   hypothetical: every one of those questions used to DECLARE the session again
   on the server, so a delete that had already closed the browsers and erased
   the transcript came straight back as an empty row, for as long as one tab
   stayed open on it. */
async function door(path, init){
  return readStatus(path, await fetch(at(path), init));
}

/* ⛔ THE SAME READING, FOR THE THREE ROUTES THAT ARE NOT ADDRESSED. `/sessions`,
   `/sessions/forget` and `/sessions/rename` are about the SET of conversations
   rather than one, so they carry their id in the body and must not have `?s=`
   appended - and two of them were calling `fetch` directly to avoid it, which
   also skipped what a 404 and a 410 mean.

   What that cost, and it is a sentence rather than a silence: delete a session
   on a server that no longer serves that route and the page says `That session
   is still working, so it was not deleted`, because a 404 is not `ok` and the
   only other reading of `forgotten:false` is that one. A wrong explanation is
   worse than none - it sends somebody to stop a run that is not running.

   Addressing and reading the answer are two jobs; only the first of them
   belongs to some routes and not others. */
async function plainDoor(path, init){
  return readStatus(path, await fetch(path, init));
}

function readStatus(path, r){
  /* 410 and nothing else. Every other failure is worth trying again; this one
     is the only one that will never stop being true. */
  if(r.status === 410){ vanish(); throw new Error('this conversation was deleted'); }
  /* 404 is the OTHER thing that will never stop being true, and until
     2026-09-11 it was silent. Every path this page asks for is a route the
     app declares, so a 404 cannot be a missing row or a bad id - it means
     this page and this server disagree about what exists, which happens to
     every tab left open across a deploy. Reported from a real session: the
     address bar said `no page yet` on a browser plainly on a page, because
     the tab was older than the server and the route it asked for had been
     removed. The old code read `if(r.ok)` and dropped the answer without a
     word, so the only visible effect was one part of the page quietly
     ceasing to be true while everything else kept working. */
  if(r.status === 404){ outOfDate(path); }
  return r;
}

/* Older than the server, which is not the same as broken and must not be
   treated like it. Only the routes that went away stop answering; the rest
   of the page is still live and still worth reading, so this SAYS it and
   changes nothing else - going inert here would take away more than the
   defect did. Once per page: a pump asking every two seconds would otherwise
   write the same sentence thirty times a minute. */
function outOfDate(path){
  if(outdated) return;
  outdated = true;
  orphan('err', 'This page is older than the server: it asked for '
         + String(path).split('?')[0] + ', which this version does not serve. '
         + 'Reload to get the current page.');
}

/* ⛔ ONE OWNER FOR `inert` WHEREVER TWO REASONS CAN HOLD THE SAME BOX. The
   browser pane goes out of play when this conversation is deleted, and again
   while the sessions panel lies on top of it, and those two are set from
   different files. Written by hand, whichever one lets go last wins: press
   Escape on the panel over a deleted conversation and the browser pane comes
   back fully lit on a page where nothing is live. A box is inert while ANY
   reason holds it, and each reason releases only its own.

   A box only one thing can hold does not need this - the layout picker in the
   stage file has a single reason and writes the flag directly. This is for the
   boxes where the question "is it still held?" has more than one answer. */
const heldBy = new WeakMap();
function outOfPlay(box, why, on){
  let why_not = heldBy.get(box);
  if(!why_not){ why_not = new Set(); heldBy.set(box, why_not); }
  if(on) why_not.add(why); else why_not.delete(why);
  box.inert = why_not.size > 0;
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
  /* The way out is named AND put on screen: the word Sessions is drawn
     nowhere while the panel is closed - the spine is an icon - so the sentence
     sent people looking for a label that did not exist. Opening the panel here
     writes the remembered preference, which is accepted: splitting persistence
     out of `showRail` would cost more than it saves. */
  orphan('err', 'This conversation was deleted. Nothing here is live any more '
         + '- pick another one from the panel, or start a new one.');
  /* Everything goes inert EXCEPT the way out. `inert` rather than `disabled`
     because these are subtrees and not single controls, and it takes them out
     of the pointer AND the tab order - a composer that answers the keyboard
     while it cannot send is the same lie in a different place. The column of
     sessions keeps its full contrast, because the sentence above tells the
     person to use it. */
  for(const box of [f, $('right'), $('fresh')]) outOfPlay(box, 'deleted', true);
  showRail(true);
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
  if(busyNow){
    orphan('said', 'Clear is off while the agent is working: stop the run '
           + 'first, then clear.');
    return;
  }
  if(!confirm('Clear this conversation? The agent forgets everything you have told it. Its browsers stay open.')) return;
  ask('/chat/fresh', undefined, 'Could not clear this conversation');
};

/* ⛔ AND THE ANSWER IS READ. `/chat/stop` replies `stopped:false` when there
   was nothing to stop, which is not hypothetical: a restarted server, a second
   tab that already stopped the run, a page whose idea of the state is a few
   seconds stale. The press then did nothing, said nothing, and left the button
   offering to stop a run that had already ended - so the next reading available
   to the person is that the product ignores its own panic button.

   `busyNow` is deliberately NOT written here. The event stream is its single
   writer, and a second one is how two places start disagreeing about whether
   the agent is working. */
halt.onclick = async () => {
  const r = await ask('/chat/stop', undefined,
                      'The stop did not reach the agent - it is still running');
  if(!r) return;
  let stopped = true;
  try { stopped = (await r.json()).stopped; } catch(err){}
  if(!stopped) orphan('said', 'There was nothing running to stop: this page was '
                      + 'showing a run that had already ended.');
};
f.onsubmit = (e) => {
  e.preventDefault();
  const t = i.value.trim();
  if(!t){ return; }
  i.value = ''; i.style.height = 'auto';
  if(busyNow){ setQueued(t); return; }
  send(t); paint();
};

/* ⛔ AND THE CARET STARTS WHERE THE WORK STARTS. The one input on the page
   never had the keyboard on any load or any session switch, so every
   visit began with a click or a Tab through the frame before a word could
   be typed - on a page whose entire purpose is to receive a sentence.

   `preventScroll` is not optional: without it the focus drags a restored
   transcript to the bottom, which is the thing the replay goes out of its
   way not to do. And if the sessions panel comes back open, it is a modal
   and the composer is inert behind it, so this quietly does nothing and
   the panel takes the keyboard instead - which is the right order. */
i.focus({preventScroll:true});
