"""A sample answer published in the wiki names fields the server still has.

⛔ MEASURED, AND IT HAD BEEN WRONG FOR THREE VERSIONS. `docs/writing-an-mcp-
client-in-python.md` publishes a transcript of driving this server, and the
`browser_list` line in it carried `running: false` - a field removed in 0.54.0
- inside a fleet holding a browser that a freshly started server has not had
since open-first landed in 0.53.0. Somebody following that page saw an answer
the product cannot produce.

Nothing was watching. The content gate anchors on the total character count of
the tool descriptions, which moves whenever a tool is added, removed or
reworded, and it caught the twelve pages that publish that number on the day
`browser_list` was rewritten. It cannot see a JSON sample: a sample is prose to
it.

So this asks the server what the answer looks like, rather than holding a list
of field names that would go stale the same way the samples did. What is
compared is the VOCABULARY - the keys, at both levels - and not the values: a
sample is allowed to show a different session than yours, and is not allowed
to show a field that does not exist.
"""
from __future__ import annotations

import json
import pathlib
import re

from invisible_playwright_mcp.mcp.work import Work

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Every place a sample can appear: the wiki, the articles, the plugin skills
#: and the README. The same set the content gate reads.
WHERE = [p for base in ("docs", "articles", "skills")
         for p in sorted((ROOT / base).rglob("*.md"))] + [ROOT / "README.md"]

SAMPLE = re.compile(r"browser_list\s*->\s*(\{.*?\})\s*$", re.S | re.M)


class _OnePage:
    """A browser with one page, which is what a row is built from."""

    async def start(self):
        pass

    async def close(self):
        pass

    def is_usable(self):
        return True

    async def describe_pages(self):
        return [{"url": "https://example.com/", "title": "", "active": True}]


def samples():
    """(file, parsed answer) for every published `browser_list` answer."""
    out = []
    for path in WHERE:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in SAMPLE.finditer(text):
            flat = " ".join(m.group(1).split())
            try:
                out.append((path.relative_to(ROOT).as_posix(), json.loads(flat)))
            except ValueError as broken:
                raise AssertionError(
                    "%s publishes a browser_list answer that is not JSON, so "
                    "somebody copying it gets a parse error: %s"
                    % (path.name, broken))
    return out


async def test_every_published_sample_names_fields_the_server_has(tmp_path, monkeypatch):
    """Known-bad, and it is the defect that happened: put `running: false`
    back into a row of the sample, or `limit` back beside `focus`."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    work = Work("sample", factory=lambda **kwargs: _OnePage())
    await work.open("main")
    real = await work.listing()
    top, row = set(real), set(real["browsers"][0])
    assert "browsers" in top and "id" in row, real

    found = samples()
    assert found, (
        "no published sample was found at all, so this gate is watching "
        "nothing: the pattern or the files moved")

    for where, got in found:
        assert set(got) <= top, (
            "%s publishes %r, which browser_list does not answer (it answers "
            "%r)" % (where, sorted(set(got) - top), sorted(top)))
        for one in got.get("browsers") or []:
            assert set(one) <= row, (
                "%s publishes a browser row with %r, which no row carries (a "
                "row is %r)" % (where, sorted(set(one) - row), sorted(row)))


async def test_a_sample_of_a_server_that_has_just_started_shows_nothing_open(tmp_path, monkeypatch):
    """⛔ THE OTHER HALF OF WHAT WENT STALE, and the keys alone cannot see it:
    the old sample's fields were all real in their day, and what made it wrong
    was that it showed a browser. Since open-first, a server that has just
    started holds none - which is the first thing anybody reading that page
    will run.

    Known-bad: publish a sample with a browser in it beside the words that say
    nothing has been opened.
    """
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    work = Work("sample", factory=lambda **kwargs: _OnePage())
    fresh = await work.listing()
    assert fresh["browsers"] == [] and fresh["focus"] == ""

    for where, got in samples():
        if "not open" not in json.dumps(got):
            continue
        assert got.get("browsers") == [] and not got.get("focus"), (
            "%s publishes an answer that says nothing is open and lists a "
            "browser anyway: %r" % (where, got))
