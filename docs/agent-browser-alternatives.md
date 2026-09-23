---
title: "Vercel agent-browser alternatives, compared honestly"
description: "Vercel's agent-browser is a Rust CLI that gives AI agents a browser. How browser-use, Playwright MCP, Stagehand and invisible_playwright_mcp compare on checkable facts."
parent: "Alternatives and Comparisons"
nav_order: 23
---

# Vercel agent-browser alternatives, compared honestly

Vercel's agent-browser is a native Rust command-line tool that gives an AI
agent a browser to drive, published under Apache-2.0. The alternatives doing
the same job are browser-use, Microsoft's Playwright MCP server, Stagehand
and invisible_playwright_mcp, and they differ less in what they automate than in how the agent
talks to them and which browser ends up running.

One disclosure before the comparison: this wiki is maintained by the people
behind invisible_playwright_mcp, one of the tools below. Read our row with that in mind. The
picks at the end name two other tools before they name ours.

## What Vercel's agent-browser actually is

The repository describes it as a browser automation CLI for AI agents, and
the shape of the thing follows from that word: it is a compiled binary an
agent runs as a separate process, not a library it imports. A daemon
persists between commands so a session survives from one invocation to the
next, and `--json` makes the output parseable rather than pretty.

Two details matter when you compare it with the rest. First, an agent can
also reach it over the Model Context Protocol, because the binary can run
as an MCP server, so it is not CLI-only in practice. Second, it drives
local Chrome or a cloud browser provider, which puts it in the same
Chromium-family camp as most of this category.

Its feature list leans toward what an agent needs rather than what a test
suite needs: semantic locators and element refs, accessibility audits,
network interception and multi-session handling. That is a different
emphasis from a testing framework, and it is the clearest signal of who the
tool is for.

## The alternatives, on facts you can check

Every cell below was read from the project's own repository on 5 September
2026. Licenses and runtimes change, so re-check before you standardise on
one.

| Tool | License | Browser it drives | How an agent talks to it | Runtime |
|---|---|---|---|---|
| Vercel agent-browser | Apache-2.0 | Chrome locally, or a cloud browser provider | CLI with JSON output, or as an MCP server | Rust binary |
| browser-use | MIT | Chromium family, through Playwright | Python library; the agent loop decides each action | Python 3.11+ |
| Playwright MCP | Apache-2.0 | Chromium, Firefox or WebKit | MCP server; any MCP client calls its tools | Node.js 18+ |
| Stagehand | MIT | Chromium, through Playwright | Library with act, observe and extract calls beside raw Playwright | TypeScript, Python or Go |
| invisible_playwright_mcp (ours) | MIT | Firefox, patched at the source level rather than a stock automation build | MCP server, or a local two-pane UI | Python 3.11+ |

Three honest notes on that table. Playwright MCP reads the page's
accessibility snapshot instead of screenshots, which keeps each step cheap
when a page exposes good semantics and hurts when it does not. Stagehand is
the only one that lets you mix plain-language steps and hand-written
Playwright calls in the same script, which is the right shape if you already
have Playwright code. And browser-use has by some distance the largest
community in this list, which matters more than any feature comparison when
you hit a problem at midnight.

## Where they genuinely differ

**Process shape.** A CLI binary and an MCP server are both out-of-process,
so a crash in the browser layer does not take your agent with it. A library
is in-process, which is simpler to debug and easier to bring down.

**Who decides the next action.** browser-use and Stagehand put a model in
the loop by design. Playwright MCP and agent-browser expose actions and let
whatever assistant you already run do the deciding. invisible_playwright_mcp does both,
depending on which of its two entry points you use.

**Language.** This is the boring criterion that decides most real adoptions.
Node-only or Rust-only rules a tool out of a Python shop as effectively as
any missing feature.

## Which one would I pick

- **You already run an MCP-first assistant and want the plainest hookup:**
  Playwright MCP. It is Microsoft's own, it speaks three browser engines,
  and there is nothing extra to learn.
- **You have Playwright code and want AI-directed steps inside it:**
  Stagehand, because `act()` sits in the same file as your selectors.
- **You want the biggest community and a Python agent loop:** browser-use.
  [Its own tradeoffs are covered here](browser-use-alternatives.md).
- **You want a compiled binary with no runtime to install and a daemon that
  holds sessions:** agent-browser.
- **You care that the browser presents as an ordinary desktop browser, and
  you want a run to repeat identically:** invisible_playwright_mcp, ours, conflict noted.

## Short answers to the questions that lead here

**What is Vercel's agent-browser?** A native Rust CLI, Apache-2.0 licensed,
that gives AI agents browser automation: navigation, semantic locators,
screenshots, network interception and multi-session handling, with a daemon
that persists between commands.

**Is agent-browser open source?** Yes, under Apache-2.0 as published in the
vercel-labs repository.

**What is the difference between agent-browser and browser-use?**
agent-browser is a compiled binary an agent shells out to or reaches over
MCP, with no model inside it. browser-use is a Python library with an
LLM-driven agent loop built in: you give it a task, it decides the actions.

**Does Playwright have its own MCP server?** Yes. Microsoft publishes it
under Apache-2.0, it needs Node.js 18 or newer, and it drives Chromium,
Firefox or WebKit while exposing accessibility snapshots rather than
screenshots.

**Is Stagehand the same as Playwright?** No. Stagehand builds on Playwright
and adds act, observe and extract, so a step can be written in plain
language instead of a selector. It ships TypeScript, Python and Go SDKs.

**See also:** [browser-use alternatives](browser-use-alternatives.md) for the
most-adopted option above, [Stagehand vs browser-use](stagehand-vs-browser-use.md)
for a direct comparison of two rows, and
[choosing an AI browser agent](best-ai-browser-agent.md) for the decision
framework these picks come from.

## Sources

- Vercel agent-browser repository, https://github.com/vercel-labs/agent-browser -
  description, Apache-2.0 license, Rust runtime, CLI and MCP interfaces,
  daemon and feature list. Read 5 September 2026.
- browser-use repository, https://github.com/browser-use/browser-use - MIT
  license, Python 3.11 or newer, Playwright underneath, LLM-driven agent
  loop. Read 5 September 2026.
- Playwright MCP repository, https://github.com/microsoft/playwright-mcp -
  Apache-2.0, Node.js 18 or newer, accessibility-snapshot approach, browser
  coverage. Read 5 September 2026.
- Stagehand repository, https://github.com/browserbase/stagehand - MIT
  license, TypeScript, Python and Go SDKs, act/observe/extract on top of
  Playwright. Read 5 September 2026.

---

*From the [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) wiki. invisible_playwright_mcp is one row
in the table above, not the first, and the picks name two other tools before
they name ours.*
