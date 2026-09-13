---
title: "Local or remote MCP server: what changes, and what does not"
description: "stdio and Streamable HTTP carry identical semantics, so the choice is about lifetime and reach. The one thing that silently changes, measured on ours."
parent: "Using the Agent"
nav_order: 43
---

# Local or remote MCP server

The specification is unusually direct about this: protocol semantics are
identical on every transport. A transport is a **binding** that defines how
messages are framed and delivered, not what they mean. Two are standard today:
**stdio**, newline-delimited JSON-RPC over the standard streams of a subprocess
the client launches, and **Streamable HTTP**, where each message is an HTTP POST
to one endpoint and replies come back as JSON or as a request-scoped SSE stream.

So the decision is not about capability. Every tool works the same either way.
It is about three other things, and one of them will bite you.

## What actually differs

**Who owns the process.** On stdio the client launches your server and the
server dies with it. Nothing to deploy, nothing to authenticate, nothing left
running. On HTTP the server outlives every client and somebody has to be
responsible for it.

**Who can reach it.** A stdio server serves exactly the one client that spawned
it. An HTTP server can serve several, including several at once, which is the
real reason to want it.

**Where the work happens, which does not move.** This is the part people get
wrong. A remote MCP server does not put your work somewhere else; it puts the
**server** somewhere else. If the server drives a browser, the browser runs
wherever the server runs, on the server's network, with the server's files. For
a browser server that is usually the argument against remote rather than for it:
the profile you are logged into and the proxy you route through are on your
machine, and moving the server away from them is moving the work away from its
inputs. [Playwright MCP with a proxy](playwright-mcp-with-a-proxy.md) is the
same point from the network side.

## The thing that silently changes: what "a session" means

Here is ours, because it is the failure we actually hit rather than one we
imagine somebody might.

Our server closes its browsers when the SDK's lifespan context exits. Over
stdio the SDK enters that lifespan **once per process**, so its exit is the last
moment the event loop that opened the browsers is still alive, which is exactly
the right time to close them. Over Streamable HTTP the SDK enters it **once per
client**. The same line of code, unchanged, therefore means "close everything
when the process ends" on one transport and "close everything when anybody
disconnects" on the other.

Measured on this server: with a client attached the machine held **7 firefox
processes**, and one second after that client detached it held **1**. The
browsers a second client was still using would have gone with them.

Nothing in the protocol is wrong here, and nothing in the SDK is wrong either.
Per-client is the correct scope for an HTTP session. The bug is entirely in the
assumption that a lifecycle hook means the same thing on both bindings because
the tools do. **When you move a server to HTTP, audit every piece of state whose
lifetime you tied to a connection**, and expect the audit to find something.

The other half is less dramatic and worth knowing: over stdio the shutdown path
is the client closing stdin, and that path can hang. Measured on Linux,
2026-09-06: a client that closed stdin with a page still open waited **180
seconds** for the process and gave up; with no page open the same shutdown took
**0.2 seconds**.

## Choosing, in one pass

- **One user, one client, work that lives on your machine:** stdio. This is most
  servers, and it is the default for a reason.
- **Several clients that must share one live thing:** HTTP. That is the case
  stdio cannot express at all.
- **A team, or a server you want to deploy once:** HTTP, and now you own
  authentication, lifetime and the state audit above.
- **A browser server:** stdio unless you can say why the browser should not be
  where your profile is. Ours takes `STEALTHFOX_MCP_TRANSPORT=http` if you can,
  and defaults to stdio because usually you cannot.

If the thing pushing you toward remote is "I want it always available", check
that the always-available part is the server rather than the data. Often it is
the data, and then the answer is a resource or a plain API rather than a
relocated process.
[MCP alternatives](model-context-protocol-alternatives.md) has that argument in
full.

## Short answers to the questions that lead here

**What is the difference between a local and a remote MCP server?** Where the
process runs and who owns its lifetime. The tools and their behaviour are
identical, by specification.

**Is SSE still a transport?** Not as a separate one in the current revision.
Streamable HTTP uses SSE for request-scoped reply streams; the standalone SSE
transport belongs to an earlier revision, and interoperating with those is
described in the spec's backward-compatibility rules.

**Can I run one MCP server for my whole team?** Over HTTP, yes. You then own
authentication and the question of what happens when two people drive the same
stateful thing at once, which for a browser server is a real question and not a
formality.

**Which is faster?** Neither, meaningfully. Both are local IPC or one HTTP round
trip, and in an agent session every cost is dominated by the model.

**Does remote mean my data leaves my machine?** It means the server's work
happens on the server's machine. Whether that is your data depends entirely on
what the server does.

**See also:** [How to build an MCP server](how-to-build-an-mcp-server.md),
[writing an MCP client in Python](writing-an-mcp-client-in-python.md), and
[the MCP server](mcp-server.md) for this server's settings.

## Sources

- [The MCP transports overview](https://modelcontextprotocol.io/docs/concepts/transports), retrieved 2026-09-13, for the two standard bindings, the wording on bindings versus semantics, and backward compatibility with earlier revisions.
- This project's own server: the per-client lifespan behaviour and the 7-to-1 process measurement are recorded beside the code that handles it in `src/aihawk/mcp/server.py`; the 180-second stdin measurement was taken on Linux on 2026-09-06.

---

*Written while maintaining a server that supports both and ships stdio. The
recommendation is the one that makes our own remote mode the exception, because
for a browser the inputs are where the person is.*
