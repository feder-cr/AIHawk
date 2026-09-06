"""The selector the snapshot hands out must reach one element, and the right one.

Measured 2026-09-02 across 969 interactive elements on real pages: 88.1% carried
an id, a name or an href, and every one of those selectors reached the element it
came from. But before this, only 47.6% reached it ALONE.

For the other 40% the obvious selector matches several nodes, and Playwright acts
on the first. A model looking at the third of five identical links builds
`a[href='/x']`, clicks, and is told it worked. Nothing raises, nothing is logged,
and the wrong thing happened. That is the failure mode this file exists for: not
an error, a quiet substitution.

The source checks run without a browser, because the mechanism lives in a JS
string. The end-to-end ones share ONE browser through a module fixture: three
parametrized cases plus two separate tests meant five launches and over two
minutes, and a launch is the most expensive thing in this suite.
"""
import re

import pytest

from invisible_playwright_mcp import actions

CASES = {
    "three identical links": (
        "<a href='/dup'>primo</a><a href='/dup'>secondo</a><a href='/dup'>terzo</a>", 3),
    "a unique id": ("<button id='solo'>x</button>", 1),
    "a named field": ("<input name='email'>", 1),
    "an id needing escaping": ("<div id='a.b:c' role='button'>x</div>", 1),
    "duplicate ids": ("<span id='same' role='button'>one</span>"
                      "<span id='same' role='button'>two</span>", 2),
    "a quote inside the value": ('<input name="e\'mail">', 1),
    # Appended to the handle order rather than woven into it, so nothing that
    # already worked changed. 9.5% of elements had no handle at all and fell
    # back on coordinates; of those, 58% carried a data-testid - an attribute
    # whose whole purpose is to be a stable unique handle - and a further
    # quarter an aria-label that was unique on the page.
    "a test id": ("<button data-testid='send'>Send</button>", 1),
    "duplicate test ids": ("<button data-testid='r'>a</button>"
                           "<button data-testid='r'>b</button>", 2),
    "an aria-label only": ("<div role='button' aria-label='Close'>x</div>", 1),
}


def _code(js: str) -> str:
    """The JS with its comments stripped: the comments name the defect on
    purpose, and a check that read them would fail over its own documentation."""
    return re.sub(r"//[^\n]*", "", js)


# --- the mechanism, without a browser --------------------------------------

def test_the_snapshot_emits_a_selector_field():
    assert "e.selector" in _code(actions.SNAPSHOT_JS), (
        "the snapshot no longer hands out a selector")


def test_the_handle_counts_matches_before_trusting_a_selector():
    """The count has to come from the document. Counting within the snapshot's
    own list undercounts, because an element filtered out here for being
    invisible still occupies a position in querySelectorAll, and the index would
    then point at the wrong node."""
    js = _code(actions.SNAPSHOT_JS)
    assert "querySelectorAll" in js
    assert "nth-match" in js, "ambiguity is no longer disambiguated"
    assert "indexOf" in js, "the position among matches is no longer computed"


def test_attribute_values_are_escaped_into_the_selector():
    """A quote or a backslash in an id or an href turns a selector into a syntax
    error, and a syntax error in a handle is a handle that never works."""
    js = _code(actions.SNAPSHOT_JS)
    assert "CSS.escape" in js, "ids go into a selector unescaped"
    assert "replace(/'/g" in js, "attribute values go into a selector unescaped"


def test_the_selector_uses_single_quotes():
    """It is about to be serialized as JSON, where every double quote comes back
    as two characters. CSS accepts either, so this is free."""
    js = _code(actions.SNAPSHOT_JS)
    assert "[name='" in js and "a[href='" in js, "the selector is back on double quotes"


# --- the same claims, on a real engine, in one browser ---------------------

@pytest.fixture(scope="module")
def page():
    from invisible_playwright import InvisiblePlaywright

    with InvisiblePlaywright(seed=1, headless=True) as browser:
        ctx = browser.new_context()
        yield ctx.new_page()
        ctx.close()


def _load(page, body):
    """Load a fragment as a page.

    The markup is percent-encoded, and that is not tidiness. A `data:` URL ends
    at the first `#`, so a body containing `href="#main"` is TRUNCATED there:
    the page loads, the browser reports no error, and the test then measures a
    document that stops mid-attribute. It cost one wrong diagnosis - a fix
    declared broken when the test had never shown it the case.
    """
    from urllib.parse import quote

    page.goto("data:text/html," + quote(f"<html><body>{body}</body></html>"))
    page.wait_for_timeout(250)
    return page.evaluate(actions.SNAPSHOT_JS)["interactive_elements"]


@pytest.mark.e2e
def test_every_selector_resolves_to_exactly_one_and_to_the_right_one(page):
    """Two assertions per element and they are not the same one. Resolving to a
    single node says the handle is unambiguous; reaching the element it came
    from says it is the RIGHT node. Without the index all three duplicate links
    satisfy the first and fail the second, which is the defect in its purest
    form: a handle that works and points somewhere else.
    """
    problems = []
    for name, (body, expected) in CASES.items():
        elements = _load(page, body)
        if len(elements) != expected:
            problems.append(f"{name}: saw {len(elements)} elements, expected {expected}")
            continue
        for element in elements:
            selector = element.get("selector")
            if not selector:
                problems.append(f"{name}: no handle for {element.get('text')!r}")
                continue
            found = page.locator(selector).count()
            if found != 1:
                problems.append(f"{name}: {selector!r} matched {found} elements")
                continue
            reached = page.locator(selector).inner_text(timeout=3000).strip()
            if reached != (element.get("text") or "").strip():
                problems.append(f"{name}: {selector!r} reached {reached!r}, "
                                f"snapshot said {element.get('text')!r}")
    assert not problems, problems


@pytest.mark.e2e
def test_the_href_is_not_repeated_inside_and_beside_the_selector(page):
    """Emitting the selector cost +47.2% of the payload on real pages and +15.1%
    once the duplicated href came out, for the same information: `a[href='/x']`
    says where the link goes as plainly as a separate field did. A link
    addressed by its id keeps its href, having nothing duplicated."""
    by_href, by_id = _load(page, "<a href='/dup'>a</a><a href='/dup'>b</a>"), None
    for element in by_href:
        assert "href" not in element, (
            f"the href is repeated beside the selector that already holds it: {element}")
        assert "/dup" in element["selector"]

    by_id = _load(page, "<a href='/solo' id='x'>a</a>")[0]
    assert by_id["selector"] == "#x"
    assert by_id.get("href") == "/solo", "a link addressed by id lost its href for nothing"


@pytest.mark.e2e
def test_an_ambiguous_selector_silently_clicks_the_first_match(page):
    """A claim about a DEPENDENCY, pinned because it is the reason the whole
    handle exists and because it is exactly the sort that changes on an upgrade
    without anybody noticing.

    It was written into four places - a public README, a tool description, the
    JS comments and these docstrings - before it was ever run. It turned out to
    be true. `page.click` on a selector matching three elements does not raise:
    it clicks the first and reports success. So does `locator.click`, which is
    the API documented as strict.

    If this test ever goes red, the fix is not here. It is that Playwright
    changed, and every sentence built on this needs rewriting.
    """
    body = ("<a href='/d' onclick='window.__hit=\"primo\";return false'>primo</a>"
            "<a href='/d' onclick='window.__hit=\"secondo\";return false'>secondo</a>"
            "<a href='/d' onclick='window.__hit=\"terzo\";return false'>terzo</a>")
    page.goto(f"data:text/html,<html><body>{body}</body></html>")
    page.wait_for_timeout(250)
    assert page.evaluate("() => document.querySelectorAll(\"a[href='/d']\").length") == 3

    page.click("a[href='/d']", timeout=5000)
    assert page.evaluate("() => window.__hit") == "primo", (
        "Playwright no longer silently picks the first match; the sentences "
        "explaining why `selector` exists need rewriting")

    page.goto(f"data:text/html,<html><body>{body}</body></html>")
    page.wait_for_timeout(250)
    page.click(":nth-match(a[href='/d'], 3)", timeout=5000)
    assert page.evaluate("() => window.__hit") == "terzo", (
        "the disambiguated handle no longer reaches the element it names")


@pytest.mark.e2e
def test_an_element_with_nothing_at_all_gets_no_handle_rather_than_a_bad_one(page):
    """The fallbacks stop where guessing would start. A bare button with only
    its text gets `at` and no selector, because a text-based selector is not
    stable and a handle that sometimes points elsewhere is the defect this whole
    file exists to remove."""
    element = _load(page, "<button>bare</button>")[0]
    assert "selector" not in element
    assert element["at"], "with no selector there must at least be a coordinate"


@pytest.mark.e2e
def test_one_impossible_element_does_not_cost_the_page(page):
    """Measured on a real site: the snapshot died inside getBoundingClientRect
    with "can't access property width, r is undefined", and the caller received
    nothing at all for the whole document.

    Nothing is the worst possible answer. It is worse than a partial list, and
    it is indistinguishable from a page with no controls on it, so the caller
    cannot even tell that something went wrong. A page can shadow or replace
    that method, and some do.
    """
    body = ("<a href='/uno' id='primo'>uno</a>"
            "<button id='rotto'>broken</button>"
            "<a href='/due' id='terzo'>due</a>"
            "<script>document.getElementById('rotto')"
            ".getBoundingClientRect = function () { return undefined; };</script>")
    elements = _load(page, body)
    texts = [e.get("text") for e in elements]
    assert "uno" in texts and "due" in texts, (
        f"one broken element cost the others: {texts}")
    assert "broken" not in texts, "the element with no rectangle was reported anyway"


@pytest.mark.e2e
def test_a_link_clipped_to_nothing_is_not_offered_as_clickable(page):
    """A "skip to content" link is invisible until focused, and clicking it as
    reported does not work: Playwright spends its whole timeout on it, 208
    attempts over 15 seconds, and hands back an opaque failure. Two of three
    failed clicks in a real-site run were exactly this.

    Excluding it is not concealment. `shown()` exists to report what is VISIBLE
    and already excludes visibility:hidden and opacity:0; an element clipped to
    a zero rectangle is invisible by the same rule, written differently in CSS.
    """
    body = ("<a href='#main' style='position:absolute;clip:rect(0,0,0,0);"
            "width:1px;height:1px;overflow:hidden'>Skip to content</a>"
            "<a href='/real' id='vero'>Real link</a>")
    texts = [e.get("text") for e in _load(page, body)]
    assert "Real link" in texts
    assert "Skip to content" not in texts, (
        "a link clipped to nothing was offered as clickable")


@pytest.mark.e2e
def test_a_small_but_visible_control_is_still_offered(page):
    """The exclusion has to stay narrow. A checkbox is small and perfectly
    clickable, and losing it would be the defect this file exists to prevent."""
    elements = _load(page, "<input type='checkbox' name='ok'><label>Yes</label>")
    assert any(e.get("name") == "ok" for e in elements), (
        f"a real checkbox was excluded as too small: {elements}")


@pytest.mark.e2e
def test_a_form_control_hidden_the_visually_hidden_way_is_kept(page):
    """The exclusion above must not reach form controls.

    A file input and a custom checkbox are hidden by exactly that markup on an
    enormous share of the web, with a styled <label> as the visible affordance,
    and they stay fully operable: Playwright can check() and set_input_files()
    them. Losing them would cost an agent the ability to tick a consent box or
    upload a file, which is worse than the skip link the rule exists to remove.

    Found by review, not by writing: the first version of the rule excluded
    both, and the case that made it obvious is that a skip link is an <a> while
    these are not.
    """
    hidden = "position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)"
    kept = {
        "file input": f"<input type='file' id='f' style='{hidden}'>",
        "custom checkbox": "<input type='checkbox' id='c' style='width:1px;height:1px;overflow:hidden'>",
        "hidden button": f"<button id='b' style='{hidden}'>Go</button>",
    }
    dropped = {
        "skip link": f"<a href='/main' style='{hidden}'>Skip</a>",
        "decorative div": f"<div role='button' style='{hidden}'>x</div>",
    }
    problems = []
    for name, body in kept.items():
        if not _load(page, body):
            problems.append(f"{name} was excluded and is operable")
    for name, body in dropped.items():
        if _load(page, body):
            problems.append(f"{name} was reported and cannot be clicked")
    assert not problems, problems


@pytest.mark.e2e
def test_elements_that_cannot_be_measured_are_counted_not_hidden(page):
    """A guard that swallows is worse than the crash it replaces.

    The first version returned false when getBoundingClientRect misbehaved, so a
    page replacing it on Element.prototype - the exact case the guard names -
    produced an empty list with no error, byte-identical to a page with no
    controls. The crash at least named its cause. Counting separates the two:
    one odd element leaves the rest and says 1, a shadowed prototype leaves
    nothing and says how many it could not read.
    """
    one_bad = ("<a href='/a' id='p'>one</a><button id='x'>bad</button>"
               "<a href='/b' id='t'>two</a>"
               "<script>document.getElementById('x')"
               ".getBoundingClientRect = () => undefined;</script>")
    page.goto("data:text/html," + __import__("urllib.parse", fromlist=["quote"]).quote(
        f"<html><body>{one_bad}</body></html>"))
    page.wait_for_timeout(250)
    d = page.evaluate(actions.SNAPSHOT_JS)
    assert len(d["interactive_elements"]) == 2
    assert d.get("unmeasurable") == 1, f"the skipped element was not counted: {d}"

    tampered = ("<a href='/a'>one</a><button>two</button>"
                "<script>Element.prototype.getBoundingClientRect = () => undefined;</script>")
    page.goto("data:text/html," + __import__("urllib.parse", fromlist=["quote"]).quote(
        f"<html><body>{tampered}</body></html>"))
    page.wait_for_timeout(250)
    d = page.evaluate(actions.SNAPSHOT_JS)
    assert d["interactive_elements"] == []
    assert d.get("unmeasurable", 0) >= 2, (
        "a page-wide tampering is indistinguishable from a page with no "
        f"controls, which is the defect this counter exists to remove: {d}")
