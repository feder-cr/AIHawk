---
title: "Using the keyboard instead of the mouse"
description: "A key press is 0.14 seconds against about a second for a click, and on some controls it is the only thing that works. Where the keyboard wins, and the one place it quietly does not."
parent: "Using the Agent"
nav_order: 77
---

# Using the keyboard instead of the mouse

Agents reach for clicks. A lot of what a click is used for is done better from
the keyboard, and one measured number makes the case on its own: `browser_press_key`
took **0.14 seconds** on 2026-09-17, against **0.23 s** for a click by selector
and **0.59 s** for one by coordinates.

Small differences, until they are in a loop.

## Where the keyboard is simply better

**Submitting a form.** Enter in a text field submits, and it does it the way the
page expects, without needing to find a button that might be a `<button>`, an
`<input type=submit>`, a div, or in a sticky footer that is covering something
else.

**Moving between fields.** Tab follows the page's own focus order, which is
defined by the document rather than by where things happen to be drawn. On a form
whose visual order and DOM order disagree, tabbing is more predictable than
clicking.

**Dismissing things.** Escape closes most modals, dropdowns and overlays. It is
one call and it does not require locating a close control, which is frequently an
unlabelled glyph in a corner.

**Filtering a long list.** A combobox you can type into narrows in two keystrokes
what scrolling would take twenty of. That route is covered in
[native selects and the ones that only look like selects](native-selects-and-fake-ones.md).

**Anything with a documented shortcut.** Web applications that define their own
keys usually define good ones, and using them is both faster and closer to how
the application expects to be driven.

## Where it quietly does not work

**A control that is not focusable.** A div acting as a button without a tabindex
cannot be reached by Tab and does not respond to Enter. It is clickable and only
clickable. This is common enough that "the keyboard route failed" is not
evidence of anything except that particular control.

**When focus is not where you think.** Every key goes to whatever has focus, and
nothing about a key press tells you where that is. After a navigation, a modal
opening, or a click that landed on the page background, focus may be on the
document body and your Enter goes nowhere.

The fix is the same as everywhere else here: establish focus deliberately, by
clicking or typing into the specific field first, and then use keys relative to
that.

**Inside an iframe.** Keys go to the focused element, and if focus is in the
outer document they do not enter the frame. Getting focus in there needs a click
in the frame's area first, which is the coordinate route in
[an agent and an iframe](an-agent-and-an-iframe.md).

## Typing is a keyboard operation and it is the expensive one

Worth separating, because it is the exception to everything above. Filling a
field costs about **one second plus 270 ms per character**, measured in
[how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md),
because keystrokes arrive at a human cadence on purpose.

So "use the keyboard" makes single actions cheaper and does nothing for text
entry, which remains the dominant cost of any form-filling task. The two facts
sit together: press keys freely, and count the characters you type.

## A sequence worth stealing

For an ordinary form, this is both faster and more robust than clicking each
field:

```
click the first field        (establish focus, once)
type the value
press Tab
type the value
press Tab
...
press Enter                  (submit)
```

One click instead of one per field, and the focus order is the page's own rather
than your reading of the layout. The caveat is that a form with conditional
fields changes its tab order as it goes, so read the page back rather than
assuming the seventh Tab lands where it did last time. That general habit is in
[when the page changes under the AI agent](when-the-page-changes-under-the-agent.md).

## Short answers to the questions that lead here

**Is pressing a key faster than clicking?** Yes: 0.14 s against 0.23 s for a
selector click and 0.59 s for a coordinate one. It also avoids having to locate
the control at all.

**Can the agent submit a form with Enter?** Yes, from a focused text field, and
it is usually more reliable than finding the submit button.

**Why did Enter do nothing?** Focus was not where you thought. Click into a
specific field first, then use keys relative to that.

**Can I Tab into an iframe?** Not from the outer document. Click inside the
frame's area first, by coordinates.

**Does using the keyboard make typing faster?** No. Text entry is about a second
plus 270 ms a character regardless, because the keystrokes are paced deliberately.

**See also:**
[clicking by selector or by coordinates](clicking-by-selector-or-by-coordinates.md)
for the other two ways to reach a control, and
[getting an AI agent to fill out forms](ai-agent-fill-out-forms.md) for what each
control type demands.

## Sources

- Measured 2026-09-17 through this project's MCP server over stdio, on a page served from `127.0.0.1`: `browser_press_key` with Tab returned `pressed Tab` in 0.14 s; `browser_click` by selector 0.23 s median over three runs; `browser_click_at` 0.59 s median over three runs.
- The typing cost model is measured and sourced on [how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md).

---

*One click to establish focus, then keys. It is the shape of the whole page, and
the measured numbers only explain why it is also faster.*
