"""The interface, as three files in the languages they are written in.

⛔ IT WAS ONE STRING IN A PYTHON MODULE, AND THAT IS WHY THIS EXISTS. 1023 lines
of CSS, 1399 of JavaScript and 165 of markup lived inside one raw triple-quoted
literal in `web.py`, which made the module 3370 lines and meant no editor,
linter or diff ever saw any of it as what it was. A stylesheet in a `.css` file
is a stylesheet; the same bytes in a Python literal are a string.

⛔ AND THE ASSEMBLY IS BYTE FOR BYTE, WHICH IS THE WHOLE SAFETY OF THE MOVE. The
page a browser receives is exactly the string that used to be typed here - it
was checked against the old bytes, not argued about - so the dozens of gates
that read `PAGE` as text kept passing untouched, and nothing on the screen could
have moved. A refactor whose output differs by one character is not a refactor.

The two sentinels are comments in their own languages, so `page.html` stays a
file a browser can open. They are `str.replace`d and not `str.format`ed: a
format string would treat all 223 rules' braces as fields.
"""
from __future__ import annotations

from pathlib import Path

_HERE = Path(__file__).parent

#: Where the stylesheet and the script go back into the markup.
CSS_AT = "/*__CSS__*/"
JS_AT = "//__JS__"


def _read(name: str) -> str:
    """One file, as UTF-8 with LF endings whatever the checkout did.

    ⛔ AND THE NORMALISING IS LOAD-BEARING, not tidiness. Python reads its own
    source with universal newlines, so the literal these files came out of held
    LF even in a CRLF file - and the extraction, byte for byte, produced CRLF
    files that assembled a page 2592 characters longer than the one it replaced,
    one per line. `read_text` would have hidden that on this machine and shown
    it on a runner; reading bytes and folding the endings here means the page is
    the same on every checkout, whatever `core.autocrlf` decided.
    """
    return lf(_HERE.joinpath(name).read_bytes().decode("utf-8"))


def lf(text: str) -> str:
    """CRLF folded to LF, as its own function so it can be shown to work.

    ⛔ A GATE THAT READS THESE FILES CANNOT PROVE THIS. On a checkout where they
    are already LF, removing the fold changes nothing and the assertion passes
    on a broken reader - measured: that mutation survived. The fold has to be
    exercised on input that HAS carriage returns, which means a function that
    takes a string rather than a filename.
    """
    return text.replace(chr(13) + chr(10), chr(10))


def build_page() -> str:
    """The whole page, assembled once at import."""
    html = _read("page.html")
    return html.replace(CSS_AT, _read("app.css"), 1).replace(JS_AT, _read("app.js"), 1)


PAGE = build_page()
