---
title: "How many MCP tools is too many? The context arithmetic"
description: "Every tool description rides in the model's context on every turn. Our own server measured, what that costs over a session, and the two failures that arrive before the budget does."
parent: "Using the Agent"
nav_order: 41
---

# How many MCP tools is too many? The context arithmetic

There is no protocol limit, so the honest answer is a calculation rather than a
number. **Every tool a server exposes puts its name, description and input
schema into the model's context on every single turn** - not once at the start.
Multiply by turns.

## The measurement, from our own server

Nobody publishes this figure, so here is ours, enumerated from the running
server's own tool registry on 2026-09-13 and counted with a tokenizer rather
than a characters-per-token rule of thumb:

| | |
|---|---|
| Tools exposed | **16** |
| Description characters | 9,145 |
| Tokens, descriptions alone | 2,123 |
| Tokens, complete definitions resent every turn | **3,192** |
| Median tokens per tool | 180 |

A forty-turn browsing session therefore spends on the order of **128,000
tokens** restating what the tools are, before counting a single page of content
or a word of the model's reasoning. Two servers of that size, and it doubles.

**The gap between the third row and the fourth is the part to take away.** A
tool is not sent as its description; it is sent as a name, a description and a
JSON schema for its arguments, and the schema is a third of the weight here.
Counting descriptions alone is the natural way to measure and it understates the
bill by half as much again - which is what an earlier version of this page did,
and the correction is the reason the row is broken out rather than folded in.
When you measure your own server, enumerate what the protocol actually hands
over, not the docstrings you wrote.
[How to build an MCP server](how-to-build-an-mcp-server.md) carries the ten
lines that do it.

That is the arithmetic. It is not an argument against tools; it is the reason
the answer to "how many" is "as few as do the job".

## The two failures that arrive before the budget does

**Choice degradation, which happens earlier than the cost.** A model picking
among 16 well-separated tools does it reliably. Among 100 with overlapping
verbs - three ways to read a page, two ways to click - it picks a plausible
wrong one, and you pay for the retry as well. This bites before the token bill
does, and it bites small models hardest.

**Silent truncation in the client.** Editors and chat clients cap how many
tools they will offer at once. Cross the cap and some tools simply stop being
available, usually without a message that says so. If a tool you know exists
is being ignored, count your registered servers before debugging the server.

## Practical ceilings

- **One browser server, not two.** The overlap is total and the cost doubles.
- **Enable capabilities, do not accept all of them.** Servers that make
  capabilities additive - vision, pdf, devtools as separate opt-ins - let you
  pay only for what you use.
- **Around 15-25 tools from one server is workable**; our 16 covers browsers, reading, pointer,
  keyboard, a live view and a JavaScript reader without overlapping
  verbs. Past that, ask what a new tool does that an existing one cannot.
- **Count across servers, not per server.** The model sees the union.

## Fewer tools, or better-shaped tools

The more useful reframing: a large surface is usually a symptom of tools shaped
around implementation rather than intent. Three properties cover most of what a
browser server needs - read the state, reach what selectors cannot, fall back to
JavaScript - and a server that has those three does not need thirty verbs.
[How the tools are shaped, and why](mcp-tool-design.md) is this project's
reasoning on that, and
[MCP tools, resources and prompts](mcp-tools-resources-and-prompts.md) covers
the case where the thing you were about to make a tool should have been a
resource or a prompt instead.

## Short answers to the questions that lead here

**Is there a hard limit on MCP tools?** Not in the protocol. Clients impose
their own caps, and the model's ability to choose degrades before any cap.

**How much context do MCP tools use?** Ours: 3,192 tokens on every turn, for 16
tools. Yours scales with description length and argument schemas, not just
count.

**Why is my MCP tool being ignored?** Most often too many tools registered
across all servers, so the client silently offered a subset. Second most often,
two tools whose descriptions overlap.

**Should I split one server into several?** It does not help: the model sees
the union of everything registered. Splitting helps only if you then register
just one of them.

**Does a shorter description save money?** Yes, linearly, on every turn. It also
makes the choice worse if you cut the part that says when to use the tool.

**See also:**
[how to choose among MCP servers](best-mcp-servers.md) and
[Playwright MCP best practices](playwright-mcp-best-practices.md), whose first
of four decisions is exactly this budget.

## Sources

- This project's own MCP server, enumerated through its tool registry on 2026-09-13: 16 tools, 9,145 characters of description, 3,192 tokens for the complete definitions, median 180 tokens per tool. Tokens counted with `tiktoken` (`o200k_base`), not estimated from character count.
- [The Model Context Protocol documentation](https://modelcontextprotocol.io/docs/learn/server-concepts), retrieved 2026-09-11, for `tools/list` and the schema-defined shape of a tool.

---

*Written while maintaining a 16-tool server, which is the number this page uses
as its example rather than as its recommendation. The measurement is published
because the advice is worthless without it.*
