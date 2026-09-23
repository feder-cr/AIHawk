/* ---------------- the workspace ----------------
   What the right half of the page is showing, in ONE place. Two of these are
   the server's and two are this page's own, and keeping them in one object is
   what makes that legible: `fleet` is which browsers this session holds and
   `focus` is the one the AGENT is driving, both read from `/live/browsers`
   every three seconds; `pinned` is the screen the PERSON chose to watch, and
   `grid` how many screens the stage shows, which follows the browsers that are
   running. `turn` is which screen the frame pump asks next.

   Until 0.52.0 these were six top-level variables across three files, one of
   them called `pinned2` because `pinned` was already taken by the transcript's
   scroll - a name that said "there was a clash" and nothing else.

   ⛔ TWO DIFFERENT THINGS, AND THEY USED TO BE ONE. `focus` is the browser the
   AGENT drives - it lives on the server and only the agent moves it, by being
   asked. `pinned` is the pane the PERSON is looking at, which is this page's
   own business and nobody else's.

   They were the same value until somebody said everything should be commanded
   from the chat, and folding them together is what made clicking a pane a
   COMMAND. Now the big pane follows the agent, which is what you want while it
   works, and looking somewhere else is a choice that sticks until you undo it.

   ⛔ AND THE PARAGRAPH ABOVE WAS TRUE OF THE PAGE AND FALSE OF THE SERVER
   UNTIL 0.55.0. `focus` arrived as the constant `main`, because the tools
   that moved a focus went with the eight-browser session and nothing replaced
   them, so the dot below reading `the agent is working here` sat on `main`
   while the agent typed into `support`. The server answers where the last
   command acted now, so what this file has always said is finally what
   arrives. */
const stage = {fleet: [], focus: '', pinned: null, grid: 1, turn: 0};
const watched = () => stage.pinned || stage.focus;

/* Looking, not commanding. Clicking the pane you are already watching gives
   the view back to the agent, so there is a way out of a choice as well as in.
   Nothing is sent: what the person looks at is not the agent's business. */
function watchThis(id){
  stage.pinned = (stage.pinned === id) ? null : id;
  drawStage(); paintWhere();
}
