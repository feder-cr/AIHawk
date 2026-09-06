"""The cleaner keeps everything a caller can act on.

Every test below is a defect that was measured on real pages, not a defect that
was imagined. They are grouped by the thing that went wrong, because each one
went wrong for a different reason and only one of them looked like a bug at the
time - the other four all shipped a plausible number.
"""

import pytest

from invisible_playwright_mcp import clean
from selectolax.lexbor import LexborHTMLParser


def interactive(html):
    """The interactive elements, COUNTED.

    A set was used here first, and it hid the defect it was written to find: two
    identical buttons collapse into one entry, so a page could lose 46 elements
    and still report the same total. Counting is the whole difference between
    "no loss" and "28% loss" on the page that measured it.
    """
    out = []
    for n in LexborHTMLParser(html).css(clean.INTERACTIVE_CSS):
        if clean.is_interactive(n):
            out.append((n.tag, n.attributes.get("id") or "", n.attributes.get("name") or ""))
    return out


# --- the invariant ---------------------------------------------------------

def test_no_interactive_element_is_ever_removed():
    html = """
    <html><body>
      <nav><a href="/a">A</a><a href="/b">B</a></nav>
      <form><label for="e">Email</label><input id="e" name="email" required>
        <div onclick="go()">fake button</div>
        <span role="button" tabindex="0">another</span>
        <button type="submit">Send</button></form>
      <footer><a href="/privacy">Privacy</a></footer>
    </body></html>"""
    before, after = interactive(html), interactive(clean.clean_page(html, "form"))
    assert len(after) == len(before), f"lost {len(before) - len(after)} interactive elements"


def test_duplicate_controls_all_survive():
    """Ten identical "Add" buttons are ten places to click, not one repeated."""
    rows = "".join('<li><span>Item</span><button>Add</button></li>' for _ in range(10))
    html = f"<html><body><ul>{rows}</ul></body></html>"
    assert len(interactive(clean.clean_page(html, "form"))) == 10


# --- the five measured defects ---------------------------------------------

def test_the_attributes_that_confer_interactivity_survive_slimming():
    """The worst one. Stripping `onclick` does not hide an element, it makes it
    unrecognisable and unreachable - and the cleaner then measured
    interactivity after removing the evidence of it. 46 elements on one real
    page, 117 on another."""
    html = ('<html><body><div onclick="f()">x</div>'
            '<span tabindex="0">y</span>'
            '<p contenteditable="true">z</p></body></html>')
    assert len(interactive(html)) == 3
    assert len(interactive(clean.clean_page(html, "form"))) == 3


def test_an_inline_handler_keeps_its_presence_but_not_its_body():
    html = '<html><body><div onclick="' + "doSomething();" * 200 + '">x</div></body></html>'
    out = clean.clean_page(html, "form")
    assert "onclick" in out
    assert "doSomething" not in out
    assert len(interactive(out)) == 1


def test_links_inside_svg_survive():
    """SVG is a document format, not a picture. On one corpus page 105
    interactive elements lived inside svg, and dropping svg wholesale took
    every one of them."""
    html = ('<html><body><svg viewBox="0 0 10 10"><path d="M0 0 L9 9"/>'
            '<a href="/inside"><rect width="4" height="4"/></a></svg></body></html>')
    out = clean.clean_page(html, "form")
    assert "/inside" in out, "a link inside svg was destroyed with the icon"
    assert "M0 0 L9 9" not in out, "the drawing geometry should not survive"


def test_aria_hidden_text_is_not_treated_as_invisible():
    """`aria-hidden` means "do not announce", not "do not paint". A link that
    carries its own aria-label routinely marks its VISIBLE caption aria-hidden
    so it is not read twice; deleting it left the link with no name at all."""
    html = ('<html><body><a href="/orders" aria-label="Orders and returns">'
            '<div aria-hidden="true">Orders &amp; Returns</div></a></body></html>')
    out = clean.clean_page(html, "form")
    assert "Orders" in out, "the only visible label on the link was deleted"


def test_a_missing_contenteditable_does_not_make_an_element_interactive():
    """`contenteditable=""` means editable, so the obvious test - value in
    ("", "true") - accepts every element that lacks the attribute entirely,
    because a missing attribute also reads back as "". That made
    `is_interactive` answer True for decorative role=presentation icons."""
    html = '<html><body><svg role="presentation" aria-hidden="true"></svg><p>text</p></body></html>'
    assert interactive(html) == []


def test_display_none_is_still_removed():
    """The correction above must not turn into "nothing is ever hidden"."""
    html = ('<html><body><div style="display:none"><p>gone</p></div>'
            '<p>kept</p></body></html>')
    out = clean.clean_page(html, "form")
    assert "gone" not in out and "kept" in out


# --- choices ---------------------------------------------------------------

def test_a_long_select_reports_its_size_instead_of_a_sample():
    """All of them or none of them, never three of two hundred. Showing a
    sample does not compress the answer, it replaces it with a wrong one: it
    tells the model the choices are those three."""
    options = "".join(f'<option value="{i}">Country {i}</option>' for i in range(200))
    html = f'<html><body><select name="country">{options}</select></body></html>'
    out = clean.clean_page(html, "form")
    assert "Country 7" not in out
    assert 'data-option-count="200"' in out
    assert 'name="country"' in out


def test_a_short_select_keeps_every_option():
    html = ('<html><body><select name="size">'
            '<option>S</option><option>M</option><option>L</option>'
            "</select></body></html>")
    out = clean.clean_page(html, "form")
    for size in ("S", "M", "L"):
        assert f">{size}<" in out


# --- modes -----------------------------------------------------------------

def test_text_mode_does_not_destroy_the_article():
    """The structure this replaces compressed long prose blocks BEFORE the mode
    split, so text mode returned a placeholder where its own article had been -
    the one thing that mode exists to produce."""
    body = "This is a real paragraph of content. " * 40
    html = f"<html><body><article><p>{body}</p></article></body></html>"
    out = clean.clean_page(html, "text")
    assert len(out) > 1000
    assert "real paragraph" in out
    assert "<p" not in out


def test_text_mode_separates_blocks():
    html = "<html><body><p>one</p><p>two</p><li>three</li></body></html>"
    out = clean.clean_page(html, "text")
    assert out.count("\n") >= 2


def test_empty_input_is_empty_output():
    assert clean.clean_page("", "form") == ""
    assert clean.clean_page("   ", "text") == ""


# --- failure ---------------------------------------------------------------

def test_an_unknown_mode_raises_instead_of_guessing():
    with pytest.raises(clean.CleanError):
        clean.clean_page("<p>x</p>", "whatever")


def test_failure_does_not_return_the_input_unchanged():
    """The obvious fallback hands back a payload two orders of magnitude larger
    than the caller asked for and says nothing about it. A failure wearing the
    costume of a success is worse than a failure."""
    import inspect
    src = inspect.getsource(clean.clean_page)
    assert "return html" not in src, "the cleaner silently returns its input on error"


# --- weight ----------------------------------------------------------------

def test_the_noise_actually_goes():
    html = ("<html><head><script>var x=" + "1;" * 5000 + "</script>"
            "<style>" + ".a{color:red}" * 500 + "</style></head>"
            '<body><div class="mt-4 px-2 flex items-center">'
            '<button id="go">Go</button></div></body></html>')
    out = clean.clean_page(html, "form")
    assert len(out) < len(html) / 10
    assert "var x" not in out and "color:red" not in out
    assert "mt-4" not in out, "framework class soup survived"
    assert 'id="go"' in out


def test_a_state_class_is_rescued_before_class_is_dropped():
    html = ('<html><body><input name="e" class="mt-4 px-2 form-error-message">'
            "</body></html>")
    out = clean.clean_page(html, "form")
    assert "mt-4" not in out
    assert "error" in out, "the state encoded in the class was thrown away with the layout"


def test_a_data_uri_does_not_survive_at_full_length():
    html = '<html><body><a href="/x"><img alt="a" src="data:image/png;base64,' + "A" * 50_000 + '"></a></body></html>'
    out = clean.clean_page(html, "form")
    assert len(out) < 1000
    assert "/x" in out


def test_a_tracking_query_is_trimmed_but_the_destination_is_not():
    long_q = "&".join(f"utm_{i}=value{i}" for i in range(60))
    html = f'<html><body><a href="/product/12345?{long_q}">Buy</a></body></html>'
    out = clean.clean_page(html, "form")
    assert "/product/12345" in out
    assert "utm_40" not in out


def test_stats_report_both_halves():
    """A reduction figure alone says nothing about whether the result is still
    usable. The most attractive -13% of that day cost 8.1% of the elements."""
    s = clean.clean_stats("x" * 1000, "x" * 250)
    assert s["reduction_pct"] == 75.0
    assert s["chars_removed"] == 750
    assert s["tokens_saved_est"] == 187


# --- the live-page half ----------------------------------------------------

def test_the_live_page_pass_never_writes_to_the_page():
    """It clones, and every removal lands on the detached copy. Mutating the
    live DOM would create the detection surface this product exists not to
    have."""
    js = clean.VISIBLE_HTML_JS
    assert "cloneNode(true)" in js
    for write in ("setAttribute", "document.documentElement.removeChild",
                  "dataset.", "innerHTML ="):
        assert write not in js, f"the live-page pass writes to the page: {write}"
    assert js.index("cloneNode") < js.index("removeChild")


def test_unwrapping_keeps_the_words_it_unwraps():
    """selectolax has two methods a line apart in meaning: `strip_tags` deletes
    the tag WITH its contents, `unwrap_tags` keeps the children. Using the first
    where the second was meant deleted the text inside every <b>, <em> and
    <strong> on the page, and no element count could see it - a word is not an
    element."""
    html = "<html><body><p>plain <b>bold</b> and <em>italic</em> words</p></body></html>"
    out = clean.clean_page(html, "text")
    for word in ("plain", "bold", "italic", "words"):
        assert word in out, f"unwrapping ate {word!r}"


def test_a_repeated_option_label_does_not_survive_the_collapse():
    """selectolax compares nodes by CONTENT, so `opt not in selected` kept every
    option sharing text with a selected one. Asking each option whether IT is
    selected has no such failure mode."""
    dups = "".join("<option>X</option>" for _ in range(40))
    html = f'<html><body><select name="q">{dups}<option selected>X</option></select></body></html>'
    out = clean.clean_page(html, "form")
    assert out.count("<option") == 1, "a non-selected option survived by sharing text"
    assert 'data-option-count="41"' in out


def test_full_mode_keeps_the_prose_that_form_mode_prunes():
    """Three modes, three answers. `full` is the one for reading structure AND
    content, so the pruning that makes `form` small must not reach it."""
    html = ("<html><body><article><p>" + "Long prose with no controls at all. " * 30
            + "</p></article><button>Go</button></body></html>")
    assert "Long prose" in clean.clean_page(html, "full")
    assert "Long prose" not in clean.clean_page(html, "form")


def test_wrappers_that_say_nothing_are_collapsed():
    """Found by an edge case, not by reading: 500 nested `<div>` around one
    button survived as 5,560 characters, because every ancestor of an
    interactive element is kept and nothing asked whether the ancestor said
    anything."""
    html = "<html><body>" + "<div>" * 200 + "<button>deep</button>" + "</div>" * 200 + "</body></html>"
    out = clean.clean_page(html, "form")
    assert len(out) < 200, f"the empty wrappers survived: {len(out)} chars"
    assert "<button>deep</button>" in out


def test_a_wrapper_carrying_state_is_left_alone():
    """The condition has to stay narrow, or this becomes another way of losing
    things. An element still carrying an attribute after slimming is carrying
    something worth carrying."""
    html = ('<html><body><div class="field-error"><span><input name="e"></span>'
            "</div></body></html>")
    out = clean.clean_page(html, "form")
    assert "error" in out, "the wrapper that said the field is in error was collapsed"


def test_a_wrapper_with_its_own_text_is_left_alone():
    html = '<html><body><div>Label here<span><input name="e"></span></div></body></html>'
    assert "Label here" in clean.clean_page(html, "form")


def test_the_package_version_is_derived_not_typed():
    """It said "0.1.0" through four releases, because a hand-written literal is
    a second place the version lives and the second place is the one nobody
    moves. No test could see it: every test imports the checkout, where the
    number is whatever the file says. Installing the built wheel into an empty
    environment and asking the package is what found it."""
    import inspect

    import invisible_playwright_mcp as pkg
    src = inspect.getsource(pkg)
    assert "importlib.metadata" in src, "the version is hand-written again"
    import re
    assert not re.search(r'__version__\s*=\s*"\d+\.\d+', src), "a version literal is back"
