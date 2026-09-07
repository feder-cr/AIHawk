---
title: "Extracting data to a CSV with an AI agent"
description: "What to say, what the agent actually does underneath, where a scripted scraper wins instead, the failure modes - truncation, drifting columns, cost - and how to verify the output."
parent: "Using the Agent"
nav_order: 6
---


# Extracting data to a CSV with an AI agent

The instruction is one sentence: "go to this page, pull every item's name and
price into a CSV." The agent reads the page's structure, walks the pagination
if there is any, and hands you the rows. That part genuinely works. The rest of
this page is what most write-ups skip: what actually happens underneath, why
cost grows faster than page count, the specific ways extractions go quietly
wrong, and why you never ship an extraction you have not spot-checked.

The running example is [books.toscrape.com](https://books.toscrape.com/), a
sandbox built for exactly this practice: 1,000 fictional books, 20 per page
across 50 pages, each with a title, a price and a stock line. Practice there or
on a page you serve yourself; the mechanics transfer, the risk does not.

## What you actually say

A working instruction, typed into the AIHawk interface or handed to your
assistant with AIHawk's browser attached:

> Go to https://books.toscrape.com/. For each book on the first two pages,
> extract the title and the price. Reply with CSV only: a header line
> `title,price`, one line per book, no commentary before or after.

Four choices in there do most of the work:

- **Name the columns.** A model left to choose its own schema chooses a
  slightly different one next run; a named header line is a contract.
- **Say "CSV only, no commentary."** Models wrap answers in prose by default,
  and prose in the middle of a redirected file is a broken file.
- **Bound the scope.** "The first two pages" is a budget. "Every page" on a
  50-page catalog is a long, expensive walk that may not finish in one run.
- **Point at the region when the page is busy.** On a page with sidebars and
  banners, "the product list in the main column" saves the agent from reading,
  and you from paying for, everything else.

One mechanical fact, early: the agent has no file-writing
tool. The browser tools navigate, read, click and type; the CSV materializes as
the model's final answer, nothing else. From the interface you copy it out of
the chat. For the RECURRING extraction, where the selectors are stable and
no judgment is involved, the honest tool is a script on the same engine -
[the Google Sheets page](website-data-to-google-sheets-ai-agent.md) carries
one, executed, that prints CSV to stdout.

## What happens underneath

The loop is the same one [the explainer](ai-web-agent-explained.md) describes:
observe, decide one action, repeat. The agent navigates, then reads the page,
with a text read or a structural snapshot, and the values it extracts live in
the conversation transcript, not in any database. On a page that fits in one
read, extraction is a handful of turns. With pagination, each further page is
another cycle: find the next control, click it, read again, keeping the
accumulating rows straight in a growing transcript.

That transcript is where the cost curve hides. Every turn resends the entire
conversation so far to the model, so page ten is priced with pages one through
nine still in the context. A 20-page walk is not twenty times the cost of one
page; it is worse, because the pages ride along. The comparison page
[runs the actual numbers](ai-browser-agents-vs-traditional-scraping.md).

Two hard limits in AIHawk's own loop, taken from its source, bound one run:

- **Tool results are clipped at 8,000 characters** before the model sees them.
  A 20-item page fits comfortably; a page listing hundreds of items may not.
- **The final reply has a token ceiling** (8,192 tokens). Around a thousand
  rows, the CSV itself outgrows the answer that is supposed to carry it.

What is not limited is how long a run goes on. The loop has no turn ceiling: a
50-page walk will not be cut short part way, it will keep going, one page at a
time, until it answers or you stop it.

That makes the batching habit more useful rather than less. "Pages one to ten,
then stop" completes, is cheap to verify, and is short enough to watch. "All
fifty pages" is a run whose cost per row climbs the further it gets, because
every turn resends the whole transcript, and a long run is exactly the one you
stop paying attention to - which matters, because attention is what ends a walk
that has gone wrong.

## Where this beats a scraper, and where it loses

The honest comparison has [its own page](ai-browser-agents-vs-traditional-scraping.md);
the extraction-specific summary: the agent wins when the task is small,
one-off, or needs judgment a selector cannot express - twenty differently-built
pages, a "category" column that requires reading the item, a layout that changed
last week and will change again. You state intent once and pay cents.

The scraper wins on volume and repetition, and it is not close. The 1,000 books
of the example are a few lines of deterministic code that run in seconds, cost
nothing per run, and produce the same bytes every time. If you will extract the
same shape from the same site more than a handful of times, the strongest
pattern is the hybrid: use the agent once to discover where the data lives,
then let it help you write the script that does the repeated runs.

## The failure modes, specifically

Extractions rarely fail loudly. These are the quiet versions to expect:

- **Truncation on long lists.** An over-full page arrives clipped at 8,000
  characters, and the model extracts what it received, confidently: output
  that looks complete and is short. Defense: keep reads narrow ("read the
  product list, not the page"), and check counts, below.
- **Columns drifting between pages.** Page one yields `title,price`; page four,
  where a title contains a comma or a price is missing, yields quoted fields or
  an improvised extra column. Each page is a fresh decision, and fresh
  decisions drift. A named header and "exactly two columns on every line" in
  the instruction hold it down; a per-line check afterwards catches what
  slipped.
- **Declared success, early.** The model finishes page three of five, sees a
  plausible pile of rows, and answers: partial output, delivered with
  confidence.
- **Invented or repaired rows.** Rare on clean pages, real on messy ones: a
  missing price becomes a guessed one because the model would rather complete
  the row than break the schema. Say so explicitly: "if a value is missing,
  write an empty field, do not infer it."
- **Cost growth.** Not wrong output, just a bill: retries and long walks
  multiply turns, and turns carry the whole transcript. If a run wanders, stop
  it and re-scope rather than letting it find its way.

If the page never loads at all, or loads empty, that is not an extraction
problem; work through [why agents get blocked](why-does-my-ai-agent-get-blocked.md)
before touching the prompt.

## Verify the output, every time

Never trust an extraction unseen. The checks are cheap and mechanical:

1. **Count.** The site usually tells you the truth to check against: the
   example catalog says 1,000 results, 20 per page, so two pages should be 40
   rows plus a header. `wc -l` settles it in a second; a short count is
   truncation or an early stop, caught cheap.
2. **Spot-check rows by hand.** Pick a few, including the last one, and compare
   them against the live page. The last row matters most: truncation and early
   stops eat the tail, not the head.
3. **Check the shape.** Every line has the same number of fields; every price
   parses as a number. A spreadsheet import that flags ragged rows catches
   column drift.
4. **Run it twice if it matters.** Two runs that agree do not prove
   correctness, but two runs that disagree prove one of them is wrong.
   (AIHawk's `--seed` pins the browser's identity across runs, not the model's
   choices, so agreement is evidence, not a guarantee.)

The checks are the price of using a stochastic reader for a deterministic job,
and they are still far cheaper than writing the scraper, right up until the day
they are not, which is when you write it.

## Short answers to the questions that lead here

**Can an AI agent export scraped data to a CSV?** Yes: describe the columns and
the scope, and the CSV comes back as the agent's answer, which you copy or
redirect to a file. There is no file-writing tool; the answer text is the
deliverable.

**How do I get only CSV, with no explanation around it?** Say exactly that:
"reply with CSV only, header `title,price`, no commentary before or after."
Named columns and an explicit no-prose clause are the two highest-value lines
in the instruction.

**Why is my extracted CSV incomplete?** Three usual causes: a long page
truncated before the model saw all of it, an early "done" before the last
pages, or a run stopped mid-walk. Counting rows against the site's own total
finds all three; batching into smaller runs prevents them.

**Can it handle pagination?** Yes, by walking it: find next, click, read,
repeat, with cost per page climbing as the transcript grows. Bound the walk
("pages one to ten") and concatenate batches.

**Is an agent cheaper than writing a scraper?** For one-off and small jobs,
usually, because the scraper's real cost is engineering time. For repeated
volume, no, and it is not close; the crossover math is on
[the comparison page](ai-browser-agents-vs-traditional-scraping.md).

**How do I know the data is right?** You check: row count against the site's
stated total, a few hand-compared rows including the last, and a
same-field-count pass over every line. An unverified extraction is a guess
with a header row.

## Sources

All retrieved 2026-09-03, except the loop's own bounds, re-read 2026-09-08.

- [books.toscrape.com](https://books.toscrape.com/), the scraping sandbox used
  as the running example: 1,000 fictional items, 20 per page, with the site's
  own disclaimer that prices and ratings are randomly assigned.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its README and
  source in this repository: the loop, its lack of a turn ceiling, the
  8,000-character tool-result clip and the reply ceiling are in
  [`src/aihawk/agent.py`](https://github.com/feder-cr/AIHawk/blob/main/src/aihawk/agent.py),
  and the CLI surface in
  [`src/aihawk/cli.py`](https://github.com/feder-cr/AIHawk/blob/main/src/aihawk/cli.py).

A complete worked run of this task shape, with the real transcript, the two
screenshots the session returned and the 32-row CSV it produced, is in the
repository:
[extracting a category to CSV](https://github.com/feder-cr/AIHawk/tree/main/articles/extracting-a-category-to-csv).

**See also:** [AI browser agents vs traditional scraping](ai-browser-agents-vs-traditional-scraping.md),
[monitoring a page for changes](how-to-monitor-a-page-with-an-ai-agent.md),
[what is an AI web agent?](ai-web-agent-explained.md), and the rest of
[Using the Agent](guides-using-the-agent.md).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The verification
section is not boilerplate: the maintainer counts the rows every time, because
the unchecked extraction is the one that ships wrong.*
