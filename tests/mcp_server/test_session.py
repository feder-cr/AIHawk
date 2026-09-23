"""A session is one browser and the page it drives: the newest live page of
its context, with no bookkeeping of its own."""
import pytest

from invisible_playwright_mcp.mcp.session import StealthSession


class _FakePage:
    # `is_closed()` is a METHOD on a real Page, and `session.page()` calls it
    # to avoid handing back a page the site closed under us. A fake carrying
    # only a `closed` attribute passed while the code could not have worked.
    def __init__(self, url="about:blank"):
        self.closed = False
        self.url = url

    def is_closed(self):
        return self.closed

    async def close(self):
        self.closed = True


class _FakeContext:
    def __init__(self):
        self.pages = []
        self.closed = False

    async def new_page(self):
        p = _FakePage(); self.pages.append(p); return p

    async def close(self):
        self.closed = True


class _FakeBrowser:
    """Stands in for the ephemeral-mode return of __aenter__: a Browser."""
    def __init__(self, connected=True):
        self.context_returned = _FakeContext()
        self._connected = connected

    def is_connected(self):
        return self._connected

    async def new_context(self):
        return self.context_returned


class _FakePersistentContext:
    """Stands in for the persistent-context-mode return of __aenter__: a
    BrowserContext, which has no new_context() method."""
    def __init__(self):
        self.pages = []


async def test_the_page_a_command_drives_is_the_newest_live_one():
    """Newest, because a site that opens a page of its own has moved the
    person's attention there; live, because a page the site closed must not
    come back as a handle that raises on the next tool."""
    s = StealthSession()
    s._context = _FakeContext()  # inject, bypass real browser start
    a = await s.new_page()
    b = await s.new_page()

    assert s.pages() == [a, b]
    assert s.page() is b
    await b.close()
    assert s.pages() == [a]
    assert s.page() is a


async def test_page_without_any_open_raises():
    s = StealthSession()
    s._context = _FakeContext()
    with pytest.raises(RuntimeError, match="no page open"):
        s.page()
    assert s.pages() == []


async def test_a_page_the_site_opened_is_seen_without_being_registered():
    s = StealthSession()
    s._context = _FakeContext()
    await s.new_page()
    popup = _FakePage("https://popup.test/")
    s._context.pages.append(popup)          # `window.open`, not `new_page`

    assert s.page() is popup
    # Both pages are seen, in the order they were opened, and the newest is
    # the one a command drives. Read through `describe_pages`, which is the
    # one thing that answers "where are the pages" since `where_pages_are`
    # went in 0.56.0 with its last caller.
    assert [r["url"] for r in await s.describe_pages()] == [
        "about:blank", "https://popup.test/"]


async def test_attach_ephemeral_browser_calls_new_context():
    s = StealthSession()
    fake_browser = _FakeBrowser()
    await s._attach(fake_browser)
    assert s._browser is fake_browser
    assert s._context is fake_browser.context_returned


async def test_attach_persistent_context_used_directly():
    s = StealthSession()
    fake_persistent = _FakePersistentContext()
    assert not hasattr(fake_persistent, "new_context")
    await s._attach(fake_persistent)
    assert s._context is fake_persistent
    assert s._browser is None


async def test_usable_means_started_and_not_closed_here():
    """The two failures a LOCAL question can see: a session that never
    finished starting has no context, and one closed here has none either.

    ⛔ WHAT IT CANNOT SEE IS THE ONE PEOPLE EXPECT, and the engine test
    beside this file measured it: a browser whose process was killed goes on
    answering `is_connected()` true for seconds. Only a round trip notices,
    which is why `Work` translates a closed target as well.

    Known-bad: answer `True` whenever `_context` is set.
    """
    s = StealthSession()
    assert s.is_usable() is False, "a session that never started is usable"

    await s._attach(_FakeBrowser(connected=True))
    assert s.is_usable() is True

    s._browser._connected = False
    assert s.is_usable() is False, (
        "a browser that says it is disconnected is still handed out")

    persistent = StealthSession()
    await persistent._attach(_FakePersistentContext())
    assert persistent.is_usable() is True, "a persistent context has no browser to ask"

    await s.close()
    assert s.is_usable() is False
