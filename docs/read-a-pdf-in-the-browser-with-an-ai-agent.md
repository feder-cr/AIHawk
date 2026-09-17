---
title: "Reading a PDF that opens inside the browser"
description: "The viewer does put the text in the page, so an agent can read it. It also renders lazily: on a 12-page document only two pages existed at once. Measured, with the selector that gives clean text."
parent: "Using the Agent"
nav_order: 61
---

# Reading a PDF that opens inside the browser

A link that opens a PDF in the browser instead of downloading it looks like a
dead end for an agent: there is no file, and the page is a picture of a document.
It is not a dead end. The viewer puts real text in the page, and a text read gets
it.

The part that will catch you is what *else* is in the page, and how much of the
document is in it at any moment. Both were measured on 2026-09-17 against a PDF
served from `127.0.0.1`.

## Yes, the text is there

Reading a one-page PDF with a plain text read returned the document's text, in
full and as text rather than as pixels. So the first instinct, screenshot the
viewer and have the model read the image, is the expensive wrong answer: it costs
about ninety times as much, as
[measured](what-should-the-agent-read.md), and returns an approximation of
something that was available exactly.

## But the toolbar comes with it

An unselectored read returns the viewer's own interface first. Verbatim, from the
run:

```
Manage pages
Previous
Next
of 12
Zoom Out
Zoom In
Comment
Add signature
...
```

and then the document. On the one-page test that was 180 bytes of which most was
chrome.

The fix is to read the container rather than the page:

```
browser_read_text  selector: #viewerContainer
```

On the twelve-page document that took the read from **167 bytes to 39**: the same
document text, none of the buttons. Scope the read and the noise disappears.

**And do not throw the toolbar away without looking at it**, because one thing in
it is genuinely useful: `of 12` is the page count. It is the only place the
viewer tells you how long the document is, and you need it for the next section.

## The measurement that matters: only a window is ever present

Here is the finding that decides how you write the task. The viewer renders
lazily, so the document's text is not all in the page at once.

On a twelve-page PDF, immediately after loading:

| when | pages present in the text |
|---|---|
| on load | **1, 2** |
| after pressing End | **1, 2, 11, 12** |

Pages three to ten were never in the page at all. A single read of a long PDF
does not return a short version of the document. It returns **the beginning**,
and nothing warns you that the rest is missing.

This is the difference between an agent that says "the contract does not mention
termination" and one that is correct. On a forty-page document, one read sees
about five per cent of it.

## So the task has to walk the document

The shape that works:

1. Read the toolbar once to get the page count.
2. Read `#viewerContainer` and keep what you got.
3. Move down by one screen, wait for the text to change, read again, append.
4. Repeat until you have seen the last page.
5. Deduplicate: consecutive reads overlap, and the same page will arrive twice.

Waiting for the text to change rather than for a fixed duration is the same rule
as everywhere else, and it matters more here because rendering a page is slower
than scrolling to it. The general form is in
[when the page changes under the AI agent](when-the-page-changes-under-the-agent.md).

Reads cost a hundredth of a second, so walking forty pages costs nothing in tool
time. The expense is entirely in how much text ends up in the model's context,
which is the real budget for a long document.

## When to stop trying and get the file instead

If you can get the file, get the file. A PDF handed to something that parses PDFs
gives you the whole document, the page boundaries, the tables and the metadata,
with none of this.

**And be clear about who does that, because it is not the agent.** The tool
surface here is navigate, read, click, type, screenshot and their session
siblings: there is no download tool and no save-file tool, so the agent's
deliverable is its answer as text. It can find the document and tell you where it
is; fetching the bytes is yours, or a script's.
[Using an AI agent to download invoices from portals](ai-agent-download-invoices.md)
is the page that works through that division honestly, and it applies to any
document portal rather than only to invoices.

So read it in the browser when that is the deliverable you actually want: the
fields rather than the file, or a document generated on demand behind a session
that you only need to answer one question about.

## What the viewer does not give you

**Layout.** The text arrives in the viewer's reading order, which is not always
the document's. Multi-column pages and tables come out interleaved, and a table
read this way is usually unusable.

**Page boundaries.** You know which pages are present only because you can see
their content; the text does not come tagged with page numbers unless the
document prints them.

**Scanned documents.** A PDF that is images of text has no text layer, so a text
read returns nothing at all. That is the one case where the screenshot is the
correct tool, and the answer is only as good as the model's reading of the image.

The distinguishing test is free: read the container once. Empty means scanned.

## Short answers to the questions that lead here

**Can an AI agent read a PDF in the browser?** Yes. The built-in viewer puts real
text in the page and a text read returns it, which is far cheaper and more
accurate than screenshotting the viewer.

**Why does my read only return the first part of the document?** Because the
viewer renders lazily. Measured on a twelve-page PDF: two pages present on load,
four after jumping to the end, the middle eight never present at once. Walk the
document and accumulate.

**How do I get rid of the toolbar text?** Read with the selector
`#viewerContainer`. On the test document that cut the read from 167 bytes to 39.

**How do I know how many pages it has?** The toolbar says `of N`, and that is the
only place it is stated. Read it before you scope the read to the container.

**The read comes back empty. Why?** Most likely a scanned PDF with no text layer.
That is the case where a screenshot is the right tool rather than the wasteful
one.

**Should I get the file instead?** If you can, yes: a real PDF parser gives you
page boundaries, tables and metadata that the viewer does not. Note that the
agent is not the thing that fetches it. There is no download tool in this
surface, so the agent finds and reads while saving stays with you.

**See also:**
[using an AI agent to download invoices from portals](ai-agent-download-invoices.md),
which sets out what "download" honestly means with this tool surface, and
[text, HTML, snapshot or screenshot](what-should-the-agent-read.md) for why
reading beats screenshotting whenever the text is actually there.

## Sources

- Measured 2026-09-17 through this project's MCP server against PDFs served from `127.0.0.1`. One-page document: a plain text read returned the document text plus the viewer toolbar, 180 bytes. Twelve-page document: unselectored read 167 bytes, `#viewerContainer` read 39 bytes; pages 1 and 2 present on load, pages 1, 2, 11 and 12 present after pressing End, pages 3 to 10 never present in a single read.
- The 89x cost ratio between a screenshot and the text of the same page is measured and sourced on [text, HTML, snapshot or screenshot](what-should-the-agent-read.md).

---

*The lazy-rendering number is the reason this page exists. Everything else about
reading a PDF in a browser is guessable; that one is not, and it is the
difference between an answer and a confident wrong answer about page thirty.*
