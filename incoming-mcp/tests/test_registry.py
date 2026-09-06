"""A start that fails must not take the rest of the conversation with it.

This is the defect that made the server unusable in practice: the session was
stored BEFORE `start()` was awaited, so a start that raised left a half-built
object behind. Every later call then found something non-None, skipped the
start, and died on `'NoneType' object has no attribute ...` - an error that
names nothing and, on a stdio server, ends the session.

These tests moved here from test_ensure_session.py when the module global became
a registry. What they protect did not change: they still fail against a registry
that stores a session before it has started, or that hands back a dead one, or
that rebuilds a healthy one.
"""
import pytest

from invisible_playwright_mcp.registry import DEFAULT_SESSION_ID, SessionRegistry


class _SessionThatFailsOnce:
    """Raises on the first start and succeeds on the second.

    A stale INVISIBLE_SEAL_FILE and a proxy that is down both look like this
    from here: the object constructs fine and the failure happens in `start()`.
    """

    instances: list = []

    def __init__(self, **kwargs):
        self._browser = None
        self._context = None
        self.started = False
        _SessionThatFailsOnce.instances.append(self)

    async def start(self):
        if len(_SessionThatFailsOnce.instances) == 1:
            raise RuntimeError("engine/seal mismatch - refusing to launch")
        self.started = True
        self._browser = None
        self._context = object()

    async def close(self):
        pass


class _ConnectedBrowser:
    """The registry asks a live browser whether it is still connected, so a
    stand-in without that method is indistinguishable from a dead one."""

    def is_connected(self):
        return True


class _Healthy:
    def __init__(self, **kwargs):
        self._browser = _ConnectedBrowser()
        self._context = object()
        self.started = False

    async def start(self):
        self.started = True

    async def close(self):
        pass


class _AlreadyPoisoned:
    """What a server that has been running since before the fix looks like."""

    def __init__(self, **kwargs):
        self._browser = None
        self._context = None

    async def start(self):
        raise AssertionError("the poisoned object must not be started again")

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_a_failed_start_is_not_kept_and_the_next_call_retries():
    _SessionThatFailsOnce.instances = []
    reg = SessionRegistry(factory=_SessionThatFailsOnce)

    with pytest.raises(RuntimeError, match="refusing to launch"):
        await reg.ensure()

    # The half-built object must not have been kept. Before the fix this was the
    # failed instance, and every later call returned it.
    assert reg.peek() is None

    session = await reg.ensure()
    assert session.started is True
    assert reg.peek() is session
    assert len(_SessionThatFailsOnce.instances) == 2


@pytest.mark.asyncio
async def test_a_session_with_no_browser_is_replaced_rather_than_returned():
    """The process that HAS the defect is the one you notice it in.

    A fix that only prevents the state does nothing for a server already in it,
    and there a later release never arrives: the operator has to restart, which
    is the thing they could not work out how to do from the error message.
    """
    reg = SessionRegistry(factory=_Healthy)
    reg._sessions[DEFAULT_SESSION_ID] = _AlreadyPoisoned()

    session = await reg.ensure()
    assert isinstance(session, _Healthy)
    assert session.started is True
    assert reg.peek() is session


@pytest.mark.asyncio
async def test_a_healthy_session_is_reused_and_not_restarted():
    """The half that must NOT fire. A guard that rebuilds every time would open
    a second browser per call and lose the cookies of the first."""
    def _explode():
        raise AssertionError("a healthy session must be reused, not rebuilt")

    reg = SessionRegistry(factory=_explode)
    live = _Healthy()
    reg._sessions[DEFAULT_SESSION_ID] = live

    assert await reg.ensure() is live
    assert live.started is False


@pytest.mark.asyncio
async def test_two_ids_get_two_browsers():
    """The reason the registry exists. One global could serve one client; this
    has to serve the built-in chat and somebody else's agent at once."""
    reg = SessionRegistry(factory=_Healthy)

    a = await reg.ensure("chat")
    b = await reg.ensure("claude-desktop")

    assert a is not b
    assert reg.ids() == ["chat", "claude-desktop"]
    assert await reg.ensure("chat") is a


@pytest.mark.asyncio
async def test_close_all_closes_every_session():
    reg = SessionRegistry(factory=_Healthy)
    a = await reg.ensure("one")
    b = await reg.ensure("two")

    closed = []
    a.close = lambda: closed.append("one") or _noop()
    b.close = lambda: closed.append("two") or _noop()

    await reg.close_all()
    assert sorted(closed) == ["one", "two"]
    assert reg.ids() == []


async def _noop():
    return None
