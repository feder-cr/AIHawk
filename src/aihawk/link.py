"""One long-lived MCP connection, shared by the conversation and the live view.

The connection outlives any single instruction, because the browser has to still
be there when the next line is typed and the live pane has to keep watching it
in between. One way in is the whole point of the page this serves.

WHY THIS IS A CLIENT AND NOT AN IMPORT. The same shell used to run inside the MCP
server process and reach the browser through `registry`, which is a Python object
in the same interpreter. Here it is a separate program talking over MCP, and that
is the point of the split rather than an accident of it: the server exposes tools
and nothing else, and everything with a face is a client of those tools, exactly
like anybody else's agent.

⛔ THIS PARAGRAPH USED TO DESCRIBE A COST THAT NO LONGER EXISTS, and left saying
so would be exactly the kind of stale reasoning this project keeps finding one
step past where it was written. The in-process view could once ask
`registry.peek` - "is there a browser, without starting one" - and there was no
such question over MCP at all: the tab tool of the day called `ensure`
regardless, so asking would start a browser just to be told nothing was
running. `Link` used to
work around that by remembering whether it had EVER issued an instruction, and
the live view stayed quiet until it had - a coarser answer than the real
question, armed by the first call of any kind rather than by whether a browser
was actually up.

The real question exists now: `browser_watch` refuses rather than starts when
nothing is running, and `browser_list` answers what is held without waking any
of it (`registry.peek` reached from `looking`, in `mcp/server.py`), so a client
can simply ask and read the answer.
`Link` remembers nothing any more; there is nothing left it needs to.
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Mapping, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .runner import child_env


class Link:
    """A connection to one MCP server, and the browser behind it."""

    def __init__(self, opts: Mapping[str, Any] | None = None, *,
                 key: str | None = None) -> None:
        self._opts = dict(opts or {})
        # Held only to keep it OUT of the child: child_env removes every
        # variable carrying this value, and a key given on the command line
        # is in no environment for it to find by reading.
        self._key = key
        self._session: Optional[ClientSession] = None
        # Annotated, because an attribute left to be inferred from `None` makes
        # every later use of it read as an error on a type that cannot have one.
        self._ctx: Any = None
        self._sess_ctx: Optional[ClientSession] = None
        self._tools: Optional[list] = None
        #: What the server says about itself at `initialize`. It is the one
        #: place the two-browser contract is written - what `support` is for,
        #: and that whoever opens it closes it - and until 2026-09-12 nothing
        #: read it: the loop sent the system prompt and the tool descriptions
        #: and the server's own instructions went nowhere.
        self._instructions: str = ""
        # One instruction at a time. Two tool calls racing on one browser is not
        # a transport problem, it is two hands on the same mouse.
        self._lock = asyncio.Lock()

    async def open(self) -> "Link":
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "aihawk"],
            env=child_env(self._opts, os.environ, key=self._key),
        )
        self._ctx = stdio_client(params)
        read, write = await self._ctx.__aenter__()
        self._sess_ctx = ClientSession(read, write)
        self._session = await self._sess_ctx.__aenter__()
        started = await self._session.initialize()
        self._instructions = getattr(started, "instructions", None) or ""
        self._tools = (await self._session.list_tools()).tools
        return self

    async def close(self) -> None:
        for ctx in (self._sess_ctx, self._ctx):
            if ctx is not None:
                try:
                    await ctx.__aexit__(None, None, None)
                except Exception:
                    pass
        self._session = None
        self._sess_ctx = None
        self._ctx = None

    @property
    def tools(self):
        return self._tools or []

    @property
    def instructions(self) -> str:
        """The server's own instructions, verbatim, or an empty string."""
        return self._instructions

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("the link is not open; call open() first")
        return self._session

    async def call(self, name: str, arguments: dict | None = None):
        """Call one tool, serialised against every other call on this link."""
        async with self._lock:
            return await self.session.call_tool(name, arguments or {})

    async def call_text(self, name: str, arguments: dict | None = None) -> str:
        return text_of(await self.call(name, arguments))


def text_of(result) -> str:
    """The text of a tool result, or an empty string.

    Shared with the agent loop rather than written twice: a tool result is read
    in two places now, and two readers of one wire format drift.
    """
    content = getattr(result, "content", None)
    if not content:
        return ""
    first = content[0]
    return getattr(first, "text", None) or "[non-text result]"


def image_of(result) -> "tuple[bytes, str] | None":
    """The image bytes of a tool result that carries one, with its MIME type, or None.

    `browser_watch` and `browser_take_screenshot` answer with image content
    rather than text, and over MCP that arrives base64-encoded with the type
    beside it: JPEG for the window capture, PNG for a screenshot. This is the
    only place that knows it, so the live view never learns the wire format.
    """
    import base64

    for item in getattr(result, "content", None) or []:
        data = getattr(item, "data", None)
        if data is None:
            continue
        mime = getattr(item, "mimeType", None) or "image/png"
        if isinstance(data, bytes):
            return data, mime
        try:
            return base64.b64decode(data), mime
        except Exception:
            continue
    return None


# ⛔ `SessionLink` STOOD HERE AND IS GONE WITH THE THING IT MULTIPLEXED. It
# gave every call this conversation's id, imposed rather than trusted from a
# model, because one shared connection served every conversation and a tool
# call naming none landed on a default that two conversations could collide
# on. MCP has no session concept to impose an id ONTO any more - no tool
# takes one - so the only way left to keep two conversations apart is the one
# this always should have been: two conversations, two CONNECTIONS, each its
# own spawned server told at birth which saved file is its own
# (`AIHAWK_SESSION_ID`, in `Sessions.get`). A plain `Link` is what every
# conversation holds now; there is no second class to wrap it in.
