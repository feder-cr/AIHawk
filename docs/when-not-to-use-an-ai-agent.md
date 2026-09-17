---
title: "When not to use an AI browser agent"
description: "Seven cases where something else is better, with the reason in each. A page on this wiki arguing against its own subject, because the alternative is people finding out the expensive way."
parent: "Using the Agent"
nav_order: 75
---

# When not to use an AI browser agent

Conflict of interest, declared at the top: this is the wiki of a browser
automation tool. That is exactly why the list is worth writing down rather than
leaving to discovery, and several of the entries below have their own page here
recommending the alternative.

## 1. There is an API

The most common mistake and the least interesting. If the system exposes an
endpoint, use it: it is faster, it does not break when a layout changes, it
returns structured data, and it is supported.

A browser is what you reach for when the interface is the only interface. Using
one in front of a documented API is choosing the fragile path on purpose.

## 2. The page is static and the job is recurring

Reading the same stable page every morning is a job for a short script. The
selectors do not change, so there is no judgement to make, and paying a model to
re-decide the same thing daily is cost without benefit.

The pattern that works is a hybrid: use the agent **once** to find out where the
data lives and what the page demands, then have it help you write the twenty
lines that run every day.
[Getting website data into Google Sheets](website-data-to-google-sheets-ai-agent.md)
takes that route explicitly, and
[extracting data to a CSV](how-to-extract-data-to-csv-with-an-ai-agent.md) has the
cost curve behind it.

## 3. The task must be exactly right, every time

An agent is a stochastic reader. It is very good and it is not deterministic:
the same page twice can produce two slightly different readings, and on a long
run the variation compounds.

For anything where a wrong value is expensive rather than annoying, either the
job is a script, or the agent's output needs a verification step you actually
run. [Validating an AI agent's output](validating-an-agents-output.md) is that
step.

## 4. The action is irreversible and nobody is watching

Sending, buying, publishing, deleting, cancelling. The agent can navigate the
whole flow and the last click belongs to a person, for the reasons in
[keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md)
and, in its purest form, in
[cancelling a subscription with an AI agent](ai-agent-cancel-a-subscription.md).

The exception that proves it: irreversible actions are fine when a human confirms
each one, which is a different workflow rather than a caveat on this one.

## 5. A specialist tool exists and is better at it

Checking links is a link checker. Monitoring a page for a byte change is a
monitor and a `diff`. Load testing is a load tester. Filling one form once is
your hands.

Each of those does one job better than a general agent, and two of them have
pages here that open by saying so:
[finding the dead links on a site](find-dead-links-with-an-ai-agent.md) and
[monitoring a page for changes](how-to-monitor-a-page-with-an-ai-agent.md).

## 6. The volume is the point

Hundreds of requests to one host in a short window is a volume pattern, and it is
noticed regardless of how real the browser looks. If the value of the task comes
from doing it a thousand times quickly, a browser agent is both the slowest way
to do it and the one most likely to get the account looked at.
[Agent retry loops trip rate limits, not fingerprints](agent-retry-loops-rate-limits.md)
is the mechanism.

## 7. You cannot describe what done looks like

If you cannot write the sentence that says when to stop, the run will not stop.
This is less a category of task than a state of the requester, and it is worth
noticing before spending rather than after:
[giving an AI browser agent a stopping condition](giving-an-ai-agent-a-stopping-condition.md).

## And two where it is not a judgement call at all

**Uploading a file.** Not possible with this tool surface, measured and explained
in [its own page](uploading-a-file-with-an-ai-agent.md).

**Anything requiring a code from your phone, a hardware key, or a signature.**
Those are deliberately outside what any automation reaches, and the honest design
is a headed browser with you present.

## What is left, which is the actual case for the thing

After all that, the cases where a browser agent is the right tool are specific
and real: an interface with no API, a layout that changes often enough that a
script would need constant repair, a task done a handful of times rather than
continuously, one that needs reading and judgement rather than extraction, and
anything exploratory where you do not yet know what the page contains.

That is a narrower claim than "automate your browsing", and it is the one the
measurements on this wiki support.

## Short answers to the questions that lead here

**When should I not use an AI browser agent?** When an API exists, when the page
is stable and the job is daily, when exactness matters more than convenience,
when the action cannot be undone and nobody is watching, or when a specialist
tool already does that one job.

**Is an agent slower than a script?** For a repeated job, much. The browser
actions are quick; the model turns between them are not, and a script has none.

**Is it less reliable?** It is non-deterministic by nature. That is a feature on
a page you have never seen and a liability on one you have seen a hundred times.

**What is the hybrid everyone recommends?** The agent explores once and helps you
write the script; the script runs daily. You pay for judgement where judgement is
needed and nowhere else.

**So when is it right?** No API, changing layouts, low volume, judgement
required, or you do not yet know what is on the page.

**See also:**
[AI browser agents versus traditional scraping](ai-browser-agents-vs-traditional-scraping.md),
which runs the comparison with numbers, and
[browser problem or model problem](browser-problem-or-model-problem.md) for when
you have already chosen an agent and it is not working.

## Sources

- No external statistics are cited. Every claim here is either a design fact about this tool surface, measured on the page linked beside it, or an argument about task selection that would be worse with an invented number attached.

---

*Written for the wiki of the tool it argues against using. The seven cases are
the ones that come back, and every one of them is cheaper to read than to
discover.*
