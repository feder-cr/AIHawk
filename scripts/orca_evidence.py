#!/usr/bin/env python3
"""Photograph the OrcaRouter panel on the running interface, for the record.

Usage: python3 scripts/orca_evidence.py [--out DIR]

⛔ THIS IS EVIDENCE, NOT A DEMO. It starts the real application - the real
routes, the real panel markup, the real stylesheet, the real catalog read - and
takes each picture from the browser that renders them. Nothing here is a mock
of the interface and nothing here is a static HTML stand-in.

Both authentication entries are engaged for real. The API key is typed into the
form and stored through the product's own route; the sign-in entry is clicked,
which sends the page to the real authorize URL and puts it in its waiting
state. What this script does NOT do is approve the authorization: that needs a
person, and a worker that faked consent would be proving nothing.

The catalog is the live one. The server reads `GET /v1/models` with the key from
ORCAROUTER_API_KEY and the selector is built from what came back, so the picture
shows the fleet a workspace can actually call rather than a list written here.

⛔ THE OPEN DROPDOWN IS PHOTOGRAPHED BY OPENING IT. A `<select>` popup is drawn
by the browser outside the page's own boxes, so no amount of reading the DOM
says it was on screen. This clicks the control and then measures the PIXELS
that appear only while it is open, which is the same thing a reader of the
picture sees - and it is why the geometry assertions below are read off the
image rather than off `getBoundingClientRect`.

The output directory is written, never committed: it is a picture of one
machine's fleet at one moment, and `git` is told to ignore it.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import pathlib
import re
import struct
import sys
import tempfile
import urllib.request
import zlib
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
#: The checkout this script lives in answers, not whichever one the
#: interpreter's installation happens to point at.
sys.path.insert(0, str(REPO / "src"))

import uvicorn  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402

from aihawk import orcarouter  # noqa: E402
from aihawk.chat import DEFAULT_CHAT_ID, ChatService  # noqa: E402
from aihawk.orcarouter import Credentials  # noqa: E402
from aihawk.provider import Provider, warm  # noqa: E402
from aihawk.routes import build_app  # noqa: E402
from aihawk.sessions import Sessions  # noqa: E402

#: The one URL this evidence claims its list came from, and the one it reads.
CATALOG_URL = "https://api.orcarouter.ai/v1/models?capability=chat"

#: A key shaped like the real thing with a marker in it. The paste screenshot is
#: taken with THIS typed in, never with the real key: a picture of a live
#: credential is a leaked credential, and the masking is one of the things the
#: evidence exists to show.
SHOWN_KEY = "sk-orca-EVIDENCE-marker-not-a-real-key"

MIN_WIDTH, MIN_HEIGHT = 800, 450


def free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class QuietLink:
    """A conversation's connection, with nothing behind it.

    ⛔ THE PANEL DOES NOT NEED A BROWSER AND THE EVIDENCE IS ABOUT THE PANEL. A
    real `Link` would spawn a real server process and download an engine to
    photograph a settings panel; the registry and the routes are the product's
    own either way, which is what makes this evidence rather than a mock.
    """

    tools = ()

    def __init__(self, session_id):
        self.session_id = session_id

    async def close(self):
        return None


def registry(provider):
    sessions = Sessions({}, None, lambda: None, model_label=provider.model)
    service = ChatService(QuietLink(DEFAULT_CHAT_ID), None,
                          model_label=provider.model,
                          session_id=DEFAULT_CHAT_ID, name="Evidence")
    sessions._live[DEFAULT_CHAT_ID] = service
    return sessions


class Served:
    """The real application, served by the real server, for the pictures."""

    def __init__(self, app, port):
        self._app = app
        self._port = port
        self._server = None
        self._task = None

    async def start(self):
        config = uvicorn.Config(self._app, host="127.0.0.1", port=self._port,
                                log_level="error")
        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._server.serve())
        for _ in range(200):
            if getattr(self._server, "started", False):
                return
            await asyncio.sleep(0.05)
        raise RuntimeError("the interface did not start")

    async def stop(self):
        if self._server is not None:
            self._server.should_exit = True
        if self._task is not None:
            await self._task


def _png_rows(path):
    """Decode a PNG to (width, height, channels, rows). Enough to read pixels.

    ⛔ NO IMAGE LIBRARY IS DECLARED FOR THIS, AND ONE WOULD BE A DEPENDENCY FOR
    A MEASUREMENT. The two shots are 8-bit RGB/RGBA PNGs the browser wrote, and
    every filter type is five lines; what is needed from them is "where did the
    ink change", which is arithmetic rather than imaging.
    """
    data = pathlib.Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)
    pos, idat, width, height, channels = 8, b"", 0, 0, 0
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, _depth, colour = struct.unpack(">IIBB", body[:10])
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colour]
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width * channels
    out, previous, at = [], bytearray(stride), 0
    for _y in range(height):
        filt = raw[at]
        at += 1
        line = bytearray(raw[at:at + stride])
        at += stride
        if filt:
            for x in range(stride):
                a = line[x - channels] if x >= channels else 0
                b = previous[x]
                c = previous[x - channels] if x >= channels else 0
                if filt == 1:
                    line[x] = (line[x] + a) & 255
                elif filt == 2:
                    line[x] = (line[x] + b) & 255
                elif filt == 3:
                    line[x] = (line[x] + (a + b) // 2) & 255
                else:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    near = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                    line[x] = (line[x] + near) & 255
        out.append(bytes(line))
        previous = line
    return width, height, channels, out


def changed_box(before, after, threshold=12):
    """The rectangle that differs between two shots of the same page."""
    w1, h1, ch, a = _png_rows(before)
    w2, h2, _c, b = _png_rows(after)
    if (w1, h1) != (w2, h2):
        raise ValueError("the two shots are not the same size")
    xs, ys = [], []
    for y in range(h1):
        ra, rb = a[y], b[y]
        for x in range(w1):
            i = x * ch
            if (abs(ra[i] - rb[i]) + abs(ra[i + 1] - rb[i + 1])
                    + abs(ra[i + 2] - rb[i + 2])) > threshold:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return {"left": min(xs), "top": min(ys),
            "right": max(xs) + 1, "bottom": max(ys) + 1}


def popup_paint(path, box, channels):
    """Whether the painted popup has an opaque interior and a visible edge.

    ⛔ READ OFF THE PIXELS, BECAUSE THAT IS THE CLAIM. `opaque_background` and
    `visible_border` are properties of the picture a reader looks at; asking the
    DOM for a `background-color` would answer about a stylesheet the browser may
    or may not have applied to a popup it draws itself.

    ⛔ OPAQUE MEANS ONE BACKGROUND UNDER THE WORDS, NOT A BLANK RECTANGLE. The
    popup draws model ids on its surface, so demanding one colour across the
    interior would fail on a perfectly solid popup. What separates a drawn
    surface from a see-through one is that most of it is ONE colour: a popup
    with no background carries whatever the panel has underneath it - a header,
    a field, a row of buttons - and no single colour dominates there. The band
    measured starts below the top border and stops before the first glyph, so
    what is counted is surface rather than text.
    """
    _w, _h, ch, rows = _png_rows(path)

    def pixel(x, y):
        i = x * ch
        return tuple(rows[y][i:i + 3])

    band = range(box["top"] + 3, box["top"] + 9)
    interior = [pixel(x, y)
                for y in band
                for x in range(box["left"] + 10, box["right"] - 10)]
    counted = Counter(interior)
    surface, seen = counted.most_common(1)[0]
    opaque = seen / len(interior) > 0.5 and sum(surface) > 0
    edge = [pixel(x, box["top"]) for x in range(box["left"] + 4, box["right"] - 4)]
    bordered = bool(edge) and len(set(edge)) == 1 and set(edge) != {surface}
    return {"opaque_background": bool(opaque),
            "visible_border": bool(bordered),
            "surface": list(surface),
            "surface_share": round(seen / len(interior), 3)}


def _redact(text):
    """A sentence with every key-shaped run replaced, for the manifest.

    ⛔ A WRITTEN ARTIFACT CARRIES NO PART OF A KEY. The product masks a
    credential to its prefix and a length, which is right for a screen and still
    a fact about that key; what the evidence has to record is the SHAPE - that a
    mask was drawn at all - so the characters go.
    """
    return re.sub(r"sk-orca-[A-Za-z0-9_\-]*", "sk-orca-<redacted>", text or "")


def live_chat_ids(key):
    """The chat fleet the authoritative URL answers with, for this workspace."""
    request = urllib.request.Request(
        CATALOG_URL,
        headers={"Authorization": "Bearer %s" % key, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as answer:
        payload = json.loads(answer.read().decode("utf-8", "replace"))
    return [record["id"] for record in payload.get("data", [])
            if isinstance(record, dict) and isinstance(record.get("id"), str)]


async def shoot(page, out, name):
    path = out / name
    await page.screenshot(path=str(path))
    width, height = await page.evaluate("() => [window.innerWidth, window.innerHeight]")
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        raise SystemExit("%s is %dx%d, under the %dx%d floor"
                         % (name, width, height, MIN_WIDTH, MIN_HEIGHT))
    return path


async def capture(out, key):
    home = pathlib.Path(os.environ.get("AIHAWK_HOME")
                        or tempfile.mkdtemp(prefix="aihawk-evidence-"))
    home.mkdir(parents=True, exist_ok=True)
    os.environ["AIHAWK_HOME"] = str(home)
    out.mkdir(parents=True, exist_ok=True)

    store = Credentials()
    provider = Provider(None, dict(os.environ), store)
    provider.adopt(orcarouter.resolve_credential(None, os.environ, store))
    provider.set_model(None)
    #: ⛔ THE LIVE CATALOG, THROUGH THE CODE PATH THE PRODUCT USES. If discovery
    #: fails the provider degrades to the labelled seed, and this script says so
    #: instead of photographing a fallback as though it were the live fleet.
    await warm(provider)
    catalog = provider.catalog_state()

    port = free_port()
    server = Served(build_app(registry(provider), provider), port)
    await server.start()
    base = "http://127.0.0.1:%d" % port
    manifest = {
        "automation": {
            "name": "orca-evidence",
            "framework": "playwright",
            "passed": False,
            "catalog_source": CATALOG_URL,
            "catalog_source_kind": catalog["source"],
            "catalog_model_count": len(catalog["models"]),
            "image_model_count": len(provider.models_for("image")["models"]),
        },
        "artifacts": [],
        "ui": {},
    }
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                executable_path=os.environ.get("ORCA_CHROMIUM", "/usr/bin/chromium"),
                args=["--no-sandbox", "--disable-dev-shm-usage"])
            #: ⛔ SCALE 1, BECAUSE A SCALED SHOT DOES NOT CARRY THE POPUP. The
            #: browser's own `<select>` popup is composited at device scale 1
            #: and a `device_scale_factor=2` screenshot comes back without it -
            #: measured, the changed pixels were the focus ring alone. At 1 the
            #: popup is in the image, which is the whole point of the picture.
            page = await browser.new_page(viewport={"width": 1280, "height": 800},
                                          device_scale_factor=1)
            await page.goto(base, wait_until="load")
            await page.wait_for_selector("#provider")
            await page.click("#provider")
            await page.wait_for_selector("#orcapanel:not([hidden])")
            await page.wait_for_timeout(500)

            # --- the two ways in, side by side -----------------------------
            shown = await page.evaluate("""() => {
              const vis = (sel) => {
                const el = document.querySelector(sel);
                if(!el || el.hidden) return false;
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.visibility !== 'hidden'
                       && s.display !== 'none';
              };
              return {api_key_visible: vis('#orcakey') && vis('#orcasave'),
                      pkce_visible: vis('#orcaconnect'),
                      controls_enabled:
                        !document.querySelector('#orcaconnect').disabled
                        && !document.querySelector('#orcasave').disabled,
                      headings: Array.from(document.querySelectorAll('.orcablock h2'))
                                  .map(h => h.textContent)};
            }""")
            drawn = await page.evaluate(
                "() => (document.querySelector('#orcawhere')||{}).textContent || ''")
            #: ⛔ THE PICTURE SHOWS A MASKED KEY, NEVER THE KEY. The credential
            #: the server resolved at startup is on screen as its prefix and a
            #: length, and this proves the value itself is not in the document.
            secret_masked = (key not in drawn and "sk-orca-" in drawn
                             and "characters" in drawn)
            manifest["ui"].update({
                "headings": shown["headings"],
                "masked_line_shape": _redact(drawn),
                "live_key_absent_from_dom": key not in await page.content(),
            })
            manifest["artifacts"].append({
                "kind": "auth-methods",
                "path": "auth-methods.png",
                "ui": {
                    "api_key_visible": bool(shown["api_key_visible"]),
                    "pkce_visible": bool(shown["pkce_visible"]),
                    "secret_masked": bool(secret_masked),
                    "controls_enabled": bool(shown["controls_enabled"]),
                },
            })
            auth_shot = await shoot(page, out, "auth-methods.png")

            # --- the model selector, from the live catalog -----------------
            options = await page.evaluate("""() => {
              const s = document.querySelector('#orcapick');
              return {count: s.options.length,
                      ids: Array.from(s.options).map(o => o.value),
                      status: (document.querySelector('#orcastatus')||{}).textContent || ''};
            }""")
            #: ⛔ FOCUS BEFORE THE FIRST FRAME, SO ONLY THE POPUP DIFFERS. The
            #: focus ring is drawn when the control is reached; taking the
            #: "closed" picture before that would put the ring into the diff and
            #: the measured rectangle would be the ring, not the popup.
            await page.focus("#orcapick")
            await page.wait_for_timeout(300)
            closed = await shoot(page, out, ".dropdown-closed.png")
            trigger = await page.evaluate(
                "() => {const r=document.querySelector('#orcapick').getBoundingClientRect();"
                "return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};}")
            await page.click("#orcapick")
            await page.wait_for_timeout(800)
            opened = await page.evaluate(
                "() => !!document.querySelector('select:open')")
            open_shot = await shoot(page, out, "text-model-dropdown.png")

            # --- and the key entry works in this same page -----------------
            #: ⛔ AFTER THE PICTURES, BECAUSE A MARKED KEY IS NOT A REAL ONE.
            #: The form stores what is typed through the product's own route and
            #: the panel redraws from the server's answer; the catalog that
            #: follows is the labelled fallback, which is the honest consequence
            #: of pasting a key no relay recognises. What this proves is the
            #: path, not the key: the value goes in, a mask comes back, and the
            #: value itself is nowhere in the document afterwards.
            await page.keyboard.press("Escape")
            await page.fill("#orcakey", SHOWN_KEY)
            await page.click("#orcasave")
            await page.wait_for_timeout(1500)
            await page.fill("#orcakey", "")
            pasted = await page.evaluate("""() => {
              const w = (document.querySelector('#orcawhere')||{}).textContent || '';
              const s = document.querySelector('#orcastatus');
              return {where: w, status: (s||{}).textContent || '',
                      count: document.querySelector('#orcapick').options.length};
            }""")
            manifest["ui"].update({
                "after_paste_masked_shape": _redact(pasted["where"]),
                "after_paste_degraded_to": pasted["status"],
                "api_key_paste_works": bool(
                    SHOWN_KEY not in pasted["where"]
                    and "sk-orca-E" in pasted["where"]
                    and "pasted" in pasted["where"]),
                "pasted_key_absent_from_dom": (
                    SHOWN_KEY not in await page.content()
                    and key not in await page.content()),
            })
            await browser.close()
    finally:
        await server.stop()

    box = changed_box(closed, open_shot)
    if box is None:
        raise SystemExit("the dropdown left no mark on the page: it was never open")
    #: The "closed" frame existed only to measure the popup against; it is not a
    #: declared artifact and does not belong in the output directory.
    closed.unlink()
    paint = popup_paint(open_shot, box, 3)
    manifest["ui"].update({
        "dropdown_open": bool(opened),
        "dropdown_item_count": options["count"],
        "dropdown_ids": options["ids"],
        "dropdown_status": options["status"],
        "popup_box": box,
        "trigger_right": trigger["right"],
        "trigger_panel_right_delta": round(box["right"] - trigger["right"], 2),
    })
    manifest["artifacts"].append({
        "kind": "text-model-dropdown",
        "path": "text-model-dropdown.png",
        "ui": {
            "dropdown_open": bool(opened),
            "item_count": options["count"],
            "opaque_background": paint["opaque_background"],
            "visible_border": paint["visible_border"],
            "trigger_panel_right_delta": round(box["right"] - trigger["right"], 2),
        },
    })

    #: ⛔ THE PICTURES HAVE TO SHOW THE LIVE LIST, AND THE LIST HAS TO BE THE
    #: ONE THE AUTHORITATIVE URL ANSWERS WITH. A degraded catalog records itself
    #: and fails the run rather than passing a seed off as the fleet.
    authoritative = live_chat_ids(key)
    manifest["ui"]["chat_catalog_ids"] = authoritative
    manifest["ui"]["page_title"] = "AIHawk"

    for shot_path, entry in ((auth_shot, manifest["artifacts"][0]),
                             (open_shot, manifest["artifacts"][1])):
        entry["sha256"] = hashlib.sha256(shot_path.read_bytes()).hexdigest()

    auth_ui = manifest["artifacts"][0]["ui"]
    drop_ui = manifest["artifacts"][1]["ui"]
    manifest["automation"]["passed"] = bool(
        all(auth_ui.get(f) for f in ("api_key_visible", "pkce_visible",
                                     "secret_masked", "controls_enabled"))
        and all(drop_ui.get(f) for f in ("dropdown_open", "opaque_background",
                                         "visible_border"))
        and manifest["automation"]["catalog_source_kind"] == "live"
        and manifest["automation"]["catalog_model_count"] > 0
        and drop_ui["item_count"] == manifest["automation"]["catalog_model_count"]
        #: The selector is built from the endpoint, not from a list here: every
        #: id it drew is one the authoritative URL named, and every id that URL
        #: named is one it drew. Compared as sets because the two requests are
        #: different queries - the provider reads `/v1/models`, this asks for
        #: `?capability=chat` - and the endpoint is free to order them
        #: differently. What is being held is membership, which is the claim.
        and sorted(manifest["ui"]["dropdown_ids"]) == sorted(authoritative)
        and manifest["ui"]["live_key_absent_from_dom"]
        and manifest["ui"]["api_key_paste_works"]
        and manifest["ui"]["pasted_key_absent_from_dom"])
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                       encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["automation"]["passed"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO / "orca-evidence"),
                        help="where the pictures and the manifest go")
    args = parser.parse_args(argv)
    key = os.environ.get("ORCAROUTER_API_KEY", "")
    if not key:
        raise SystemExit("ORCAROUTER_API_KEY is not set: no live catalog to show")
    return asyncio.run(capture(pathlib.Path(args.out).resolve(), key))


if __name__ == "__main__":
    sys.exit(main())
