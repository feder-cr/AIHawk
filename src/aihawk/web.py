"""The interface: the page, the conversations behind it, and the routes.

⛔ THIS MODULE WAS 3370 LINES AND IS NOW A DOOR. It held three languages inside
one string and three unrelated jobs beside it: a stylesheet, a script, the
markup, one conversation, the registry of all of them, and every route. Every
change to any of those had to walk through all of the others.

The parts live where they belong now - `ui/` for the three files the browser
gets, `chat.py` for a conversation, `sessions.py` for the registry, `routes.py`
for the HTTP surface - and every one of them is re-exported from here, because
this is where the product, the tests and the gates have always imported them
from. Moving where something LIVES is not a reason to move where it is FOUND,
and a refactor that makes callers change is not free the way this one is.

⛔ AND THE PAGE CAME OUT BYTE FOR BYTE. That was checked against the old string
rather than argued about: the dozens of gates that read `PAGE` as text kept
passing untouched, which is the only reason a move this size was safe to make in
one commit.

One class of bug went with the split and is worth naming: the script used to
live in a raw Python literal, so every backslash in a regular expression was one
mistake away from being read by Python instead of by the browser. A `.js` file
has no such reading.
"""
from __future__ import annotations

from .chat import DEFAULT_CHAT_ID, UNNAMED, ChatService
from .routes import build_app
from .sessions import SessionGone, Sessions
from .ui import PAGE

__all__ = [
    "PAGE",
    "DEFAULT_CHAT_ID",
    "UNNAMED",
    "ChatService",
    "Sessions",
    "SessionGone",
    "build_app",
]
