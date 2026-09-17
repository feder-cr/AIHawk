---
title: "Native selects and the ones that only look like selects"
description: "One is a single call that takes 0.06 seconds. The other is a button, a list and two clicks. The tool refuses the second by name, which is the most useful thing about it."
parent: "Using the Agent"
nav_order: 69
---

# Native selects and the ones that only look like selects

Two controls on a page can look identical and be completely different things. A
real `<select>` is one element the browser draws; a "custom select" is a button
that shows a list of divs. An agent has to treat them differently, and the useful
news is that it finds out immediately rather than silently doing the wrong thing.

Measured on 2026-09-17, both on one page served from `127.0.0.1`:

| | what happened |
|---|---|
| `browser_select_option` on a real `<select>` | **0.06 s**, the page's change handler fired, the value was `b` |
| `browser_select_option` on a div that looks like one | **refused**: `Page.select_option: Element is not a <select> element` |
| `browser_click` on the button, then on the option | worked, the page recorded the choice |

## Why the refusal is the good outcome

An agent handed a custom dropdown and a select-shaped tool has a few ways to go
wrong, and most of them are quiet. It could click the button and report success
without the value having changed. It could set an attribute from script, which
produces a change no handler hears about. It could pick whatever option is
nearest.

Instead it gets back a sentence naming the actual problem: **the element is not a
`<select>`**. That is immediately actionable, both for a person reading the
transcript and for a model deciding what to do next, and it costs the eighth of a
second the failed call took.

This is the same design as the refusal on scripted interaction, where the message
names the tool to use instead rather than just declining. That one is quoted in
full in
[keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md).

## Telling them apart before you try

The snapshot reports the tag, so a real select is identifiable without guessing:
an entry whose `tag` is `select` takes the single call. Anything that behaves like
a dropdown and reports as a `button`, a `div` or a `span` needs the two-click
route.

That is worth putting in the task when you know the page, because it saves the
agent a failed call and a decision. When you do not know the page, letting it
try the cheap call first and read the refusal is a perfectly good strategy, which
is not always true of failed calls.

## Writing the two-click route

Three details separate a version that works from one that half works.

**Open, then choose, then confirm.** Click the control, read the page to see the
options that appeared, click the one you want. Reading in the middle matters:
the options often do not exist in the document until the control is opened, so a
selector planned in advance may not resolve yet.

**Some of them need the keyboard, not the mouse.** Comboboxes built on a text
input filter as you type and commit on Enter or on a click. There, typing the
first characters and then clicking the filtered option is more reliable than
scrolling a long list.

**Verify the value, do not assume the click.** Custom dropdowns frequently close
on any click, including one that missed. The check is whatever the page shows
afterwards: the button's label, a summary line, a hidden field. Without it a
missed option looks exactly like a chosen one.

That last point is the local form of a general rule about reading the field back
after filling it, which is in
[one form submission per spreadsheet row](one-form-per-spreadsheet-row.md).

## The third kind, which is neither

Worth naming because it defeats both routes: a dropdown rendered inside a shadow
root or an iframe. The click by selector still works into a shadow root, measured
on
[its own page](shadow-dom-and-an-ai-agent.md); inside a frame it does not, and
you are on coordinates, per
[an agent and an iframe](an-agent-and-an-iframe.md).

If a dropdown refuses both the select call and the two-click route while being
plainly visible, that is the thing to check, rather than the selector.

## Why native is worth asking for, when you have the choice

If you are on the side of the page rather than the agent: a real `<select>` costs
one call and sixty milliseconds, and works from the keyboard, with a screen
reader, and on a phone, without anybody writing that behaviour. The custom one
costs two calls, a read in between, and a verification step, and it breaks in the
three ways above.

That is not an argument an agent can make on your behalf, but it is the honest
summary of what the measurement shows.

## Short answers to the questions that lead here

**How does an AI agent choose from a dropdown?** One call on a real `<select>`,
measured at 0.06 seconds. On a custom one: click to open, read the options, click
the one you want, verify.

**Why did select_option fail?** Because the element is not a `<select>`. The tool
says so by name rather than failing vaguely, which tells you to switch to the
two-click route.

**How do I tell which kind it is?** The snapshot reports the tag. `select` takes
the single call; `button`, `div` or `span` means the custom route.

**The option I clicked did not take.** Custom dropdowns close on any click,
including a miss. Read the control's label or the page's summary afterwards
instead of trusting the click.

**What about a combobox I can type into?** Type a few characters to filter, then
click the option. Scrolling a long unfiltered list is the fragile version.

**See also:**
[getting an AI agent to fill out forms](ai-agent-fill-out-forms.md) for the other
control types and the validation behaviour around them, and
[what a page snapshot costs, per control](what-a-page-snapshot-costs.md), since
the tag that distinguishes these two comes from the snapshot.

## Sources

- Measured 2026-09-17 through this project's MCP server over stdio, on one page carrying a real `<select>` and a button-plus-list pretending to be one, served from `127.0.0.1`. `browser_select_option` on the real one completed in 0.06 s and the page's change handler recorded the value; on the div it returned `Page.select_option: Element is not a <select> element`, quoted verbatim. Two clicks on the custom control set it, confirmed by the page's own output element.

---

*The refusal is the part worth remembering. A tool that declines by name is worth
more than one that tries its best on the wrong kind of element.*
