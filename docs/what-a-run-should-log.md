---
title: "What an agent run should log"
description: "Eight fields that turn a run you cannot explain into one you can, what to leave out, and the one line that makes a result reproducible six weeks later."
parent: "Using the Agent"
nav_order: 79
---

# What an agent run should log

An agent run produces an answer and a transcript. The transcript is long, hard to
search, and usually gone by the time somebody asks "where did this number come
from". A small log, written deliberately, answers that question in one line.

Here is the field list, why each one is there, and what to keep out.

## The eight fields

| field | why |
|---|---|
| **timestamp, UTC** | every other field is meaningless without when |
| **the final URL** | after redirects, not the one you asked for |
| **the value, raw** | exactly as the page said it, before any cleaning |
| **the value, normalised** | what you will actually use |
| **read or inferred** | whether the page stated it or the model concluded it |
| **the exit country** | pages vary by market, and yours is a fact about the run |
| **the identity seed** | so the same browser can be reconstructed |
| **outcome** | done, not found, blocked, error, needs a person |

The first six each prevent a specific argument. The seventh makes the run
repeatable. The eighth is the one people leave out and the one that makes a file
of results usable rather than a file of successes.

## Raw beside normalised, everywhere

This pattern runs through the whole corpus and it is the same reason each time:
the raw string is a fact and the normalised value is a judgement, and when the
judgement turns out wrong you want the fact still there.

It applies to prices, dates, statuses and addresses.
[Normalising values across sites](normalising-values-across-sites.md) is the
general case, and
[collecting event and course listings](collect-event-listings-with-an-ai-agent.md)
is where getting it wrong is most expensive, because a numeric date read in the
other order is wrong by up to eleven months and looks fine.

## Why the seed belongs in the log

The browser's identity is deterministic from a seed. Recording it means a run can
be reproduced with the same identity later, which matters when you are trying to
work out whether a site treated you differently today or you were simply somebody
else.

Without it, "it worked last week" is unfalsifiable. With it, the week-old run can
be repeated exactly. The setting and how a session picks one are on
[the MCP server page](mcp-server.md).

## What to leave out

**Credentials, obviously**, and also the things that arrive without being asked
for: your name, your email, the account identifiers a logged-in page prints. A
log is the artifact most likely to be shared, pasted into a ticket, or committed
by accident.

The habit that works is to log the fields above rather than page dumps. A whole
page read into a log file carries whatever the page was showing about you, which
is the problem described in
[secrets in an agent task](secrets-in-an-agent-task.md).

**The full transcript.** It is already somewhere, it is enormous, and it is not
searchable in the way this log is. Reference it if your client gives runs an id;
do not copy it.

## The line that makes it reproducible

Once per run rather than once per row: the task text, or a hash of it, and the
model that ran it.

Six weeks later the question is never only "what did the page say", it is "what
did we ask, and with what". A results file whose rows are perfect and whose
prompt is lost is a file nobody can extend, because nobody can produce more rows
the same way.

## Outcome needs more than two values

`done` and `failed` collapse cases that need different responses. The set that
earns its complexity:

- **done** with a value;
- **not found**, the page loaded and the thing is not there, which is a finding;
- **blocked**, the page would not serve, which is not about the data;
- **error**, the run broke, so retrying is reasonable;
- **needs a person**, a login, a code, an upload the agent
  [cannot do](uploading-a-file-with-an-ai-agent.md).

The difference between the second and the fourth is the important one. "Not
found" is an answer and "error" is the absence of one, and a file that scores
them the same is a file you will re-run entirely instead of re-running the eleven
rows that need it.

## Where this bites hardest

On list tasks. Forty rows, six of them empty, and no column saying why, is the
failure described in
[running one AI agent task across a list of sites](run-one-task-across-a-list-of-sites.md).
The log fields above are what turn those six into a to-do list instead of a
mystery.

## Short answers to the questions that lead here

**What should an AI agent run record?** Timestamp, final URL, raw value,
normalised value, whether it was read or inferred, exit country, identity seed
and an outcome from a small set.

**Why record the raw value as well?** Because the normalisation is a judgement
and will sometimes be wrong. The raw string is the only thing that lets you
redo it.

**Why log the seed?** So the run can be repeated with the same browser identity.
Without it you cannot tell whether the site changed or you did.

**What should never go in the log?** Credentials, and the personal data that
logged-in pages print into every read. Log fields, not page dumps.

**Is done/failed enough for an outcome?** No. "Not found" is a result and "error"
is the absence of one, and they need different responses.

**See also:**
[validating an AI agent's output](validating-an-agents-output.md), which is what
you do with the log once you have it, and
[extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md)
for the shape of the output file itself.

## Sources

- No external figures are cited: this is a field list and an argument for it. The seed and exit settings named here are this project's own, documented on [the MCP server page](mcp-server.md).

---

*Eight fields and one line per run. The test of whether it is enough: can you
answer "where did this number come from" without opening a transcript.*
