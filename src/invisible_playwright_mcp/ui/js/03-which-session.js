/* ---------------- which conversation this page is in ----------------
   ⛔ ONE PLACE, AND EVERY REQUEST GOES THROUGH IT. The server routes all read
   `?s=`, so a fetch that forgets it acts on the DEFAULT conversation while the
   page shows another - and the way that shows up is the picture on the right
   belonging to somebody else's browser, with nothing red anywhere. `at()` is
   the only thing that writes the parameter, so there is one place to be wrong
   and it is covered by a test that reads this file.

   The id is kept in the URL rather than in a variable, so a reload, a bookmark
   and a second tab all land in the same conversation instead of silently
   dropping to the default one.

   ⛔ AND A PAGE THAT NAMES NONE ASKS WITH NONE. The default conversation's
   id is the server's constant - `DEFAULT_SESSION_ID`, declared once there -
   and until 0.52.0 this line held a second copy of it, `'default'`, that
   nothing kept in step. A request with no `?s=` is answered with the
   server's default by the server's own rule, and the one place this page
   has to COMPARE against that id, the session column, learns it from the
   listing, which carries it. */
let here = new URLSearchParams(location.search).get('s') || '';
let defaultId = '';
const isHere = (id) => id === (here || defaultId);
const at = (path) => !here ? path
  : path + (path.includes('?') ? '&' : '?') + 's=' + encodeURIComponent(here);

let es = null;
function listen(){
  if(es) es.close();
  es = new EventSource(at('/chat/events'));
  es.onmessage = onEvent;
  /* ⛔ A STREAM THAT DIED LOOKS EXACTLY LIKE AN AGENT WITH NOTHING TO SAY.
     EventSource reconnects on its own, so this is not a retry - it is the
     only signal that the silence is the connection and not the work. The dot
     and the word beside it describe the BROWSER, and said `live` throughout. */
  es.onerror = () => {
    if(es.readyState === EventSource.CONNECTING) say('offline', 'reconnecting');
    if(es.readyState === EventSource.CLOSED) say('offline', 'the stream closed');
    dropped();
  };
  es.onopen = () => { lost = false;
                      if(right.dataset.state === 'offline') say(frozen ? 'frozen' : 'live'); };
}

/* ⛔ THE CLOCK WENT ON COUNTING ON A DEAD STREAM, AND THE CONVERSATION SAID
   NOTHING. Only a `busy`, `said`, `tool` or `result` event ever ends the wait,
   so when the stream died mid-run - the server restarted, the laptop slept -
   the transcript kept a row reading `Thinking 412.7s` and climbing: a counter
   asserting that an agent is alive, with no way to tell it from one that is.
   The only contradicting signal was a 7px dot in the OTHER pane.

   Once per drop, cleared when the stream comes back, because EventSource
   retries on its own and a sentence per retry would be a column of them.

   And the sentence is careful about what it claims: losing the page's
   connection does not stop the agent, which goes on working server-side, so it
   must not say that nothing is running. */
let lost = false;
function dropped(){
  if(lost) return;
  lost = true;
  waited();
  orphan('err', 'The connection to the server dropped. Reconnecting - anything '
         + 'the agent does while it is down appears when it comes back.');
}
const onEvent = (e) => {
  const m = JSON.parse(e.data), r = m.replay;
  /* ⛔ A REPLAY IS NOT NEWS, AND IT WAS ANNOUNCED AS IF IT WERE. The
     transcript is the page's only live region, and a reconnect - a
     restarted server, a laptop waking, a tab coming back - replays the
     whole conversation into it, so a screen reader read out an entire
     hour of work from the beginning while the agent went on adding to
     it. The burst is silenced and the region comes BACK: switching it
     off for good would be the louder bug, told quietly. */
  if(r){ thread.setAttribute('aria-live', 'off'); clearTimeout(quiet);
         quiet = setTimeout(() => thread.setAttribute('aria-live', 'polite'), 200); }
  switch(m.kind){
    case 'model': $('model').textContent = m.text; $('model').hidden = false; break;
    /* Sent to every listener, so a second tab clears too instead of showing a
       transcript the server has already forgotten. */
    /* ⛔ ONE WORD, TWO REASONS, AND ONLY ONE OF THEM IS A REASON TO
       THROW AWAY A TYPED SENTENCE. `fresh` arrives when somebody pressed
       Clear, and it arrives when this page reconnected holding a position
       from another transcript - a server that restarted under it. The page
       answered both by wiping, and wiping dropped the queued message: so a
       follow-up typed while the agent worked disappeared on the next
       restart, which is the one thing this interface says everywhere it
       must not do. The server says which now. */
    case 'fresh': wipe(); if(m.text !== 'rewound') setQueued(null); break;
    case 'busy':
      busyNow = m.text === '1';
      /* Not on a replay: those events describe a wait that is over. */
      if(busyNow && !r) waiting(); else waited();
      if(!busyNow){ flush(true, r);
                    /* A turn can end with a step still open: Stop pressed with
                       a click in flight, a run that died, a model that never
                       answered. The row is settled HERE because this is the one
                       place that knows the turn is over - otherwise it keeps
                       the running state and its breathing dot for as long as
                       the page stays up, asserting work nobody is doing. */
                    if(live) close(live, 'off', 'stopped');
                    live = null; clearInterval(timer);
                    /* The name of a conversation is decided by its FIRST
                       instruction, on the server, so the column is stale from
                       the moment a new session is used until it is redrawn.
                       Redrawn on the end of a turn and not on its start: the
                       turn count beside the name is only right once. */
                    /* ⛔ AND NOT WHILE NOBODY CAN SEE IT. This asks the
                       server for the list and rebuilds a DOM inside a panel
                       that is `hidden` almost always - once per turn, for a
                       column nobody is looking at. The boot line below already
                       carries this guard; the rule was known and applied in one
                       of the two places. Opening the panel draws it. */
                    if(!r && !$('rail').hidden) drawChats();
                    if(queued){ const t = queued; setQueued(null); send(t); } }
      paint(); break;
    /* ⛔ AS AN ANSWER, AND A REPLAY IS THE ONLY PLACE IT SHOWS. A sentence
       still held when the PERSON speaks had nothing after it in its own turn,
       which is the same thing `busy 0` means - and `busy` is deliberately not
       kept in the history, so on a reopened conversation this branch is the
       only one that can ever draw the answer of a turn that is not the last.
       Measured 2026-09-11 on a real transcript of three turns: one answer
       drawn, two dropped, silently, by a change made an hour earlier that had
       a gate of its own - the gate ran `flush` both ways and never asked WHEN
       the dispatcher calls which. */
    case 'you':   flush(true, r); live = null; newTurn();
                  put(el('div','you', m.text), r); break;
    case 'said':  waited(); flush(false, r); hold = m.text; break;
    case 'tool':  waited(); flush(false, r); step(m.text, r); break;
    case 'result':
    case 'err':   flush(false, r); land(m.kind, m.text, r);
                  /* The step is done and the model is reading its result, which
                     is another wait of the same kind: the loop asks again before
                     anything else can appear. */
                  if(busyNow && !r) waiting();
                  break;
    /* A note is the interface's own sentence - "Stopped." after the button -
       and not the model's: named so the two cannot be confused later. */
    case 'note':  flush(false, r); orphan('note', m.text, r); break;
    /* Deliberately total: a kind this page has never heard of is still shown,
       for the same reason an unknown tool still renders its arguments. */
    default:      flush(false, r); orphan('said', m.text, r);
  }
};

/* The way back, and it is the ONE control on screen while a reader is scrolled
   up: it says how much has arrived since they left the bottom. */
new IntersectionObserver(([e]) => { $('jump').hidden = e.isIntersecting;
                                    if(e.isIntersecting) seen(); },
                         {root: log}).observe(anchor);
/* ⛔ IT LANDS AT THE BOTTOM AT ONCE, AND THAT IS THE CORRECTION. It asked for a
   SMOOTH scroll, which computes a destination and animates to it over a few
   hundred milliseconds - and every row that arrives during the animation pushes
   the anchor further down, so the animation finishes where the bottom USED to
   be. Measured with the agent working: one press moved the view 2,700px and
   still left 303px to go, with the anchor 282px below the fold and the button
   still on screen; the content had grown 283px while the animation ran, which
   is almost exactly the shortfall. Press again, same thing, forever. The same
   press with the run finished landed 20px from the bottom and the button went
   away.

   An animation cannot arrive at a target that moves. Landing at once always
   can. There is also no motion left to reduce, which is why the reduced-motion
   reading that used to be here is gone rather than kept.

   ⛔ AND THE SENTENCE THAT STOOD HERE WAS MEASURED FALSE: "from there the
   stylesheet keeps the view at the bottom by itself". It does not. `#anchor` is
   the only child with `overflow-anchor:auto`, and the browser will only choose
   an anchor that is ON SCREEN - so the stylesheet holds a bottom that something
   else has already reached, and holds nothing otherwise. Measured: with the
   scroller one pixel from the top, 374 px of rows arrived and it moved by zero.
   What makes the button a follow is `put`, which asks the observer whether the
   reader is at the bottom and chases it when they are. */
$('jump').onclick = () => { toBottom(); seen(); };

/* The transcript growing is what puts the view back at the bottom, and a
   resize observation is the one signal delivered AFTER layout. `grew` is in
   `02-transcript.js` with the measurement that put it there. */
new ResizeObserver(grew).observe(thread);

