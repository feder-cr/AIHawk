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
of it (`Work.listing`, in `mcp/work.py`), so a client can simply ask and read
the answer. That parenthesis named `registry.peek` and a `looking` helper in
`mcp/server.py` until 2026-09-16, and neither had existed for weeks: the
paragraph opens by warning about stale reasoning and had gone stale itself.
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
from .quiet import swallow


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
        #
        # ⛔ THE CONTEXTS ARE NOT HELD HERE ANY MORE, AND THAT IS THE POINT.
        # They used to be - `self._ctx` and `self._sess_ctx` - so that `close`
        # could exit them from a different task than the one that entered them,
        # which is what an anyio cancel scope forbids. They live inside `_hold`
        # now, where the task that enters them is the task that leaves them.
        self._owner: Optional[asyncio.Task] = None
        self._stop: asyncio.Event = asyncio.Event()
        self._ready: Any = None
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

    def _params(self) -> StdioServerParameters:
        """How the child is started. Its own method so a test can point the
        connection at a command that fails, which is the one case `open` has to
        report rather than swallow."""
        return StdioServerParameters(
            command=sys.executable,
            args=["-m", "invisible_playwright_mcp"],
            env=child_env(self._opts, os.environ, key=self._key),
        )

    async def _hold(self) -> None:
        """Own the connection for the whole of its life, in ONE task.

        ⛔ THIS EXISTS BECAUSE `open` AND `close` USED TO BE TWO HALVES OF A
        CONTEXT MANAGER, TORN APART. `open` called `__aenter__` on
        `stdio_client` and on `ClientSession` by hand, and `close` called
        `__aexit__` on them - from whatever task happened to be closing. Both
        are anyio context managers, so each owns a cancel scope, and a cancel
        scope has to be exited in the task that ENTERED it. Exiting it
        elsewhere delivers the cancellation to the scope enclosing the entering
        task.

        In this application that was fatal in one reachable case. `cli.serve`
        opens the default conversation and then runs uvicorn in the same task,
        so deleting that conversation from the sessions panel closed its link
        from a request task, the cancellation landed on `server.serve()`, and
        the interface exited 1. Measured over plain HTTP: deleting any other
        conversation left it alive; deleting the default killed it.

        ⛔ AND THE OTHERS WERE NOT FINE, THEY WERE QUIET. Their scopes belong
        to request tasks that have already finished, so the same wrong exit
        raised a `RuntimeError` that `close` was swallowing under a sentence
        about teardown failures. EVERY close was wrong; one of them had
        something alive to damage. Making only the default lazy would have
        removed the visible half and kept the defect.

        So the contexts are entered and left here, by this task, and nobody
        else ever holds them. Closing from another task is not guarded
        against - it is made impossible.
        """
        try:
            async with stdio_client(self._params()) as (read, write):
                async with ClientSession(read, write) as session:
                    started = await session.initialize()
                    self._instructions = getattr(started, "instructions", None) or ""
                    self._tools = (await session.list_tools()).tools
                    self._session = session
                    self._ready.set_result(None)
                    # Held open until somebody asks for it to end. This is the
                    # whole reason the task exists: the connection outlives any
                    # single instruction.
                    await self._stop.wait()
        except BaseException as exc:
            # A failure BEFORE the connection was usable is `open`'s answer to
            # give; one after it belongs to whoever closes.
            if not self._ready.done():
                self._ready.set_exception(exc)
            raise
        finally:
            self._session = None

    async def open(self) -> "Link":
        self._stop = asyncio.Event()
        self._ready = asyncio.get_running_loop().create_future()
        self._owner = asyncio.create_task(self._hold())
        try:
            await self._ready
        except BaseException:
            # The owner is already unwinding; wait for it so a failed open
            # leaves nothing running and no exception unretrieved.
            with swallow("the open already failed; its owner's exit adds nothing"):
                await self._owner
            self._owner = None
            raise
        return self

    async def close(self) -> None:
        """Ask the owner to let go, and wait until it has.

        Idempotent because more than one path holds a link: `close_all` at
        exit and `forget` on a conversation.
        """
        owner, self._owner = self._owner, None
        if owner is None:
            return
        self._stop.set()
        with swallow("a connection torn down on purpose is not a failure to report"):
            await owner

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

    ⛔ THE ONE PLACE THAT READS A TOOL RESULT, AND THE SENTENCE ABOVE USED TO
    CLAIM THAT WHILE IT WAS FALSE. It said "shared with the agent loop rather
    than written twice", and the agent loop did not call it: `_result_text` in
    `agent.py` carried these same five lines, the `[non-text result]` literal
    included, and imported nothing from here. Two copies with a test suite
    each, so either could have drifted and stayed green on both sides. The
    docstring asserting the invariant is what made it hard to see, because a
    reader checking for duplication found a sentence saying there was none.
    """
    content = getattr(result, "content", None)
    if not content:
        return ""
    first = content[0]
    return getattr(first, "text", None) or "[non-text result]"


def answer_of(result) -> tuple[str, bool]:
    """What the tool said, and whether it was a failure.

    ⛔ MCP REPORTS A FAILED TOOL AS A RESULT, NOT AS AN EXCEPTION. A tool that
    cannot do the thing answers with `isError` set and the reason in its text;
    only a broken transport raises. Reading the text and ignoring the flag made
    every failure arrive at the page as a success: the step row kept the past
    tense that asserts the thing happened - `Navigated https://...` - with the
    error printed after it in the colour of an ordinary result. Measured on a
    live transcript: a `NS_ERROR_UNKNOWN_HOST` drawn at `data-state="ok"`, and
    zero rows in the whole session had ever reached the error state the page
    has always known how to draw.

    For an agent that acts on real websites this is the worst kind of defect in
    a log: not a gap, a lie, and it costs the reader the ability to trust any
    other row.

    ⛔ AND IT ANSWERS BOTH HALVES BECAUSE EVERY CALLER WANTS BOTH, which is
    what three readers of one wire format were each solving alone: the loop
    with a private copy of `text_of`, and `/live/frame` with `text_of(result)
    if getattr(result, "isError", False) else ""` written out in the route. The
    flag and the text are one fact about one result, so they are read once.
    """
    return text_of(result), bool(getattr(result, "isError", False))


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
# (`INVISIBLE_MCP_SESSION_ID`, in `Sessions.get`). A plain `Link` is what every
# conversation holds now; there is no second class to wrap it in.
