"""The OrcaRouter panel, photographed on the running product.

⛔ A PICTURE OF THE INTERFACE IS AN OBSERVATION, NOT A SOURCE FILE. The first
version of this evidence was a generator script plus two committed PNGs and a
manifest, and that is the one shape it must not have: a screenshot in the patch
is a claim nobody re-ran, and it goes on describing an interface that has moved.
So the evidence is produced HERE, by a test, against a real `python -m aihawk
ui` on loopback with a real browser, and `orca-evidence/` is written by the run
and is not tracked. A reviewer who changes the panel and forgets the pictures
gets them regenerated rather than kept.

⛔ AND IT IS THE PRODUCT'S OWN ROUTES THAT ARE PHOTOGRAPHED. The panel is
opened the way a person opens it (the Provider button in the header), the key
is put in through `POST /provider/key`, and the model list is the server's
answer for the account's own catalogue - not a fixture, and not a page built
for the photograph. What the assertions read is the live DOM: the two ways in
on one card, the mask the SERVER computed, and the listbox actually expanded.

⛔ THE MASK ON SCREEN IS A FAKE KEY'S. The catalogue evidence needs the real
key, because the point of it is that the dropdown holds what the account can
actually call; the auth-methods photograph is taken after a fake key has been
saved through the same route, so no part of the real key is ever drawn. That is
why the two shots are taken in that order rather than together.

It is `ui`-marked: it starts a browser and a server, so `addopts` deselects it
and it is asked for by name. Without `ORCAROUTER_API_KEY` it skips, so a
checkout with no key still runs the suite.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import pathlib
import signal
import socket
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

from aihawk import orcarouter

pytestmark = pytest.mark.ui

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "orca-evidence"
SRC = str(ROOT / "src")

#: The browser the automation drives. Named rather than downloaded: this test
#: must not fetch a quarter of a gigabyte to take two photographs.
CHROMIUM = "/usr/bin/chromium"

#: ⛔ THE AUTHORITATIVE CATALOGUE, AND IT IS NAMED HERE IN FULL. The manifest
#: has to say which catalogue the dropdown was bound to, and "the chat
#: catalogue" is not an address.
CATALOG_URL = "https://api.orcarouter.ai/v1/models?capability=chat"

#: A key that is obviously not one, saved through the real route so the mask on
#: screen is the server's own arithmetic rather than a string this test wrote.
FAKE_KEY = "sk-orca-CANARYCANARY0000"

KEY = os.environ.get("ORCAROUTER_API_KEY", "")

needs_key = pytest.mark.skipif(
    not KEY, reason="no ORCAROUTER_API_KEY, so there is no catalogue to photograph")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _png_size(path: pathlib.Path) -> tuple:
    """The width and height out of a PNG header, so "at least 800x450" is
    measured rather than assumed from the viewport that was asked for."""
    header = path.open("rb").read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", "%s is not a PNG" % path
    return struct.unpack(">II", header[16:24])


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Interface:
    """The real interface, on loopback, in its own home and its own session.

    ⛔ A SESSION OF ITS OWN, so a photograph cannot depend on what this machine
    happens to have signed in, and so nothing this test writes can reach a real
    credential. The key travels in the child's environment, which is the
    mechanism the product documents for it.
    """

    def __init__(self, home: pathlib.Path) -> None:
        self.port = _free_port()
        self.home = home
        self.process = None

    @property
    def base(self) -> str:
        return "http://127.0.0.1:%d" % self.port

    def start(self) -> None:
        env = dict(os.environ)
        env["AIHAWK_HOME"] = str(self.home)
        env["PYTHONPATH"] = SRC + os.pathsep + env.get("PYTHONPATH", "")
        env["ORCAROUTER_API_KEY"] = KEY
        # ⛔ THE OTHER PROVIDER'S NAME IS CLEARED. `ui` reads it to decide which
        # provider a run is for, and a shell that happens to export it would
        # otherwise photograph a different product.
        env.pop("OPENROUTER_API_KEY", None)
        env.pop("ORCA_KEY", None)
        self.process = subprocess.Popen(
            [sys.executable, "-m", "aihawk", "ui",
             "--binary", CHROMIUM, "--host", "127.0.0.1",
             "--port", str(self.port)],
            cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, start_new_session=True)
        self._wait_until_up()

    def _wait_until_up(self) -> None:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                said = self.process.stdout.read() if self.process.stdout else ""
                raise AssertionError(
                    "the interface exited (%s) before it served anything:\n%s"
                    % (self.process.returncode, said[-2000:]))
            try:
                with urllib.request.urlopen(self.base + "/provider/state",
                                            timeout=2) as answer:
                    if answer.status == 200:
                        return
            except (urllib.error.URLError, OSError):
                time.sleep(0.25)
        raise AssertionError("the interface never answered on %s" % self.base)

    def state(self) -> dict:
        with urllib.request.urlopen(self.base + "/provider/state",
                                    timeout=10) as answer:
            return json.loads(answer.read().decode("utf-8"))

    def stop(self) -> None:
        if self.process is None:
            return
        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            pass
        if self.process.stdout:
            self.process.stdout.close()
        self.process = None


def _playwright():
    """Playwright, or a skip that says why.

    ⛔ IMPORTED INSIDE A `try` THAT CATCHES ImportError, which is how this
    repository declares an optional dependency (see the rule in
    `test_what_is_imported_is_declared.py`): the evidence run needs a driver,
    the ordinary suite does not, and a suite that cannot start without one
    would be a new floor for everybody.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on the machine
        pytest.skip("the evidence run needs playwright: %s" % exc)
    return sync_playwright


@needs_key
def test_the_panel_is_photographed_on_the_running_product(tmp_path):
    """The two pictures and the manifest, produced by running the interface.

    ⛔ WHAT IT ASSERTS IS WHAT THE PICTURES HAVE TO SHOW. The dropdown holds the
    account's own catalogue (so the count it reports is the catalogue's, read
    through the project's own reader), the card shows both ways in with the
    server's mask and live controls, and the open list is a thing on the screen
    rather than a hidden element with rows in it. A `passed` that only meant
    "two files exist" would be the same claim the committed PNG made.
    """
    sync_playwright = _playwright()
    if not pathlib.Path(CHROMIUM).exists():
        pytest.skip("no browser at %s to photograph the interface with" % CHROMIUM)

    # ⛔ THE CATALOGUE FIRST, THROUGH THE CODE UNDER TEST. `fetch_catalog` is
    # the provider's own reader of `GET /v1/models`, so the number the manifest
    # reports is the number the product would have used, not a `curl` beside it.
    chat_models = asyncio.run(orcarouter.fetch_catalog(KEY, capability="chat"))
    image_models = asyncio.run(orcarouter.fetch_catalog(KEY, capability="image"))
    catalog_count = len(chat_models)
    assert catalog_count, "the account's chat catalogue came back empty"

    OUT.mkdir(exist_ok=True)
    interface = Interface(tmp_path / "home")
    findings = {}
    try:
        interface.start()
        started = interface.state()
        assert started["provider"] == "orcarouter", (
            "the interface did not start on OrcaRouter: %r" % started["provider"])
        assert started["source"] == orcarouter.LIVE_SOURCE, (
            "discovery failed, so there is no account catalogue to photograph: %s"
            % started["catalog_error"])
        assert len(started["models"]) == catalog_count, (
            "the panel offers %d models and the catalogue has %d"
            % (len(started["models"]), catalog_count))

        with sync_playwright() as driver:
            browser = driver.chromium.launch(
                executable_path=CHROMIUM,
                args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1100, "height": 720})
            page.goto(interface.base + "/", wait_until="load")
            # The panel, opened the way a person opens it.
            page.wait_for_selector("#provopen", timeout=30000)
            page.click("#provopen")
            page.wait_for_function(
                "() => (document.getElementById('provchosen')||{}).textContent",
                timeout=30000)

            # --- text-model-dropdown.png: the account's list, open -----------
            page.click("#provmodel")
            page.wait_for_function(
                "n => document.querySelectorAll('#provlist .opt').length === n",
                arg=catalog_count, timeout=15000)
            rows = page.eval_on_selector_all(
                "#provlist .opt", "els => els.map(e => e.textContent)")
            boxes = page.eval_on_selector_all(
                "#provlist .opt",
                "els => els.map(e => { const b = e.getBoundingClientRect();"
                " return {x: b.x, y: b.y, w: b.width, h: b.height}; })")
            listbox = page.evaluate("""() => {
              const l = document.getElementById('provlist');
              const s = getComputedStyle(l);
              const b = l.getBoundingClientRect();
              return {bg: s.backgroundColor, width: s.borderTopWidth,
                      style: s.borderTopStyle, position: s.position,
                      x: b.x, y: b.y, w: b.width, h: b.height,
                      hidden: l.hidden};
            }""")
            trigger = page.locator("#provmodel").bounding_box()
            # ⛔ THE OPEN LIST IS A THING ON THE SCREEN, so the point in the
            # middle of it belongs to a row rather than to the panel behind it.
            hit = page.evaluate("""() => {
              const b = document.getElementById('provlist').getBoundingClientRect();
              const e = document.elementFromPoint(b.x + b.width / 2,
                                                  b.y + b.height / 2);
              return e ? (e.closest('.opt') ? e.closest('.opt').textContent
                                            : (e.id || e.tagName)) : null;
            }""")
            visible_rows = [b for b in boxes
                            if b["y"] >= 0 and b["y"] + b["h"] <= 720]
            findings["rows_total"] = len(boxes)
            findings["rows_on_screen"] = len(visible_rows)
            findings["point_in_list_hit"] = hit
            findings["point_in_list_is_a_row"] = hit in rows
            findings["item_count"] = len(rows)
            findings["items"] = rows
            findings["opaque_background"] = (
                listbox["bg"].startswith("rgb(") and "0, 0, 0, 0" not in listbox["bg"])
            findings["visible_border"] = (
                listbox["width"] not in ("0px", "") and listbox["style"] != "none")
            findings["dropdown_open"] = not listbox["hidden"]
            findings["panel_position"] = listbox["position"]
            findings["trigger_panel_right_delta"] = (
                abs((trigger["x"] + trigger["width"])
                    - (listbox["x"] + listbox["w"])) if trigger else None)
            page.screenshot(path=str(OUT / "text-model-dropdown.png"))
            page.click("#provmodel")  # put the list away again

            # --- auth-methods.png: both ways in, with the server's mask ------
            # ⛔ THE FAKE KEY GOES IN THROUGH THE REAL ROUTE, AFTER the
            # catalogue has been photographed, so the mask on screen is the
            # server's own and no part of the real key is ever drawn.
            page.evaluate("""async (fake) => {
              await fetch('/provider/key', {method:'POST',
                headers:{'Content-Type':'application/json'},
                body: JSON.stringify({key: fake})});
              await refreshProvider();
            }""", FAKE_KEY)
            page.wait_for_function(
                "() => (document.getElementById('provmasked')||{}).textContent"
                "      .startsWith('sk-orca-...')", timeout=15000)
            findings["api_key_visible"] = page.is_visible("#provinput")
            findings["pkce_visible"] = page.is_visible("#provconnect")
            findings["controls_enabled"] = (page.is_enabled("#provconnect")
                                            and page.is_enabled("#provinput"))
            masked = page.inner_text("#provmasked")
            findings["masked_shown"] = masked
            findings["secret_masked"] = (masked.startswith("sk-orca-...")
                                         and "CANARY" not in masked
                                         and FAKE_KEY not in masked)
            findings["api_key_label"] = page.inner_text("#provkey label.lbl")
            findings["pkce_label"] = page.inner_text("#provoauth .how").strip()[:80]
            page.screenshot(path=str(OUT / "auth-methods.png"))
            browser.close()
    finally:
        interface.stop()

    right_delta = abs(findings["trigger_panel_right_delta"] or 0)
    passed = bool(
        findings["api_key_visible"] and findings["pkce_visible"]
        and findings["secret_masked"] and findings["controls_enabled"]
        and findings["dropdown_open"] and findings["item_count"] == catalog_count
        and findings["point_in_list_is_a_row"] and findings["opaque_background"]
        and findings["visible_border"] and right_delta <= 2)
    manifest = {
        "automation": {
            "framework": "playwright",
            "passed": passed,
            "catalog_source": CATALOG_URL,
            "catalog_model_count": catalog_count,
            "catalog_model_count_note": (
                "read through aihawk.orcarouter.fetch_catalog, the provider's own "
                "reader of GET %s" % CATALOG_URL),
            "image_model_count": len(image_models),
            "automation": ("playwright (python) driving %s against a real "
                           "`python -m aihawk ui` on 127.0.0.1, produced by "
                           "tests/test_orcarouter_ui_evidence.py" % CHROMIUM),
        },
        "artifacts": [
            {"kind": "text-model-dropdown", "path": "text-model-dropdown.png",
             "sha256": _sha256(OUT / "text-model-dropdown.png"),
             "ui": {"dropdown_open": findings["dropdown_open"],
                    "item_count": findings["item_count"],
                    "opaque_background": findings["opaque_background"],
                    "visible_border": findings["visible_border"],
                    "trigger_panel_right_delta": right_delta}},
            {"kind": "auth-methods", "path": "auth-methods.png",
             "sha256": _sha256(OUT / "auth-methods.png"),
             "ui": {"api_key_visible": findings["api_key_visible"],
                    "pkce_visible": findings["pkce_visible"],
                    "secret_masked": findings["secret_masked"],
                    "controls_enabled": findings["controls_enabled"]}},
        ],
        "notes": {
            "multimodal": ("not applicable: this interface has no attachment or "
                           "image input. The composer is one textarea "
                           "(src/aihawk/ui/page.html) and the route it posts to "
                           "reads one text field (src/aihawk/routes.py, `send`)."),
            "auth": ("API Key and OAuth 2.0 PKCE side by side on one OrcaRouter "
                     "card; the mask shown is the server's own, computed for a "
                     "fake key saved through POST /provider/key"),
            "catalog": ("the model listbox is drawn from the server's answer for "
                        "the account's own catalogue; the count reported here is "
                        "that catalogue's, read through the provider's reader"),
        },
        "findings": findings,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                       encoding="utf-8")

    # ⛔ THE MANIFEST IS ONLY WORTH WHAT IT ASSERTED. Every line below is a
    # claim the pictures have to support, checked against the DOM the pictures
    # were taken from rather than against the file that was just written.
    for name in ("auth-methods.png", "text-model-dropdown.png"):
        width, height = _png_size(OUT / name)
        assert (width, height) >= (800, 450), "%s is %dx%d" % (name, width, height)
        assert (OUT / name).stat().st_size >= 10_000, "%s is too small" % name
    assert findings["item_count"] == catalog_count, (
        "the open list holds %d rows and the catalogue has %d"
        % (findings["item_count"], catalog_count))
    assert findings["secret_masked"], "the key on screen is not masked: %r" % masked
    assert findings["api_key_visible"] and findings["pkce_visible"], (
        "the card does not show both ways in")
    assert findings["point_in_list_is_a_row"], (
        "the middle of the open list belongs to %r, not to a row" % hit)
    assert right_delta <= 2, "the list is %r px off its trigger" % right_delta
    assert passed, "the evidence run did not pass: %s" % json.dumps(findings)
