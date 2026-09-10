/* ---------------- showing and hiding the column ----------------
   Closed until asked for, and it remembers: a panel that reopens itself every
   time the page loads is a panel that ignores what you told it. Per browser
   rather than per conversation - which panels you keep open is a habit, not a
   property of the work. */
const RAILKEY = 'aihawk.rail';
function showRail(open){
  $('rail').hidden = !open;
  $('railtab').setAttribute('aria-expanded', open ? 'true' : 'false');
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
  if(open) drawChats();
}
$('railtab').onclick = () => showRail($('rail').hidden);
try { showRail(localStorage.getItem(RAILKEY) === '1'); } catch(err){ showRail(false); }

async function renameChat(id, was){
  const name = prompt('Name this session', was);
  if(name === null) return;
  /* The server refuses a name that is only spaces and says so with
     `renamed:false`; without reading it the column simply redrew the old
     name, which reads as the rename having been ignored. */
  const r = await ask('/sessions/rename', {id, name}, 'Could not rename it');
  if(r && !(await r.json()).renamed){
    orphan('err', 'A session needs a name with something in it.');
  }
  drawChats();
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
    const r = await fetch('/sessions/forget', {method:'POST',
                          headers:{'Content-Type':'application/json'},
                          body: JSON.stringify({id})});
    gone = r.ok && (await r.json()).forgotten;
  } catch(err){ gone = false; }
  if(!gone){
    orphan('err', 'That session is still working, so it was not deleted. '
           + 'Stop its run first, then delete it.');
    drawChats();
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

