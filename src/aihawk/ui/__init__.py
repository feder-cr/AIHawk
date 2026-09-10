"""The interface, as the files it is actually written in.

⛔ IT WAS ONE STRING IN A PYTHON MODULE, AND THEN TWO ENORMOUS FILES. First the
three languages came out of the literal in `web.py`; that left a 1023-line
stylesheet of 208 rules and a 1398-line script of 54 functions, each covering
seven unrelated areas with nothing but a comment between them. Those comments
were where the cuts went: the split follows the structure the code always had
rather than one invented for it.

⛔ AND THE ASSEMBLY IS BYTE FOR BYTE, WHICH IS THE WHOLE SAFETY OF BOTH MOVES.
595 assertions across fifteen gate files read this page as text, dozens of them
pinning exact strings of stylesheet and script - whole function signatures,
whole expressions, selectors. A restructuring that reworded any of that would
invalidate them wholesale, and rewriting the gates to match is how a suite stops
being evidence. Concatenation in a declared order changes no character, so every
one of those assertions still means what it meant.

⛔ THE ORDER IS DECLARED AND IT IS LOAD-BEARING. The script is one `<script>`
with top-level bindings, so a file that ran before its dependencies would break
the page in the way this project has recorded twice: an error at the top level
kills the whole file and the document still draws, so the suite stays green and
the page is dead. The lists below are the order the single file had.
"""
from __future__ import annotations

from pathlib import Path

_HERE = Path(__file__).parent

#: Where the stylesheet and the script go back into the markup.
CSS_AT = "/*__CSS__*/"
JS_AT = "//__JS__"

#: The stylesheet, in cascade order. Later files may override earlier ones and
#: two of them rely on it: the narrow layout must follow the layout it
#: overrides, and the shared control rule must follow the tokens it names.
CSS_FILES = (
    "01-tokens.css",       # the palette, the type scale, the spacing base
    "02-sessions.css",     # the rail and the drawer it opens
    "03-shell.css",        # the two panes, the separator, the headers
    "04-transcript.css",   # turns, steps, answers, rendered markdown
    "05-composer.css",     # the box you type in
    "06-browser.css",      # the browser bar and the live picture
    "07-fleet.css",        # the strip of browsers along the bottom
    "08-stage.css",        # one screen, or two, or four
)

#: The script, in execution order.
JS_FILES = (
    "01-markdown.js",      # the renderer for an answer
    "02-transcript.js",    # turns, steps, the queued message
    "03-which-session.js", # which conversation this page is in
    "04-composer.js",      # sending, the event stream, one door for requests
    "05-browser.js",       # the live pane: frames, address, tabs, state
    "06-sessions.js",      # the column of conversations
    "07-rail.js",          # opening and closing that column
    "08-workspace.js",     # which browsers this session holds
    "09-stage.js",         # the screens and the strip
    "10-splitter.js",      # the separator between the panes
)


def lf(text: str) -> str:
    """CRLF folded to LF, as its own function so it can be shown to work.

    ⛔ A GATE THAT READS THESE FILES CANNOT PROVE THIS. On a checkout where they
    are already LF, removing the fold changes nothing and the assertion passes
    on a broken reader - measured: that mutation survived. The fold has to be
    exercised on input that HAS carriage returns, which means a function that
    takes a string rather than a filename.

    It is load-bearing rather than tidiness. Python reads its own source with
    universal newlines and a file is read as it is, so extracting the original
    literal byte for byte produced CRLF files whose page was 2592 characters
    longer than the one it replaced, one per line.
    """
    return text.replace(chr(13) + chr(10), chr(10))


def _read(*parts: str) -> str:
    """One file, as UTF-8 with LF endings whatever the checkout did."""
    return lf(_HERE.joinpath(*parts).read_bytes().decode("utf-8"))


def _join(folder: str, names: tuple[str, ...]) -> str:
    """The pieces, in the order given. Nothing between them: the cuts were made
    on character boundaries, so a separator here would be a character the
    original did not have."""
    return "".join(_read(folder, name) for name in names)


def build_page() -> str:
    """The whole page, assembled once at import."""
    html = _read("page.html")
    return (html
            .replace(CSS_AT, _join("css", CSS_FILES), 1)
            .replace(JS_AT, _join("js", JS_FILES), 1))


PAGE = build_page()
