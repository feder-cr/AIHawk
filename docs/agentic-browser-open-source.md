---
title: "Open-source agentic browsers: the three layers, compared"
description: "What is genuinely open in this field sits one layer below the browser. The full browsers, the agent libraries, the MCP servers, and what free means here."
parent: "Alternatives and Comparisons"
nav_order: 25
---

# Open-source agentic browsers

Most of the browsers people mean by "agentic browser" are closed products with a
free tier. The open-source part of the field is real but sits mostly one layer
down, in the agents and the servers rather than the browser you install. This
page separates the three layers so you can tell what you would actually be
cloning.

If the term itself is doing the confusing,
[what is an agentic browser](what-is-an-agentic-browser.md) untangles it first.

## Layer 1: the browser you install

**BrowserOS** is the clearest open-source example of the consumer shape: a
browser you use, with agent capability built in, and the source published. It is
the answer to "is there an open Comet", and the honest caveat is that a browser
is an enormous amount of software to maintain, so judge the project's activity
before you make it your daily driver.

Everything else in this row - Comet, Atlas, Opera Neon, Dia, Fellou - is
proprietary. Some are free to use. Free to use is not open source, and the
distinction matters here more than usual, because the thing you cannot inspect
is a program with your session cookies.

## Layer 2: the agent you drive from code

This is where the open-source field is deep, and where most people who search
for an open agentic browser will actually end up.

**browser-use** is the adopted default: MIT, very large community, Chromium
family. **Skyvern** is AGPL-3.0 and vision-first, which trades tokens for
resilience when layouts move. **Stagehand** sits between a framework and a
library, letting you mix written instructions with ordinary Playwright calls.
**Agent S3** is a wider scope again: the whole desktop, not just the browser.

This wiki compares them one by one rather than ranking them:
[open-source AI browser agents](ai-browser-agent-open-source.md) and
[open-source computer-use agents](computer-use-agent-open-source.md).

What they share, and what almost no comparison mentions: they all drive a stock
automation build. The agent is open, the browser underneath is the same
Chromium-over-CDP stack everyone else is running, with the same well-studied
observable choices. If your problem is the agent's reasoning, pick by the list
above. If your problem is that the browser gets recognised, none of these rows
differ from each other, because the browser is not the part they changed.

## Layer 3: the MCP server

The newest layer, and the cheapest to try, because it adds a browser to an
assistant you are already paying for instead of standing up a new program.

**Microsoft's playwright-mcp** is the reference implementation: Apache-2.0,
36.9k stars when read on 2026-09-10, driving Chrome, Firefox, WebKit or Edge,
and exposing the page to the model as an accessibility tree rather than pixels.
It is the one to start with, and
[what it is and how it differs from the CLI](playwright-mcp-vs-cli.md) is on its
own page here.

**The stealth-oriented servers** are a small, young cluster: wrappers around
Camoufox, nodriver and Patchright that expose those engines over MCP.
[Stealth MCP servers compared](stealth-mcp-servers-compared.md) goes through
them, including the part where several of them advertise capabilities we could
not verify.

**AIHawk** - ours - is an MCP server whose browser is a Firefox patched at the
C++ source rather than a stock build with a script on top. MIT. That is the
whole differentiator and it is narrow: it changes what the browser looks like,
not how well the agent thinks. [The MCP server](mcp-server.md) has the config
block and the tool list.

## What "free" means in each layer

Worth stating plainly, because the word carries three different meanings across
these rows and product pages rarely separate them.

| Layer | Source open? | Runs without payment? | What you still pay |
|---|---|---|---|
| Consumer browser | Rarely (BrowserOS is the exception) | Usually, with limits | Nothing, or a subscription for volume |
| Agent library | Usually, MIT or AGPL | Yes | Model tokens, at your provider's rate |
| MCP server | Usually | Yes | Model tokens, via the assistant you already run |
| Cloud browser | No | Free tier | Per-hour or per-session after the tier |

[What is actually free in the agent stack](what-is-free-in-the-agent-stack.md)
works through the specific tiers, because the trap is not price, it is that the
free thing and the paid thing have the same name.

## Choosing, in one pass

- **You want to browse with an agent and inspect the code:** BrowserOS.
- **You want to write a program that does a task:** browser-use, unless layouts
  keep breaking you (Skyvern) or the task leaves the browser (Agent S3).
- **You want your assistant to be able to open a page today:** playwright-mcp.
- **The browser itself is what gets recognised:** that is the narrow case where
  the engine matters, and the stealth-oriented servers and AIHawk are the row
  that addresses it. It does not repair an IP's reputation or robotic pacing.

## Short answers to the questions that lead here

**Is there an open-source Perplexity Comet?** BrowserOS is the closest, and it
is a different project with a much smaller team, not a clone.

**What is the best open-source AI browser agent?** browser-use by adoption, and
that is a real signal. Best for you depends on whether your failure is the
reasoning, the layout, the scope or the browser.

**Is browser-use free?** The MIT core is. The cloud product is not, and the
model tokens are yours either way.

**Are open-source agents harder to detect?** No. Openness is a licence property.
The detection surface comes from the browser build and the network path, and
most open agents share the same stock stack.

**Can I self-host an agentic browser?** Yes for layers 2 and 3, which is the
usual reason people go looking for the open ones.

**See also:** [Choosing an AI browser agent](best-ai-browser-agent.md),
[cloud browser infrastructure explained](cloud-browser-infrastructure-for-ai-agents.md),
and [why an agent gets blocked](why-does-my-ai-agent-get-blocked.md) if you got
here after something stopped working.

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10: licence, star count, browser support and the accessibility-tree approach.
- The [browser-use](https://github.com/browser-use/browser-use), [Skyvern](https://github.com/Skyvern-AI/skyvern) and [Agent-S](https://github.com/simular-ai/Agent-S) repositories for licences and scope.
- [Top 5 agentic browsers in 2026](https://seraphicsecurity.com/learn/ai-browser/top-5-agentic-browsers-in-2026-capabilities-and-security-risks/), retrieved 2026-09-10, for the consumer-browser list.

---

*Written while maintaining [AIHawk](https://github.com/feder-cr/AIHawk), which
appears in layer 3. It is listed where it belongs rather than first, and the
sentence describing what it does not fix is the same one we would want from
somebody else's page.*
