---
title: "MCP vs an API, and MCP vs RAG: three different layers"
description: "MCP is not a competitor to either. It is a standard way to expose capabilities to a model, usually on top of an API, and it solves a different problem from retrieval."
parent: "Alternatives and Comparisons"
nav_order: 36
---

# MCP vs an API, and MCP vs RAG: three different layers

Both comparisons get asked constantly and both are category errors, in
different directions. **MCP usually sits on top of an API rather than replacing
one, and it does something RAG does not do at all.** Worth ten minutes because
picking the wrong layer is expensive to undo.

## MCP vs an API

An API is how two programs talk. MCP is how a **model** is told what it can do
and then does it.

In practice an MCP server is very often a thin wrapper over an API you already
have. The server declares each capability as a tool with a JSON Schema for its
inputs, the model reads those declarations and chooses when to call one, and
the server turns that call into the API request it was always going to make.

What MCP adds on top of the API, and why the wrapper is not pointless:

- **Discovery the model can read.** `tools/list` returns the capabilities with
  their schemas. Your API's OpenAPI document is for developers; this is for a
  model at runtime.
- **One connection shape across every capability.** Files, databases, browsers
  and issue trackers arrive through the same client, so the assistant does not
  need bespoke integration per service.
- **A place for oversight.** Approval prompts, permission settings and activity
  logs sit at this layer rather than in each API client.

**When you do not need it:** if your own code is calling your own API, MCP adds
nothing. The layer earns its keep when a model is choosing.

## MCP vs RAG

These solve different halves of the same sentence. RAG gets **information** in
front of a model. MCP lets the model **act**, and also lets an application
attach information.

The overlap is real but partial, and the protocol itself draws the line: its
three primitives are tools, resources and prompts, and it is **resources** that
look like retrieval - read-only data behind a URI, pulled in by the application
as context.
[MCP tools, resources and prompts](mcp-tools-resources-and-prompts.md) has the
full split.

The differences that decide it:

| | RAG | MCP resources |
|---|---|---|
| Selection | embeddings or search over a corpus | the application picks a URI |
| Freshness | as fresh as the last index build | read at request time |
| Scale | designed for large corpora | designed for specific known things |
| Can it act? | no | tools can, resources cannot |

**Use RAG** when the question is "which of these ten thousand documents is
relevant". **Use MCP resources** when the answer is a specific known thing:
this file, this calendar, this schema. **Use both** when the model needs to
find something and then do something about it, which is the common real case.

## The one-line versions

- MCP vs an API: not competitors. MCP is usually a model-facing layer over an
  API.
- MCP vs RAG: not competitors. RAG retrieves at scale; MCP acts, and attaches
  known context.
- If nothing in your system is a model choosing what to do next, you probably
  need neither.

## Short answers to the questions that lead here

**Does MCP replace REST APIs?** No. It typically wraps one so a model can
discover and call it.

**Is MCP better than RAG?** They answer different questions. RAG finds relevant
text in a large corpus; MCP lets a model take actions and lets an app attach
specific context.

**Can MCP do retrieval?** Resources are read-only data by URI, which covers
"fetch this known thing". It is not a substitute for search over a large
corpus.

**Do I need an MCP server for my own API?** Only if a model, rather than your
code, should decide when to call it.

**Is MCP just function calling with extra steps?** Function calling is the
model-side mechanism; MCP is the transport and discovery standard that lets any
client talk to any server without bespoke wiring. When both ends are yours,
that discovery is a registry with one entry in it, which is the case
[MCP alternatives](model-context-protocol-alternatives.md) makes with the
measured cost attached.

**See also:** [how to choose among MCP servers](best-mcp-servers.md), and
[MCP tools, resources and prompts](mcp-tools-resources-and-prompts.md).

## Sources

- [Understanding MCP servers](https://modelcontextprotocol.io/docs/learn/server-concepts), the protocol's own documentation, retrieved 2026-09-11: the three primitives, `tools/list` and its schemas, resources as read-only URIs retrieved by the application, and the oversight mechanisms described above.

---

*Written while maintaining an MCP server. The section that says you do not need
MCP when your own code calls your own API is the one to check us on, and it is
in the middle of the page rather than the footnotes.*
