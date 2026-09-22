/* ---------------- the OrcaRouter sign-in ----------------
   The PKCE road into a credential: start an attempt on the server, open the
   consent screen, and hand the code back. It is a file of its own because the
   card that draws the two ways in and the state machine that finishes one of
   them are two jobs, and the file that held both was over the ceiling this
   project puts under every piece of the page.

   ⛔ THE VERIFIER, THE STATE AND THE PORT NEVER REACH THIS FILE. The server
   binds its loopback listener and answers with a URL and an attempt number;
   the code comes back through that listener, not through here, and what this
   file submits is the code. Nothing in the browser can complete the exchange
   on its own, which is the point of the flow.

   ⛔ THE ATTEMPT NUMBER IS THE WHOLE CANCELLATION STORY. Every sign-in gets a
   number from the server, every answer carries the number it belongs to, and
   an answer for a superseded number is discarded rather than drawn - including
   a success, because a late success landing on a newer sign-in is how a page
   ends up holding an account the person did not choose. `pagehide` clears the
   busy state and the hint SYNCHRONOUSLY and then cancels on the server with
   `keepalive`, because the guarded `finally` deliberately refuses to touch an
   attempt it no longer owns - which is exactly why a page restored from the
   back-forward cache used to stay busy for ever. */

async function connectProvider(){
  const r = await ask('/provider/connect', undefined, 'The sign-in could not start');
  if(!r) return;
  const got = await r.json();
  if(got.error){ providerSay(got.error, true, false); return; }
  signInAttempt = got.attempt;
  signInBusy = true;
  $('provcancel').hidden = false;
  $('provconnect').disabled = true;
  $('provmanual').hidden = false;
  /* ⛔ THE URL IS ON SCREEN AS WELL AS OPENED. A browser that does not open, or
     a machine where the default handler is not this browser, would otherwise
     leave the person with a button that did nothing. */
  providerSay('Approve in the browser. If nothing opened, paste this into one: '
              + got.url, false, false);
  window.open(got.url, '_blank', 'noopener');
  const done = await ask('/provider/login', {attempt: got.attempt},
                         'The sign-in did not finish');
  if(!done){ signInDone(); return; }
  const state = await done.json();
  if(state.error){ providerSay(state.error, true, false); }
  else { drawProvider(state); providerSay(state.note || 'Signed in.', false, true); }
  signInDone();
}

async function submitProviderCode(){
  const field = $('provcode');
  const given = (field.value || '').trim();
  if(!given){ providerSay('Paste the code from the consent screen first.', true, false); return; }
  field.value = '';
  const r = await ask('/provider/login',
                      {attempt: signInAttempt, code: given, wait: 30},
                      'That code was not accepted');
  if(!r) return;
  const state = await r.json();
  if(state.error){ providerSay(state.error, true, false); return; }
  drawProvider(state);
  providerSay(state.note || 'Signed in.', false, true);
  signInDone();
}

async function cancelProvider(){
  /* ⛔ THE ATTEMPT IS NAMED, so cancelling the sign-in this page started cannot
     release somebody else's. The server bumps its own number as well, so a late
     answer for this one is refused rather than applied. */
  const attempt = signInAttempt;
  clearSignIn();
  const r = await ask('/provider/cancel', {attempt}, 'The sign-in could not be cancelled');
  if(r) providerSay('Sign-in cancelled.', false, false);
}

/* ⛔ ONE PLACE PUTS THE SIGN-IN BACK TO REST, and `pagehide` is why it exists as
   a function rather than as four lines inside the handler. A page restored from
   the back-forward cache keeps its DOM and has lost the attempt that was in the
   air, so the busy flag, the hint and the controls have to be cleared
   SYNCHRONOUSLY - the guarded `finally` on the request deliberately refuses to
   touch an attempt it no longer owns, which is exactly how a restored page used
   to stay busy for ever. Cancel, a denial and a window close all end the same
   way, so all three call this. */
function signInDone(){
  /* ⛔ AND THE CONTROLS GO BACK TOO, ON EVERY ENDING. Measured: a sign-in that
     finished left the Connect button disabled and the code field on screen, so
     the NEXT sign-in could not be started at all without a page reload - which
     is the same defect the `pagehide` handler exists to avoid, one path over. */
  signInBusy = false;
  const connect = $('provconnect');
  const cancel = $('provcancel');
  const manual = $('provmanual');
  if(connect) connect.disabled = false;
  if(cancel) cancel.hidden = true;
  if(manual) manual.hidden = true;
}

function clearSignIn(){
  signInDone();
  signInAttempt = 0;
  providerSay('');
}

/* ⛔ THE BACK-FORWARD CACHE, WHICH IS THE ONE PATH A GUARDED `finally` CANNOT
   COVER. A page put into the bfcache keeps its DOM and loses its running work,
   so an attempt that was in the air is neither finished nor cancelled; when the
   page is restored it draws the busy state it was frozen with. So the busy flag
   and the hint are cleared HERE, synchronously, and only then is the server
   told - with `keepalive`, because a beacon outlives the page it was sent from
   and a normal request does not. `pagehide` fires for a reload and a window
   close as well, which is what makes this the right place rather than unload. */
function providerPageHide(){
  const busy = signInBusy;
  const attempt = signInAttempt;
  clearSignIn();
  if(!busy || !attempt) return;
  /* ⛔ THE SAME DOOR AS EVERY OTHER REQUEST, AND `keepalive` IS WHY IT IS A
     DOOR AND NOT A BEACON. `navigator.sendBeacon` posts what it is given and
     cannot set a content type, which this server answers with a 400 before the
     route runs - so the cancellation would never arrive. `fetch` with
     `keepalive` outlives the page being torn down AND can say it is JSON, and
     it is the page's one door, so a stale page is told so here too. The URL is
     built by `at()` like every other, so the cancellation names the
     conversation it belongs to. */
  door('/provider/cancel', {method:'POST', keepalive:true,
                            headers:{'Content-Type':'application/json'},
                            body: JSON.stringify({attempt})}).catch(() => {});
}

window.addEventListener('pagehide', providerPageHide);
