---
title: "MCP on GitHub: finding servers and judging them fast"
description: "The protocol, the SDKs and most servers live in public repositories. Where each one is, and the four checks that separate a maintained server from an abandoned demo."
parent: "Alternatives and Comparisons"
nav_order: 35
---

# MCP on GitHub: finding servers and judging them fast

Most of MCP is public code. That is genuinely useful and it also means the
ecosystem is full of weekend demos that look identical to production servers
from a search result. This page is where things are, and how to tell them
apart in about two minutes.

## Where the pieces live

**The protocol itself** is specified at `modelcontextprotocol.io`, with the
specification, the SDKs and reference servers published under the
`modelcontextprotocol` organisation. If you are implementing rather than
installing, start there rather than from a blog post: the SDKs exist for
several languages and the protocol methods are documented rather than inferred.

**Vendor servers** live with their vendor: Microsoft publishes the Playwright
one, the Chrome DevTools team publishes theirs.
[Playwright MCP vs Chrome DevTools MCP](playwright-mcp-vs-chrome-devtools-mcp.md)
compares those two, which are the largest browser-adjacent ones.

**Community servers** are everywhere else, and outnumber the first two
categories by a wide margin.

**Directories** aggregate all of the above. They are a decent way to discover
and a poor way to judge: listing is not curation, and a directory entry tells
you nothing about whether the thing still works.

## The four checks, in order

**1. Last commit, not stars.** Stars accumulate and never decay; a server with
eight thousand stars and no push in a year is a worse dependency than one with
two hundred pushed last week. MCP moved fast enough in 2025 and 2026 that a
year-old server may not speak the current protocol revision.

**2. Who owns it.** A server wrapping a product, published by that product's
own organisation, is maintained as a side effect of the product existing. A
community wrapper is maintained while its author is interested.

**3. The tool list, before you register it.** `tools/list` is a protocol
method, so you do not have to read the source to know what a server can do -
any client will enumerate it. Look for tools that write, delete or send, and
decide deliberately rather than discovering later.

**4. The size of the surface.** Tool descriptions ride in the model's context
on every turn, argument schemas included. Measured on our own server: 16
tools, 9,145 characters of description, 3,192 tokens per turn. A server
advertising a hundred tools is asking for several times that, forever.
[How many MCP tools is too many](how-many-mcp-tools-is-too-many.md) has the
arithmetic.

## What a README will not tell you

**Whether it handles concurrency.** Two clients, one server, one profile
directory is the most common first-hour failure in the browser category and it
has nothing to do with code quality:
[browser is already in use](playwright-mcp-browser-already-in-use.md).

**What it does when something fails.** A demo returns a stack trace to the
model. A production server returns something the model can act on.

**Whether its claims were tested.** Several servers in the stealth corner
advertise capabilities we could not verify, which is stated plainly in
[stealth MCP servers compared](stealth-mcp-servers-compared.md) along with
what our own does not do.

## Short answers to the questions that lead here

**Where is the official MCP GitHub organisation?** Under
`modelcontextprotocol`, alongside the specification site, with SDKs and
reference servers.

**How do I find MCP servers on GitHub?** Directories and topic searches both
work for discovery. Neither judges: apply the four checks above.

**Are community MCP servers safe?** They run with whatever access you grant and
expose tools that act. Read `tools/list` before registering, and prefer
read-only where the choice exists.

**Which MCP server should I start with?** Depends on the capability you want.
[How to choose among MCP servers](best-mcp-servers.md) maps the categories.

**Is there an official list of MCP servers?** The protocol organisation
publishes reference servers; third-party directories cover the rest with no
curation guarantee.

**See also:** [the MCP server](mcp-server.md), and
[MCP tools, resources and prompts](mcp-tools-resources-and-prompts.md) for what
a server can expose in the first place.

## Sources

- [The Model Context Protocol documentation](https://modelcontextprotocol.io/docs/learn/server-concepts), retrieved 2026-09-11, for the protocol operations including `tools/list` and for the SDK and reference-server layout.
- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) and [ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp), retrieved 2026-09-10, as the two vendor-published examples named above.
- This project's own server source, read 2026-09-13, for the tool-surface measurement.

---

*Written while maintaining a community MCP server, which is the category this
page tells you to check hardest. The four checks apply to ours: read our tool
list before registering it.*
