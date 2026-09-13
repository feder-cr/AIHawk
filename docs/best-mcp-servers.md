---
title: "How to choose among MCP servers: a map by category"
description: "There is no single best MCP server, because they do unrelated jobs. The seven categories that exist, what to check inside each, and the cost every one adds."
parent: "Alternatives and Comparisons"
nav_order: 33
---

# How to choose among MCP servers: a map by category

"Best MCP server" is the wrong question in the same way "best library" is. MCP
servers give an assistant a capability it did not have, and the capabilities are
unrelated: reading your files, querying a database, driving a browser, filing
issues. **Pick the category first, then judge inside it.**

## The seven categories that actually exist

**Filesystem and local data.** Read and write files on the machine the
assistant runs on. The most common first install, and the one with the widest
blast radius: an assistant that can write files can write the wrong file.

**Code hosting.** Issues, pull requests, repository contents. Useful the moment
your assistant is doing anything about a codebase it cannot see.

**Databases.** Schema and queries. The interesting design question here is
read-only versus read-write, and the honest default is read-only.

**Browsers.** Navigate, read and act on live pages. This is the category with
the most servers in it and the most differentiation, which is why it has its
own page here:
[choosing an MCP server for browser automation](best-mcp-server-for-browser-automation.md).

**Communication.** Slack, email, calendars. Reading is usually safe, sending is
where you want a confirmation step.

**Developer tooling.** Debuggers, profilers, log search. Chrome DevTools MCP is
the prominent one and it is not a browser-automation server despite driving a
browser:
[Playwright MCP vs Chrome DevTools MCP](playwright-mcp-vs-chrome-devtools-mcp.md)
separates them.

**Search and retrieval.** Web search, documentation, internal knowledge bases.

## What to check, inside whichever category

**Who maintains it.** A server written by the vendor of the thing it wraps is
usually better maintained than a community wrapper, and community wrappers
outnumber official ones. Check the last commit before the star count.

**What it can do to you.** A server declares tools, and tools act. Read the
tool list before registering: `tools/list` is a protocol method, so any client
can show you exactly what a server exposes. A server that can delete should be
a deliberate choice.

**What it costs in context.** Every tool description travels in the model's
context on every turn, and so does the JSON schema of its arguments. Measured on our own browser server on 2026-09-13: **16 tools, 3,192 tokens resent on every single turn**
(9,145 characters of description, counted with a tokenizer). Two servers of that
size on a forty-turn session spend about 255,000 tokens restating what the tools
are, before a single page has been read.

**Whether you will actually use it.** The most common mistake is registering
five servers because they were interesting. Every one costs context and adds
verbs for the model to choose wrongly between.

## The short answer for the common setups

- **Coding assistant, nothing else installed:** filesystem plus your code host.
  Those two cover most of what people mean by wanting MCP.
- **The assistant needs to see a live page:** one browser server, not two.
- **You are debugging your own site's performance:** developer tooling, not
  browser automation.
- **You want it to touch production data:** read-only first, and add write
  access only for the specific thing that needed it.

## Short answers to the questions that lead here

**What is the best MCP server?** Not a question with an answer. Pick the
category you need, then judge maintenance, tool surface and context cost inside
it.

**How many MCP servers should I register?** As few as do the job. Each one
costs context on every turn and makes the model's choice harder.

**Are official MCP servers better than community ones?** Usually better
maintained, which is the property that matters over a year. Check the last
commit date either way.

**Where do I find MCP servers?** Directory sites and the protocol's own
ecosystem listings exist; the useful filter is maintenance, not count.

**Do MCP servers cost money?** The servers listed in these categories are
generally open source. The model calls they cause are billed by your provider,
and an agentic session is turn-heavy.

**See also:**
[the MCP server](mcp-server.md) for this project's own,
[MCP tools, resources and prompts](mcp-tools-resources-and-prompts.md) for what
a server can actually expose,
[how many MCP tools is too many](how-many-mcp-tools-is-too-many.md) for the
context arithmetic, and
[MCP alternatives](model-context-protocol-alternatives.md) for when the answer
is that you did not need a server at all.

## Sources

- [The Model Context Protocol documentation](https://modelcontextprotocol.io/docs/learn/server-concepts), retrieved 2026-09-11, for the protocol operations named above including `tools/list`.
- This project's own MCP server source, read 2026-09-13, for the tool-count and description-size measurement.

---

*Written while maintaining a browser MCP server, which is one entry in one of
the seven categories. It is named in the category where it belongs rather than
at the top, and the section arguing for fewer servers argues against
registering ours alongside another.*
