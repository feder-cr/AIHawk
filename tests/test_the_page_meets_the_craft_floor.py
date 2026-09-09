"""The floor under every visual decision, checked mechanically.

These are not opinions about how the interface should look: they are the few
craft rules that can be read off the file and that this page has broken at least
once. Each one costs nothing to keep and is invisible until it is missing, which
is exactly the kind of rule that rots without a gate.

The one that matters most is the last group - selection, caret, scrollbar, focus
ring. Those surfaces are drawn by the browser from defaults that belong to no
design system, and theming them is the cheapest signal that a page was built
rather than assembled.
"""
from __future__ import annotations

import re

from aihawk.web import PAGE

#: The page without its comments: every rule here is about what SHIPS, and a
#: comment explaining why something is not done must not read as doing it.
CODE = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)


def test_no_glyph_stands_in_for_an_icon():
    """⛔ AN ICON IS DRAWN. A pencil, an arrow or an emoji borrowed from the text
    encoding is a shortcut that shows: it lands in whatever the reader's font
    decides, at whatever weight that font has, beside icons drawn at a chosen
    one. This page shipped `&#9998;` as the mark on the queued-message chip.

    The five HTML entities that are punctuation, not pictures, stay allowed.

    Known-bad: put any numeric character entity back.
    """
    entities = set(re.findall(r"&#?\w+;", PAGE))
    allowed = {"&amp;", "&lt;", "&gt;", "&quot;", "&#39;", "&nbsp;"}
    assert not (entities - allowed), (
        "the page carries %s, and a character is not an icon"
        % ", ".join(sorted(entities - allowed)))

    # Emoji ride in as characters too, and are the same shortcut with a colour.
    # Only the marker this project writes its own hard rules with. The em dash
    # and the curly quote used to be allowed here too, and they were not in the
    # page at all: an allowlist that admits what nobody uses is a hole waiting
    # for the day somebody does - and the em dash is separately banned across
    # this whole product, so allowing it in the page would have been a gate
    # contradicting a rule.
    emoji = [c for c in PAGE if ord(c) > 0x2100 and c != "⛔"]
    assert not emoji, "the page draws with emoji: %s" % "".join(sorted(set(emoji)))


def test_the_drawn_icons_share_one_stroke():
    """Icons from one hand have one weight. This page had 2.5, 1.6 and 1.3 in
    three places, which reads as three icon sets borrowed from three products.

    Known-bad: give any `<svg>` a different stroke-width.
    """
    widths = set(re.findall(r'stroke-width="([\d.]+)"', PAGE))
    assert len(widths) == 1, (
        "the drawn icons use %d different stroke weights: %s"
        % (len(widths), ", ".join(sorted(widths))))


def test_no_callout_wears_a_coloured_bar_down_its_left_edge():
    """⛔ THE 2px STRIPE IS A COSTUME. A coloured bar on the left of an alert is
    the house style of every framework and belongs to none of them; a tint plus
    a hairline in the same hue says the same thing without borrowing anybody's
    accent. The blockquote keeps its rule - a quotation is not a callout, and
    that rule is a typographic convention older than the web.

    Known-bad: put an `inset 2px 0 0 var(--err)` back on the error row.
    """
    bars = re.findall(r"box-shadow:\s*inset (\d+)px 0 0 var\(--(err|accent|ok)\)", CODE)
    assert not bars, (
        "%d callout(s) wear a coloured left bar: %s" % (len(bars), bars))


def test_a_heading_gets_more_space_above_it_than_below():
    """The space is what says a section starts. A heading floating equidistant
    between two paragraphs belongs to neither of them.

    Known-bad: even the two margins out.
    """
    rule = re.search(r"h3\.md-h[^{]*\{([^}]*)\}", CODE)
    assert rule, "the answer's headings no longer have a rule of their own"
    margin = re.search(r"margin:([^;]+);", rule.group(1))
    assert margin, "the heading no longer states its own spacing"
    # The shorthand carries calc() values, so it is split on its middle zero
    # rather than on whitespace: `calc(a + b) 0 var(--s2)` is three components
    # and five tokens.
    parts = margin.group(1).strip().split(" 0 ")
    assert len(parts) == 2, "the heading's margin is no longer top / 0 / bottom"
    assert parts[0] != parts[1], (
        "a heading with %s above and %s below belongs to neither side" % tuple(parts))


def test_the_surfaces_the_browser_would_have_picked_are_picked_here():
    """⛔ THE CHEAPEST SIGNAL THAT A PAGE WAS BUILT RATHER THAN ASSEMBLED, and
    the one most often skipped: text selection, the caret, the scrollbar and the
    focus ring all ship with defaults that belong to no design system. On a dark
    page a default selection is a bright blue block from the operating system.

    Known-bad: drop any one of the four.
    """
    for what, pattern in (
        ("the text selection", r"::selection\s*\{[^}]*background"),
        ("the caret", r"caret-color:"),
        ("the scrollbar", r"scrollbar-color:"),
        ("the focus ring", r":focus-visible\s*\{[^}]*outline:\s*\d"),
    ):
        assert re.search(pattern, CODE), "%s is left to the browser" % what

    # A ring that is switched off for everything is worse than none at all: it
    # takes the browser's and gives nothing back.
    off = re.findall(r":focus-visible\s*\{\s*outline:\s*none", CODE)
    assert len(off) <= 1, (
        "%d rules turn the focus ring off; the splitter is the only element "
        "that draws its own" % len(off))


def test_the_type_scale_has_steps_a_reader_can_see():
    """Two heading sizes a single pixel apart are one size with two names: the
    hierarchy then rests on weight alone, which is one signal doing two jobs.

    Known-bad: move the two headings back within a pixel of each other.
    """
    got = {name: float(v) for name, v in
           re.findall(r"--t-(h1|h2|h3|body):([\d.]+)rem", CODE)}
    assert {"h1", "h2", "body"} <= set(got), "the type scale lost a role: %s" % got
    for big, small in (("h1", "h2"), ("h2", "body")):
        step = (got[big] - got[small]) * 16
        assert step >= 1.9, (
            "%s and %s are %.1fpx apart, which is not a step anybody sees"
            % (big, small, step))
