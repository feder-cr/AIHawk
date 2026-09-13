---
title: "How to build an MCP server: the decisions, not the scaffold"
description: "The scaffold takes ten minutes and every tutorial has it. These are the four decisions that decide whether the thing is any good, with our own numbers."
parent: "Using the Agent"
nav_order: 42
---

# How to build an MCP server

The scaffold is not the hard part. The official quickstart will have a server
answering `tools/list` inside ten minutes, and there is no point repeating it
here: start from
[the protocol's own build guide](https://modelcontextprotocol.io/docs/develop/build-server),
which is current and maintained.

This page is about what the quickstart cannot tell you, because it only shows
up after your server has been registered by somebody for a month. Four
decisions, each one expensive to reverse.

## 1. The surface you will regret is the one you added early

Every tool you expose is sent to the model **on every turn**, for the life of
every session. Not once at registration: every turn. That makes the tool list a
recurring bill rather than a feature list, and it is the only part of a server's
design that gets more expensive the more successful the server is.

Here is ours, and the point is the method rather than the figure. Enumerate
what the protocol actually hands over, which is a name, a description and a JSON
schema per tool, and count it with a tokenizer:

```python
"""Measure your own server's tool surface, the way the model receives it."""
import json

import tiktoken
from aihawk.mcp.server import mcp  # your own FastMCP instance

enc = tiktoken.get_encoding("o200k_base")
total = 0
for tool in mcp._tool_manager.list_tools():
    wire = (tool.name + "\n" + (tool.description or "") + "\n"
            + json.dumps(tool.parameters, separators=(",", ":")))
    total += len(enc.encode(wire))
print(total, "tokens on every turn")
```

Run against this project's server on 2026-09-13 that prints **3192**, for 16
tools and 9,145 characters of description. The schemas are a third of it, which
is the part that surprises people who measured their docstrings and thought they
were done.

**What that buys you as a builder is a stopping rule.** We shipped 24 tools and
now ship 16: nine were removed and one added, in one release. The nine were a
session layer, tools to start, list, inspect and forget a session, plus tools to
open, select and close extra pages inside one browser, and a tool to choose
which browser an unaddressed command meant. Every one of them existed for a real
request. Together they were a vocabulary the model had to hold and choose
within, on every turn, to express things that turned out to have simpler shapes.
[How many MCP tools is too many](how-many-mcp-tools-is-too-many.md) has the
arithmetic; [how the tools are shaped](mcp-tool-design.md) has the case for each
of ours.

The rule we would give our past self: **a tool earns its place by being the only
way to say something, not by being a convenient way to say it.**

## 2. Tools, or resources, or prompts

The protocol has three server primitives and they differ by who initiates them.
A tool is called by the model. A resource is read by the application. A prompt
is chosen by the user. Builders reach for a tool by reflex, because a tool is
what the tutorials demonstrate, and then wonder why the model keeps calling
something that should have been a lookup.

If the thing is static reference material the host could attach without asking a
model to decide, it is a resource, and it costs nothing per turn.
[Tools, resources and prompts](mcp-tools-resources-and-prompts.md) works through
the three.

## 3. Transport, which is a smaller decision than it looks

The current specification defines exactly two standard bindings: **stdio**,
newline-delimited JSON-RPC over the standard streams of a subprocess the client
launches, and **Streamable HTTP**. Protocol semantics are identical on both, in
the specification's own words: a transport defines how messages are framed and
delivered, not what they mean.

Default to stdio. It is what every client expects, it needs no authentication
story, and it makes the process lifetime somebody else's problem. Add HTTP when
you have a reason you can name, and read
[local or remote](local-vs-remote-mcp-server.md) first, because the reason most
people give does not survive contact with what actually moves.

## 4. How you will know it works

The thing that makes MCP servers rot quietly is that the client is a model, and
a model works around a broken tool instead of reporting it. A tool that returns
a misleading string does not fail; it sends the model somewhere else.

Two habits that catch this, both cheap:

**Write a client.** Thirty lines gets you a script that connects, lists the
tools and calls one, with no model involved and no guessing about whether the
registration is the problem.
[Writing an MCP client in Python](writing-an-mcp-client-in-python.md) has the
one we actually ran.

**Assert on the whole answer, not a substring of it.** Our own `session_forget`
deleted a session correctly and then replied that no such session existed. The
test asserted that the session's name appeared in the reply, and the name
appears in both things that tool can say, so the test passed for a full release.
A model reading that reply concludes it got the name wrong and goes looking for
another one.

## Short answers to the questions that lead here

**What do I need to build an MCP server?** An SDK in your language and a
transport decision. The Python SDK's `FastMCP` turns a decorated function into a
tool, and the docstring becomes what the model reads.

**How many tools should it have?** As few as can say everything. The count is
paid on every turn forever, and the model's choice gets worse before your token
bill does.

**Do I need to host it anywhere?** Not for stdio, which is the default and
covers most cases. The client launches your process.

**How do I test it?** With a client of your own before a model ever sees it, and
with assertions that distinguish every reply a tool can give.

**Can I write one in a language other than Python?** Yes. The protocol is
JSON-RPC and there are SDKs for several languages; nothing in the decisions above
is Python-specific.

**See also:** [How the tools are shaped](mcp-tool-design.md),
[local or remote](local-vs-remote-mcp-server.md), and
[the MCP server](mcp-server.md) for a shipped example with its settings.

## Sources

- [The MCP transports overview](https://modelcontextprotocol.io/docs/concepts/transports), retrieved 2026-09-13, for the two standard bindings and the statement that protocol semantics are identical on every transport.
- [Build an MCP server](https://modelcontextprotocol.io/docs/develop/build-server), retrieved 2026-09-13, for the quickstart this page deliberately does not repeat.
- This project's own server, enumerated through its tool registry on 2026-09-13 (16 tools, 3,192 tokens) and its git history for the 24-to-16 change.

---

*Written while maintaining a server that got a third smaller on purpose. The
first decision is the one we got wrong for several releases, which is why it is
first rather than last.*
