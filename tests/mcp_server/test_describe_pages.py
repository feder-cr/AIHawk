"""`describe_pages` has to return what the layer above it promises: url, title
and which page a command drives, for every live page, with a page that will not
answer contributing what it can."""
from __future__ import annotations

from invisible_playwright_mcp.mcp.session import StealthSession


class _Page:
    def __init__(self, url="https://example.com/", title="Example", *, boom=None):
        self.url = url
        self._title = title
        self._boom = boom
        self.closed = False

    def is_closed(self):
        return self.closed

    async def title(self):
        if self._boom:
            raise self._boom
        return self._title

    async def close(self):
        self.closed = True


class _Context:
    def __init__(self):
        self.pages = []


def _session_with(*pages):
    s = StealthSession()
    s._context = _Context()
    s._context.pages.extend(pages)
    return s


async def test_every_page_comes_back_with_all_three_fields():
    s = _session_with(_Page("https://a.test/", "A"), _Page("https://b.test/", "B"))
    rows = await s.describe_pages()

    assert rows == [{"active": False, "url": "https://a.test/", "title": "A"},
                    {"active": True, "url": "https://b.test/", "title": "B"}]


async def test_exactly_one_page_is_flagged_active_and_it_is_the_newest_live_one():
    """The page a command drives, which moves when the newest one goes."""
    first, second = _Page("https://a.test/"), _Page("https://b.test/")
    s = _session_with(first, second)

    assert [r["active"] for r in await s.describe_pages()] == [False, True]
    await second.close()
    assert [r["active"] for r in await s.describe_pages()] == [True]


async def test_a_page_that_will_not_answer_contributes_what_it_can():
    """A page mid-navigation must not make the others unreadable."""
    s = _session_with(_Page("https://ok.test/", "OK"),
                      _Page("https://stuck.test/", boom=RuntimeError("navigating")))
    rows = await s.describe_pages()

    assert rows[0]["title"] == "OK"
    assert rows[1] == {"active": True, "url": "https://stuck.test/", "title": ""}


async def test_no_pages_is_an_empty_list_rather_than_an_error():
    s = _session_with()
    assert await s.describe_pages() == []
