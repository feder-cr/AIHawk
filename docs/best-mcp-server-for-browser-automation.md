---
title: "Choosing an MCP server for browser automation: four axes"
description: "Start with Microsoft's, then the four axes that separate the rest: how the model sees the page, sessions, the engine underneath, and the surface size."
parent: "Alternatives and Comparisons"
nav_order: 26
---

# Choosing an MCP server for browser automation

**Start with Microsoft's playwright-mcp.** It is the reference implementation,
Apache-2.0, 36.9k stars when read on 2026-09-10, maintained by the team that
maintains Playwright, and it covers the ordinary case well. If you have no
specific complaint, installing anything else first is a mistake.

This page is for people with a specific complaint. Below are the four axes that
actually separate these servers, and which one changes hands on each.

## Axis 1: how the model sees the page

**Accessibility tree** or **pixels**. playwright-mcp defaults to the tree: the
model receives a structured description with stable references, which is cheap
in tokens and precise to act on. Its `--caps vision` adds coordinate-based
interaction when the tree is not enough.

The tree fails on the things it cannot describe: a canvas, a map, a slider, a
custom widget built out of unlabelled divs. Every serious server therefore needs
both, and the question is not which it has but whether it lets the model fall
back cleanly. A server with only a tree will get stuck silently; a server with
only screenshots will burn tokens on pages a tree would have handled in a
sentence.

**Winner:** playwright-mcp, and most others copy its shape.

## Axis 2: sessions and concurrency

The single most common first-hour failure in this category is two clients
fighting over one profile, which surfaces as
[browser is already in use](playwright-mcp-browser-already-in-use.md).

Servers differ in whether concurrency is a flag or a model. playwright-mcp makes
it a flag: `--isolated`, or a distinct `--user-data-dir` per client.
[AIHawk](https://github.com/feder-cr/AIHawk) makes it a model: named sessions
and named browsers, so opening a browser that already exists focuses it rather
than colliding. Neither is free. A flag is simpler until you need two of
something; a model is more to learn on day one.

**Winner:** depends on whether you will ever run two.

## Axis 3: the engine underneath

This is the axis that no feature table lists and the only one that matters if
your problem is that the site says no.

Almost every MCP server in this space drives a **stock automation build over
CDP**. That is a specific, well-studied set of observable choices, and it
travels with the server regardless of which server you picked. Switching from
one CDP-based server to another does not change it.

The exceptions are the servers built on engines that were modified rather than
scripted: the Camoufox, nodriver and Patchright wrappers, and this project.
[Stealth MCP servers compared](stealth-mcp-servers-compared.md) goes through
them. Read that page for the caveat as well as the list: several of them
advertise capabilities we could not verify, and none of them repairs an IP's
reputation or robotic pacing, which is where most blocks actually come from.

**Winner:** nobody, unless the browser is your problem. Then it is the only axis
there is.

## Axis 4: how much surface it exposes

Tool count is a bad metric that gets used as a good one. A server with a hundred
tools is not more capable than one with twenty; it is harder for a model to
choose within, and every tool description costs context on every turn.

To put a number on the cost rather than assert it, here is ours, read from our
own source on 2026-09-10: **24 tools, 14,064 characters of description, about
3,500 tokens on every turn.** A server advertising a hundred tools of similar
description length is asking for roughly four times that, on every turn, for
the whole session. Ask any server you are evaluating for the same two figures
before believing that more tools is more capability.

What to look for instead: can the model **read** state without scripting, does
it have a **coordinate** path for what selectors cannot reach, and is there a
**JavaScript reader** for the rest. Three properties, not a hundred entries.
[How the tools are shaped, and why](mcp-tool-design.md) is this project's
reasoning on that, and it applies to servers other than ours.

**Winner:** the smallest surface that has all three.

## The one-pass decision

- **No specific complaint:** playwright-mcp.
- **Two clients, or several browsers at once:** a server with a session model,
  or playwright-mcp with `--isolated` per client.
- **You need Firefox or WebKit specifically:** playwright-mcp covers all four
  engines with `--browser`.
- **The site recognises the browser:** the engine axis, and only there does
  ours or the stealth wrappers change anything. Attribute the failure first:
  [why an agent gets blocked](why-does-my-ai-agent-get-blocked.md).
- **You want the browser inside an assistant you already pay for:** any of them.
  That is the whole point of MCP and it is the cheapest thing to try.

## Short answers to the questions that lead here

**What is the best MCP server for browser automation?** playwright-mcp, unless
you can name the thing it does not do for you. Three names for that: two
clients, a non-Chromium engine, or a browser that keeps getting recognised.

**Is there an official Playwright MCP?** Yes, `microsoft/playwright-mcp`.

**Can I use more than one browser MCP server at once?** Yes, clients allow
several. It costs context on every turn, and the model has to choose between
overlapping tools, so it is worth doing deliberately.

**Do MCP browser servers cost money?** The servers listed here are open source.
The model calls are billed by your provider, and a browsing session is a lot of
turns.

**Which one avoids bot detection?** None of them makes that promise honestly.
The engine axis changes what the browser looks like; it does not change your IP,
your pacing or a site's rate limits.

**See also:** [Playwright MCP vs the CLI](playwright-mcp-vs-cli.md),
[Playwright MCP alternatives](playwright-mcp-alternative.md), and
[the MCP server](mcp-server.md) for this project's configuration.

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10: licence, stars, `--caps`, `--browser`, `--isolated` and the accessibility-tree design.
- The stealth-oriented servers surveyed in [stealth MCP servers compared](stealth-mcp-servers-compared.md), with their own retrieval dates.

---

*Written while maintaining one of the servers being compared. It is not the
recommendation at the top, and the axis where it wins is stated as narrowly as
it actually is.*
