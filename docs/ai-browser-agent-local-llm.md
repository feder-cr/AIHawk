---
title: "AI browser agent with a local LLM: what changes"
description: "AIHawk's interface only calls OpenRouter. How to attach this browser to a client running a local model, and why privacy, not capability, is the real payoff."
parent: "Using the Agent"
nav_order: 25
---


# AI browser agent with a local LLM: what changes

A local model changes exactly one thing about this browser: where the model runs.
AIHawk's own interface only ever calls OpenRouter, there is no local-model flag. To
actually drive this browser with a model on your own machine, you attach it to an
assistant or client that already runs one, over the same MCP connection Claude Code
uses.

## The two routes, and the one that is not actually local

`aihawk ui --openrouter-key ...` reaches OpenRouter and nowhere else. That is not
a default that can be pointed elsewhere with a flag: `src/aihawk/llm.py` hardcodes the
OpenRouter base URL, and the `ui` command refuses to start at all without a key. If
you came here hoping for `--ollama`, it does not exist in the current source.

The library underneath has the opposite property: `invisible_playwright`, the plain
Python package this interface talks to over MCP, carries no model at all. Local, in
the sense that the weights never leave your machine, is not a setting on AIHawk's own
interface. It is a different door: an assistant or client that already runs a model
locally, most commonly through something like Ollama's own API, attaching this same
browser to it exactly the way any other MCP client would. Ollama has served tool
calls since 2024, exposing them through a `tools` parameter on its chat API and
answering with a `tool_calls` response, and its OpenAI-compatible endpoint accepts
the same shape, which is what makes this route possible at all. Which desktop
clients wire a local model to MCP changes fast enough that naming one here would
age badly; check your client's own documentation for MCP support before planning
around it.

## Adding the browser to a client that already has its model sorted

The attachment mechanics do not change based on where the model lives. The
[Claude Code walkthrough](running-aihawk-with-claude-code.md) documents the exact
shape, even though Claude Code's own model is hosted rather than local:

```bash
claude mcp add --scope user stealth -- invisible-playwright-mcp
```

One command, once, and the browser's tools show up in that client from then on. A
client built around a local model takes the equivalent command or config screen for
adding an MCP server; the package on the other end, `invisible-playwright-mcp`, the
tool names it exposes, and the roughly quarter-gigabyte engine it downloads on first
use are identical regardless of what is asking. The server has no idea whether the
model calling it runs on your GPU or on someone else's, and that is by design: it
only ever sees tool calls.

## What browser driving specifically demands from a model

[Which model to use with AIHawk](which-model-to-use-with-aihawk.md) lays out what
this task actually exercises: well-formed tool calls on every turn, instructions
followed closely enough to know when a task is actually done, and long, messy context
made mostly of extracted page text. Every word of that applies to a local model, and
two of the three get harder at smaller scale.

Context length is the first one to clear. A structural read of an ordinary page is
thousands of characters on its own, and in a resent-transcript loop that one read is
paid again on every later turn, so a model that runs out of room partway through a
task cannot finish it regardless of how well it reasons. Read the context window of
the exact model tag you are pulling, not the family's headline number, and compare
it against a real page read rather than a hello-world prompt. The second is
patience across turns: a real task rarely finishes in
one or two calls, and local inference on ordinary hardware is commonly slower per turn
than a well-provisioned hosted API, so the wait compounds turn over turn more than it
would against a fast one.

## Where small local models lose the thread

Be honest about the failure mode before it costs an afternoon of debugging the wrong
thing. After enough turns of a growing, resent transcript, a smaller model tends to
repeat a click it already tried, lose a constraint from the original instruction, or
declare the task finished with steps still undone. These are the same model-side
symptoms [the diagnostic page](browser-problem-or-model-problem.md) lists for any
model; a smaller local one just hits them sooner and more often, because the same
growing context that eventually strains a frontier model strains a smaller one
several turns earlier. That is not a defect in the browser: the page loaded, the tool
call worked, the model simply lost the thread of its own multi-step task.

## The one win that has nothing to do with capability

Even a local model that stumbles on turn eighteen already delivered its real benefit
on turn one: the page content it read went to a process on your own machine and
nowhere past it. The OpenRouter route sends that same text to whichever provider ends
up serving the model you picked, simply by routing a request to a hosted API. For a
page you would not want logged on a third party's servers, an internal dashboard, an
account page, anything sensitive, a local model is the one route where that stays true
regardless of how capable the model turns out to be. That is a reason to accept a
weaker model on purpose, not to expect a strong one.

## Telling a model problem from a browser problem on a local model

The model-free replay described on
[browser problem or model problem?](browser-problem-or-model-problem.md) fits a local
setup well, because it shares the same premise: nothing sent anywhere, nothing spent.
Run the failing step against the `invisible_playwright` library directly, no model
attached. If the failure reproduces, no model change, local or hosted, will fix it. If
the replay goes through cleanly, the local model is the variable, and the next move is
a larger local model, or one hosted run on the same task and seed, before concluding
the whole local approach is the wrong fit.

## Short answers to the questions that lead here

**Can I use a local model with AIHawk's own interface?** No. `aihawk ui` only
ever calls OpenRouter, hardcoded in the source. A local model means attaching this
browser to a different client over MCP instead.

**What does a local model actually buy me for browser agent work?** Mostly privacy:
page content stays on your machine instead of reaching whichever provider serves a
hosted model. Capability is usually the trade, not the goal.

**Why does a local model seem to forget the task partway through?** The transcript
grows every turn, and a smaller model's grip on an early instruction or tool result
tends to loosen sooner than a larger one's. The same demand hits every model; a
smaller one just fails sooner.

**Do I need Ollama specifically?** Not by requirement. Any client that speaks MCP for
tools and already has a local model sorted, however it serves that model, attaches
this browser the same way. Which clients currently do that changes too fast to name
reliably here.

**How do I know if a bad run is the local model or the browser?** Replay the failing
step with no model against the library: if it reproduces, the browser side is at
fault regardless of any model; if not, the model was the variable.

**See also:** [running an agent unattended on a schedule](run-ai-agent-on-a-schedule.md) for the other half of the running question, [Which model to use with AIHawk](which-model-to-use-with-aihawk.md),
[Browser problem or model problem?](browser-problem-or-model-problem.md), and
[Running AIHawk's browser from Claude Code](running-aihawk-with-claude-code.md).

## Sources

Retrieved 2026-09-05.

- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), this repository's README,
  `src/aihawk/llm.py` (the hardcoded OpenRouter base URL and default model) and
  `src/aihawk/cli.py` (the `ui` command's key requirement and its own note that
  driving the browser without a model at all is the `invisible_playwright` library's
  job).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. This interface has
never had a local-model flag to remove; the local route has always run through a
different client entirely, and that is worth saying plainly before anyone goes
looking for a setting that isn't there.*
