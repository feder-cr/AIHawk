"""The ink of this page is measured here, not described in a comment.

⛔ THIS IS THE MOST REPEATED DEFECT IN THE STYLESHEET AND NOTHING WAS WATCHING
IT. `01-tokens.css` carries two separate blocks about the same thing: a token
declared DECORATION ONLY ended up colouring words - nine rules at 2.4:1 where
AA asks 4.5, among them the address that is printed precisely so an injected
link can be read, which was the hardest thing on the page to read - and then
the same class again one rung up, a graphic measured against the ground instead
of against the surface it is painted on.

Both were found by somebody looking. The file records the ratios it relies on
as numbers written into comments, and nothing recomputes them: this project
refuses a hand-written count in its documentation and had no opinion about one
in its stylesheet.

So this computes them. Three halves:

  * every ratio the file PUBLISHES is recomputed and has to match, because a
    comment that has gone stale is worse than no comment - it is evidence that
    was true once;
  * the floors for the roles the file itself declares, against the surfaces it
    itself names;
  * and the rule that has been broken twice, made mechanical: the decorative
    token never sets `color` anywhere.

The arithmetic is WCAG 2.x relative luminance, which is what every source the
file cites is quoting.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSS = ROOT / "src" / "invisible_playwright_mcp" / "ui" / "css"
TOKENS = (CSS / "01-tokens.css").read_text(encoding="utf-8")

#: Text needs 4.5:1 and a graphic that carries meaning needs 3:1. Both are
#: WCAG AA, and both are quoted in the file this reads.
TEXT, GRAPHIC = 4.5, 3.0


def _hex(name):
    got = re.search(r"--%s:\s*(#[0-9a-fA-F]{6})" % re.escape(name), TOKENS)
    assert got, "the token --%s is gone, and rules still name it" % name
    return got.group(1)


def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(colour):
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def ratio(ink, surface):
    a, b = _luminance(_hex(ink)), _luminance(_hex(surface))
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def test_every_ratio_the_file_publishes_is_still_true():
    """⛔ A NUMBER WRITTEN BY HAND IN A FILE NOBODY RE-READS GOES STALE IN DAYS,
    and this project already refuses one in its documentation. The stylesheet
    is the one place where that was allowed, in the file whose whole subject is
    numbers that have to hold.

    Every `N:1` written beside a token is recomputed from the token itself.

    Known-bad: move any ink by a shade and leave its comment where it is.
    """
    #: (token, the surface its published number is measured against). The file
    #: says "the contrast each one carries against --base" for the ink ladder,
    #: and names --raised where a value is measured where it is painted.
    published = {
        ("fg", "base"): 14.5, ("fg-2", "base"): 8.4, ("fg-3", "base"): 6.3,
        ("fg-3", "raised"): 5.9, ("fg-4", "base"): 3.9,
        ("accent", "base"): 8.5, ("ok", "base"): 8.6, ("err", "base"): 7.4,
    }
    #: Figures in the file that are NOT a measurement of a token as it stands.
    #: Named rather than listed, so a new one has to be classified instead of
    #: quietly joining the set.
    not_a_token = {
        "4.5": "the floor for text, quoted from the sources",
        "2.4": "what --fg-4 read as while it was colouring words",
        "2.96": "the same defect one rung up, measured on --raised",
        "2.23": "the state beside the browser, before the ladder",
    }
    #: Every number of that shape in the file, so a new one cannot be added
    #: without this test being taught where it is measured from.
    claims = set(re.findall(r"(\d+\.\d+):1", TOKENS))
    accounted = {"%.1f" % v for v in published.values()} | set(not_a_token)
    assert claims == accounted, (
        "a contrast figure appeared or moved in the token file and nothing "
        "here says what it is measured from: %r"
        % sorted(claims.symmetric_difference(accounted)))

    wrong = []
    for (ink, surface), said in published.items():
        got = ratio(ink, surface)
        if abs(got - said) >= 0.1:
            wrong.append("--%s on --%s says %s and is %.2f" % (ink, surface, said, got))
    assert not wrong, "; ".join(wrong)


def test_the_ink_that_carries_words_clears_the_floor_for_text():
    """Known-bad: darken any of the three, or paint the ladder on a surface it
    was not measured against."""
    low = []
    for ink in ("fg", "fg-2", "fg-3"):
        for surface in ("well", "base", "raised", "hover", "top"):
            got = ratio(ink, surface)
            if got < TEXT:
                low.append("--%s on --%s is %.2f, under %s" % (ink, surface, got, TEXT))
    # The accent and the two verdicts carry words too.
    for ink in ("accent", "ok", "err"):
        got = ratio(ink, "base")
        if got < TEXT:
            low.append("--%s on --base is %.2f, under %s" % (ink, got, TEXT))
    assert not low, "; ".join(low)


def test_the_decorative_ink_clears_the_floor_for_a_graphic_where_it_is_painted():
    """⛔ MEASURED WHERE IT IS PAINTED, which is the correction the file itself
    records: all of its uses sit on a raised surface, and against the ground it
    looked better than it was.

    Known-bad: darken it, or use it somewhere darker than it was measured for.
    """
    for surface in ("base", "raised"):
        got = ratio("fg-4", surface)
        assert got >= GRAPHIC, (
            "--fg-4 on --%s is %.2f, under the %s a graphic that carries "
            "meaning needs" % (surface, got, GRAPHIC))


def test_the_text_on_the_one_filled_control_clears_the_floor():
    """The send button is ink on the accent rather than on any surface, so it
    is the one pair the ladder above cannot see.

    Known-bad: lighten `--on-accent` towards the amber it sits on.
    """
    got = ratio("on-accent", "accent")
    assert got >= TEXT, (
        "the send button's mark is %.2f against its own fill, under %s"
        % (got, TEXT))


def test_the_decorative_token_never_colours_a_word():
    """⛔ THE RULE THIS FILE HAS BROKEN TWICE, MADE MECHANICAL. `--fg-4` is
    declared decoration only - a dot, a chevron, never a word - and it was
    carrying the count beside a conversation, the address under a link, the
    timing on a step, the marker of a list, the dim halves of the URL and the
    placeholder inside a preview: nine rules, all of them text.

    A comment cannot enforce that and did not. Setting `color` is the one
    property that puts a token on words, so it is the one this refuses. Border,
    background and shadow are what the token is for and stay.

    Known-bad: write `color:var(--fg-4)` anywhere.
    """
    guilty = []
    for sheet in sorted(CSS.glob("*.css")):
        text = re.sub(r"/\*.*?\*/", "", sheet.read_text(encoding="utf-8"), flags=re.S)
        for hit in re.finditer(r"(?<![-\w])color:\s*var\(--fg-4\)", text):
            line = text[:hit.start()].count("\n") + 1
            guilty.append("%s around line %d" % (sheet.name, line))
    assert not guilty, (
        "the token declared decoration-only is colouring words again, at 3.9:1 "
        "where text needs 4.5: %s" % ", ".join(guilty))
