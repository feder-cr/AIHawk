"""HTML cleaning: the same page, small enough to hand to a model.

A raw page is not something you can put in a prompt. Measured on the corpus this
was tuned against, one page serialized to 3.9 MB, and most of that is invisible
to a reader: inline scripts, base64 images, style attributes, tracking payloads,
and framework class lists longer than the content they decorate.

The design constraint, and the one thing that separates this from every
article extractor: THE INTERACTIVE SURFACE IS THE CONTENT. Readability,
trafilatura, jusText and their family all solve the opposite problem - they keep
the prose and throw away the controls. Twenty-one of those were surveyed for this
module; ten were rejected for exactly that reason. Here a submit button matters
more than the paragraph next to it.

So there is one invariant, and everything else is negotiable:

    NO INTERACTIVE ELEMENT IS EVER REMOVED.

The relevance score below orders and annotates. It never deletes. That rule is
not stylistic - it was learned three times in one day on the sibling snapshot
code: a character cap returned zero usable elements above the limit, a
signature dedup removed 8.1% of the clickable elements to save 13% of the
weight, and both looked reasonable when written. What shrinks the payload here
is per-FIELD trimming (attribute whitelists, truncated data URIs, dropped class
soup), which measured -7% on the snapshot at exactly zero element loss.
"""
from __future__ import annotations

import re
from typing import Dict, Optional

from selectolax.lexbor import LexborHTMLParser, LexborNode

# selectolax over lxml, decided by measurement rather than reputation: on six
# real pages both parsers found byte-identical sets of interactive elements, so
# correctness did not separate them. What did: selectolax parsed 3-5x faster, it
# is one dependency where lxml needs a second (`cssselect`) for CSS selection,
# and lexbor implements the spec HTML5 parsing algorithm - the same one a
# browser runs, on the same malformed markup.

__all__ = ["clean_page", "clean_stats", "CleanError", "VISIBLE_HTML_JS"]


class CleanError(RuntimeError):
    """Raised when a page cannot be cleaned.

    Deliberately raised rather than swallowed. The obvious fallback - return the
    input unchanged when something goes wrong - hands the caller a payload two
    orders of magnitude larger than it asked for and says nothing, which is a
    failure wearing the costume of a success.
    """


# --- what a page is made of ------------------------------------------------

# Gone entirely, with their contents. None of these carry anything a reader or
# an agent can use, and the first two are usually most of the file.
DROP_WHOLE = (
    "script", "style", "noscript", "template", "link", "meta", "base",
    "canvas", "map", "area", "source", "track", "param",
)

# `<svg>` is NOT in the list above, and that is a measured correction rather
# than an oversight. SVG is a document format: it can hold real `<a>` elements,
# and on one corpus page 105 interactive elements lived inside svg - a fifth of
# the page. Dropping svg wholesale destroyed every one of them.
#
# What is actually heavy in an icon is the geometry, so the geometry is what
# goes; the svg wrapper is then unwrapped and any link inside it survives.
SVG_DRAWING = (
    "path", "defs", "g", "circle", "ellipse", "rect", "polygon", "polyline",
    "line", "use", "mask", "clippath", "filter", "lineargradient",
    "radialgradient", "stop", "pattern", "symbol", "marker", "desc",
    "feGaussianBlur", "feOffset", "feBlend", "feColorMatrix", "animate",
    "animateTransform", "foreignObject",
)

# Gone, but their children stay: pure typographic wrappers that add depth
# without adding meaning.
UNWRAP_ALWAYS = (
    "font", "b", "i", "u", "em", "strong", "small", "big", "center",
    "abbr", "cite", "dfn", "kbd", "samp", "var", "mark", "wbr",
    "figure", "figcaption", "picture", "hgroup",
)

# Structural containers that may be unwrapped when they carry nothing useful.
GENERIC_CONTAINERS = ("div", "span", "section", "article", "aside", "main", "header", "footer")

# Anything a caller can act on. Deliberately wider than the form tags: half the
# buttons on the modern web are a div with a role and a click handler, and a
# list closed to form elements does not look for them at all.
INTERACTIVE_TAGS = ("input", "select", "textarea", "button")
INTERACTIVE_ROLES = frozenset({
    "button", "link", "checkbox", "radio", "tab", "menuitem", "menuitemcheckbox",
    "menuitemradio", "switch", "combobox", "textbox", "searchbox", "slider",
    "spinbutton", "option", "listbox", "treeitem", "gridcell", "columnheader",
})
# Structure that explains the controls: which label belongs to which field.
FORM_STRUCTURE = ("label", "form", "fieldset", "legend", "optgroup", "option", "datalist", "output")

INTERACTIVE_CSS = (
    "a[href],button,input,select,textarea,[onclick],[contenteditable],"
    "[tabindex]:not([tabindex='-1']),[role]"
)

# Attributes worth their bytes. Everything else goes: `class` alone routinely
# runs to a few hundred characters of framework utilities per element.
KEEP_ATTRS = frozenset({
    # handles - how a tool reaches the element again
    "id", "name", "for", "data-testid", "data-test", "data-qa", "data-cy",
    # what it is
    "role", "type", "href", "value", "placeholder", "title", "alt", "action",
    "method", "target", "rel", "lang", "dir",
    # what a screen reader would be told
    "aria-label", "aria-labelledby", "aria-describedby", "aria-expanded",
    "aria-checked", "aria-selected", "aria-current", "aria-invalid",
    "aria-required", "aria-disabled", "aria-hidden", "aria-controls",
    "aria-haspopup", "aria-live", "aria-valuenow", "aria-valuemin", "aria-valuemax",
    # state a model must know before it acts
    "checked", "selected", "disabled", "readonly", "required", "multiple",
    "open", "hidden", "download",
    # input constraints - what the field will accept
    "pattern", "min", "max", "step", "maxlength", "minlength", "accept",
    "autocomplete", "inputmode", "list", "rows", "cols",
    # tables, where structure is the meaning
    "colspan", "rowspan", "headers", "scope",
    # WHAT MAKES AN ELEMENT INTERACTIVE IN THE FIRST PLACE. Leaving these out
    # was the worst defect this module had: a `<div onclick=...>` with the
    # attribute stripped is still on the page but is no longer reachable and no
    # longer recognisable, so the cleaner removed the evidence of interactivity
    # and then measured interactivity. Cost, before it was caught: 46 elements
    # on one corpus page and 117 on another, while every count still looked
    # plausible.
    "onclick", "tabindex", "contenteditable", "draggable",
})

# Attributes kept for their PRESENCE, never their value: an inline handler can
# be a kilobyte of minified JavaScript and none of it means anything here.
EMPTY_VALUE_ATTRS = frozenset({"onclick"})

# `class` is dropped, but not before the state it encodes is rescued. A real
# class attribute reads `mt-4 px-2 flex items-center form-error-message`: three
# hundred bytes of layout around one token that says the field is in error.
STATE_CLASS = re.compile(
    r"(?:^|[-_ ])(error|invalid|required|disabled|readonly|warning|alert|danger"
    r"|success|active|selected|checked|current|open|expanded|collapsed|hidden"
    r"|loading|busy|helper|hint|tooltip|validation)(?:$|[-_ ])",
    re.I,
)

# Long attribute values are truncated - this is the one place a cap is right,
# because it bounds the size of a FIELD and never the number of ELEMENTS. A
# single inline `data:image/png;base64,...` can be larger than the rest of the
# document put together.
MAX_ATTR = 160
MAX_HREF = 220

# Over this many options a `<select>` stops listing them. Not truncated to a
# sample: dropped entirely, with the count kept. Showing the first three of two
# hundred countries does not compress the answer, it replaces it with a wrong
# one - it tells the model the choices are those three. Omitting says "ask me";
# truncating says "these are the choices", and only one of those is true.
MAX_OPTIONS = 25

BLOCK_TAGS = frozenset({
    "p", "div", "section", "article", "header", "footer", "main", "aside", "nav",
    "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "td", "th", "br", "hr",
    "blockquote", "pre", "form", "fieldset", "table", "ul", "ol", "dl", "dt", "dd",
})

_WS = re.compile(r"[ \t\x0b\f\r]+")
_BLANKS = re.compile(r"\n\s*\n\s*\n+")


# --- reading the tree ------------------------------------------------------

def _attrs(node: LexborNode) -> Dict[str, Optional[str]]:
    try:
        return dict(node.attributes)
    except Exception:
        return {}


def _attr(node: LexborNode, name: str) -> str:
    v = _attrs(node).get(name)
    return "" if v is None else v


def _has(node: LexborNode, name: str) -> bool:
    return name in _attrs(node)


def is_interactive(node: LexborNode) -> bool:
    """Whether a caller could act on this element.

    Ordered so the cheap structural checks answer first. `hidden` is not
    consulted here: hiding is decided on the live page, where computed style
    exists, and a string parser guessing at it gets the answer wrong in both
    directions.
    """
    tag = node.tag
    if tag in INTERACTIVE_TAGS:
        return True
    if tag == "a" and _attr(node, "href"):
        return True
    if _attr(node, "role").strip().lower() in INTERACTIVE_ROLES:
        return True
    if _has(node, "onclick"):
        return True
    # `contenteditable` with an empty value means editable, which makes the
    # obvious test - `_attr(...) in ("", "true")` - accept every element that
    # does not carry the attribute at all, because a missing attribute reads
    # back as "" too. That defect made `is_interactive` answer True for
    # anything reaching this line, decorative `role=presentation` icons
    # included, and it went unnoticed because an over-eager detector inflates
    # both sides of a before/after comparison equally. Presence first, value
    # second.
    editable = _attrs(node).get("contenteditable")
    if editable is not None and editable.strip().lower() in ("", "true", "plaintext-only"):
        return True
    if _attr(node, "tabindex").strip() not in ("", "-1"):
        return True
    if tag in FORM_STRUCTURE:
        return True
    return False


def relevance(node: LexborNode) -> int:
    """How much a model is likely to need this element.

    Used to ORDER and to decide how much surrounding text to keep. Never to
    delete: see the invariant at the top of the module.

    The signs here are worth reading against the version this replaces, where
    they ran the other way. A submit button scored -10 and a cookie banner -15,
    which inverts what an agent actually needs: the submit button is the one
    that finishes the task, and the cookie banner is the modal standing between
    the agent and the whole page. Measured on the sibling snapshot code, missing
    the element that blocks the viewport is not a local failure, it is a
    terminal one - the agent cannot see why nothing it clicks responds.
    """
    score = 0
    tag = node.tag
    if tag in ("input", "select", "textarea"):
        score += 15
    elif tag == "button":
        score += 12
    elif tag == "a":
        score += 8
    elif tag == "label":
        score += 6
    elif tag in ("form", "fieldset", "legend"):
        score += 10

    if _attr(node, "name"):
        score += 8
    if _attr(node, "id"):
        score += 4
    if _attr(node, "placeholder") or _attr(node, "aria-label") or _attr(node, "title"):
        score += 5
    if _has(node, "required") or _attr(node, "aria-required") == "true":
        score += 8

    text = (node.text(deep=True) or "").strip().lower()
    label = (_attr(node, "aria-label") + " " + _attr(node, "value") + " " + text).lower()

    # The button that finishes the job. Positive, and by a wide margin.
    if re.search(r"\b(submit|send|continue|next|save|upload|apply|confirm|pay|"
                 r"checkout|search|sign in|log in|accept|agree|invia|continua|"
                 r"salva|cerca|accetta|avanti)\b", label):
        score += 20

    # An error message is the single most informative thing on a form that just
    # rejected something, and it is what tells the agent what to change.
    if (_attr(node, "aria-invalid") == "true"
            or _attr(node, "role") in ("alert", "alertdialog", "status")
            or re.search(r"error|invalid|required", _attr(node, "class"), re.I)):
        score += 50

    # A blocking overlay outranks the page behind it: until it is dismissed,
    # nothing else on the page can be reached at all.
    if re.search(r"\b(cookie|consent|gdpr|dismiss|close|accetta|chiudi)\b", label):
        score += 15
    return score


# --- phase 1: noise --------------------------------------------------------

def _drop_noise(tree: LexborHTMLParser) -> None:
    for tag in DROP_WHOLE:
        for node in tree.css(tag):
            node.decompose()
    # Icons: the drawing goes, the wrapper is unwrapped, anything clickable
    # inside it stays where it was.
    for tag in SVG_DRAWING:
        for node in tree.css("svg " + tag):
            node.decompose()
    # unwrap_tags, NOT strip_tags. In selectolax `strip_tags` deletes the tag
    # WITH its contents, and `unwrap_tags` is the one that keeps the children
    # and drops only the wrapper. Getting that backwards deleted the text inside
    # every <b>, <em> and <strong> on the page - invisibly, because an element
    # count keyed on tag and id cannot see a missing word.
    try:
        tree.unwrap_tags(list(UNWRAP_ALWAYS) + ["svg"])
    except Exception as exc:
        raise CleanError(f"the tree could not be flattened: {exc}") from exc


def _drop_inline_hidden(tree: LexborHTMLParser) -> None:
    """Remove what the markup itself says is hidden.

    Only what a STRING can prove: an inline `display:none`, `visibility:hidden`,
    a `hidden` attribute, `aria-hidden`. Anything hidden by a stylesheet is
    invisible to this pass by construction, which is why `VISIBLE_HTML_JS` below
    exists - on a live page the question has a real answer.
    """
    # `aria-hidden` is NOT in this query, and that is the correction that matters
    # here. It means "do not announce this to a screen reader", not "do not
    # paint it" - a link carrying its own aria-label routinely marks its VISIBLE
    # caption aria-hidden so the name is not read twice. Treating the two as the
    # same thing deleted the only label several links had, leaving the model an
    # anonymous destination it could see no reason to click.
    for node in tree.css("[style],[hidden]"):
        style = _attr(node, "style").replace(" ", "").lower()
        hidden = (
            "display:none" in style
            or "visibility:hidden" in style
            or "opacity:0;" in style
            or _has(node, "hidden")
        )
        if not hidden:
            continue
        # An interactive element inside is a reason to keep the container: a
        # menu marked aria-hidden while collapsed still holds real controls,
        # and the live-page pass is what decides visibility properly.
        if holds_interactive(node):
            continue
        node.decompose()


def _slim_attributes(tree: LexborHTMLParser) -> None:
    for node in tree.css("*"):
        attrs = _attrs(node)
        if not attrs:
            continue
        state = ""
        cls = attrs.get("class") or ""
        if cls:
            hits = [t for t in cls.split() if STATE_CLASS.search(t)]
            state = " ".join(hits[:3])
        for name, value in list(attrs.items()):
            if name not in KEEP_ATTRS:
                del node.attrs[name]
                continue
            if value is None:
                continue
            if name in EMPTY_VALUE_ATTRS:
                node.attrs[name] = ""
            elif name == "href":
                node.attrs[name] = _trim_href(value)
            elif len(value) > MAX_ATTR:
                node.attrs[name] = value[:MAX_ATTR] + "..."
        if state:
            node.attrs["class"] = state


def _trim_href(href: str) -> str:
    """Keep the part that identifies the destination, drop the part that does not.

    Measured on the sibling snapshot: href was 36% of the whole payload, with a
    median of 42 characters but a tail reaching 338, and 27% carrying a query
    string. Tracking parameters are most of that tail and none of the meaning.
    """
    href = href.strip()
    if not href or href == "#" or href.lower().startswith(("javascript:", "data:")):
        return "#"
    if len(href) <= MAX_HREF:
        return href
    base, _, query = href.partition("?")
    if len(base) <= MAX_HREF:
        return base + ("?..." if query else "")
    return base[:MAX_HREF] + "..."


def _collapse_options(tree: LexborHTMLParser) -> None:
    for select in tree.css("select"):
        options = select.css("option")
        if len(options) <= MAX_OPTIONS:
            continue
        # Tested by attribute, never by comparing nodes. selectolax compares
        # nodes by CONTENT: two `<option>X</option>` are `==`, so a membership
        # test against a list of the selected ones keeps every option that
        # happens to share text with a selected one. Asking each option about
        # itself has no such failure mode, and is not quadratic either.
        for opt in options:
            if not _has(opt, "selected"):
                opt.decompose()
        select.attrs["data-option-count"] = str(len(options))


def _unwrap_pointless_wrappers(tree: LexborHTMLParser) -> None:
    """Collapse containers that exist only to hold one other container.

    Found by an edge case rather than by reading: 500 nested `<div>` around a
    single button survived as 5,560 characters, because every ancestor of an
    interactive element is kept and nothing asked whether the ancestor said
    anything. Real pages do not nest 500 deep, but they nest twenty, and twenty
    empty wrappers per control is most of what is left after the noise goes.

    The condition is deliberately narrow, so this cannot become another way of
    losing things: no attributes at all (so nothing to lose - `class` has
    already been reduced to the state it encoded, and an element still carrying
    one is left alone), exactly one element child, and no text of its own. Such
    an element is information-free by construction rather than by judgement.
    """
    for _ in range(6):
        removed = 0
        for node in tree.css(",".join(GENERIC_CONTAINERS)):
            if node.attributes:
                continue
            children = [c for c in node.iter(include_text=False)]
            if len(children) != 1:
                continue
            # Its own text, not its descendants': a wrapper with a caption
            # beside the child is not a pointless wrapper.
            own = (node.text(deep=False) or "").strip()
            if own:
                continue
            try:
                node.unwrap()
                removed += 1
            except Exception:
                pass
        if not removed:
            break


def _drop_empty(tree: LexborHTMLParser) -> None:
    for _ in range(3):
        removed = 0
        for node in tree.css(",".join(GENERIC_CONTAINERS)):
            if node.attributes:
                continue
            if (node.text(deep=True) or "").strip():
                continue
            if node.css(INTERACTIVE_CSS + ",img,iframe,input"):
                continue
            node.decompose()
            removed += 1
        if not removed:
            break


# --- phase 2: the form surface ---------------------------------------------

def holds_interactive(node: LexborNode) -> bool:
    """Whether anything inside this subtree can be acted on.

    This replaces an ancestor set keyed on `id(node)`, which was INERT: a
    selectolax node is a fresh Python wrapper on every traversal, so `id()`
    differs between two walks of the same tree and the membership test was
    always false. Nothing failed loudly - the pruning step simply protected
    nothing, and reported +0 elements removed while another phase did the
    damage.

    The repair is not a stable key. It is removing the second answer: the tree
    already knows what it contains, and asking it costs one query.
    """
    if is_interactive(node):
        return True
    return any(is_interactive(d) for d in node.css(INTERACTIVE_CSS))


# There was a `_shorten_prose` here, and it was removed rather than repaired.
# It marked every prose block over 400 characters with the number of characters
# it had "cut" - and cut nothing, so it only ever ADDED bytes. Worse, the phase
# right below already decides the fate of exactly those blocks and DELETES them,
# so two phases were ruling on the same question and one of them was mute. The
# docstring meanwhile said "the text is shortened, not discarded", describing
# behaviour the code did not have.

MAX_LABEL_CHARS = 200


def _prune_to_scaffold(tree: LexborHTMLParser) -> None:
    """Drop what is neither interactive, nor holding something interactive, nor
    short text sitting close enough to a control to explain it.

    Top-down, and a subtree that survives is descended into rather than trusted
    wholesale. Removing a branch takes its children with it, which is safe here
    precisely because a branch is only removed once it is known to hold nothing
    interactive - so its children hold nothing either.
    """
    body = tree.body
    if body is None:
        return

    def walk(node: LexborNode) -> None:
        for child in list(node.iter(include_text=False)):
            if child.tag in ("html", "body", "head"):
                walk(child)
                continue
            if holds_interactive(child):
                walk(child)
                continue
            text = (child.text(deep=True) or "").strip()
            # Short nearby text is what turns `<input name=q>` into a field a
            # model can reason about, so it stays even with nothing clickable.
            if text and len(text) <= MAX_LABEL_CHARS:
                continue
            try:
                child.decompose()
            except Exception:
                pass

    walk(body)


# --- text mode -------------------------------------------------------------

def _to_text(tree: LexborHTMLParser) -> str:
    body = tree.body or tree.root
    if body is None:
        return ""
    raw = body.text(deep=True, separator="\n", strip=False) or ""
    lines = [_WS.sub(" ", ln).strip() for ln in raw.splitlines()]
    return _BLANKS.sub("\n\n", "\n".join(ln for ln in lines if ln)).strip()


# --- the live page ---------------------------------------------------------

VISIBLE_HTML_JS = """() => {
    // The HTML of the page with everything the browser is not painting removed.
    //
    // The whole point is the CLONE. Visibility is a computed property - it comes
    // from stylesheets, inherited rules, layout - and a string parser cannot see
    // any of it, so the decision has to happen here. But writing to the live DOM
    // is not allowed in this product: mutating the page a detector can read is
    // exactly the surface it exists not to have.
    //
    // A clone resolves both. The live tree is only ever read, and every removal
    // lands on a detached copy nobody can observe.
    const clone = document.documentElement.cloneNode(true);
    const live = document.documentElement.querySelectorAll('*');
    const copy = clone.querySelectorAll('*');
    // cloneNode preserves document order, so the two lists index the same nodes.
    const doomed = [];
    for (let i = 0; i < live.length && i < copy.length; i++) {
        const el = live[i];
        // Wrapped, because a page can shadow or replace either of these methods
        // and this loop walks EVERY element in the document: one failure would
        // otherwise take the whole read with it, and browser_read_html would
        // return an error where a page was asked for.
        //
        // Failure means KEEP, which is the opposite of what the snapshot does
        // with the same uncertainty, and deliberately so. This function decides
        // what to DELETE from a copy, so "I could not tell" has to mean "leave
        // it alone"; the snapshot decides what to REPORT, where the same answer
        // means "do not claim it is there". Both directions preserve rather
        // than destroy.
        let s = null, r = null;
        try { s = getComputedStyle(el); r = el.getBoundingClientRect(); } catch (err) { continue; }
        if (!s || !r || typeof r.width !== 'number') continue;
        if (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity) === 0) {
            doomed.push(copy[i]);
            continue;
        }
        // Zero-area is not enough on its own: a wrapper can have no box while
        // its children are painted, so only strip it when nothing is inside.
        if (r.width <= 0 && r.height <= 0 && el.children.length === 0
            && !el.textContent.trim()) {
            doomed.push(copy[i]);
        }
    }
    for (const el of doomed) { if (el.parentNode) el.parentNode.removeChild(el); }
    return clone.outerHTML;
}"""


# --- the entry point -------------------------------------------------------

def clean_page(html: str, mode: str = "form") -> str:
    """Return `html` reduced to what a model needs.

    mode="form"  the interactive surface plus the text that explains it
    mode="text"  the prose, with the markup gone
    mode="full"  noise removed and attributes slimmed, structure otherwise kept
    """
    if not html or not html.strip():
        return ""
    if mode not in ("form", "text", "full"):
        raise CleanError(f"unknown mode {mode!r}; expected form, text or full")

    try:
        tree = LexborHTMLParser(html)
    except Exception as exc:
        raise CleanError(f"the page could not be parsed: {exc}") from exc

    _drop_noise(tree)
    _drop_inline_hidden(tree)

    if mode == "text":
        # Nothing above this point touches prose, which is the whole reason the
        # split sits here rather than after the shared cleanup.
        return _to_text(tree)

    _slim_attributes(tree)
    _collapse_options(tree)

    if mode == "form":
        _prune_to_scaffold(tree)

    _unwrap_pointless_wrappers(tree)
    _drop_empty(tree)

    out = tree.html or ""
    return _BLANKS.sub("\n\n", out).strip()


def clean_stats(before: str, after: str) -> Dict[str, float]:
    """What the cleaning cost and what it saved.

    `tokens_*` are ESTIMATES at four characters each, and the estimate is worst
    exactly where it is used - JSON and long URLs tokenize far denser than prose.
    Reported as an order of magnitude, not a number to plan against.

    And a reduction figure alone says nothing about whether the result is still
    usable: pair it with how many elements survived, measured on the same page.
    The most attractive -13% of the day cost 8.1% of the clickable elements.
    """
    a, b = len(before), len(after)
    return {
        "chars_before": a,
        "chars_after": b,
        "chars_removed": a - b,
        "reduction_pct": round(100.0 * (a - b) / a, 1) if a else 0.0,
        "tokens_before_est": a // 4,
        "tokens_after_est": b // 4,
        "tokens_saved_est": (a - b) // 4,
    }
