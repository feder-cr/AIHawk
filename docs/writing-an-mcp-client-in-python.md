---
title: "Writing an MCP client in Python: the thirty-line version"
description: "A client is a process that speaks JSON-RPC to a server. Here is one that connects, lists the tools and calls one, with its real output and one surprise."
parent: "Using the Agent"
nav_order: 44
---

# Writing an MCP client in Python

Most people meet MCP as a user of a client: Claude Code, an editor, a chat app.
The word makes the thing sound bigger than it is. **A client is a process that
speaks JSON-RPC to a server and decides what to do with the answers.** There is
no model in that sentence, and there does not have to be one in your client
either.

That is the useful realisation, because a client with no model is the fastest
way to find out whether a server works.

## The whole thing

```python
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "aihawk"],
        env={**os.environ, "PYTHONPATH": "src"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("server:", init.serverInfo.name, init.serverInfo.version)

            tools = (await session.list_tools()).tools
            print("tools:", len(tools))
            for t in tools[:3]:
                print("   ", t.name)

            out = await session.call_tool("browser_list", {})
            print("browser_list ->", out.content[0].text[:200])


asyncio.run(main())
```

Run against this project's server on 2026-09-13, that prints:

```text
server: stealth 1.28.0
tools: 16
    browser_open
    browser_close
    browser_list
browser_list -> {"focus": "main", "limit": 2, "browsers": [{"id": "main",
"running": false, "focused": true, "url": "", "urls": []}], "note": "1 of 2
browsers. Commands that name none go to main."}
```

Four things are worth naming in those thirty lines.

**`stdio_client` launches the server.** You are not connecting to something
already running; you are giving the SDK a command line and it spawns the
process, hands you its pipes, and kills it when the block exits. That is what
makes a stdio server easy to develop against and is the same mechanism every
desktop client uses when you paste a config block.

**`initialize` is a handshake, not a formality.** Nothing else is legal before
it. Its answer is where you learn the protocol version and what the server
declares it can do.

**`list_tools` is the same call the model's host makes.** What comes back is
exactly what would be spent on context every turn, so a client is also how you
measure a server's cost honestly.
[How many MCP tools is too many](how-many-mcp-tools-is-too-many.md) does that
arithmetic on this one.

**`call_tool` takes the name and a dict, and gives you content back.** For a
browser server that content might be text, a snapshot, or an image. Read the
text rather than the shape of the object: the answer above is JSON in a string,
which is a choice this server makes and not a rule.

## The surprise in the output

`init.serverInfo.version` reported **1.28.0**. That is the version of the
installed `mcp` SDK, not of the server package, which is on a completely
different number. It is not a bug, but it is a trap: **do not use `serverInfo`
to decide which version of a server you are talking to** unless that server
explicitly sets it. If you need to branch on a server's version, ask the server,
through a tool that answers it.

This is the kind of thing a thirty-line client finds in thirty seconds and a
week of reading documentation does not.

## What to use it for

**Deciding whether the problem is the server or the client.** When tools are not
showing up in your editor, this script answers the only question that matters:
does the server work at all? If it lists tools here and not there, the
registration is wrong, not the server.
[A browser MCP server in GitHub Copilot](playwright-mcp-in-github-copilot.md)
covers the registration side.

**Testing your own server without a model.** A model is a bad test harness: it
works around a broken tool rather than reporting it, so a misleading reply
becomes a wrong action instead of a red test.
[How to build an MCP server](how-to-build-an-mcp-server.md) has more on that
failure mode.

**Scripting a server you did not write.** Nothing says a client has to be
interactive. If a server exposes a tool you want in a nightly job, this is the
whole integration.

## When you do want a model in it

Adding one is not a different program. You call `list_tools`, convert each tool
to whatever shape your model provider expects, pass the model's chosen call
through `call_tool`, and feed the result back as a message. That loop is the
entire "agent" part, and writing it once is the clearest way to see that MCP is
a discovery and transport convention rather than an intelligence layer.

Whether you want that loop at all is a real question with a real answer:
[MCP alternatives](model-context-protocol-alternatives.md) is about when the
protocol is the wrong shape for what you are doing.

## Short answers to the questions that lead here

**What is an MCP client?** The side that connects to a server, lists what it
offers and calls it. Your editor is one. A thirty-line script is one too.

**Do I need an LLM to write a client?** No, and leaving it out is the point for
testing.

**What is the difference between an MCP client and an MCP server?** The client
starts the connection and calls tools; the server offers them. Over stdio the
client also launches the server process.

**How do I connect to a remote MCP server instead?** Swap `stdio_client` for the
streamable HTTP client and give it a URL. Everything after the handshake is
identical, by specification. [Local or remote](local-vs-remote-mcp-server.md)
explains what else changes.

**Why do the tools not show up?** Run the script above. If they appear here,
your client's config is the problem, not the server.

**See also:** [How to build an MCP server](how-to-build-an-mcp-server.md),
[tools, resources and prompts](mcp-tools-resources-and-prompts.md), and
[the MCP server](mcp-server.md) for the server this was run against.

## Sources

- [The MCP transports overview](https://modelcontextprotocol.io/docs/concepts/transports), retrieved 2026-09-13, for stdio framing and the identical-semantics guarantee across bindings.
- The `mcp` Python SDK, version 1.28.0 as installed here on 2026-09-13, for `ClientSession`, `stdio_client` and `StdioServerParameters`.
- The script above was executed against this project's server on 2026-09-13; the output block is its real output, wrapped to fit.

---

*Written while maintaining a server, which is why the client is pointed at ours.
It is thirty lines against any server, and the paragraph that cost us something
is the one about `serverInfo`.*
