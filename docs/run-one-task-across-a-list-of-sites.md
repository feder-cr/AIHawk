---
title: "Running one AI agent task across a list of sites"
description: "The same task on fifty sites is not fifty times one site. What changes at scale: partial results, one session or fifty, the per-site failure budget, and where the time actually goes."
parent: "Using the Agent"
nav_order: 52
---

# Running one AI agent task across a list of sites

"Check the pricing page of these forty companies" is the most requested shape of
browser-agent work and the one that most often produces nothing usable. The task
is fine on one site. The list is what breaks it, and it breaks in ways that have
nothing to do with the task.

## The arithmetic you should do first

Start from the per-step numbers, which are
[measured elsewhere](how-long-an-ai-agent-takes-per-step.md): a browser starts in
about five seconds, a navigation and a couple of reads are hundredths, a click is
about a second, and typing is about a second plus 270 ms a character.

For a read-only task, forty sites is roughly: one browser start, forty
navigations, and forty to eighty reads. The browser side is well under a minute
in total. **Every remaining second is model turns and page load.**

That result is the useful one, because it tells you where the knob is. Making the
browser part faster buys you nothing. Reducing the number of model turns per site
buys you everything, and the way to do that is a task specific enough that one
look answers it.

## One session or one per site

The default instinct is a fresh browser per site, for cleanliness. It costs about
five seconds each, so forty sites is three and a half minutes of pure startup
against five seconds for a single session.

Use one session when the sites are unrelated and you are only reading. Use a
fresh one when state must not leak between items: different logins, a cart, a
consent choice you do not want carried, or anything where site A's cookie would
change site B's behaviour.

There is a third option people miss, which is one session with a clean context per
item. It keeps the process warm and throws away the state, which is the
combination most list tasks actually want.

## Partial results are the whole game

On a list of forty, some number will fail. A page will be down, a layout will be
unusual, a consent wall will be unfamiliar, a site will be slow today. **The
question is not how to prevent that. It is what the run leaves behind when it
happens.**

**First, be clear about who writes the file, because the browser does not.** This
tool surface navigates, reads, clicks, types and screenshots: there is no
save-file tool in it, and what the browser returns is text in the conversation.
The file gets written by the client you are driving from, if it has tools for
that, which an editor or coding assistant generally does and a plain chat window
does not.
[Extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md)
sets out that division, including the ceilings a long run hits when the rows have
to fit in an answer.

With that established, the difference between a useful run and a wasted one:

- **Write each result as you get it**, not at the end. A run that dies at item
  thirty-one with nothing on disk has produced nothing; one that dies with thirty
  rows written has produced thirty rows.
- **Give failure a value.** Every item gets a row, including the ones that did not
  work, with a short reason in place of the answer. A file of forty rows where
  eight say "no pricing page found" is a result you can act on. A file of
  thirty-two rows is a mystery.
- **Never let one item stop the list.** The instruction has to say so explicitly,
  because the natural behaviour of a model that hits a wall is to keep trying.

This is the list-shaped version of the escape hatch in
[giving an AI browser agent a stopping condition](giving-an-ai-agent-a-stopping-condition.md),
and at list scale it is not a nicety: a missing escape hatch on a forty-item run
is a forty-fold multiplier on your worst case.

## The per-item budget

Give each item its own ceiling, in pages or in attempts, separate from the run's
ceiling. Without it, one pathological site consumes the budget of the whole list,
and the items after it never get looked at.

A shape that works:

> For each company in the list, open its site and find the page that shows
> pricing. Write one row per company to pricing.csv with the company, the lowest
> listed price, and the URL. If you cannot find a pricing page within five pages
> on that site, write "not found" in the price column with the last URL you tried,
> and move to the next company. Do not go back to a company you have already
> written a row for.

The last sentence is not decoration. Revisiting is the most common way these runs
loop, because a model that finishes the list and is dissatisfied will start over
on the ones it marked "not found".

## What changes when the task writes rather than reads

Everything above assumes reading. A list task that submits, sends or buys is a
different risk class, because a bug that would waste one run now repeats forty
times before anybody notices.

Two rules, and they are cheap: **run the first item alone and look at the result**
before releasing the list, and put the confirmation step from
[keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md)
in front of the action rather than in front of the run. A run-level confirmation
approves forty actions you have not seen.

## Sites will not be comparable, and that is a content problem

The quiet failure of list tasks is not technical. Forty companies describe their
prices in forty ways: per seat, per month billed annually, "from", on request,
in a comparison table, behind a currency selector. An agent asked for "the price"
returns forty numbers that are not the same kind of number.

Say what to record when the answer is shaped differently, and record the raw
string alongside whatever you normalised it to. Both of those are one extra
column and they are the difference between a spreadsheet you can use and one you
have to redo by hand.

The related trap, where the same page shows different prices depending on where
the request comes from, is
[seeing a page from another country](see-a-page-from-another-country.md).

The two steps that turn a pile of rows into a comparable table have their own
pages:
[normalising values across sites](normalising-values-across-sites.md) for the
raw-beside-normalised rule, and
[deduplicating what an AI agent collects](deduplicating-what-an-agent-collects.md)
for picking a key before the run rather than cleaning up after it. What to record
per row while it happens is
[what an agent run should log](what-a-run-should-log.md).

## Short answers to the questions that lead here

**Should I open a new browser for each site?** Only if state must not leak. A
fresh browser costs about five seconds each, so forty of them is three and a half
minutes of startup you do not need for a read-only task.

**How do I stop one bad site from killing the run?** A per-item ceiling plus an
explicit instruction to write a reason and move on. Both must be in the task; the
model will not supply them.

**Why did my agent redo items it had already done?** Almost always a missing "do
not revisit a company you have written a row for". A dissatisfied model starts
over.

**Where does the time actually go on a list task?** Model turns and page loads.
The browser actions themselves are seconds in total across dozens of sites.

**How do I make the results comparable?** Record the raw string as well as the
normalised value, and say in the task what to do when the answer is shaped
differently from what you asked for.

**See also:**
[extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md)
for the output side of this, and
[when the page changes under the AI agent](when-the-page-changes-under-the-agent.md),
because at list scale an intermittent race stops being intermittent.

## Sources

- The per-step timings this page reasons from are measured and sourced on [how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md). The failure patterns are from running list tasks with this browser and are offered as experience, not as a measurement.

---

*Written after enough forty-item runs that produced thirty-one rows and no
explanation for the other nine. Every rule here exists to make the ninth row say
something.*
