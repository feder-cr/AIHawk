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
    """The point of the split, and it holds for every piece.

    A stylesheet in a `.css` file is a stylesheet; the same bytes in a Python
    literal are a string that no editor, formatter or diff understands. The
    same goes one level down: a script cut into ten files is ten scripts only
    if none of them carries markup or rules.

    ⛔ AND IT STRIPS THE COMMENTS FIRST. The first version asserted that the
    script contains no `<script>` and was accused by the comment explaining why
    a script inside an ANSWER is drawn as text - the gate-accused-by-a-comment
    defect this project has recorded more than any other, committed by the gate
    that was meant to be careful about it.

    Known-bad: put a rule in a script file, or markup in either.
    """
    def strip_css(s):
        return re.sub(r"/\*.*?\*/", "", s, flags=re.S)

    def strip_js(s):
        # Two passes, and the line comments without a newline escape: `.` does
        # not cross a line without DOTALL, so `.*$` under MULTILINE is exactly
        # "to the end of this line" and needs no backslash-n to say so.
        return re.sub(r"^\s*//.*$", "", strip_css(s), flags=re.M)

    for name in ui.CSS_FILES:
        css = strip_css(ui._read("css", name))
        assert "<style>" not in css and "function " not in css, (
            "%s carries markup or script" % name)
        assert "{" in css, "%s has no rules in it at all" % name

    for name in ui.JS_FILES:
        js = strip_js(ui._read("js", name))
        assert "<script>" not in js, "%s carries its own tag" % name

    html = re.sub(r"<!--.*?-->", "", ui._read("page.html"), flags=re.S)
    assert ui.CSS_AT in html and ui.JS_AT in html, (
        "the markup does not say where the other two go")
    assert html.count("{") < 40, (
        "the markup carries a stylesheet's worth of braces, so the split did "
        "not actually separate anything")


def test_no_piece_is_big_enough_to_hide_in():
    """⛔ THE WHOLE POINT, AND THE ONLY THING THAT CAN QUIETLY COME BACK. The
    stylesheet was 1023 lines of 208 rules and the script 1398 lines of 54
    functions, each covering seven unrelated areas with a comment between them.
    Nothing stops the next change appending to whichever file it lands in until
    one of them is a thousand lines again.

    The ceiling is generous on purpose: this is a floor under the split, not a
    style rule about file length.

    Known-bad: paste two of the pieces back together.
    """
    for folder, names in (("css", ui.CSS_FILES), ("js", ui.JS_FILES)):
        for name in names:
            lines = ui._read(folder, name).count(chr(10))
            assert lines < 400, (
                "%s is %d lines: the split it was made by has been undone"
                % (name, lines))

def test_the_wheel_carries_every_file_the_page_is_made_of():
    """⛔ A WHEEL WITHOUT THEM INSTALLS AND THEN SERVES NOTHING. The assets are
    not Python, so nothing imports them and no test that runs from a checkout
    can notice they were left out of the build.

    ⛔ AND THE LIST COMES FROM THE ORDER, NOT FROM A COPY OF IT. This named the
    two files by hand and went on naming them after the split: it only failed
    when a wheel happened to exist in the checkout, and would have skipped in
    silence anywhere else. A gate that repeats a list has a second list to keep
    in step, which is the defect this project keeps writing down.

    Skipped when there is no wheel to look at; the release workflow builds one
    before this ever matters.
    """
    import pytest

    wheels = sorted((Path(__file__).resolve().parents[1] / "dist").glob("*.whl"))
    if not wheels:
        pytest.skip("no wheel built in this checkout")
    names = set(zipfile.ZipFile(wheels[-1]).namelist())
    wanted = (["aihawk/ui/page.html"]
              + ["aihawk/ui/css/%s" % f for f in ui.CSS_FILES]
              + ["aihawk/ui/js/%s" % f for f in ui.JS_FILES])
    for needed in wanted:
        assert needed in names, (
            "%s is not in the wheel, so an installed copy serves a page with a "
            "piece missing" % needed)


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
