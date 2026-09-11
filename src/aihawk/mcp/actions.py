"""The browser operations, as plain functions over a session.

This module is the only implementation. The MCP tools in `server.py` are a thin
wrapper over it, and anything else that drives the browser - the built-in chat,
a test, a script - calls the same functions rather than reimplementing them.

That constraint is the point of the file. A second path to the page would give
two behaviours to keep in step, and they would drift: the tool would grow a
timeout the chat never got, the chat would grow a retry the tool never got, and
the difference would surface as a bug report nobody could reproduce.

Nothing here knows what MCP is, or what a session id is. It takes a session and
acts on it.
"""
from __future__ import annotations

import json
import re
from typing import Any

from . import clean

# The character cap every text-returning action shares. Callers can lower it;
# it exists so one enormous page cannot fill a model's context by itself.
DEFAULT_MAX_CHARS = 6000


def json_capped(obj: Any, limit: int = DEFAULT_MAX_CHARS) -> str:
    """Serialize obj as JSON, capped at `limit` chars.

    Never slices an already-serialized string, which would yield invalid JSON.
    When the payload is too big it returns a small, always-valid envelope.

    For anything that is not a list of elements this is the best that can be
    done. `capped_elements` below is what the snapshot uses, and it exists
    because this envelope was throwing away the whole page.
    """
    s = json.dumps(obj)
    if len(s) <= limit:
        return s
    return json.dumps({"truncated": True, "chars": len(s), "preview": s[:limit]})


def capped_elements(head: dict, elements: list, limit: int = DEFAULT_MAX_CHARS) -> str:
    """As many elements as fit under `limit`, and a count of what did not.

    The snapshot used to serialize everything and then hand back an envelope
    with a slice of the JSON string inside when it was too long. The slice is
    not parseable, so on any page above the cap the caller received zero usable
    elements. Not the first fifty: zero. Measured on a page with 160 elements at
    about 112 characters each, the default cap of 6000 returned nothing at all,
    and a real results page passes that easily.

    So the list is what gets shortened, in document order, and the answer says
    how many were left out. A partial list a model can act on beats a complete
    one it cannot parse.
    """
    out = list(elements)
    while True:
        payload = dict(head)
        payload["interactive_elements"] = out
        omitted = len(elements) - len(out)
        if omitted:
            payload["omitted_elements"] = omitted
            payload["hint"] = "raise max_chars to see the rest"
        s = json.dumps(payload)
        if len(s) <= limit or not out:
            return s
        # Drop roughly the overflow rather than one at a time: a page with two
        # thousand elements would otherwise re-serialize two thousand times.
        overflow = len(s) - limit
        drop = max(1, int(len(out) * overflow / len(s)) + 1)
        out = out[:-drop]


# --- pages -----------------------------------------------------------------

# ⛔ `new_page`, `list_pages`, `select_page` and `close_page` STOOD HERE. They
# were one line each over the same method on the session, and their only
# callers were the four tab tools, which are gone. `navigate` opens the first
# page itself, through `session.new_page()`, so nothing in this module needs
# them any more.


# --- reading ---------------------------------------------------------------

async def navigate(session, url: str, wait_until: str = "domcontentloaded") -> str:
    """Go to a url, and say what came back.

    ⛔ IT USED TO ANSWER `navigated to {url}` WHATEVER HAPPENED, and both halves
    of that were capable of being untrue. A page that answered 404, 403 or 500
    got the same sentence as one that answered 200, so a model reading the reply
    had no way to tell a missing page from a real one and would go on to read an
    error document as content. And after a redirect the url in the sentence was
    the one ASKED FOR, not the one landed on, which is the same defect as the
    silent cut `read_text` used to do: a caller cannot see what it is not told.

    Both halves are now read off the Response. The status is the server's own
    verdict, and the url is `response.url`, which is where the redirect chain
    actually ended.

    ⛔ AND THIS IS WHY `pyproject.toml` FLOORS `invisible-playwright` AT 0.13.2,
    not at 0.13.0. Below that version `goto` answered `None` on every navigation
    ([B200] in the engine's docs), so this function would report "no HTTP
    response" for every page in the world - which is worse than the sentence it
    replaces, because it is a confident and wrong statement rather than a vague
    one. The floor is load-bearing, not hygiene.
    """
    if not session.list_pages():
        await session.new_page()
    page = session.page()
    response = await page.goto(url, wait_until=wait_until, timeout=45_000)
    if response is None:
        # A same-document navigation (an anchor, or the same url again) creates
        # no document and so has no response. Playwright answers None here and
        # so do we: naming the reason keeps it from reading as a failure.
        return f"navigated to {page.url} (no HTTP response: same-document navigation)"
    return f"navigated to {response.url} (HTTP {response.status})"


async def read_text(session, selector: str = "body", max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """The visible text of an element, and an honest word when it did not fit.

    ⛔ THE CUT USED TO BE SILENT, alone among the capped actions. `json_capped`
    returns `{"truncated": true, "chars": N}` and `capped_elements` reports how
    many elements it dropped, but this one simply sliced. A caller then read
    prose that stopped mid-sentence with nothing to distinguish it from a page
    that really ends there, and the natural next move - answering from what came
    back - is answering from a fragment while believing it is the whole thing.

    A cap is fine; a cap nobody can see is not.
    """
    txt = await session.page().evaluate(
        "(sel) => { const el = document.querySelector(sel);"
        " return el ? el.innerText : null; }", selector,
    )
    if txt is None:
        return f"(no element matches {selector!r})"
    if len(txt) <= max_chars:
        return txt
    return txt[:max_chars] + (
        "\n\n[cut after %d of %d characters. Raise max_chars, or narrow the "
        "selector to the part you need.]" % (max_chars, len(txt)))


SNAPSHOT_JS = """() => {
    // Read only. Numbering the elements would mean writing an attribute into
    // the page, which is a detection surface in a product that exists not to
    // have one. If a stable index is ever wanted, it gets decided in the open.
    const SEL = [
        'input', 'button', 'select', 'textarea', 'a[href]',
        '[role="button"]', '[role="link"]', '[role="checkbox"]',
        '[role="radio"]', '[role="tab"]', '[role="menuitem"]', '[role="switch"]',
        '[onclick]', '[tabindex]:not([tabindex="-1"])',
        '[contenteditable="true"]'
    ].join(',');

    // offsetParent used to stand in for "visible" and was wrong both ways: it is
    // null on every position:fixed element - the cookie banner, the sticky bar,
    // the button inside a modal - and it says nothing about visibility:hidden or
    // about an element parked at left:-9999px.
    // How many elements could not be measured at all. It is REPORTED, and that
    // is the whole point of counting it.
    //
    // The first version of this guard just returned false, which turned a loud
    // failure into a silent one: a page that replaces
    // Element.prototype.getBoundingClientRect - the exact threat the comment
    // below names - made shown() answer false for EVERY element, and the tool
    // returned an empty list with no error, byte-identical to a page that
    // genuinely has no controls. That is worse than the crash it replaced,
    // because the crash at least named its cause.
    //
    // With the count, the two cases separate on sight: one odd element leaves
    // 199 results and `unmeasurable: 1`, while a shadowed prototype leaves zero
    // results and `unmeasurable: 412`.
    let unmeasurable = 0;

    function shown(el) {
        // getBoundingClientRect can fail to give a rectangle on a real page:
        // measured on one, the snapshot died with "can't access property
        // width, r is undefined" and the caller got NOTHING for the whole
        // document. A page can shadow or replace this method, and some do.
        // One odd element must not cost the other two hundred.
        let r = null;
        try { r = el.getBoundingClientRect(); } catch (err) { unmeasurable++; return false; }
        if (!r || typeof r.width !== 'number') { unmeasurable++; return false; }
        if (r.width <= 0 || r.height <= 0) return false;
        const s = getComputedStyle(el);
        if (s.visibility === 'hidden' || s.display === 'none') return false;
        if (parseFloat(s.opacity) === 0) return false;
        if (el.disabled === true) return false;
        // Parked off-canvas to the left or above: the ordinary way to hide
        // something without hiding it. Below the fold is NOT excluded, because
        // the page may simply be long and that content is still real.
        if (r.right <= 0 || r.bottom <= 0) return false;
        // Clipped to nothing. This is how a "skip to content" link hides until
        // it is focused, and it is the same kind of invisible as
        // visibility:hidden two lines up - the rule this function already
        // applies, just written a different way in CSS.
        //
        // Measured: two of three failed clicks on real pages were skip links
        // reported as visible. Playwright spends its whole timeout on one, 208
        // attempts over 15 seconds, and hands back an opaque failure. Reporting
        // an element nobody can click is not information, it is a trap.
        //
        // ⛔ NOT for form controls, and that exception is the whole difficulty.
        // A file input and a custom checkbox are hidden by exactly this markup
        // on an enormous share of the web - the visible affordance is a styled
        // <label> over the top - and they stay fully operable: Playwright can
        // check() and set_input_files() them, and a click on the label reaches
        // them. Excluding those would cost an agent the ability to tick a
        // consent box or upload a file, which is a worse loss than the skip
        // link this rule exists to remove. A skip link is an <a>.
        const control = /^(input|select|textarea|button)$/.test(el.tagName.toLowerCase());
        if (!control) {
            if (s.clipPath && /inset\\(\\s*(?:50|100)%/.test(s.clipPath)) return false;
            if (s.clip && /rect\\(\\s*0(?:px)?[,\\s]/.test(s.clip)) return false;
            if (r.width <= 1 && r.height <= 1 && s.overflow === 'hidden') return false;
        }
        return true;
    }

    // There is no cap on how many elements come back. A cap is a guess about
    // what the caller needs, made without knowing what it is looking for, and a
    // form's submit button is exactly the sort of thing that sits past it. What
    // is controlled instead is the weight of each element: measured on real
    // pages, href alone was 46% of the payload, so what gets dropped is what
    // carries no information rather than what happens to come last.
    // What a <select> is SET TO, which is the one thing its text cannot say:
    // innerText on a menu is every option concatenated, so a country picker
    // reads the same before and after it is chosen.
    function chosen(el) {
        return [...el.selectedOptions].map(o => o.text).join(', ');
    }

    function useful(h) {
        if (!h) return undefined;
        if (h === '#' || h.startsWith('javascript:')) return undefined;
        return h;
    }

    // A handle that reaches ONE element, and the reason it exists is measured.
    // Across 958 elements on real pages, 88.3% carried id, name or href and
    // every one of those reached the right node - but only 47.6% reached it
    // ALONE. For the other 41% the obvious selector matches several nodes, and
    // Playwright acts on the first, so a model looking at the third of five
    // identical links clicks the first and is told it succeeded. Nothing fails
    // and nothing is logged: it just quietly does the wrong thing.
    //
    // `:nth-match(sel, n)` is Playwright's own syntax and it resolves through
    // this engine, verified rather than assumed. The count comes from the whole
    // document, not from this list, because an element filtered out here for
    // being invisible still occupies a position in querySelectorAll.
    const matches = new Map();
    function nodesFor(sel) {
        if (!matches.has(sel)) {
            let n = [];
            try { n = Array.from(document.querySelectorAll(sel)); } catch (err) { n = []; }
            matches.set(sel, n);
        }
        return matches.get(sel);
    }
    function cssq(s) { return (window.CSS && CSS.escape) ? CSS.escape(s) : s.replace(/[^\\w-]/g, '\\\\$&'); }
    // Single quotes inside the selector, because this string is about to be
    // serialized as JSON and every double quote in it would come back as two
    // characters. CSS accepts either.
    function attr(s) { return String(s).replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'"); }
    function handle(el, href) {
        let base = null, fromHref = false;
        if (el.id) base = '#' + cssq(el.id);
        else if (el.name) base = el.tagName.toLowerCase() + "[name='" + attr(el.name) + "']";
        else if (href) { base = "a[href='" + attr(href) + "']"; fromHref = true; }
        // The two below are APPENDED to the order rather than woven into it, so
        // no selector that already worked changes and the risk of regressing
        // the 88% is zero. They exist because 9.5% of elements had no handle at
        // all and fell back on coordinates, which go stale the moment the page
        // scrolls: of those, 58% carried a data-testid - an attribute whose
        // whole purpose is to be a stable unique handle - and a further quarter
        // an aria-label that was unique on the page.
        else {
            const dt = el.getAttribute('data-testid') || el.getAttribute('data-test')
                    || el.getAttribute('data-qa') || el.getAttribute('data-cy');
            if (dt) {
                const which = el.getAttribute('data-testid') ? 'data-testid'
                            : el.getAttribute('data-test') ? 'data-test'
                            : el.getAttribute('data-qa') ? 'data-qa' : 'data-cy';
                base = '[' + which + "='" + attr(dt) + "']";
            } else {
                const al = el.getAttribute('aria-label');
                if (al) base = "[aria-label='" + attr(al) + "']";
            }
        }
        if (!base) return null;
        const n = nodesFor(base);
        if (n.length === 1) return {sel: base, fromHref: fromHref};
        const i = n.indexOf(el);
        if (i < 0) return null;
        return {sel: ':nth-match(' + base + ', ' + (i + 1) + ')', fromHref: fromHref};
    }

    // No deduplication. It looked free - the same link in the header and in
    // the footer - and it is not: two buttons with the same text and no id are
    // two different places on the screen, and on a results page they are "add
    // to cart" repeated once per product. Measured on the same DOM, in the same
    // instant: it removed 8.1% of the elements to save 13% of the weight. An
    // element the model cannot see is an element it cannot click, which is the
    // character cap wearing a different name.
    const seen = new Set();
    const out = [];
    // The body is wrapped because one element must never cost the page. A real
    // page killed the whole snapshot from inside getBoundingClientRect, and the
    // caller received nothing at all - which is worse than any partial answer,
    // and indistinguishable from a page with no controls on it.
    for (const el of document.querySelectorAll(SEL)) {
      try {
        if (seen.has(el)) continue;
        seen.add(el);
        if (!shown(el)) continue;
        const r = el.getBoundingClientRect();
        const isSel = el.tagName === 'SELECT';
        const isBox = el.type === 'checkbox' || el.type === 'radio';
        const text = (isSel ? chosen(el) : (el.innerText || el.value || '')).trim().replace(/\\s+/g, ' ').slice(0, 60);
        const href = el.tagName === 'A' ? useful(el.getAttribute('href')) : undefined;

        const e = { tag: el.tagName.toLowerCase() };
        if (el.getAttribute('role')) e.role = el.getAttribute('role');
        if (el.type) e.type = el.type;
        if (el.name) e.name = el.name;
        if (el.id) e.id = el.id;
        // The selector to pass to browser_click / browser_type verbatim. Always
        // present when the element can be reached by one at all, so a caller
        // never has to build one, never has to escape anything, and never has
        // to know when the obvious one would have been ambiguous. One rule
        // instead of a conditional one, which is the kind a caller gets wrong.
        const h = handle(el, href);
        if (h) e.selector = h.sel;
        // The href is dropped when the selector already carries it, which is
        // the whole reason this stayed affordable. Measured over 969 elements
        // on real pages: emitting the selector cost +47.2% of the payload, and
        // +15.1% once the duplicated href came out - for the same information,
        // since `a[href='/cart']` says where the link goes as plainly as the
        // separate field did. A link addressed by its id keeps its href, having
        // nothing duplicated.
        if (href && !(h && h.fromHref)) e.href = href;
        if (el.placeholder) e.placeholder = el.placeholder;
        if (el.getAttribute('aria-label')) e.label = el.getAttribute('aria-label');
        if (text) e.text = text;
        // THE CURRENT STATE, and it is here because of what its absence caused.
        // A model asked to tick a box and pick an option could see neither, so
        // it read them the only way left to it - by injecting script - and then
        // wrote them back the same way. A gap in what the caller can SEE is
        // answered with evaluate() just as surely as a gap in what it can DO,
        // and a value set from script is not a trusted event.
        if (isBox) e.checked = el.checked;
        if (isSel) e.value = el.value;
        // Centre coordinates in the viewport, so browser_click_at can reach
        // what no selector describes.
        e.at = [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)];
        // Only when it is OUTSIDE: inside is the common case, and saying so
        // every time costs bytes without informing anyone.
        if (!(r.top < innerHeight && r.left < innerWidth)) e.off_screen = true;
        out.push(e);
      } catch (err) { unmeasurable++; }
    }
    const answer = { title: document.title, url: location.href, interactive_elements: out };
    // Emitted only when it happened, and emitted HERE rather than added by the
    // Python side: with no cap the snapshot returns this object verbatim, so a
    // counter added later would never reach the caller on the default path.
    if (unmeasurable) answer.unmeasurable = unmeasurable;
    return answer;
}"""


async def snapshot(session, max_chars: int = 0) -> str:
    """Title, url, and the interactive elements that are actually visible.

    Not the accessibility tree, and the reason is measured rather than
    aesthetic: on a real sign-up page a single country `<select>` contributes
    about two hundred `<option>` nodes, which fill the character cap before the
    form the caller was looking for appears at all. Filtering to elements a
    caller can act on - and to `offsetParent !== null`, so hidden ones do not
    count - keeps the answer about the page rather than about its longest
    dropdown.
    """
    d = await session.page().evaluate(SNAPSHOT_JS)
    if not max_chars:
        return json.dumps(d)
    elements = d.pop("interactive_elements", [])
    return capped_elements(d, elements, limit=max_chars)


async def read_html(session, mode: str = "form") -> str:
    """The page's markup, reduced to what is worth reading.

    Two steps, and they are split because only one of them can be done in each
    place. The browser decides what is actually painted - computed style and
    layout exist only there - and it does that on a CLONE, so the live page is
    never written to. The string that comes back is then cleaned in Python,
    where the structural work is testable without a browser.

    Measured over a corpus of real pages: 9.6 MB of markup became 293 KB, 97%
    smaller, with every one of the 1,453 interactive elements still present, and
    a median of 48 ms per page.

    mode="form"  the interactive surface plus the text that explains it
    mode="text"  the prose, with the markup gone
    mode="full"  noise removed and attributes slimmed, structure kept
    """
    html = await session.page().evaluate(clean.VISIBLE_HTML_JS)
    return clean.clean_page(html, mode)


async def screenshot_png(session) -> bytes:
    """Raw PNG bytes of the active tab.

    Bytes rather than an MCP Image, because this is also what a live view in a
    browser tab needs, and that caller has no use for an MCP type.
    """
    return await session.page().screenshot()


async def watch_jpeg(session) -> bytes:
    """Raw JPEG bytes of the whole browser WINDOW of the active tab.

    What a person at the machine would see: tab strip, address bar, page and
    the pointer, which no page screenshot can contain because the engine draws
    it outside the page on purpose. Comes from a live capture the session keeps
    running on the tab (`StealthSession.watch_frame`).
    """
    return await session.watch_frame()


# --- acting ----------------------------------------------------------------

DIAGNOSE_JS = """(sel) => {
    // Why a click could not land. Runs only after one has failed, so it can
    // afford to look properly.
    let n = [];
    try { n = document.querySelectorAll(sel); } catch (err) { return {bad_selector: true}; }
    if (!n.length) return {matches: 0};
    const el = n[0];
    const r = el.getBoundingClientRect();
    const out = {matches: n.length, width: Math.round(r.width), height: Math.round(r.height)};
    const s = getComputedStyle(el);
    if (s.display === 'none') out.display_none = true;
    if (s.visibility === 'hidden') out.visibility_hidden = true;
    if (el.disabled === true) out.disabled = true;
    if (s.pointerEvents === 'none') out.pointer_events_none = true;
    if (r.bottom < 0 || r.top > innerHeight) out.off_screen = true;
    // The one that matters most: something else is on top. Report WHAT, because
    // the caller's next move is to deal with that thing.
    const cx = Math.round(r.left + r.width / 2), cy = Math.round(r.top + r.height / 2);
    if (cx >= 0 && cy >= 0 && cx < innerWidth && cy < innerHeight) {
        const hit = document.elementFromPoint(cx, cy);
        if (hit && hit !== el && !el.contains(hit) && !hit.contains(el)) {
            out.covered_by = {
                tag: hit.tagName.toLowerCase(),
                id: hit.id || undefined,
                cls: (hit.className && hit.className.toString().slice(0, 60)) || undefined,
                text: (hit.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 60) || undefined,
                position: getComputedStyle(hit).position
            };
        }
    }
    return out;
}"""


async def click(session, selector: str) -> str:
    """Click an element, and say what stopped it when nothing happens.

    Playwright reports a failed click as "not actionable in 15s after N
    attempts", which tells a caller that something is wrong and nothing about
    what. Measured across eighteen real sites, four clicks failed and every one
    of them failed that way: a logo, a footer link, a shipping button. Fifteen
    seconds spent to learn nothing.

    So a failure asks the page why. The answer a caller can act on is
    `covered_by`: if a cookie banner is sitting over the button, the next move
    is to dismiss the banner, and that is a different action from retrying.
    """
    try:
        await session.page().click(selector, timeout=15_000)
    except Exception as exc:
        try:
            why = await session.page().evaluate(DIAGNOSE_JS, selector)
        except Exception:
            why = None
        if why:
            raise RuntimeError(f"{exc}\n\nwhy the click did not land: {json.dumps(why)}") from exc
        raise
    return f"clicked {selector}"


async def click_at(session, x: float, y: float, hold_seconds: float = 0.0) -> bytes:
    """Click (or press-and-hold) a raw viewport coordinate instead of a
    selector - for targets a selector cannot reliably reach: a slider track, a
    canvas-drawn captcha, or a precise point inside a wider element. Moves the
    pointer there first (no teleport), then down, then - if hold_seconds is 0 -
    immediately up (a plain click); otherwise waits before releasing.

    Returns a screenshot taken right after release, so the result of the click
    is visible without a second round-trip.
    """
    page = session.page()
    await page.mouse.move(x, y, steps=12)
    await page.mouse.down()
    if hold_seconds > 0:
        await page.wait_for_timeout(int(hold_seconds * 1000))
    await page.mouse.up()
    # Give a post-click transition (checkmark, redirect, reflow) a moment to
    # start before the screenshot, so it reflects the outcome, not the click.
    await page.wait_for_timeout(400)
    return await page.screenshot()


async def type_text(session, selector: str, text: str) -> str:
    await session.page().fill(selector, text, timeout=15_000)
    return f"typed into {selector}"


async def select_option(session, selector: str, value: str) -> str:
    """Choose an option in a `<select>`, by its value OR by its visible label.

    ⛔ IT EXISTS BECAUSE ITS ABSENCE PUSHED MODELS INTO A DETECTABLE WORKAROUND.
    Measured on a four-field form: with no way to set a select, the model clicked
    it, pressed ArrowDown twice hoping to land on the right row, could not tell
    whether it had, and finally set `select.value` through `browser_evaluate`.
    That last step is script injection into the page - it skips the humanised
    path entirely and produces a change the site never saw a real interaction
    for. A missing tool is not a neutral gap: the model routes around it, and the
    route it finds is worse than the tool would have been.

    BOTH value and label, tried in that order, because a model reads the page and
    what a page shows is the LABEL. Asking it for the `value` attribute means
    asking it to read markup it may never have fetched, and a tool that needs the
    caller to know a hidden attribute is a tool that gets used wrong.
    """
    page = session.page()
    try:
        chosen = await page.select_option(selector, value=value, timeout=15_000)
        if chosen:
            return f"selected {selector} by value: {chosen}"
    except Exception:
        # Not an error yet: `value` may well have been a label. The second
        # attempt is what decides, and its failure is the one worth reporting.
        pass
    chosen = await page.select_option(selector, label=value, timeout=15_000)
    if not chosen:
        # Playwright answers with an empty list rather than raising when nothing
        # matched, so a caller reading only the exception would believe it had
        # worked and go on to submit a form that never changed.
        raise RuntimeError(
            f"no option in {selector} has the value or the label {value!r}")
    return f"selected {selector} by label: {chosen}"


async def press_key(session, key: str) -> str:
    await session.page().keyboard.press(key)
    return f"pressed {key}"


# ── evaluate, and the one thing it must not be used for ─────────────────────
#
# ⛔ THIS PACKAGE EXISTS SO THAT INTERACTION LOOKS REAL, AND A VALUE SET FROM
# SCRIPT IS THE OPPOSITE OF THAT. `el.value = 'beta'` changes the field without
# a keystroke, without focus, without a trusted event; `el.click()` fires a
# handler with `isTrusted === false`, which is one property read away from being
# the clearest bot signal a page can collect. Every other tool here goes through
# the humanised path - approach, hover, press, release - and this one would go
# around it.
#
# It is not a hypothetical. Measured 2026-09-02, first run with a real model:
# asked to pick an option from a dropdown, with no tool that could, it clicked
# the select, pressed ArrowDown twice, and then ran `s.value='beta'` through
# here. The model was not being careless - it was routing around a gap, which is
# what a capable model does. The gap is the defect; this refusal is what makes
# the gap visible instead of silently detectable.
#
# So the fix is in two halves and both are needed. The gaps are closed
# (`browser_select_option` exists, and the snapshot reports `checked` and the
# selected `value`, which is what sent it here to READ in the first place), and
# the shortcut is refused with the name of the tool to use instead. Closing the
# gaps alone leaves the shortcut for the next gap; refusing alone leaves the
# model stuck with a task it can see how to finish.
#
# ⛔ AND THIS IS A PATTERN CHECK, NOT A SANDBOX. JavaScript has unlimited ways
# to say the same thing and this catches the ones a model actually writes. It is
# a guardrail on the obvious road, not a wall around the field, and it must not
# be described as one anywhere.
_BY_SCRIPT = (
    (re.compile(r"""\.(?:value|checked|selected)\s*\+?=(?!=)"""),
     "browser_type for a text field, browser_select_option for a dropdown, "
     "browser_click for a checkbox or a radio"),
    (re.compile(r"""\[\s*['"](?:value|checked|selected)['"]\s*\]\s*\+?=(?!=)"""),
     "browser_type for a text field, browser_select_option for a dropdown, "
     "browser_click for a checkbox or a radio"),
    (re.compile(r"""\.click\s*\("""),
     "browser_click, or browser_click_at when no selector describes the target"),
    (re.compile(r"""\.dispatchEvent\s*\("""),
     "browser_click, browser_type or browser_press_key - whichever interaction you are synthesising, there is a tool that produces it for real"),
    (re.compile(r"""\.(?:submit|requestSubmit)\s*\("""),
     "browser_click on the form's submit button"),
    # The five below were measured passing on 2026-09-04: they are the ordinary
    # modern spellings of the same acts, not exotic ones. `requestSubmit` above
    # is the same story - it is what `submit()` has become, and only the older
    # name was refused.
    (re.compile(r"""\.setAttribute\s*\(\s*['"](?:value|checked|selected|disabled)['"]"""),
     "browser_type for a text field, browser_select_option for a dropdown, "
     "browser_click for a checkbox or a radio"),
    (re.compile(r"""Object\s*\.\s*assign\s*\("""),
     "browser_type, browser_select_option or browser_click - whichever of those "
     "properties you are setting, a tool sets it for real"),
    (re.compile(r"""Reflect\s*\.\s*set\s*\("""),
     "browser_type, browser_select_option or browser_click"),
    (re.compile(r"""\.execCommand\s*\("""),
     "browser_type, which types into the focused field through the keyboard"),
)


def _refuse_script_interaction(expression: str) -> None:
    for pattern, instead in _BY_SCRIPT:
        if pattern.search(expression):
            raise ValueError(
                "refused: this changes the page from script, which produces an "
                "untrusted event and is exactly what this browser exists to "
                "avoid. Use " + instead + ". Reading is fine - it is assigning "
                "and calling that is refused. If no tool fits, say so in your "
                "answer rather than working around it.")


async def evaluate(session, expression: str) -> str:
    """Read from the page. Acting on it goes through the named tools.

    The refusal is deliberately narrow: it looks at what is being ASSIGNED or
    CALLED, so `el.value` reads and `el.value === 'x'` comparisons pass, and
    only `el.value = 'x'` does not.
    """
    _refuse_script_interaction(expression)
    return json_capped(await session.page().evaluate(expression))
