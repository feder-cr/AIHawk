import json


def test_small_object_returns_normal_json():
    from invisible_playwright_mcp.server import _json_capped
    s = _json_capped({"a": 1})
    assert json.loads(s) == {"a": 1}


def test_large_object_returns_valid_truncated_json():
    from invisible_playwright_mcp.server import _json_capped
    big = {"data": "x" * 20000}
    s = _json_capped(big, limit=6000)
    parsed = json.loads(s)  # must not raise: slicing raw JSON breaks this
    assert parsed["truncated"] is True
    assert parsed["chars"] > 6000
    assert isinstance(parsed["preview"], str)
    assert len(parsed["preview"]) <= 6000


# ⛔ read_text was the one capped action whose cut was SILENT. json_capped above
# returns {"truncated": true, "chars": N} and capped_elements reports how many
# elements it dropped; read_text simply sliced. A caller then read prose ending
# mid-sentence with nothing to tell it apart from a page that really ends there,
# and answering from the fragment looks exactly like answering from the page.


class _Page:
    def __init__(self, text):
        self._text = text

    async def evaluate(self, _js, _selector):
        return self._text


class _Session:
    def __init__(self, text):
        self._page = _Page(text)

    def page(self, page_id=None):
        return self._page


async def test_short_text_comes_back_whole_and_unmarked():
    """The case that must NOT fire: text under the cap carries no marker, so the
    marker's absence is itself information."""
    from invisible_playwright_mcp import actions
    out = await actions.read_text(_Session("hello"), "body", 6000)
    assert out == "hello"


async def test_text_over_the_cap_says_it_was_cut():
    from invisible_playwright_mcp import actions
    out = await actions.read_text(_Session("x" * 20000), "body", 6000)

    assert "cut after" in out, "the text was truncated silently"
    assert "6000" in out and "20000" in out, (
        "the marker does not say how much was kept or how much there was: %r"
        % out[-120:])
    assert out.startswith("x" * 100)


async def test_a_missing_element_is_not_reported_as_truncation():
    from invisible_playwright_mcp import actions
    out = await actions.read_text(_Session(None), "#nope", 6000)
    assert "no element matches" in out and "cut after" not in out


def test_the_two_readers_do_not_pretend_to_share_a_cap():
    """⛔ They behave differently and both now say so.

    `read_text` cuts at 6000 and marks the cut; `read_html` is UNCAPPED, and on
    a large page returns tens of thousands of characters - measured 206,929 on a
    4,000-paragraph document, 34x the other tool's cap. Declaring one cap while
    saying nothing about the other invites the reader to assume symmetry, which
    is a worse state than saying neither.
    """
    import asyncio

    from invisible_playwright_mcp import server

    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    text = (tools["browser_read_text"].description or "").lower()
    html = (tools["browser_read_html"].description or "").lower()

    assert "6000" in text and "cut" in text, "read_text does not declare its cap"
    assert "not capped" in html, "read_html does not say it has no cap"
