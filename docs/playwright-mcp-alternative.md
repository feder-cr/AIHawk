---
title: "Playwright MCP alternatives, and the three you don't need"
description: "Four complaints send people looking for a replacement. Three are fixed by a flag on the server you already have; only one of them needs a real switch."
parent: "Alternatives and Comparisons"
nav_order: 28
---

# Playwright MCP alternatives

Microsoft's [playwright-mcp](https://github.com/microsoft/playwright-mcp) is
Apache-2.0, 36.9k stars when read on 2026-09-10, and maintained by the Playwright
team. **If you cannot name what it fails to do for you, there is no reason to
replace it.** This page is organised around the four complaints that are real,
because three of them have a fix that is not a different server.

## Complaint 1: two clients cannot share it

The most common one, and it arrives as
[browser is already in use](playwright-mcp-browser-already-in-use.md). A
persistent profile can only be opened by one browser at a time, and the server
defaults to a single fixed profile.

**Fix without switching:** `--isolated` for a throwaway profile per session, or
a distinct `--user-data-dir` per client. Both are documented options.

**When a switch is warranted:** if your client only lets you register a bare
command with no arguments, you may not be able to pass either flag, and a server
whose concurrency is a model rather than a flag saves you the fight. Servers
with named sessions - [AIHawk](https://github.com/feder-cr/AIHawk) among them -
treat two browsers as two named things rather than a collision.

## Complaint 2: it costs too much context

Every tool description is in the model's context on every turn, and a browsing
session is a lot of turns. Reasonable complaint, wrong first move.

**Fix without switching:** trim the capability set. `--caps` is additive, so do
not enable vision, pdf and devtools if you are not using them. Do not register a
second browser server alongside it "just in case": the overlapping tool names
also make the model choose worse, not just cost more.

**When a switch is warranted:** if you genuinely need one job done, a four-tool
server does it with a fraction of the surface. That is the design point of the
smallest wrappers listed in
[stealth MCP servers compared](stealth-mcp-servers-compared.md).

## Complaint 3: the site keeps recognising the browser

The one case where the alternative really is a different server, because the
cause is the engine and no flag reaches it. playwright-mcp drives a stock
automation build; that is a specific set of observable choices and it travels
with the server.

**Before switching, attribute the failure.** Most reports of "the agent gets
detected" are machine and network facts that no server changes: a datacenter IP,
no GPU, a container font set, or an agent clicking faster than a person can.
[Why an agent gets blocked](why-does-my-ai-agent-get-blocked.md) works through
how to tell which one you have. Switching servers over an IP problem costs you a
day and fixes nothing.

**If it really is the browser:** the engine-modified servers are the row that
differs. Camoufox, nodriver and Patchright wrappers, and this project.
[Stealth MCP servers compared](stealth-mcp-servers-compared.md) is the
comparison, including which of their claims we could not verify.

## Complaint 4: it does the wrong kind of work

Sometimes the alternative to an MCP server is not an MCP server.

If you are running the same known flow every night, a model rediscovering it
each time is slower and more expensive than a script.
[Playwright MCP vs the CLI](playwright-mcp-vs-cli.md) has the split. If you are
pulling structured data at volume, see
[MCP for web scraping](mcp-for-web-scraping.md): the working pattern is a model
to establish the shape once and plain code for the repetition. If you want an
autonomous program rather than a tool inside your assistant, you want an agent
library - browser-use, Skyvern, Stagehand - and
[open-source agentic browsers](agentic-browser-open-source.md) lays out that
layer.

## The alternatives, plainly labelled

**Engine-modified MCP servers.** Camoufox, nodriver and Patchright wrappers.
Address complaint 3 only. Younger and smaller than Microsoft's, so check push
dates.

**AIHawk** (ours, MIT). A Firefox patched at the C++ source, identity derived
from a seed so a failing run replays exactly, named sessions and browsers, and
the agent interface in the same package. Addresses complaints 1 and 3. It does
not make the model better, does not solve captchas, and covers Windows and Linux
only.

**Agent libraries.** Not MCP at all. The right answer to complaint 4 when you
wanted a program.

**Staying, with flags.** The right answer to complaints 1 and 2 most of the
time, and the cheapest.

## Short answers to the questions that lead here

**Is there a better Playwright MCP?** Better at a named thing, yes. Better in
general, no, and any page telling you otherwise is selling something.

**What is the closest alternative to Microsoft's server?** Functionally, the
Camoufox and Patchright wrappers - the same shape with a different engine.

**Can I run two MCP browser servers at once?** Yes, and it costs context on
every turn plus a harder choice for the model. Prefer one, configured properly.

**Does an alternative server make my agent undetectable?** No. Nobody can say
that honestly. The engine changes what the browser looks like and nothing else.

**Is playwright-mcp being maintained?** Yes, actively, by the Playwright team.
The alternatives are the ones where maintenance tempo is worth checking.

**See also:** [Choosing an MCP server for browser automation](best-mcp-server-for-browser-automation.md),
[Playwright MCP best practices](playwright-mcp-best-practices.md), and
[the MCP server](mcp-server.md).

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10: licence, stars, `--isolated`, `--user-data-dir`, `--caps`.
- The wrappers and engines surveyed in [stealth MCP servers compared](stealth-mcp-servers-compared.md), with dates.

---

*Written while maintaining an alternative to the tool this page is about. Three
of the four complaints resolve without us, and they are listed first for that
reason.*
