---
title: "Text, HTML, snapshot or screenshot: what the agent should read"
description: "The same page, read four ways, measured: a screenshot costs 89 times the text. Which one to ask for, and the one case where the expensive answer is the only one."
parent: "Using the Agent"
nav_order: 47
---

# Text, HTML, snapshot or screenshot: what the agent should read

A browser MCP server offers several ways to hand the model a page, and they are
not interchangeable. Measured on 2026-09-17 through the four tools in turn, on a
**small page**: 3,665 bytes of served HTML with a heading, a paragraph, a
twenty-item navigation list, a five-control form and a forty-row table.

| how the page comes back | bytes | relative |
|---|---|---|
| `browser_read_text` | 1,021 | 1x |
| `browser_read_html` | 1,342 | 1.3x |
| `browser_snapshot` | 2,186 | 2.1x |
| `browser_take_screenshot` | 90,768 | **89x** |

**Everything on that list is the same page.** The last row is eighty-nine times
the first because a picture of text is not text, and it rides in the model's
context on the turn it arrives and on every turn after it, unless your client
prunes it.

## The same four reads on a big page, which reorders them

Do not carry those ratios to a long page. Repeated against a page of 400
paragraphs, 37,538 bytes of served HTML:

| how the page comes back | bytes | note |
|---|---|---|
| `browser_read_text`, default | 6,101 | **truncated, and it says so** |
| `browser_read_text`, `max_chars: 50000` | 35,490 | the whole text |
| `browser_read_html` | 37,531 | **not truncated** |
| `browser_snapshot` | 78 | no interactive elements on this page |
| `browser_take_screenshot` | 123,940 | one viewport |

Three things change, and each one contradicts something you would have assumed
from the first table.

**Text truncates by default and tells you.** The tail of the default read is,
verbatim: `6000 of 35490 characters. Raise max_chars, or narrow the selector to
the part you need.` That is the best possible behaviour, because the alternative
is a silently short answer, and it means **a read that looks complete on a small
page is a tenth of a long one** unless you raise the limit or scope the selector.

**HTML does not truncate, so on a long page it is the expensive one.** It was 1.3
times the text on the small page and it is the largest text payload here, bigger
than the full text. The rule "HTML is a cheap escalation" is a small-page rule
only.

**The snapshot is not text at all.** Seventy-eight bytes, because this page has no
interactive elements. It lists what you can act on, so its size tracks the number
of controls rather than the amount of content. On a form-heavy page it is
substantial and on an article it is nearly empty, which is exactly right and is
not what "2.1x the text" suggested.

## The decision, in one rule

**Ask for the cheapest representation that contains the answer, and go up only
when it does not.**

- **`browser_read_text`** when you want what the page says. Prices, an address, a
  confirmation number, an article. It is a tenth of a snapshot and a ninetieth of
  a picture.
- **`browser_snapshot`** when you want to *act*. It is the only one of the four
  that hands back the selectors and the coordinates for each element, which is
  what a click or a fill needs. It costs what the page's controls cost, not what
  its content costs.
- **`browser_read_html`** when structure is the content: a table you want row by
  row, attributes, a data attribute holding the real value. Reach for it after
  text has failed, not before, and on a long page know that it is the biggest
  text payload of the four rather than a cheap escalation.
- **`browser_take_screenshot`** when the answer is visual and nothing else will
  do. A chart with no underlying table. A layout question. A canvas. A page whose
  meaning is in what is on top of what.

## The case for the expensive one, stated fairly

There is a real case, and dismissing it on the byte count would be wrong.

A screenshot is the only representation that shows what is actually *presented*:
what is covered by an overlay, what is below the fold, what is visually
disabled, which of two identical labels is the one a person would click. A model
reasoning about "the button next to the total" is reasoning about a picture, and
handing it the text of the page is handing it a different problem.

So the rule is not "never screenshot". It is **screenshot on purpose, once, when
the visual arrangement is the question**, and read text the rest of the time. The
failure to avoid is the loop that screenshots after every action out of caution,
which is where an eighty-nine-fold multiplier becomes the whole context window.

## What the snapshot actually buys

Worth separating, because it is the one people skip. A snapshot is not "text with
extra weight". It reports, per element, the identity a tool call needs: a
selector built to be unambiguous, and the element's position in viewport pixels.

That is what makes the three-rung ladder work. A named tool with a selector
first; coordinates from the snapshot when no selector describes the thing, which
is the case for a canvas, a slider or a map; the picture only when the snapshot
does not list the element at all.
[How the tools are shaped, and why](mcp-tool-design.md) is the reasoning behind
that ordering.

## What this is not about

There is a separate question with a similar shape, and mixing them up leads to
the wrong fix: whether an agent that reads the DOM and an agent that clicks
pixels are *detected* differently. That is a question about what a site can see,
not about what your context costs, and it has its own answer in
[DOM-reading vs screenshot agents](https://github.com/feder-cr/invisible_playwright/wiki/dom-reading-vs-screenshot-agents).
This page is only about the bill.

## Short answers to the questions that lead here

**Should my agent use screenshots or the DOM?** For cost, the DOM, by a factor of
about ninety on a small page. For anything where the visual arrangement is the
question, the screenshot, deliberately and once.

**How much context does a screenshot use?** On the page measured here, 90,768
bytes of base64 against 1,021 bytes of text. Scale with the viewport, not with
how much the page says: a mostly empty page still costs a full picture.

**Why is my agent running out of context on a short task?** Count the
screenshots. Ten of them on this page is nine hundred thousand bytes, and the
task itself was a kilobyte.

**What is the difference between read_text and snapshot?** Text is what the page
says. The snapshot is what the page offers: elements, selectors, positions. You
read with the first and act with the second.

**Is HTML ever the right answer?** When the structure carries meaning that the
text loses: table cells, attributes, a value stored in the markup rather than
displayed. On a small page it is 1.3x the text; on a long one it was the largest
of the four text payloads, so it is a cheap escalation only while the page is
short.

**Why did my read come back truncated?** The text read has a default ceiling, and
on the long page here it returned 6,000 of 35,490 characters with a line saying
exactly that. Raise `max_chars` or scope the read with a selector. The important
part is that a short answer on a long page is not the page being short.

**See also:**
[how many MCP tools is too many](how-many-mcp-tools-is-too-many.md), which counts
the other standing context cost, the one you pay every turn whether you read
anything or not, and
[how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md),
which shows that all four of these reads are free in wall clock and only differ
in context.

## Sources

- Measured 2026-09-17 through the MCP server over stdio, tools called in turn against pages served from `127.0.0.1`. Small page: 3,665 bytes of HTML (one heading, one paragraph, a twenty-item nav list, a five-control form, a forty-row table, no images), medians over three runs. Large page: 37,538 bytes of HTML, 400 paragraphs, no interactive elements, one run per tool. Byte counts are the length of the text or image payload the tool returned, and the truncation line is quoted verbatim from the response.

---

*The two tables disagree on purpose, and that is the finding. A ratio measured on
one page is a fact about that page: re-measure on yours by calling the tools once
each and comparing the lengths, which is a minute of work and the whole method.*
