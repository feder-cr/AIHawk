"""No tracked text file carries a control byte, because a corrupted regex does
not fail: it matches nothing, and a gate built on it prints PASS for ever.

⛔ TWICE IN ONE AFTERNOON, 2026-09-12, IN THIS SUITE. A word boundary written
as `\\b` and passed through a shell reached the file as the byte 0x08. The
regex `border-radius:\\s*([\\d]+px)<BS>` then required a backspace after `px`,
found none, and the gate that was supposed to refuse a retyped radius passed
with the retyped radius on disk. A second gate in another file carried two more
of the same byte around a pattern meant to catch a layout number typed back
into the drag code; it was blind from the moment it was written. Both were
found by a known-bad mutation SURVIVING, not by reading the code - `sed` prints
a backspace as nothing at all, so the two files read as correct.

The class is wider than `\\b`: `\\f` becomes a form feed, `\\t` a tab inside a
path, `\\0` a NUL. None of them error. So this reads the BYTES of every text
file git tracks and refuses any control character that is not a tab, a line
feed or a carriage return.

Known-bad: write a 0x08 into any tracked text file.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: What may legitimately appear below 0x20 in a text file.
ALLOWED = {9, 10, 13}

#: Files whose bytes are not text and are not read by any regex here.
BINARY = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".pdf")


def test_no_tracked_text_file_carries_a_control_byte():
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True,
                             check=True).stdout.decode("utf-8").split("\0")
    assert len(tracked) > 50, "found almost nothing tracked, so this is not looking"

    found = []
    for rel in tracked:
        if not rel or rel.endswith(BINARY):
            continue
        path = ROOT / rel
        if not path.is_file():
            continue
        data = path.read_bytes()
        bad = sorted({b for b in data if b < 32 and b not in ALLOWED})
        if bad:
            found.append((rel, [hex(b) for b in bad]))

    assert not found, (
        "%d tracked file(s) carry a control byte, which a regex or a path in "
        "them will read as a character that is never there: %s" % (len(found), found))
