---
title: "Getting data out of a dashboard with no export button"
description: "Four routes out of a dashboard that will not export, in the order worth trying. The HTML usually already holds the numbers, and the chart almost never does."
parent: "Using the Agent"
nav_order: 54
---

# Getting data out of a dashboard with no export button

Internal tools, admin panels and analytics screens routinely show you a number
and give you no way to take it away. An agent driving the browser can get it out,
and which route it should take depends on something you can check in ten seconds.

Four routes, cheapest first. Try them in order; most dashboards fall at the
second.

## Route 1: the table is already in the page

If the numbers are laid out as a table or a list, they are in the HTML and you
are done. Ask for the markup rather than the text, because the structure is the
part you want: cells stay cells, and a row does not collapse into a sentence.

`browser_read_html` is 1.3 times the cost of the plain text and about a
ninetieth of a screenshot, which is
[measured on its own page](what-should-the-agent-read.md). For tabular data it is
almost always the right ask.

The thing to check before you trust it: **the displayed value is sometimes not
the full value.** A cell showing `1.2M` often carries the exact figure in a title
attribute or a data attribute, and a cell showing `12.3%` may be a rounded render
of something longer. Reading the markup rather than the text is what gets you the
real one.

## Route 2: the page is paginated or virtualised

The table is there, and it holds twenty of four hundred rows. Two different
problems wearing the same coat.

**Paginated**: there is a next control. The agent clicks through and accumulates,
which works and costs about a second per page in click time. Give it a page
ceiling so a broken pager does not become an endless run.

**Virtualised**: the list renders only what is on screen and destroys rows as you
scroll past them. Scrolling and re-reading works, and the trap is that the agent
must accumulate as it goes, because scrolling back does not recover what it saw.
Deduplicate on a key rather than on position, since a virtualised list will hand
you the same row twice.

## Route 3: the numbers are in a chart

This is where dashboards get genuinely hard, and where the obvious move is the
wrong one.

The obvious move is a screenshot and ask the model to read the chart. It costs
about ninety times the text of the page, and it gives you values read off pixels,
which means a number that looks right and is not. For a series of forty points it
is not a transcription, it is an estimate.

Look for the data first, because it is usually somewhere:

- **A table behind a toggle.** Many chart libraries ship an accessible table
  view, sometimes visually hidden, always in the HTML.
- **The tooltip.** Hovering a point reveals the exact value, and the agent can
  hover a point at a time. Slow but exact.
- **The element's own attributes.** Charts drawn as SVG carry their geometry, and
  charts fed from a data attribute carry their numbers.

Use the picture when the question is about the shape rather than the values:
which line is higher, where the step is, whether there is a gap. That is a
genuinely visual question and a screenshot answers it properly.

## Route 4: the value only exists after you ask for it

Some dashboards compute on demand: pick a date range, press apply, wait, read.
There is no shortcut here, and the only thing to get right is the waiting. Wait
for the state rather than for a duration, as in
[when the page changes under the AI agent](when-the-page-changes-under-the-agent.md):
wait until the total has changed from the previous value, not two seconds.

The failure this avoids is reading the *old* numbers after pressing apply, which
produces a perfectly formatted CSV of the previous query and nothing to indicate
it.

## Write it down as you go

Whichever route, accumulate to the file per page or per scroll rather than at the
end. A forty-page pager that dies on page thirty-one should leave thirty pages of
rows behind, and
[extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md)
is the output side of that.

Record the URL and the timestamp with the rows. A dashboard number without the
filter state it came from is not reproducible, and you will not remember which
date range you had selected.

## The check that catches the silent failure

Ask for the total the dashboard itself displays, and compare it with the sum of
what you extracted. If the page says 412 rows and you have 380, you lost a page;
if the page says a total of 91,204 and your column sums to 74,880, you lost rows
or read a rounded column.

This is one extra read and it is the only thing standing between a partial
extraction and a partial extraction you did not notice.

## Short answers to the questions that lead here

**How do I export data from a dashboard with no export?** Read the HTML if the
data is a table, page or scroll through if it is paginated or virtualised, and go
looking for the chart's underlying table before screenshotting the chart.

**Should I screenshot the chart and have the model read it?** Only if the question
is about shape. For values it is expensive and approximate, and the exact numbers
are usually in the markup or the tooltip.

**Why did my extraction get 20 rows out of 400?** Pagination or virtualisation.
Both look identical on the first read; check for a next control before assuming.

**Why do my numbers not match what the dashboard says?** Either a rounded display
value where the markup holds the exact one, or a page you lost. Compare against
the total the dashboard prints.

**The page recalculates when I change a filter. How do I not read the old
numbers?** Wait for a value to change rather than waiting a fixed time, and
confirm the filter state is what you set before recording anything.

**See also:**
[getting website data into Google Sheets with an AI agent](website-data-to-google-sheets-ai-agent.md)
for where the rows go next, and
[text, HTML, snapshot or screenshot](what-should-the-agent-read.md) for why the
markup is the cheap ask and the picture is not.

## Sources

- The relative cost of the four reads (text 1x, HTML 1.3x, snapshot 2.1x, screenshot 89x) is measured and sourced on [text, HTML, snapshot or screenshot](what-should-the-agent-read.md).
- The routes and their failure modes are from driving real dashboards with this browser, and are offered as experience rather than as a study. No specific product is named.

---

*Route 3 is the one worth remembering. Everybody reaches for the screenshot on a
chart, and the numbers are nearly always sitting in the page in a form that does
not need reading off pixels.*
