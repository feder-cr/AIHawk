---
title: "Normalising values across sites"
description: "Forty sites describe a price forty ways. The two-column rule, the four fields that are ambiguous by construction, and why the normalisation belongs to you rather than to the model."
parent: "Using the Agent"
nav_order: 81
---

# Normalising values across sites

A list task returns forty answers and they are not the same kind of answer. One
price is monthly, one is annual-billed-monthly, one says "from", one is a range,
one is per seat, one says contact us. Averaging that column produces a number
that means nothing.

Normalisation is the step between collection and use, and most of the difficulty
is deciding where it happens.

## The two-column rule

Every field that needs interpretation gets two columns: **what the page said**,
verbatim, and **what you concluded**.

It costs nothing at write time and it is the difference between a dataset you can
repair and one you have to re-collect. When the interpretation turns out wrong,
and on a forty-site run it will be wrong somewhere, the raw column lets you fix
it with a pass over the file instead of forty page loads.

This is the same discipline as the source-and-confidence columns in
[filling a CRM record from a company's website](fill-a-crm-record-with-an-ai-agent.md)
and the raw-status column in
[checking order and delivery status](check-an-order-status-with-an-ai-agent.md).
It keeps recurring because it is the one habit that makes collected data
survivable.

## The four fields that are ambiguous by construction

**Dates.** `03/04/2026` is two different days and the string does not say which.
Take the reading from evidence on the page, the site's language, a long-form date
elsewhere, and record which evidence you used.

**Money.** Three questions, not one: which currency, what period, and whether tax
is included. A number without all three is not comparable to another number.
Symbols are ambiguous across countries, and the period is frequently in small
text next to the figure rather than in it.

**Quantities with units.** 500 g against 0.5 kg against "half a kilo". Decide the
canonical unit up front and store the original.

**Anything that was a dropdown.** "Medium", "M" and "Size 2" are the same
selection on three sites. This is the field where a normalised value is most
useful and most likely to be silently wrong.

## Where the normalisation should happen

**Not in the model, per row, during the run.** That is the tempting option and it
is the worst of the three: the rule is applied forty times by something that can
apply it slightly differently each time, and it is not written down anywhere you
can inspect.

**In the task, as an explicit instruction**, when the rule is simple and stated
once: "record the monthly price; if only an annual price is shown, record it
divided by twelve and note that you did". Now the rule is visible and uniform.

**In a pass over the file afterwards**, for anything harder. You have the raw
column, so a deterministic script can do it, you can read the rule, and it can be
changed without re-collecting.

The general principle: **the model reads, you interpret**. A model deciding
per row what "from EUR 9" means is a judgement repeated forty times with no
record; a rule applied to a column is one decision you can audit.

## Say what to do with the ones that do not fit

The failure that ruins these runs is an agent that will not return empty. Asked
for a monthly price on a page that says "contact us", it produces a plausible
number.

The instruction is one sentence and it belongs in every list task: **write the
raw string and leave the normalised column empty rather than inferring a value.**
Then the awkward rows are visible and countable instead of hidden among the good
ones. The general form of the escape hatch is in
[giving an AI browser agent a stopping condition](giving-an-ai-agent-a-stopping-condition.md).

## Count the unnormalised before you use the column

One number, and it is the honesty check on the whole dataset: how many rows have
a raw value and no normalised one.

Two out of forty is a usable column with a caveat. Fifteen out of forty means the
thing you are comparing is not comparable across these sites, and the right
response is to change the question rather than to fill the gaps. That is a
finding, and it is one you only get if the empty cells were allowed to stay
empty.

## Short answers to the questions that lead here

**How do I make data from different sites comparable?** Two columns per field:
the page's exact string, and your normalised value. Normalise in a pass over the
file, not per row inside the run.

**Why not let the model normalise as it reads?** Because it applies the rule
slightly differently each time and the rule is not written down. A rule applied
to a column is auditable and uniform.

**What do I do about "contact us" and "from EUR 9"?** Record the raw string and
leave the normalised cell empty. Never let the agent infer a number into it.

**Which fields go wrong most?** Dates, money, units, and anything that was a
dropdown. All four are ambiguous in the source, not in the reading.

**How do I know the column is usable?** Count the rows with a raw value and no
normalised one. A large count means the comparison itself does not hold.

**See also:**
[deduplicating what an AI agent collects](deduplicating-what-an-agent-collects.md),
the step before this one, and
[validating an AI agent's output](validating-an-agents-output.md), the step after.

## Sources

- No external figures are cited. The four ambiguous field types and the two-column rule are practice from running list tasks with this browser, and the page says so rather than dressing them in a statistic.

---

*The model reads, you interpret. If you remember one line from this page, that is
the one, and the two-column rule is just what it looks like in a file.*
