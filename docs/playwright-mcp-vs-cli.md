---
title: "Playwright MCP vs the Playwright CLI: which fits when"
description: "Not competing tools. The CLI runs a script you wrote; MCP lets a model pick the next step. Which fits exploration, which fits CI, and three wrong picks."
parent: "Using the Agent"
nav_order: 31
---

# Playwright MCP vs the Playwright CLI

Short answer: **the CLI executes a script you already wrote; the MCP server lets
a model decide the next step while the page is open.** They are different points
in the same workflow, and the reason the comparison keeps getting searched is
that both are marketed as "browser automation" and neither page says what the
other is for.

## What each one actually is

**The Playwright CLI** (`npx playwright test`, `playwright codegen`,
`playwright show-trace`) is a test runner and its tooling. You give it a file of
assertions. It runs them, in parallel, headless, deterministically, and tells
you which failed with a trace you can step through. It has no model in it and no
opinion about what to do next.

**Playwright MCP** is a server that speaks the Model Context Protocol. An
assistant connects to it and gets tools: open a tab, snapshot the page, click,
type, press a key. The model calls those one at a time and looks at what came
back before deciding the next call. Microsoft ships it at
[microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp),
Apache-2.0, 36.9k stars when read on 2026-09-10, and it exposes the page to the
model as an accessibility tree rather than a screenshot, so the model reads
structure instead of pixels.

The load-bearing difference is **who decides the next action**. In the CLI, you
did, when you wrote the file. In MCP, the model does, now, having seen the page.

## Which one you want

| You are | Use | Why |
|---|---|---|
| Writing regression tests | CLI | Determinism and parallelism are the whole point, and a model in the loop destroys both |
| Running the same known flow nightly | CLI | It is a script. A model would re-derive the same steps every night and charge you for it |
| Exploring a site you have never seen | MCP | The step after the next one depends on what the page says |
| Debugging why a selector broke | MCP first, then CLI | Ask the model what the page looks like now, then fix the test |
| Handling a flow that changes shape between runs | MCP | This is the case the CLI cannot express |
| Turning a manual flow into a test | Both | Drive it once over MCP, then write the CLI test from what worked |

**`codegen` is the third thing, and it confuses this comparison.**
`playwright codegen` records your clicks and prints a script. That is the CLI
family, not the MCP family: it produces code from a human, where MCP produces
actions from a model. If what you wanted was "watch me do it once and write it
down", `codegen` is the cheaper answer and it costs no tokens.

## The three wrong picks people make

**Using MCP for a nightly job.** Every run pays for the model to rediscover a
flow that has not changed. It is slower, more expensive and less repeatable than
the script it should have become after the first successful run. Use MCP to
find the flow, then commit the flow.

**Using the CLI for a page whose structure moves.** If your test file is mostly
`try` blocks and retries because the site keeps changing, you are hand-rolling
the thing the model does natively. That is the case MCP exists for.

**Expecting MCP to be faster.** It is not. Each step is a round trip through a
model. A CLI test doing forty steps finishes while an MCP session is still on
step five. Speed is not why you would pick it.

## Where this project sits

[AIHawk](https://github.com/feder-cr/AIHawk) is the MCP shape, not the CLI shape,
with one difference from Microsoft's server that matters only in one situation:
the browser underneath is a Firefox patched at the C++ source rather than a
stock automation build. That changes what a defended site sees, and nothing
else. It does not make the model smarter, it does not make the steps faster, and
for writing tests you still want the CLI.

If you are choosing between MCP servers rather than between MCP and the CLI,
[choosing an MCP server for browser automation](best-mcp-server-for-browser-automation.md)
is the comparison, and [the MCP server](mcp-server.md) has our config block and
tool list.

## Short answers to the questions that lead here

**Is Playwright MCP a replacement for Playwright?** No. It is a way for a model
to drive Playwright. The library and the test runner are unchanged underneath.

**Can I run Playwright MCP in CI?** You can, and usually should not. CI wants a
deterministic script; if a model picks the steps, a green run does not prove the
same thing twice.

**Is Playwright MCP free?** The server is Apache-2.0 and costs nothing. The
model calls it makes are billed by whoever provides your model.

**Which is better for scraping?** Neither, alone. See
[MCP for web scraping](mcp-for-web-scraping.md): the honest pattern is a model
to work out the shape and plain code to do the repetition.

**Does Playwright MCP work with Firefox?** Yes, `--browser firefox` is one of
its documented options, alongside chrome, webkit and msedge.

**See also:** [Playwright MCP best practices](playwright-mcp-best-practices.md),
[when a Playwright MCP session gets blocked](playwright-mcp-blocked.md), and
[the browser is already in use](playwright-mcp-browser-already-in-use.md) for
the error most people hit in their first hour.

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10: licence, stars, browser options, and the accessibility-tree design.
- [Playwright's own documentation](https://playwright.dev/docs/test-cli) for what the test CLI does.

---

*Written while maintaining an MCP browser server, so the row that says "use the
CLI" is the one to check us on. It is there because it is right more often than
the row that recommends us.*
