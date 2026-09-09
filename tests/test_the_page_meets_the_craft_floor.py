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

#: The stylesheet alone. A brace count over the whole page would count
#: every block in the script too, and answer about the wrong thing.
CSS = PAGE[PAGE.index("<style>"):PAGE.index("</style>")]


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


def test_the_stylesheet_closes_everything_it_opens():
    """⛔ A MISSING BRACE DOES NOT FAIL, IT SWALLOWS. An `@media` block left
    unclosed while being moved took every rule after it inside itself, so the
    whole page above the breakpoint quietly lost its header height, its browser
    bar and its composer width - and nothing went red, because a stylesheet
    with an unbalanced brace is still one the browser parses. It was found by
    measuring a layout whose numbers made no sense.

    Counting is the whole check, and it is enough.

    Known-bad: drop any closing brace.
    """
    css = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    opened, closed = css.count("{"), css.count("}")
    assert opened == closed, (
        "the stylesheet opens %d blocks and closes %d, so everything after "
        "the unclosed one is inside it" % (opened, closed))


def test_the_narrow_layout_comes_after_the_layout_it_overrides():
    """⛔ SAME SPECIFICITY, SO SOURCE ORDER DECIDES, and the first version of
    this rule sat ABOVE the rules it meant to override: it changed nothing, and
    measured as though the breakpoint did not exist.

    Under 720px the two panes stack, because side by side the right one is
    allotted nothing and its bar is drawn past the edge of the window. Measured
    in a frame 320px wide, which is what WCAG 1.4.10 asks a layout to survive:
    the document scrolled sideways to 482px before this rule and not at all
    after it, at every width from 320 to 1400.

    Known-bad, three: move the block above `#right`, drop the wrap, drop the
    hidden splitter.
    """
    narrow = CSS.find("@media (max-width:720px)")
    assert narrow > 0, "nothing stacks the panes when they no longer fit"
    base = CSS.find("#right{ flex:1; min-width:0")
    assert base > 0, "the base rule for the browser pane is gone"
    assert narrow > base, (
        "the narrow layout is declared before the layout it overrides, so at "
        "equal specificity the base rule wins and the breakpoint does nothing")
    block = CSS[narrow:CSS.index("}", CSS.index("#right{ flex:1 0 100%", narrow))]
    for needed in ("flex-wrap:wrap", "#split{ display:none }"):
        assert needed in block, (
            "the stacked layout is missing %r, without which the panes do not "
            "stack at all" % needed)

def test_the_type_scale_has_steps_a_reader_can_see():
    """⛔ EITHER THE SAME SIZE OR A REAL STEP, NEVER A HAIR APART. Measured on
    the running page, this column drew NINE size/weight pairs at 11, 12, 13, 14
    and 16px - four sizes inside three pixels. A 1.08 step is not read as a
    step, it is read as an accident, and a scale that fine is a scale in name
    only.

    So two levels may share a size, and then weight or colour separates them,
    which is the stronger signal anyway. What is forbidden is the middle: one or
    two pixels, carrying nothing and costing a step.

    This gate used to demand every pair be at least 1.9px apart, which forbade
    the sharing as well as the hair. That was the wrong half to forbid.

    Known-bad, three: put two levels one pixel apart; drop the body under the
    reading floor; give two levels the same size AND the same weight.
    """
    got = {name: float(v) * 16 for name, v in
           re.findall(r"--t-(h1|h2|h3|body|label):([\d.]+)rem", CODE)}
    assert {"h1", "h2", "body", "label"} <= set(got), (
        "the type scale lost a role: %s" % got)

    assert got["body"] >= 15, (
        "the body is %.0fpx on a column that exists to be read, and every "
        "source puts the floor at 15" % got["body"])

    for big, small in (("h1", "h2"), ("h2", "body"), ("body", "label")):
        step = got[big] - got[small]
        assert step == 0 or step >= 2, (
            "%s and %s are %.1fpx apart: too far to be one level, too close to "
            "read as two" % (big, small, step))

    # One ratio: the distinct sizes, in order, step by a consistent amount.
    sizes = sorted(set(got.values()))
    for a, b in zip(sizes, sizes[1:]):
        assert 1.15 <= b / a <= 1.35, (
            "%.0f to %.0f is a ratio of %.2f, off the scale this page declares "
            "(~1.2)" % (a, b, b / a))

    # A level that shares a size has to say what carries it instead.
    for role in ("h2", "h3"):
        if got.get(role) == got["body"]:
            rule = re.search(r"h[45]\.md-h[^{]*\{([^}]*)\}", CODE) if role == "h3" \
                else re.search(r"h4\.md-h\{([^}]*)\}", CODE)
            assert rule and ("font-weight" in rule.group(1)
                             or "color" in rule.group(1)), (
                "%s is the body's size and nothing else separates it" % role)
