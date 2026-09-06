"""`session_list_pages` has to return what its description promises.

Until 0.9.0 the tool described itself as "Every open tab: id, title, url, and
which one is active" and returned `["tab-1"]`. Ids, and nothing else.

That is worse than an ordinary docstring drifting, and the reason is what this
file exists to hold. A tool's description is not documentation for a person who
can go and read the code when it looks wrong - it is the API documentation handed
to a MODEL, which cannot. An agent wanting the current address called this,
received a list of ids, and had no way to tell it had been told something untrue.
It could only guess or waste turns.

Fixed toward the description rather than away from it: choosing a tab by an id
that says nothing about the tab is choosing blind, so the promise was the
sensible half and the data moved to meet it.
"""
from __future__ import annotations

import json

import pytest

from invisible_playwright_mcp import actions
from invisible_playwright_mcp.session import StealthSession

pytestmark = pytest.mark.asyncio

FIELDS = {"id", "title", "url", "active"}


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

    async def new_page(self):
        p = _Page()
        self.pages.append(p)
        return p


async def _session_with(*pages):
    s = StealthSession()
    s._context = _Context()
    for p in pages:
        s._context.pages.append(p)
    s.list_pages()          # adopt them the way a real call would
    return s


async def test_every_tab_comes_back_with_all_four_fields():
    """The whole promise, asserted as the whole promise.

    Known-bad, and it is what shipped: `json.dumps(session.list_pages())`, which
    satisfies "returns something about the tabs" and satisfies nothing else.
    """
    s = await _session_with(_Page("https://a.example/one", "First"),
                            _Page("https://b.example/two", "Second"))
    rows = await s.describe_pages()

    assert len(rows) == 2
    for row in rows:
        assert set(row) == FIELDS, f"a tab is missing part of the promise: {row}"
    assert [r["url"] for r in rows] == ["https://a.example/one", "https://b.example/two"]
    assert [r["title"] for r in rows] == ["First", "Second"]


async def test_exactly_one_tab_is_flagged_active_and_it_is_the_current_one():
    """The `active` flag is the half a caller cannot work around. Without it,
    `session_select_page` is the only way to know where you are, and using it to
    find out changes the answer."""
    s = await _session_with(_Page("https://a.example/", "A"),
                            _Page("https://b.example/", "B"))
    ids = s.list_pages()
    s.select_page(ids[0])

    rows = await s.describe_pages()
    assert [r["active"] for r in rows] == [True, False]

    s.select_page(ids[1])
    rows = await s.describe_pages()
    assert [r["active"] for r in rows] == [False, True]
    assert sum(r["active"] for r in rows) == 1


async def test_a_tab_that_will_not_answer_contributes_what_it_can():
    """A page mid-navigation raises on `title()`. It must not take the list down.

    Known-bad: letting the exception escape, after which one busy tab makes every
    other tab unreadable - and the busy one is exactly the tab an agent is most
    likely to be asking about.
    """
    s = await _session_with(_Page("https://ok.example/", "Fine"),
                            _Page("https://busy.example/", boom=RuntimeError("navigating")))
    rows = await s.describe_pages()

    assert len(rows) == 2
    assert rows[0]["title"] == "Fine"
    assert rows[1]["title"] == "", "a title that cannot be read is empty, not missing"
    assert rows[1]["url"] == "https://busy.example/", "the url costs nothing and survives"
    assert set(rows[1]) == FIELDS


async def test_the_tool_layer_serialises_all_four_fields():
    """The gap the defect actually lived in: the session could have known and the
    tool still returned less. This asserts the JSON a model receives."""
    s = await _session_with(_Page("https://a.example/", "A"))
    payload = json.loads(await actions.list_pages(s))

    assert isinstance(payload, list) and payload
    assert set(payload[0]) == FIELDS
    assert payload[0]["url"] == "https://a.example/"


async def test_no_tabs_is_an_empty_list_rather_than_an_error():
    s = StealthSession()
    s._context = _Context()
    assert await s.describe_pages() == []
    assert json.loads(await actions.list_pages(s)) == []
