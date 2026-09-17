---
title: "Clicking by selector or by coordinates"
description: "Measured: 0.23s against 0.59s on the same button. Speed is not the reason to prefer one, though. The reason is that they fail in opposite ways, and only one of the failures is visible."
parent: "Using the Agent"
nav_order: 70
---

# Clicking by selector or by coordinates

Two ways to click the same thing. Measured on 2026-09-17 on one button, three
runs each, on a page served from `127.0.0.1`:

| | median |
|---|---|
| `browser_click` with a selector | **0.23 s** |
| `browser_click_at` with the coordinates from the snapshot | **0.59 s** |

The coordinate click is about two and a half times slower, because it is a real
pointer being moved to a place rather than an element being located and
activated. It also hands back a picture of the page afterwards, where the
selector click hands back a sentence.

Neither of those is the reason to choose. The reason is the next section.

## They fail in opposite ways, and that decides it

**A stale selector fails loudly.** If the element has moved, been replaced, or
was never there, the call reports it. You get an error, the agent can react, and
nothing happened to the page.

**Stale coordinates succeed wrongly.** There is always something at an x and a y.
If the layout shifted between the snapshot and the click, the pointer lands on
whatever is there now: a different button, a link, an advert. The call reports
success, the wrong thing happened, and nothing in the run says so.

That asymmetry is worth more than two-fifths of a second. **Prefer the selector
because its failure is visible**, and reach for coordinates when the selector
cannot describe the target at all.

Layout moving between the look and the click is not rare. It is the normal
behaviour of a page with images and lazy content, and it has
[its own page](when-the-page-changes-under-the-agent.md).

## When coordinates are the only route

Three cases, two of them measured on their own pages here:

- **Inside an iframe.** The selector times out after fifteen seconds; the
  coordinate click lands. Measured, in
  [an agent and an iframe](an-agent-and-an-iframe.md).
- **A component with no usable selector**, typically inside a shadow root with
  nothing stable exposed. Clicking into a shadow root by selector does work when
  you have one, which is
  [its own surprise](shadow-dom-and-an-ai-agent.md); coordinates are for when you
  do not.
- **Anything not made of elements.** A canvas, a map, a chart, a slider drawn
  with divs, a signature pad, a picture with hotspots. There is nothing to
  select, and a position is the only way to say where you mean.

There is also a fourth that is about behaviour rather than structure: a control
that only responds to a genuine pointer sequence in one place. Rare on ordinary
pages, real on drag handles and custom sliders, where `hold_seconds` on the
coordinate click is the tool that has the shape of the gesture.

## Getting coordinates right

Take them from the snapshot, which reports `at: [x, y]` in viewport pixels for
every element it lists, and use them immediately. They are a description of the
page at the moment of the read, and their accuracy decays as soon as anything
moves.

The sequence that works:

```
snapshot  ->  pick the element  ->  snapshot again  ->  click_at the fresh position
```

The second read costs about a hundredth of a second, per
[how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md),
and it closes the gap from a model turn to a tool call.

When the element is not in the snapshot at all, the coordinates have to come from
a picture: take a screenshot, find the thing in it, click where it is. That is
the third rung, and it is the expensive one, at about ninety times the text of
the page in
[what the agent should read](what-should-the-agent-read.md).

## Why the coordinate click returns a picture

Because it is the rung you use when you could not describe the target, so the
only honest confirmation is what the page looks like now. On the measured run
that reply was a 17 KB image.

Treat it as a confirmation to look at when something seems wrong rather than
something to keep. Ten coordinate clicks in a loop is ten images in the context,
which is the budget problem described on the reading page.

## The rule in one line

**Selector when you can name it, coordinates when you can only point at it,
screenshot when you cannot even find it to point at.** Go down the ladder only
when the rung above genuinely does not work, and go back up as soon as it does.

## Short answers to the questions that lead here

**Which is faster, selector or coordinates?** Selector: 0.23 s against 0.59 s on
the same button. The difference is a real pointer being moved.

**Why prefer the selector if both work?** Because when it is wrong it fails
visibly. A wrong coordinate clicks something else and reports success.

**When do I have to use coordinates?** Inside an iframe, on a component with no
usable selector, and on anything drawn rather than built from elements: canvas,
maps, sliders.

**Where do the coordinates come from?** The snapshot gives `at: [x, y]` per
element. Re-read immediately before clicking, because they age as soon as the
layout moves.

**Why did my coordinate click do the wrong thing?** The page moved between the
read and the click. That failure is silent by construction, which is the argument
for the selector.

**See also:**
[why did the AI agent click the wrong thing](why-did-the-agent-click-the-wrong-thing.md),
where this asymmetry is the first of six causes, and
[what a page snapshot costs, per control](what-a-page-snapshot-costs.md), since the
snapshot is where both the selector and the coordinates come from.

## Sources

- Measured 2026-09-17 through this project's MCP server over stdio, three runs of each call against the same button on a page served from `127.0.0.1`, with a fresh navigation before each run: `browser_click` median 0.23 s, `browser_click_at` at the snapshot's reported position median 0.59 s. The coordinate call returned a 17,392-byte image alongside its result. `browser_press_key` on the same page took 0.14 s.

---

*Two and a half times slower is the headline and the least important line here.
The one that matters is that only one of these two tells you when it was wrong.*
