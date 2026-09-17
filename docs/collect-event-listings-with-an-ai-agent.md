---
title: "Collecting event and course listings with an AI agent"
description: "Dates are where this task fails, not navigation. The one field that is ambiguous by construction, the structured data most listing pages already publish, and what a recurring event does to your rows."
parent: "Using the Agent"
nav_order: 64
---

# Collecting event and course listings with an AI agent

Conferences, meetups, training courses, exhibitions, club fixtures: the same
shape everywhere. A list page, a card per event, a detail page with the real
information, and a set of dates that will quietly ruin your spreadsheet.

Navigation is the easy part. Dates are the job.

## Check for structured data before you read anything

Listing pages are one of the few categories where the site frequently hands you
the answer in machine form. Event pages often embed a JSON block describing the
event: name, start and end in ISO format with an offset, location, organiser,
sometimes price and availability.

When it is there, take it, and use the rendered page only to confirm. It is
unambiguous, it has the time zone in it, and it solves by itself most of what the
rest of this page is about.

Read the markup rather than the text to find it, since it lives in a script
element and the text view will not show it. That is 1.3 times the cost of plain
text, which is
[measured](what-should-the-agent-read.md).

When it is absent, you are reading dates off a page written for humans, and the
following applies.

## The date field that is ambiguous by construction

`03/04/2026` is the third of April or the fourth of March. There is no way to
tell from the string, and both readings are common depending on the site's
audience. An agent will pick one, consistently and invisibly, and half your rows
will be wrong by up to eleven months.

Three rules, and the first is not optional:

- **Store the raw string exactly as the page showed it**, in its own column,
  always. When you find out the mapping was wrong you can re-derive; without it
  the data is gone.
- **Take the interpretation from the page, not from the agent.** The site's
  language, its country domain, a long-form date elsewhere on the same page
  ("4 March 2026") all settle it. Have the task say what it used.
- **Record the time zone or record that there is not one.** An event at 18:00
  with no zone is not a time, and treating it as your own local time is a guess
  that will be wrong for anything international.

## Recurring events break the one-row-per-thing assumption

A weekly class is one page and thirty occurrences. A conference is one event and
four days. A course runs three times this year from the same listing.

Decide before you start which one is a row: the *listing* or the *occurrence*.
Both are legitimate and they answer different questions. What is not legitimate
is letting the agent decide per page, which is the default and produces a file
where some rows are series and some are instances, with nothing to distinguish
them.

If occurrences are the row, add a column for the listing they came from so the
two views are recoverable from one file.

## The list page is a summary and it is often wrong

Cards on a list page are frequently stale or truncated: a price that has changed,
a venue that says "London" when the detail page says the actual address, a
"sold out" flag that has not updated, a title cut at forty characters.

So: **the list page is for finding, the detail page is for reading.** It costs one
navigation per event, which is a page load and not much else, and it is the
difference between a dataset and a set of teasers.

The exception is when you are only counting, or only need titles and links, in
which case the list page is fine and you should say so deliberately rather than
by omission.

## What to capture

- title, raw date string, parsed start, parsed end, time zone or "none stated";
- whether the date interpretation was confirmed by something on the page, and by
  what;
- venue as written, and online or in person;
- price as written, and free or paid, with the currency;
- whether registration is open, closed, waitlisted, or not stated;
- the detail URL, and the date you read it.

The pattern of a raw column beside a parsed column runs through all of these, and
it is the same discipline as everywhere else in this corpus: keep the fact, keep
the judgement, keep them apart.

## Pace it, and do not register for anything

Listing sites are often small, run by volunteers or a single organiser, on modest
hosting. A crawl of four hundred detail pages at full speed is discourteous
regardless of what any policy says, and it is the volume pattern described in
[agent retry loops trip rate limits, not fingerprints](agent-retry-loops-rate-limits.md).

And keep the agent read-only. Registering, joining a waitlist or reserving a place
takes something from a real person if it is wrong, and it belongs behind the
confirmation step in
[keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md).

## Short answers to the questions that lead here

**How do I scrape event dates reliably?** Look for the structured event data
first; most listing sites publish it and it carries an unambiguous start with an
offset. Failing that, store the raw string and derive the interpretation from
evidence on the page.

**How do I handle a recurring event?** Decide up front whether a row is the
listing or the occurrence, and if it is the occurrence, keep a column pointing
back to the listing.

**Should I read the list page or each event page?** Each event page, unless you
only need titles and links. List cards are routinely stale or truncated.

**Why are some of my dates a month out?** A numeric date read in the other order.
This is why the raw string has to be stored in its own column.

**What about time zones?** Record the one stated, or record that none was. An
online event with no zone is not a time, and assuming your own is wrong for
anything cross-border.

**See also:**
[running one AI agent task across a list of sites](run-one-task-across-a-list-of-sites.md)
for the partial-results discipline a long collection needs, and
[extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md)
for the output format.

## Sources

- The relative cost of reading markup against plain text is measured and sourced on [text, HTML, snapshot or screenshot](what-should-the-agent-read.md). The structured-data block this page recommends looking for lives in a script element, which is why the text view cannot see it.
- The failure modes are from collecting listings with this browser and are offered as experience. No listing site is named.

---

*Every rule here is really the same rule: keep what the page said and what you
concluded in different columns. On dates it is the difference between a dataset
and a plausible one.*
