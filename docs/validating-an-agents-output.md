---
title: "Validating an AI agent's output"
description: "Five checks that cost a minute and catch almost everything, ordered by how cheap they are. The last row matters more than the first, and two runs that agree still prove nothing."
parent: "Using the Agent"
nav_order: 82
---

# Validating an AI agent's output

An agent reading pages is a stochastic instrument pointed at a deterministic job.
It is very good and it is not exact, so the output needs a check, and the check
needs to be cheap enough that you actually run it.

Five, in order of cost. The first three are seconds.

## 1. Count against something the page told you

Most listings state their own size: "1,240 results", "page 3 of 17", "showing 20
of 400". Compare your row count against it.

A short count is truncation or an early stop, and it is the single most common
failure of a collection run. A read that came back clipped is one cause, and it
announces itself when it happens: measured on a long page, the default text read
returned 6,000 of 35,490 characters and said so in its own last line, per
[text, HTML, snapshot or screenshot](what-should-the-agent-read.md). A silent
short count usually means the walk stopped early instead.

## 2. Check the last row, not a random one

Spot-checking the middle is the natural instinct and the wrong one. Truncation,
timeouts and early stops all eat the **tail**, so the last row is where the
damage is, and the first rows are always fine.

Open the last row's URL and compare. Thirty seconds, and it catches the class of
failure that a sample of five in the middle never will.

## 3. Check the shape mechanically

Every line has the same number of fields; every number parses as a number; every
date falls in a plausible range; no cell contains a whole sentence where a value
belongs.

Column drift is the failure this catches: page one produces two columns, page
four contains a comma inside a title and produces three, and every subsequent row
is shifted. Any spreadsheet import that flags ragged rows does this for free.

## 4. Count the empties, and read them

How many rows have a raw value and no normalised one, and how many have an
outcome that is not "done".

This is the number that tells you whether the dataset answers the question. Two
awkward rows out of forty is a caveat; fifteen means the thing you are comparing
is not comparable, which is a finding rather than a defect, and it is only
visible if the agent was allowed to leave cells empty.
[Normalising values across sites](normalising-values-across-sites.md) is where
that instruction belongs.

## 5. Re-run a slice, not the whole thing

Take five rows and run them again. Disagreement between the two runs proves one
of them is wrong, which is worth knowing.

**Agreement proves less than it looks.** Two runs of the same model on the same
page share the same blind spots: if it misreads a label the first time, it will
usually misread it the same way the second. Two agreeing runs rule out flakiness
and say nothing about a systematic misreading.

For that, the only check is a human comparing a row against the page, which is
check 2 done deliberately rather than as a spot check.

## What none of these catch

**A correct extraction of the wrong thing.** The agent read the price accurately,
from the subscription option rather than the one-time one, on all forty sites.
Every check above passes: the count is right, the shape is right, the values
parse, the reruns agree.

Only a person looking at one page and one row together finds this, and it is
worth doing once at the start rather than at the end. Run the first row alone and
compare it against the page before releasing the list, which is the same
discipline as
[one form submission per spreadsheet row](one-form-per-spreadsheet-row.md).

## Build the checks into the task

Two of the five can be the agent's own job, and they are the two it is reliable
at because they are arithmetic rather than judgement:

> After finishing, state how many rows you wrote, what number the page said the
> total was, and how many rows you left empty and why. If those two numbers
> disagree, say so first.

That costs one sentence and it turns "here is your file" into a file with a
declared coverage. The remaining three stay with you, because they require
comparing against something the agent cannot see.

## Short answers to the questions that lead here

**How do I check an AI agent's extraction?** Count against the total the page
stated, open the last row, check the shape mechanically, count the empties, and
re-run a slice.

**Why the last row rather than a random one?** Because truncation and early stops
eat the tail. The first rows are always right.

**Do two agreeing runs prove it is correct?** No. They rule out flakiness. A
systematic misreading repeats identically, so agreement is not evidence against
it.

**What do the checks miss?** A correct reading of the wrong element, on every
row. Only comparing one row against the page by hand finds that.

**Can the agent check its own work?** The arithmetic parts, yes: row count
against the stated total, and a count of what it left empty. Ask for both in the
task.

**See also:**
[what an agent run should log](what-a-run-should-log.md), which is what these
checks read, and
[deduplicating what an AI agent collects](deduplicating-what-an-agent-collects.md),
because a row count is only meaningful once duplicates are resolved.

## Sources

- The truncation behaviour used in check 1, a default text read returning 6,000 of 35,490 characters with a line saying so, is measured and sourced on [text, HTML, snapshot or screenshot](what-should-the-agent-read.md).
- The five checks are practice rather than a study, and the page presents them as such.

---

*Checks one to three take a minute between them. Check five is the one people
reach for first and the one that proves the least.*
