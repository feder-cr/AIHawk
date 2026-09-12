/* ---------------- which conversation this page is in ----------------
   ⛔ ONE PLACE, AND EVERY REQUEST GOES THROUGH IT. The server routes all read
   `?s=`, so a fetch that forgets it acts on the DEFAULT conversation while the
   page shows another - and the way that shows up is the picture on the right
   belonging to somebody else's browser, with nothing red anywhere. `at()` is
   the only thing that writes the parameter, so there is one place to be wrong
   and it is covered by a test that reads this file.

   The id is kept in the URL rather than in a variable, so a reload, a bookmark
   and a second tab all land in the same conversation instead of silently
   dropping to the default one. */
let here = new URLSearchParams(location.search).get('s') || 'default';
const at = (path) => path + (path.includes('?') ? '&' : '?') + 's=' + encodeURIComponent(here);

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
    case 'fresh': wipe(); break;
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
                    if(!r) drawChats();
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
    /* Deliberately total: a kind this page has never heard of is still shown,
       for the same reason an unknown tool still renders its arguments. */
    default:      flush(false, r); orphan('said', m.text, r);
  }
  settleOnce();
};

new IntersectionObserver(([e]) => { $('jump').hidden = e.isIntersecting; },
                         {root: log}).observe(anchor);
/* ⛔ THE LARGEST MOTION ON THE PAGE, AND THE ONE THE REDUCED-MOTION BLOCK
   COULD NOT REACH: a smooth scroll is asked for in script, not in CSS, so the
   rule that quiets every animation had no say over it. Read at click time and
   not at load, because the setting can change while the tab is open. */
$('jump').onclick = () => anchor.scrollIntoView({block:'end',
  behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});

