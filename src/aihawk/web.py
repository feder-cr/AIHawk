"""The two-pane interface: conversation on the left, the live browser on the right.

This used to live inside the MCP server and reach the browser through a Python
object in the same process. It lives here now, and it reaches the browser the way
everybody else does: over MCP, calling the same tools any agent gets.
The server went back to being only a server.

That is not a tidier arrangement of the same code, it changes what is true about
each side. The MCP package now has no opinion about being looked at, so nothing
in it has to be kept working for the sake of a page. And this interface has no
privileged access, so anything it can do, somebody else's client can also do -
which is the strongest guarantee available that the tools are sufficient.

Three consequences, each handled rather than hidden:

  The live view cannot ask "is a browser running" without starting one, because
  `session_list_pages` calls `ensure`. `Link` remembers whether an instruction
  has been issued and the view stays quiet until then.

  Frames and actions share one pipe. They are serialised in `Link`, and they
  would have been serialised by the browser anyway.

  The page URL is no longer free. It is fetched on its own slower timer rather
  than with every frame, so watching costs one cheap call every two seconds.

The picture on the right is `browser_watch`: the window as a person at the
machine sees it - tab strip, address bar, the page and the pointer - from a
capture the server keeps running on the active tab. It is not
`browser_take_screenshot`, which the pane was built on until 2026-09-06. A
screenshot is the page alone, and the engine draws the pointer outside the page
on purpose so that no page can see it, so that pane could never show where the
agent's hand was; and a page mid-load cannot be painted, so the pane went blank
on every navigation. The window is always there to be captured, and a frame is
one JPEG the server already holds rather than a paint it has to do.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncIterator, Dict, List, Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from .brain import Brain
from .link import Link, SessionLink, image_of, text_of
from .mcp import store

# A RAW string. The script below contains \n, \w and \s inside JavaScript
# literals and regular expressions; in an ordinary triple-quoted string Python
# would turn `'\n'` into a real newline before the browser ever saw it, and the
# regex would quietly mean something else. Same family as the rule about
# backslashes through a shell heredoc: nothing errors, the text is just no
# longer the text that was written.
PAGE = r"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AIHawk</title>
<style>
:root{
  color-scheme: dark;

  /* Surfaces as a ladder rather than two greys. The steps widen going up
     (5,7,7,8) because equal hex steps read as progressively smaller the lighter
     they get. */
  --well:   #0b0d10;   /* recessed: behind the frame, the deepest thing here */
  --base:   #101317;   /* the ground */
  --raised: #171b21;   /* composer, header, browser chrome, expanded output */
  --hover:  #1e232a;   /* row hover, and the user's own bubble */
  --top:    #262c34;   /* a control sitting on --hover */

  /* Edges are translucent white, never a hex: rgba composites correctly on
     every rung, so a component can move up the ladder without its border being
     picked again. */
  --line-1: rgba(255,255,255,.06);
  --line-2: rgba(255,255,255,.09);
  --line-3: rgba(255,255,255,.14);
  --lip:    inset 0 1px 0 rgba(255,255,255,.045);

  /* ⛔ THE LADDER IS PICKED FROM THE USE SCENE, NOT FROM THE CATEGORY. This
     interface is watched during long runs in a room with the lights off - the
     screen is the only light - so the ground stays near black and nothing on it
     is pure white: a full white on a dark ground at night is a lamp pointed at
     the reader. The accent moves off coral onto amber for the same reason, that
     being the warm end that disturbs dark-adapted eyes least, and every rung
     gains headroom over the floor rather than sitting on it.

     Ink, with the contrast each one carries against --base. */
  --fg:   #dfe4e8;   /* 14.5:1  what the user typed, what the model answered */
  --fg-2: #a6b0b8;   /*  8.4:1  narration and chrome labels */
  --fg-3: #8d98a1;   /*  6.3:1  tool output and arguments, and every quiet word */
  /* ⛔ AND `--fg-4` NEVER COLOURS WORDS. It was carrying the count beside a
     conversation, the address under a link, the timing on a step, the marker of
     a list, the dim halves of the URL and the placeholder inside a preview -
     nine rules, all of them text, all of them at 2.4:1 where AA asks 4.5. The
     worst was the address: it is printed precisely so an injected link can be
     read, and it was the hardest thing on the page to read. */
  --fg-4: #6b747d;   /*  3.9:1  decoration only - a dot, a chevron, never a word.
                                Three to one and not two: a chevron and an idle
                                dot MEAN something, and a graphic that carries
                                meaning has a floor of its own.
                                ⛔ AND MEASURED WHERE IT IS PAINTED, not
                                against the ground. All three of its uses sit on
                                --raised: the idle dot in the browser bar, the
                                chevron of a hovered row, the ring on a stopped
                                browser's chip. At the old value that was 2.96:1
                                - the same defect this ladder fixed for text,
                                repeated one rung up. */

  --accent:    #e0a35f;   /* 8.5:1 */
  --accent-hi: #ecb377;   /* the same amber a step up, for hover */
  --stop:      #d94f45;   /* the one red that is a CONTROL and not a state */
  --stop-hi:   #e0655a;
  --on-accent: #151005;
  --ok:  #79bf94;         /* 8.6:1 */
  --err: #e88b76;         /* 7.4:1 */

  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, "Cascadia Mono", "SF Mono", Menlo, Consolas,
          "Liberation Mono", "DejaVu Sans Mono", monospace;
  /* ⛔ rem AND NOT px, WHICH IS THE DIFFERENCE BETWEEN HONOURING AND IGNORING
     A SETTING SOMEBODY CHANGED FOR THEIR EYES. A default font size set in the
     browser or the system does nothing to a page whose sizes are absolute -
     page zoom still works, but that is a different control and it scales the
     browser view on the right along with the text. web.dev's typography
     accessibility guidance marks `font-size: 16px` "Don't" and `1rem` "Do" for
     exactly this. Same pixels at the default 16px root, so nothing moves for
     anybody who never changed it. */
  /* ⛔ ONE RATIO, AND THE STEPS ARE STEPS. Measured on the running page, the
     left column drew NINE size/weight pairs at 11, 12, 13, 14 and 16px: four
     sizes inside three pixels, which is a scale in name only. A step of 1.08
     is not a step - the eye reads it as an accident - and the fix is not more
     sizes but fewer, with weight and colour carrying the tiers that size no
     longer does.

     Three prose steps on ~1.2: 12 / 15 / 18. Body is 15 because this column
     exists to be read and 14 is under the floor every source gives for reading
     text. */
  --t-label:.75rem;                            /* 12 - labels, meta, counts */
  --t-body:.9375rem;                           /* 15 - prose, and the base */
  --t-ui:.9375rem;                             /* 15 - chrome reads as prose */
  /* ⛔ MONO IS OFF THIS SCALE BY DECISION, NOT BY OVERSIGHT. A mono face runs
     wider and reads larger at the same pixel, so it does not belong on a scale
     built for a proportional one - and the step track is MEASURED against it:
     `LONG` is how many characters fit in 416px at this size, so moving it moves
     a threshold that a gate checks. It is the data face, and it says so here. */
  --t-mono:.8125rem;                           /* 13 - steps, code, addresses */
  /* The answer's headings. One size above the body, then weight and colour:
     three sizes a pixel apart carried nothing that 600 and a quieter ink do
     not carry better. `--t-h1` is the off-screen page heading's size too. */
  --t-h1:1.125rem; --t-h2:.9375rem; --t-h3:.9375rem;

  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:20px; --s6:32px;
  --r-sm:4px; --r:8px; --r-lg:12px; --r-pill:999px;
  --spine:54px;                               /* the sessions band */
  --topbar:50px;                              /* every header, one height */
  --h-ctl:28px;                               /* every control on a bar */
  --gutter:1.75rem;                            /* three digits of 11px mono */
  --gap:.55rem;
  --indent:calc(var(--gutter) + var(--gap));   /* ONE source for the step indent */
}

*{ box-sizing:border-box }
body{ margin:0; height:100vh; display:flex; position:relative;
      background:var(--base); color:var(--fg);
      font:var(--t-body)/1.55 var(--sans); }
code,pre,.g,.meta,.badge,#url{
  font-family:var(--mono);
  /* Not cosmetic: a step reads `#email <- ada@example.com`, and a mono face with
     contextual alternates draws `<-` as one arrow. The text on screen would stop
     being the text the model emitted. */
  font-variant-ligatures:none; }
.meta,.g{ font-variant-numeric:tabular-nums }
/* ⛔ `--fg-4` IS DECLARED DECORATIVE AT 2.4:1 AND THIS CLASS PUT WORDS ON IT.
   Measured on the running page: the state beside the browser read at 2.23:1,
   the meter at 2.71, the placeholder inside a screen at 2.51, the layout icons
   at 2.51. WCAG AA wants 4.5:1 for text and 3:1 for a graphic that carries
   meaning, and the token's own comment in this file says what it is for. A
   label is a small word, not a faint one: `--fg-3` is 4.8:1 and still reads as
   quieter than the thing it labels. */
.label{ font-size:var(--t-label); font-weight:600; letter-spacing:.07em;
        text-transform:uppercase; color:var(--fg-3); line-height:1 }
.sr{ position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%) }
.skip{ position:absolute; left:var(--s2); top:var(--s2); z-index:20;
       padding:8px 12px; background:var(--top); color:var(--fg);
       border:1px solid var(--line-3); border-radius:var(--r);
       font-size:var(--t-ui); text-decoration:none;
       transform:translateY(-200%); transition:transform 120ms ease-out }
.skip:focus{ transform:none }
/* `hidden` must beat any display an id or class sets, or an element the script
   believes it has hidden stays on screen. This shipped once on the live image
   and again on the queued-message chip: both were "hidden" and both were
   visible, because a rule with an id selector outranks the user agent's
   [hidden]. One line, and the whole class is gone. */
[hidden]{ display:none !important }

/* ---------------- panes ---------------- */
/* The session column is FIXED width and the two panes beside it share what is
   left, because the column holds names and a name does not get more readable
   with more room, while the transcript and the picture both do. It collapses
   below 900px rather than squeezing the two things that matter. */
/* ⛔ CLOSED UNTIL SOMEBODY ASKS FOR IT. A column of sessions standing open
   beside a conversation somebody is reading is a list nobody needed yet taking
   a fifth of the width; open by default it reads as scaffolding rather than as
   a choice. It is one keystroke away, it remembers what you last did with it,
   and the toggle lives IN the header row rather than above the list - a control
   floating over a panel is what "bolted on" looks like. */
/* ⛔ IT FLOATS OVER THE CONVERSATION, IT DOES NOT PUSH IT. As a flex sibling
   the column took its width out of the room and everything to its right moved
   the moment it opened, which for a panel you open and shut twenty times an
   hour is the whole layout twitching. Out of flow it costs nothing: the
   conversation stays exactly where it was, the panel lies on top of the near
   edge of it, and because the panel is narrower than the conversation the rest
   of the words are still there to come back to.
   Anchored to the spine's own width so the two are one object, and lifted with
   a shadow rather than a border, because what says "this is over that" is the
   shadow. */
#rail { position:absolute; top:0; bottom:0; left:var(--spine); width:224px;
        z-index:5; display:flex; flex-direction:column;
        background:var(--well); border-right:1px solid var(--line-1);
        box-shadow:14px 0 34px -18px #000 }
/* The header of the column lines up with the header of the conversation beside
   it: same height, same padding, so the two read as one row across the app. */
#railhead{ flex:none; height:var(--topbar); display:flex; align-items:center;
           gap:8px; padding:0 var(--s3) 0 var(--s4);
           border-bottom:1px solid var(--line-1) }
#railhead .label{ flex:1 }
#newchat{ flex:none; width:26px; height:26px; display:grid;
          place-items:center; padding:0; border-radius:7px;
          border:1px solid transparent; background:none;
          color:var(--fg-3); cursor:pointer;
          transition:background-color 120ms ease-out, color 120ms ease-out }
#newchat:hover{ background:var(--raised); color:var(--fg);
                border-color:var(--line-2) }

/* ⛔ THE THREE LINES WERE A GUESS AND THE WORD IS NOT, and the word belongs on
   the EDGE. A hamburger says "there is a menu here" only to somebody who has
   already learned that it does. Written into the frame instead, the full height
   of the window, it is not a control among the header's other controls: it is
   part of the room, always there, and the only way in or out of the column.
   The type is `.label`'s, so the spine and the column it opens read as one word
   in one voice.
   `vertical-rl` turned upside down gives the word bottom to top, which is the
   direction every spine on a shelf uses in this alphabet, and the direction the
   napkin had it. */
/* The accent runs the full height of the spine and stays there whether the
   column is open or shut: asked for on 2026-09-09, and it is the better of the
   two - a line that appears and disappears is a state indicator competing with
   the background, while a line that is always there is the edge of the room,
   and the open state has the background and the ink to say it. It also replaces
   the hairline that used to separate this from what follows. */
#railtab{ flex:none; width:var(--spine); padding:0; cursor:pointer; border:0;
          position:relative; background:var(--base); color:var(--fg-3);
          box-shadow:inset -1px 0 0 var(--accent);
          /* The chevron and the word are two rows of one grid, centred
             together: pinned to the top the arrow sat 450px from the word and
             the two read as separate things on the same strip. */
          display:grid; align-content:center; justify-items:center; gap:12px;
          transition:background-color 120ms ease-out, color 120ms ease-out }
/* ⛔ A WORD ON A WALL IS NOT A BUTTON. At 34px with nothing but letters it read
   as a label somebody had printed on the frame, which is the one thing it must
   not read as - said in those words on 2026-09-09. Wider, and with the same
   chevron the step rows use, drawn from borders rather than an icon: it points
   into the room when the column is shut and back out when it is open, so the
   thing you press also says which way it goes. */
#railtab::before{ content:""; width:5px; height:5px;
                  border-right:1.5px solid currentColor;
                  border-bottom:1.5px solid currentColor;
                  transform:rotate(-45deg) translate(-1px, -1px);
                  transition:transform 150ms ease }
#railtab[aria-expanded="true"]::before{ transform:rotate(135deg) translate(-1px, -1px) }
/* ⛔ THE TEXT TURNS, NOT THE BUTTON. `transform` on the button would rotate the
   whole box with it, so the border and the accent below would be drawn on the
   edge away from the column instead of the one beside it - correct in the
   element's own coordinates and backwards on the screen. */
/* On the label step like every other tracked uppercase word on the page: it
   was the last size in this column that belonged to no scale. The tracking
   stays wider than `.label` because the letters are stacked, not set. */
#railtab span{ writing-mode:vertical-rl; transform:rotate(180deg);
               font:600 var(--t-label)/1 var(--sans); letter-spacing:.2em;
               text-transform:uppercase }
#railtab:hover{ background:var(--raised); color:var(--fg) }
/* Open: the spine lifts a rung and the word goes to full ink. The state is
   drawn on the thing you press, where a hand already is. */
#railtab[aria-expanded="true"]{ background:var(--raised); color:var(--fg) }
#railtab[aria-expanded="true"] span{ display:none }
/* ⛔ THE PANEL FOLDS, THE WAY IN DOES NOT. Both used to disappear at the
   same breakpoint, and `#newchat` lives inside the panel - so a window snapped
   to half a 1366-wide laptop lost every session control at once, with the only
   route left being hand-editing `?s=` in the address bar. The panel is an
   overlay: it costs nothing at any width. */
@media (max-width:900px){ #rail{ width:min(84vw, 224px) } }
#chats{ flex:1; min-height:0; overflow-y:auto; padding:var(--s2) var(--s2) var(--s3);
        /* A long list is cheap to skip past: the rows below the fold are not
           laid out until they are scrolled to, and Ctrl+F still finds them. */
        content-visibility:auto; contain-intrinsic-size:auto 600px }
.chat{ position:relative; display:flex; align-items:center; gap:6px; width:100%;
       padding:7px 8px 7px 10px; border:0; border-radius:8px; background:none;
       /* --t-body and not --t-small: the latter was referenced here, exactly
          once, and declared nowhere, so the size silently fell back to what
          it inherited. A dangling token that renders plausibly is the kind
          nobody reports. */
       color:var(--fg-2); font:inherit; font-size:var(--t-body);
       text-align:left }
.chat:hover{ background:var(--raised); color:var(--fg) }
/* A mark on the edge rather than a filled row: the current session should be
   findable at a glance without the list turning into a row of blocks. */
.chat[aria-current="true"]{ color:var(--fg) }
.chat[aria-current="true"]::before{ content:""; position:absolute; left:0;
       top:7px; bottom:7px; width:2px; border-radius:2px; background:var(--fg-3) }
/* The name is a button so it can be reached by keyboard, and the whole of the
   user agent's button chrome has to come off or it draws as a raised box with
   its text centred - which is what shipped in the first screenshot of this
   column. A row in a list looks like a row. */
/* ⛔ THE POINTER GOES ON WHAT IS CLICKABLE. The row carried it and the row
   has no handler: the padding around the name was a pointer cursor over
   nothing, which is the honesty contract this file states for the browser bar
   thirty lines earlier and did not keep here. */
.chat .nm{ cursor:pointer; flex:1; min-width:0; overflow:hidden;
           text-overflow:ellipsis;
           white-space:nowrap; border:0; background:none; color:inherit;
           font:inherit; text-align:left; padding:0 }
#chats .none{ margin:0; padding:var(--s3) var(--s2); color:var(--fg-3);
              font-size:var(--t-label); line-height:1.5 }
.chat .cnt{ flex:none; font-family:var(--mono); font-size:var(--t-label);
            color:var(--fg-3) }
/* 24 and not 18: WCAG 2.2 puts the floor at 24px and this is the control
   that DELETES a conversation, so it is also the one where a near miss costs
   the most. */
/* ⛔ HIDDEN FROM THE EYE, NOT FROM THE TAB ORDER. `visibility:hidden` takes
   an element out of the focus order, and tabbing BACKWARD into a row then
   skips it every time: the browser looks for the previous focusable while
   that row is neither hovered nor focused, so the control that deletes a
   conversation was reachable in one direction only. Transparent instead, and
   it shows itself the moment it takes focus. */
.chat .x{ flex:none; width:24px; height:24px; border:0; border-radius:4px;
          background:none; color:var(--fg-3); cursor:pointer; line-height:1;
          opacity:0; transition:opacity 120ms ease-out }
.chat:hover .x, .chat:focus-within .x, .chat .x:focus-visible{ opacity:1 }
.chat .x:hover{ background:var(--line-2); color:var(--fg) }


/* ⛔ A PERCENTAGE ALONE GIVES THE SURPLUS TO THE WRONG PANE. The conversation
   stops getting better past its measure cap - a wider column is a longer line,
   not more text - while the browser view is a picture and gets better with
   every pixel. At 44% of a 2560 screen this column was 1126px around a 634px
   thread: 460px of nothing, taken from the pane that could have used it. The
   clamp holds the column at what the thread plus its gutters actually need and
   hands the rest to the right. Only desktops run this, so the floor is the
   narrow end of a laptop and there is no phone case to carry.

   The ceiling is derived, not chosen: the thread caps at 66ch, which is 498px
   in this font, plus the 32px of log padding it sits in. Anything wider would
   be slack inside this pane rather than measure, and it is worth more to the
   picture on the right. */
#left { width:clamp(420px, 44%, 530px); display:flex; flex-direction:column;
        position:relative }
/* The separator carries the line that used to be `#left`'s right border, so
   the thing you drag and the thing you see are the same thing. Wider than the
   line it draws: a 1px target is a 1px target, and this one is grabbed by
   hand. */
#split{ flex:0 0 9px; cursor:col-resize; position:relative; background:none;
        border:0; padding:0; touch-action:none }
/* ⛔ NINE PIXELS OF LINE, TWENTY-FIVE OF TARGET. WCAG 2.2 puts the floor at
   24px and none of its exceptions cover a separator: the arrow keys are a
   path, not a control. The grab area reaches into the two panes it divides,
   which is where a hand aims anyway, and nothing about the layout moves. */
#split::before{ content:""; position:absolute; inset:0 -8px; cursor:col-resize }
#split::after{ content:""; position:absolute; top:0; bottom:0; left:4px; width:1px;
               background:var(--line-1); transition:background-color 120ms ease-out }
#split:hover::after{ background:var(--line-3) }
#split:focus-visible{ outline:none }
#split:focus-visible::after, #split[data-drag]::after{ background:var(--accent); width:2px }
#right{ flex:1; min-width:0; display:flex; flex-direction:column; background:var(--well) }
/* ⛔ UNDER 720px THE TWO PANES STOP BEING SIDE BY SIDE, or the right one is
   allotted nothing and its bar spills out of the window. Measured in a frame
   320px wide, which is what WCAG 1.4.10 asks a layout to survive: the document
   scrolled sideways to 482px, the conversation was squeezed to 270 and the
   browser pane was FOUR HUNDRED AND EIGHTY-TWO minus everything, which is to
   say zero, with the Live/Frozen pair and the layout picker drawn past the
   edge of the screen.

   Stacked, both halves keep a full width and the page scrolls in one direction
   only. The spine stays where it is - it belongs to the frame, and that was
   decided - so it keeps the conversation company on the first row.

   ⛔ AND THE MEASUREMENT NEEDED A REAL VIEWPORT. The `zoom` property scales
   what is drawn and does NOT move the CSS viewport, so media queries do not
   fire under it: a first pass "at 400%" reported a failure that was an artefact
   of the instrument. An iframe of a fixed width has a viewport of its own, and
   that is what these numbers come from. */
@media (max-width:720px){
  body{ flex-wrap:wrap }
  /* `min-width:0` or the pane refuses to go under its content's own minimum,
     the flex line overflows, and the pane wraps to a row of its own - leaving
     the spine alone above it as a 93px stub with the word clipped inside. */
  #left{ width:calc(100% - var(--spine)); min-width:0; height:60vh }
  #split{ display:none }
  #right{ flex:1 0 100%; height:40vh }
}
/* Three groups and not four things in a row: the name, then what this
   conversation is costing and running, then the one thing you can do to it.
   The rule that separates the last is the same hairline the panes use. */
#head { flex:none; height:var(--topbar); display:flex; align-items:center;
        gap:var(--s2); padding:0 var(--s4);
        border-bottom:1px solid var(--line-1) }
#head .vr{ width:1px; height:18px; flex:none; background:var(--line-2);
           margin:0 var(--s1) }
/* ⛔ THE GROUP STAYS ON THE RIGHT, AND THE THING THAT KEPT IT THERE WAS THE
   METER. `margin-left:auto` lived on the meter, so removing it dropped the
   model and Clear against the left edge, under the transcript's own margin and
   nowhere near the edge they had always sat on. The push belongs to the first
   of whatever survives, not to whichever element happened to be there. */
#head #model{ margin-left:auto }
/* The heading is out of flow (`.sr` is absolute), so it is not one of the
   things being pushed, and this rule only describes the size it is announced
   at rather than drawn at. */
#head h1{ margin:0; font-size:var(--t-ui); font-weight:600 }
.badge{ font-size:var(--t-label); color:var(--fg-2);
        background:var(--raised); border:1px solid var(--line-2);
        padding:3px 9px; border-radius:var(--r-pill) }
/* 24px is the floor WCAG 2.2 sets for a target, and these three sat at 21,
   22 and 23 - close enough to look fine and short enough to fail. */
#fresh{ min-height:24px; font-size:var(--t-label); font-family:var(--sans);
        color:var(--fg-2);
        background:var(--raised); border:1px solid var(--line-2); cursor:pointer;
        padding:3px 9px; border-radius:var(--r-pill);
        transition:background-color 120ms ease-out, color 120ms ease-out }
#fresh:hover:not(:disabled){ background:var(--hover); color:var(--fg) }
#fresh:disabled{ opacity:.3; cursor:default }

/* ⛔ `inert` HAS NO LOOK, AND A CONTROL THAT CANNOT BE USED MUST NOT LOOK
   USABLE. This page already spells that `opacity:.3` on a disabled button, and
   then said the same thing about whole SUBTREES with `inert` and drew them as
   if nothing had happened. It was already wrong before the case that found it:
   the Live/Frozen pair and the layout picker go inert whenever there is nothing
   to see, and stayed fully lit the whole time. Seen on the running page, a
   deleted conversation left a composer inviting a sentence it could not send.
   One rule, so the look follows the mechanism rather than whoever remembers. */
[inert]{ opacity:.3 }

#log{ flex:1; overflow:auto; padding:var(--s5) var(--s4); scrollbar-gutter:stable }
/* Capped in CHARACTERS and not in pixels, because the thing being limited is
   the measure and 680px is only one screen's worth of it: on a 1920 window the
   same column ran to about 92 characters, past the 80 the WCAG asks for and
   well past the 50 to 75 the readability research settles on. `ch` follows the
   font instead of guessing at it.

   ⛔ AND `ch` IS NOT A CHARACTER. It is the advance width of the digit zero,
   which in a proportional font is much wider than an average letter, so a
   number written in `ch` reads like a character count and is not one.
   MEASURED on this font with a canvas, on real prose in both languages this
   interface serves: `0` is 7.55px at 14px system-ui, while the average
   character of a sentence is 6.11px. One `ch` is 1.24 characters.

   What that turned into, twice. The cap started at 72ch believing it was 72
   characters: minus the indent an answer carries, it was really 83. Then it
   was widened to 84ch on the reasoning that the indent made the column too
   NARROW - the arithmetic was done in `ch` again, and the result was 98
   characters per line, past every source that has a number: 65-72 in the chat
   design guidance, 75 as Baymard's upper bound, 80 as the WCAG 2.1 AAA cap.

   66ch is 498px here; minus the 37px indent that is 461px of text, and at
   6.11px a character that is 75 characters. The unit stays `ch` because it
   tracks the font's own metrics if the font ever changes; the number comes
   from the measurement, and the conversion is written down here so the next
   person does not redo it in the wrong unit for the third time.

   Left aligned rather than centred: centring splits the slack in two and puts
   half on the LEFT, which reads as the column having been pushed away from the
   edge for no reason - 185px of nothing before the first character, in a
   screenshot. */
#thread{ max-width:66ch; margin:0 }

/* Bottom-pinning with no scroll handler and no epsilon: the sentinel is the only
   anchor the browser may keep, so content inserted before it pushes the view
   down, and a reader who has scrolled up is left alone because an anchor off
   screen is not chosen. */
#log > *{ overflow-anchor:none }
#anchor{ height:1px; overflow-anchor:auto }

#hint{ color:var(--fg-3); max-width:46ch; margin:var(--s6) auto 0; text-align:center }
#hint p{ margin:0 0 var(--s4) }
#hint .eg{ font:var(--t-mono)/1.9 var(--mono); color:var(--fg-2);
           background:var(--raised); border:1px solid var(--line-1);
           border-radius:var(--r); padding:var(--s3) var(--s4); text-align:left }
#hint .sm{ font-size:var(--t-label); color:var(--fg-3) }

#jump{ position:absolute; bottom:100%; margin-bottom:var(--s2);
       left:50%; transform:translateX(-50%); z-index:2;
       background:var(--top); border:1px solid var(--line-2); color:var(--fg);
       font:var(--t-ui)/1 var(--sans); padding:7px 13px;
       border-radius:var(--r-pill); cursor:pointer }

/* ---------------- one turn ---------------- */
.turn + .turn{ margin-top:var(--s6) }   /* between turns */
.turn > * + *{ margin-top:var(--s3) }   /* inside a turn */
/* A turn that has scrolled out of sight costs no layout and no paint. Chosen
   over hiding or removing old turns because it is the only one of the three
   that leaves the text findable with Ctrl+F and readable by a screen reader:
   the browser skips the work, it does not drop the content. `auto` on the
   placeholder so a turn that has never been on screen still guesses its own
   height instead of collapsing the scrollbar. */
.turn{ content-visibility:auto; contain-intrinsic-size:auto 4rem }
.ev + .ev    { margin-top:var(--s1) }   /* between steps: a continuation */

.you{ margin-left:auto; width:fit-content; max-width:88%;
      background:var(--hover); border:1px solid var(--line-1);
      border-radius:var(--r-lg) var(--r-lg) var(--r-sm) var(--r-lg);
      padding:9px 13px; white-space:pre-wrap; overflow-wrap:anywhere }
/* ⛔ THE PRE-WRAP MOVED DOWN, and that is the whole reason the blocks below can
   exist. While the answer was one pre-wrap box, every blank line the model left
   between two paragraphs was drawn as an empty line - so a paragraph margin on
   top of it would space the answer twice. Now the parser eats the blank lines
   and the margins do the spacing, while pre-wrap survives exactly where a line
   break belongs to the author: inside a paragraph, an item, a cell. */
.say   { color:var(--fg-2); padding-left:var(--indent) }
.answer{ color:var(--fg);   padding-left:var(--indent) }
.say > :first-child, .answer > :first-child{ margin-top:0 }
.say > :last-child,  .answer > :last-child { margin-bottom:0 }
/* ⛔ THE RHYTHM IS THE FIRST THING THAT WAS WRONG once the blocks existed, and
   it read as "everything is stuck together". The gap between two items was 4px
   under a line 22px tall, so an item that wrapped ran into the next one and a
   list of six looked like one paragraph with dots in it. The scale here is a
   ladder rather than one value: 8 inside a list, 16 between blocks, 24 above a
   heading - a heading needs more space ABOVE it than below, because the space
   is what says the section starts, and a heading floating equidistant between
   two paragraphs belongs to neither. */
/* 1.6 rather than the 1.55 the rest of the app uses: this is the only place
   somebody reads paragraphs rather than scans rows, and the guidance for
   long-form chat answers puts the comfortable leading at about 1.6. WCAG 2.2
   asks 1.5 as a floor, so both pass; this one is the reading surface. */
.md-p, .md-i{ line-height:1.6 }
.md-p{ margin:0 0 var(--s4); white-space:pre-wrap; overflow-wrap:anywhere }
h3.md-h, h4.md-h, h5.md-h, h6.md-h{
      margin:calc(var(--s4) + var(--s2)) 0 var(--s2); font-family:var(--sans);
      font-weight:600; line-height:1.35; color:var(--fg) }
/* `##` is what a model writes most, so h4 is the one that has to read as a
   heading and not as a bold line: at 14px it was the size of the body text
   under it, which is a hierarchy only the weight was carrying. */
h3.md-h{ font-size:var(--t-h1) }
h4.md-h{ font-size:var(--t-h2); font-weight:600 }
h5.md-h, h6.md-h{ font-size:var(--t-h3); font-weight:600; color:var(--fg-2) }
/* A fenced block inside an answer is already inside the answer's indent, and
   `.out` carries its own for the tool output it was written for: the two
   stacked, so code sat a step to the right of the prose describing it. */
.say > .out, .answer > .out{ margin-left:0 }
/* ⛔ A LIST IS SET APART ON BOTH SIDES, and only stepping the left is why it
   still read as prose with dots in it. Measured on a real answer: the items
   began 26px in from the paragraph above and ended at 548, the SAME pixel the
   paragraph ended on, so the block was indented on one edge and flush on the
   other - which the eye reads as the same column, slightly ragged, rather than
   as something set inside it. 2.6em in and 1.4em back gives it two edges of its
   own. (1.9 was already the second attempt: at the 1.4 it started with, the
   marker sat almost under the first letter.) */
.md-l{ margin:0 1.4em var(--s4) 0; padding-left:2.6em }
.md-l .md-l{ margin:var(--s2) 0 0 }        /* a nested list continues its item */
.md-i{ margin:0 0 var(--s2); white-space:pre-wrap; overflow-wrap:anywhere }
.md-i::marker{ color:var(--fg-3) }
.md-q{ margin:0 0 var(--s4); padding:2px 0 2px var(--s4); color:var(--fg-2);
       box-shadow:inset 2px 0 0 var(--line-3) }
.md-hr{ margin:var(--s5) 0; border:0; border-top:1px solid var(--line-2) }
/* display:block so a wide table scrolls inside itself instead of widening the
   whole conversation, which on this layout would push the live pane off. */
.md-t{ display:block; overflow-x:auto; max-width:100%; margin:0 0 var(--s4);
       border-collapse:collapse; font-size:var(--t-mono) }
.md-t th, .md-t td{ padding:6px 18px 6px 0; text-align:left; vertical-align:top;
                    white-space:pre-wrap; border-bottom:1px solid var(--line-1) }
.md-t th{ font-family:var(--sans); font-size:var(--t-label); font-weight:600;
          text-transform:uppercase; letter-spacing:.04em; color:var(--fg-3) }
/* A link is SHOWN and never made clickable: this pane draws words chosen by
   whatever page the agent last read, and the browser it drives is right there.
   The address is printed next to them so an injected one is legible. */
.lk  { color:var(--fg) }
.href{ color:var(--fg-3); font:.75rem/1.5 var(--mono); overflow-wrap:anywhere }
.href::before{ content:" " }
/* ⛔ NO COLOURED BAR DOWN THE LEFT EDGE. A 2px stripe on a callout is the
   house style of every framework and belongs to none of them; a tint plus a
   hairline in the same hue says the same thing without the costume. */
.orph  { display:flex; gap:8px; font-size:var(--t-mono); color:var(--err);
         background:color-mix(in srgb, var(--err) 9%, transparent);
         border-radius:var(--r-sm);
         border:1px solid color-mix(in srgb, var(--err) 32%, transparent);
         padding:6px 10px }

/* ONE grid: every row on the same rails, so nothing shifts as text changes. */
.row{ display:grid; grid-template-columns:var(--gutter) minmax(0,1fr) auto 1rem;
      column-gap:var(--gap); align-items:baseline; padding:3px 6px;
      list-style:none; cursor:pointer; border-radius:var(--r-sm);
      transition:background-color 120ms ease-out }
.row::-webkit-details-marker{ display:none }
.row:hover{ background:var(--raised) }
.g   { grid-column:1; justify-self:end; font-size:var(--t-label); color:var(--fg-3) }
/* Selectable: `user-select:none` on the whole row kept a double-click from
   painting the line blue, and also made a truncated URL impossible to copy -
   which is the one thing somebody wants from a row they cannot finish
   reading. */
.lab { user-select:text; grid-column:2; min-width:0; overflow:hidden;
       text-overflow:ellipsis; white-space:nowrap; font-size:var(--t-mono) }
.lab b   { font-family:var(--sans); font-weight:600; color:var(--fg) }  /* the verb */
.lab code{ color:var(--accent) }                                        /* the object */
.lab .inline{ color:var(--fg-3) }                    /* a short result, on the row */
.meta{ grid-column:3; white-space:nowrap; font-size:var(--t-label); color:var(--fg-3) }

/* The chevron is the row's own pseudo-element in its own track: no svg, no icon
   font, and it cannot shift the label when it turns. */
.row::after{ content:""; grid-column:4; justify-self:end; align-self:center;
             width:5px; height:5px; margin-top:-2px;
             border-right:1.5px solid var(--fg-4); border-bottom:1.5px solid var(--fg-4);
             transform:rotate(-45deg); transition:transform 150ms ease }
.ev[open] > .row::after{ transform:rotate(45deg); margin-top:-4px }
.ev[data-body="none"] > .row{ cursor:default }
.ev[data-body="none"] > .row::after{ visibility:hidden }

.ev[data-state="run"] .g{ color:transparent; position:relative }
.ev[data-state="run"] .g::after{ content:""; position:absolute; right:0; top:.45em;
  width:6px; height:6px; border-radius:50%; background:var(--accent);
  animation:breathe 1.4s ease-in-out infinite }
.ev[data-state="err"] .g{ color:var(--err) }
/* The wait between steps, wearing the same row as a step so the sequence does
   not change shape when the agent is thinking rather than acting. Its verb is
   muted, because nothing has happened yet and a bold one would claim it had. */
.pend{ display:grid; grid-template-columns:var(--gutter) minmax(0,1fr) auto 1rem;
       column-gap:var(--gap); align-items:baseline; padding:3px 6px }
.pend .lab b{ color:var(--fg-3); font-weight:400 }
.pend .g{ position:relative }
.pend .g::after{ content:""; position:absolute; right:0; top:.45em;
  width:6px; height:6px; border-radius:50%; background:var(--fg-3);
  animation:breathe 1.4s ease-in-out infinite }
@media (prefers-reduced-motion: reduce){ .pend .g::after{ animation:none } }
/* inset and not border-left: a border would shift all four tracks by two pixels */
/* ⛔ THE TOKEN, MIXED - NOT THE TOKEN'S CURRENT VALUE TYPED OUT AGAIN. Seven
   places had `--err` and `--well` re-expanded as rgba by hand, which is seven
   surfaces that would keep the old hue the day either token moves. */
.ev[data-state="err"] > .row{
     background:color-mix(in srgb, var(--err) 8%, transparent);
     box-shadow:inset 0 0 0 1px color-mix(in srgb, var(--err) 30%, transparent) }

.out{ margin:2px 0 var(--s2) var(--indent);
      max-height:290px; max-height:15lh; overflow:auto; overscroll-behavior:contain;
      white-space:pre-wrap; overflow-wrap:anywhere;
      font:.75rem/1.5 var(--mono); color:var(--fg-3);
      background:var(--raised); border-left:2px solid var(--line-2);
      border-radius:0 var(--r-sm) var(--r-sm) 0; padding:8px 10px }

/* ---------------- composer ---------------- */
form{ position:relative; padding:var(--s3) var(--s4) var(--s4);
      border-top:1px solid var(--line-1);
      background:var(--raised);
      box-shadow:0 -1px 0 rgba(0,0,0,.5), 0 -12px 28px -12px rgba(0,0,0,.65) }
.composer{ display:flex; align-items:flex-end; gap:var(--s2);
           background:var(--base); border:1px solid var(--line-2);
           border-radius:var(--r-lg); padding:10px 10px 10px var(--s3);
           box-shadow:var(--lip); transition:border-color 120ms ease-out }
.composer:focus-within{ border-color:var(--line-3) }
#i{ flex:1; background:transparent; border:0; outline:none; resize:none; color:var(--fg);
    font:var(--t-body)/1.55 var(--sans); min-height:24px; max-height:200px;
    overflow-y:hidden; padding:0; caret-color:var(--accent) }
/* --fg-3 and not --fg-4: the placeholder is the only hint the composer gives,
   so it is text that has to be read, and --fg-4 sits at 2.4:1 against 4.5:1.
   This was the first rule to be moved and it stayed the only one for a while;
   the other nine went the same way once somebody counted them. */
#i::placeholder{ color:var(--fg-3) }
/* ⛔ `currentColor` INHERITED THE PAGE'S INK ONTO THE ACCENT: the arrow
   inside the only primary control on the page measured 1.71:1 against the
   button it sits on, where a graphic that is a button's whole label wants
   3:1. `--on-accent` was declared for exactly this and used nowhere; on the
   accent it reads 8.6:1. */
#go, #halt{ width:32px; height:32px; flex:none; border:0; border-radius:50%; display:grid;
     place-items:center; cursor:pointer; background:var(--accent);
     color:var(--on-accent);
     box-shadow:inset 0 1px 0 rgba(255,255,255,.22);
     transition:background 120ms ease-out, transform 80ms ease-out }
/* ⛔ THE PRIMARY CONTROL HAD NO HOVER AT ALL: the one button the whole
   page exists for gave the pointer no answer until it was already pressed.
   Everything else on the page hovers. */
#go:hover:not(:disabled){ background:var(--accent-hi) }
#halt:hover{ background:var(--stop-hi) }
#go:active, #halt:active{ transform:scale(.92); box-shadow:none }
#go:disabled{ opacity:.3; cursor:default }
/* Its own button, not a mode of the send button. As a mode it disappeared the
   moment somebody typed, because the same control then meant "queue this for
   the next turn" - and the loop has no turn ceiling, so this button is the only
   thing that ends a run that will not converge. It follows the RUN. */
#halt{ background:var(--stop) }
#chip{ display:inline-flex; align-items:center; gap:6px; margin-bottom:var(--s2);
       background:var(--hover); border:1px solid var(--line-2); color:var(--fg-2);
       font-size:var(--t-label); padding:3px 9px; border-radius:var(--r-pill);
       cursor:pointer }

/* ---------------- browser pane ---------------- */
/* The strip only exists when there is more than one tab: a single tab labelled
   with its own title is chrome that says nothing the address bar below it does
   not already say. */
/* ⛔ THE STRIP IS THE TOP OF THE BAR, NOT A THING FLOATING OVER IT. It sat
   on the same surface as the bar with the SELECTED tab cut out in a darker
   one, so the current page read as a hole punched in the header, and its left
   edge started 4px before the address below it. Now the strip stands on the
   page's ground and the selected tab is the bar's own surface, which is what
   makes a tab look attached to what it opens - and both share one padding. */
#tabs{ flex:none; display:flex; gap:2px; padding:6px var(--s3) 0;
       background:var(--base); overflow-x:auto; scrollbar-width:none }
#tabs button{ flex:0 1 190px; min-width:80px; height:28px; display:flex;
              align-items:center; gap:6px; border:0; cursor:pointer;
              border-radius:var(--r) var(--r) 0 0;
              background:transparent; color:var(--fg-3); padding:0 10px;
              font:var(--t-label)/1.4 var(--sans); white-space:nowrap;
              overflow:hidden; text-overflow:ellipsis }
#tabs button:hover{ background:var(--hover); color:var(--fg-2) }
#tabs button[aria-selected="true"]{ background:var(--raised); color:var(--fg) }
#tabs .t{ overflow:hidden; text-overflow:ellipsis }

/* The same height as the conversation's header beside it. They were 38 and
   50, so the top edge of the product broke by twelve pixels on its main
   seam - the one place a misalignment is read as the whole thing being
   loose rather than as one box being wrong. */
/* ⛔ IT WRAPS, AND THE HEIGHT IS A FLOOR RATHER THAN A CEILING. Measured at
   400% zoom, which WCAG 1.4.10 asks a layout to survive and which is the same
   thing as a 320px window: this bar was the only place on the page that pushed
   the document sideways. The address can shrink to nothing, but the Live/Frozen
   pair and the layout picker cannot, so three fixed-width groups in a row on a
   fixed 50px line had nowhere to go and went past the edge. A `height` would
   then have clipped the second row, so it is a `min-height`: the bar is one
   line whenever one line fits, and it is the bar's own business when it does
   not. Found by the reflow check and not by looking - at 100% there is room,
   so nothing shows. */
#chrome{ flex:none; min-height:var(--topbar); display:flex; align-items:center;
         flex-wrap:wrap; row-gap:var(--s1);
         gap:var(--s2); padding:var(--s1) var(--s3); background:var(--raised);
         border-bottom:1px solid var(--line-1) }
/* The honesty contract: nothing in here is interactive except what is, so
   nothing in here gets a pointer cursor except what does. */
#chrome, #chrome *{ cursor:default; user-select:none }
#url{ user-select:text }
#mode button{ cursor:pointer; min-height:24px }
#dot{ width:7px; height:7px; flex:none; border-radius:50%; background:var(--fg-4) }
[data-state="live"]  #dot{ background:var(--ok); animation:breathe 1.8s ease-in-out infinite }
[data-state="busy"]  #dot{ background:var(--accent); animation:breathe .9s ease-in-out infinite }
[data-state="frozen"]#dot{ background:var(--fg-2) }
[data-state="offline"] #dot, [data-state="error"] #dot{ background:var(--err) }
/* ⛔ ONE HEIGHT FOR EVERYTHING IN THIS BAR. The address was 24 tall, the
   Live/Frozen pair 30 and the layout picker 30, so three controls on one line
   sat on three different rhythms - the kind of thing nobody names and everybody
   reads as unfinished. And the address is a FIELD, so it gets the field's
   corner: a pill is for a badge, and using both shapes for everything is what
   made this bar look assembled rather than designed. */
#url{ flex:1; min-width:0; height:var(--h-ctl); line-height:calc(var(--h-ctl) - 2px);
      padding:0 var(--s3); border-radius:var(--r); background:var(--well);
      border:1px solid var(--line-1); font-size:var(--t-mono);
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis }
/* ⛔ BOTH FORMS, BECAUSE THE INTENT LIVED IN TWO PLACES AND MATCHED IN
   NEITHER. The script sets `dim` on the address bar ITSELF when there is no
   page, and the only rule was a descendant selector - so `no page yet`
   rendered in the inherited ink and was the brightest thing on a bar that
   was describing an empty room. The halves of a real URL are the descendant
   case and keep working. */
#url.dim, #url .dim{ color:var(--fg-3) }
#url .host{ color:var(--fg) }
#mode{ display:inline-flex; gap:2px; flex:none; height:var(--h-ctl);
       align-items:center; background:var(--base); border:1px solid var(--line-1);
       border-radius:var(--r); padding:0 2px }
#mode button{ border:0; background:transparent; color:var(--fg-3);
              border-radius:var(--r-sm); padding:2px 9px;
              font:500 var(--t-label)/1.5 var(--sans);
              transition:color 120ms ease-out }
#mode button:hover:not([aria-pressed="true"]){ color:var(--fg-2) }
#mode button[aria-pressed="true"]{ background:var(--top); color:var(--fg);
                                    box-shadow:0 1px 2px rgba(0,0,0,.35) }
/* ⛔ A CONTROL THAT CANNOT DO ANYTHING DOES NOT LOOK READY. With no browser
   open, Live/Frozen, the layout picker and the address are three armed controls
   over an empty room: the bar looked identical whether the product was working
   or waiting to be told what to do. */
#right[data-empty="1"] #url,
#right[data-empty="1"] #mode,
#right[data-empty="1"] #grid{ opacity:.4 }
/* ⛔ AND `pointer-events` IS NOT A DISABLED STATE. It only stops the
   mouse: the five buttons kept their place in the tab order, kept the focus
   ring, and Enter still fired the handler - so a keyboard could operate five
   controls that look dead, and a screen reader announced them as ordinary
   enabled buttons. `inert` takes them out of both. */
#right[data-empty="1"] #mode,
#right[data-empty="1"] #grid{ pointer-events:none }
/* And the state word goes altogether: with nothing running it said IDLE, in
   capitals, and was the brightest thing on a bar describing an empty room -
   while the room itself already says what it is. */
#right[data-empty="1"] #state{ position:absolute; width:1px; height:1px;
                              overflow:hidden; clip-path:inset(50%) }

/* The frame is solved from the available height, so a wide shot fills the width
   and a tall one fills the height. What is left over is stage, never a hole
   inside the frame. object-fit stays underneath for the one frame where the
   ratio is still the previous page's. */
/* ---------------- the other browsers ----------------
   A row under the stage, never a second live pane: eight at full rate would
   want more pipe than there is, and that is arithmetic rather than an
   optimisation problem.

   ⛔ AND A BROWSER WITH NO PICTURE DOES NOT GET A PICTURE FRAME. Six declared
   but stopped browsers used to draw six 168x133 cards, each holding the words
   `not up` in the middle of an empty grey rectangle: a wall of nothing, 133px
   tall, in the place where the running ones live. A thing with no image is a
   NAME, so it is drawn as one - a 26px chip - and the row goes from a gallery
   of failures to a list of what this session has. */
/* ⛔ NO CONTROLS HERE. Browsers are opened and closed by ASKING - "open
   another browser", "close the second one" - because the agent is what drives
   this and a button beside it is a second way to do the same thing, in a place
   where the two can disagree about which browser is current. The panes are
   views: clicking one changes what YOU are looking at and tells the agent
   nothing. */
#thumbs{ flex:none; display:flex; align-items:flex-end; gap:var(--s2);
         padding:0 var(--s3) var(--s3); overflow-x:auto }
.thumb{ flex:none; width:150px; border:1px solid var(--line-2);
        border-radius:var(--r); background:var(--raised); padding:0;
        cursor:pointer; overflow:hidden; display:flex; flex-direction:column;
        text-align:left; font:inherit; color:var(--fg-3);
        transition:border-color 120ms ease-out }
.thumb:hover{ border-color:var(--line-3); color:var(--fg-2) }
.thumb[aria-current="true"]{ border-color:var(--fg-2); color:var(--fg-2) }
.thumb .pic{ width:100%; aspect-ratio:16/10; background:var(--well);
             display:grid; place-items:center; overflow:hidden }
.thumb .pic img{ width:100%; height:100%; object-fit:cover; display:block }
.thumb .pic span{ font-size:var(--t-label); color:var(--fg-3); padding:4px;
                  text-align:center }
.thumb .cap{ display:flex; align-items:center; gap:6px; padding:5px 8px;
             font-family:var(--mono); font-size:var(--t-label) }
.thumb .cap .id{ flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis;
                 white-space:nowrap }
/* The one the agent is driving, marked rather than selected: the person's eye
   and the agent's hand are two different things and the row says both. */
.thumb .cap .dot, .chip .dot{ flex:none; width:6px; height:6px; border-radius:50%;
                              background:var(--ok) }
.chip{ flex:none; height:26px; display:flex; align-items:center; gap:7px;
       padding:0 10px; border:1px solid var(--line-2); border-radius:var(--r-pill);
       background:var(--raised); cursor:pointer; color:var(--fg-3);
       font:var(--t-label)/1 var(--mono); letter-spacing:.02em;
       transition:border-color 120ms ease-out, color 120ms ease-out }
.chip:hover{ border-color:var(--line-3); color:var(--fg-2) }
.chip[aria-current="true"]{ border-color:var(--fg-2); color:var(--fg-2) }
.chip .off{ flex:none; width:6px; height:6px; border-radius:50%;
            box-shadow:inset 0 0 0 1px var(--fg-4) }

/* ---------------- the stage ----------------
   ⛔ THE CARD IS THE PICTURE, NOT THE CELL, and getting that backwards is what
   made this pane look unfinished. A cell used to be a full-height box with a
   border and a shadow, and the picture floated in the middle of it: measured on
   the bench, a 1280x688 window in a one-up cell drew 40% of the card as black,
   and at two-up the two cards were the same size while their pictures were not,
   so the smaller one read as broken rather than as a narrower window. Now the
   frame SHRINK-WRAPS the picture - the border, the corner and the shadow belong
   to the image - and the cell is only the space it is centred in.

   How, without measuring anything: the picture sizes itself against the cell
   with container units, and the browser's own chrome is cut with a NEGATIVE
   MARGIN in percent. A percentage margin resolves against the containing
   block's width, so `--cut` is the chrome expressed as a fraction of the
   picture's WIDTH, and the frame's height ends up being the cropped height by
   construction. No getBoundingClientRect, nothing to recompute on resize, and
   the old two-number cache disappears with it. */
#stage{ flex:1; min-height:0; padding:var(--s3); display:grid; gap:var(--s3) }
#stage[data-grid="1"]{ grid-template-columns:1fr }
#stage[data-grid="2"]{ grid-template-columns:1fr 1fr }
/* Three on a 2x2 with one slot empty, because three equal screens and a gap
   is what a control room does: the alternative makes one of them special. */
#stage[data-grid="3"],
#stage[data-grid="4"]{ grid-template-columns:1fr 1fr; grid-template-rows:1fr 1fr }

.screen{ container-type:size; min-width:0; min-height:0;
         display:grid; place-items:center; overflow:hidden;
         background:none; border:0; padding:0; margin:0;
         font:inherit; color:inherit; text-align:left; cursor:pointer }
.frame{ position:relative; overflow:hidden; border:1px solid var(--line-2);
        border-radius:var(--r-lg); background:var(--well);
        box-shadow:0 12px 30px -20px #000;
        transition:border-color 120ms ease-out }
.screen:hover .frame{ border-color:var(--line-3) }
/* The one you are looking at, when there is more than one to look at. A border
   that carries meaning wants 3:1, and --fg-2 is 8.6. */
.screen[aria-current="true"] .frame{ border-color:var(--fg-2) }
/* ⛔ AND THE FRAME IS THE LARGEST BOX OF THE PICTURE'S SHAPE THAT THE CELL
   CAN HOLD, which is one line of CSS and the whole reason the cells stopped
   being loose. The first attempt let the image size itself and the frame
   shrink-wrap it: correct for a picture bigger than the cell, and wrong for
   every other case, because an image is never scaled UP to fill a box - so a
   small capture sat at its natural size in the middle of a large pane and the
   cell looked empty again, which is the defect this was meant to end.
   `--arn` is the picture's shape AFTER the crop and `--cut` the crop itself,
   both set once per shape by the frame that arrives. */
.frame{ aspect-ratio:var(--arn, 1.6);
        width:min(100cqw, calc(100cqh * var(--arn, 1.6))) }
.frame img{ position:absolute; left:0; top:0; width:100%; height:auto;
            margin-top:calc(var(--cut, 0%) * -1) }
.frame img[hidden]{ display:none }

/* ⛔ WAITING, EMPTY, STOPPED AND FAILED ARE FOUR STATES AND THEY USED TO DRAW
   ONE BLACK RECTANGLE. On the bench, a browser whose capture answered 503 and
   one that simply had not sent its first frame were pixel-identical, and both
   read as a product that is broken. Whatever the pane cannot show, it says. */
.veil{ position:absolute; inset:0; display:grid; place-content:center;
       justify-items:center; gap:6px; padding:0 var(--s4); text-align:center;
       background:var(--well) }
.veil b{ font:600 var(--t-ui)/1.4 var(--sans); color:var(--fg-2) }
.veil span{ font-size:var(--t-label); color:var(--fg-3); max-width:34ch }
.veil[hidden]{ display:none }
/* Over a picture that is still there, the veil is a scrim and not a wall: the
   last frame is evidence, and hiding it to announce that it is old throws away
   the only thing the pane has. */
/* Deep enough that the words on it hold their contrast over a white page,
   shallow enough that the last frame stays evidence underneath. */
.screen[data-state="stale"] .veil{
     background:linear-gradient(color-mix(in srgb, var(--well) 86%, transparent),
                                color-mix(in srgb, var(--well) 93%, transparent)) }
.screen[data-state="error"] .veil b{ color:var(--err) }
/* The pulse says the pane is trying, which is the difference between waiting
   and stopped - and it is the whole reason a spinner exists. */
.veil .pulse{ width:56px; height:2px; border-radius:2px; background:var(--line-3);
              overflow:hidden; position:relative }
.veil .pulse::after{ content:""; position:absolute; inset:0 auto 0 0; width:40%;
                     background:var(--fg-3); border-radius:2px;
                     animation:slide 1.4s ease-in-out infinite }
@keyframes slide{ 0%{ left:0 } 50%{ left:60% } 100%{ left:0 } }

/* The name rides ON the picture. It used to be a 28px bar bolted under the
   card, which put the label of a thing outside the thing and cost a row of
   height in every cell of a 2x2. */
/* ⛔ THE PLATE CARRIES ITS OWN GROUND. These two sit on a live capture of
   somebody else's website, so a translucent backdrop makes their contrast a
   function of that page's stylesheet: measured over a white page the id read
   3.9:1 and the staleness 3.4:1, both under the floor, and most of the web is
   white. Opaque, with a hairline so it still reads as sitting on top. */
.tag, .stamp{ position:absolute; top:8px; height:20px; display:flex;
              align-items:center; gap:6px; padding:0 8px; pointer-events:none;
              border-radius:var(--r-sm); background:var(--well);
              box-shadow:0 0 0 1px rgba(255,255,255,.14);
              font:var(--t-label)/1 var(--mono); letter-spacing:.02em }
.tag{ left:8px; color:var(--fg-2); max-width:calc(100% - 96px);
      overflow:hidden; text-overflow:ellipsis; white-space:nowrap }
.tag .dot{ flex:none; width:6px; height:6px; border-radius:50%;
           background:var(--ok) }
/* ⛔ STALE HAS TO LOOK STALE. In a grid most of what you see is a picture from
   a moment ago by construction, and a control room's first rule is that a feed
   which has stopped must not read as one that is running. Nothing while the
   frames keep coming, a number in seconds the moment they do not. */
.stamp{ right:8px; color:var(--err) }
.stamp[hidden]{ display:none }

/* The empty stage is not a void with a sentence in it: it is the one place
   that has to say how a browser gets opened, because there is no button that
   does it - they are opened by asking, on purpose. */
.empty{ grid-column:1 / -1; grid-row:1 / -1; display:grid; place-content:center;
        justify-items:center; gap:var(--s2); text-align:center; padding:var(--s4) }
.empty b{ font:600 var(--t-h2)/1.3 var(--sans); color:var(--fg-2) }
.empty span{ font-size:var(--t-ui); color:var(--fg-3); max-width:38ch }
.empty code{ font:var(--t-mono)/1.9 var(--mono); color:var(--fg-2);
             background:var(--raised); border:1px solid var(--line-1);
             border-radius:var(--r); padding:6px var(--s3); margin-top:var(--s1) }

/* The second half of the address bar when nobody has picked a screen: the count
   is the fact, this is what to do about it. */
#url .hint{ color:var(--fg-3); font-family:var(--sans); font-size:var(--t-label) }
#url .hint::before{ content:"  -  "; white-space:pre }

#grid{ flex:none; display:flex; align-items:center; gap:2px; height:var(--h-ctl);
       background:var(--well); border:1px solid var(--line-2);
       border-radius:var(--r); padding:0 2px }
#grid button{ min-width:30px; height:24px; padding:0 5px; border:0;
              border-radius:var(--r-sm); background:none; cursor:pointer;
              display:grid; place-items:center; color:var(--fg-3);
              transition:background-color 120ms ease-out, color 120ms ease-out }
#grid button:hover{ color:var(--fg-2) }
#grid button[aria-pressed="true"]{ background:var(--raised); color:var(--fg) }

/* The small things whose absence is felt without being noticed. */
:focus{ outline:none }
:focus-visible{ outline:2px solid var(--accent); outline-offset:2px; border-radius:inherit }
/* The accent itself, mixed - it was a second orange one shade off the one
   this page uses, and white ink in a palette whose own rule forbids it. */
::selection{ background:color-mix(in srgb, var(--accent) 30%, transparent);
             color:var(--fg) }
:root{ accent-color:var(--accent) }
*{ scrollbar-width:thin; scrollbar-color:var(--top) transparent }

@keyframes rise{ from{ opacity:0; transform:translateY(3px) } }
@keyframes breathe{ 0%,100%{opacity:1} 50%{opacity:.35} }
#thread .turn, #thread .ev, #thread .say, #thread .answer{
  animation:rise 140ms cubic-bezier(.2,.6,.3,1) both }
#thread [data-replay]{ animation:none }
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{ animation-duration:.01ms !important;
    animation-iteration-count:1 !important; transition-duration:.01ms !important }
}
</style>

<!-- The spine. It is the first thing in the document and the leftmost thing on
     the screen, it is always there, and it is the only way in or out of the
     column: closed it is the word, open it is the word next to the list.
     Drawn on a napkin on 2026-09-09 after a bar in the header turned out not to
     be it - a control that is part of the frame reads as permanent, where one
     among the header's other controls reads as one more button. -->
<!-- ⛔ THE COMPOSER IS THE 112th TAB STOP. Every step of every run is a
     <summary>, so the only input on the page - the reason the page exists -
     sits behind the entire transcript, and the queue grows with the run. One
     link, first in the document, off-screen until it is focused. -->
<a class="skip" href="#i">Skip to the message box</a>
<button id="railtab" type="button" aria-expanded="false" aria-controls="rail"
        title="Sessions"><span>Sessions</span></button>

<nav id="rail" aria-label="Sessions" hidden>
  <!-- No title here any more: the spine to the left of this column carries the
       word, and with the column open the two sat twenty pixels apart saying the
       same thing. The row keeps its height from its padding, so it still lines
       up with the app header beside it. -->
  <div id="railhead">
    <span class="label" aria-hidden="true"></span>
    <button id="newchat" type="button" aria-label="New session" title="New session">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor"
           stroke-width="1.6" stroke-linecap="round"><path d="M7 2.5v9M2.5 7h9"/></svg>
    </button>
  </div>
  <div id="chats" role="list"></div>
</nav>

<!-- Two landmarks, so somebody moving by region can go straight to the
     conversation or to the browsers instead of walking the whole page. -->
<main id="left" aria-label="Conversation">
  <div id="head">
    <!-- ⛔ THE HEADING IS OFF-SCREEN, NOT ABSENT, AND IT IS LOAD-BEARING WHERE
         IT CANNOT BE SEEN. The answers' own headings start at h3 on the
         reasoning that the product's name sits above them, so deleting this
         leaves every one of them hanging under nothing and the document with no
         outline at all. It reads as dead markup and it is not: a gate holds it
         here. What was removed is the NAME ON THE SCREEN, which said the same
         thing as the tab, the window and the address bar. -->
    <h1 class="sr">AIHawk</h1>
    <span class="badge" id="model">no model</span>
    <span class="vr" aria-hidden="true"></span>
    <button id="fresh" type="button" title="Clear this conversation">Clear</button></div>
  <div id="log">
    <!-- ⛔ role=log, OR THE WHOLE PRODUCT IS SILENT. Everything the agent
         does arrives here by appending a node, and the only live region on the
         page carried the word `idle`. Somebody who cannot see the screen was
         told nothing, ever - and the other channel, the picture, ships with an
         empty alt on purpose. -->
    <div id="thread" role="log" aria-live="polite" aria-relevant="additions">
      <div id="hint">
        <p>Tell it what to do, in a sentence. It opens the pages, reads them and
           clicks, and you watch on the right.</p>
        <p class="eg">Go to example.com and tell me the main heading.</p>
        <p class="sm">Plain language: the model works out the clicks. One
           instruction at a time works best.</p>
      </div>
    </div>
    <div id="anchor"></div>
  </div>
  <form id="f" autocomplete="off">
    <!-- Inside the composer and anchored to its top edge: it used to sit at a
         hard 110px from the bottom, which is a guess at the height of a box
         that GROWS with what is typed into it and again with the reader's font
         size, so at 200% with a queued message it landed on top of the thing
         it floats above. -->
    <button id="jump" hidden type="button">jump to latest</button>
    <button id="chip" type="button" hidden>1 message queued
      <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true"
           stroke="currentColor" stroke-width="1.6" stroke-linecap="round"
           stroke-linejoin="round"><path d="M10.6 2.9l2.5 2.5L5.6 12.9 2.5 13.5l.6-3.1z"/></svg></button>
    <div class="composer">
      <label class="sr" for="i">What should the agent do?</label>
      <textarea id="i" rows="1" placeholder="What should the agent do?"></textarea>
      <button id="go" type="submit" aria-label="Send" disabled>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
             stroke="currentColor" stroke-width="1.6" stroke-linecap="round"
             stroke-linejoin="round">
          <path d="M7 12V2M2.5 6.5L7 2l4.5 4.5"/></svg>
      </button>
      <button id="halt" type="button" hidden aria-label="Stop">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <rect width="12" height="12" rx="2" fill="currentColor"/></svg>
      </button>
    </div>
  </form>
</main>

<!-- The split is a control, so it says so: a real separator with a value a
     screen reader can read and the arrow keys can move. Which pane deserves
     the room is a property of the TASK - reading a long answer wants one
     ratio, watching a form being filled wants another - so it is not a number
     this file gets to decide once. -->
<div id="split" role="separator" aria-orientation="vertical" tabindex="0"
     aria-label="Width of the conversation" aria-valuemin="420"
     aria-valuenow="530"></div>

<section id="right" data-state="idle" aria-label="The browsers this session holds">
  <div id="tabs" hidden></div>
  <div id="chrome">
    <span id="dot"></span>
    <span id="url" class="dim">no page yet</span>
    <!-- ⛔ A GROUP OF TOGGLES, NOT TABS. `role="tablist"` promises panels this
         page does not have and a keyboard pattern it does not implement: arrow
         keys did nothing, `aria-controls` pointed at nothing, and a screen
         reader announced "tab, 1 of 2" for a switch. Its neighbour, the layout
         picker, already had this right. -->
    <span id="mode" role="group" aria-label="Whether the picture keeps updating">
      <button aria-pressed="true" data-v="live" type="button"
              title="Keep the picture updating">Live</button>
      <button aria-pressed="false" data-v="hold" type="button"
              title="Stop updating the picture. The agent keeps working.">Frozen</button>
    </span>
    <span id="state" class="label" aria-live="polite">idle</span>
    <!-- How many browsers are on the stage at once. The vocabulary of a
         control room, because that is the job: one when you are watching the
         work, four when you are keeping an eye on it. -->
    <!-- Drawn rather than numbered: the icon IS the layout, where a digit is a
         label for it. Each carries its own name because there is no text in it
         to read - the opposite of the sessions spine, where the word is the
         name and an aria-label would replace it. -->
    <span id="grid" role="group" aria-label="Screens at once">
      <button type="button" data-n="1" aria-pressed="true"
              aria-label="One screen" title="One screen">
        <svg viewBox="0 0 18 12" width="18" height="12" fill="none"
             stroke="currentColor" stroke-width="1.6">
          <rect x="1" y="1" width="16" height="10" rx="1.6"/></svg></button>
      <button type="button" data-n="2" aria-pressed="false"
              aria-label="Two screens" title="Two screens">
        <svg viewBox="0 0 18 12" width="18" height="12" fill="none"
             stroke="currentColor" stroke-width="1.6">
          <rect x="1" y="1" width="16" height="10" rx="1.6"/>
          <path d="M9 1v10"/></svg></button>
      <button type="button" data-n="4" aria-pressed="false"
              aria-label="Four screens" title="Four screens">
        <svg viewBox="0 0 18 12" width="18" height="12" fill="none"
             stroke="currentColor" stroke-width="1.6">
          <rect x="1" y="1" width="16" height="10" rx="1.6"/>
          <path d="M9 1v10M1 6h16"/></svg></button>
    </span>
  </div>
  <div id="stage" data-grid="1"></div>
  <!-- role, or the label is ignored: a bare div takes no accessible name. -->
  <div id="thumbs" role="group" aria-label="The other browsers in this session"></div>
</section>

<script>
const $ = id => document.getElementById(id);
/* ---- markdown, and the gate lifts everything down to the end of `rich` ----
   These lines are the only ones in this file a JavaScript engine runs during
   the tests: `test_the_answer_pane_draws_markdown.py` cuts the region out and
   executes it against a DOM small enough to print. The markers exist so that
   cut is exact - moving them means moving what is under test. */
const el = (t,c,x) => { const e = document.createElement(t);
                        if(c) e.className = c; if(x != null) e.textContent = x; return e; };

/* Markdown to NODES, never to a string of HTML.
   The text arriving here was written by a model that has just read arbitrary
   web pages, so it is chosen by whoever wrote the last page it visited. Putting
   it through innerHTML is the documented road to exfiltration by injected
   image, and no amount of sanitising makes that road shorter than this one.
   So: the marks become elements, built by hand, and the text between them stays
   text. A `<script>` in the answer is still drawn as the characters of a
   script, because it never stops being a text node.
   Images are absent on purpose - they are the exfiltration vector itself, and
   an `<img>` fetches its source the instant it enters the document, with no
   click and no error needed. A link is drawn but never made clickable, and its
   destination is PRINTED rather than hidden behind words, so an injected
   address is legible instead of invisible. */
function inline(text, into){
  for(const part of text.split(/(\*\*[^*\n]+\*\*|`[^`\n]+`|\*[^*\n]+\*|!?\[[^\]\n]*\]\([^()\s]*\))/)){
    if(!part) continue;
    const two = part.length > 4 && part.startsWith('**') && part.endsWith('**');
    const tick = part.length > 2 && part.startsWith('`') && part.endsWith('`');
    const one = part.length > 2 && !two && part.startsWith('*') && part.endsWith('*');
    const link = /^!?\[([^\]\n]*)\]\(([^()\s]*)\)$/.exec(part);
    if(two)       into.appendChild(el('strong', null, part.slice(2, -2)));
    else if(tick) into.appendChild(el('code', null, part.slice(1, -1)));
    else if(one)  into.appendChild(el('em', null, part.slice(1, -1)));
    else if(link){ if(link[1]) into.appendChild(el('span','lk', link[1]));
                   if(link[2]) into.appendChild(el('span','href', link[2])); }
    else          into.appendChild(document.createTextNode(part));
  }
}

/* The block marks, which are most of what a model writes: it answers in
   headings and lists far more often than in the three inline marks this pane
   understood until now, and every one of them was drawn as its own characters -
   `## Roles` arrived on screen as a hash, a hash and a space. */
const HEAD   = /^(#{1,6})\s+(.*)$/;
const BULLET = /^(\s*)[-*+]\s+(.*)$/;
const NUMBER = /^(\s*)\d+[.)]\s+(.*)$/;
const QUOTE  = /^\s*>\s?(.*)$/;
const RULE   = /^\s*([-*_])\s*(?:\1\s*){2,}$/;
const CELLS  = /\|/;
const DASHES = /^[\s:|-]*-[\s:|-]*$/;

/* ⛔ A FLOOR ON THE RECURSION, because this text was written by a model
   that had just read arbitrary web pages. Measured against the extracted
   parser: 20,000 `>` on one line, or a list indented 10,000 levels, throws
   RangeError - and the throw does not land in the parser, it lands in the
   event handler, where it strands the step clock, skips the redraw and eats
   the queued instruction. Past this depth the marks are drawn as the text
   they are, which is what nesting that deep actually is. */
const DEEP = 24;
function blocks(text, into, depth){
  depth = depth || 0;
  const lines = text.split('\n');
  let i = 0;
  while(i < lines.length){
    const line = lines[i];
    if(!line.trim()){ i++; continue; }
    const head = HEAD.exec(line);
    if(head){
      /* `#` lands on h3: the page's own title is above this pane, and an answer
         that opened at h1 would outrank it in the document outline. */
      const h = el('h' + Math.min(head[1].length + 2, 6), 'md-h');
      inline(head[2], h); into.appendChild(h); i++; continue;
    }
    if(RULE.test(line)){ into.appendChild(el('hr','md-hr')); i++; continue; }
    if(QUOTE.test(line) && depth < DEEP){
      const held = [];
      while(i < lines.length && QUOTE.test(lines[i])) held.push(QUOTE.exec(lines[i++])[1]);
      const q = el('blockquote','md-q');
      blocks(held.join('\n'), q, depth + 1); /* a quote holds blocks like any other */
      into.appendChild(q); continue;
    }
    if(CELLS.test(line) && i + 1 < lines.length && DASHES.test(lines[i + 1])
       && lines[i + 1].includes('-')){ i = tableAt(lines, i, into); continue; }
    if((BULLET.test(line) || NUMBER.test(line)) && depth < DEEP){
      i = listAt(lines, i, into, depth); continue;
    }
    /* ⛔ THE FIRST LINE IS TAKEN WITHOUT ASKING, and that is what makes this
       loop finish. Every branch above consumes; this one is the floor, so if
       its condition ever excluded the line that got here the walker would sit
       on it forever building empty paragraphs - a hung tab, not a bad render.
       Measured while mutating the list branch away: the browser stops. */
    const held = [lines[i++]];
    while(i < lines.length && lines[i].trim() && !HEAD.test(lines[i])
          && !RULE.test(lines[i]) && !QUOTE.test(lines[i])
          && !BULLET.test(lines[i]) && !NUMBER.test(lines[i])) held.push(lines[i++]);
    const p = el('p','md-p');
    inline(held.join('\n'), p);
    into.appendChild(p);
  }
}

/* Both of these return the line to carry on from, so the walker above never has
   to guess how much they ate - a block parser that advances by one and hopes is
   how a list ends up inside itself. */
function listAt(lines, i, into, depth){
  const first = BULLET.exec(lines[i]) || NUMBER.exec(lines[i]);
  const base = first[1].length;
  const ordered = !BULLET.test(lines[i]);
  const box = el(ordered ? 'ol' : 'ul', 'md-l');
  let item = null;
  while(i < lines.length && lines[i].trim()){
    const mark = BULLET.exec(lines[i]) || NUMBER.exec(lines[i]);
    if(!mark){
      /* A line under an item and not marked is the rest of that item. */
      if(!item) break;
      item.appendChild(document.createTextNode('\n' + lines[i].trim()));
      i++; continue;
    }
    if(mark[1].length > base && (depth || 0) < DEEP){
      i = listAt(lines, i, item || box, (depth || 0) + 1); continue;
    }
    if(mark[1].length < base || !BULLET.test(lines[i]) !== ordered) break;
    item = el('li','md-i');
    inline(mark[2], item);
    box.appendChild(item);
    i++;
  }
  into.appendChild(box);
  return i;
}

function tableAt(lines, i, into){
  const cells = row => row.replace(/^\s*\|/,'').replace(/\|\s*$/,'').split('|');
  const box = el('table','md-t');
  const head = el('tr','md-r');
  for(const c of cells(lines[i])) inline(c.trim(), head.appendChild(el('th')));
  box.appendChild(head);
  i += 2;                                   /* the header row and its dashes */
  while(i < lines.length && lines[i].trim() && CELLS.test(lines[i])){
    const tr = el('tr','md-r');
    for(const c of cells(lines[i])) inline(c.trim(), tr.appendChild(el('td')));
    box.appendChild(tr); i++;
  }
  into.appendChild(box);
  return i;
}

function rich(text){
  const frag = document.createDocumentFragment();
  /* An odd number of fences means the last block never closed, which is what a
     half-written answer looks like. It is still shown as code: the alternative
     is prose that changes shape when the closing fence arrives. */
  text.split('```').forEach((block, i) => {
    if(i % 2) frag.appendChild(el('pre','out', block.replace(/^[a-z]*\n/i, '')));
    else if(block.trim()) blocks(block, frag, 0);
  });
  return frag;
}
/* ---- end markdown ---- */

/* Raw tool names read as the machine's word order. One table, two tenses. */
const VERB = {
  browser_navigate:['Navigating','Navigated'], browser_click:['Clicking','Clicked'],
  browser_click_at:['Clicking','Clicked'],     browser_type:['Typing','Typed'],
  browser_press_key:['Pressing','Pressed'],    browser_read_text:['Reading','Read'],
  browser_read_html:['Reading','Read'],        browser_snapshot:['Inspecting','Inspected'],
  browser_evaluate:['Evaluating','Evaluated'], browser_take_screenshot:['Capturing','Captured'],
  browser_watch:['Watching','Watched'],
  browser_select_option:['Choosing','Chose'],
  session_new_page:['Opening tab','Opened tab'],   session_select_page:['Switching tab','Switched tab'],
  session_close_page:['Closing tab','Closed tab'], session_list_pages:['Listing tabs','Listed tabs'],
  session_start:['Starting browser','Started browser'],
  browser_open:['Opening browser','Opened browser'],
  browser_close:['Closing browser','Closed browser'],
  browser_list:['Listing browsers','Listed browsers'],
  browser_focus:['Switching browser','Switched browser'],
  session_list:['Listing sessions','Listed sessions'],
  session_forget:['Deleting session','Deleted session'],
  session_status:['Checking session','Checked session']
};
const LEAD = /^(I will |I'll |I am |I'm |Let me |Now I will |Now I'll )/i;
/* ⛔ MEASURED IN CHARACTERS, SPENT IN PIXELS - the same defect this project
   recorded when `ch` was mistaken for a character, one surface later. The
   label track is 416px wide at the default split, the mono face is 7.15px a
   character at 13px and the verb in front eats about 67, so the row shows
   about FORTY-EIGHT. The branch accepted a hundred and twenty. Counted on a
   live transcript: 43 rows of 108 were cut off AND had their disclosure
   removed, so the one thing that could have shown the rest was gone. */
const LONG = 48;

const thread = $('thread'), anchor = $('anchor'), log = $('log');
let turn = null, live = null, hold = null, n = 0, t0 = 0, timer = 0;
let busyNow = false, queued = null, pinned = false, settle = 0;

/* ---------------- the queued message ----------------
   ⛔ IT WAS A VARIABLE, AND A RELOAD ATE IT. Somebody types a follow-up while
   the agent is working, the page reloads - a refresh, a crash, a laptop lid -
   and the sentence they wrote is gone with nothing said. That is the one thing
   this interface must not do to typed text: the transcript is saved, the
   answer is saved, and the instruction that was waiting to run was the only
   thing held in a variable.

   Kept per conversation, because it belongs to one: switching sessions must
   not carry somebody's pending sentence into another chat. Written through ONE
   function rather than beside each of the five places that assign it - that is
   how it went unsaved in the first place, and a sixth assignment somewhere
   would go unsaved the same way.

   Storage can refuse (a private window, site data blocked) and the page has to
   work when it does: the queue simply goes back to being a variable. */
/* ⛔ A FUNCTION AND NOT A CONSTANT, because a constant here read `here`
   before `here` was declared - and a top-level binding used in its own dead
   zone throws at parse time, which kills the WHOLE script: no event stream, no
   session column, no workspace, and the page still renders. 440 tests green
   with the page dead, for the second time in two days and by a different
   mechanism than the first. Computed when called, the order of the lines stops
   being something anybody has to keep right. */
const qkey = () => 'aihawk.queued.' + here;
function setQueued(text){
  queued = text || null;
  try {
    if(queued) localStorage.setItem(qkey(), queued);
    else localStorage.removeItem(qkey());
  } catch(err){}
  paint();
}
function queuedFromBefore(){
  try { return localStorage.getItem(qkey()); } catch(err){ return null; }
}
let pend = null, pendTimer = 0;

const dur = ms => ms < 1000 ? Math.round(ms) + 'ms' : (ms/1000).toFixed(1) + 's';

function newTurn(){
  const hint = $('hint'); if(hint) hint.remove();
  n = 0; turn = el('section','turn'); thread.appendChild(turn); return turn;
}
function put(node, replay){ if(!turn) newTurn(); if(replay) node.dataset.replay = '1';
                            turn.appendChild(node); }

/* The narration is held for one event, so a sentence followed by tool calls
   reads as their lead-in and a sentence with nothing after it reads as the
   answer. One event of lookahead is all a stream allows and all this needs. */
function flush(asAnswer, replay){
  if(hold === null) return;
  const text = hold.replace(LEAD,'').replace(/^\w/, c => c.toUpperCase());
  hold = null;
  const box = el('div', asAnswer ? 'answer' : 'say');
  /* ⛔ A DEFECT INSIDE ONE ANSWER MUST NOT TAKE THE TURN WITH IT. This runs
     from the event handler, and the caller goes on to clear the step clock,
     redraw the column and send whatever was queued - so a throw here stranded
     a 10 Hz timer for the life of the page and silently swallowed an
     instruction somebody had typed. The text is shown as text rather than
     lost: the same shape as the scheduler, which keeps doing its own job when
     a pass inside it fails. */
  try {
    box.appendChild(rich(text));
  } catch(err){
    box.appendChild(el('pre','out', text));
  }
  put(box, replay);
}

function step(text, replay){
  const sp = text.indexOf(' ');
  const name = sp < 0 ? text : text.slice(0, sp);
  const arg  = sp < 0 ? ''   : text.slice(sp + 1);
  const d = el('details','ev'); d.dataset.state = 'run'; d.dataset.name = name;
  const s = el('summary','row');
  const lab = el('span','lab');
  lab.appendChild(el('b', null, (VERB[name] || ['Calling','Called'])[0]));
  if(arg){ lab.append(' ', el('code', null, arg)); }
  s.append(el('span','g', ++n), lab, el('span','meta'));
  d.appendChild(s);
  put(d, replay);
  live = d;
  clearInterval(timer);
  if(!replay){                       /* a replayed step has no live clock to run */
    t0 = performance.now();
    const meta = s.lastElementChild;
    timer = setInterval(() => meta.textContent = dur(performance.now() - t0), 100);
  }
}

/* A result or an error folds into the step above it, which is what makes a step
   one unit carrying its target, its timing, its state and its own disclosure. */
function land(kind, text, replay){
  clearInterval(timer);
  if(!live) return orphan(kind, text, replay);
  const d = live, s = d.firstElementChild;
  live = null;
  d.dataset.state = kind === 'err' ? 'err' : 'ok';
  s.querySelector('.lab b').textContent =
    (VERB[d.dataset.name] || ['Calling','Called'])[kind === 'err' ? 0 : 1];
  if(!replay) s.lastElementChild.textContent = dur(performance.now() - t0);
  /* Short output goes ON the row and the row stops being expandable. In an
     ordinary run most rows are then one line with the answer already visible,
     which is the difference between a list and a stack of accordions. */
  if(text.length <= LONG && text.indexOf('\n') < 0){
    d.dataset.body = 'none';
    s.querySelector('.lab').append(' ', el('span','inline', text));
  } else {
    /* Anything that does not fit keeps a body, so the chevron is present for
       exactly the rows that need it. */
    d.appendChild(el('pre','out', text));
    /* And the row says it on hover too: nobody should have to open a
       disclosure to find out whether it is worth opening. */
    s.querySelector('.lab').title = text.slice(0, 400);
  }
}

function orphan(kind, text, replay){
  const p = el('div', kind === 'err' ? 'orph' : 'say');
  p.append(el('span','sr', kind === 'err' ? 'error ' : ''), el('span', null, text));
  put(p, replay);
}

/* The wait, made visible. Measured on this interface: the instruction reaches
   the screen 23 ms after the click and the server accepts it in 2, but the
   first thing the AGENT does lands 4 to 7 seconds later, because the model has
   to read the whole transcript before it can act - and the pane said nothing at
   all in between. That silence is what "everything freezes for a second" was
   describing: not a blocked page, an unlit one.

   A running clock and not a spinner, because the number is the honest part:
   it says the machine is alive AND how long this is taking, and it is the same
   clock a step already shows, so the wait reads as part of the same sequence. */
function waiting(){
  if(pend) return;
  pend = el('div','pend');
  const lab = el('span','lab');
  lab.append(el('b', null, 'Thinking'));
  pend.append(el('span','g', ''), lab, el('span','meta'));
  put(pend, false);
  const meta = pend.lastElementChild, from = performance.now();
  pendTimer = setInterval(() => meta.textContent = dur(performance.now() - from), 100);
}

function waited(){
  if(!pend) return;
  clearInterval(pendTimer);
  pend.remove();
  pend = null;
}

/* Only the first settle. After that the CSS sentinel pins the view, and a reader
   who has scrolled up is never yanked because nothing here fires again. */
function settleOnce(){
  if(pinned) return;
  clearTimeout(settle);
  settle = setTimeout(() => { pinned = true; anchor.scrollIntoView({block:'end'}); }, 150);
}

/* ---------------- which conversation this page is in ----------------
   ⛔ ONE PLACE, AND EVERY REQUEST GOES THROUGH IT. The server routes all read
   `?s=`, so a fetch that forgets it acts on the DEFAULT conversation while the
   page shows another - and the way that shows up is the picture on the right
   belonging to somebody else's browser, with nothing red anywhere. `at()` is
   the only thing that writes the parameter, so there is one place to be wrong
   and it is covered by a test that reads this file.

   The id is kept in the URL rather than in a variable, so a reload, a bookmark
   and a second tab all land in the same conversation instead of silently
   dropping to the default one. */
let here = new URLSearchParams(location.search).get('s') || 'default';
const at = (path) => path + (path.includes('?') ? '&' : '?') + 's=' + encodeURIComponent(here);

let es = null;
function listen(){
  if(es) es.close();
  es = new EventSource(at('/chat/events'));
  es.onmessage = onEvent;
  /* ⛔ A STREAM THAT DIED LOOKS EXACTLY LIKE AN AGENT WITH NOTHING TO SAY.
     EventSource reconnects on its own, so this is not a retry - it is the
     only signal that the silence is the connection and not the work. The dot
     and the word beside it describe the BROWSER, and said `live` throughout. */
  es.onerror = () => {
    if(es.readyState === EventSource.CONNECTING) say('offline', 'reconnecting');
    if(es.readyState === EventSource.CLOSED) say('offline', 'the stream closed');
  };
  es.onopen = () => { if(right.dataset.state === 'offline') say(frozen ? 'frozen' : 'live'); };
}
const onEvent = (e) => {
  const m = JSON.parse(e.data), r = m.replay;
  switch(m.kind){
    case 'model': $('model').textContent = m.text; break;
    /* Sent to every listener, so a second tab clears too instead of showing a
       transcript the server has already forgotten. */
    case 'fresh': wipe(); break;
    case 'busy':
      busyNow = m.text === '1';
      /* Not on a replay: those events describe a wait that is over. */
      if(busyNow && !r) waiting(); else waited();
      if(!busyNow){ flush(true, r); live = null; clearInterval(timer);
                    /* The name of a conversation is decided by its FIRST
                       instruction, on the server, so the column is stale from
                       the moment a new session is used until it is redrawn.
                       Redrawn on the end of a turn and not on its start: the
                       turn count beside the name is only right once. */
                    if(!r) drawChats();
                    if(queued){ const t = queued; setQueued(null); send(t); } }
      paint(); break;
    case 'you':   flush(false, r); live = null; newTurn();
                  put(el('div','you', m.text), r); break;
    case 'said':  waited(); flush(false, r); hold = m.text; break;
    case 'tool':  waited(); flush(false, r); step(m.text, r); break;
    case 'result':
    case 'err':   flush(false, r); land(m.kind, m.text, r);
                  /* The step is done and the model is reading its result, which
                     is another wait of the same kind: the loop asks again before
                     anything else can appear. */
                  if(busyNow && !r) waiting();
                  break;
    /* Deliberately total: a kind this page has never heard of is still shown,
       for the same reason an unknown tool still renders its arguments. */
    default:      flush(false, r); orphan('said', m.text, r);
  }
  settleOnce();
};

new IntersectionObserver(([e]) => { $('jump').hidden = e.isIntersecting; },
                         {root: log}).observe(anchor);
$('jump').onclick = () => anchor.scrollIntoView({block:'end', behavior:'smooth'});

/* ---- the composer. It is never disabled: greying out the input the moment the
   run gets interesting is most of what reads as unfinished. ---- */
const i = $('i'), go = $('go'), halt = $('halt'), f = $('f'), chip = $('chip'),
      fresh = $('fresh');

function paint(){
  const typed = i.value.trim().length > 0;
  /* Shown for as long as work is in flight and for no other reason: it is tied
     to the run, never to what the composer happens to contain. */
  halt.hidden = !busyNow;
  /* Refused while a run is in flight, and shown as refused rather than left to
     fail at the server: dropping a transcript something is still writing into
     is not undoable. */
  fresh.disabled = busyNow;
  go.disabled = !typed;
  go.setAttribute('aria-label',
    queued ? 'Replace queued message' : busyNow ? 'Queue for next turn' : 'Send');
  i.placeholder = queued ? 'Type to replace the queued message'
    : busyNow ? 'Type to queue a message' : 'What should the agent do?';
  chip.hidden = !queued;
}
i.addEventListener('input', () => {
  /* ⛔ ONE FORCED LAYOUT PER KEYSTROKE, NOT TWO. Reading scrollHeight after
     writing height forces the layout; reading it a SECOND time after the
     second write forces another, over a document holding the whole
     transcript. The one number is enough to decide both. */
  i.style.height = 'auto';
  const wants = i.scrollHeight;
  i.style.height = Math.min(wants, 200) + 'px';
  i.style.overflowY = wants >= 200 ? 'auto' : 'hidden';
  paint();
});
i.addEventListener('keydown', e => {
  if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); f.requestSubmit(); }
});
/* Escape stops the run, from anywhere on the page. The button is the visible
   way and this is the one a hand already on the keyboard reaches first, which
   matters more now that the loop has no ceiling of its own. Not while typing
   into the composer with something in it: there Escape belongs to the draft. */
document.addEventListener('keydown', e => {
  if(e.key !== 'Escape' || !busyNow) return;
  if(document.activeElement === i && i.value.trim()) return;
  /* Through the same door as the button: a hoisted declaration, so calling it
     from above where it is written is safe and nothing here depends on the
     order of the lines. */
  ask('/chat/stop', undefined,
      'The stop did not reach the agent - it is still running');
});
/* A pencil and not a cross: a cross would read as "cancel the queued message".
   This returns it to the composer to be edited. */
chip.onclick = () => { i.value = queued; setQueued(null); i.focus();
                       i.dispatchEvent(new Event('input')); };

/* ⛔ THE BOX IS NOT EMPTIED UNTIL THE SERVER HAS THE SENTENCE. This page
   already argues, about the QUEUED path, that losing typed text with nothing
   said is the one thing it must not do - and then the primary path cleared
   the box first and fired a fetch nobody read. Server restarting, port
   changed, laptop asleep: the instruction was gone and the transcript never
   grew, which reads as the agent ignoring you. */
async function send(text){
  try {
    const r = await door('/chat/send', {method:'POST',
                         headers:{'Content-Type':'application/json'},
                         body: JSON.stringify({text})});
    if(!r.ok) throw new Error('HTTP ' + r.status);
  } catch(err){
    /* Give it back, exactly as it was, and say why - the sentence is the
       person's work and this is the only copy of it. */
    i.value = text;
    i.dispatchEvent(new Event('input'));
    if(vanished) return;
    orphan('err', 'That instruction did not reach the server (' + err.message
           + '). It is back in the box - try again.');
  }
}
/* Clearing the page is NOT what this does, and the difference is the point:
   it asks the server to forget the transcript, because the transcript is what
   every turn resends and therefore what the wait and the bill are made of. The
   page is wiped only when the server says it has forgotten. */
function wipe(){
  waited();
  thread.textContent = '';
  turn = null; live = null; hold = null; n = 0;
  clearInterval(timer);
  /* Idle until told otherwise. On a reconnection the server sends this wipe
     first and the run state after it, so a page that reconnects to a RESTARTED
     process stops believing in a run that died with the old one - which
     otherwise left the composer saying "queue for next turn" forever. */
  busyNow = false;
  setQueued(null);
}
let vanished = false;
/* ⛔ ONE PLACE ASKS THIS CONVERSATION FOR ANYTHING, so one place can notice
   that it is not there any more. Six fetches carry `?s=`, and each of them
   would otherwise need the same three lines - written six times, the seventh
   is where a page goes on talking to a session somebody deleted. Which is not
   hypothetical: every one of those questions used to DECLARE the session again
   on the server, so a delete that had already closed the browsers and erased
   the transcript came straight back as an empty row, for as long as one tab
   stayed open on it. */
async function door(path, init){
  const r = await fetch(at(path), init);
  /* 410 and nothing else. Every other failure is worth trying again; this one
     is the only one that will never stop being true. */
  if(r.status === 410){ vanish(); throw new Error('this conversation was deleted'); }
  return r;
}

/* Deleted from the other tab, or from another window. The page says so and
   stops asking, in that order. It does NOT navigate anywhere: the column
   beside it still works, and where to go next is not this page's decision to
   make for somebody who is in the middle of reading. */
function vanish(){
  if(vanished) return;
  vanished = true;
  if(es) es.close();
  say('offline', 'deleted');
  orphan('err', 'This conversation was deleted. Nothing here is live any more '
         + '- open another one from Sessions, or start a new one.');
  /* Everything goes inert EXCEPT the way out. `inert` rather than `disabled`
     because these are subtrees and not single controls, and it takes them out
     of the pointer AND the tab order - a composer that answers the keyboard
     while it cannot send is the same lie in a different place. The column of
     sessions keeps its full contrast, because the sentence above tells the
     person to use it. */
  for(const box of [f, $('right'), $('fresh')]) box.inert = true;
  drawChats();
}

/* ⛔ ONE PLACE KNOWS WHAT TO DO WHEN A REQUEST DOES NOT ARRIVE. Six
   `fetch` calls had no failure path at all, and the sharpest of them is the
   stop button: this file says elsewhere that it is the only thing that ends a
   run which will not converge, and a press that never reached the server
   looked exactly like a press that did. `ask` returns the response when it
   worked and says so on the page when it did not. */
async function ask(path, body, whatFailed){
  try {
    const r = await door(path, body === undefined
      ? {method:'POST'}
      : {method:'POST', headers:{'Content-Type':'application/json'},
         body: JSON.stringify(body)});
    if(!r.ok) throw new Error('HTTP ' + r.status);
    return r;
  } catch(err){
    /* The one failure that already said its piece, and says it once. */
    if(!vanished) orphan('err', whatFailed + ' (' + err.message + ').');
    return null;
  }
}

/* ⛔ THE ONLY UNGUARDED DESTRUCTIVE CONTROL, AND IT SAT IN THE PERMANENT
   HEADER. Deleting a whole session - rarer, and behind a closed panel - asked
   first and named what went with it; clearing the transcript, which also
   makes the model forget everything it has been told, went on one click. The
   guard was on the wrong control. Named on the message, and named again on
   the button. */
fresh.onclick = () => {
  if(!confirm('Clear this conversation? The agent forgets everything you have told it. Its browsers stay open.')) return;
  ask('/chat/fresh', undefined, 'Could not clear this conversation');
};

halt.onclick = () => ask('/chat/stop', undefined,
                         'The stop did not reach the agent - it is still running');
f.onsubmit = (e) => {
  e.preventDefault();
  const t = i.value.trim();
  if(!t){ return; }
  i.value = ''; i.style.height = 'auto';
  if(busyNow){ setQueued(t); return; }
  send(t); paint();
};


/* ---- the browser pane ---- */
const right = $('right'), stateEl = $('state'), urlEl = $('url');
let frozen = false;

/* The second argument is the sentence behind a one-word state, shown on hover:
   an "error" with no reason is a thing to restart, an "error" that says the
   engine has no screencast is a thing to upgrade. */
/* ⛔ AND IT SAYS NOTHING WHEN IT WOULD ONLY REPEAT THE TAB NEXT TO IT.
   `Live` selected with the word `live` printed beside it is one fact twice,
   one of them in the place the eye goes for news. `idle`, `busy` and `error`
   are news, and they are now the only things that appear there; the dot keeps
   carrying live and frozen, which is what a dot is for. */
/* ⛔ HIDDEN FROM THE EYE, NOT FROM THE EAR. `hidden` is display:none, and a
   live region mutated inside a display:none subtree announces nothing - so the
   one transition that matters, live to error, was silent for a screen reader
   precisely because the word had been redundant a moment earlier. Off-screen
   instead: the eye sees the tab it repeats, the ear still hears the change. */
function say(s, why){ right.dataset.state = s; stateEl.textContent = s;
                      stateEl.classList.toggle('sr', s === 'live' || s === 'frozen');
                      stateEl.title = why || ''; }
async function reason(r){ try { return (await r.json()).error || ''; } catch(err) { return ''; } }

$('mode').onclick = (e) => {
  const b = e.target.closest('button'); if(!b) return;
  frozen = b.dataset.v === 'hold';
  for(const x of $('mode').children) x.setAttribute('aria-pressed', String(x === b));
  say(frozen ? 'frozen' : 'live');
};


/* ⛔ FRAMES A SECOND EACH, BY HOW MANY SCREENS ARE ON THE STAGE, and every one
   of these numbers is measured rather than chosen. Four real browsers, this
   same pipe, 2026-09-09: a frame costs 5 to 6 ms - not the 22 ms this file
   assumed for months - because the capture already runs inside the engine and
   the server hands over the latest picture instead of taking one. Polling as
   fast as the answers came back, each pane got about 20 frames a second
   whether there was one of them or four, so four panes moved 80 frames a
   second and an action still landed in 49 ms against 40 with a single pane.
   The pipe is the constraint at eight, not at four.

   So the budget is spent deliberately and not to the limit: one screen gets
   the 25 the engine is asked to produce, two get 20 each, four get 10 each -
   40 requests a second at most, about a quarter of what the pipe can carry,
   leaving the rest to the agent whose clicks share it. */
/* And it is paced on the screens that are ACTUALLY on the stage, never on
   the layout picked. Two browsers in a four-up layout are two browsers: the
   table this used to be gave them 10 frames a second each because the
   BUTTON said four, halving the thing the person asked for by reading the
   wrong number. The ceiling below is the measured budget - 40 requests a
   second, about a quarter of the pipe - and the top rate is what the engine
   is asked to produce, so asking for more would make frames to throw away. */
const LAYOUTS = [1, 2, 4];
const TOPRATE = 25, CEILING = 40;
const fps = (n) => Math.min(TOPRATE, Math.floor(CEILING / n));
const onScreen = () => Math.max(1, $('stage').children.length);
const pause = () => Math.round(1000 / (fps(onScreen()) * onScreen()));

/* One scheduler for the whole stage. It used to be two - a fast one for the
   single live pane and a slow one for the previews - and with a grid that
   would be two numbers describing one rate, which is how a pace stops being
   something anybody can read off the page. */
/* ⛔ THE SCHEDULER CANNOT BE ALLOWED TO DIE, and it died the first time this
   ran. `ageAll` reached for the age label on the placeholder cell, which has
   no caption, threw a TypeError, and because the throw was outside the fetch's
   try the timer at the bottom was never reached: the pump stopped for good, in
   silence, and what you see then is a pane that never updates - which reads as
   a server that has stopped answering rather than as a page with a bug in it.
   The body is a separate function now and the scheduling is the only thing
   this one does, so no defect inside a pass can take the loop with it. */
/* ⛔ NOTHING IS POLLED WHILE NOBODY IS LOOKING. Four loops ran flat out in
   a background tab: the frame pump at up to 40 requests a second, the address
   every two, the fleet every three, a preview every four hundred
   milliseconds. That budget was measured against what the pipe can carry
   while the AGENT is using it - and the agent keeps working when the tab is
   hidden, which is exactly when the page was still spending its share on
   pictures nobody could see. The loops keep their rhythm so a page coming
   back is one tick away from current. */
/* ⛔ AND NOTHING IS POLLED FOR A CONVERSATION THAT NO LONGER EXISTS, which is
   the same gate because it is the same question: is there anything here worth
   asking about. See `vanish`. */
const looking = () => !document.hidden && !vanished;

async function tick(){
  if(looking()){ try { await onePass(); } catch(err) {} }
  setTimeout(tick, pause());
}

/* And the moment it is looked at again, before the next tick lands. */
document.addEventListener('visibilitychange', () => {
  if(!looking()) return;
  onePass().catch(() => {});
  paintWhere(); drawFleet();
});

async function onePass(){
  const cells = [...$('stage').children];
  if(cells.length && !frozen){
    const cell = cells[turnOf % cells.length];
    turnOf++;
    const id = cell.dataset.id;
    if(cell.dataset.blank === '1'){ say(cells.length > 1 ? 'live' : 'idle'); }
    else try {
      const r = await door('/live/frame?b=' + encodeURIComponent(id)
                           + '&t=' + Date.now(), {cache:'no-store'});
      if(r.status === 204){ blank(cell, 'no page yet'); if(id === watched()) say('idle'); }
      else if(r.ok){
        const im = cell.querySelector('img'), blob = await r.blob(), old = im.src;
        im.src = URL.createObjectURL(blob);
        if(old && old.startsWith('blob:')) URL.revokeObjectURL(old);
        im.hidden = false;
        shapeFrom(cell, im);
        setState(cell, 'live');
        /* The monotonic clock, like the step timer and the thinking timer:
           a wall clock corrected by NTP or a DST step marks every screen
           stale at once, or hides one that really is. */
        cell.dataset.at = String(Math.round(performance.now()));
        if(id === watched()) say('live');
      }
      /* The capture could not answer, and the body says why: no frame within
         the server's wait (a minimised window is captured as nothing), or an
         engine without the screencast. The last frame stays on screen - a
         picture of where the browser was beats a blank pane - and the reason
         goes ON the screen rather than into a tooltip nobody hovers: this
         used to leave the same black rectangle as a pane that had simply not
         drawn yet, which is how a failure got to look like patience.
         
         And it is said for EVERY screen, not only the watched one. On a 2x2
         the three you are not following are exactly the ones whose silence
         you would otherwise have to guess at. */
      else {
        const why = r.status === 503 ? await reason(r) : '';
        setState(cell, 'error', 'the capture failed',
                 why || 'the server answered ' + r.status);
        if(id === watched()) say('error', why);
      }
    } catch(err){ if(id === watched()) say('offline'); }
    ageAll(cells);
  }
}

/* ⛔ THE BROWSER'S OWN CHROME IS CUT OFF THE TOP OF EVERY SCREEN. The capture
   is a picture of a window, and the tab strip and the address bar in it are a
   second address bar under the one this page already draws - the same fact
   twice, in the place where the eye goes for the page itself. Measured on
   three captures: 57/688, 43/515 and 57/688, so the chrome is 8.3% of the
   window's height and that is a proportion rather than a number of pixels.

   ⛔ AND IT IS CUT WITH A MARGIN IN PERCENT, NOT WITH MEASURED PIXELS. A
   percentage margin resolves against the containing block's width, so the
   chrome expressed as a fraction of the picture's WIDTH crops the same slice at
   any size, and the frame - which shrink-wraps the picture - ends up the
   cropped height by construction. The version before this one read the box with
   getBoundingClientRect on every frame, cached two numbers to avoid a reflow,
   and had to be told again on every resize. */
const CHROME = 0.083;
function shapeFrom(cell, im){
  if(!im.naturalWidth) return;
  const key = im.naturalWidth + 'x' + im.naturalHeight;
  if(cell.dataset.shape === key) return;
  cell.dataset.shape = key;
  const box = cell.querySelector('.frame');
  if(!box) return;
  const seen = im.naturalHeight * (1 - CHROME);
  box.style.setProperty('--cut',
    (CHROME * im.naturalHeight / im.naturalWidth * 100).toFixed(3) + '%');
  box.style.setProperty('--arn', (im.naturalWidth / seen).toFixed(4));
}

/* ⛔ ONE PLACE DECIDES WHAT A SCREEN IS SHOWING, because four states used to
   draw one black rectangle: no frame yet, no tab, stopped answering, and a
   capture that failed were pixel-identical, and all four read as a product
   that is broken. `data-blank` is a different question - whether to ASK for a
   picture at all - and it stays where it was: a browser with no tab is not
   asked, because asking spends a round trip to be told there is nothing. */
function setState(cell, state, title, detail){
  cell.dataset.state = state;
  const veil = cell.querySelector('.veil');
  if(!veil) return;
  veil.hidden = state === 'live';
  veil.textContent = '';
  if(state === 'live') return;
  if(state === 'waiting') veil.appendChild(el('span','pulse'));
  if(title) veil.appendChild(el('b', null, title));
  if(detail) veil.appendChild(el('span', null, detail));
}

/* ⛔ A PICTURE THAT HAS STOPPED MUST NOT READ AS ONE THAT IS RUNNING. On a
   healthy stage every screen is refreshed every 40 to 100 ms, so anything past
   a couple of seconds means that browser has stopped answering - and the last
   frame is still sitting there looking alive. Two seconds, because at four
   screens a round is 100 ms and a hiccup of three or four rounds is not news. */
function ageAll(cells){
  const now = performance.now();
  for(const c of cells){
    /* The empty stage has no stamp to write into, which is how this function
       killed the pump the first time it ran. */
    const lab = c.querySelector('.stamp');
    if(!lab) continue;
    const at2 = Number(c.dataset.at || 0), old = at2 && (now - at2) > 2000;
    /* ⛔ ONLY WHEN IT CHANGES. This runs at the end of every pass, so up to
       forty times a second, and it wrote three properties per cell whether or
       not anything had moved - about 480 DOM writes a second at four screens,
       for a label that is empty 99% of the time. Assigning '' to textContent
       still replaces the node's children. */
    const says = old ? Math.round((now - at2) / 1000) + 's' : '';
    if(lab.textContent !== says){
      lab.textContent = says;
      lab.title = old ? 'no frame for this long' : '';
    }
    /* Guarded separately: the text is unchanged between two fresh passes but
       the visibility still has to be right the first time. */
    if(lab.hidden !== !old) lab.hidden = !old;
    if(old && c.dataset.state === 'live') setState(c, 'stale');
    else if(!old && c.dataset.state === 'stale') setState(c, 'live');
  }
}

/* Built from elements with textContent and never innerHTML: this string comes
   from whatever page is being automated. */
function paintUrl(u){
  urlEl.textContent = ''; urlEl.title = u || ''; urlEl.className = u ? '' : 'dim';
  if(!u){ urlEl.textContent = 'no page yet'; return; }
  let a; try { a = new URL(u); } catch(err) { urlEl.textContent = u; return; }
  const part = (t,c) => urlEl.appendChild(el('span', c, t));
  part(a.protocol + '//', 'dim'); part(a.host, 'host'); part(a.pathname + a.search, 'dim');
}
function paintTabs(rows){
  const box = $('tabs');
  /* One tab is not a strip. Showing it would be chrome repeating the address
     bar directly beneath it. */
  if(!rows || rows.length < 2){ box.hidden = true; box.textContent = ''; return; }
  box.hidden = false;
  box.textContent = '';
  for(const r of rows){
    const b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('aria-selected', String(!!r.active));
    b.title = (r.title || '') + (r.url ? '  -  ' + r.url : '');
    b.dataset.id = r.id;
    let host = '';
    try { host = new URL(r.url).host; } catch(err) { host = ''; }
    b.appendChild(el('span','t', r.title || host || r.id));
    box.appendChild(b);
  }
}
/* A tab DOES something, so it is the one thing in this chrome that may look
   clickable. Selecting is an action on the browser like any other, and it goes
   through the same tool an agent would call. */
$('tabs').onclick = (e) => {
  const b = e.target.closest('button'); if(!b) return;
  ask('/live/select', {id: b.dataset.id}, 'Could not switch to that tab');
};

/* ⛔ THE ADDRESS FOLLOWS THE SCREEN YOU ARE LOOKING AT, and with four of them
   there is a case where no single address is the honest answer: nobody has
   picked one, so the bar would be showing whichever browser the agent happens
   to be in while three other pages sit beside it, unnamed. It says how many
   instead, and how to choose. Once a screen has been clicked the bar follows
   that one, at any layout. */
function severalOpen(n){
  urlEl.textContent = ''; urlEl.className = 'dim'; urlEl.title = '';
  urlEl.append(el('span', null, n + ' pages open'),
               el('span', 'hint', 'click a screen to follow it'));
}

/* ⛔ THE WORK AND THE TIMER ARE SEPARATE, for the reason the strip beside it
   was: changing the layout changes what the address should say, and there is
   nothing to wait for. While this was one function the bar kept the old answer
   until the next poll landed - two seconds showing one page's address over four
   screens. Calling `where` itself from a click would start a SECOND timer
   chain, which is how a pace stops being one number. */
async function where(){ if(looking()) await paintWhere(); setTimeout(where, 2000); }

async function paintWhere(){
  const many = grid > 1 && !pinned2 && onStage().length > 1;
  if(many){ severalOpen(onStage().length); paintTabs([]); }
  else try {
    const who = watched();
    /* ⛔ AND NEVER OF A BROWSER THAT IS NOT RUNNING. Asking for the tabs of a
       declared-but-stopped browser STARTS it - the server resolves the id and
       the registry wakes the engine - so clicking a stopped browser's chip
       spent 800 MB and seven seconds nobody asked for, and then kept asking
       every two seconds because the pin never cleared. The frame pump, the
       preview row and both cell builders already know this rule; this was the
       fifth place that had to and did not. */
    if(who && !fleet.some(b => b.id === who && b.running)){
      paintUrl(''); paintTabs([]); return;
    }
    /* `at`, inside `door`, is what adds the question mark, so the browser goes
       in as one too and it appends its own with an ampersand. */
    const r = await door(who ? '/live/tabs?b=' + encodeURIComponent(who)
                             : '/live/tabs', {cache:'no-store'});
    if(r.ok){ const j = await r.json(); paintUrl(j.url || ''); paintTabs(j.tabs); }
  } catch(err){}
}
/* ---------------- the session column ----------------
   Drawn from the server every time it changes rather than kept in step by hand:
   a name is set by the FIRST INSTRUCTION of a conversation, which happens on
   the server, so a column the page maintained locally would be right until
   somebody actually used a session. */
async function drawChats(){
  let rows = [];
  try { const r = await fetch('/sessions', {cache:'no-store'});
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

/* ---------------- the workspace ----------------
   ⛔ THE COST OF THE PREVIEWS DOES NOT GROW WITH THE NUMBER OF THEM, and that
   is the whole design rather than a detail. A frame costs about 22 ms on the
   pipe that ACTIONS share, and the pipe is serialised: eight panes each asking
   thirteen times a second would want 2.3 seconds of pipe per second, so the
   picture would be behind and every click would queue behind the pictures.

   So there is ONE live pane - the focused one, at the full rate, in `tick` -
   and ONE slow loop that refreshes a single other pane every 400 ms, taking
   them in turn. Seven others therefore refresh about every three seconds, and
   whether there are two panes or eight the previews cost the same two and a
   half requests a second. A loop per pane would have been the obvious way to
   write it and its cost would be the thing the measurement forbids. */
const SLOW_MS = 400;
let fleet = [], nextPane = 0, focusHere = '';
let grid = 1, turnOf = 0;

/* ⛔ TWO DIFFERENT THINGS, AND THEY USED TO BE ONE. `focusHere` is the browser
   the AGENT drives - it lives on the server and only the agent moves it, by
   being asked. `pinned2` is the pane the PERSON is looking at, which is this
   page's own business and nobody else's.

   They were the same value until somebody said everything should be commanded
   from the chat, and folding them together is what made clicking a pane a
   COMMAND. Now the big pane follows the agent, which is what you want while it
   works, and looking somewhere else is a choice that sticks until you undo it. */
let pinned2 = null;
const watched = () => pinned2 || focusHere;

function thumbFor(b){
  /* ⛔ A BROWSER WITH NO PICTURE DOES NOT GET A PICTURE FRAME. Six declared
     but stopped browsers drew six 168x133 cards, each with the words `not up`
     in the middle of an empty rectangle - a gallery of failures under the
     stage, 133px tall, in the place the running ones live. A thing with no
     image is a NAME: it gets a chip, and the row becomes a list of what this
     session holds. Clicking one still asks to watch it, exactly as before. */
  if(!b.running){
    const chip = document.createElement('button');
    chip.type = 'button'; chip.className = 'chip'; chip.dataset.id = b.id;
    chip.title = 'Watch ' + b.id;
    /* Clicking a chip changes what the address bar and the stage follow, and
       nothing said so: the identical control one row up, the preview card,
       has carried this mark from the start. */
    chip.setAttribute('aria-current', String(b.id === watched()));
    chip.append(el('span','off'), el('span','id', b.id));
    chip.onclick = () => watchThis(b.id);
    return chip;
  }
  const el2 = document.createElement('button');
  el2.type = 'button'; el2.className = 'thumb'; el2.dataset.id = b.id;
  el2.title = 'Watch ' + b.id;
  const pic = el('div','pic');
  /* Three states, not two, and the third is the one that read as a failure.
     A browser that is RUNNING WITH NO TAB cannot be captured - the engine
     answers "no such tab" - and asking anyway spends a round trip to be told
     so, then paints ERROR over something that is simply empty. The tabs are
     already in the answer this pane was built from, so the question is asked
     of data rather than of the pipe. */
  if((b.urls || []).length){
    const im = document.createElement('img'); im.alt = ''; pic.appendChild(im);
  } else {
    pic.appendChild(el('span', null, 'no tab open'));
  }
  const cap = el('div','cap');
  cap.appendChild(el('span','id', b.id));
  cap.appendChild(el('span','st', ''));
  if(b.id === focusHere){
    const dot = el('span','dot');
    dot.title = 'the agent is working here';
    cap.appendChild(dot);
  }
  el2.append(pic, cap);
  el2.onclick = () => watchThis(b.id);
  return el2;
}

/* ⛔ THE WAIT IS SHOWN, because it is seven to fourteen seconds - measured, and
   the eighth browser takes twice the first. An interface that goes quiet for
   fourteen seconds is the defect this project fixed elsewhere with the Thinking
   clock, and a pane that simply does not change is indistinguishable from a
   click that did nothing. */
/* Looking, not commanding. Clicking the pane you are already watching gives
   the view back to the agent, so there is a way out of a choice as well as in. */
function watchThis(id){
  pinned2 = (pinned2 === id) ? null : id;
  drawStage(); drawStrip(); paintWhere();
}

/* ---- the stage: one screen, or two, or four ----
   Which browsers are on it and in what order: the one being watched first,
   then the rest as the server lists them. So clicking any screen or any
   preview brings that browser to the front, and at one-up that means it fills
   the stage - which is what "click it and go to another screen" means. */
function onStage(){
  const w = watched();
  const live = fleet.filter(b => b.running);
  const first = live.filter(b => b.id === w);
  return first.concat(live.filter(b => b.id !== w)).slice(0, grid);
}

/* ⛔ A BLOB URL IS NOT GARBAGE-COLLECTED WITH ITS ELEMENT. Every frame is
   an object URL, and the two rebuild paths threw their <img> away without
   revoking: the stage redraws whenever the agent moves to another browser -
   which it does on its own - so a long run leaked one full window capture per
   pane per switch, held until the tab closes. */
function dropFrames(box){
  for(const im of box.querySelectorAll('img')){
    if(im.src && im.src.startsWith('blob:')) URL.revokeObjectURL(im.src);
  }
}

function blank(cell, why){
  const im = cell.querySelector('img'); if(im) im.hidden = true;
  setState(cell, 'nopage', why || 'no tab open',
           'ask the agent to open a page here');
  cell.dataset.blank = '1';
  cell.dataset.at = '';
}

/* One screen: a frame that wraps the picture, the name written on it, and
   whatever the picture cannot say written over it. */
function screenFor(b, current){
  const cell = document.createElement('button');
  cell.type = 'button'; cell.className = 'screen'; cell.dataset.id = b.id;
  cell.setAttribute('aria-current', String(current));
  cell.title = 'Watch ' + b.id;
  const box = el('div','frame');
  const im = document.createElement('img'); im.alt = ''; im.hidden = true;
  const tag = el('span','tag');
  tag.appendChild(el('span','id', b.id));
  /* The one the agent is driving, marked rather than selected: the person's
     eye and the agent's hand are two different things and the tag says both. */
  if(b.id === focusHere){
    const dot = el('span','dot');
    dot.title = 'the agent is working here';
    tag.appendChild(dot);
  }
  const stamp = el('span','stamp'); stamp.hidden = true;
  box.append(im, el('div','veil'), tag, stamp);
  cell.appendChild(box);
  /* Three states and not two, and the third is the one that reads as a
     failure: a browser that is RUNNING WITH NO TAB cannot be captured - the
     engine answers "no such tab" - and asking anyway spends a round trip to be
     told so. The tabs are already in the answer this was built from, so the
     question is asked of data rather than of the pipe. */
  const has = (b.urls || []).length > 0;
  if(has) setState(cell, 'waiting', 'waiting for the first frame');
  else { setState(cell, 'nopage', 'no tab open',
                  'ask the agent to open a page here');
         cell.dataset.blank = '1'; }
  cell.onclick = () => watchThis(b.id);
  return cell;
}

function drawStage(){
  const box = $('stage'), show = onStage();
  /* ⛔ THE TEMPLATE FOLLOWS THE CELLS THAT EXIST. Two running browsers in
     a four-up layout used to be laid on a 2x2 whose second row was empty, so
     each of them got half the height for nothing - the layout control is a
     ceiling on how many you watch at once, not a promise that there are that
     many. */
  box.dataset.grid = String(Math.min(grid, Math.max(1, show.length)));
  /* Only when the SET changes, or every poll would throw away the pictures and
     make the whole stage flash once a second for no new fact. */
  const sig = show.map(b => b.id + ((b.urls || []).length ? 'p' : '')
                            + (b.id === focusHere ? 'a' : '')).join(',')
              + '|' + grid + '|' + watched();
  if(box.dataset.sig === sig) return;
  box.dataset.sig = sig;
  dropFrames(box);
  box.textContent = '';
  turnOf = 0;
  /* ⛔ THE QUESTION IS 'IS THERE ANYTHING TO SEE', NOT 'ARE THERE
     BROWSERS'. With a browser running and no tab open, the bar stayed fully
     armed - address, Live/Frozen, layout picker and the word IDLE - over a
     stage whose own words were `no tab open`. A screen with nothing on it is
     the same empty room to the person looking at it. */
  const anything = show.some(b => (b.urls || []).length);
  right.dataset.empty = anything ? '' : '1';
  /* Not decoration: `inert` removes them from the tab order and from the
     accessibility tree, which is what 'this control cannot do anything right
     now' has to mean for somebody who is not using a mouse. */
  for(const box of [$('mode'), $('grid')]) box.inert = !anything;
  if(!show.length){
    /* An empty state that only reports the emptiness leaves the person to
       guess where the button is. There is no button - browsers are opened by
       asking - so this is the one place that has to say so, and to show the
       shape of the sentence that does it. */
    const cell = el('div','empty');
    cell.append(el('b', null, 'No browser open'),
                el('span', null, 'Ask in the chat and one opens here. There is no button for it, on purpose.'),
                el('code', null, 'open a browser and go to example.com'));
    box.appendChild(cell);
    return;
  }
  for(const b of show) box.appendChild(screenFor(b, b.id === watched()));
}

const GRIDKEY = 'aihawk.grid';
function setGrid(n){
  grid = n;
  for(const b of $('grid').children)
    b.setAttribute('aria-pressed', String(Number(b.dataset.n) === n));
  try { localStorage.setItem(GRIDKEY, String(n)); } catch(err){}
  drawStage(); drawStrip(); paintWhere();
}
$('grid').onclick = (e) => {
  const b = e.target.closest('button');
  if(b) setGrid(Number(b.dataset.n));
};

async function drawFleet(){
  let got = {browsers: []};
  try { const r = await door('/live/browsers', {cache:'no-store'});
        if(r.ok) got = await r.json(); }
  catch(err){ return; }
  fleet = got.browsers || [];
  focusHere = got.focus || '';
  drawStage();
  drawStrip();
}

/* ⛔ SEPARATE FROM THE POLL, because changing the layout changes what the strip
   holds and there is nothing to ask the server about it. While this lived
   inside `drawFleet` the strip stayed wrong until the next poll landed - up to
   three seconds showing browsers that were already on the stage, or missing the
   ones that had just left it. It reads the fleet that is already here. */
function drawStrip(){
  /* The strip carries what the stage does not, so at four-up with four
     browsers it is empty and at one-up with eight it holds seven. */
  const up = new Set(onStage().map(b => b.id));
  const others = fleet.filter(b => !up.has(b.id));
  const box = $('thumbs');
  /* Only when the SET changes. Redrawing on every poll would throw away the
     preview images and make the row flash once a second for no new fact. */
  const sig = others.map(b => b.id + (b.running ? '1' : '0') + (b.id === focusHere ? 'a' : ''))
                    .join(',') + '|' + watched() + '|' + grid;
  if(box.dataset.sig !== sig){
    box.dataset.sig = sig;
    dropFrames(box);
    box.textContent = '';
    for(const b of others) box.appendChild(thumbFor(b));
    nextPane = 0;
  }
  /* The row of previews disappears with one browser; the button to open
     another does not, or a session could never grow past its first. */
  box.hidden = others.length === 0;
}

async function slowTick(){
  const box = $('thumbs');
  /* Only running browsers are asked for a picture. A declared browser that has
     not started is not a slow pane, it is a browser that does not exist yet,
     and asking would START it - 800 MB and seven seconds to fill a thumbnail
     nobody asked for. Same rule the live pane follows. */
  const shown = [...box.children].filter(t => t.querySelector('img'));
  if(shown.length && looking()){
    const t = shown[nextPane % shown.length];
    nextPane++;
    try {
      const r = await door('/live/frame?b=' + encodeURIComponent(t.dataset.id)
                           + '&t=' + Date.now(), {cache:'no-store'});
      if(r.ok && r.status !== 204){
        const im = t.querySelector('img'), blob = await r.blob(), was = im.src;
        im.src = URL.createObjectURL(blob);
        if(was && was.startsWith('blob:')) URL.revokeObjectURL(was);
      }
    } catch(err){}
  }
  setTimeout(slowTick, SLOW_MS);
}

async function fleetPoll(){ if(looking()) await drawFleet(); setTimeout(fleetPoll, 3000); }

/* Whatever was waiting when the page went away comes back into the composer
   rather than into the queue: the run it was queued behind is over, so the
   honest place for it is where somebody can read it and press send. */
const waiting_text = queuedFromBefore();
if(waiting_text){ i.value = waiting_text; setQueued(null);
                  i.style.height = 'auto';
                  i.style.height = Math.min(i.scrollHeight, 200) + 'px'; }

/* ---- the split between the two panes ----
   ⛔ THE RATIO IS A PROPERTY OF THE TASK, NOT OF THIS FILE. Reading a long
   answer wants one, watching a form get filled wants another, and the ratio
   this page picks is right for neither for very long. The measured default is
   still a default - the conversation stops at its reading measure and the rest
   goes to the picture - and from there it is dragged, with the arrow keys, or
   double-clicked back to the default. Remembered per browser, because somebody
   who has set it once has said what they want.

   Everything here is a FUNCTION called from the boot line below: nothing at
   the top level of this script may depend on the order of the lines. */
const SPLITKEY = 'aihawk.split';

function splitTo(px, remember){
  /* The floor is the narrowest the conversation stays usable at; the ceiling
     leaves the browser pane enough to be a picture rather than a strip. Both
     are recomputed against the window, so a value dragged wide on a big
     monitor does not strand the right pane on a laptop. */
  const min = 420, max = Math.max(min, window.innerWidth - 480);
  const w = Math.round(Math.min(max, Math.max(min, px)));
  $('left').style.width = w + 'px';
  $('split').setAttribute('aria-valuenow', String(w));
  $('split').setAttribute('aria-valuemax', String(max));
  if(remember){ try { localStorage.setItem(SPLITKEY, String(w)); } catch(e) {} }
}

function splitReset(){
  try { localStorage.removeItem(SPLITKEY); } catch(e) {}
  $('left').style.width = '';
  $('split').setAttribute('aria-valuenow',
                          String(Math.round($('left').getBoundingClientRect().width)));
  /* The ceiling too: this is the FIRST-RUN path, so without it a range widget
     was announced with a floor and a value and no top for every new user. */
  $('split').setAttribute('aria-valuemax',
                          String(Math.max(420, window.innerWidth - 480)));
}

function splitter(){
  const bar = $('split');
  let saved = null;
  try { saved = localStorage.getItem(SPLITKEY); } catch(e) {}
  if(saved) splitTo(parseInt(saved, 10), false);
  else splitReset();

  bar.addEventListener('pointerdown', e => {
    bar.setPointerCapture(e.pointerId);
    bar.dataset.drag = '1';
    edge = $('left').getBoundingClientRect().left;
    /* ⛔ FOCUS BY HAND, BECAUSE THE LINE BELOW TAKES IT AWAY. preventDefault on
       pointerdown stops the drag from selecting the text beside it, and it also
       stops the browser from focusing what was pressed - so the separator could
       be dragged and then not moved with the arrow keys, which is the half of
       this control that exists for people who do not drag. Found by clicking
       it: nothing in the suite clicks. */
    bar.focus();
    e.preventDefault();
  });
  /* ⛔ ONE WRITE PER FRAME, AND ONE TO DISK PER DRAG. Every pointermove read
     the pane's box and then wrote a width and a value to localStorage: at a
     120 Hz pointer that is 120 forced layouts and 120 synchronous storage
     writes per second of dragging, for a number nobody reads until the drag
     ends. The left edge does not move while dragging, so it is measured once
     when the drag starts. */
  let edge = 0, pending = 0;
  bar.addEventListener('pointermove', e => {
    if(!bar.dataset.drag) return;
    const x = e.clientX;
    if(pending) return;
    pending = requestAnimationFrame(() => { pending = 0; splitTo(x - edge, false); });
  });
  bar.addEventListener('pointerup', e => {
    delete bar.dataset.drag;
    if(pending){ cancelAnimationFrame(pending); pending = 0; }
    /* Remembered once, at the end: the value it lands on is the choice. */
    splitTo($('left').getBoundingClientRect().width, true);
    bar.releasePointerCapture(e.pointerId);
  });
  bar.addEventListener('dblclick', splitReset);
  bar.addEventListener('keydown', e => {
    const step = e.shiftKey ? 64 : 16;
    const now = $('left').getBoundingClientRect().width;
    if(e.key === 'ArrowLeft'){ splitTo(now - step, true); e.preventDefault(); }
    else if(e.key === 'ArrowRight'){ splitTo(now + step, true); e.preventDefault(); }
    else if(e.key === 'Home' || e.key === 'Escape'){ splitReset(); e.preventDefault(); }
  });
  /* A width saved on a wide monitor is not a width on a laptop: put it back
     through the same clamp whenever the window changes. */
  window.addEventListener('resize', () => {
    if($('left').style.width) splitTo(parseFloat($('left').style.width), false);
  });
}

let sawGrid = null;
try { sawGrid = localStorage.getItem(GRIDKEY); } catch(err){}
setGrid(LAYOUTS.includes(Number(sawGrid)) ? Number(sawGrid) : 1);

paint(); listen(); tick(); where(); fleetPoll(); slowTick(); splitter();
if(!$('rail').hidden) drawChats();
</script>
"""


#: The conversation a page that names none is in. The SAME string the server
#: uses for the session a tool call that names none reaches, and that is the
#: point rather than a coincidence: every client written before this existed
#: keeps landing on one conversation driving one browser, exactly as before.
DEFAULT_CHAT_ID = "default"

#: What a conversation is called before it has been asked anything.
UNNAMED = "New chat"


class ChatService:
    """One conversation, its listeners, and the link it drives."""

    def __init__(self, link: Link, brain: Brain,
                 model_label: str = "no model", *,
                 session_id: str = DEFAULT_CHAT_ID,
                 name: str | None = None) -> None:
        self._link = link
        self._brain = brain
        self._listeners: List[asyncio.Queue] = []
        self.history: List[Dict[str, str]] = []
        self.session_id = session_id
        self.name = name or UNNAMED
        self.model_label = model_label
        self._busy = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None
        #: Which conversation the history belongs to. A reconnecting page says
        #: how far it got with `Last-Event-ID`, and that position only means
        #: something inside one conversation: after a reset, or after the
        #: process restarts, the same number points at a different transcript.
        #: Counted from the clock so a restart cannot collide with the run
        #: before it.
        self._epoch = str(int(time.time() * 1000))

    @property
    def link(self):
        """The connection this conversation drives, addressed to it.

        Exposed because the LIVE routes need it: the picture and the tab strip
        belong to this session's browser, and reaching for the shared connection
        instead would draw whatever the default session happens to be looking
        at. That is a wrong answer that looks exactly like a right one.
        """
        return self._link

    def save(self) -> None:
        """Write this conversation down as it stands.

        Called when the conversation CHANGES - a turn ended, it was renamed, it
        was reset - and not on a timer, for the reason the browsers are saved
        the same way: a file written on a tick is a version of the session that
        existed only between two ticks.

        ⛔ BOTH TRANSCRIPTS, and saving only one would be a promise the other
        half cannot keep. The page draws `history`; the model holds `messages`.
        Reopening with only the first gives somebody a conversation they can
        read and cannot continue, under a follow-up box that still says "and now
        sort them by price" will work.

        A write that fails costs the saved conversation and nothing else: the
        turn is already finished and answered, and losing it to a full disk
        would be a strange way to report a full disk.
        """
        try:
            store.save_chat(self.session_id, self.name, self.history,
                            list(getattr(self._brain, "messages", []) or []),
                            self.usage)
        except Exception:
            pass

    def restore(self) -> bool:
        """Read this conversation back, if one was saved. Answers whether it was.

        The epoch is NOT restored, and that is deliberate: it says which
        transcript a page's positions belong to, and a page reconnecting from
        before the restart holds positions into a transcript this process never
        had. A new epoch makes it replay from the beginning instead of resuming
        into the middle of something else.
        """
        saved = store.load_chat(self.session_id)
        if not saved:
            return False
        self.history = list(saved.get("history") or [])
        self.name = saved.get("name") or self.name
        messages = saved.get("messages") or []
        remember = getattr(self._brain, "remember", None)
        if callable(remember) and messages:
            remember(messages, saved.get("usage") or {})
        return True

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._listeners.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._listeners:
            self._listeners.remove(q)

    async def emit(self, kind: str, text: str) -> None:
        event = {"kind": kind, "text": text}
        # `busy` is STATE, not conversation: replaying it to somebody who
        # opens the page later would show a spinner for work that finished
        # an hour ago.
        if kind != "busy":
            self.history.append(event)
        for q in list(self._listeners):
            q.put_nowait(event)

    def reset(self) -> bool:
        """Start a fresh conversation, keeping the browser where it is.

        ⛔ THIS IS A COST AND LATENCY CONTROL, not a tidiness feature, and
        until it existed there was no way to reach it short of killing the
        process. Every turn resends the whole transcript, so the transcript is
        the bill and it is also the wait: measured on this interface, a first
        instruction on a fresh process carries 3,106 prompt tokens and the
        agent moves 4.1 s after the click; by the third instruction of the same
        session the first turn already carries 38,207 and the wait is 6.7 s.
        Nothing trimmed it, so it only grew.

        The browser is deliberately left alone. Someone who has logged in
        somewhere and wants to drop the transcript should not lose the session
        they built, and the two have no reason to be tied.

        Refused while a run is in flight rather than cancelling it: throwing
        away a transcript that something is still writing into is the kind of
        surprise a person cannot undo.
        """
        if self.busy:
            return False
        forget = getattr(self._brain, "forget", None)
        if callable(forget):
            forget()
        self.history.clear()
        self._epoch = str(int(time.time() * 1000))
        return True

    @property
    def epoch(self) -> str:
        """Which transcript the history positions belong to."""
        return self._epoch

    @property
    def usage(self) -> dict:
        """What this conversation has cost, for the file it is saved into.

        Read through the brain rather than kept here: the brain owns the
        transcript, so it owns what the transcript has cost. It is no longer
        sent anywhere - the meter that drew it is gone - but it is still counted
        and still saved, so putting a number back on the screen is a question of
        where to draw it and not of measuring it again.
        """
        got = getattr(self._brain, "usage", None)
        return dict(got) if isinstance(got, dict) else {}

    @property
    def busy(self) -> bool:
        """Whether an instruction is in flight, for a listener joining now.

        The lock and not the task handle: the lock is held for exactly as long
        as `send` runs, which is the span the page draws as busy, while the
        handle survives its own task and would answer for a run that ended.
        """
        return self._busy.locked()

    def start(self, text: str) -> None:
        """Run an instruction detached, keeping the handle so it can be stopped.

        The task is held for exactly that reason. Firing and forgetting is one
        line shorter and makes the stop button a decoration.
        """
        self._task = asyncio.create_task(self.send(text))

    def stop(self) -> bool:
        t = self._task
        if t is not None and not t.done():
            t.cancel()
            return True
        return False

    async def send(self, text: str) -> None:
        async with self._busy:
            # Emitted here and not added by the page, so the instruction is part
            # of the transcript: somebody opening the page mid-run sees what was
            # asked, and a reload does not lose it. The page adding it locally is
            # one line shorter and leaves a conversation with no questions in it.
            if self.name == UNNAMED:
                # Named from what it was first asked, because a column of eight
                # rows that all say "New chat" is a column nobody can use, and
                # asking somebody to name a conversation before having it is
                # asking them to describe work they have not done yet.
                flat = " ".join(text.split())
                self.name = flat[:48] + ("..." if len(flat) > 48 else "")
            await self.emit("you", text)
            await self.emit("busy", "1")
            try:
                await self._brain.handle(text, self._link, self.emit)
            except asyncio.CancelledError:
                # The cancellation lands at the next await, and since the model
                # request runs in a thread that is either the request itself or
                # the tool call after it - so stop is prompt rather than "after
                # the step in flight", which is what this comment used to say
                # and what the loop used to do.
                #
                # Prompt is not free: a model request already sent finishes in
                # its thread and its answer is discarded, so a run stopped
                # mid-turn is still billed for that reply. Stopping cuts what
                # comes next, never what is already in the air.
                await self.emit("err", "stopped")
                raise
            except Exception as exc:
                await self.emit("err", f"{type(exc).__name__}: {exc}")
            finally:
                await self.emit("busy", "0")
                # After the turn and not during it: a transcript written
                # mid-run is a version of the conversation that existed for a
                # moment, and this is the moment it is worth keeping. Stopped
                # and failed runs are saved too - what was asked and how far it
                # got is exactly what somebody reopens the session to see.
                self.save()


class SessionGone(Exception):
    """A request named a conversation that does not exist.

    Its own class rather than an HTTPException so the one handler that answers
    it lives beside the routes instead of inside each of them: eight routes
    resolve a session and every one of them would otherwise carry the same
    three lines, which is how a rule stops being enforced one route later.
    """

    def __init__(self, session_id: str) -> None:
        super().__init__(session_id)
        self.session_id = session_id


class Sessions:
    """Every conversation this interface holds, by id, saved as it goes.

    ⛔ A CONVERSATION AND ITS BROWSERS ARE ONE SESSION, and this class is where
    that is true rather than nearly true. The id it keys on is the SAME id the
    server keys browsers on, so the chat called `lavoro` drives the browsers of
    session `lavoro` and nothing else - which is why `forget` below closes them
    as well. Two ids would have been easier and would have meant that deleting a
    conversation left up to eight engines running with nothing naming them.

    The MCP connection underneath is shared on purpose: one server, one process,
    one place the browsers live. What keeps two conversations from driving each
    other's browser is `SessionLink`, which puts the id on every call.

    Conversations are built on demand and read from disk the first time they are
    asked for. They are not all loaded at startup: a transcript is thousands of
    lines and somebody with twenty sessions wants a column of names, not twenty
    transcripts in memory to draw it.
    """

    def __init__(self, link: Link, make_brain, model_label: str = "no model") -> None:
        self._link = link
        self._make_brain = make_brain
        self.model_label = model_label
        self._live: Dict[str, ChatService] = {}

    @classmethod
    def around(cls, service: "ChatService") -> "Sessions":
        """A registry holding one conversation somebody else built.

        For callers that make the conversation themselves - the tests do, and so
        would anything embedding this - so that having one conversation does not
        require a second code path through the routes. One path means the single
        case is exercised by the same code the many-session case uses.
        """
        got = cls(service._link, lambda: service._brain, service.model_label)
        got._live[service.session_id] = service
        return got

    def get(self, session_id: str | None = None) -> ChatService:
        """The conversation with this id, loaded from disk the first time."""
        at = session_id or DEFAULT_CHAT_ID
        found = self._live.get(at)
        if found is not None:
            return found
        service = ChatService(SessionLink(self._link, at), self._make_brain(),
                              model_label=self.model_label, session_id=at)
        service.restore()
        self._live[at] = service
        return service

    def new(self) -> ChatService:
        """A conversation nobody has used yet, with an id of its own.

        The id is the clock, not a counter: a counter has to be stored somewhere
        to survive a restart, and the place it would be stored is the thing that
        breaks. It is never shown - the name is - so it only has to be unique.
        """
        at = "s%d" % int(time.time() * 1000)
        while at in self._live or store.load_chat(at) is not None:
            at += "x"
        return self.get(at)

    def listing(self) -> List[dict]:
        """Every conversation, saved or only live, newest first.

        A conversation opened a moment ago has nothing on disk yet, and leaving
        it out would make the column disagree with the page it is drawn beside.
        """
        rows = {r["id"]: dict(r) for r in store.known_chats()}
        for at, service in self._live.items():
            row = rows.setdefault(at, {"id": at, "saved": "", "turns": 0})
            row["name"] = service.name
            row["turns"] = sum(1 for e in service.history if e.get("kind") == "you")
            row["live"] = True
        out = list(rows.values())
        out.sort(key=lambda r: (r.get("saved") or "", r["id"]), reverse=True)
        return out

    def knows(self, session_id: str | None) -> bool:
        """Whether this conversation exists, WITHOUT bringing it into being.

        ⛔ THE QUESTION EVERY REQUEST HAS TO ASK BEFORE `get`. Building what it
        does not find is right for a caller that MEANS to start a conversation -
        `new`, an embedder, a test - and wrong for a request that only means to
        look at one. Measured: a page left open on a session somebody deleted
        went on asking `/live/browsers` every three seconds, and one of those
        questions was enough to declare the session again. The delete worked,
        answered `forgotten:true`, closed the browsers, erased the file - and the
        row came back on its own, empty and unnamed, for as long as that tab
        stayed open. Every visible signal said the delete had failed.

        ⛔ AND IT ASKS ABOUT BOTH HALVES OF A SESSION, because a session is a
        conversation AND its browsers and either half can be the only one on
        disk. An agent client that opens a browser in session `work` and never
        touches this interface writes the browsers and no transcript; opening
        `?s=work` here has to work, and asking only about transcripts would have
        refused it. That is the same defect this method exists to fix, made one
        step further along - which is why it is written into the one question
        rather than into the routes that ask it.

        Each half is asked of whoever owns it: what is in memory of this
        registry, what is on disk of the store. The default is always known
        because it is the conversation a page with no id gets, and on a fresh
        install nothing has written it down yet.
        """
        at = session_id or DEFAULT_CHAT_ID
        return (at == DEFAULT_CHAT_ID or at in self._live
                or store.load_chat(at) is not None
                or store.load(at) is not None)

    def rename(self, session_id: str, name: str) -> bool:
        clean = " ".join((name or "").split())[:80]
        if not clean:
            return False
        service = self.get(session_id)
        service.name = clean
        service.save()
        return True

    async def forget(self, session_id: str) -> bool:
        """Delete a conversation AND the browsers that belonged to it.

        ⛔ Both halves, because they are one session. Erasing only the chat file
        would leave up to eight engines running with nothing left that names
        them - 6.5 GB, measured, unreachable and unkillable short of the task
        manager. `session_forget` on the server is the tool that does the other
        half, and it exists for exactly this.

        Refused while that conversation is mid-run: the same reason `reset` is.

        ⛔ AND `False` MEANS THAT AND NOTHING ELSE. It used to mean "there was
        nothing to erase" as well, and the two are opposite news: the page reads
        it and says "that session is still working, so it was not deleted", which
        for a session somebody else had already deleted is the wrong sentence in
        both halves. The caller asked for it to be gone; if it is gone, the
        answer is yes.
        """
        service = self._live.get(session_id)
        if service is not None and service.busy:
            return False
        try:
            await self._link.call("session_forget", {"session_id": session_id})
        except Exception:
            # The browsers could not be closed - the server is gone, or it
            # refused. The conversation is still deleted: leaving it listed
            # because something else failed would tell somebody the delete did
            # not work, when the half they were looking at did.
            pass
        self._live.pop(session_id, None)
        store.erase_chat(session_id)
        return True


def build_app(link: Link, sessions: "Sessions") -> Starlette:
    def named(session_id: str | None) -> ChatService:
        """The conversation with this id, refusing one nobody declared.

        ⛔ ONE PLACE TURNS AN ID OFF THE WIRE INTO A CONVERSATION, because the
        id does not always arrive the same way: eight routes carry it in the
        query string and the rename carries it in the body. Written twice, the
        rename is where it would have gone on resurrecting deleted sessions
        after the eight beside it had stopped.
        """
        if not sessions.knows(session_id):
            raise SessionGone(session_id or "")
        return sessions.get(session_id)

    def which(request: Request) -> ChatService:
        """The conversation this request is about.

        ⛔ EVERY ROUTE GOES THROUGH HERE, the live ones included. A route that
        read the session id and a route that did not would act on two different
        conversations while the page showed one, and the way that fails is the
        picture on the right belonging to somebody else's browser. A caller that
        names nothing gets the default conversation, which is what every page
        written before this existed does.

        ⛔ AND IT REFUSES AN ID NOBODY DECLARED, instead of declaring it. A
        request is a way to look at a conversation, never a way to start one -
        `/sessions/new` is. See `Sessions.knows` for what a page left open on a
        deleted session did to it.
        """
        return named(request.query_params.get("s"))

    async def root(_request: Request) -> HTMLResponse:
        return HTMLResponse(PAGE)

    async def listing(_request: Request) -> JSONResponse:
        return JSONResponse({"sessions": sessions.listing(),
                             "default": DEFAULT_CHAT_ID})

    async def new_session(_request: Request) -> JSONResponse:
        service = sessions.new()
        return JSONResponse({"id": service.session_id, "name": service.name})

    async def rename_session(request: Request) -> JSONResponse:
        body = await request.json()
        at = (body or {}).get("id") or DEFAULT_CHAT_ID
        service = named(at)
        done = sessions.rename(at, (body or {}).get("name", ""))
        return JSONResponse({"renamed": done, "name": service.name})

    async def forget_session(request: Request) -> JSONResponse:
        body = await request.json()
        at = (body or {}).get("id")
        if not at:
            return JSONResponse({"error": "no id"}, status_code=400)
        return JSONResponse({"forgotten": await sessions.forget(at)})

    async def send(request: Request) -> JSONResponse:
        body = await request.json()
        text = (body or {}).get("text", "")
        if not text:
            return JSONResponse({"error": "empty"}, status_code=400)
        which(request).start(text)
        return JSONResponse({"accepted": True})

    async def stop(request: Request) -> JSONResponse:
        return JSONResponse({"stopped": which(request).stop()})

    async def fresh(request: Request) -> JSONResponse:
        service = which(request)
        done = service.reset()
        if done:
            # Told to every listener, not just the tab that asked: two tabs on
            # one session must not disagree about what the conversation is.
            await service.emit("fresh", "1")
            service.save()
        return JSONResponse({"fresh": done})

    async def events(request: Request) -> StreamingResponse:
        service = which(request)
        q = service.subscribe()
        # Freeze the replay/live boundary while subscribing. StreamingResponse
        # starts `stream` later, so taking this snapshot inside it would let an
        # intervening event appear in both history and the listener's queue.
        history = list(service.history)
        # Taken with the snapshot, for the same reason: whether a run is in
        # flight is part of the state this listener is joining.
        joining_a_run = service.busy

        # ⛔ WHERE THIS LISTENER GOT TO, AND WHETHER IT IS EVEN THE SAME
        # CONVERSATION. `EventSource` reconnects by itself after any drop, and
        # until this was read the server answered every reconnection with the
        # whole transcript again, while the page - which has no de-duplication
        # and had never been given an id to resume from - appended a second
        # copy of everything. Measured: three consecutive subscriptions each
        # received all 21 events of the same conversation.
        #
        # The epoch is the other half. A position only means something inside
        # one transcript: after a reset, or after the process restarts, the
        # same number points at something else entirely, so a mismatch replays
        # from the beginning - and says `fresh` first, so a page holding the
        # previous conversation drops it instead of growing a chimera.
        resume_from, same_conversation = 0, False
        marker = request.headers.get("last-event-id") or ""
        if ":" in marker:
            epoch, _, index = marker.partition(":")
            if epoch == service.epoch and index.isdigit():
                resume_from = int(index) + 1
                same_conversation = True
        replay = history[resume_from:] if same_conversation else history

        async def stream() -> AsyncIterator[bytes]:
            try:
                yield b"data: " + json.dumps(
                    {"kind": "model", "text": service.model_label}).encode() + b"\n\n"
                if not same_conversation and marker:
                    # It reconnected carrying a position from another
                    # transcript, so what it is still showing is not this one.
                    yield b"data: " + json.dumps(
                        {"kind": "fresh", "text": "1"}).encode() + b"\n\n"
                # Flagged as replay so the page does not animate forty rows at
                # once and does not start a stopwatch on work that finished
                # before this listener existed. Numbered so the next
                # reconnection can say where it got to instead of starting over.
                for offset, past in enumerate(replay):
                    yield (b"id: " + ("%s:%d" % (service.epoch, resume_from + offset)).encode()
                           + b"\ndata: " + json.dumps({**past, "replay": True}).encode()
                           + b"\n\n")
                # And then the CURRENT state, which the replay above cannot
                # carry: `emit` keeps `busy` out of the history on purpose, so a
                # page opened long after a run would not show a spinner for work
                # that ended an hour ago. That is right for a finished run and
                # wrong for one still going - the page would show a transcript
                # growing under a composer that says nothing is happening, and
                # with no turn ceiling the stop button is the only thing that
                # ends such a run. So it is sent as what it is, the present, and
                # only when true: a page starts out believing it is idle.
                # ⛔ AND IT IS SENT WHEN FALSE TOO, WHICH IS NOT SYMMETRY FOR
                # ITS OWN SAKE: without it the last thing the model said was
                # never drawn. The page holds one narration line back so that a
                # sentence with tool calls after it reads as their lead-in and
                # one with nothing after it reads as the answer, and the event
                # that resolves that lookahead is the end of the turn - which
                # is a `busy` going false. A replay carries no `busy` at all, so
                # a page reopening a FINISHED conversation sat holding its last
                # sentence forever. Measured on the developer's own saved
                # session: 257 events ending in `said`, and the answer to the
                # last thing they asked was not on the screen.
                # Marked as replay so it flushes without animating one row and
                # without redrawing the session list, exactly like the events
                # above it.
                # The two are NOT one line with a conditional inside: the live
                # one must arrive unflagged or the page calls `waited()` where
                # it should call `waiting()`, and a run in progress would lose
                # its clock.
                if joining_a_run:
                    yield b"data: " + json.dumps(
                        {"kind": "busy", "text": "1"}).encode() + b"\n\n"
                else:
                    yield b"data: " + json.dumps(
                        {"kind": "busy", "text": "0", "replay": True}).encode() + b"\n\n"
                while True:
                    event = await q.get()
                    # Only what the history keeps is numbered: an id moves the
                    # resume point, and `busy` is not a place to resume from.
                    # Leaving the field out keeps the last one,
                    # which is what the spec says and what is wanted here.
                    if event["kind"] in ("busy", "fresh"):
                        yield b"data: " + json.dumps(event).encode() + b"\n\n"
                    else:
                        yield (b"id: " + ("%s:%d" % (service.epoch,
                                                     len(service.history) - 1)).encode()
                               + b"\ndata: " + json.dumps(event).encode() + b"\n\n")
            finally:
                service.unsubscribe(q)

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store"})

    async def frame(request: Request) -> Response:
        """The window the active tab lives in, as `browser_watch` captures it.

        Not `browser_take_screenshot`: that is the page alone, and the engine
        draws the pointer outside the page on purpose, so no screenshot can
        show it. The window capture shows the pointer, the tab strip and the
        address bar, keeps answering while a page loads, and costs one frame
        the server already holds rather than a paint. The tool exists from
        0.15.0 of the server, which is the floor pyproject declares.

        The strip and the address in the picture are pixels; the ones the
        page draws above it are the same facts as elements, and those can be
        clicked and copied. Both stay.
        """
        seen = which(request)
        if not seen.link.touched:
            # 204, not an error: nothing is wrong, there is simply nothing to
            # look at. Asking the server would START a browser, which is exactly
            # what a view is not allowed to cause - and it is asked of THIS
            # conversation, so opening a second chat does not launch an engine
            # to draw a pane for a session that has done nothing.
            return Response(status_code=204)
        # ⛔ THE PANE SAYS WHICH BROWSER, and without that the workspace is one
        # picture drawn eight times. `browser_id` is the caller's to choose here
        # exactly as `session_id` is not: which SESSION a request belongs to is
        # decided by the page's own url and imposed, while which BROWSER inside
        # it a pane is watching is what the pane is for.
        watching = request.query_params.get("b") or None
        try:
            result = await seen.link.call("browser_watch",
                                          {"browser_id": watching} if watching else {})
        except Exception as exc:
            return JSONResponse({"error": str(exc)[:200]}, status_code=503)
        got = image_of(result)
        if got is None:
            # A tool that raised reaches a client as an error RESULT with the
            # reason as text, not as an exception: an engine without the
            # screencast, or a window captured as nothing. That is a 503 with
            # the reason, never a 204, which would read as "nothing to look at"
            # in the one case where a person needs to read a sentence.
            reason = text_of(result) if getattr(result, "isError", False) else ""
            if reason:
                return JSONResponse({"error": reason[:200]}, status_code=503)
            return Response(status_code=204)
        jpeg, mime = got
        return Response(jpeg, media_type=mime, headers={"Cache-Control": "no-store"})

    async def browsers(request: Request) -> JSONResponse:
        """The panes to draw: which browsers this session holds, and where.

        Asked of the server through the same tool an agent would call, because
        the interface has no privileged path to the browsers - and it starts
        nothing, so drawing the workspace can never cost an engine.

        ⛔ AND IT ASKS EVEN WHEN THIS CONVERSATION HAS DONE NOTHING, which is
        the opposite of what the picture and the tab strip do. Those may not ask
        before an instruction because asking STARTS a browser; `browser_list` is
        the one question that starts nothing, by construction and by its own
        test. Copying the guard here looked prudent and was a bug: a session
        reopened after a restart has browsers it declared and no instruction
        yet, so the workspace would have been empty in exactly the case the
        declarations exist for - and the panes offering to wake them would
        never have been drawn.
        """
        seen = which(request)
        try:
            got = json.loads(await seen.link.call_text("browser_list"))
        except Exception:
            # An older server answered this in prose. The workspace then draws
            # nothing rather than half of something, and the single live pane -
            # which does not need this - keeps working.
            return JSONResponse({"browsers": [], "focus": "", "limit": 0})
        if not isinstance(got, dict):
            return JSONResponse({"browsers": [], "focus": "", "limit": 0})
        return JSONResponse({"browsers": got.get("browsers") or [],
                             "focus": got.get("focus") or "",
                             "limit": got.get("limit") or 0})

    async def tabs(request: Request) -> JSONResponse:
        """Every tab, and which one is current.

        ONE call where there were two. It asks `session_list_pages`, which since
        0.9.0 of the server answers with id, title, url and active - the four
        fields its description had always promised and had never returned. While
        it returned ids only this had to ask `browser_evaluate` for
        `location.href` instead, which is script in the page to learn something
        the server already knew.

        A stale or older server is not an error here: anything that does not
        parse into those fields leaves the strip empty and the address blank,
        and the pane keeps working as a picture.
        """
        seen = which(request)
        if not seen.link.touched:
            return JSONResponse({"url": "", "tabs": []})
        # ⛔ WHICH BROWSER, like the frame route beside it. The address above the
        # stage has to be the address of the screen being looked at, and with
        # more than one screen the answer stopped being "the focused one" the
        # moment clicking a screen became a way to look somewhere else.
        watching = request.query_params.get("b") or None
        try:
            raw = await seen.link.call_text(
                "session_list_pages",
                {"browser_id": watching} if watching else None)
            rows = json.loads(raw)
        except Exception:
            return JSONResponse({"url": "", "tabs": []})
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            return JSONResponse({"url": "", "tabs": []})
        here = next((r for r in rows if r.get("active")), rows[0] if rows else {})
        return JSONResponse({"url": here.get("url") or "", "tabs": rows})

    async def select(request: Request) -> JSONResponse:
        body = await request.json()
        page_id = (body or {}).get("id", "")
        if not page_id:
            return JSONResponse({"error": "no id"}, status_code=400)
        await which(request).link.call("session_select_page", {"page_id": page_id})
        return JSONResponse({"ok": True})

    async def vanished(_request: Request, exc: Exception) -> JSONResponse:
        """410, because the conversation existed and does not any more.

        Not 404: the page asking is a page that HAD this conversation open, and
        the difference between "there is no such thing" and "this is over" is
        the difference between a page that says something wrong happened and a
        page that says what happened. It is also the only status the page reads
        as a reason to stop asking - anything else is a failure worth retrying.
        """
        return JSONResponse({"error": "this conversation was deleted",
                             "id": getattr(exc, "session_id", "")},
                            status_code=410)

    return Starlette(exception_handlers={SessionGone: vanished}, routes=[
        Route("/", root),
        Route("/sessions", listing),
        Route("/sessions/new", new_session, methods=["POST"]),
        Route("/sessions/rename", rename_session, methods=["POST"]),
        Route("/sessions/forget", forget_session, methods=["POST"]),
        Route("/chat/send", send, methods=["POST"]),
        Route("/chat/stop", stop, methods=["POST"]),
        Route("/chat/fresh", fresh, methods=["POST"]),
        Route("/chat/events", events),
        Route("/live/frame", frame),
        Route("/live/browsers", browsers),
        Route("/live/tabs", tabs),
        Route("/live/select", select, methods=["POST"]),
    ])
