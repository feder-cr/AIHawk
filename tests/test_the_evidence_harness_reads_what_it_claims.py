"""The measurement half of `scripts/orca_evidence.py`, on pictures it can judge.

⛔ WHAT IS TESTED HERE IS THE READING, NOT THE TAKING. The screenshots come from
a real browser against a real server and need a live key, so they are produced
by the script during delivery verification rather than by the suite. What can be
held on every run is the part that DECIDES: whether a rectangle of pixels shows
an opaque surface with a visible edge, where the popup's edge is, and whether
two frames differ at all. Those are the answers the evidence manifest is built
from, and a reader that is wrong makes every picture say whatever it likes.

The fixtures are tiny PNGs written here, so the reader is exercised on known
input rather than on whatever a browser happened to draw.
"""
from __future__ import annotations

import importlib.util
import pathlib
import struct
import zlib

REPO = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "orca_evidence", REPO / "scripts" / "orca_evidence.py")
orca_evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orca_evidence)


def write_png(path, width, height, pixel):
    """A PNG of one colour, or of whatever `pixel(x, y)` answers."""
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # filter: none
        for x in range(width):
            rows.extend(pixel(x, y))
    def chunk(kind, body):
        return (struct.pack(">I", len(body)) + kind + body
                + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))
    header = struct.pack(">IIBB", width, height, 8, 2)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                     + chunk(b"IDAT", zlib.compress(bytes(rows)))
                     + chunk(b"IEND", b""))
    return path


def test_two_identical_frames_differ_nowhere(tmp_path):
    """A page that did not change must report no change, or every measurement
    below is taken against a rectangle invented by the reader."""
    a = write_png(tmp_path / "a.png", 40, 20, lambda x, y: (10, 10, 10))
    b = write_png(tmp_path / "b.png", 40, 20, lambda x, y: (10, 10, 10))
    assert orca_evidence.changed_box(a, b) is None


def test_a_painted_rectangle_is_reported_exactly(tmp_path):
    """Where the ink appeared is the popup's own edge, so the rectangle has to
    be the painted one and not one pixel of slack either side."""
    a = write_png(tmp_path / "a.png", 40, 20, lambda x, y: (10, 10, 10))
    b = write_png(tmp_path / "b.png", 40, 20,
                  lambda x, y: (200, 200, 200) if 5 <= x < 15 and 4 <= y < 9
                  else (10, 10, 10))
    assert orca_evidence.changed_box(a, b) == {
        "left": 5, "top": 4, "right": 15, "bottom": 9}


def test_an_opaque_surface_with_a_visible_edge_is_read_as_one(tmp_path):
    """The two fields the evidence manifest is required to assert: a drawn
    background and a border that is not the background."""
    def drawn(x, y):
        if y == 0:
            return (133, 133, 133)      # the border row
        return (23, 27, 33) if not (y == 8 and x % 7 == 0) else (223, 228, 232)

    shot = write_png(tmp_path / "drawn.png", 60, 20, drawn)
    got = orca_evidence.popup_paint(shot, {"left": 0, "top": 0,
                                           "right": 60, "bottom": 20}, 3)
    assert got["opaque_background"] is True
    assert got["visible_border"] is True
    assert got["surface"] == [23, 27, 33]


def test_a_see_through_popup_is_not_called_opaque(tmp_path):
    """⛔ THE CASE THE ASSERTION EXISTS FOR. A popup with no background carries
    the page underneath it, so no single colour dominates - and calling that
    opaque would let a transparent rectangle pass as a drawn one."""
    shot = write_png(tmp_path / "through.png", 60, 20,
                     lambda x, y: ((x * 7) % 256, (y * 11) % 256, (x + y) % 256))
    got = orca_evidence.popup_paint(shot, {"left": 0, "top": 0,
                                           "right": 60, "bottom": 20}, 3)
    assert got["opaque_background"] is False


def test_a_surface_with_no_border_is_not_called_bordered(tmp_path):
    """A single flat colour edge to edge is a surface with no edge drawn: the
    border row is the same colour as everything under it."""
    shot = write_png(tmp_path / "flat.png", 60, 20, lambda x, y: (23, 27, 33))
    got = orca_evidence.popup_paint(shot, {"left": 0, "top": 0,
                                           "right": 60, "bottom": 20}, 3)
    assert got["visible_border"] is False


def test_a_key_shaped_run_is_redacted_out_of_a_written_sentence():
    """⛔ A WRITTEN ARTIFACT CARRIES NO PART OF A KEY. The mask the product draws
    is a fact about that key; the characters are not, and the manifest is a file
    that gets published."""
    line = "Using sk-orca-abcdef123456...(29 characters) (api_key, from pasted)."
    redacted = orca_evidence._redact(line)
    assert "abcdef123456" not in redacted
    assert "sk-orca-<redacted>" in redacted
    assert "(29 characters)" in redacted, "the shape is the evidence and it stays"


def test_the_catalog_url_the_evidence_claims_is_the_authoritative_one():
    """The manifest's `catalog_source` is checked by the delivery validator
    against one exact string; it is written here once so it cannot drift."""
    assert orca_evidence.CATALOG_URL == \
        "https://api.orcarouter.ai/v1/models?capability=chat"


def test_the_script_is_the_one_the_manifest_is_built_from():
    """The harness is reached by path rather than imported as a package, so this
    holds the two together: the file that exists is the file that was loaded."""
    assert pathlib.Path(orca_evidence.__file__).resolve() == \
        (REPO / "scripts" / "orca_evidence.py").resolve()
    assert callable(orca_evidence.main)
    assert orca_evidence.MIN_WIDTH >= 800 and orca_evidence.MIN_HEIGHT >= 450
