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
import time
from pathlib import Path
from typing import Dict, Optional

from ..storage import (DEFAULT_SESSION_ID, erase as _erase, file_for,
                       read_json, write_atomically)


#: The piece of work a caller that names none is in, and so the file it
#: persists to.
#:
#: ⛔ ONE DECLARATION, BECAUSE TWO OF THEM CANNOT BE HELD TOGETHER BY A TEST
#: THAT COMPARES ONE OF THEM TO A LITERAL. This lived in `registry.py` as
#: `DEFAULT_SESSION_ID` while `chat.py` declared `DEFAULT_CHAT_ID = "default"`
#: beside it, with a comment saying the two had to match. What guarded that was
#: an assertion reading `DEFAULT_CHAT_ID == "default"` - a literal, not the
#: other constant - so moving the server's default would have left the
#: interface and the server addressing two different files while the test that
#: names the invariant stayed green.
#:
#: It belongs here rather than in the registry: the registry keys BROWSERS, and
#: this names a piece of WORK, which is to say a file in this directory. The
#: registry never needed it except as a default argument no caller used.
#: Re-exported: the constant itself lives in `invisible_playwright_mcp.storage`, because the
#: interface's half needs the same value and a second literal is how the two
#: halves would quietly start naming different pieces of work.
_ = DEFAULT_SESSION_ID  # re-exported for callers that import it from here


#: The directory this half of a session lives in. The only thing the two halves
#: do not share, which is why it is the only thing named here.
KIND = "sessions"


def path_of(session_id: str) -> Path:
    return file_for(KIND, session_id)


def save(session_id: str, browsers: Dict[str, dict],
         focus: Optional[str] = None) -> Path:
    """Write one session down. Returns where it went.

    How it reaches the disk - bytes rather than text, and a temporary
    neighbour moved into place so a process that dies mid-write leaves the
    previous session intact - is in `storage.write_atomically`, which is where
    that decision lives for both halves of a session. It is not repeated here:
    written twice it would be two accounts of one rule, free to disagree.

    ⛔ AND IT WAS REPEATED HERE, which is worth saying rather than quietly
    deleting. This docstring carried the bytes-not-text rule in full while the
    function DELEGATES it - so the rule was written where it is not applied,
    and a reader fixing it here would have changed nothing. `load` below had
    it right about the same file, five lines down, and the module that owns
    the rule opens by saying that two copies is the arrangement where a fix
    reaches one of them. Found 2026-09-15 by a scan for prose repeated across
    modules, not by reading.
    """
    where = path_of(session_id)
    payload = {
        "id": session_id,
        # ⛔ `name` STOOD HERE AND WAS ALWAYS `id`. It was kept on the argument
        # that an older build rolled back onto this directory would expect it -
        # and no build ever read it: its one reader was `known()`, which went
        # with the `session_list` tool when MCP stopped having a session
        # concept. A field that is a copy of the field above it, that nothing
        # reads, is the same thing `running` and `limit` were one layer up.
        # Files already on disk still carry it; `load` hands back what it
        # finds and `remembered()` reads two keys, so an old file is read by a
        # new build exactly as it was.
        "saved": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "focus": focus,
        "browsers": browsers,
    }
    blob = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    write_atomically(where, blob)
    return where


def load(session_id: str) -> Optional[dict]:
    """One session as it was written, or None if there is nothing to read.

    Why an unparsable file answers None rather than raising is in
    `storage.read_json`, which is where that decision lives for both halves
    of a session. It is not repeated here: written twice it would be two
    accounts of one rule, free to disagree.
    """
    return read_json(path_of(session_id))


# ⛔ `known()` STOOD HERE, listing every saved session newest first. Its only
# caller was the `session_list` tool, and that tool was removed when MCP
# stopped having a session concept: enumerating pieces of work other than this
# process's own is precisely the capability that went. Nothing else ever
# globbed this directory - the interface lists CONVERSATIONS, through
# `known_chats` below.


def erase(session_id: str) -> None:
    """Forget a saved session."""
    _erase(path_of(session_id))
