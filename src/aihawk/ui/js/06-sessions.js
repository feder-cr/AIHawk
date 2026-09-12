/* ---------------- the session column ----------------
   Drawn from the server every time it changes rather than kept in step by hand:
   a name is set by the FIRST INSTRUCTION of a conversation, which happens on
   the server, so a column the page maintained locally would be right until
   somebody actually used a session. */
async function drawChats(){
  let rows = [];
  try { const r = await plainDoor('/sessions', {cache:'no-store'});
        if(r.ok) rows = (await r.json()).sessions || []; }
  catch(err){ return; }
  const box = $('chats');
  box.textContent = '';
  /* An empty column is a state, not a blank: on a first run there is exactly
     one conversation and it is this one, so the panel would otherwise open on
     nothing at all. */
  if(!rows.length){
    const none = el('p','none', 'No saved conversations yet. This one is saved '
                    + 'as soon as you send an instruction.');
    box.appendChild(none);
  }
  for(const s of rows){
    const row = el('div','chat');
    row.setAttribute('role','listitem');
    if(s.id === here) row.setAttribute('aria-current','true');
    const open = el('button', 'nm', s.name || s.id);
    open.type = 'button';

    /* Switching is a NAVIGATION, not a repaint: the transcript, the picture and
       the stream all belong to the conversation, and the server hands back the
       whole of it for an id. Rebuilding that by hand would be a second
       implementation of what a page load already does correctly. */
    open.onclick = () => { if(s.id !== here) location.search = '?s=' + encodeURIComponent(s.id); };
    open.ondblclick = () => renameChat(s.id, s.name || s.id);
    /* ⛔ AND A KEY, because a double click is not a keyboard path and nothing
       on the screen advertises it. F2 is what renames a thing in a list
       everywhere else on this machine. */
    open.onkeydown = (e) => { if(e.key === 'F2') renameChat(s.id, s.name || s.id); };
    open.title = (s.name || s.id) + ' - F2 to rename';
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

