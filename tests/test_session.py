import pytest
from invisible_playwright_mcp.session import StealthSession


class _FakePage:
    # `is_closed()` is a METHOD on a real Page, and `session.page()` calls it
    # to avoid handing back a tab the site closed under us. A fake carrying
    # only a `closed` attribute passed while the code could not have worked.
    def __init__(self): self.closed = False
    def is_closed(self): return self.closed
    async def close(self): self.closed = True


class _FakeContext:
    def __init__(self): self.pages = []
    async def new_page(self):
        p = _FakePage(); self.pages.append(p); return p


class _FakeBrowser:
    """Stands in for the ephemeral-mode return of __aenter__: a Browser."""
    def __init__(self):
        self.context_returned = _FakeContext()

    async def new_context(self):
        return self.context_returned


class _FakePersistentContext:
    """Stands in for the persistent-context-mode return of __aenter__: a
    BrowserContext, which has no new_context() method."""
    def __init__(self):
        self.pages = []


@pytest.mark.asyncio
async def test_multi_tab_bookkeeping():
    s = StealthSession()
    s._context = _FakeContext()  # inject, bypass real browser start
    a = await s.new_page()
    b = await s.new_page()
    assert a == "tab-1" and b == "tab-2"
    assert s.list_pages() == ["tab-1", "tab-2"]
    # active is the last opened
    assert s.page() is s.page("tab-2")
    s.select_page("tab-1")
    assert s.page() is s.page("tab-1")
    await s.close_page("tab-1")
    assert s.list_pages() == ["tab-2"]
    with pytest.raises(RuntimeError):
        s.page("tab-1")


@pytest.mark.asyncio
async def test_page_without_any_open_raises():
    s = StealthSession()
    s._context = _FakeContext()
    with pytest.raises(RuntimeError):
        s.page()


@pytest.mark.asyncio
async def test_attach_ephemeral_browser_calls_new_context():
    s = StealthSession()
    fake_browser = _FakeBrowser()
    await s._attach(fake_browser)
    assert s._browser is fake_browser
    assert s._context is fake_browser.context_returned


@pytest.mark.asyncio
async def test_attach_persistent_context_used_directly():
    s = StealthSession()
    fake_persistent = _FakePersistentContext()
    assert not hasattr(fake_persistent, "new_context")
    await s._attach(fake_persistent)
    assert s._context is fake_persistent
    assert s._browser is None
