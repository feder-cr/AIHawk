/* ---------------- the provider card ----------------
   Which model this conversation runs on, and the two ways to hold an
   OrcaRouter credential. Everything here goes through `door` and `ask`, the
   page's one door for requests, so a card that is open when the conversation
   is deleted is put out of play by the same code that does it for the rest of
   the page.

   ⛔ THE KEY NEVER COMES BACK FROM THE SERVER, AND THIS FILE NEVER ASKS FOR IT.
   The server answers with a mask, a method and a generation; the field this
   page sends a key through is emptied the moment it is accepted, and the value
   is not put in a status line, an error or the transcript. A secret in a
   browser is a secret in a screenshot, a devtools session and a crash report.

   ⛔ THE MODEL CONTROL IS A LIST THE SERVER FILLS, AND IT CANNOT BE TYPED IN.
   There is no free-text box anywhere in this file and there is no `<select>`
   either: a native select draws its open state as an operating-system popup,
   which is not part of the page, cannot be styled, and is what makes the list
   invisible to anything reading or photographing the document. So the control
   is a button that expands a listbox built from the same answer - same
   requirement, a list and not a text box, and the open list is a thing on
   screen. A model id typed from memory is a request that fails at the first
   turn with the reason nowhere near the cause; the list is the account's own,
   read from the catalogue, and when discovery fails what is offered is the
   verified seed with the panel saying so.

   The sign-in half - the attempt number, the code, the cancellation and the
   back-forward-cache handler - is the next file. It is a separate piece
   because the card that draws the two ways in and the state machine that
   finishes one of them are two jobs, and one file holding both was over the
   ceiling this project puts under every piece of the page. */
let providerState = null;
let providerWay = 'key';
let providerOptions = [];
let providerOpen = false;
let providerPick = 0;
let signInAttempt = 0;
let signInBusy = false;

/* The card is built once and shown or hidden, so nothing in it is a second
   declaration of a fact the server owns: every value below is written from an
   answer, never from the markup. */
function providerCard(){
  let card = $('provider');
  if(card) return card;
  card = el('div');
  card.id = 'provider';
  card.setAttribute('role','dialog');
  card.setAttribute('aria-modal','true');
  card.setAttribute('aria-labelledby','provtitle');
  card.hidden = true;

  const box = el('div','card');
  const head = el('div','prow');
  const title = el('h2', null, 'OrcaRouter');
  title.id = 'provtitle';
  const grow = el('span','grow');
  const close = el('button','close','Close');
  close.type = 'button';
  close.onclick = () => showProvider(false);
  head.appendChild(title); head.appendChild(grow); head.appendChild(close);
  box.appendChild(head);
  box.appendChild(el('p','why','OrcaRouter is an OpenAI-compatible gateway that '
    + 'routes many providers behind one endpoint. Either paste a key from your '
    + 'console, or sign in and one is issued for you.'));

  /* The two roads, as two labelled choices rather than one button that
     sometimes asks for a key and sometimes opens a browser. */
  const ways = el('div','ways');
  ways.setAttribute('role','group');
  ways.setAttribute('aria-label','How to give OrcaRouter a credential');
  for(const [id, word] of [['key','API key'], ['oauth','Sign in']]){
    const b = el('button', null, word);
    b.type = 'button';
    b.setAttribute('aria-pressed', id === providerWay ? 'true' : 'false');
    b.onclick = () => chooseWay(id);
    ways.appendChild(b);
  }
  box.appendChild(ways);

  const keyWay = el('div','way');
  keyWay.id = 'provkey';
  const keyHow = el('p','how','Paste an sk-orca-... key from '
    + 'orcarouter.ai/console. It is billed to your account and you can revoke '
    + 'it there.');
  const keyLabel = el('label','lbl','OrcaRouter API key');
  keyLabel.setAttribute('for','provinput');
  const keyInput = el('input');
  keyInput.id = 'provinput';
  keyInput.type = 'password';
  keyInput.autocomplete = 'off';
  keyInput.spellcheck = false;
  keyInput.placeholder = 'sk-orca-...';
  const keyActs = el('div','acts');
  const keySave = el('button', null, 'Save key');
  keySave.type = 'button';
  keySave.onclick = () => saveProviderKey();
  const keyClear = el('button','plain','Remove');
  keyClear.type = 'button';
  keyClear.onclick = () => removeProviderKey();
  keyActs.appendChild(keySave); keyActs.appendChild(keyClear);
  keyWay.appendChild(keyHow); keyWay.appendChild(keyLabel);
  keyWay.appendChild(keyInput); keyWay.appendChild(keyActs);
  box.appendChild(keyWay);

  const oauthWay = el('div','way');
  oauthWay.id = 'provoauth';
  const oauthHow = el('p','how','A browser opens on the consent screen and you '
    + 'approve once. No client secret and no redirect address to register: the '
    + 'code is bound to this process, so nobody who intercepts it can use it.');
  const oauthActs = el('div','acts');
  const connect = el('button', null, 'Connect with OrcaRouter');
  connect.id = 'provconnect';
  connect.type = 'button';
  connect.onclick = () => connectProvider();
  const cancel = el('button','plain','Cancel');
  cancel.id = 'provcancel';
  cancel.type = 'button';
  cancel.hidden = true;
  cancel.onclick = () => cancelProvider();
  oauthActs.appendChild(connect); oauthActs.appendChild(cancel);
  const manual = el('div','way');
  manual.id = 'provmanual';
  manual.hidden = true;
  const manualLabel = el('label','lbl','Code from the consent screen');
  manualLabel.setAttribute('for','provcode');
  const manualInput = el('input');
  manualInput.id = 'provcode';
  manualInput.type = 'password';
  manualInput.autocomplete = 'off';
  manualInput.spellcheck = false;
  const manualActs = el('div','acts');
  const send = el('button','plain','Use this code');
  send.type = 'button';
  send.onclick = () => submitProviderCode();
  manualActs.appendChild(send);
  manual.appendChild(manualLabel); manual.appendChild(manualInput);
  manual.appendChild(manualActs);
  oauthWay.appendChild(oauthHow); oauthWay.appendChild(oauthActs);
  oauthWay.appendChild(manual);
  box.appendChild(oauthWay);

  const keyline = el('div','keyline');
  keyline.appendChild(el('span', null, 'Credential'));
  const masked = el('code', null, 'not set');
  masked.id = 'provmasked';
  keyline.appendChild(masked);
  box.appendChild(keyline);

  /* ⛔ A BUTTON AND A LIST, NOT A `<select>`. See the note at the top of this
     file: the open state of a native select is drawn by the operating system,
     outside the document, so the one control this change exists to add is the
     one control a page reader or a screenshot cannot see. */
  const modelLabel = el('label','lbl','Model');
  modelLabel.id = 'provmodellbl';
  const trigger = el('button','trigger');
  trigger.id = 'provmodel';
  trigger.type = 'button';
  trigger.setAttribute('aria-labelledby','provmodellbl');
  const chosen = el('span','grow');
  chosen.id = 'provchosen';
  trigger.appendChild(chosen);
  trigger.appendChild(el('span','caret','v'));
  trigger.onclick = () => toggleProviderModels();
  const list = el('div','list');
  list.id = 'provlist';
  list.setAttribute('role','listbox');
  list.setAttribute('aria-labelledby','provmodellbl');
  list.hidden = true;
  const picker = el('div','picker');
  /* One key handler on the container, so the arrows and Enter work whether the
     focus is on the trigger or on a row of the list the trigger expanded. */
  picker.onkeydown = (e) => providerModelKey(e);
  picker.appendChild(trigger);
  picker.appendChild(list);
  const src = el('p','src');
  src.id = 'provsrc';
  const say = el('p','say');
  say.id = 'provsay';
  say.setAttribute('role','status');
  const hint = el('p','hint');
  hint.appendChild(el('span', null, 'Manage or revoke keys at '));
  /* ⛔ NOT A LINK, AND THAT IS THE PAGE'S RULE RATHER THAN THIS FILE'S. An
     anchor built here would be a clickable thing beside a browser this page is
     already driving, and the page refuses to build one at all. The address is
     shown as text to copy, which is also what a person on a locked-down
     machine needs. */
  hint.appendChild(el('code', null, 'orcarouter.ai/console/authorized-apps'));
  box.appendChild(modelLabel); box.appendChild(picker);
  box.appendChild(src); box.appendChild(say); box.appendChild(hint);

  card.appendChild(box);
  document.body.appendChild(card);
  return card;
}

function providerSay(word, bad, good){
  const say = $('provsay');
  if(!say) return;
  say.textContent = word || '';
  if(bad) say.dataset.bad = '1'; else delete say.dataset.bad;
  if(good) say.dataset.ok = '1'; else delete say.dataset.ok;
}

/* The card is a modal over the two panes, the way the sessions column is: the
   conversation behind it goes out of play rather than staying reachable. */
function showProvider(open){
  const card = providerCard();
  card.hidden = !open;
  if(!open) closeProviderModels();
  for(const box of [$('left'), $('right')]) outOfPlay(box, 'provider', !!open);
  if(open){
    providerSay('');
    refreshProvider();
    const field = providerWay === 'key' ? $('provinput') : $('provmodel');
    if(field) field.focus();
  }
}

function chooseWay(id){
  providerWay = id;
  for(const b of providerCard().querySelectorAll('.ways button'))
    b.setAttribute('aria-pressed', b.textContent === (id === 'key' ? 'API key' : 'Sign in')
                    ? 'true' : 'false');
  $('provkey').hidden = id !== 'key';
  $('provoauth').hidden = id !== 'oauth';
  providerSay('');
}

async function refreshProvider(){
  /* ⛔ `door`, NOT `ask`, BECAUSE THIS ONE IS A READ. `ask` posts, and these
     two routes answer a question rather than change anything: a POST to them is
     a 405, and the panel then opened with an empty list and no mask. Found on
     the running page - the suite had the paths and not the verbs. */
  const r = await door('/provider/state');
  if(!r.ok) return;
  drawProvider(await r.json());
}

/* ⛔ THE WHOLE CARD IS WRITTEN FROM ONE ANSWER. Provider, credential, model and
   source arrive together because they are one fact about one process; drawing
   them from separate answers is how the header ends up naming a model the
   dropdown is not offering. */
function drawProvider(state){
  if(!state) return;
  providerState = state;
  const credential = state.credential || {};
  $('provmasked').textContent = credential.set ? credential.masked
                                              : 'not set';
  if(credential.needs_reauth && !signInBusy)
    providerSay('OrcaRouter refused this key, so it needs signing in again. '
                + 'Nothing was deleted.', true, false);
  /* ⛔ THE OPTIONS COME FROM THE ANSWER AND FROM NOWHERE ELSE, and they are
     kept in one array the listbox is drawn from - so what the key handler
     moves through and what the list shows cannot be two different lists. */
  providerOptions = (state.models || []).map(m => m.id);
  $('provchosen').textContent = state.model || (providerOptions.length
    ? 'Choose a model' : 'No model list yet');
  $('provmodel').dataset.chosen = state.model || '';
  if(!providerOpen) providerPick = Math.max(0, providerOptions.indexOf(state.model || ''));
  drawProviderList();
  const src = $('provsrc');
  if(state.source === 'seed'){
    /* ⛔ SAID, NOT HIDDEN. A seed presented as the account's own catalogue is a
       claim about somebody's account that nobody verified, and the person is
       about to send a request against one of these ids. */
    src.textContent = 'Showing the verified short list: the model catalogue '
      + 'could not be read' + (state.catalog_error ? ' (' + state.catalog_error + ')' : '')
      + '. Press Refresh to try again.';
  } else {
    src.textContent = providerOptions.length
      ? 'From this account\'s catalogue at api.orcarouter.ai/v1/models, '
        + providerOptions.length + ' model' + (providerOptions.length === 1 ? '' : 's') + '.'
      : 'The catalogue answered with no model this client can call.';
  }
  const badge = $('model');
  if(state.provider !== 'openrouter'){
    badge.textContent = state.model || 'OrcaRouter: no model chosen';
    badge.hidden = false;
  }
}

async function saveProviderKey(){
  const field = $('provinput');
  const given = (field.value || '').trim();
  if(!given){ providerSay('Paste a key first.', true, false); return; }
  const r = await ask('/provider/key', {key: given}, 'The key could not be saved');
  /* ⛔ EMPTIED BEFORE THE ANSWER IS READ, on every path. The value has been
     sent; leaving it in the field is leaving it in a screenshot, in a
     screen-share and in whatever the browser restores after a crash. */
  field.value = '';
  if(!r) return;
  const state = await r.json();
  if(state.error){ providerSay(state.error, true, false); return; }
  drawProvider(state);
  providerSay(state.note || 'Saved.', false, true);
}

async function removeProviderKey(){
  const r = await ask('/provider/key', {remove: true}, 'The key could not be removed');
  if(!r) return;
  const state = await r.json();
  drawProvider(state);
  providerSay(state.note || 'Removed.', false, true);
}

async function refreshProviderModels(){
  const r = await door('/provider/refresh', {method:'POST'});
  if(!r.ok) return;
  drawProvider(await r.json());
}

/* ⛔ THE MODEL IS CHANGED ON THE SERVER, and the answer is what the control is
   redrawn from. Writing the choice here first and hoping the server agreed is
   how the control and the request come to disagree - and the server is the one
   that knows whether the model is still in the compatible list. */
async function chooseProviderModel(wanted){
  closeProviderModels();
  const r = await ask('/provider/choose', {provider: providerState
                        ? providerState.provider : 'orcarouter', model: wanted},
                      'The model could not be selected');
  if(!r) return;
  const state = await r.json();
  drawProvider(state);
  if(state.refused || !state.model)
    providerSay(state.note || 'That model is not offered by this provider.', true, false);
  else
    providerSay('Running on ' + state.model + '.', false, true);
}

/* ⛔ THE HEADER CONTROL IS WIRED HERE, WHERE THE CARD IS. The card is built by
   this file and nothing else knows what it is called, so the line that opens it
   lives beside the code that draws it rather than in the boot sequence - one
   file owns the panel, and a reader looking for "what does the Provider button
   do" finds the whole answer in one place. */
function wireProviderOpen(){
  const open = $('provopen');
  if(open) open.onclick = () => showProvider(true);
}
wireProviderOpen();
