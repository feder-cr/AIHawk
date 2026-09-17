---
title: "Shadow DOM and an AI agent: you can click it, you cannot read it"
description: "Measured on a closed shadow root: the click lands and the handler fires, while all three reads and standard JavaScript show nothing. The asymmetry decides how you write the task."
parent: "Using the Agent"
nav_order: 67
---

# Shadow DOM and an AI agent: you can click it, you cannot read it

Web components hide their internals in a shadow root. An open one is reachable
from script through `shadowRoot`; a closed one is, by specification, not
reachable at all, and Playwright's own documentation says closed-mode shadow
roots are not supported.

Measured here on 2026-09-17, one page with both kinds, served from
`127.0.0.1`:

| | open shadow root | closed shadow root |
|---|---|---|
| `browser_read_text` | not present | not present |
| `browser_read_html` | not present | not present |
| `browser_snapshot` | not listed | not listed |
| `browser_evaluate` via `shadowRoot` | **returns the text** | `null` |
| **`browser_click` by selector** | **`clicked #ob`** | **`clicked #cb`** |

The last row is the finding, and it is not what the rest of the table would lead
you to expect. Both clicks landed, and the page's own log element confirmed it:
`open clicked`, then `closed clicked`. **The button inside a closed shadow root
was clicked by selector, on a boundary the specification says script cannot
cross.**

## So the shape is: act yes, read no

Three of the four reads see neither kind. Standard JavaScript sees the open one
and is refused the closed one, exactly as the specification requires. But the
engine's own element resolution reaches both, because it is not doing it from
page script.

That asymmetry is the whole practical content of this page:

- **You can drive a component whose internals you cannot inspect.** If you know
  the selector, the click, the typing and the key press all work.
- **You cannot verify the result from the page text**, because the state that
  changed is inside the same boundary you cannot read.

Verification therefore has to come from somewhere the shadow root is not: a
change in the light DOM, a URL change, a network effect, a value the component
surfaces deliberately. In the measurement above it was a `<div>` outside the
component, which the component's own handler wrote into.

## How to write a task against a component you cannot read

**Find the selector once, by hand.** Open the page in a browser, inspect the
component, and put the selector in the task. The agent cannot discover it,
because the snapshot does not list what is inside the root.

**Name what should change afterwards, in the light DOM.** "Click the confirm
control in the date picker, then check that the summary line shows a date." The
second half is the part that makes the run checkable.

**Do not ask the agent to explore inside the component.** It will read the page,
find nothing resembling what you described, and either give up or start clicking
things that are visible. This is a common route to
[clicking the wrong thing](why-did-the-agent-click-the-wrong-thing.md).

## When the selector does not exist either

Some components expose nothing usable from outside: no stable id, no part
attribute, no accessible name in the light DOM. Then the selector rung is gone
too, and what is left is the pointer.

A screenshot, find the control in the picture, click where it is. The same route
the frame case needs, for a different reason: there the document boundary blocks
the selector, here the component's own encapsulation does.
[Clicking by selector or by coordinates](clicking-by-selector-or-by-coordinates.md)
has the trade, and
[what an AI agent can and cannot do inside an iframe](an-agent-and-an-iframe.md)
is the neighbouring case where the selector fails and the pointer works.

## Why this is worth knowing about the engine

Most tooling treats a closed shadow root as a hard stop, and says so. This one
does not, and the measurement above is what that difference looks like in
practice rather than as a claim.

Be precise about what it buys, though, because overstating it would be the sort
of thing this wiki avoids. It buys **reach**, not **visibility**. A component you
can operate and cannot inspect is still a component you cannot inspect, and a
task that assumes otherwise fails in a way that is hard to read.

## The failure to recognise

An agent told to work with a component inside a shadow root, without a selector,
produces a very characteristic run: it reads the page, reports that the control
is not there, reads again, maybe screenshots, and concludes the page has not
loaded.

It has loaded. The control is there and is on screen. Nothing the agent can read
contains it. If the run says "the element does not appear to exist" about
something you can see with your own eyes, the two candidates are a frame and a
shadow root, and both have their page here.

## Short answers to the questions that lead here

**Can an AI agent interact with shadow DOM?** Yes, including closed roots:
measured, a click by selector into a closed shadow root landed and the
component's handler fired.

**Can it read inside a shadow root?** Not through the page reads or the snapshot,
for either kind. Standard JavaScript can read an open one and gets `null` for a
closed one.

**How do I verify the click worked?** By something outside the shadow boundary: a
change in the visible page, a URL, a summary line. Name it in the task.

**Why can't the agent find the element?** Because the snapshot lists what it can
enumerate in the document, and shadow contents are not in it. Supply the selector
yourself.

**What if there is no usable selector?** Screenshot and click by position. That
is the third rung and it exists for exactly this.

**See also:**
[what a page snapshot costs, per control](what-a-page-snapshot-costs.md), for what
the snapshot does contain and what it costs, and
[keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md),
because a control you cannot inspect is one you should be more careful about
clicking, not less.

## Sources

- Measured 2026-09-17 through this project's MCP server over stdio, on a page carrying one open and one closed shadow root, each containing a paragraph and a button, served from `127.0.0.1`. `browser_click` returned `clicked #ob` and `clicked #cb`; a light-DOM log element read back `open clicked` and then `closed clicked`. `browser_evaluate` on the open host's `shadowRoot.textContent` returned the component's text; on the closed host `shadowRoot` was `null`.
- [Playwright's own documentation](https://playwright.dev/docs/locators) states that closed-mode shadow roots are not supported, which is the baseline the measurement above is interesting against.

---

*One table, one surprising row. The rest of the page is what to do about the fact
that you can operate something you cannot see.*
