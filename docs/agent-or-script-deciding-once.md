---
title: "Agent or script: deciding once instead of every time"
description: "Four questions that settle it, in order, and the break-even that most people get wrong. The answer is usually both, in a specific sequence."
parent: "Using the Agent"
nav_order: 76
---

# Agent or script: deciding once instead of every time

The question comes up per task and gets re-argued every time, usually on taste.
It has an answer, and it is four questions deep.

## The four questions, in order

**1. How many times will this run?**
Once or a handful: agent. Every day forever: script. The crossover is not about
capability, it is about where the cost lands. An agent pays a model for judgement
on every run; a script pays a developer once and then nothing.

**2. Does the page change shape, or only content?**
Content changing is what a script handles fine. Shape changing, meaning the
selectors move, is what breaks it, and a script that needs repairing monthly has
quietly become a recurring cost too. If the site redesigns often or you are
reading many different sites with the same intent, judgement per run is worth
paying for.

**3. Does the task need a decision, or only extraction?**
"Take the third cell of each row" is extraction. "Find the price, which might be
a range, might be per month, might say contact us" is a decision. Scripts are
better at the first and cannot do the second without becoming a pile of special
cases.

**4. How expensive is a wrong answer?**
A script is wrong the same way every time, which is detectable. An agent is wrong
differently each time, which is harder to notice and harder to test. Where
exactness matters, either script it or add a verification step you genuinely run:
[validating an AI agent's output](validating-an-agents-output.md).

## The break-even people get wrong

The usual framing is "the script costs a day to write, the agent costs cents per
run, so the agent wins until you hit a lot of runs". That undercounts both sides.

**The agent's real cost is the model turns, and they scale with pages, not with
runs.** A forty-page walk resends a growing transcript, so page forty is priced
with pages one to thirty-nine still in the context. The per-page cost climbs as
the run goes on, and the numbers for that are in
[extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md).

**The script's real cost includes repair.** Not a day, a day plus whatever a
layout change costs a few times a year.

So the break-even is lower than the naive version suggests for long single runs,
and higher than it suggests for short ones against unstable pages.

## The answer is usually both, in this order

The pattern that actually works, and it is not a compromise:

1. **The agent explores.** Point it at the page and have it report where the data
   is, what the page demands, what the odd cases look like, and what the
   selectors are. This is the part a person otherwise spends an hour on with
   developer tools open.
2. **You write the script from that report**, or have the agent help write it.
3. **The script runs daily.**
4. **The agent comes back when the script breaks**, to find out what moved.

You pay for judgement exactly where judgement is needed: at the start, and at
each failure. Nothing pays for judgement in the middle, where there is none to
apply.

## The asymmetry nobody mentions

A script cannot tell you it is subtly wrong. If the layout changes so that the
third cell is now the fourth, the script keeps running and returns the wrong
column, silently and forever.

An agent in the same situation usually notices, because the value no longer looks
like a price, and says something. That is worth real money on data you are going
to act on, and it is an argument for the agent that has nothing to do with
convenience.

The counter-argument is the same fact from the other side: because the agent
decides each time, it can decide differently between runs on a page that did not
change. Which of the two failures you prefer is the actual question, and it
depends on whether you would rather be consistently wrong or inconsistently
right.

## A worked case

Forty supplier sites, pricing pages, once a quarter.

Wrong answer: write forty scrapers. Forty layouts, forty repair jobs, and it runs
four times a year.

Wrong answer: run the agent on all forty every quarter with no structure. It
works and the results are not comparable, because forty pages describe prices
forty ways.

Right answer: the agent reads all forty and records the raw string plus a
normalised value plus the URL, per
[normalising values across sites](normalising-values-across-sites.md); you look
at the raw column once and fix the normalisation; quarterly reruns compare against
the last file rather than starting fresh. Judgement where the sites differ,
mechanics where they do not.

## Short answers to the questions that lead here

**Should I use an agent or write a script?** Script for a stable page run
repeatedly; agent for a page you have not seen, a layout that moves, or a task
needing judgement. Most real cases want both, in that order.

**Where is the break-even?** Lower than the naive per-run arithmetic suggests,
because the agent's cost rises within a long run as the transcript grows, and the
script's cost includes repairing it when a layout moves.

**Which is more reliable?** Neither, differently. A script is consistently wrong
when the page changes and never says so. An agent notices, and can be
inconsistent between runs.

**What is the standard hybrid?** Agent explores once, you script the repetition,
agent returns when the script breaks.

**See also:**
[when not to use an AI browser agent](when-not-to-use-an-ai-agent.md), which is
the longer list of cases where the answer is neither, and
[AI browser agents versus traditional scraping](ai-browser-agents-vs-traditional-scraping.md)
for the comparison with the numbers attached.

## Sources

- The cost-curve claim about a growing transcript is documented and argued on [extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md), which is where this project's own figures for it live. Everything else here is a framing rather than a measurement, and is presented as one.

---

*Four questions, asked in order, and the fourth one is the tiebreaker more often
than people expect.*
