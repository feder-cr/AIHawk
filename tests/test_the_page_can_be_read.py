"""The two things a page has to get right before anything else it does.

⛔ CONTRAST AND TARGET SIZE ARE ARITHMETIC, WHICH IS WHY THEY ARE HERE. Every
other judgement about this interface is a matter of taste and belongs in a
screenshot; these two are numbers with a threshold, and a threshold that nobody
computes is a threshold that drifts. WCAG 2.2 asks 4.5:1 for text, 3:1 for a
graphic that carries meaning, and 24 by 24 pixels for anything you have to hit.

Measured on the running page before this was written: the state beside the
browser read at 2.23:1, the token meter at 2.71, the placeholder inside a screen
at 2.51, the layout icons at 2.51 - and nine more rules had put words on the ink
this file's own palette annotates as `decorative only`. The worst of them was
`.href`, the address printed beneath a link precisely so that an injected one
can be read; it was the hardest text on the page to read.
"""
from __future__ import annotations

import re

from aihawk.web import PAGE

#: The palette declares its own ratios in a comment beside each hex. This is
#: what makes that comment checkable rather than decorative in its own right.
INK = re.compile(r"--(fg(?:-\d)?):\s*(#[0-9a-fA-F]{6});\s*/\*\s*([\d.]+):1")


def channel(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hexcolour):
    r, g, b = (int(hexcolour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(one, two):
    a, b = sorted((luminance(one), luminance(two)))
    return (b + 0.05) / (a + 0.05)


def blocks():
    """Every CSS rule in the page as (selector, declarations), comments gone."""
    css = PAGE[PAGE.index("<style>"):PAGE.index("</style>")]
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return re.findall(r"([^{}]+)\{([^{}]*)\}", css)


def test_the_palette_carries_the_ratios_it_claims():
    """⛔ THE NUMBER IN THE COMMENT IS THE REASON THE RULE ABOVE EXISTS. Four
    inks, each annotated with its contrast against the page's base, and every
    decision about which one a thing gets was made by reading those. A hex
    nudged for taste moves the ratio and leaves the comment describing the old
    one, which is how a palette stops meaning anything.

    Known-bad: lighten the base, or darken any ink, without moving its number.
    """
    base = re.search(r"--base:\s*(#[0-9a-fA-F]{6})", PAGE)
    assert base, "the page no longer declares the colour everything sits on"
    claimed = {name: (hexc, float(ratio)) for name, hexc, ratio in INK.findall(PAGE)}
    assert set(claimed) >= {"fg", "fg-2", "fg-3", "fg-4"}, \
        "the ink ladder is %s" % sorted(claimed)

    for name, (hexc, ratio) in claimed.items():
        real = contrast(hexc, base.group(1))
        assert abs(real - ratio) < 0.1, (
            "--%s is %s, which reads at %.1f:1 against the base while the "
            "palette says %.1f:1" % (name, hexc, real, ratio))


def test_no_word_on_this_page_is_painted_with_the_decorative_ink():
    """⛔ THE CLASS, NOT THE INSTANCE. `--fg-4` is annotated `decorative only`
    and eleven rules used it as a text colour anyway: the message count beside a
    conversation, the address under a link, the timing on a step, a list marker,
    the dim halves of the URL, the placeholder inside a preview. Each one read
    as a small deliberate choice; together they were most of the quiet text in
    the product, at half the contrast the same file says it needs.

    Known-bad: give any rule `color:var(--fg-4)` back.
    """
    claimed = {name: (hexc, float(r)) for name, hexc, r in INK.findall(PAGE)}
    assert claimed["fg-4"][1] < 4.5, (
        "--fg-4 now meets AA for text, so this gate is guarding a rule that no "
        "longer exists - decide what the ladder means before deleting it")
    assert claimed["fg-3"][1] >= 4.5, (
        "--fg-3 is where the words moved TO, and at %.1f:1 it does not meet AA "
        "either" % claimed["fg-3"][1])

    guilty = [sel.strip() for sel, decl in blocks()
              if re.search(r"(^|[^-])color:\s*var\(--fg-4\)", decl)]
    assert not guilty, (
        "%d rule(s) paint text with the ink this page annotates as decorative: %s"
        % (len(guilty), ", ".join(guilty)))


def test_nothing_you_have_to_click_is_smaller_than_the_floor():
    """⛔ 24 BY 24, AND THREE CONTROLS SAT AT 21, 22 AND 23. Close enough to
    look deliberate and short enough to fail: the Live/Frozen tabs, the Clear
    button, the layout icons - and the delete-a-conversation cross at 18, which
    is the control where a near miss costs the most.

    What this can see is a declared pixel size, not a computed one, so it is a
    floor and not a proof. That is still the shape every one of those defects
    had: a height typed into the rule.

    Known-bad: put any of them back under 24.
    """
    small = []
    for sel, decl in blocks():
        if "cursor:pointer" not in decl and "button" not in sel:
            continue
        for prop, px in re.findall(r"(?:min-)?(height|width):\s*(\d+)px", decl):
            if int(px) < 24:
                small.append("%s %s:%spx" % (sel.strip(), prop, px))
    assert not small, (
        "%d control(s) declare less than the 24px WCAG 2.2 asks for: %s"
        % (len(small), ", ".join(small)))


def test_no_attribute_leaks_onto_the_page_as_text():
    """⛔ A COMMENT INSIDE A START TAG ENDS THE TAG. The `>` that closes an HTML
    comment is the `>` that closes whatever tag it sits in, so every attribute
    written after it becomes visible text. It happened to the separator on
    2026-09-12: `aria-label="Width of the conversation" aria-valuenow="530">`
    printed down the seam between the two panes, in body type, with 577 tests
    green - because nothing in the suite reads the page the way a browser
    does. Found by looking at a screenshot.

    Two checks, from the parser side and from the source side: no text node
    outside script and style may carry attribute syntax, and no start tag may
    contain a comment opener.

    Known-bad: put a comment back between two attributes of any tag.
    """
    from html.parser import HTMLParser

    class Reader(HTMLParser):
        def __init__(self):
            super().__init__()
            self.inside = None
            self.leaks = []

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self.inside = tag

        def handle_endtag(self, tag):
            if tag == self.inside:
                self.inside = None

        def handle_data(self, data):
            if self.inside is None and '="' in data:
                self.leaks.append(" ".join(data.split())[:90])

    reader = Reader()
    reader.feed(PAGE)
    assert not reader.leaks, (
        "attribute syntax is drawn on the page as text, which is what a comment "
        "inside a start tag does to everything after it: %s" % reader.leaks)

    inside = re.findall(r"<[a-zA-Z][^<>]*<!--", PAGE)
    assert not inside, (
        "%d start tag(s) carry a comment opener, and the comment's closing "
        "bracket will end the tag early: %s" % (len(inside), inside))

