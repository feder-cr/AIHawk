"""The lifespan must NOT close the sessions, and that is the whole point.

FastMCP runs the lifespan per MCP session, which is per CLIENT rather than once
per process. Measured while building this: with one client attached the machine
had 7 firefox processes, and a second after that client disconnected it had 1
again, because the lifespan was closing the registry. A browser that dies when
somebody detaches cannot be shared, cannot outlive a chat, and cannot back a
live view.

So these tests assert the absence of a behaviour. They fail against any version
that cleans up here, including the one this replaced.
"""
import pytest

#: The browser this file addresses. Explicit since the registry's key
#: stopped having a default: a bare "default" was never a key any browser
#: occupied, because the server composes `<piece of work>/<browser>`.
KEY = "default/main"


class _FakeSession:
    def __init__(self, **kwargs):
        self.closed = False
        self._browser = None
        self._context = object()

    async def start(self):
        pass

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_a_client_leaving_does_not_close_its_browser():
    from aihawk.mcp import server

    fake = _FakeSession()
    server.registry._browsers[KEY] = fake

    async with server._lifespan(server.mcp) as ctx:
        assert ctx == {}

    assert fake.closed is False, "the lifespan closed a session; a second client would find no browser"
    assert server.registry.peek(KEY) is fake

    await server.registry.close_all()


@pytest.mark.asyncio
async def test_several_clients_coming_and_going_leave_every_session_alone():
    from aihawk.mcp import server

    a, b = _FakeSession(), _FakeSession()
    server.registry._browsers["chat"] = a
    server.registry._browsers["someone-else"] = b

    for _ in range(3):
        async with server._lifespan(server.mcp):
            pass

    assert a.closed is False and b.closed is False
    assert server.registry.ids() == ["chat", "someone-else"]

    await server.registry.close_all()


@pytest.mark.asyncio
async def test_close_all_is_what_actually_shuts_them_down():
    """The cleanup did not disappear, it moved. It runs when the PROCESS ends,
    which on stdio is the same moment a client leaves, so nothing changes for
    the clients that exist today."""
    from aihawk.mcp import server

    fake = _FakeSession()
    server.registry._browsers[KEY] = fake

    await server.registry.close_all()

    assert fake.closed is True
    assert server.registry.ids() == []


def test_the_exit_hook_is_registered():
    """Without this the browsers would simply leak: Firefox launches a tree of
    processes, and an orphan goes on holding its profile directory and port.

    ⛔ THIS TEST DID NOT TEST ITS OWN NAME. It asserted only that
    `_close_sessions_at_exit` EXISTS and is callable, which stays true if the
    `atexit.register` line is deleted - the leak it is named for would ship
    green. Above it sat a dead `registered = ...` line, a first attempt at
    reading `atexit._exithandlers` that CPython does not expose, left in place
    with a comment explaining the retreat.

    ⛔ AND THE OBVIOUS REPLACEMENT IS INERT ON THIS INTERPRETER, which is worth
    writing down because it looks like it works. `atexit.unregister(f)` then
    comparing `atexit._ncallbacks()` reads like a behavioural proof; measured
    on CPython 3.12.0, the count does NOT go down after `unregister` - not for
    this function and not for a freshly registered local one either. A test
    built on it fails against correct code, which is the worst kind of gate:
    it accuses the product of the defect it was written to find.

    So this reads the SOURCE, which is what this suite already does elsewhere
    for properties no behaviour test can reach (`test_addressing.py` scans the
    same module for unaddressed registry calls). Over the AST rather than for
    a substring, because this project has a recorded case of a gate satisfied
    by the COMMENT next to the call it was checking for.

    Known-bad: comment out `atexit.register(_close_sessions_at_exit)` in
    `mcp/server.py`. The old assertion stayed green; this one goes red.
    """
    import ast
    import inspect

    from aihawk.mcp import server

    assert callable(server._close_sessions_at_exit)

    tree = ast.parse(inspect.getsource(server))
    registered = [
        node for node in tree.body
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "register"
        and isinstance(node.value.func.value, ast.Name)
        and node.value.func.value.id == "atexit"
        and any(isinstance(a, ast.Name) and a.id == "_close_sessions_at_exit"
                for a in node.value.args)
    ]
    assert registered, (
        "nothing registers the browser-closing hook at import, so an ending "
        "process leaves Firefox holding its profile directory and its port")
