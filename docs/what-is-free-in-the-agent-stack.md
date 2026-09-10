---
title: "What is actually free in the AI browser agent stack"
description: "Free means four different things here, and one product name often covers two. What each layer costs, and the three surprises that arrive in month two."
parent: "Alternatives and Comparisons"
nav_order: 30
---

# What is actually free in the agent stack

The word does four jobs in this category: open source, free tier, free to start,
and free because somebody else is paying for the model. They are not the same,
and the confusion is not accidental, because several products use one name for a
free thing and a paid thing.

Here is where the money is at each layer, and where it lands later.

## The four meanings

**Open source.** The code is published under a licence. You can run it, read it
and fork it. Says nothing about running costs. browser-use, Skyvern, the MCP
servers and this project are here.

**Free tier.** A hosted service with a quota. Beyond the quota you pay. Cloud
browser providers work this way, and the tier is generally sized to be enough
to evaluate and not enough to run anything.

**Free to start.** A trial, or a subscription with a free plan that lacks the
feature you came for. This is where cancelling turns out to be a question people
search for.

**Free because the model is someone else's problem.** The tool costs nothing and
does nothing without a model, and the model is billed to you. This describes
almost every open agent, and it is the meaning that surprises people.

## Layer by layer

| Layer | Typically | The bill you actually get |
|---|---|---|
| Agent library | Open source | Model tokens, at your provider's rate |
| MCP server | Open source | Model tokens, through the assistant you already pay for |
| Consumer agentic browser | Free to use, some free to start | A subscription for volume, or nothing |
| Cloud browser | Free tier | Per hour or per session after the tier |
| The engine | Open source | Nothing, or a machine to run it on |

**The pattern:** the software is nearly always free and the model nearly never
is. A browsing session is turn-heavy - a snapshot plus a few actions per page,
dozens of pages - so the token bill for an agent is larger per task than for the
same model used in chat. This is the number worth estimating before you build
anything on top.

## The three surprises in month two

**Token cost scaling with pages, not with tasks.** A task that touches two pages
and one that touches two hundred cost two orders of magnitude apart, and the
tool's price is the same in both. This is the single largest cost, and the
mitigation is structural rather than commercial:
[stop using the model once the flow is known](playwright-mcp-best-practices.md).
[Using a browser MCP server for web scraping](mcp-for-web-scraping.md) is the
same argument at volume.

**Cloud browser minutes.** Priced per hour or per session, and an agent that
leaves a browser open while a model deliberates is billing for the thinking as
well as the browsing. Read whether idle time counts.
[Cloud browser infrastructure explained](cloud-browser-infrastructure-for-ai-agents.md)
covers what you are renting.

**The free plan without the feature.** A product free to use, with the thing you
adopted it for behind the paid plan. Check what the free plan excludes before
you build a workflow on it, not after.

## The genuinely free path

If you want to try this with no bill at all beyond a model:

- An open MCP server, registered with an assistant you already pay for. The
  server costs nothing and the tokens come out of a subscription you already
  have. [The MCP server](mcp-server.md) is ours,
  [choosing an MCP server](best-mcp-server-for-browser-automation.md) covers the
  field.
- The browser on your own machine rather than a rented one. No per-hour meter,
  and your home address is usually treated better than a cloud one anyway.
- A local model for the easy half of the work.
  [AI browser agent with a local LLM](ai-browser-agent-local-llm.md) has what
  changes, and it is not free of cost either: it is free of bills and expensive
  in hardware and patience.

[AIHawk](https://github.com/feder-cr/AIHawk) is MIT and the engine downloads
from a public release, so the software side is genuinely nothing. The model is
yours, through your assistant or through your own key, and we do not resell it.

## Short answers to the questions that lead here

**Is browser-use free?** The MIT core is. The cloud product is not, and tokens
are yours either way.

**Is Playwright MCP free?** Yes, Apache-2.0. Same token caveat.

**Is there a free Browserbase tier?** There is a free tier, sized for
evaluation. Read whether idle browser time counts against it.

**How much does Manus cost?** A subscription, with a free plan below it. Prices
in this category change often enough that any figure written here would be
wrong; check theirs.

**What is the cheapest way to run a browser agent?** An open MCP server plus an
assistant subscription you already have, with the browser on your own machine.

**Why is my token bill so high?** Pages, not tasks. Every page is a snapshot in
context, and the context carries forward.

**See also:** [open-source agentic browsers](agentic-browser-open-source.md),
[which LLM for browser automation](best-llm-for-browser-automation.md), and
[Playwright MCP best practices](playwright-mcp-best-practices.md).

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10, for its licence.
- The [browser-use](https://github.com/browser-use/browser-use) and [Skyvern](https://github.com/Skyvern-AI/skyvern) repositories for licences and the split between open core and hosted product.

---

*Written by a project that is free and has no paid tier, which is a reason to
check the table above rather than take it on trust. Specific prices are
deliberately absent: they move, and a stale number is worse than a pointer.*
