---
title: "Watching the agent work, and when it is worth it"
description: "The live view is the whole window as a person sees it, tab strip and pointer included, at 37 KB a look. What it shows that a screenshot does not, and why it is for you rather than the model."
parent: "Using the Agent"
nav_order: 74
---

# Watching the agent work, and when it is worth it

There is a tool whose output is not for the model. `browser_watch` returns the
browser window the way somebody sitting at the machine would see it: the tab
strip, the address bar, the page, and the pointer where it currently is.

Measured on 2026-09-17: **0.36 seconds, 37,236 bytes** for one look.

## What it shows that a page screenshot does not

A page screenshot is the viewport. The live view is the application. The
difference carries four things you cannot otherwise see:

- **The pointer.** Where the mouse actually is, which is the only direct evidence
  for a coordinate click landing where you meant. When a click by position goes
  wrong, this is the artifact that shows why.
- **The tab strip.** Whether a click opened a second tab, which is a common and
  otherwise invisible reason the agent seems to be acting on the wrong page.
- **The address bar.** The URL as the browser has it, including a redirect the
  page body gives no sign of.
- **The window itself**, including anything drawn over the page by the browser
  rather than by the site.

## It is for the person, not for the model

The cost says so. At 37 KB a look it is in the same class as a screenshot, and a
model that takes one after every action spends its context on pictures of a tab
strip. The reading page has the arithmetic:
[text, HTML, snapshot or screenshot](what-should-the-agent-read.md).

The other reason is that the model already has better instruments for its own
questions. What is on the page is the text read, at a hundredth of the size. What
it can click is the snapshot. The live view answers "what is going on", which is
a question a person asks.

So the sensible pattern is: **the agent works, you look when something seems
wrong.** One look at the moment of confusion is worth ten taken as a habit.

## Two failure modes it settles immediately

**"The click succeeded and nothing happened."** Look. Either the pointer is not
where you expected, which is a coordinate problem, or there is an overlay across
the page that the text read shows nothing about. Both are visible in one frame.
The full list of causes is in
[why did the AI agent click the wrong thing](why-did-the-agent-click-the-wrong-thing.md).

**"The agent is reading the wrong page."** Look at the tab strip. A link with a
target opened a new tab, the agent is still driving the old one, and every read
it takes is correct and about the wrong document.

## The honest limits

**A capture that stops.** A headed window that gets minimised stops producing
frames. The tool starts the capture again on the next look rather than handing
back a stale picture, and if the window cannot be captured it says so instead of
answering with an old one. That is the right behaviour and it is worth knowing it
is happening.

**It is a picture.** Text in it is pixels, so anything you want to quote, diff or
search should come from a text read instead. For a record you intend to keep,
[dated screenshots of a page as evidence](dated-screenshots-as-evidence.md) makes
the case that the image is the least useful artifact in the capture.

**It shows your window.** Whatever is in that browser is in the frame, including
a logged-in state, an account name, or another tab's title. Before a frame from
it goes anywhere, look at it.

## Headed or headless

Headless is the default and the live view still works: there is a window being
composited, it is simply not on your screen.

Running headed is the other way to watch, and it is the better one when a human
step is coming: a login, a code from an app, an upload the agent
[cannot perform](uploading-a-file-with-an-ai-agent.md). Then the point is not
observation, it is that you can reach in and do the step yourself.

## Short answers to the questions that lead here

**How do I watch an AI agent browse?** `browser_watch` returns the whole window,
pointer and tab strip included. Measured at 0.36 s and 37 KB per look.

**How is it different from a screenshot?** A screenshot is the page. This is the
application around it: pointer, tabs, address bar, browser chrome.

**Should the model call it every turn?** No. At 37 KB it is screenshot-class cost,
and the model has cheaper instruments for its own questions. Use it when
something seems wrong.

**Does it work headless?** Yes. There is still a window being composited, just
not on your screen.

**Why did the view stop updating?** A minimised headed window stops the capture.
It is restarted on the next look, and if the window cannot be captured the tool
says so rather than showing you an old frame.

**See also:**
[browser problem or model problem](browser-problem-or-model-problem.md), where
looking at the window is one of the fastest ways to tell the two apart, and
[clicking by selector or by coordinates](clicking-by-selector-or-by-coordinates.md),
since the pointer's position is the evidence a coordinate click needs.

## Sources

- Measured 2026-09-17 through this project's MCP server over stdio: one `browser_watch` call returned an image payload of 37,236 bytes in 0.36 s. The capture behaviour on a minimised window, and the refusal to answer with a stale frame, are the tool's documented behaviour in this project's own MCP server page.

---

*The one-line version: it is the only tool here whose audience is you. Everything
about how to use it follows from that.*
