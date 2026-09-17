---
title: "Giving an AI browser agent a stopping condition"
description: "Agents do not fail by stopping too early. They fail by not stopping. Four kinds of stopping condition, which ones a model can check for itself, and the two that have to live outside it."
parent: "Using the Agent"
nav_order: 48
---

# Giving an AI browser agent a stopping condition

Most tasks people write for a browser agent say what to do and never say when to
stop. The agent then stops for one of the wrong reasons: it runs out of context,
it runs out of your patience, or it decides on its own that something adjacent
counts as done.

A stopping condition is one sentence, and it belongs in the task rather than in
your head. There are four kinds, they fail differently, and two of them cannot be
enforced by the model at all.

## The four kinds

**The artifact.** Stop when a named thing exists. "Stop when the CSV has a row
for every company in the list." This is the strongest kind, because it is
checkable by looking at something outside the conversation, and because it
survives the agent losing the thread halfway.

**The state.** Stop when the page says something. "Stop when the page shows an
order number." Nearly as good, with one trap: pages say things in several ways,
and an agent that is looking for the word "confirmed" will keep going past a page
that says "thanks, we have your order".

**The budget.** Stop after N pages, N minutes, or N attempts. Weak on its own
because it says nothing about success, and essential as a backstop, because it is
the only one of the four that bounds a run that has gone wrong in an unanticipated
way.

**The question.** Stop and ask me. The right answer whenever the next step is
irreversible, costs money, or writes something public. It converts a failure into
a pause.

The useful combination is almost always **an artifact plus a budget**: what done
looks like, and how much you are willing to spend finding out.

## What the model can enforce, and what it cannot

An agent can check the first two kinds by itself, because both are things it can
observe. It reads the page, or it reads back the file it wrote.

It cannot reliably enforce the last two. A budget counted by the thing spending
the budget is a soft limit: a model that has decided it is nearly finished will
take one more page. And "ask me" only works if there is a channel to ask on,
which in a headless scheduled run there usually is not.

So the honest split is: **write all four into the task, and make sure at least
one of them is enforced from outside.** Outside means whatever is holding the
session, a timeout on the wrapper script, or a person watching. The tool calls
themselves already carry per-call ceilings, but a per-call timeout does not bound
a run that is making steady progress in the wrong direction.

## The failure this prevents, by name

The loop that costs money is not the agent that stops early. It is the agent that
has *nearly* succeeded and keeps trying variations: reload, try the other button,
scroll further, go back, try again. Each attempt is plausible on its own. There is
no page in the run that looks like a failure, and the whole thing is one.

This is the same shape as the retry behaviour described in
[agent retry loops trip rate limits, not fingerprints](agent-retry-loops-rate-limits.md),
seen from the other end: that page is about what the site notices, this one is
about what it costs you. A stopping condition is the cheapest fix for both, and it
is one sentence.

## Writing one that works

Bad, and extremely common:

> Find the pricing for these five products.

Better:

> Find the list price for each of the five products below and write them to
> prices.csv with a column for the product, the price and the URL you read it
> from. If a product's price is not visible without signing in, write "login
> required" in the price column and move on. Stop when the file has five rows.
> If you have visited more than fifteen pages, stop and tell me where you got to.

The second version has the artifact ("five rows in prices.csv"), the escape hatch
for the case that would otherwise cause a loop ("login required, move on"), and
the budget ("fifteen pages"). It is four sentences and it removes the three most
common ways this task fails.

The general shape of this, and why an explicit "what to do when you cannot" beats
any amount of instruction about trying harder, is in
[how to write a task an AI browser agent can follow](writing-tasks-for-an-ai-browser-agent.md).

## The escape hatch is the part people leave out

Every stopping condition needs a sibling: what to record when the condition
cannot be met. Without it, a task that says "stop when you have the price"
becomes unbounded the moment a price is genuinely not there.

Give the agent a way to write down "not available, and here is why" and the run
terminates on the hard cases instead of grinding on them. This is also the part
that makes the output useful: a file with five rows, two of which say why they are
empty, is a result. A run that ended because you killed it is not.

## Short answers to the questions that lead here

**How do I stop an AI agent from looping?** Give it an artifact to produce, a
budget in pages or minutes, and an explicit instruction for what to write when a
step is impossible. The third one is what actually breaks the loop.

**Why does my agent keep going after it has the answer?** Usually the task
described an activity rather than a result. "Research the competitors" has no end
state; "write five rows to competitors.csv" does.

**Can the agent enforce its own limit?** Partly. It can check for an artifact or a
page state. A count it enforces on itself is a soft limit, so put a hard one
outside the agent as well.

**What if the agent stops too early?** Almost always because the stopping
condition matched something weaker than you meant. Name the artifact precisely,
including how many of the thing you expect.

**See also:**
[when the page changes under the agent](when-the-page-changes-under-the-agent.md),
which is the other reason a run does not end the way you expected, and
[running one task across a list of sites](run-one-task-across-a-list-of-sites.md),
where a missing stopping condition multiplies by the length of the list.

## Sources

- This page is about how tasks are written rather than about a measurement, so it cites no external figure. The per-call ceilings it refers to are the ones this project's own MCP server applies to each tool call; the run-level bound it says you need is the one that does not exist there.

---

*Written after enough runs that ended by being killed rather than by finishing.
Every rule here is a sentence that would have prevented one of them.*
