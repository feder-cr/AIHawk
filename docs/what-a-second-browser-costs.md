---
title: "What a second browser costs"
description: "Measured: 77 MB for the server alone, 704 MB with one browser, 1,261 MB with two. The second one is 556 MB and eight processes, which is the number that decides whether your machine can hold it."
parent: "Using the Agent"
nav_order: 72
---

# What a second browser costs

The session can hold two browsers, `main` and `support`, and the reason to know
what the second one costs is that the answer is not "a bit more". Measured on
2026-09-17 on one Windows machine, reading the whole process tree rather than the
parent:

| state | resident memory | processes |
|---|---|---|
| the MCP server, no browser | **77 MB** | 2 |
| one browser open | **704 MB** | 10 |
| two browsers open | **1,261 MB** | 18 |
| **the second browser alone** | **556 MB** | **8 more** |

The second browser is **79% on top of the first**, not a rounding error. Eight
more processes, because Firefox is multiprocess and a second browser brings its
own set.

## What that means for where you can run this

A single browser at 704 MB fits on a 2 GB machine with room to work. Two at 1,261
MB is most of a 2 GB machine before the pages have anything heavy on them, and
the figures above are with blank pages: real content pushes content processes up
from here.

So the practical line: **two browsers wants 4 GB**, and on 2 GB you should open
the second one deliberately and close it when the comparison is done. The wider
disk-and-memory picture for running any of this yourself is in
[what a self-hosted AI agent costs to run](self-hosted-ai-agent.md).

The server itself, at 77 MB and two processes, is nothing. All of the cost is the
browsers, which is the same conclusion the self-hosting measurement reached from
the other direction.

## When the second one earns it

It earns 556 MB when the task genuinely needs two views at the same moment:

- a reference open while a form is being filled, so checking something does not
  navigate away from half-entered state;
- two accounts side by side;
- the same page from two exits, which is the only honest way to compare markets
  at one moment rather than two minutes apart, as in
  [seeing a page as it appears in another country](see-a-page-from-another-country.md);
- a clean second opinion on a page that is behaving oddly in a browser that has
  been clicking around for twenty steps.

It does not earn it for doing two unrelated jobs. Two sessions is cleaner there:
separate processes, separate failures, and one browser's memory freed when its
job ends.

## Close it when you are done

`browser_close` with the browser named. Worth saying because the natural habit
is to leave both open for the rest of the conversation, and the second one goes
on holding half a gigabyte while nothing is using it.

The identities and the focus rule, which are the other half of running two, are
in
[two browsers in one session](two-browsers-in-one-session.md).

## Measuring it on your own machine

The method is the part to copy, because the absolute numbers are one machine and
one set of blank pages:

1. Find the server process and read its resident memory **including children**.
   Reading the parent alone reports about a tenth of the truth here, since the
   parent is the Python process and the browsers are its descendants.
2. Take a reading with no browser, one browser, and two.
3. Subtract.

That is three readings and a subtraction, and it tells you what your pages
actually cost rather than what a blank one does.

## Short answers to the questions that lead here

**How much memory does a browser agent use?** Measured here: 704 MB for the
server plus one browser across ten processes, on a blank local page. Real pages
are higher.

**How much does a second browser add?** 556 MB and eight processes, a 79%
increase on the first.

**Can I run two browsers on a 2 GB machine?** One comfortably, two barely and not
with heavy pages. Plan on 4 GB if two are normal for your work.

**Why is the parent process only using a few dozen megabytes?** Because it is the
Python side. The browsers are separate processes and you have to sum the tree to
see them.

**Should I use two browsers or two sessions?** Two sessions for unrelated jobs,
which also frees the memory when one finishes. Two browsers when one task needs
both views at once.

**See also:**
[two browsers in one session](two-browsers-in-one-session.md) for the behaviour,
including the focus rule that catches people, and
[what a self-hosted AI agent costs to run](self-hosted-ai-agent.md) for the disk
and startup side of the same question.

## Sources

- Measured 2026-09-17 on one Windows 11 machine, reading resident memory across the MCP server process and all of its descendants at three points: before opening a browser (77 MB, 2 processes), after `browser_open` (704 MB, 10 processes), and after `browser_open` with `browser: support` (1,261 MB, 18 processes). Both browsers were headless and on blank pages.

---

*Three readings and a subtraction. The reason the number is worth having is that
"a second browser" sounds cheap and is 79%.*
