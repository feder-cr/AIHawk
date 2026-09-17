---
title: "One form submission per spreadsheet row, with an AI agent"
description: "The task where a mistake repeats two hundred times before anybody looks. The typing bill, the two-pass design, the idempotency column, and why the first row runs alone."
parent: "Using the Agent"
nav_order: 58
---

# One form submission per spreadsheet row, with an AI agent

Take a spreadsheet, submit one web form per row. It is the oldest office
automation task there is, and it is the one where an agent's mistakes are most
expensive, because the run repeats them at machine speed with nobody reading.

Three things decide whether this works: what it costs, how you recover, and how
you stop a bad run at row one instead of row two hundred.

## Know the bill before you start

Typing is the dominant cost and it is not close. Measured on this browser, a
field costs roughly **one second plus 270 ms per character**, with the full
numbers on
[how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md).

So a form with a name, an email, a company and a short message, say 120
characters across four fields, is about **36 seconds of typing** plus four
seconds of field overhead plus a second for the submit. Call it 45 seconds a row
before page loads and before the model thinks.

Two hundred rows is two and a half hours. That is a fine answer if you expected
it and an unpleasant surprise if you budgeted by the number of rows rather than
by the number of characters. **Count characters, not fields.**

The reason typing is paced rather than instant is in that page too: a field that
fills instantly with no inter-key variation is one of the cheapest things for a
page to notice, so the cost buys the thing you came for.

## The idempotency column, which is the whole recovery story

Add a column to the spreadsheet, and have it updated after each successful
submission with the timestamp and whatever the page gave back as a confirmation.

The updating is done by your client rather than by the browser: this tool surface
reads and acts on pages and has no save-file tool, so the file work belongs to
whatever you are driving from. That division, and the ceilings it imposes on a
long run, are in
[extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md).

That single column gives you:

- **Resume.** A run that dies at row 83 restarts by skipping rows that have a
  value.
- **Proof.** A reference number per row, so "did this one go through" is a
  lookup rather than an argument.
- **Duplicate protection.** The instruction "skip any row that already has a
  confirmation" is what stops a rerun from submitting everything twice, and a
  double submission is the most common real-world damage from this task.

Without it, a failed run leaves you with a spreadsheet and no idea which half of
it is already in the other system. That is worse than not having run it.

## Run row one alone, and look at it

Before releasing the list, submit exactly one row and go and look at the result
in the destination system. Not the agent's report of the result: the record
itself.

This catches the class of error that is invisible from the browser side and fatal
at scale: a field that silently truncated, a date the form parsed as
month-first, a dropdown that defaulted because the value did not match an option,
a required field that was optional-looking and got left blank.

Every one of those produces a successful submission and a wrong record. The agent
has no way to know, because the page said thank you.

## What goes wrong in the fields themselves

**Dropdowns.** A select needs the option's value, not the label you have in the
spreadsheet. "United Kingdom" in your column may be `GB` in the form. Decide the
mapping before the run, and have the agent record the option it actually chose,
not the one it intended.

**Dates.** The same eight characters mean two different days depending on the
form's locale. Write the format you expect into the task and have the agent read
back the field after filling it.

**Fields that reformat as you type.** Phone numbers and card-shaped inputs insert
their own separators, so what you typed and what is in the field differ. Read
back rather than assume.

**Fields that appear conditionally.** Choosing a country reveals a state
dropdown. A task written against one row's shape breaks on a row with a different
country, and the failure looks like a missing element.

The general principle behind all four: **read the field back after filling it**,
before submitting. It is a free read, and it converts four silent corruptions
into four visible errors.

## A task that works

> Open the form at the URL below once and keep the session. For each row of
> rows.csv where the "submitted" column is empty:
>
> Fill the fields from the row. After filling each one, read it back and check it
> matches what you intended. If any field does not match, write the difference
> into the "submitted" column, prefixed with "MISMATCH:", and move to the next
> row without submitting.
>
> Otherwise submit, wait for the confirmation to appear, and write the date and
> the confirmation text into the "submitted" column. Never submit a row that
> already has a value in that column.
>
> Stop and tell me if three consecutive rows fail.

## The part that is not technical

A form that submits two hundred times in two hours sends two hundred notifications
to whoever is on the other end. If that is your own system, fine. If it is
somebody else's, the volume is the thing they will notice and the thing they will
mind, and the mechanism is the one in
[agent retry loops trip rate limits, not fingerprints](agent-retry-loops-rate-limits.md).

Pace it, and if the task is contacting people rather than filing records, the
question of whether to send two hundred of anything is a separate one that a
browser does not answer.

## Short answers to the questions that lead here

**How long does it take to fill a form with an AI agent?** About a second per
field plus 270 ms per character, plus page load and model turns. Budget by total
characters, not by row count.

**How do I stop it submitting twice?** A column the agent writes a confirmation
into, and an instruction never to touch a row that already has one. Nothing else
survives a rerun.

**Why is the data wrong in the destination but the agent said success?** A
silently truncated field, a mismatched dropdown, or a date parsed in the other
order. Read every field back before submitting and run the first row alone.

**Can I skip the read-back to go faster?** The read costs a hundredth of a
second. It is not where the time is.

**The form changes depending on what I pick.** Expect it: conditional fields are
normal. Write the task against the branches you have in the data, not against one
example row.

**See also:**
[getting an AI agent to fill out forms](ai-agent-fill-out-forms.md) for the
single-form version and the mechanics of each control type, and
[keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md),
because submit is irreversible and this task does it in a loop.

## Sources

- The typing cost model, about one second fixed plus 270 ms per character, is measured and sourced on [how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md): 1.87 s for 3 characters, 3.93 s for 12, 12.63 s for 43.
- The field-level failure modes are from running forms with this browser and are offered as experience.

---

*Run row one alone and go and look at the record. It is thirty seconds and it is
the only step here that catches the mistakes the browser cannot see.*
