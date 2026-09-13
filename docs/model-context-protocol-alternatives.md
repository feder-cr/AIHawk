---
title: "MCP alternatives: when the protocol is the wrong shape"
description: "MCP buys discoverability and charges for it on every turn. The four alternatives, what each one costs instead, and the measured price of the one we ship."
parent: "Alternatives and Comparisons"
nav_order: 37
---

# MCP alternatives

MCP solves one problem well: **letting a model find out what it can do, from a
thing nobody wrote into the model's prompt.** A host registers a server, the
server declares its tools, and the model can use something its author never
heard of. That is genuinely new, and it is why the standard spread.

It charges for that, on every turn, forever. Whether the charge is worth it
depends on a question with a clear answer: **does the model need to discover
this, or do you already know what you want done?**

**This page is about not using MCP.** If you have already decided you want an
MCP server and are only choosing which one, the page you want is
[Playwright MCP alternatives](playwright-mcp-alternative.md) for browsers, or
[how to choose among MCP servers](best-mcp-servers.md) for the rest.

## The price, measured

Enumerated from our own browser server's tool registry on 2026-09-13 and counted
with a tokenizer: **16 tools, 3,192 tokens**, sent again on every single turn of
every session. A forty-turn session spends around 128,000 tokens restating what
the tools are, before a page has been read.

That is not a criticism of MCP; it is the mechanism working. Discoverability
means the description has to be present for the model to discover it. But it is
the number to hold against every alternative below, because **every alternative
below costs zero per turn** and pays somewhere else instead.
[How many MCP tools is too many](how-many-mcp-tools-is-too-many.md) is the same
figure from the inside.

## The four alternatives

**A library, imported directly.** You write code that calls the thing. No
protocol, no server, no descriptions in context, no model deciding whether to
call it. This is the right answer far more often than the current conversation
suggests, and it is the one people skip because it feels like a step backwards.
It is only a step backwards if the step forward was discovery, and in a script
you wrote, it was not.

**Provider-native function calling.** You hand the model a list of function
schemas in your own request and dispatch what it picks. The model still chooses,
which is the part MCP is often credited with; what you give up is
interoperability, because your definitions live in your application and nobody
else's host can find them. What you gain is control over exactly what is sent,
when. If your tool list is fixed and yours, this is MCP without the registry.

**A plain API, with the model out of the loop.** The strongest option and the
easiest to overlook. If the sequence of calls is known, a model deciding it
again on every run is the expensive way to run a script you could have written,
and it is less reproducible: nothing guarantees the same decision on the four
thousandth item as on the third.
[Playwright MCP vs the CLI](playwright-mcp-vs-cli.md) is this argument applied to
browsers, and [MCP for web scraping](mcp-for-web-scraping.md) is it applied to
the case where the repetition is the whole job.

**An agent framework.** Not an alternative to MCP so much as a different layer:
most of them can consume MCP servers. If what you actually wanted was a program
that loops, retries and keeps state, the protocol was never the missing piece.

## The test that decides it

One question, and it is not about your tooling:

> **Is the next step knowable before you run it?**

If yes, everything above beats MCP, and the plain API beats all of them. If no,
because the page is different every time, because the answer determines the next
call, because a hundred sources have a hundred shapes, then a model choosing
among declared tools is worth 3,192 tokens a turn and there is no cheaper way to
get it.

The second question is narrower and decides between MCP and native function
calling: **does somebody else need to find these tools?** MCP's real product is
that an assistant you did not write can use a server you did not write. If both
ends are yours, you are paying for a registry with one entry in it.

## What we did about our own answer

Worth saying, since this page is published by people who ship an MCP server.

Until version 0.9.0 this project's interface lived inside the server process and
reached the browser directly, because it was right there. It was moved out, and
it now talks to the server over MCP like any other client. That is the opposite
of the trade this page recommends, and the reason is the one case where it holds:
**a privileged path means the tools are never proven sufficient.** If the
flagship interface can reach around the protocol, the protocol quietly becomes a
second-class way to do things, and the gaps only show up for other people. Being
our own client is how the tool surface gets tested by the thing we care about
most.

So the recommendation is not "avoid MCP". It is that the protocol earns its cost
where discovery is real, and that a great many things sold as needing it are a
function call with extra steps.

## Short answers to the questions that lead here

**What is an alternative to MCP?** A library import, provider-native function
calling, a plain API with no model in the loop, or an agent framework. Which one
depends on whether the next step is knowable.

**Is MCP better than function calling?** Different. Function calling is your
tools in your app; MCP is anybody's tools in anybody's host. If both ends are
yours, function calling is cheaper and simpler.

**Do I need MCP to give a model tools?** No. Every provider supports tool
definitions directly.

**Is MCP going away?** Nothing here suggests so, and the point of this page is
not to bet on that. It is that a standard being good does not make it the right
shape for one particular job.

**What does MCP cost?** Measured on ours: 3,192 tokens on every turn for 16
tools. Yours scales with description length and argument schemas, not just tool
count.

**See also:** [How to choose among MCP servers](best-mcp-servers.md),
[MCP versus an API and versus RAG](model-context-protocol-vs-api-vs-rag.md), and
[how to build an MCP server](how-to-build-an-mcp-server.md).

## Sources

- This project's own MCP server, enumerated through its tool registry on 2026-09-13: 16 tools, 3,192 tokens for the complete definitions, counted with `tiktoken` rather than estimated.
- [The MCP transports overview](https://modelcontextprotocol.io/docs/concepts/transports), retrieved 2026-09-13, for what the protocol does and does not define.

---

*Written by people who ship an MCP server and moved their own interface onto it.
The recommendation most against our interest is the third one, and it is third
because it is right more often than the two above it.*
