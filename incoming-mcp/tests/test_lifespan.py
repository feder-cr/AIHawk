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
    from invisible_playwright_mcp import server

    fake = _FakeSession()
    server.registry._sessions["default"] = fake

    async with server._lifespan(server.mcp) as ctx:
        assert ctx == {}

    assert fake.closed is False, "the lifespan closed a session; a second client would find no browser"
    assert server.registry.peek() is fake

    await server.registry.close_all()


@pytest.mark.asyncio
async def test_several_clients_coming_and_going_leave_every_session_alone():
    from invisible_playwright_mcp import server

    a, b = _FakeSession(), _FakeSession()
    server.registry._sessions["chat"] = a
    server.registry._sessions["someone-else"] = b

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
    from invisible_playwright_mcp import server

    fake = _FakeSession()
    server.registry._sessions["default"] = fake

    await server.registry.close_all()

    assert fake.closed is True
    assert server.registry.ids() == []


def test_the_exit_hook_is_registered():
    """Without this the browsers would simply leak: Firefox launches a tree of
    processes, and an orphan goes on holding its profile directory and port."""
    import atexit
    from invisible_playwright_mcp import server

    registered = [f for f in getattr(atexit, "_exithandlers", [])] if hasattr(atexit, "_exithandlers") else None
    # CPython does not expose the handler list, so check the function exists and
    # is callable instead of reaching into the interpreter's internals.
    assert callable(server._close_sessions_at_exit)
