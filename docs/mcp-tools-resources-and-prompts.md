---
title: "MCP tools, resources and prompts: who controls each"
description: "The protocol has three server primitives and they differ by who initiates them: the model, the application, or the user. What that means when you build or pick one."
parent: "Using the Agent"
nav_order: 40
---

# MCP tools, resources and prompts: who controls each

An MCP server can expose three kinds of thing, and the difference between them
is not what they contain. It is **who decides when they are used**.

| Primitive | What it is | Who controls it |
|---|---|---|
| **Tools** | Functions the model can call, which act | The model |
| **Resources** | Read-only data the client can pull in as context | The application |
| **Prompts** | Parameterised templates for a task | The user |

That column on the right is the whole design, and it is the part that most
introductions skip.

## Tools: the model decides

A tool is a schema-defined function. The server declares its name, a
description and a JSON Schema for its inputs; the model reads that and decides
when to call it. `tools/list` discovers them, `tools/call` runs one.

Because the model chooses, two things follow. The description is not
documentation, it is the input on which the choice is made - a vague one gets
the tool called at the wrong moment. And tools act, so the protocol expects
human oversight around them: approval dialogs, pre-approved safe operations,
activity logs. A tool that writes should not be silently auto-approved.

This is also where the cost lives, because every description is in context on
every turn:
[how many MCP tools is too many](how-many-mcp-tools-is-too-many.md) has the
arithmetic with our own numbers.

## Resources: the application decides

A resource is passive data behind a URI - `file:///Documents/notes.md`,
`calendar://events/2026`. The model does not fetch it; the **application** does,
and then decides how much of it to put in front of the model.

Two discovery shapes: direct resources with a fixed URI, and resource templates
with parameters, like `weather://forecast/{city}/{date}`, which are
self-documenting and support parameter completion. Clients can also subscribe to
changes and get notified when a watched resource updates.

The practical consequence people miss: **if you want the model to be able to go
and get something on its own, that is a tool, not a resource.** A resource is
context the application chose to include.

## Prompts: the user decides

A prompt is a reusable template with declared arguments, invoked explicitly -
typically a slash command or a palette entry. It is the server author's way of
saying "here is how this server is meant to be used", which is why a good
server ships prompts even though nothing forces it to.

Nothing triggers a prompt automatically. That is the point: it is the one
primitive where the human is in the loop by construction.

## Choosing between them when you build

- **The assistant should be able to do this whenever it judges it useful:**
  tool.
- **This is data the user or app should attach deliberately:** resource.
- **This is a workflow you want people to run the same way each time:** prompt.

The failure mode is making everything a tool, because tools are the only
primitive that works without the client implementing anything. It works, and it
spends context and hands the model choices it did not need. It is the first of
the four decisions in
[how to build an MCP server](how-to-build-an-mcp-server.md), and the one that
costs most to reverse once people have registered you.

## What "tools versus skills" is asking

A related question worth separating: skills, in the clients that have them, are
instructions and context bundled for a task, while MCP tools are callable
functions on a server. They are not competitors - a skill can tell a model how
to use a tool well. If the thing you want is "make the model good at this
workflow", that is closer to a prompt or a skill; if it is "let the model do
this thing at all", that is a tool.

## Short answers to the questions that lead here

**What is the difference between MCP tools and resources?** Control. The model
calls tools; the application retrieves resources and decides what to show the
model.

**How do I list the tools an MCP server exposes?** `tools/list` is a protocol
method, so any client can enumerate them. Reading that list before registering
a server is the cheapest safety check there is.

**Are prompts required?** No. A server can expose only tools, and most do. A
server with good prompts is telling you how it expects to be used.

**Can a resource change while the client is connected?** Yes, and clients can
subscribe to be notified of updates on watched resources.

**Should everything be a tool?** No, and it is the common mistake. Tools cost
context on every turn and hand the model choices it may not need.

**See also:** [how the tools are shaped, and why](mcp-tool-design.md) for this
project's own design reasoning, and
[the MCP server](mcp-server.md) for the tools it actually exposes.

## Sources

- [Understanding MCP servers](https://modelcontextprotocol.io/docs/learn/server-concepts), the protocol's own documentation, retrieved 2026-09-11: the three primitives, the control column, the protocol methods (`tools/list`, `tools/call`, `resources/list`, `resources/read`, `prompts/list`, `prompts/get`), resource templates and subscriptions, and the human-oversight mechanisms around tools.

---

*Written while maintaining an MCP server, which exposes tools and no prompts -
so the paragraph arguing that a good server ships prompts is a criticism of
ours as much as anyone's.*
