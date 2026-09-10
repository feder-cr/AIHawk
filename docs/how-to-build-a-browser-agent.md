---
title: "How to build a browser agent, and what to take instead"
description: "The loop is about forty lines. The page description, the action path and the stopping condition are the project, plus the four failures every one hits."
parent: "Using the Agent"
nav_order: 38
---

# How to build a browser agent

The loop is genuinely simple, and people who build one are usually surprised
twice: first that it works in an afternoon, then that the afternoon version is
about ten percent of the job. This page is both halves.

## The loop

Four steps, repeated:

1. **Describe the page to the model.** A structured description, not raw HTML:
   the accessibility tree, or the interactive elements with stable identifiers.
   Raw HTML is enormous, mostly irrelevant, and will exhaust your context on the
   third page.
2. **Ask for one action.** Constrained to a small vocabulary: navigate, click,
   type, select, press, read, screenshot, done. For calibration, our own
   production server settled on **24 tools totalling 14,064 characters of
   description** (measured 2026-09-10) covering sessions, tabs, reading,
   pointer, keyboard and a JavaScript reader. If your vocabulary is much
   larger than that, the model is choosing between overlapping verbs.
3. **Perform it,** and get the resulting state.
4. **Decide whether to stop.**

That is it. The interesting part is that each of these four has a failure mode
that only appears after the demo works.

## What actually takes the time

**Describing the page well.** Too much and you pay for tokens and the model gets
lost; too little and it clicks the wrong thing. The working shape is: interactive
elements only, with a short label, a role and a stable reference the next call
can use. If your descriptions contain CSS selectors you invented, the model will
invent them too, and they will be wrong after the next deploy.

**Making the action reach the page correctly.** Any automation library can click
a selector. Two things bite later: elements that no selector describes, which
need a coordinate path, and the fact that a click issued from script is not the
same event as a click issued from a pointer. Whether that matters depends
entirely on the site.

**Knowing when to stop.** The failure that costs the most money. Without an
explicit stopping condition, an agent that has the answer will keep browsing.
Build the stop into the loop, not into the prompt alone: a turn budget, and a
required "done" action with the result attached.

**Recovering from surprise.** A dialog, a cookie banner, a redirect to a login,
an empty result. The demo never hits these and the real task hits one within
five pages. Most of the engineering in a mature agent is here.

## What to build and what to take

Building the loop yourself is a good way to understand the problem and a poor
way to end up with something maintainable. The parts worth taking off the shelf:

**The page description.** MCP servers already produce a model-friendly snapshot
with stable references. Reimplementing that well is weeks.

**The action vocabulary.** Same reason. And a server gives you the coordinate
fallback that you would otherwise discover you needed.

**The whole loop, if you do not need it to be yours.** browser-use, Skyvern and
Stagehand are the agent layer, open source, with the recovery cases already
handled. [Open-source agentic browsers](agentic-browser-open-source.md) lays out
what each gives you.

The cheapest starting point of all is to not build a program: register a browser
MCP server with an assistant you already run and prompt it. You get the loop,
the model and the interface for the cost of a config block, and you find out in
an hour whether the task is even feasible. [The MCP server](mcp-server.md) has
ours, and [choosing an MCP server](best-mcp-server-for-browser-automation.md)
covers the field.

## The four failures every home-built agent hits

**The context fills up.** Thirty snapshots of a page in one conversation. Keep
the last state and a summary of the path, not the whole history.

**It loops.** Click, page does not change, click again, forever. Detect that
the state did not change and force a different action or a stop.

**It cannot see what it needs.** A canvas, a map, a widget with no accessible
name. This is the point where you need screenshots and coordinates, and adding
them later is harder than starting with the path in place.

**The site starts refusing it.** Not an agent problem, and switching model or
framework will not touch it.
[Why an agent gets blocked](why-does-my-ai-agent-get-blocked.md) has the
attribution: usually the address, the pacing, or a stock automation build, in
that order.

## Short answers to the questions that lead here

**How hard is it to build a browser agent?** The loop is an afternoon. The
recovery cases are the project.

**Should I use raw HTML or the accessibility tree?** The tree, or a reduced
element list. Raw HTML will not fit and mostly is not about anything the agent
can act on.

**Do I need a vision model?** Only where the structured description fails.
Build the coordinate path anyway; you will need it.

**Should I build on Playwright or Selenium?** Either drives a page. Neither
changes what the page can observe about the browser, which is a separate layer.

**Can I just use an MCP server instead?** Yes, and it is the right first move:
you find out whether the task is feasible before writing a program.

**See also:** [writing tasks for a browser agent](writing-tasks-for-an-ai-browser-agent.md),
[which LLM for browser automation](best-llm-for-browser-automation.md), and
[how the tools are shaped](mcp-tool-design.md) for why a small action vocabulary
beats a large one.

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10, for the snapshot-with-references design that this page recommends copying.
- The [browser-use](https://github.com/browser-use/browser-use) and [Skyvern](https://github.com/Skyvern-AI/skyvern) repositories for the off-the-shelf agent layer.

---

*Written while maintaining a browser MCP server, which is the "take it off the
shelf" recommendation in the middle of the page. The loop is described in full
anyway, because knowing what is inside it is how you tell whether a tool is
doing it well.*
