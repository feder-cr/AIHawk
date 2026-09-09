"""Turn a tool call into one readable line.

The difference between a step list somebody watches and a wall of JSON. The raw
arguments are already in the transcript the model sees; what the person on the
left needs is the target, in the shortest form that still identifies it.

Deliberately total: an unknown tool renders its arguments rather than raising or
printing nothing, because a new tool in the server must never make the UI go
quiet about what it just did.
"""
from __future__ import annotations


def _short(value, limit: int = 60) -> str:
    text = value if isinstance(value, str) else repr(value)
    text = " ".join(text.split())
    # "..." and not the single ellipsis character: these lines end up in a
    # terminal as often as in the page, and the Windows console is cp1252, where
    # one non-ASCII character in a print kills the process after the work is done.
    return text if len(text) <= limit else text[: limit - 3] + "..."


#: Anything that looks like it was typed once and must not be read twice. The
#: transcript is drawn on screen AND written to disk, so a password echoed here
#: outlives the session it was typed into.
SECRET = ("password", "passcode", "passwd", "otp", "2fa", "code", "token",
          "secret", "cvv", "pin")


def _looks_secret(selector: str) -> bool:
    low = (selector or "").lower()
    return any(word in low for word in SECRET)


def _mask(text: str) -> str:
    # ASCII only, deliberately: these lines are printed to a terminal as well as
    # drawn on the page, and one non-ASCII character in a print kills the process
    # on a cp1252 console after all the work is done.
    return "hidden, %d characters" % len(text)


def summarise(name: str, args: dict | None) -> str:
    """One line for one call. `where` names the browser only when the CALL did:
    a session holding eight browsers turns 25 steps into 25 identical lines
    otherwise, and inventing a default would say more than the call said.
    """
    args = args or {}
    where = ""
    if name.startswith("browser_") and name != "browser_open" and args.get("browser_id"):
        where = " in %s" % _short(args["browser_id"], 24)

    if name == "browser_open":
        return _short(args.get("browser_id") or "", 40)
    if name == "browser_navigate":
        return _short(args.get("url", ""), 80) + where
    if name in ("browser_click",):
        return _short(args.get("selector", "")) + where
    if name == "browser_click_at":
        hold = args.get("hold_seconds") or 0
        at = "%s,%s" % (args.get("x"), args.get("y"))
        return at + (" hold %ss" % hold if hold else "") + where
    if name == "browser_type":
        # ⛔ A PASSWORD IS NOT A STEP DESCRIPTION. `Typed #passcode-input <-
        # 434262` was on screen and in the saved transcript: the line that exists
        # so a person can follow along was also the line that kept the secret.
        selector = args.get("selector", "")
        typed = args.get("text", "") or ""
        shown = _mask(typed) if _looks_secret(selector) else _short(typed, 40)
        return "%s <- %s%s" % (_short(selector, 40), shown, where)
    if name == "browser_press_key":
        return _short(args.get("key", ""), 20)
    if name == "browser_read_text":
        return _short(args.get("selector", "body")) + where
    if name == "browser_read_html":
        return "mode=%s" % _short(args.get("mode", "form"), 20) + where
    if name == "browser_evaluate":
        return _short(args.get("expression", ""), 70)
    if name in ("session_select_page", "session_close_page"):
        return _short(args.get("page_id", ""), 40)
    if name in ("browser_snapshot", "browser_take_screenshot",
                "session_new_page", "session_list_pages"):
        return where.strip()

    if not args:
        return ""
    return _short(", ".join("%s=%s" % (k, v) for k, v in args.items()), 70)
