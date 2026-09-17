---
title: "Deduplicating what an AI agent collects"
description: "Agents produce duplicates for four reasons that need four different fixes, and the one everybody reaches for first makes the data worse. Pick a key before the run, not after."
parent: "Using the Agent"
nav_order: 80
---

# Deduplicating what an AI agent collects

Any collection run longer than one page produces duplicates. They come from four
different places, they need four different fixes, and the instinct that handles
all of them at the end, deduplicate identical rows, is the one that quietly
damages the result.

## Where they come from

**Scrolling.** A virtualised or lazy list hands back a moving window, so
consecutive reads overlap and the same item arrives several times. This is the
most common source and the most benign.

**Pagination that is not stable.** A list sorted by recency, with new items
arriving while you walk it, pushes items across page boundaries. You see some
twice and **miss others entirely**, which is the part that matters: a duplicate
is visible and the gap it implies is not.

**The same entity on several pages.** A company in two categories, a product in
two collections. Genuinely one thing, legitimately encountered twice.

**Re-reading after a failure.** A retry that starts the page again appends what
it already had.

## Why deduplicating whole rows is wrong

Two rows for one entity are rarely identical. One read caught the price mid-update,
one has the description truncated differently, one was taken before a banner
loaded and has a stray line in a field.

Deduplicate on the whole row and all of those survive as separate entries,
because they differ. Every one of the four sources above produces near-duplicates
rather than exact ones, so the exact-match pass removes almost nothing and leaves
you believing it worked.

## Pick a key, before the run

The fix is to decide what makes two rows the same thing, and to record that field
deliberately:

- a stable id from the URL, which is the best key there is when it exists;
- the canonical URL, after redirects, with tracking parameters stripped;
- a natural key such as a reference number or a code;
- as a last resort, a normalised name plus one distinguishing field.

Put the key in its own column and deduplicate on it. Everything else can vary
between reads without confusing the count.

**The URL needs care.** The same item is reachable as `/item/42`,
`/item/42?from=list` and `/category/x/item/42`. Strip query parameters that are
not part of identity and take the final URL after redirects, which is also one of
the fields
[a run should log](what-a-run-should-log.md).

## Deduplicate while collecting, not at the end

Holding the keys you have already seen and skipping repeats as you go has three
advantages over a cleanup pass:

- **the count during the run is real**, so a stopping condition based on "fifty
  distinct items" works;
- **a run that dies halfway leaves a clean partial file**, which is the
  discipline in
  [running one AI agent task across a list of sites](run-one-task-across-a-list-of-sites.md);
- **the model stops re-reading detail pages it has already read**, which on a
  task that opens a page per item is most of the cost.

## Keep the duplicates you resolved

When two rows share a key, do not silently discard one. Record that it happened:
a count, or the URLs that resolved to the same key.

Twice for a single item is expected. Twenty times is a walk that looped, and the
only way to distinguish a well-deduplicated run from a broken one is to have kept
the number.

## The case where duplicates are the finding

Sometimes seeing the same entity twice is the answer rather than noise: a product
listed at two prices, a company appearing under two names, an event posted on two
dates.

So it is worth writing the task to say which of the two you are doing. "One row
per distinct product" and "one row per listing, including the duplicates" are
different jobs, and an agent left to decide will pick one per run. That ambiguity
is a special case of the general point in
[how to write a task an AI browser agent can follow](writing-tasks-for-an-ai-browser-agent.md).

## Short answers to the questions that lead here

**Why does my agent return the same item twice?** Usually scrolling: a lazy list
hands back an overlapping window on each read. Also unstable pagination,
cross-listed entities, and retries that restart a page.

**Why did deduplicating not remove them?** Because the rows are near-duplicates,
not identical. Deduplicate on a key rather than on the whole row.

**What makes a good key?** A stable id from the URL, the canonical URL with
tracking parameters stripped, or a reference number. A name alone is not one.

**Should I deduplicate during or after?** During. It keeps the running count
honest, keeps a partial file usable, and stops the agent re-reading pages it has
already read.

**Duplicates worry me more than they should?** They should worry you as a
symptom: unstable pagination produces duplicates and gaps together, and only the
duplicates are visible.

**See also:**
[normalising values across sites](normalising-values-across-sites.md), the
neighbouring problem of making rows comparable once they are distinct, and
[validating an AI agent's output](validating-an-agents-output.md) for the counts
that catch a walk that looped.

## Sources

- No external figures are cited. The four sources of duplicates are from running collection tasks with this browser and are offered as experience; the advice about keys is standard practice rather than a measurement, and inventing a number for either would not improve it.

---

*Pick the key before the run. Every other line here is a consequence of having
one, and the cleanup pass everybody writes afterwards is a consequence of not.*
