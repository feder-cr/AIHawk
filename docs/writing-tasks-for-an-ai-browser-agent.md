---
title: "How to write a task an AI browser agent can follow"
description: "The most important skill for driving a browser agent: name the URL, define done, state the output shape, and cap scope. Before/after examples included."
parent: "Using the Agent"
nav_order: 27
---


# How to write a task an AI browser agent can follow

Name the exact starting URL instead of asking it to search, say what "done"
looks like, and state the output shape you want. Tell it what to do when
data is missing, describe any interaction the page demands, keep one task to
one goal, and cap how many pages or how long it runs. That is the whole
skill.

## Why the same task, worded two ways, gets different results

A browser agent does not see your intent, it sees a snapshot of a page and
whatever you typed as the instruction. It has no memory of what you meant
beyond the words used, and it fills any gap with a guess, because most
agent loops never get a chance to ask a follow-up mid-task.

If a well-written task still misfires, the next question is not a better
prompt, it is [whether the browser or the model
broke](browser-problem-or-model-problem.md), which is a different test.

## Name the starting URL instead of asking it to search

Asking an agent to "find" something sends it through a search engine first,
and results are themselves a page full of ambiguity: which result, sponsored
or not, which of three similarly-named sites. Naming the URL skips that
decision.

**Before:**
> Find me some interesting tech news from today.

**After:**
> Go to news.ycombinator.com and give me the top five titles.

The "after" version is close to verbatim from AIHawk's own README: one URL,
one bounded ask. The "before" version leaves the agent to pick a search
engine, a query, and which result counts as news, three extra decisions
before it reaches the content you wanted.

## Say what "done" looks like, and the shape you want the answer in

Without a stated finish line, "finished" can mean anything from one page
read to the model declaring victory early. Pair that with the exact shape
you want the answer in, or you get prose where you wanted a table.

**Before:**
> Get me the prices of the laptops on this page.

**After:**
> Go to `<paste the URL>`. List every laptop under $1000 shown on the first
> two pages of results, one row per laptop, with columns Name and Price.
> Stop after two pages even if more remain.

The "before" prompt never says when to stop reading, so the agent might
read one laptop or forty. The "after" prompt fixes the shape (a row per
laptop, two named columns) and the stopping point, so the result is
predictable before the run starts. [The forms
page](ai-agent-fill-out-forms.md) makes the same point from the filling
side: a stated checkpoint beats an open-ended "finish the whole thing."

## Tell it what to do when data is missing

A model under pressure to answer will often guess rather than admit it does
not know. Say explicitly what counts as missing and what to do about it.

**Before:**
> Give me the shipping cost to Canada for this product.

**After:**
> Give me the shipping cost to Canada as listed on the product page. If it
> is not shown before checkout, say "not listed" rather than estimating
> from other countries' rates.

Without that second sentence, a model that cannot find a number sometimes
reasons its way to one anyway and hands it to you as fact. "Say so, never
guess" is a short instruction that closes an entire failure mode.

## Describe the interaction the page actually demands

Typing and clicking are not interchangeable to a page. An agent that assumes
text input works everywhere will fight a calendar widget for several turns
before landing on the wrong day.

**Before:**
> Find me a cheap flight from Milan to Lisbon next month.

**After (adapted from AIHawk's own README):**
> Go to `<paste the URL>`. One way, Milan to Lisbon, economy, one checked
> bag, one adult. Check every date from the 12th to the 16th of next month,
> one at a time, and read the cheapest fare for each day. The date field is
> a calendar widget, so click the days rather than typing them. If a date
> has no availability, say so. Do not guess a number.

That one sentence, "the date field is a calendar widget, click the days
rather than typing them," tells the agent which of its two ways of entering
a date will actually work here, before it burns turns discovering that
alone.

## Keep one task to one goal, and cap the scope

### One goal per task

A prompt asking for three unrelated things gives the model three chances to
drop one silently, with no way to tell which from the transcript alone. One
instruction, one goal, and a fresh instruction for the next, is more
reliable than it looks.

### A limit on pages and time

An unbounded task ("check every listing") runs until it is done or until you
stop it, on a page the agent had no way to know was this large - and nothing
in the loop will end it for you. Stating a cap, "the first three pages,"
"stop after ten minutes," turns an open-ended risk into a bounded one with a
clean stopping point you did not have to sit and watch for.

[AI agents for web research](ai-agent-web-research.md) bounds a walk the
same way, one page range at a time, for exactly this reason.

## Short answers to the questions that lead here

**What is the most important thing to get right in an AI agent prompt?**
Removing ambiguity about the starting point, the finish line, and the
output shape. Those three alone fix most of the failures people blame on
the model.

**How do I stop an AI agent from making up an answer?** Tell it explicitly
what to do when a value is missing: "say not listed, do not estimate."
Naming the failure case in the instruction is what stops the model from
quietly filling the gap with a guess.

**Can an AI agent handle a calendar or date picker?** Better if the
instruction says the field is click-only. Agents that assume typing works
everywhere waste turns on the widgets that demand clicks instead.

**How long or how many pages should I let an agent run?** Whatever you can
state as a number: a page count, a time limit, an item count. An unbounded
task risks stopping mid-thought at a turn limit instead of at a point you
chose.

**See also:** [getting an AI agent to fill out forms](ai-agent-fill-out-forms.md),
[browser problem or model problem?](browser-problem-or-model-problem.md), and
[AI agents for web research](ai-agent-web-research.md).

## Sources

All retrieved 2026-09-05.

- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), this repository's
  README, for the Hacker News and flight-fare example prompts, both read in
  the working tree 2026-09-05.

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. Every
before/after pair above follows the same shape the project's own README
uses in its worked example: name the page, name the finish line, name the
shape of the answer.*
