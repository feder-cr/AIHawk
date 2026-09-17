---
title: "Reading a table with an AI agent"
description: "Tables lose their shape in a text read and keep it in the markup, which costs more on a long page. Headers that span, cells that hide the real value, and the row that is not a row."
parent: "Using the Agent"
nav_order: 83
---

# Reading a table with an AI agent

A table is the one page element where the structure is the meaning. Read it as
text and you get the numbers in reading order with nothing saying which column
each belonged to, which for anything wider than two columns is not recoverable.

So the first decision is which read to ask for, and it is not the cheapest one.

## Ask for the markup, with the cost in mind

`browser_read_html` keeps cells as cells and rows as rows. On a small page it
costs about 1.3 times the plain text; on a long one it was the **largest** text
payload of the four reads, because it does not truncate where the text read does.
Both measurements are on
[text, HTML, snapshot or screenshot](what-should-the-agent-read.md).

That matters here more than elsewhere, because tables are exactly the pages that
get long. A four-hundred-row table in markup is a lot of context, and the way out
is to scope the read to the table rather than the page, not to switch to a
cheaper read that destroys the structure.

## The displayed value is often not the value

Three ways a cell lies, all common in real tables:

- **Rounding.** `1.2M`, `12.3%`, `3.4k`. The exact figure is frequently in a
  title or a data attribute on the cell, and the text read cannot see either.
- **Formatting.** Thousands separators and decimal marks differ by locale, so
  `1.234` is one number in one country and another elsewhere. Record what the
  page showed as well as what you parsed, which is the two-column rule in
  [normalising values across sites](normalising-values-across-sites.md).
- **Sorting by a hidden key.** A column of dates displayed as "3 days ago" sorts
  on a timestamp that only exists in an attribute.

All three are reasons the markup is the right ask rather than a preference.

## Headers are harder than rows

Simple tables have one header row. Real ones do not:

- **Spanning headers**, where one cell covers three columns and a second row
  names them. The column a value belongs to is the pair, and a naive read takes
  the nearest.
- **Row headers**, where the first cell of each row is a label rather than data.
  Treating it as a value shifts the whole row by one.
- **Repeated headers** every twenty rows, on long tables, which then appear as
  data rows containing the word "Price".
- **Layout tables**, where a table element is used for arrangement and there is
  no data in it at all.

Tell the agent which shape it is looking at if you know, and have it report the
header row it decided on. A run that states "columns: Item, Price, Stock" is one
you can check in a second; a run that returns rows is one you cannot.

## Rows that are not rows

Totals, subtotals, section separators, "no results" placeholders and expandable
detail rows all arrive as rows. A sum over a column that includes the total row
is double the truth, and it looks plausible.

Two instructions handle it: **say what a data row looks like** (for instance, one
whose first cell is a product code), and **have the agent report how many rows it
rejected and why**. The second number is the one that shows a filter that was too
aggressive.

## Long tables: paginated, scrolled or virtualised

Three different problems that look identical on the first screen, and each has
its own fix. They are the same three as in
[getting data out of a dashboard with no export button](dashboard-with-no-export-button.md),
which is the sibling page for the case where the table is in an internal tool.

The trap specific to tables: **a virtualised table destroys rows as you scroll
past them**, so the agent must accumulate as it goes and deduplicate on a key
rather than on position. That is
[its own page](deduplicating-what-an-agent-collects.md).

## The check that costs nothing

Tables usually state their own size, in a caption, a counter, or a pagination
control. Compare it against the number of rows you got, and compare a column sum
against a total the table prints if it has one.

A row count that matches and a sum that does not usually means a rounded display
value read as exact, which is the first failure on this page arriving at the end
of it.

## Short answers to the questions that lead here

**How does an AI agent read a table?** Ask for the HTML rather than the text: the
text read loses which column a value belonged to. Scope the read to the table on
a long page.

**Why are my columns shifted?** Usually a row header treated as data, or a
spanning header row that put values under the wrong name.

**Why do my numbers not add up?** Either a total row counted as data, or a
rounded display value where the exact one sits in a cell attribute.

**Why did I only get twenty rows?** Pagination, scrolling or virtualisation.
Check for a next control before assuming the table is short.

**Should I screenshot the table?** No. The structure is the content, and a
picture of a table is the one representation that keeps none of it.

**See also:**
[getting data out of a dashboard with no export button](dashboard-with-no-export-button.md)
for tables inside internal tools, and
[validating an AI agent's output](validating-an-agents-output.md) for the counts
that catch a partial read.

## Sources

- The relative cost of the four reads, including that HTML is 1.3x the text on a small page and the largest payload on a long one, is measured and sourced on [text, HTML, snapshot or screenshot](what-should-the-agent-read.md).
- The table failure modes are from reading real tables with this browser and are offered as experience rather than as a study. No site is named.

---

*Ask for the markup and scope it to the table. Most of the rest of this page is
what happens to people who asked for the text because it was cheaper.*
