/* The provider panel, first half: what it draws.

   ⛔ THIS FILE AND `12-orcarouter-auth.js` ARE ONE PANEL SPLIT IN TWO, and the
   split is by subject rather than by length: this half turns a server state
   into what is on screen, and the other half is the two ways in - the sign-in
   flow and the key. The page is assembled in order (`ui.JS_FILES`), so the
   functions here are declared before the ones that call them and both halves
   see one another, exactly as they did when they were one file.

   ⛔ ONE ATTEMPT NUMBER, AND EVERY ANSWER IS CHECKED AGAINST IT. The sign-in is
   the only thing on this page that waits for something OUTSIDE it - a person,
   in another window, who may close the tab, come back an hour later, or start a
   second sign-in over the first. Each of those has to be decidable, and the
   number is what decides it: an answer that arrives carrying an older one is
   discarded rather than applied to whatever is current.

   ⛔ AND THE BUSY FLAG IS CLEARED BY THE PAGE, NOT BY THE REQUEST'S `finally`.
   A `finally` that checks the generation is right to refuse - it belongs to an
   attempt nobody is waiting for - and that is exactly why the restored page
   used to stay busy forever. The two are separate on purpose. */

let orcaAttempt = null;   /* the attempt the page is waiting on, or null */
let orcaBusy = false;     /* drawn state, cleared on every terminal path */
let orcaState = null;     /* the last state the server gave us */

function orcaSay(text, bad){
  const box = $('orcasay');
  box.textContent = text || '';
  box.style.color = bad ? 'var(--err)' : 'var(--fg-3)';
}

/* ⛔ THE BUSY FLAG IS ONE PLACE, so `pagehide`, a cancel, a refusal and a
   success cannot leave it in three different states. `hint` is the sentence
   beside the Connect button, and clearing it here is the half that a
   generation-guarded `finally` deliberately does not do. */
function orcaBusyNow(on, hint){
  orcaBusy = !!on;
  const connect = $('orcaconnect');
  connect.disabled = orcaBusy;
  connect.textContent = orcaBusy ? 'Waiting for your browser...'
                                 : 'Connect with OrcaRouter';
  $('orcacancel').hidden = !orcaBusy;
  $('orcacode').hidden = !orcaBusy;
  $('orcasubmit').hidden = !orcaBusy;
  if(hint !== undefined) orcaSay(hint, false);
}

/* The whole panel, from the one route that knows. Called on open, after every
   change, and after a sign-in finishes - so what is drawn is always what the
   server holds rather than what the page remembers asking for. */
function drawProvider(state){
  if(!state || !state.provider) return;
  orcaState = state;
  $('model').textContent = state.model;
  $('model').hidden = false;
  const key = state.key || {};
  const where = $('orcawhere');
  where.textContent = '';
  const note = document.createElement('span');
  const link = document.createElement('a');
  link.href = state.console;
  link.textContent = 'your OrcaRouter console';
  if(key.present){
    note.textContent = key.needs_reauth
      ? 'The stored key was refused: ' + key.masked + '. Sign in again, or '
        + 'paste a new one. Keys are listed and revocable in '
      : 'Using ' + key.masked + ' (' + key.method + ', from ' + key.source
        + '). Keys are listed and revocable in ';
  } else {
    note.textContent = 'No OrcaRouter key yet. Paste one above, or sign in. '
      + 'Keys are listed and revocable in ';
  }
  where.appendChild(note);
  where.appendChild(link);
  where.appendChild(document.createTextNode('.'));
  drawModels(state.catalog);
}

/* ⛔ THE OPTIONS COME FROM THE SERVER AND FROM NOWHERE ELSE. A list written
   here would be a second answer to "what can this provider do", it would go
   stale silently, and it would be wrong for the account it is drawn in front
   of - the catalog is the fleet that workspace can actually call. */
function drawModels(catalog){
  const pick = $('orcapick');
  const wanted = (catalog && catalog.models) || [];
  const keep = pick.value || (orcaState && orcaState.model) || '';
  pick.textContent = '';
  for(const m of wanted){
    const option = document.createElement('option');
    option.value = m.id;
    option.textContent = m.id;
    pick.appendChild(option);
  }
  /* ⛔ A MODEL THAT IS NO LONGER OFFERED IS CLEARED, NOT KEPT. Restoring the
     previous value unchecked is how a selector ends up holding something that
     is not in its own list, and the request then goes out for a model the
     provider has stopped serving. */
  if(wanted.some(m => m.id === keep)) pick.value = keep;
  else if(wanted.length) pick.value = wanted[0].id;
  const status = $('orcastatus');
  const source = catalog && catalog.source;
  /* ⛔ WHERE THE LIST CAME FROM IS ON THE ELEMENT, NOT ONLY IN THE SENTENCE.
     A screen reader, a test and a person all need to be able to ask the
     selector what it is showing, and a degraded list that only says so in
     prose is a degraded list that a caller can mistake for the live one. */
  status.dataset.source = source || 'none';
  if(source === 'live'){
    status.textContent = wanted.length + ' models, read from OrcaRouter just now.';
  } else if(source === 'seed'){
    status.textContent = 'OrcaRouter could not be reached, so this is a short '
      + 'verified list rather than the live one'
      + (catalog && catalog.detail ? ' (' + catalog.detail + ')' : '') + '.';
  } else {
    status.textContent = 'No model list yet. Paste a key or sign in, then '
      + 'refresh.';
  }
}
