/* ---------------- the model list ----------------
   The control the OrcaRouter provider picks a model with, as a listbox this
   page draws rather than a native `<select>`.

   ⛔ WHY NOT A `<select>`, WHICH WOULD HAVE BEEN SHORTER. A native select
   draws its open state as an operating-system popup: not part of the document,
   not styleable, and invisible to anything reading or photographing the page -
   so the one control this change exists to add would be the one control nobody
   could show. The requirement is a list and not a text box; a listbox is that
   requirement met where the list is a thing on screen.

   ⛔ AND THE KEYBOARD IS PART OF THE CONTROL. A native select is reachable,
   expandable and committable without a mouse. A listbox that only answered
   clicks would be a control this page took away from the keyboard, so the
   arrows open and move, Enter commits, and Escape closes the list rather than
   the card behind it - which is the same rule the sessions panel applies one
   level out: the innermost thing that owns a key gets it.

   The options themselves are written by `drawProvider` from one answer, into
   `providerOptions`. Nothing here invents an id, and nothing here reads the
   catalogue: this file moves a cursor over a list somebody else filled. */

function modelRow(id, chosen, here){
  const row = el('button','opt',id);
  row.type = 'button';
  row.dataset.model = id;
  row.setAttribute('role','option');
  row.setAttribute('aria-selected', id === chosen ? 'true' : 'false');
  if(here) row.dataset.here = '1';
  row.onclick = () => chooseProviderModel(id);
  return row;
}

function drawProviderList(){
  const list = $('provlist');
  if(!list) return;
  /* Emptied through `removeChild` rather than by writing its text: a text write
     leaves the rows behind in some engines, so the list would grow by one copy
     of every model on every redraw. */
  while(list.children.length) list.removeChild(list.children[0]);
  const chosen = $('provmodel').dataset.chosen || '';
  providerOptions.forEach((id, n) => {
    list.appendChild(modelRow(id, chosen, n === providerPick));
  });
  list.hidden = !providerOpen;
  $('provmodel').setAttribute('aria-expanded', providerOpen ? 'true' : 'false');
  /* ⛔ AND THE CARD IS SCROLLED TO HOLD THE OPEN LIST. Measured on the running
     page: the card is taller than the window, the list opens downward from a
     control near the bottom of it, and the card's own `overflow:auto` cut the
     list off - one row of three was on screen and the point in the middle of
     the list belonged to the panel behind it, so the other two could not be
     pressed at all. The card scrolls, so the fix is to scroll it. */
  if(providerOpen && list.scrollIntoView) list.scrollIntoView({block:'nearest'});
}

function toggleProviderModels(){
  providerOpen = !providerOpen;
  drawProviderList();
}

function closeProviderModels(){
  if(!providerOpen) return;
  providerOpen = false;
  drawProviderList();
}

function moveProviderChoice(step){
  if(!providerOptions.length) return;
  providerPick = (providerPick + step + providerOptions.length) % providerOptions.length;
  drawProviderList();
  const here = $('provlist').children[providerPick];
  if(here && here.scrollIntoView) here.scrollIntoView({block:'nearest'});
}

function providerModelKey(e){
  if(e.key === 'Escape'){ e.stopPropagation(); closeProviderModels(); return; }
  if(e.key === 'ArrowDown' || e.key === 'ArrowUp'){
    e.preventDefault();
    if(!providerOpen){ toggleProviderModels(); return; }
    moveProviderChoice(e.key === 'ArrowDown' ? 1 : -1);
    return;
  }
  if(e.key === 'Enter'){
    e.preventDefault();
    if(!providerOpen){ toggleProviderModels(); return; }
    const id = providerOptions[providerPick];
    if(id) chooseProviderModel(id);
  }
}
