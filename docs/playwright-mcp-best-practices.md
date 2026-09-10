---
title: "Playwright MCP best practices: four decisions that matter"
description: "Capability scope, profile strategy, how the instruction is written, and when to stop using the model. Measured: our own tool surface costs 3.5k tokens."
parent: "Using the Agent"
nav_order: 33
---

# Playwright MCP best practices

A browser MCP server is unusual among developer tools in that the same setup can
be excellent or unusable depending on four decisions, none of which is a code
change. These are those four, then the habits that follow from them.

## 1. Give it the smallest capability set that works

Every tool the server exposes has a description, and every description is in the
model's context on **every turn**. A browsing session is dozens of turns. This
is the single largest avoidable cost in the category.

Measured on our own server, because we can read our own source and nobody
publishes this number: **24 tools, 14,064 characters of tool description, which
is roughly 3,500 tokens sent again on every single turn** (median 442
characters per tool, read from `src/aihawk/mcp/server.py` on 2026-09-10). A
forty-turn session therefore spends on the order of 140,000 tokens restating
what the tools are, before a single page has been read. That is the budget the
next two paragraphs are about.

Microsoft's server makes capabilities additive with `--caps`, so vision, pdf and
devtools are off unless you ask. Leave them off until a page forces the issue.
Do not register two browser servers side by side for coverage: the overlapping
tool names cost context twice and make the model's choice worse, which is the
part people do not predict.

## 2. Decide the profile strategy on purpose

Three options, and picking by accident is how people end up in
[browser is already in use](playwright-mcp-browser-already-in-use.md).

**Isolated** (`--isolated`): a throwaway profile per session. Right default for
exploration. Two clients can run at once. You start logged out every time.

**Persistent** (`--user-data-dir`): the browser remembers. Right when the flow
needs a login you do not want to redo. One live browser per directory, so give
each client its own path.

**Storage state** (`--storage-state`): a saved cookie and local-storage
snapshot, loaded into an otherwise clean profile. The middle option people
forget, and usually the best one: logged in, no shared lock, no accumulated
history.

## 3. Write the instruction as a goal with a stopping condition

The failure that wastes the most tokens is not a wrong click, it is a model that
does not know when it is finished. "Find the pricing page" ends. "Look around
the site" does not.

Two habits that pay immediately:

- **Name the end state.** "Open the pricing page and tell me the price of the
  team plan" beats "check their pricing", because the second one invites five
  more page loads after the answer was already on screen.
- **Say what to do when it is not there.** Without that, a model that cannot
  find the thing will keep looking, and looking is the expensive part.

## 4. Stop using the model once the flow is known

This is the practice most worth internalising, and it is the one nobody puts in
a best-practices list because it argues against the tool.

An MCP session is a good way to **discover** a flow: you did not know the page's
shape, and the model worked it out. It is a bad way to **repeat** one. On the
second run the model rediscovers the same steps and you pay again, more slowly
and less reproducibly than the script it should have become.

Use the session to find the selectors and the order, then write those down as
ordinary code. [Playwright MCP vs the CLI](playwright-mcp-vs-cli.md) has the
split in full, and [MCP for web scraping](mcp-for-web-scraping.md) applies it to
the case where the repetition is the whole job.

## Habits that follow

**Read the page before acting on it.** A snapshot costs one turn and saves
several failed clicks. Models that click first tend to click something that
moved.

**Prefer a reference the server gave you over a selector you invented.** The
accessibility snapshot returns stable references precisely so the next call does
not have to guess.

**Close what you open.** Tabs accumulate, each one holds memory, and a session
that has been alive for an hour is usually carrying five pages nobody is reading.

**Keep one browser per concern.** If you are comparing two sites, two named
browsers is clearer to the model than one browser with two tabs, and much
clearer when something fails.

**Check the boring causes before blaming the server.** Slow is usually the
model's round trips, not the browser.
[Not found](playwright-mcp-blocked.md) is often a page that renders after the
snapshot was taken. And a challenge page is a network and pacing question far
more often than a browser question:
[why an agent gets blocked](why-does-my-ai-agent-get-blocked.md).

## What this project does differently, and what it costs

[AIHawk](https://github.com/feder-cr/AIHawk) makes two of these decisions
structural rather than optional. Concurrency is named rather than flagged, so
practice 2 is harder to get wrong. Identity is derived from a seed, so a session
that failed can be replayed as the same browser, which turns "it worked
yesterday" into something you can test.

The cost is that you name things on day one, and the engine covers Windows and
Linux only. [The MCP server](mcp-server.md) has the configuration.

## Short answers to the questions that lead here

**How do I make Playwright MCP cheaper?** Fewer capabilities, one server, a
stopping condition in the instruction, and stop using it for flows you already
know.

**Should I use isolated or persistent?** Isolated for exploring, storage state
for logged-in flows, persistent only when you genuinely want accumulated
history.

**Why is it so slow?** Each step is a round trip through a model. That is the
design, not a defect. If speed matters, the flow belongs in code.

**How many tools should a browser MCP server have?** Enough to read state, to
reach what selectors cannot, and to fall back to JavaScript.
[How the tools are shaped](mcp-tool-design.md) argues the case.

**Can I use it on a site I have to log into?** Yes. Whether you should is a
separate question:
[should you log your agent into accounts](should-you-log-your-ai-agent-into-accounts.md).

**See also:** [Playwright MCP vs the CLI](playwright-mcp-vs-cli.md),
[Playwright MCP with a proxy](playwright-mcp-with-a-proxy.md), and
[writing tasks for a browser agent](writing-tasks-for-an-ai-browser-agent.md).

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10, for `--caps`, `--isolated`, `--user-data-dir` and `--storage-state`.

---

*Written while maintaining a competing server. Practice 4 argues against using
either of them for the repeat case, which is the recommendation we would least
like to make and the one that saves the most money.*
