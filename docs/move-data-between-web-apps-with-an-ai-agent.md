---
title: "Move data between two web apps with an AI agent"
description: "Moving data between two web apps with an AI agent: the read-transform-write-confirm loop, batching, the row that does not fit, and an audit log a human can check."
parent: "Using the Agent"
nav_order: 28
---


# Move data between two web apps with an AI agent

When neither app has an API, an AI agent can move data between them: read each row on the source, transform it, type it into the target, then read the target back to confirm the write landed. It suits a few hundred rows, not a pipeline; where both sides have an API, the API always wins.

## When this is actually the right tool

An agent earns its keep in three situations: neither app has an API (common on internal tools and smaller products), an API exists but sits behind a plan nobody pays for, or the job is a one-off, a few hundred rows moving from an export into a new system, not a recurring feed.

Outside those three, do not reach for an agent. If both apps expose an API, call it: a request succeeds or fails as a whole and costs a fraction of a model call. If the target is a spreadsheet rather than a second app, [getting website data into Google Sheets](website-data-to-google-sheets-ai-agent.md) covers that easier, more common case.

## The shape of the task: read, transform, write, confirm

The task is four repeating stages: read a row from the source, transform its values into the shape the target expects, write it into the target's own form, then read the target back to confirm what landed. [Extracting data to a CSV](how-to-extract-data-to-csv-with-an-ai-agent.md) covers the first stage alone; [getting an agent to fill out forms](ai-agent-fill-out-forms.md) covers the third; this task chains both, plus the confirmation neither needs alone.

The transform stage is where migrations quietly go wrong. A source column named "full name" becomes "first" and "last" on the target. A date stored as "03/14/2026" needs to become "2026-03-14".

State the field mapping explicitly, one line per field, rather than trusting the model to guess a correspondence; a guessed mapping is the same wrong-value-in-wrong-field failure [the forms page](ai-agent-fill-out-forms.md) describes for filling alone.

## Why the agent should verify what it wrote, not trust the submit

A submit button returning a success page is not evidence the row landed the way you meant it to. Target apps silently drop fields they do not recognize, truncate a string past a length limit, or apply a default when a required field arrives empty. None of this produces an error the agent would see; it produces a saved row that looks fine and is not.

The fix costs one more step per row. After the write, have the agent reload the record on the target and read back the fields that matter, then compare them to the transformed source values. Two or three fields are usually enough, chosen from the ones that would hurt if wrong: dates, identifiers, anything with a length limit.

## Batching and pacing

Batch the run and stop between batches; do not ask for the whole migration in one instruction. AIHawk's own loop has no turn ceiling, so "all of them" will not be cut off part way - it will simply run on, and that is the problem rather than the reassurance it sounds like. One full read-transform-write-confirm cycle is several turns, every turn resends the whole transcript, so the cost per row climbs the longer the batch runs; and a long unattended run is the one where a bad mapping writes forty wrong rows before anyone looks. "The next twenty rows, then stop" is short enough to read the log before the next twenty start.

Writing dozens of rows back to back is also the kind of steady, gap-free rhythm that gets a session rate-limited or logged out mid-batch. The order-of-checks for a session that stops responding is on [why does my AI agent get blocked](why-does-my-ai-agent-get-blocked.md), and a short pause between batches, not only within one, is the cheapest fix; [agent retry loops and rate limits](agent-retry-loops-rate-limits.md) covers what happens when a failed write gets retried instead of paused.

## The row that does not fit

Some row will not fit the target's rules: a required field the source never populated, a value the target's validation rejects, a duplicate it refuses outright. Decide the policy before the first row runs, or the agent invents one, often "guess a plausible value," which is worse than skipping the row.

Three policies work: skip the row and log why, needing a human pass over the skipped list afterward; stop the whole batch at the first failure, safest and slowest; or write the row with the problem field left empty and flagged, which keeps the count moving. State the policy in the instruction itself: "if a required field is missing, skip the row and note it, never invent a value" is worth one sentence.

## Keeping a log a human can audit

The deliverable of a migration like this is not only the rows that landed; it is a record of what happened to each one. Ask the agent to log, per row: the source identifier, the transform applied, the target's confirmation (an ID, or "confirmed by read-back"), and the outcome: written, skipped, or failed.

A plain text or CSV log next to the moved data turns "trust the agent ran" into "read forty lines and see exactly what it did." [Verifying the output](how-to-extract-data-to-csv-with-an-ai-agent.md) applies here twice: once per row during the run, and once more across the whole log before the migration is called done; that final check is a human's job.

## Short answers to the questions that lead here

**Can an AI agent migrate data from one system to another?** Yes, for a bounded job: it reads each row on the source, transforms it, types it into the target, and reads the target back to confirm the write. It is not a substitute for an API integration where one is available on both sides.

**How do I know the data was actually written correctly?** By having the agent read the target back after each write and compare the fields that matter to the source, rather than trusting a success message. A saved row that looks fine can still be missing a field the target quietly dropped.

**What happens if a row does not fit the target's format?** Whatever policy you stated in the instruction: skip and log it, stop the batch, or write it with the bad field flagged. Without a stated policy the agent tends to invent a value to make the row fit, which is the outcome to avoid.

**See also:** [getting an agent to fill out forms](ai-agent-fill-out-forms.md), [extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md), and [getting website data into Google Sheets](website-data-to-google-sheets-ai-agent.md).

## Sources

- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its source in this repository (`src/aihawk/agent.py`), retrieved 2026-09-05 and the loop re-read 2026-09-08, for what the batching section above rests on: a loop with no turn ceiling, and the whole transcript resent on every turn.

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. A success message and a correctly saved row are two different facts, and the read-back-to-confirm step exists because only one of them is worth trusting.*
