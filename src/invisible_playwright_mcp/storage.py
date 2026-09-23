"""The things both halves of a session need to write themselves down.

A session is kept in two files by two programs: the browsers by the MCP
server (`invisible_playwright_mcp.mcp.store`) and the conversation by the interface
(`invisible_playwright_mcp.chats`). They must agree about WHERE the data lives and about HOW an
id becomes a file name, or the join between them breaks; and they must both
replace a file without ever leaving a half-written one behind.

⛔ THOSE THINGS WERE WRITTEN TWICE. `home()` and the id sanitiser lived in the
server's module and the interface reached into it to borrow them, which is how
the interface's persistence came to live inside the MCP package at all. The
atomic write was copied outright: four lines, in both files, with only one of
the two carrying the comment explaining why it has to be `write_bytes`. Two
copies of one rule is the arrangement where a fix reaches one of them.

⛔ AND READING WAS STILL WRITTEN TWICE UNTIL 0.56.0, which the first pass
missed because it was looking for duplicated VALUES rather than a duplicated
RULE. `store.load` and `chats.load_chat` were the same four lines with a
different path, and what they carry is not a value at all: it is the decision
that a file which will not parse is exactly as usable as one that was never
saved. Deleting was the same again. Both now live here, once.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

from . import env as environment
from .quiet import swallow

#: The id of the session a process serves when nobody names one.
#:
#: It lives here rather than in either half because both halves need it to
#: mean the same thing: the interface's default conversation and the server's
#: default browser file are the same piece of work, and a second literal is
#: how they would quietly become two.
DEFAULT_SESSION_ID = "default"


#: The directory this package keeps sessions in, under the place each system
#: expects. `RETIRED_DIRECTORY` is what it was called until 2026-09-23, and
#: `carry_over_the_old_directory` is what stops that rename from being data loss.
DIRECTORY = "invisible-playwright-mcp"
RETIRED_DIRECTORY = "aihawk"


def _base() -> Path:
    """The system directory applications keep their data under."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))


def home() -> Path:
    """Where sessions are kept.

    `INVISIBLE_MCP_HOME` wins, which is what the tests use and what lets
    somebody put this on another disk. Otherwise the place each system expects,
    so a person finds it where they would look for it rather than in a dotfile
    invented here.

    ⛔ IT IS A PURE FUNCTION AND IT MOVES NOTHING. Every part of the product
    calls it, several times per request, and the rename below needs a decision
    about somebody's data: that belongs at a startup edge that runs once and can
    say what it did, not inside the answer to "where is the directory".
    """
    override = environment.read(environment.HOME)
    if override:
        return Path(override).expanduser()
    return _base() / DIRECTORY


def carry_over_the_old_directory() -> Optional[Path]:
    """Move the sessions of the old name onto the new one, once. Says where to.

    ⛔ WITHOUT THIS, RENAMING THE DIRECTORY IS DATA LOSS AND NOTHING PRINTS. It
    holds the profiles, the logins and the saved conversations of everybody who
    installed the old name. Changing the literal does not move them: it points
    the process at somewhere empty, so an upgrade reads as all of it having
    vanished. The package, the command and the module were renamed on
    2026-09-23 and this was deliberately NOT, on that reasoning; the owner then
    asked for the old name to be abandoned outright, and carrying the data is
    what makes those two things compatible.

    Three cases, and only the first touches anything:

    * the new directory is absent and the old one is there: renamed onto the new
      name. One `os.replace` of the directory itself, inside one parent, so
      there is no copy to be interrupted half way and no merge to get wrong.
    * both are there: nothing. The new one is the live one, and folding an older
      tree into it would have to decide which copy of a session wins - a
      decision with no right answer that nobody asked for.
    * the override is set: nothing. The caller pointed somewhere explicitly, and
      moving a directory they did not name is not this function's business.

    Returns the directory that was moved onto, or None when nothing was.
    """
    if environment.read(environment.HOME):
        return None
    new = _base() / DIRECTORY
    old = _base() / RETIRED_DIRECTORY
    if new.exists() or not old.is_dir():
        return None
    with swallow("a directory that will not move is not worth refusing to start "
                 "over: the sessions stay readable under the old name, and the "
                 "next run tries again"):
        os.replace(old, new)
        return new
    return None


def safe_name(session_id: str) -> str:
    """A session id as a file name, without letting one escape the directory.

    A caller could send `../../etc` or a colon that Windows refuses. Anything
    outside the allowed set becomes an underscore rather than being rejected: a
    session should not become unreachable because of the name somebody gave it.
    """
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    cleaned = "".join(c if c in allowed else "_" for c in session_id)
    return cleaned[:120] or "_"


def file_for(kind: str, session_id: str) -> Path:
    """Where one half of a session lives: `<home>/<kind>/<safe id>.json`.

    ⛔ THE LAST PIECE OF THIS RULE WAS STILL WRITTEN TWICE. This module's own
    docstring says `home()` and the id sanitiser were pulled out of the server's
    package because the interface was reaching in to borrow them, and that
    reading, writing and erasing followed. The SHAPE did not: `chats.chat_path`
    and `store.path_of` each kept their own copy of "join the home, the
    directory and the id, and put .json on the end".

    Two copies of one rule is the arrangement this file exists to end, and the
    cost was visible from outside it: `Sessions.knows` has to ask whether a
    session exists on disk, and had to call two differently-named functions to
    ask one question about one id.

    `kind` is the directory, which is the only thing the two halves do not
    share - `chats` for the conversation, `sessions` for the browsers.
    """
    return home() / kind / ("%s.json" % safe_name(session_id))


def write_atomically(where: Path, blob: bytes) -> None:
    """Replace a file with these bytes, or leave the old one untouched.

    Written beside the target and moved onto it, because the reader is another
    program: a plain write that is interrupted, or read while it is happening,
    hands somebody half a JSON document and loses what was there.

    ⛔ `write_bytes`, never `write_text`. On Windows the text form translates
    every newline on the way out, so a file written here and compared
    elsewhere differs by bytes nobody wrote.
    """
    where.parent.mkdir(parents=True, exist_ok=True)
    beside = where.with_suffix(where.suffix + ".writing")
    beside.write_bytes(blob)
    os.replace(beside, where)


def read_json(where: Path) -> Optional[dict]:
    """What that file holds, or None if there is nothing to read.

    A file that will not parse answers None as well, and that is the decision
    rather than a shortcut: the alternative is raising on a server's first
    call because something once wrote a broken byte, and a saved thing that
    cannot be read is exactly as usable as one that was never saved.

    Written here rather than in each half, because it is a RULE and not a
    value - and a rule copied into two files is a rule that gets changed in
    one of them.
    """
    try:
        return json.loads(where.read_bytes().decode("utf-8"))
    except Exception:
        return None


def erase(where: Path) -> None:
    """Delete that file, if it is there.

    ⛔ IT ANSWERS NOTHING, WHERE BOTH COPIES ANSWERED A BOOL NOBODY READ. The
    two callers threw it away, and the value was ambiguous on top of being
    unread: `False` meant "there was nothing to delete" and "it could not be
    deleted", which are opposite news. `Sessions.forget` has the same defect
    written into its own docstring, from the day it answered `False` for a
    session somebody else had already deleted and the page said it was still
    working. A caller that needs to know whether a file was there asks before,
    and nothing here does.
    """
    with swallow("a file that is not there is already erased, and one that "
                 "will not go is not news to anybody who asked for it to go"):
        where.unlink()
