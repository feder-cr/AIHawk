"""The interface lives in three files, and comes back out as one page.

⛔ THE ONLY REASON THIS SPLIT WAS SAFE is that the page it produces is the same
string it replaced, byte for byte. Everything else in this suite reads `PAGE` as
text and asserts on literal pieces of stylesheet and script: if the assembly
were even one character different, dozens of gates would be checking a page
nobody serves.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

from aihawk import ui
from aihawk.web import PAGE

ASSETS = Path(ui.__file__).parent


def test_the_page_the_module_exports_is_the_page_the_files_assemble():
    """`web.PAGE` is what every route serves and what every gate reads. It has
    to be the assembly, not a copy that can drift from it.

    Known-bad: give `web.py` a `PAGE` of its own again.
    """
    assert PAGE is ui.PAGE, (
        "the module exports a different object from the one the files build, so "
        "the two can disagree without anything saying so")
    assert PAGE == ui.build_page(), (
        "assembling twice gives two different pages")


def test_nothing_is_left_unresolved_in_the_page():
    """⛔ A MISSING FILE OR A RENAMED SENTINEL SHIPS A PAGE WITH A COMMENT WHERE
    ITS STYLESHEET SHOULD BE, and a browser draws that without complaining: an
    unknown CSS comment is simply not a rule. The failure is a page with no
    styling at all and nothing in any log.

    Known-bad: rename one sentinel in `page.html` and not in the module.
    """
    for sentinel in (ui.CSS_AT, ui.JS_AT):
        assert sentinel not in PAGE, (
            "%s survived into the page, so the file it stands for was never put "
            "in" % sentinel)
    assert "<style>" in PAGE and "</style>" in PAGE, "the page lost its stylesheet"
    assert "<script>" in PAGE and "</script>" in PAGE, "the page lost its script"
    # And the two really were filled: a page with empty tags would pass the line
    # above and be just as broken.
    css = PAGE[PAGE.index("<style>"):PAGE.index("</style>")]
    js = PAGE[PAGE.index("<script>"):PAGE.index("</script>")]
    assert css.count("{") > 100, "the stylesheet is empty or nearly so"
    assert "function" in js, "the script is empty"


def test_each_file_is_written_in_its_own_language():
    """The point of the split. A stylesheet in a `.css` file is a stylesheet;
    the same bytes in a Python literal are a string that no editor, formatter or
    diff understands.

    ⛔ AND IT STRIPS THE COMMENTS FIRST. The first version of this asserted that
    `app.js` contains no `<script>` and was accused by the comment explaining
    why a script inside an ANSWER is drawn as text - the gate-accused-by-a-
    comment defect this project has recorded more than any other, committed here
    by the gate that was meant to be careful about it.

    Known-bad: put the script back inside the markup.
    """
    strip = lambda s: re.sub(r"/\*.*?\*/|^\s*//[^\n]*", "", s, flags=re.S | re.M)
    css = strip((ASSETS / "app.css").read_bytes().decode("utf-8"))
    js = strip((ASSETS / "app.js").read_bytes().decode("utf-8"))
    html = re.sub(r"<!--.*?-->", "", (ASSETS / "page.html").read_bytes().decode("utf-8"),
                  flags=re.S)

    assert "<style>" not in css and "function " not in css, (
        "the stylesheet carries markup or script")
    assert "<script>" not in js, "the script carries its own tag"
    assert ui.CSS_AT in html and ui.JS_AT in html, (
        "the markup does not say where the other two go")
    assert html.count("{") < 40, (
        "the markup carries a stylesheet's worth of braces, so the split did "
        "not actually separate anything")


def test_the_wheel_carries_the_three_files():
    """⛔ A WHEEL WITHOUT THEM INSTALLS AND THEN SERVES NOTHING. The assets are
    not Python, so nothing imports them and no test that runs from a checkout
    can notice they were left out of the build.

    Skipped when there is no wheel to look at; the release workflow builds one
    before this ever matters.
    """
    import pytest

    wheels = sorted((Path(__file__).resolve().parents[1] / "dist").glob("*.whl"))
    if not wheels:
        pytest.skip("no wheel built in this checkout")
    names = set(zipfile.ZipFile(wheels[-1]).namelist())
    for needed in ("aihawk/ui/app.css", "aihawk/ui/app.js", "aihawk/ui/page.html"):
        assert needed in names, (
            "%s is not in the wheel, so an installed copy serves an unstyled "
            "page" % needed)


def test_the_assembly_does_not_depend_on_how_the_files_were_checked_out():
    """⛔ PYTHON READS ITS OWN SOURCE WITH UNIVERSAL NEWLINES AND A FILE IS READ
    AS IT IS. The literal these files came out of held LF even in a CRLF module,
    so extracting it byte for byte produced CRLF files whose page was 2592
    characters longer than the one it replaced - one per line. It would have
    passed on a checkout with LF and failed on Windows, or the other way round.

    ⛔ AND IT IS EXERCISED ON INPUT THAT HAS THEM. The first version of this
    read the three files and asserted no carriage returns came back, which on a
    checkout where they are already LF passes on a reader that folds nothing -
    measured, that mutation survived. So the fold is its own function and it is
    given a string with the endings the checkout might have had.

    Known-bad: drop the fold in `ui.lf`.
    """
    CR, LF = chr(13), chr(10)
    assert ui.lf("a" + CR + LF + "b") == "a" + LF + "b", (
        "the reader hands carriage returns to the page")
    assert ui.lf("a" + LF + "b") == "a" + LF + "b", "the reader mangles LF input"
    assert CR not in PAGE, "the page carries carriage returns"
