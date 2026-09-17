---
title: "What an AI agent can and cannot do inside an iframe"
description: "Measured: the reads are blind to it, a selector times out after 15 seconds and 275 attempts, and the real pointer walks straight in. The clearest case for the coordinate rung there is."
parent: "Using the Agent"
nav_order: 66
---

# What an AI agent can and cannot do inside an iframe

An iframe is a second document inside the first, and a browser agent driving the
outer one does not automatically get the inner one. Measured on 2026-09-17
against a host page with one same-origin frame in it, served from `127.0.0.1`:

| what was tried | result |
|---|---|
| `browser_read_text` | the frame's text is **not** in it |
| `browser_read_html` | the frame's content is **not** in it |
| `browser_snapshot` | `"interactive_elements": []` - the frame's button is **not listed** |
| `browser_click` with the button's selector | **fails**: `'#fb' not actionable in 15s after 275 attempts` |
| `browser_click_at` on the button's position | **works** |
| `browser_evaluate` reading `contentDocument` | **works**, same-origin |

The frame's title went from `child` to `FRAME-CLICKED` after the coordinate
click, which is the page's own evidence that the click landed where it was meant
to rather than on the frame's border.

## Why the reads miss it and the pointer does not

Because they operate on different things. The reads and the selector work on the
document the tools are pointed at, and the frame is a boundary in that document:
its contents belong to another one. The pointer works on the **window**. There is
no boundary in a screen coordinate, so a real click at a position inside the
frame's rectangle is delivered to whatever the compositor has there, which is the
frame's button.

That is the whole explanation, and it generalises: **anything routed through the
document stops at the frame, anything routed through the input devices does
not.** Typing and key presses behave like the pointer once focus is inside.

## This is the textbook case for the second rung

A browser MCP server offers a ladder: a named tool with a selector first,
coordinates when no selector describes the target, the picture when the snapshot
does not list the thing at all. The ordering usually reads as a preference for
precision. Here it is not a preference, it is the only route.

Get the coordinates the same way you would for a canvas or a slider: take a
screenshot, find the control in the picture, and click where it is. The snapshot
will not help you because, as measured above, it lists nothing from inside the
frame.

[Clicking by selector or by coordinates](clicking-by-selector-or-by-coordinates.md)
has the trade in general, including the failure asymmetry that makes the first
rung worth trying first everywhere else.

## The fifteen seconds you will otherwise spend confused

The selector attempt is worth dwelling on, because of how it fails. It does not
say "there is no such element". It retries for fifteen seconds, 275 times, and
then reports the element as not actionable.

From the outside that looks like a slow page or a flaky selector, which is the
wrong diagnosis and sends you off tuning waits. **A click that burns the full
fifteen seconds on a page you know contains the element is a strong hint that the
element is in a frame**, and it is worth checking before anything else.

The general shape of the "it retried and gave up" failure is in
[how long the agent waits before it gives up](how-long-before-the-agent-gives-up.md).

## Reading what is inside, when you need the text

Two routes, and which one you get depends on origin.

**Same origin**: `browser_evaluate` can reach `contentDocument` and read the
frame's DOM. Measured above. That is a read, which this browser allows; acting on
it from script is refused, for the reason in
[keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md).

**Cross origin**: nothing. `contentDocument` is null and the browser is enforcing
the same rule it enforces for every script on the web. There is no setting on
this side that changes it, and a tool that claimed otherwise would be describing
a security hole.

For a cross-origin frame the honest options are: click by coordinates, read it
out of a screenshot, or navigate the frame's URL directly in the main page and
work with it as a page of its own. The third is usually the best one and is the
least considered.

## Say "iframe" in the task

The practical instruction, and it costs one sentence: tell the agent the content
is in a frame, and tell it to use coordinates for it. Otherwise the default
behaviour is to try the selector, wait fifteen seconds, conclude the element does
not exist, and go looking for another way in.

Also worth saying: consent walls, payment fields, embedded maps, video players,
chat widgets and comment sections are frames more often than not. If a control
you can plainly see is invisible to every read, that is the first thing to
suspect.

## Short answers to the questions that lead here

**Can an AI agent click a button inside an iframe?** By coordinates, yes,
measured. By selector, no: it times out after fifteen seconds without finding the
element.

**Why does my agent say the element does not exist when I can see it?** If it is
in a frame, the reads and the snapshot genuinely do not contain it. Look for a
frame before you suspect the selector.

**Can it read text inside a frame?** From a same-origin frame, yes, through
`contentDocument`. From a cross-origin one, no, and that is the browser's
security model rather than a limitation of the tool.

**What is the best way to handle a cross-origin frame?** Often to open the
frame's own URL as the main page and work with it directly. Otherwise
coordinates, or a screenshot.

**How do I know something is in a frame?** A control that is visible on screen
and absent from `browser_snapshot` is the signature. A fifteen-second timeout on
a selector you are sure about is the second.

**See also:**
[what a page snapshot costs, per control](what-a-page-snapshot-costs.md), which
is the other half of understanding what the snapshot does and does not contain,
and
[shadow DOM and an AI agent](shadow-dom-and-an-ai-agent.md), which is the mirror
image of this page: a boundary the reads cannot cross and the selector can.

## Sources

- Measured 2026-09-17 through this project's MCP server over stdio, against a host page with one same-origin iframe served from `127.0.0.1`. The snapshot returned `{"title": "host", "url": "...", "interactive_elements": []}`; `browser_click` on the frame button's selector returned `'#fb' not actionable in 15s after 275 attempts`; `browser_click_at` at the button's screen position changed the frame document's title from `child` to `FRAME-CLICKED`, read back through `contentDocument`.

---

*The pair to hold in your head: the document stops at the frame, the pointer does
not. Every line above follows from that, including the fifteen seconds.*
