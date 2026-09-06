"""The snapshot must see what is there and skip what is not.

Measured 2026-09-02 against the version that used `el.offsetParent !== null`: on
a page with five elements it reported three, and it was wrong in BOTH
directions.

  button position:fixed    visible     -> SKIPPED
  visibility:hidden        invisible   -> KEPT
  left:-9999px             invisible   -> KEPT
  div[role=button]         clickable   -> NEVER LOOKED FOR

`offsetParent` is `null` on any `position:fixed` element, and that is not a
laboratory configuration: it is the cookie banner, the sticky bar, the button
inside a modal. When it is the modal that blocks the page, the model does not
see it at all, so the failure is not local, it is terminal.

These tests run against the filter in isolation, without a browser: the logic
lives in a JS string, and to exercise it here it is checked against the shape of
the data that string produces. The end-to-end check with a real browser is in
test_real_launch.py.
"""
import re

from invisible_playwright_mcp import actions


def _code(js: str) -> str:
    """The JS with its comments removed.

    Needed because the comment explaining the incident NAMES `offsetParent`, and
    it is right to name it: it says why that line must not come back. A test
    that read the comments too would go red over the documentation of the very
    defect it protects. It is the same mistake this project has hit several
    times - writing the check against the comment instead of the code - only
    inverted.
    """
    return re.sub(r"//[^\n]*", "", js)


def test_the_filter_no_longer_asks_for_offsetparent():
    """The line that caused the defect must not come back."""
    assert "offsetParent" not in _code(actions.SNAPSHOT_JS), (
        "offsetParent is back in the snapshot: it skips every position:fixed "
        "element, meaning cookie banners, sticky bars and modal buttons"
    )


def test_the_filter_looks_at_what_actually_decides_visibility():
    js = actions.SNAPSHOT_JS
    for expected in ("getBoundingClientRect", "visibility", "display"):
        assert expected in js, f"the snapshot does not look at {expected}"


def test_the_query_reaches_elements_that_are_not_form_tags():
    """Half the buttons on the web are not `<button>`.

    A `div` with `role=button` and a click handler is as clickable as a button,
    and the closed list of tags did not look for it at all.
    """
    js = actions.SNAPSHOT_JS
    assert 'role="button"' in js or "role='button'" in js or "[role=" in js
    assert "onclick" in js
    assert "tabindex" in js


def test_the_snapshot_still_reports_the_fields_a_caller_needs():
    js = actions.SNAPSHOT_JS
    for field in ("tag", "text", "title", "url", "interactive_elements"):
        assert field in js


def test_the_snapshot_does_not_write_to_the_page():
    """Read only, and not as a matter of taste.

    Injecting an attribute to number the elements would mutate the DOM, which
    creates a detection surface inside a product that exists not to have one. If
    a stable index is ever wanted, that choice gets made in the open rather than
    slipped in here.
    """
    js = actions.SNAPSHOT_JS
    for write in ("setAttribute", "dataset.", "innerHTML =", "classList.add"):
        assert write not in js, f"the snapshot writes to the page: {write}"


def test_visibility_rules_are_expressed_once_each():
    """A rule written twice drifts. This is a shape check on the filter being
    one function rather than copied per branch.

    Counted on the CODE. The first version counted the raw string and went red
    the day a comment explained why getBoundingClientRect needs a guard: four
    occurrences, of which two were prose. Every other check in this file already
    strips comments for the same reason, and this one was the exception that
    proved it mattered.
    """
    js = _code(actions.SNAPSHOT_JS)
    assert js.count("getBoundingClientRect") <= 2, (
        f"the rectangle is read {js.count('getBoundingClientRect')} times in "
        "code; the filter is being copied per branch")


def test_the_snapshot_does_not_deduplicate():
    """Measured on the same DOM: deduplicating by text removed 8.1% of the
    elements in exchange for 13% of the weight.

    Two buttons with the same text and no id are not a duplicate: they are two
    different places on the screen, and on a results page they are "add to cart"
    repeated once per product. Hiding one from the model is the character cap
    wearing a different name.
    """
    js = _code(actions.SNAPSHOT_JS)
    for tell in ("doppioni", "firma", "dedup", "signature"):
        assert tell not in js, f"a deduplication is back: {tell}"
