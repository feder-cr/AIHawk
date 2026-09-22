/* The provider panel, second half: the two ways in.

   ⛔ THE CREDENTIAL INTERFACE IS THE SEAM, AND THESE ARE ITS TWO ADAPTERS.
   `orcaSaveKey` stores a key the user already had; `orcaConnect` gets one
   issued by signing in. Both end at the same route, both leave the same
   ordinary OrcaRouter key in the same store, and neither the model selector nor
   the provider request knows which one was used - which is the property that
   makes this two ways IN rather than two integrations.

   ⛔ AND EVERY WAY OUT OF A SIGN-IN RELEASES IT. Success, a denial, a refused
   exchange, a timeout, a cancel, a second attempt over the first, a closed
   panel, `pagehide` - all of them end the same way, through `orcaBusyNow(false)`
   and `cancel`, because a loopback listener left open is a port the next
   attempt cannot have. */

async function orcaAsk(path, body){
  return ask(path, body, 'The OrcaRouter panel could not reach the server');
}

/* ⛔ TWO OF THESE ROUTES ARE READS, AND `ask` IS A POST. `/provider/state` and
   `/provider/models` are declared GET, and a POST to them is answered 405 -
   which the panel drew as an empty selector, no key and no error, because a
   405 is not a network failure. So a read gets its own line through the same
   door, and it says so on the page the same way. */
async function orcaRead(path){
  try {
    const r = await door(path, {cache:'no-store'});
    if(!r.ok) throw new Error('HTTP ' + r.status);
    return r;
  } catch(err){
    orcaSay('The OrcaRouter panel could not reach the server ('
            + err.message + ').', true);
    return null;
  }
}

async function orcaLoad(){
  const r = await orcaRead('/provider/state');
  if(r) drawProvider(await r.json());
}

/* ⛔ THE ATTEMPT IS STARTED, THE URL IS SHOWN, AND THE PAGE THEN ASKS. The
   server never blocks on the person: a request that waited for the browser
   would outlive the tab that made it, and this page has to keep drawing the
   transcript and the browser pane while somebody is over in another window. */
async function orcaConnect(){
  if(orcaBusy) return;
  const r = await orcaAsk('/provider/connect', {});
  if(!r || !r.ok){ orcaBusyNow(false); return; }
  const started = await r.json();
  orcaAttempt = started.attempt;
  orcaBusyNow(true, 'Authorize in the browser window that just opened. '
    + 'If nothing opened, copy this address: ' + started.url);
  /* A click the page could not turn into a browser tab: the address is on
     screen, which is the fallback the rules ask for rather than a dead end. */
  try { window.open(started.url, '_blank', 'noopener'); } catch(err){ /* shown above */ }
  orcaPoll();
}

async function orcaPoll(){
  if(!orcaAttempt || !orcaBusy) return;
  const mine = orcaAttempt;
  const r = await orcaAsk('/provider/login', {attempt: mine});
  /* ⛔ THE ANSWER IS CHECKED AGAINST THE ATTEMPT IT BELONGS TO, and an attempt
     that was cancelled, superseded or finished while this was in the air is
     dropped without touching anything. Without this a late success from a
     sign-in somebody abandoned would land on top of a newer one. */
  if(orcaAttempt !== mine) return;
  if(!r){ orcaAttempt = null; orcaBusyNow(false); return; }
  if(!r.ok){
    const said = await r.json().catch(() => ({}));
    orcaAttempt = null;
    orcaBusyNow(false, said.error || 'The sign-in did not complete.');
    return;
  }
  const got = await r.json();
  if(got && got.state === 'waiting'){ setTimeout(orcaPoll, 1200); return; }
  orcaAttempt = null;
  orcaBusyNow(false);
  if(got && got.state === 'error'){
    orcaSay(got.detail === 'declined'
      ? 'The sign-in was declined in the browser. Nothing was changed.'
      : 'The sign-in did not complete. Start again.', true);
    return;
  }
  drawProvider(got);
  orcaSay('Signed in. AIHawk holds its own key, and you can revoke it from '
          + 'your console at any time.', false);
}

/* ⛔ THE CODE IS REDEEMED THROUGH THE SAME ROUTE AS THE LOOPBACK ONE. Somebody
   whose browser showed them a code rather than redirecting - which the consent
   screen allows whatever callback was asked for - pastes it here, and it is
   exchanged with the verifier this process still holds. */
async function orcaSubmitCode(){
  const mine = orcaAttempt;
  const code = $('orcacode').value.trim();
  if(!mine || !code) return;
  const r = await orcaAsk('/provider/login', {attempt: mine, code: code});
  orcaAttempt = null;
  orcaBusyNow(false);
  if(!r){ return; }
  if(!r.ok){
    const said = await r.json().catch(() => ({}));
    orcaSay(said.error || 'That code was not accepted. Start again.', true);
    return;
  }
  drawProvider(await r.json());
  orcaSay('Signed in. AIHawk holds its own key, and you can revoke it from '
          + 'your console at any time.', false);
}

async function orcaCancel(){
  const mine = orcaAttempt;
  orcaAttempt = null;
  orcaBusyNow(false);
  if(mine) await orcaAsk('/provider/cancel', {attempt: mine});
}

async function orcaSaveKey(){
  const field = $('orcakey');
  const r = await orcaAsk('/provider/key', {key: field.value});
  if(!r) return;
  if(!r.ok){
    const said = await r.json().catch(() => ({}));
    orcaSay(said.error || 'That key was not accepted.', true);
    return;
  }
  /* ⛔ THE FIELD IS EMPTIED ON SUCCESS AND NOT ON FAILURE. Clearing it after a
     refusal would take away the thing the person is trying to fix. */
  field.value = '';
  drawProvider(await r.json());
  orcaSay('Key stored. It is sent only to OrcaRouter, and never drawn in full.',
          false);
}

/* A second press, like every other destructive control on this page: a native
   `confirm` blocks the thread, and this page's whole claim is that you can
   watch the agent work while you use it. */
async function orcaClearKey(){
  const button = $('orcachear');
  if(!button.dataset.armed){
    button.dataset.armed = '1';
    button.textContent = 'Forget the stored key?';
    return;
  }
  delete button.dataset.armed;
  button.textContent = 'Forget it';
  const r = await orcaAsk('/provider/key', {clear: true});
  if(!r) return;
  drawProvider(await r.json());
  orcaSay('The stored key is gone. Anything pasted or exported is untouched.',
          false);
}

async function orcaRefresh(){
  const r = await orcaAsk('/provider/refresh', {});
  if(!r) return;
  if(!r.ok){ orcaSay('The model list could not be read.', true); return; }
  drawProvider(await r.json());
}

async function orcaChoose(){
  const pick = $('orcapick');
  const r = await orcaAsk('/provider/choose',
    {provider: 'orcarouter', model: pick.value});
  if(!r) return;
  if(!r.ok){
    const said = await r.json().catch(() => ({}));
    orcaSay(said.error || 'That model could not be selected.', true);
    return;
  }
  drawProvider(await r.json());
}

/* ⛔ IT OPENS FROM THE OTHER SIDE, ON PURPOSE. The session column slides out
   from the spine on the left; this one comes in from the right edge of the
   window. Two panels over the same ground would be two answers to "what is on
   top of what" - and the session column is about WHICH conversation, which is
   the left pane's business, while this is about what answers in it. Each is
   one gesture from gone, and neither is ever underneath the other. */
function showOrca(on){
  const panel = $('orcapanel');
  if(!on){
    if(panel.hidden) return;
    panel.hidden = true;
    $('provider').setAttribute('aria-expanded', 'false');
    for(const box of [$('left'), $('right')]) outOfPlay(box, 'orcarouter', false);
    return;
  }
  panel.hidden = false;
  $('provider').setAttribute('aria-expanded', 'true');
  /* The same mechanism the session column uses, and the same reason: a panel
     over live content that is still reachable by pointer and by Tab is a panel
     that announces one thing and does another. */
  for(const box of [$('left'), $('right')]) outOfPlay(box, 'orcarouter', true);
  orcaLoad();
  $('orcadone').focus();
}

/* ⛔ `pagehide` NEEDS ITS OWN HANDLER AND ITS OWN CLEARING. A page put into the
   back-forward cache is not unloaded and not remounted: it comes back exactly
   as it was, which for a sign-in in flight means permanently busy and with a
   hint still naming an attempt nobody is waiting for. So the busy flag and the
   hint are cleared SYNCHRONOUSLY here - not in the request's own `finally`,
   which correctly refuses to touch a generation it no longer owns, and which is
   therefore the reason a restored page used to stay busy forever.

   ⛔ AND THE CANCELLATION GOES OUT BY BEACON. `sendBeacon` is the one request
   API built for a document that is going away: it is queued by the browser and
   survives the unload, where an ordinary request is cancelled with the page.
   It is also why the page still has exactly one call to the door - every other
   here goes through the one door, which is what lets a 404 and a 410 mean
   something. */
function orcaPageHide(){
  if(!orcaAttempt) return;
  const mine = orcaAttempt;
  orcaAttempt = null;
  orcaBusyNow(false, '');
  try {
    navigator.sendBeacon('/provider/cancel',
      new Blob([JSON.stringify({attempt: mine})], {type: 'application/json'}));
  } catch(err){ /* the page is going away; the attempt is already dropped */ }
}

$('provider').addEventListener('click', () => showOrca($('orcapanel').hidden));
$('orcadone').addEventListener('click', () => showOrca(false));
$('orcaconnect').addEventListener('click', orcaConnect);
$('orcacancel').addEventListener('click', orcaCancel);
$('orcasubmit').addEventListener('click', orcaSubmitCode);
$('orcasave').addEventListener('click', orcaSaveKey);
$('orcachear').addEventListener('click', orcaClearKey);
$('orcarefresh').addEventListener('click', orcaRefresh);
$('orcapick').addEventListener('change', orcaChoose);
/* Disarmed when the control loses the focus, like the other one on this page:
   a second press that has to happen soon is a second press that happens by
   accident. */
$('orcachear').addEventListener('blur', (e) => {
  delete e.currentTarget.dataset.armed;
  e.currentTarget.textContent = 'Forget it';
});
window.addEventListener('pagehide', orcaPageHide);
