"""An over-long answer is shortened by dropping elements, not by cutting text.

The defect, measured 2026-09-02: the answer was serialized in full and then, if
it exceeded the cap, replaced by an envelope holding a SLICE of the JSON string.
A slice of JSON is not JSON, so on any page above the cap the caller received
zero usable elements. Not the first fifty: zero.

How close that cap sat, with the fields the snapshot returns today: about 112
characters per element, so the old default of 6000 ran out at around fifty. A
real results page passes that without effort, and one page in the test corpus
carried 118.

A partial list a model can act on beats a complete one it cannot read.
"""
import json

import pytest

from invisible_playwright_mcp import actions

HEAD = {"title": "list", "url": "https://example.com/"}


def elements(n):
    return [{"tag": "a", "id": "l%d" % i, "href": "/i/%d" % i,
             "text": "Result number %d" % i, "at": [10, 20 * i], "in_view": True}
            for i in range(n)]


@pytest.mark.parametrize("cap", [800, 2000, 6000, 20000])
def test_the_answer_is_always_valid_json(cap):
    """The heart of the defect: before, above the cap, it was not."""
    s = actions.capped_elements(HEAD, elements(200), limit=cap)
    d = json.loads(s)
    assert isinstance(d["interactive_elements"], list)


@pytest.mark.parametrize("cap", [800, 2000, 6000])
def test_usable_elements_remain_above_the_cap(cap):
    """Zero elements was the old behaviour, and it is the case not to repeat."""
    d = json.loads(actions.capped_elements(HEAD, elements(200), limit=cap))
    assert len(d["interactive_elements"]) > 0, "nothing usable was left above the cap"
    assert d["omitted_elements"] == 200 - len(d["interactive_elements"])


def test_the_cap_is_respected():
    for cap in (800, 2000, 6000, 20000):
        s = actions.capped_elements(HEAD, elements(300), limit=cap)
        assert len(s) <= cap, f"cap {cap} exceeded: {len(s)}"


def test_nothing_is_omitted_below_the_cap():
    d = json.loads(actions.capped_elements(HEAD, elements(5), limit=6000))
    assert len(d["interactive_elements"]) == 5
    assert "omitted_elements" not in d


def test_the_head_survives_the_cut():
    """Title and url must stay: without them the model does not know where it is."""
    d = json.loads(actions.capped_elements(HEAD, elements(500), limit=900))
    assert d["title"] == "list"
    assert d["url"] == "https://example.com/"


def test_the_kept_elements_are_the_first_in_document_order():
    """Predictable rather than optimal: a form is read from the top, and an order
    that changed with the cap would make two calls disagree with each other."""
    d = json.loads(actions.capped_elements(HEAD, elements(200), limit=3000))
    ids = [e["id"] for e in d["interactive_elements"]]
    assert ids == ["l%d" % i for i in range(len(ids))]


def test_a_huge_list_does_not_take_absurdly_long():
    """The naive version dropped one element at a time and re-serialized, which
    on two thousand elements means two thousand serializations."""
    import time
    t0 = time.time()
    actions.capped_elements(HEAD, elements(3000), limit=6000)
    assert time.time() - t0 < 2.0


class _FakeSession:
    """A page with more elements than fit under the cap."""

    def __init__(self, n=200):
        self._n = n

    def page(self):
        return self

    async def evaluate(self, _script, *a):
        return {"title": "list", "url": "https://example.com/",
                "interactive_elements": elements(self._n)}


@pytest.mark.asyncio
async def test_snapshot_really_uses_the_element_cut():
    """The wiring, not the piece.

    Putting `json_capped` back inside `snapshot()` left all 63 tests green: they
    exercised `capped_elements` in isolation and none of them looked at whether
    it was called. A piece that works and a connection that is missing are
    indistinguishable until somebody tests from here.
    """
    s = await actions.snapshot(_FakeSession(200), max_chars=6000)
    d = json.loads(s)
    assert d["interactive_elements"], "snapshot returned zero usable elements"
    assert "preview" not in d, "snapshot is still cutting the string instead of the list"
    assert d["omitted_elements"] > 0


@pytest.mark.asyncio
async def test_by_default_there_is_no_cap():
    """A cap is a guess about what the caller needs, made without knowing what it
    is looking for, and a form's submit button is exactly the sort of thing that
    sits past it. By default everything comes back."""
    s = await actions.snapshot(_FakeSession(400))
    d = json.loads(s)
    assert len(d["interactive_elements"]) == 400
    assert "omitted_elements" not in d


@pytest.mark.asyncio
async def test_an_explicit_cap_is_still_honoured():
    """Whoever asks for one gets it, and gets usable elements, not an envelope."""
    d = json.loads(await actions.snapshot(_FakeSession(400), max_chars=4000))
    assert 0 < len(d["interactive_elements"]) < 400
    assert d["omitted_elements"] > 0
