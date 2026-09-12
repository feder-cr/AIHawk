/* ---------------- showing and hiding the column ----------------
   Closed until asked for, and it remembers: a panel that reopens itself every
   time the page loads is a panel that ignores what you told it. Per browser
   rather than per conversation - which panels you keep open is a habit, not a
   property of the work. */
const RAILKEY = 'aihawk.rail';

/* The panel's own line, for what the panel itself failed to do. Emptied by the
   next `drawChats`, so nothing has to remember to clear it. */
function railsay(words){ $('railsay').textContent = words || ''; }

/* ⛔ OPENING IT PUTS THE PAGE BEHIND IT OUT OF PLAY, AND THAT IS THE WHOLE
   CORRECTION. It used to lie over the near edge of the conversation and leave
   it looking readable: 240px off the front of every line, 29 rows at a time,
   the verb and the step number underneath the panel. The words were not gone,
   they were unreachable while still inviting you to read them.

   Now the two panes are held inert - dimmed to 2.36:1 by the shell's one
   `[inert]` rule, out of the tab order, out of reach of the pointer - so what
   is covered is visibly not in play. That is only honest because it is also
   cheap to undo: Escape, a click on the page behind, or choosing a name, all
   below.

   Held through `outOfPlay` rather than written here, because the browser pane has a
   second reason to be out of play - a conversation deleted elsewhere - and
   whichever of the two let go last would otherwise revive it. */
function showRail(open){
  const rail = $('rail');
  /* Where the keyboard was, before hiding the panel can take it away: a
     subtree that holds the focus and goes `hidden` drops it on the document,
     and the next Tab starts at the top of the page instead of at the control
     that was just used. */
  const hadFocus = !open && rail.contains(document.activeElement);
  rail.hidden = !open;
  $('railtab').setAttribute('aria-expanded', open ? 'true' : 'false');
  for(const box of [$('left'), $('right')]) outOfPlay(box, 'sessions', open);
  /* ⛔ AND NO aria-label ANY MORE. It used to say "Show sessions" / "Hide
     sessions", which was right while the control was three lines and nothing
     else. Now the button says Sessions in words, and an aria-label REPLACES
     that name: a screen reader would read a word that is not on the button,
     and somebody driving by voice who says "Sessions" would find nothing to
     click. The open state is already carried by aria-expanded, which is the
     attribute for it. Found by reading the live DOM after the change, not the
     source: removing the attribute from the markup left this line putting it
     back. */
  try { localStorage.setItem(RAILKEY, open ? '1' : '0'); } catch(err){}
  if(open){
    drawChats();
    /* The keyboard follows the eyes. Tab would walk in here anyway, but
       Escape, the arrows and a screen reader all start from wherever the focus
       is standing - which, a moment after this, is behind an inert subtree
       none of them can reach. */
    $('newchat').focus();
  } else if(hadFocus){
    $('railtab').focus();
  }
}
$('railtab').onclick = () => showRail($('rail').hidden);

/* ⛔ ESCAPE, ON THE WAY DOWN, AND THE INTERCEPTION IS DELIBERATE. Two other
   handlers on `document` answer this key: one stops the run, the other resets
   the split. Capture runs before both, so `stopPropagation` here keeps the key
   from reaching them, and that is the point rather than a side effect - while
   a modal is up, Escape means close the modal and nothing else, which is what
   it means in every other window on the machine. Without this the key a person
   presses to dismiss a panel STOPPED THE AGENT instead. */
addEventListener('keydown', (e) => {
  if(e.key !== 'Escape' || $('rail').hidden) return;
  e.stopPropagation();
  showRail(false);
}, true);

/* And a press on the page behind it, which is the other half of what makes
   covering honest. Both guards are needed and the second one is not obvious:
   without it, pressing the spine closes the panel here and the button's own
   handler reopens it in the same gesture, so the one control that opens the
   panel could never close it. */
addEventListener('pointerdown', (e) => {
  if($('rail').hidden) return;
  if($('rail').contains(e.target) || $('railtab').contains(e.target)) return;
  showRail(false);
}, true);

try { showRail(localStorage.getItem(RAILKEY) === '1'); } catch(err){ showRail(false); }

async function renameChat(id, was){
  const name = prompt('Name this session', was);
  if(name === null) return;
  /* The server refuses a name that is only spaces and says so with
     `renamed:false`; without reading it the column simply redrew the old
     name, which reads as the rename having been ignored. */
  const r = await ask('/sessions/rename', {id, name}, 'Could not rename it');
  const refused = r && !(await r.json()).renamed;
  /* The draw first and the sentence after, in that order: `drawChats` empties
     the panel's line, so a sentence written before it would be wiped by the
     redraw it was written about. */
  await drawChats();
  if(refused) railsay('A session needs a name with something in it.');
}

async function forgetChat(id, name){
  /* The browsers go with it, and that is worth saying before it happens rather
     than after: a session can be holding eight logged-in engines. */
  if(!confirm('Delete "' + name + '"? Its conversation and its browsers go with it.')) return;
  /* ⛔ AND THE ANSWER IS READ. The server REFUSES to delete a session whose
     agent is mid-run, and answers 200 with `forgotten:false`. Ignoring the
     body meant confirming a delete, being navigated away, and leaving the
     session and its browsers exactly where they were: every visible signal
     said it had worked. */
  let gone = false;
  try {
    const r = await plainDoor('/sessions/forget', {method:'POST',
                          headers:{'Content-Type':'application/json'},
                          body: JSON.stringify({id})});
    gone = r.ok && (await r.json()).forgotten;
  } catch(err){ gone = false; }
  if(!gone){
    /* ⛔ AND IT IS SAID IN THE PANEL, NOT IN THE TRANSCRIPT. This went to the
       conversation, which is the thing the panel is lying on top of and the
       page has just put out of play: the sentence landed where the person who
       pressed the button could not read it. */
    await drawChats();
    railsay('That session is still working, so it was not deleted. '
            + 'Stop its run first, then delete it.');
    return;
  }
  if(id === here){ location.search = ''; return; }
  drawChats();
}

$('newchat').onclick = async (e) => {
  /* ⛔ AND ONLY ONCE. Two fast clicks made two sessions, the second
     navigation won, and the first stayed behind as an empty conversation
     nobody asked for and nobody would ever open. */
  const b = e.currentTarget;
  if(b.disabled) return;
  b.disabled = true;
  const r = await ask('/sessions/new', undefined, 'Could not start a session');
  if(!r){ b.disabled = false; return; }
  const j = await r.json();
  location.search = '?s=' + encodeURIComponent(j.id);
};

