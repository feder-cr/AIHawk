"""Every call a session makes carries its own id, and nothing can change that.

⛔ THE FAILURE THIS FILE EXISTS FOR IS SILENT AND IT IS THE WORST KIND. The
interface holds several conversations now. A tool call that names no session
lands on the default one, so without this two conversations would drive the SAME
browser while each drew its own transcript: the second would find the first
one's tabs, its cookies and its identity, and report them as its own. Nothing
raises, nothing is red, and the person sees two chats that seem to be doing
their own work.

No browser and no server here. The link is replaced by one that records what it
was asked, so what a session did is observable as the arguments that went out.
"""
from __future__ import annotations

import pytest

from aihawk.link import SessionLink


class _Tool:
    def __init__(self, name, props):
        self.name = name
        self.inputSchema = {"type": "object", "properties": {p: {} for p in props}}


class _Recording:
    """A link that records every call instead of making one."""

    def __init__(self, tools):
        self.tools = tools
        self.touched = False
        self.calls = []

    async def call(self, name, arguments=None):
        self.calls.append((name, dict(arguments or {})))
        return None


#: What the server actually publishes, in the shape that matters here: some
#: tools take an address, `session_list` does not.
TOOLS = [
    _Tool("browser_navigate", ["url", "session_id", "browser_id"]),
    _Tool("browser_click", ["selector", "session_id", "browser_id"]),
    _Tool("browser_list", ["session_id"]),
    _Tool("session_list", []),
]


def _link(session_id="lavoro"):
    rec = _Recording(TOOLS)
    return rec, SessionLink(rec, session_id)


async def test_every_addressable_call_carries_this_session_and_no_other():
    """Known-bad: drop the `args["session_id"] = ...` line. Every call then goes
    to the default session, and two conversations share one browser.
    """
    rec, link = _link("lavoro")

    await link.call("browser_navigate", {"url": "http://127.0.0.1/"})
    await link.call("browser_click", {"selector": "#go"})

    assert [c[1].get("session_id") for c in rec.calls] == ["lavoro", "lavoro"]
    assert rec.calls[0][1]["url"] == "http://127.0.0.1/", "the call lost its own arguments"


async def test_a_model_cannot_send_a_command_to_another_session(caplog):
    """⛔ IMPOSED, NOT DEFAULTED, and this is the security half rather than the
    tidy half. A model that passes `session_id` itself - because it read one in
    a tool result, or guessed one - must not be obeyed: the id it names decides
    whose logins the command reaches.

    Known-bad: `args.setdefault("session_id", ...)` instead of assignment. Every
    other test in this file still passes, because nothing else ever sends one.
    """
    rec, link = _link("mio")

    await link.call("browser_navigate", {"url": "http://x/", "session_id": "tuo"})

    assert rec.calls[0][1]["session_id"] == "mio", (
        "the model chose which session's browser to drive: %r" % rec.calls[0][1])


async def test_a_tool_that_takes_no_session_is_not_given_one():
    """A tool called with an argument it does not accept is an error the person
    reads instead of the answer they asked for.

    Known-bad: address every tool unconditionally. `session_list` then goes out
    with an argument its schema does not declare.
    """
    rec, link = _link()

    await link.call("session_list", {})

    assert "session_id" not in rec.calls[0][1], rec.calls[0][1]


async def test_which_tools_take_an_address_is_read_from_the_schema():
    """Not from a list written in this package, which drifts from the server the
    first time a tool is added there.

    Known-bad: replace the schema scan with a hardcoded set of names. This test
    passes a tool the set has never heard of.
    """
    rec = _Recording(TOOLS + [_Tool("browser_teleport", ["session_id"])])
    link = SessionLink(rec, "lavoro")

    assert link.addresses("browser_teleport"), (
        "a tool the server published after this code was written is not "
        "addressed, so it acts on the default session")
    assert not link.addresses("session_list")


async def test_two_sessions_on_one_connection_do_not_mix():
    """The connection is shared on purpose - one server, one process - so the
    thing that keeps them apart is this and only this.

    Known-bad: make `session_id` a module-level or class-level value instead of
    per instance. Both sessions then send whichever was built last.
    """
    rec = _Recording(TOOLS)
    a, b = SessionLink(rec, "uno"), SessionLink(rec, "due")

    await a.call("browser_navigate", {"url": "http://a/"})
    await b.call("browser_navigate", {"url": "http://b/"})
    await a.call("browser_navigate", {"url": "http://a2/"})

    assert [c[1]["session_id"] for c in rec.calls] == ["uno", "due", "uno"]


async def test_the_session_view_answers_for_the_connection_underneath():
    """The agent loop is handed this object in place of the link, so anything it
    reads off the link has to still be there.

    Known-bad: drop the `tools` property. The agent then has no tool definitions
    to send the model, which fails far from here and looks like a model problem.
    """
    rec, link = _link()

    assert link.tools is rec.tools


async def test_whether_a_browser_could_exist_is_asked_per_session():
    """⛔ AND IT IS THE ONE THING THIS VIEW MUST NOT DELEGATE. The live pane may
    ask for a picture only once a browser could exist, because over MCP there is
    no way to ask "is one running" without starting one - `browser_watch` calls
    `ensure`. If this answered for the shared CONNECTION, every new conversation
    would inherit the answer from an old one, and opening a second chat would
    launch an engine, 800 MB and seven seconds, to draw a pane for a session
    that has done nothing.

    Known-bad: `return self._link.touched`. `nuova` below then reports true
    without having made a single call.
    """
    rec = _Recording(TOOLS)
    vecchia, nuova = SessionLink(rec, "vecchia"), SessionLink(rec, "nuova")

    await vecchia.call("browser_navigate", {"url": "http://x/"})

    assert vecchia.touched is True
    assert nuova.touched is False, (
        "a conversation that has done nothing says a browser could exist, so "
        "its live pane will ask for one and the server will start it")
