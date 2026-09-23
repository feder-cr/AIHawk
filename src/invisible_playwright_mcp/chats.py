"""Where a CONVERSATION is written down, which is the interface's half.

⛔ THIS LIVED IN `invisible_playwright_mcp.mcp.store` UNTIL 2026-09-13, AND NOTHING INSIDE THAT
PACKAGE EVER CALLED IT. Every caller of `save_chat`, `load_chat`,
`known_chats` and `erase_chat` was `chat.py` or `sessions.py`, which are the
interface. A module of the MCP server owned the interface's persistence, so
"what belongs to the protocol" and "what belongs to our product" could not be
told apart by reading the tree - the question this file exists to answer.

What did NOT move is the pairing itself, which is deliberate and is explained
where the browsers are written: the browsers are written by the MCP SERVER and
a conversation by the INTERFACE, which is a separate program reaching it over
stdio. One file with two writers is a race that costs somebody their
transcript on the day two writes land together, and neither process can take a
lock the other sees. So the session id is the join key, each writer owns its
own file, and the two live in separate directories.

The primitives both halves need - where the data lives, how an id becomes a
file name, how a file is replaced without a torn read - are in
`invisible_playwright_mcp.storage`, imported by both and duplicated by neither.

What is saved is the transcript as the PAGE draws it plus the transcript as the
MODEL holds it. Saving only the first would give somebody back a conversation
they can read and cannot continue: the follow-up box would still be there,
meaning nothing.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Optional

from .storage import erase as _erase, file_for, home, read_json, write_atomically

#: The directory this half of a session lives in. The only thing the two halves
#: do not share, which is why it is the only thing named here.
KIND = "chats"


def chat_path(session_id: str) -> Path:
    return file_for(KIND, session_id)


def save_chat(session_id: str, name: str, history: List[dict],
              messages: List[dict], usage: Optional[dict] = None) -> Path:
    """Write one conversation down. Returns where it went."""
    where = chat_path(session_id)
    payload = {
        "id": session_id,
        "name": name,
        "saved": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "history": history,
        "messages": messages,
        "usage": usage or {},
    }
    blob = json.dumps(payload, indent=2).encode("utf-8")
    write_atomically(where, blob)
    return where


def load_chat(session_id: str) -> Optional[dict]:
    """One conversation as it was written, or None if there is nothing to read."""
    return read_json(chat_path(session_id))


def known_chats() -> List[dict]:
    """Every saved conversation, newest first, WITHOUT its transcript.

    The list is drawn every time somebody opens the page, and a session that has
    been worked in all afternoon holds a transcript of thousands of lines.
    Reading them all to show a column of names would make the cheapest thing the
    interface does the most expensive.
    """
    out: List[dict] = []
    try:
        files = sorted((home() / KIND).glob("*.json"))
    except Exception:
        return out
    for f in files:
        try:
            d = json.loads(f.read_bytes().decode("utf-8"))
        except Exception:
            continue
        out.append({"id": d.get("id") or f.stem,
                    "name": d.get("name") or d.get("id") or f.stem,
                    "saved": d.get("saved") or "",
                    "turns": sum(1 for e in (d.get("history") or [])
                                 if e.get("kind") == "you")})
    out.sort(key=lambda s: s.get("saved") or "", reverse=True)
    return out


def erase_chat(session_id: str) -> None:
    """Forget a saved conversation."""
    _erase(chat_path(session_id))
