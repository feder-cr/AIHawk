"""The README offers BOTH ways in, and offers them first.

⛔ THE REQUIREMENT IS ABOUT POSITION, NOT PRESENCE, which is why this file exists
instead of a grep. There are two ways to use this product and only one real
question behind them - where the model comes from:

  1. you already have an MCP client with a model in it (Claude Code, Claude
     Desktop, Cursor), and this browser arrives there as tools;
  2. you have no client, and our interface brings a model with an OpenRouter key.

Both were already documented before this test was written. The MCP server named
the interface at line 140 of 161, under a heading that reads like a footnote, and
the interface named the MCP path at line 114 of 159 under "Already have an MCP
client? Then you may not need this at all". A reader who stopped at the first
screen - which is most readers - saw one option and concluded it was the only one.

So the assertion is that the offer sits in the FIRST section that is not the
title, and that both commands are inside it. A README that mentions both paths
somewhere passes a grep and fails the requirement.
"""
from __future__ import annotations

import pathlib
import re

import pytest

README = pathlib.Path(__file__).resolve().parents[1] / "README.md"

#: The literal command for each path. Literal on purpose: this is what a reader
#: copies, and a paraphrase in the README is not a way in.
#:
#: Bare on purpose, without the `uvx ` the page puts in front of them today:
#: they matched the pip form the page showed for one day (2026-09-05 to
#: 2026-09-06) and they match the uv form it shows now, so the test measures
#: the offer and not the launcher that happens to start it.
MCP_WAY = "invisible-playwright-mcp"
UI_WAY = "aihawk ui"


def _headings(text):
    """(line number, heading) for every H1 and H2, in order.

    H1 and H2 only. A page may split the choice into "### 1." and "### 2."
    under one heading - that is the same choice, presented well, and an
    earlier version of this file called it two sections and went red on it.

    Fenced code is skipped, and it was not until 2026-09-06. A bash comment
    starts with `# ` too, and the line `# then, in a new terminal:` inside the
    install block was read as an H1, which split the offer in two and turned a
    correct page red. The parser was wrong, not the page.
    """
    heads, fenced = [], False
    for number, line in enumerate(text.split(chr(10)), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"#{1,2} ", line):
            heads.append((number, line.strip()))
    return heads


def _sections_of(text):
    """(heading, body) pairs, in order. The lead-in before the first heading is
    returned under an empty heading, because a logo block is not a section."""
    lines = text.split(chr(10))
    out, start, heading = [], 1, ""
    for number, next_heading in _headings(text):
        out.append((heading, chr(10).join(lines[start - 1:number - 1])))
        start, heading = number + 1, next_heading
    out.append((heading, chr(10).join(lines[start - 1:])))
    return out


def _sections():
    return _sections_of(README.read_text(encoding="utf-8"))


def test_the_sections_parse():
    """Otherwise everything below passes on an empty list."""
    sections = _sections()
    assert len(sections) > 3, "only %d sections parsed; the regex is wrong" % len(sections)
    assert any(h for h, _ in sections), "no headings found at all"


def test_both_ways_in_are_offered():
    text = README.read_text(encoding="utf-8")
    for way in (MCP_WAY, UI_WAY):
        assert way in text, (
            "the README never shows `%s`, so one of the two ways to use this is "
            "missing entirely" % way)


#: How far down "immediately" reaches, in lines. A screen of rendered markdown
#: is roughly this, and the requirement is about what a reader sees before
#: deciding whether to keep scrolling.
#:
#: ⛔ This started as "within the first two sections" and that was wrong for a
#: reason worth keeping: both commands begin with `uvx`, so the uv install has
#: to come BEFORE the choice or neither column works. A section-index rule
#: forbade the correct page. Counting lines measures what the requirement
#: actually says; counting sections measured the shape it happened to have.
FIRST_SCREEN = 45


def _where_the_offer_starts(text):
    """(line number, heading) of the section that carries BOTH commands."""
    lines = text.split(chr(10))
    heads = _headings(text)
    for pos, (line, heading) in enumerate(heads):
        end = heads[pos + 1][0] if pos + 1 < len(heads) else len(lines) + 1
        body = chr(10).join(lines[line - 1:end - 1])
        if MCP_WAY in body and UI_WAY in body:
            return line, heading
    return None, None

def test_the_offer_comes_within_the_first_screen():
    """Where the OFFER begins, not where each command literal sits.

    ⛔ The literal position is the wrong measurement and this test made that
    mistake first. Both pages present the choice as a two-column HTML table, and
    the table scaffolding puts twenty lines of markup between the heading and the
    second command without costing the reader a single line on screen. Measured
    that way the correct page failed. What a reader meets is the heading, so that
    is what is measured.

    Known-bad is what these pages looked like before 2026-09-03, and it is checked
    rather than remembered: see the test below.
    """
    line, heading = _where_the_offer_starts(README.read_text(encoding="utf-8"))
    assert line is not None, "no single section offers both ways"
    assert line <= FIRST_SCREEN, (
        "the choice starts at line %d, under %r, past the first screen a reader "
        "sees" % (line, heading))


def test_the_check_fails_on_the_pages_as_they_used_to_be():
    """The gate against a known-bad input, and the input is real history.

    A position check that has only ever passed says nothing about whether it can
    see a page where the offer is buried - which is the only page it exists to
    reject.
    """
    buried = chr(10).join([
        "# A project",
        "",
        "## Overview",
        "",
    ] + ["Prose about the project." for _ in range(60)] + [
        "",
        "## Already have an MCP client?",
        "",
        "Then you may not need this at all: `%s`." % MCP_WAY,
        "",
        "Otherwise `%s`." % UI_WAY,
    ])
    line, _ = _where_the_offer_starts(buried)
    assert line is not None, "the helper cannot even find the offer"
    assert line > FIRST_SCREEN, (
        "a page with the offer %d lines down passes, so this check is blind" % line)


def test_a_comment_inside_a_fence_is_not_a_heading():
    """The known-bad for the parser itself, and it is the page of 2026-09-06.

    Both install blocks opened with `# uv, once. Windows:` and carried
    `# then, in a new terminal:` before the fetch. Read as headings, those
    lines put the two ways under two different "sections", and the check went
    red on a page that offered both ways in one place, as required.
    """
    page = chr(10).join([
        "# A project",
        "",
        "## Two ways",
        "",
        "```bash",
        "# uv, once. Windows:",
        "install uv",
        "# then, in a new terminal:",
        MCP_WAY,
        "```",
        "",
        "```bash",
        "# Linux:",
        UI_WAY,
        "```",
    ])
    line, heading = _where_the_offer_starts(page)
    assert (line, heading) == (3, "## Two ways"), (
        "a fenced comment was read as a heading; the offer is now at %r under %r"
        % (line, heading))
    assert [h for h, _ in _sections_of(page) if h] == ["# A project", "## Two ways"]


def test_the_two_ways_are_offered_as_one_choice():
    """In the SAME section, so they read as alternatives rather than as two
    unrelated facts a reader has to notice and compare for themselves."""
    sections = _sections()
    found = {}
    for index, (heading, body) in enumerate(sections):
        for name, way in (("mcp", MCP_WAY), ("ui", UI_WAY)):
            if way in body and name not in found:
                found[name] = (index, heading)
    assert set(found) == {"mcp", "ui"}, "missing: %s" % sorted({"mcp", "ui"} - set(found))
    assert found["mcp"][0] == found["ui"][0], (
        "the two ways are in different sections (%r and %r), so nothing on the "
        "page says they are alternatives" % (found["mcp"][1], found["ui"][1]))


def test_the_offer_says_what_each_one_costs_the_reader():
    """A choice with no basis for choosing is not a choice.

    What distinguishes the two is where the model comes from: a client you
    already pay for, or an OpenRouter key. If neither is named next to the
    commands, the reader has to try one to find out.
    """
    sections = _sections()
    body = next(b for _, b in sections if MCP_WAY in b)
    low = body.lower()
    assert "openrouter" in low, (
        "the choice does not mention OpenRouter, so nothing says what the second "
        "way needs from the reader")
    assert any(c in low for c in ("claude", "cursor")), (
        "the choice does not name a single MCP client, so nothing says who the "
        "first way is for")


def test_no_tool_name_that_does_not_exist():
    """Any tool the README names has to be real.

    Cheaper than keeping a list in sync and it never goes stale: it constrains
    what may be SAID rather than requiring the page to say everything.
    """
    import asyncio

    try:
        from invisible_playwright_mcp import server
    except ImportError:  # pragma: no cover
        pytest.skip("invisible-playwright-mcp is not installed")

    real = {t.name for t in asyncio.run(server.mcp.list_tools())}
    named = set(re.findall(r"`((?:browser|session)_\w+)`",
                           README.read_text(encoding="utf-8")))
    assert not named - real, (
        "the README names tools that do not exist: %s" % sorted(named - real))


def test_no_hand_written_count_of_tools():
    """"the fourteen tools" was written into six files and a test literal, so
    every new tool was an edit in a place nobody remembers. A count in prose is
    a fact with two homes."""
    text = README.read_text(encoding="utf-8").lower()
    bad = re.findall(r"\b(?:eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
                     r"seventeen|eighteen|nineteen|twenty|\d{1,3})\s+tools\b", text)
    assert not bad, "the README writes a tool count in prose: %s" % bad
