---
title: "What is an AI web agent?"
description: "An AI web agent is an LLM in a loop with a browser. How the loop works, what it can do today, what it still fails at, and the architectures behind the demos."
parent: "Alternatives and Comparisons"
nav_order: 9
---


# What is an AI web agent?

An AI web agent is a language model in a loop with a browser. You give it a goal in
plain language. It looks at the current page, decides one action, the browser
performs that action, and the model looks again. The loop repeats until the goal is
met, the model concludes it cannot be met, or something runs out: patience, money,
or the site's tolerance.

That is the whole idea. Everything else on this page, and everything in the products
built on it, is engineering around three questions: what exactly does the model see,
what exactly can it do, and what happens when either goes wrong. No hype survives
contact with those three questions, so this page will not carry any.

## The loop, one turn at a time

A single turn of an agent loop has four parts.

1. **Observe.** The framework produces a representation of the page for the model.
   This is the biggest design decision in the whole category (more below): a
   structured text rendering of the DOM or accessibility tree, a screenshot, or
   both.
2. **Decide.** The model receives the observation, the goal, and the history of what
   it has done so far, and emits one action: click that element, type this text
   there, scroll, go to a URL, or declare the task finished.
3. **Act.** The framework executes the action in a real browser. The page reacts:
   navigation, a validation error, a popup, nothing at all.
4. **Repeat.** The new state becomes the next observation.

Two properties of the loop explain most of what you will experience using one.
First, every turn costs a model call, so an agent's cost scales with the number of
steps, not the number of pages, and a task that wanders costs more than a task that
goes straight. Second, the model only knows what the observation shows it, so
anything the representation drops, a canvas widget, an image-only button, content
below the fold that was truncated, is invisible to the agent no matter how good the
model is.

## What agents can actually do today

Used within their range, current agents are genuinely useful at tasks that need a
browser and a judgement call on every page: read this page and extract what matters,
compare what these three pages say, walk this multi-step process and stop when
something unexpected appears, fill this form from these facts (with a person
reviewing before submit; [the forms page](ai-agent-fill-out-forms.md) is the honest
account of that one). The common thread is low volume and high judgement.

The trajectory is real, and worth stating with numbers rather than adjectives. When
the WebArena benchmark was published in 2023, the best GPT-4-based agent completed
14.41% of its end-to-end web tasks against a human rate of 78.24%. In 2026, on the
adjacent OSWorld benchmark for full computer tasks, Agent S3's own README reports
72.6%, which it states is above the measured human level of roughly 72%. Those two
numbers are from different benchmarks and the second is self-reported, so do not
lay them end to end as one curve; the honest reading is narrower: in about three
years, scoped agent tasks went from mostly failing to mostly succeeding.

## What agents still fail at

This is the section vendors skip, so it gets the detail here.

- **Wrong targets.** The model decides to click something that is not what it thinks
  it is, or references an element that does not exist in the observation, a
  hallucinated selector. Structured-view agents fail loudly here (the element is not
  found); screenshot agents fail silently (the click lands somewhere).
- **Loops and wandering.** An agent that misreads a page can retry the same failing
  action, or oscillate between two pages, burning a model call per turn. Watching an
  agent spend forty steps on a six-step task is a rite of passage. Caps on steps and
  spend are not optional.
- **Cost per task.** Every observation of a complex page is thousands of tokens.
  Multiply by steps and by retries. Concretely: AIHawk's default model, GLM-4.6, is
  priced on OpenRouter at $0.43 per million input tokens and $1.75 per million
  output, which is cheap for the class; a multi-step task still routinely moves
  hundreds of thousands of input tokens. On frontier-priced models the same task
  costs an order of magnitude more. The full cost argument, against the alternative
  of writing a scraper, is on
  [agents vs traditional scraping](ai-browser-agents-vs-traditional-scraping.md).
- **Sites that push back.** Some pages detect and block automation, and an agent
  inherits every signal its browser emits plus tells of its own, like the
  machine-regular rhythm covered in
  [the timing-signal page](ai-agent-timing-signal.md). What blocking is made of, and
  which parts an agent framework can and cannot fix, is the subject of
  [why does my AI agent get blocked](why-does-my-ai-agent-get-blocked.md).
- **Non-determinism.** The same task on the same site can succeed today and fail
  tomorrow, because the model sampled a different path or the page changed a detail.
  Anything you need to run repeatedly and reliably deserves either a fixed script or
  an agent with tight checks around it.

## The architectures, in two axes

**How the agent sees: structure versus pixels.** A DOM-reading agent receives page
structure, element roles, labels and text, and acts on elements by reference. It is
precise and comparatively cheap, and it goes blind where structure is missing. A
screenshot agent receives the rendered image and acts at coordinates; it sees
whatever a person sees and pays for it in tokens and grounding errors. The two
category pages carry the specifics:
[open-source browser agents](ai-browser-agent-open-source.md) for the structural
side, [open-source computer-use agents](computer-use-agent-open-source.md) for the
pixel side. The field is converging on hybrids: structure where it exists, pixels
where it does not.

**Where it runs: hosted versus local.** A hosted agent runs browser and loop on a
vendor's infrastructure: nothing to install, and in exchange the vendor sees your
sessions and their logins, you queue behind their limits, and the product can be
withdrawn (the fate of one well-known hosted agent is its own page:
[is OpenAI Operator still available?](is-openai-operator-still-available.md)). A
local agent runs the browser on your machine with your keys. The model itself is
usually still a hosted API in both cases; fully local models work through tools
like Ollama, at a real capability cost on long tasks.

Where this project sits, stated once and with its boundary: AIHawk is a local,
open-source, structure-reading agent whose browser is a Firefox patched at the C++
level rather than a stock automation build, which addresses the fingerprint layer
of blocking and does nothing for the IP, volume or pacing layers. Two ways in, an
MCP server for assistants like Claude Code, or `aihawk ui` with an OpenRouter
key. This is AIHawk's wiki, so weigh that paragraph as a maintainer describing his
own tool.

## Where to go from here

This page is the hub of a cluster; each spoke goes one level deeper.

- Choosing a tool: [open-source AI browser agents](ai-browser-agent-open-source.md),
  [open-source computer-use agents](computer-use-agent-open-source.md),
  [choosing an AI browser agent](best-ai-browser-agent.md), and the
  Operator-shaped questions,
  [alternatives](openai-operator-alternatives.md) and
  [open-source equivalents](openai-operator-open-source.md).
- Deciding whether you need an agent at all:
  [agents vs traditional scraping](ai-browser-agents-vs-traditional-scraping.md).
- Running one: [getting an agent to fill out forms](ai-agent-fill-out-forms.md).
- When it stops working:
  [why does my AI agent get blocked](why-does-my-ai-agent-get-blocked.md),
  [the timing signal](ai-agent-timing-signal.md), and
  [retry loops and rate limits](agent-retry-loops-rate-limits.md).

## Short answers to the questions that lead here

**What is an AI web agent, in one sentence?** A language model in a loop with a real
browser: it observes the page, chooses one action, the browser executes it, and the
cycle repeats until the goal is done.

**Is that the same as a chatbot with browsing?** No. Search-and-summarize features
read pages; a web agent acts on them, clicking, typing and navigating, which is a
different capability with different failure modes.

**Can an agent do anything I can do in a browser?** In principle it can attempt
most of it; in practice it is reliable on scoped, judgement-per-page tasks and
unreliable on long open-ended ones. The 2023 WebArena baseline was 14.41% task
success against a human 78.24%, and while agents have improved sharply since, "give
it anything" is still not the honest pitch.

**Why do agents cost real money per task?** Each loop turn sends the page state to
a model. Complex pages are thousands of tokens per observation, tasks take many
turns, and retries multiply both.

**DOM-reading or screenshot-based, which is better?** For web-only tasks,
structure: cheaper, more precise, diagnosable failures. For anything without
readable structure, pixels are the only option. Hybrids are increasingly the
default answer.

**Do AI web agents get blocked?** Yes, for four separable reasons: browser
fingerprint, IP reputation, volume, and behavioral rhythm. An agent framework can
fix the first, influence the fourth, and cannot fix the middle two;
[the blocked page](why-does-my-ai-agent-get-blocked.md) walks the order to check.

## Sources

All retrieved 2026-09-03.

- [WebArena paper abstract (arXiv:2307.13854)](https://arxiv.org/abs/2307.13854),
  for the 14.41% agent versus 78.24% human end-to-end success rates.
- [simular-ai/Agent-S](https://github.com/simular-ai/Agent-S), for the self-reported
  OSWorld figure and its human-level comparison.
- [browser-use/browser-use](https://github.com/browser-use/browser-use), as the
  reference example of a DOM-plus-screenshot observation design.
- [GLM-4.6 on OpenRouter](https://openrouter.ai/z-ai/glm-4.6), for current per-token
  pricing of AIHawk's default model.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its README in this
  repository, for the claims about AIHawk itself.

**See also:** [open-source AI browser agents](ai-browser-agent-open-source.md),
[agents vs traditional scraping](ai-browser-agents-vs-traditional-scraping.md), and
[why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md).

---

*Maintained alongside [AIHawk](https://github.com/feder-cr/AIHawk), an open-source
web agent with a real patched Firefox underneath. The loop described above is the
one it runs, which is how its failure modes ended up documented this specifically.*
