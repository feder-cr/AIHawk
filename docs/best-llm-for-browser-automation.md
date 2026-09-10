---
title: "Which LLM for browser automation: the four properties"
description: "Leaderboards do not predict this workload. Tool-call discipline, stability as context grows, cost per turn, and vision only where a snapshot fails you."
parent: "Using the Agent"
nav_order: 37
---

# Which LLM for browser automation

Driving a browser is an unusual workload for a model and the general
leaderboards do not predict it well. A session is dozens of short turns, each
one a tool call against a page description that keeps changing, with the whole
history accumulating in context. Four properties decide the outcome, and raw
reasoning ability is only one of them.

## The four properties that matter

**Tool-call discipline.** The model must emit a well-formed call, with the
reference the server just handed it, and then stop. Models that narrate before
calling, or that invent a selector when a reference was available, burn turns
and click the wrong things. This is the single biggest separator in practice and
it is not what benchmarks measure.

**Stability as context grows.** By turn thirty the conversation contains thirty
page snapshots. Models degrade differently under that load: some start
re-reading pages they already read, some lose the goal, some keep going
indefinitely because nothing told them to stop. A model that is excellent at
turn five and lost at turn forty is worse here than a duller one that holds.

**Cost per turn.** Multiply by dozens. A session that costs pennies at one price
point costs real money at another, and the browsing workload is unusually
turn-heavy, so the multiplier hurts more than it does in chat.

**Vision, when you need it.** Only for the pages a structured snapshot cannot
describe: a canvas, a map, a custom widget. If your target pages are ordinary
HTML you may never need it, and paying for a vision-capable model to read
accessibility trees is paying for something you are not using.

## How to choose without guessing

The field moves too fast for a page to name a winner and stay true. What does
not move is the procedure:

**Pick one real task you care about,** with a clear end state, and run it on two
or three candidates from the same starting page. Not a toy task: a real one,
long enough to reach turn twenty.

**Count three things:** turns to completion, wrong actions, and whether it
stopped when it was done. Total cost falls out of the first one.

**Repeat it once.** These runs are not deterministic, and a single run tells you
less than people assume.

This is half an hour and it beats any ranking, because the answer is specific to
your pages and your prompt style.

## Things that surprise people

**A cheaper model with tight tool discipline often wins on total cost**, because
it takes fewer turns to get to the same place. The expensive model that
deliberates before every click can cost more per session while being better per
token.

**Local models are a real option for the easy half.** Navigation, reading and
form filling on well-structured pages do not need a frontier model. The hard
part is deciding what to do when something unexpected happens, and that is where
they fall off. [AI browser agent with a local LLM](ai-browser-agent-local-llm.md)
covers what changes when you run one.

**The prompt matters more than the model, up to a point.** A goal with a
stopping condition turns a rambling session into a short one on every model.
[Writing tasks for a browser agent](writing-tasks-for-an-ai-browser-agent.md)
is the practice, and it is cheaper than upgrading.

**The server's tool surface changes the answer.** A server exposing a hundred
tools makes every model worse at choosing, and makes small models much worse.
Ours is **24 tools and about 3,500 tokens of description per turn** (measured
from our own source, 2026-09-10); that overhead lands on every model you test,
so hold it constant when you compare them.
[How the tools are shaped](mcp-tool-design.md) argues why fewer is better here.

## In this project

[AIHawk](https://github.com/feder-cr/AIHawk) is model-agnostic by design. Used
as an MCP server, the model is whatever your assistant runs, and the choice is
not ours to make. Used through its own interface, it reaches models through
OpenRouter with your key, so you can change the model without changing anything
else, which is exactly the setup the half-hour procedure above wants.

[Which model to use with AIHawk](which-model-to-use-with-aihawk.md) is the
product-specific version of this page.

## Short answers to the questions that lead here

**What is the best LLM for browser automation?** No stable answer, and any page
that gives one is a snapshot of a month. Test on one real task; the procedure
above takes half an hour.

**Do I need a vision model?** Only for pages a structured snapshot cannot
describe. Most cannot be told apart from ordinary HTML until you try.

**Can I use a local model?** For the straightforward half, yes. Recovery from
surprise is where the gap shows.

**Why does my agent keep going after it has the answer?** The prompt, not the
model. Name the end state.

**Is a bigger context window better?** Up to the point where the model stops
using it well. Stability under accumulated snapshots is the property, not the
window size.

**See also:** [writing tasks for a browser agent](writing-tasks-for-an-ai-browser-agent.md),
[Playwright MCP best practices](playwright-mcp-best-practices.md), and
[browser problem or model problem](browser-problem-or-model-problem.md) when a
run fails and you are not sure which half to blame.

## Sources

- This project's own MCP tool surface and interface, for the model-agnostic claim.
- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10, for the accessibility-tree snapshot and the optional vision capability.

---

*Written by a project that does not sell a model and therefore has no favourite.
The recommendation is a procedure rather than a name because a name would be
stale within the month.*
