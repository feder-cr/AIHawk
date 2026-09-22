"""Every swallowed exception in the package says why, on the line that swallows
it, and can be heard.

`except Exception: pass` with the reason in a comment is a silence a reader
can skip and a gate cannot see. `swallow(why)` puts the reason in the code
and logs it at debug with the traceback, so a silence hiding a real defect can
be heard by turning the logger up.
"""
import logging
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "invisible_playwright_mcp"


def test_the_silence_lets_the_block_fail_and_says_why_at_debug(caplog):
    """Known-bad, two: re-raise, and every caller's careful reason becomes an
    error; drop the log, and the reason is decoration."""
    from invisible_playwright_mcp.quiet import swallow

    with caplog.at_level(logging.DEBUG, logger="invisible_playwright_mcp"):
        with swallow("a write that fails costs the saved file and nothing else"):
            raise OSError("disk full")
        with swallow("nothing failed here"):
            pass

    said = [r for r in caplog.records if "swallowed" in r.getMessage()]
    assert len(said) == 1, "a block that did not fail was logged, or one that did was not"
    assert "costs the saved file" in said[0].getMessage()
    assert said[0].exc_info and said[0].exc_info[0] is OSError, (
        "the traceback is not attached, so the silence cannot be heard")


def test_no_exception_is_swallowed_without_a_reason_in_the_code():
    """⛔ THE SHAPE, NOT THE COMMENT. A comment beside a `pass` is skipped by a
    reader and invisible to a gate, which is why this reads for the bare form
    - `except Exception:` followed, comments aside, by `pass` - and refuses it
    anywhere in the package.

    Known-bad: put one back, with a perfectly good comment above the `pass`.
    """
    bare = re.compile(r"except Exception(?: as \w+)?:\s*\n(?:[ \t]*#[^\n]*\n)*[ \t]*pass\b")
    found = []
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_bytes().decode("utf-8")
        for m in bare.finditer(text):
            found.append("%s:%d" % (path.relative_to(SRC), text[:m.start()].count("\n") + 1))
    assert not found, (
        "these swallow an exception with the reason, if any, in a comment: %s"
        % found)

    uses = sum(path.read_bytes().decode("utf-8").count("with swallow(")
               for path in SRC.rglob("*.py"))
    assert uses >= 10, (
        "only %d places say why they swallow; the package had thirteen bare "
        "silences on 2026-09-14, so the shape above has stopped being looked "
        "for" % uses)
