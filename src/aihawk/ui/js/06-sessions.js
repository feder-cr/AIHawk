/* ---------------- the session column ----------------
   Drawn from the server every time it changes rather than kept in step by hand:
   a name is set by the FIRST INSTRUCTION of a conversation, which happens on
   the server, so a column the page maintained locally would be right until
   somebody actually used a session. */
async function drawChats(){
  /* ⛔ THREE OUTCOMES, AND THE OLD CODE HAD TWO. A list that could not be
     LOADED returned early and left whatever was drawn before, and a list that
     arrived empty said `No saved conversations yet`, which was also what a
     failed fetch showed if nothing had been drawn yet: a lie in the shape of
     an empty state. `null` is the answer for "I do not know". */
  let rows = null;
  try { const r = await plainDoor('/sessions', {cache:'no-store'});
        if(r.ok) rows = (await r.json()).sessions || []; }
  catch(err){ rows = null; }
  const box = $('chats');
  box.textContent = '';
  /* The panel's line belongs to the list as it was: any redraw of the list is
     a new answer to whatever it was complaining about. */
  railsay('');
  /* An empty column is a state, not a blank: on a first run there is exactly
     one conversation and it is this one, so the panel would otherwise open on
     nothing at all. */
  /* A paragraph is not a list item, and `role="list"` promises that everything
     inside it is one. With nothing to list, the box stops claiming to be a
     list rather than holding one invalid child. */
  if(rows && rows.length) box.setAttribute('role', 'list');
  else box.removeAttribute('role');
  if(rows === null){
    box.appendChild(el('p','none', 'The list could not be loaded. It is asked '
                       + 'for again the next time this panel opens.'));
    return;
  }
  if(!rows.length){
    const none = el('p','none', 'No saved conversations yet. This one is saved '
                    + 'as soon as you send an instruction.');
    box.appendChild(none);
  }
  for(const s of rows){
    const row = el('div','chat');
    row.setAttribute('role','listitem');
    const open = el('button', 'nm', s.name || s.id);
    open.type = 'button';
    /* ⛔ ON THE BUTTON, NOT ON THE ROW AROUND IT. `aria-current` was set on the
       `listitem` wrapper, which is a container with no name of its own, so the
       one conversation a person is actually in was announced to nobody: you
       hear the name from the button and the "current" from a node the reader
       walks straight past. The mark goes on the thing that says the name. */
    if(s.id === here) open.setAttribute('aria-current','true');

    /* Switching is a NAVIGATION, not a repaint: the transcript, the picture and
       the stream all belong to the conversation, and the server hands back the
       whole of it for an id. Rebuilding that by hand would be a second
       implementation of what a page load already does correctly. */
    /* ⛔ AND IT CLOSES ON THE WAY OUT, UNCONDITIONALLY. The panel stayed open
       across the navigation, so the conversation you had just chosen arrived
       already covered by the panel you chose it from - and choosing the one you
       were already in left it open over the same page for no reason at all.
       `showRail` is the one writer of the remembered state, so closing through
       it is also what stops the next page load reopening it. */
    open.onclick = () => {
      showRail(false);
      if(s.id !== here) location.search = '?s=' + encodeURIComponent(s.id);
    };
    open.ondblclick = () => renameChat(s.id, s.name || s.id);
    /* ⛔ AND A KEY, because a double click is not a keyboard path and nothing
       on the screen advertises it. F2 is what renames a thing in a list
       everywhere else on this machine. */
    open.onkeydown = (e) => { if(e.key === 'F2') renameChat(s.id, s.name || s.id); };
    open.title = (s.name || s.id) + ' - F2 to rename';
    /* Drawn for the keyboard, which the native tooltip never serves: the tip
       appears on the row when its name has keyboard focus, and nowhere else. */
    row.dataset.tip = 'F2 renames';
    row.appendChild(open);
    if(s.turns) row.appendChild(el('span','cnt', String(s.turns)));
    const kill = el('button','x','x');
    kill.type = 'button';
    kill.title = 'Delete this session and close its browsers';
    kill.setAttribute('aria-label', 'Delete ' + (s.name || s.id));
    kill.onclick = (e) => { e.stopPropagation(); forgetChat(s.id, s.name || s.id); };
    row.appendChild(kill);
    box.appendChild(row);
  }
}

