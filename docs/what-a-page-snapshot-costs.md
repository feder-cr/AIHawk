---
title: "What a page snapshot costs, per control"
description: "Measured across four pages: about a hundred bytes per interactive element, and nothing for the prose. Which makes the snapshot free on an article and the expensive read on a form."
parent: "Using the Agent"
nav_order: 68
---

# What a page snapshot costs, per control

The snapshot is the read that tells the agent what it can act on. Its size is
usually described as "bigger than the text", which is true on some pages and
badly wrong on others. Measured on 2026-09-17, on four pages identical except for
the number of text inputs on them:

| interactive elements | snapshot | plain text | HTML |
|---|---|---|---|
| 0 | **96 B** | 8 B | 76 B |
| 5 | **574 B** | 19 B | 391 B |
| 20 | **2,065 B** | 59 B | 1,376 B |
| 60 | **6,081 B** | 179 B | 4,056 B |

Fit a line through the snapshot column and it is about **100 bytes per
interactive element**, on a base of under a hundred. The relationship is linear
and it does not involve the page's prose at all.

![Two lines against the number of interactive elements on the page. browser_snapshot climbs steadily from 96 bytes at zero controls to 6,081 bytes at sixty, about a hundred bytes per control. browser_read_text stays almost flat, from 8 bytes to 179, because the four pages differ only in how many text inputs they carry and not in how much they say.](https://raw.githubusercontent.com/feder-cr/invisible_playwright_mcp/main/docs/img/what-a-page-snapshot-costs.png)

The gap between the two lines is the whole point: one of them is answering a
question about the page's controls and the other about its words, and only the
first grows.

## The consequence, which reverses by page type

**On an article, the snapshot is nearly free.** A long explainer with a nav bar
and two links has perhaps a dozen interactive elements, so about a kilobyte,
while its text is tens of kilobytes. Asking for a snapshot there costs almost
nothing.

**On a form, the snapshot is the expensive read.** Sixty inputs is six kilobytes
of snapshot against a hundred and seventy bytes of text. Here the ratio is
thirty-four to one in the other direction.

So the general rule people carry, that the snapshot is roughly twice the text, is
an artifact of the middling page it was measured on. There is no ratio: **there
are two independent quantities, and which one dominates depends on whether the
page is for reading or for filling.**

The companion measurement on a different pair of pages, where a screenshot came
out at eighty-nine times the text on a small page and the ordering reversed on a
long one, is in
[text, HTML, snapshot or screenshot](what-should-the-agent-read.md). Between the
two pages the shape is the same lesson twice: a ratio is a fact about a page, not
about a tool.

## What the hundred bytes buy

Per element the snapshot carries what a tool call needs to act: the tag, the
type, an id where there is one, a selector built to be unambiguous, and the
position in viewport pixels. On the measured pages an entry looked like:

```json
{"tag": "input", "type": "file", "id": "file",
 "selector": "#file", "at": [123, 92]}
```

That is the whole reason to ask for it. The selector is the first rung of the
ladder and the coordinates are the second, so one snapshot equips both.
[Clicking by selector or by coordinates](clicking-by-selector-or-by-coordinates.md)
covers when each one is right.

## What it does not contain, which matters more than the size

Three things, each measured on its own page, and together they explain most of
the "the element is not there" confusions:

- **Nothing inside an iframe.** The host page of a frame containing a button
  reported `"interactive_elements": []`. See
  [an agent and an iframe](an-agent-and-an-iframe.md).
- **Nothing inside a shadow root**, open or closed, even though a click by
  selector reaches both. See
  [shadow DOM and an AI agent](shadow-dom-and-an-ai-agent.md).
- **Nothing that is not interactive.** It is not a description of the page. If
  you want to know what the page says, that is the text read, and it is a
  different tool for a different question.

There is a fourth, subtler one: the snapshot lists elements it cannot help you
use. A file input appears in it, complete with selector and position, and there
is no tool that can put a file into it. See
[uploading a file with an AI agent](uploading-a-file-with-an-ai-agent.md).

## Trimming it when the page is huge

A page with hundreds of controls, a data grid with an input per cell, a settings
screen with two hundred toggles: at a hundred bytes each that is tens of
kilobytes of snapshot every time you look.

`browser_snapshot` takes a `max_chars`, so it can be capped. Capping a list of
controls is cruder than capping prose, though, because you do not know which ones
were dropped.

Usually better: act in phases. Read the page once to decide which region you
care about, then work within it, re-reading only when the layout has changed.
Since reads cost a hundredth of a second in wall clock, the discipline here is
purely about context, not speed, and
[how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md)
has that number.

## Short answers to the questions that lead here

**How big is a page snapshot?** About a hundred bytes per interactive element,
plus a small base. Measured: 96 B with none, 6,081 B with sixty.

**Is the snapshot bigger or smaller than the text?** Both, depending on the page.
On an article it is a fraction of the text; on a sixty-field form it was
thirty-four times larger.

**Does a long page make a bigger snapshot?** Not by itself. Only more controls
do. Prose contributes nothing.

**Why is an element missing from the snapshot?** It is inside a frame, inside a
shadow root, or genuinely not interactive. Each of the first two has its own page
here.

**Can I make it smaller?** `max_chars` caps it, at the price of not knowing what
was dropped. Scoping the work to a region of the page is usually the better
answer.

**See also:**
[text, HTML, snapshot or screenshot](what-should-the-agent-read.md), the companion
measurement for the other three reads, and
[how many MCP tools is too many](how-many-mcp-tools-is-too-many.md), which counts
the context cost you pay every turn regardless of what you read.

## Sources

- Measured 2026-09-17 through this project's MCP server over stdio, against four pages differing only in the number of text inputs (0, 5, 20, 60), each served from `127.0.0.1`. Byte counts are the length of the text payload each tool returned. The example element is copied verbatim from a snapshot taken during the same session.

---

*The number to keep is a hundred bytes a control. Everything else on this page is
what happens when you multiply it by the page in front of you.*
