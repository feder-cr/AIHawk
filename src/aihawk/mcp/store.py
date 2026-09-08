"""What a session is, written down so it survives the process.

A session is the piece of work: it owns browsers, and each browser owns tabs.
Until this file existed all three lived in dictionaries that died with the
server, so "reopen the session I was working in" meant nothing.

⛔ WHAT IS PROMISED, AND WHAT IS NOT. What is saved is the DECLARATION: which
browsers a session has, who each one is (seed, exit, profile), which one had the
focus, and where its tabs were pointing. Reopening restores that declaration -
not eight live browsers. Eight of those were measured at 61 processes and about
6.5 GB, with the eighth taking 13.6 s to start, so a reopen that launched them
all would take a minute and most of the machine's memory to give back something
nobody asked for yet. They start when a command is aimed at one, as the right
person, because the identity was written down.

Cookies and logins survive only where a browser had a `profile` directory, which
is the mechanism that already exists for exactly that. Saying otherwise would be
promising that a browser's live state is a thing this file can hold, and it is
not.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional


def home() -> Path:
    """Where sessions are kept.

    `AIHAWK_HOME` wins, which is what the tests use and what lets somebody put
    this on another disk. Otherwise the place each system expects, so a person
    finds it where they would look for it rather than in a dotfile invented
    here.
    """
    override = os.environ.get("AIHAWK_HOME")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        return Path(base) / "aihawk"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "aihawk"
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "aihawk"


def _sessions_dir() -> Path:
    return home() / "sessions"


def _safe(session_id: str) -> str:
    """A session id as a file name, without letting one escape the directory.

    Ids reach this from a tool argument, so a caller could send `../../etc` or a
    colon that Windows refuses. Anything outside the allowed set becomes an
    underscore rather than being rejected: a session should not become
    unreachable because of the name somebody gave it.
    """
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    cleaned = "".join(c if c in allowed else "_" for c in session_id)
    return cleaned[:120] or "_"


def path_of(session_id: str) -> Path:
    return _sessions_dir() / ("%s.json" % _safe(session_id))


def save(session_id: str, browsers: Dict[str, dict],
         focus: Optional[str] = None, name: Optional[str] = None) -> Path:
    """Write one session down. Returns where it went.

    ⛔ `write_bytes`, never `write_text`. On Windows the text form translates
    every newline on the way out, which in this project has already turned a
    twenty-line change into a fifteen-thousand-line one. JSON does not care, but
    the habit is what keeps the next file that does care safe.

    Written to a temporary neighbour and moved into place, so a process that
    dies mid-write leaves the previous session intact rather than half of a new
    one. A session file that will not parse is worse than an old one.
    """
    where = path_of(session_id)
    where.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": session_id,
        "name": name or session_id,
        "saved": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "focus": focus,
        "browsers": browsers,
    }
    blob = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    beside = where.with_suffix(".json.writing")
    beside.write_bytes(blob)
    os.replace(beside, where)
    return where


def load(session_id: str) -> Optional[dict]:
    """One session as it was written, or None if there is nothing to read.

    A file that will not parse answers None as well. The alternative is raising
    on a server's first call because something once wrote a broken byte, and a
    session that cannot be read is exactly as usable as one that was never
    saved.
    """
    where = path_of(session_id)
    try:
        return json.loads(where.read_bytes().decode("utf-8"))
    except Exception:
        return None


def known() -> List[dict]:
    """Every saved session, newest first, without opening a browser."""
    out = []
    try:
        files = sorted(_sessions_dir().glob("*.json"))
    except Exception:
        return out
    for f in files:
        try:
            out.append(json.loads(f.read_bytes().decode("utf-8")))
        except Exception:
            continue
    out.sort(key=lambda s: s.get("saved") or "", reverse=True)
    return out


def erase(session_id: str) -> bool:
    """Forget a saved session. Answers whether there was one."""
    where = path_of(session_id)
    try:
        where.unlink()
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
