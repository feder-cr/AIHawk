"""One long-lived MCP connection, shared by the conversation and the live view.

The connection outlives any single instruction, because the browser has to still
be there when the next line is typed and the live pane has to keep watching it
in between. There was a second, shorter-lived form of this - `runner.drive`,
one task then close, behind an `aihawk do` subcommand - and both were removed on
2026-09-03: one way in is the whole point of the page this serves.

WHY THIS IS A CLIENT AND NOT AN IMPORT. The same shell used to run inside the MCP
server process and reach the browser through `registry`, which is a Python object
in the same interpreter. Here it is a separate program talking over MCP, and that
is the point of the split rather than an accident of it: the server exposes tools
and nothing else, and everything with a face is a client of those tools, exactly
like anybody else's agent.

It costs one thing, and the cost is named here rather than discovered later. The
in-process view could ask `registry.peek` - "is there a browser, without starting
one" - and there is no such question over MCP: `session_list_pages` calls
`ensure`, so asking would start a browser just to be told nothing is running.
`Link` therefore remembers whether it has ever issued an instruction, and the
live view stays quiet until it has. The invariant the old view held by calling a
different function, this one holds by knowing what it has done.
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
        self._ctx = None
        self._sess_ctx = None
        self._tools = None
        # Set the moment an instruction is issued, and never cleared: it answers
        # "could a browser exist?", which is what the live view needs to know
        # before it is allowed to ask for a picture.
        self.touched = False
        # One instruction at a time. Two tool calls racing on one browser is not
        # a transport problem, it is two hands on the same mouse.
        self._lock = asyncio.Lock()

    async def open(self) -> "Link":
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "invisible_playwright_mcp"],
            env=child_env(self._opts, os.environ, key=self._key),
        )
        self._ctx = stdio_client(params)
        read, write = await self._ctx.__aenter__()
        self._sess_ctx = ClientSession(read, write)
        self._session = await self._sess_ctx.__aenter__()
        await self._session.initialize()
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
    def session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("the link is not open; call open() first")
        return self._session

    async def call(self, name: str, arguments: dict | None = None):
        """Call one tool, serialised against every other call on this link."""
        self.touched = True
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
