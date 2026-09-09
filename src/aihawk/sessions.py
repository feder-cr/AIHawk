"""Every conversation this interface holds, and the way in to one.

Split out of `web.py` on 2026-09-10. The classes are the same bytes they were.
"""
from __future__ import annotations

import time
from typing import Dict, List

from .chat import ChatService, DEFAULT_CHAT_ID
from .link import Link, SessionLink
from .mcp import store


class SessionGone(Exception):
    """A request named a conversation that does not exist.

    Its own class rather than an HTTPException so the one handler that answers
    it lives beside the routes instead of inside each of them: eight routes
    resolve a session and every one of them would otherwise carry the same
    three lines, which is how a rule stops being enforced one route later.
    """

    def __init__(self, session_id: str) -> None:
        super().__init__(session_id)
        self.session_id = session_id

class Sessions:
    """Every conversation this interface holds, by id, saved as it goes.

    ⛔ A CONVERSATION AND ITS BROWSERS ARE ONE SESSION, and this class is where
    that is true rather than nearly true. The id it keys on is the SAME id the
    server keys browsers on, so the chat called `lavoro` drives the browsers of
    session `lavoro` and nothing else - which is why `forget` below closes them
    as well. Two ids would have been easier and would have meant that deleting a
    conversation left up to eight engines running with nothing naming them.

    The MCP connection underneath is shared on purpose: one server, one process,
    one place the browsers live. What keeps two conversations from driving each
    other's browser is `SessionLink`, which puts the id on every call.

    Conversations are built on demand and read from disk the first time they are
    asked for. They are not all loaded at startup: a transcript is thousands of
    lines and somebody with twenty sessions wants a column of names, not twenty
    transcripts in memory to draw it.
    """

    def __init__(self, link: Link, make_brain, model_label: str = "no model") -> None:
        self._link = link
        self._make_brain = make_brain
        self.model_label = model_label
        self._live: Dict[str, ChatService] = {}

    @classmethod
    def around(cls, service: "ChatService") -> "Sessions":
        """A registry holding one conversation somebody else built.

        For callers that make the conversation themselves - the tests do, and so
        would anything embedding this - so that having one conversation does not
        require a second code path through the routes. One path means the single
        case is exercised by the same code the many-session case uses.
        """
        got = cls(service._link, lambda: service._brain, service.model_label)
        got._live[service.session_id] = service
        return got

    def get(self, session_id: str | None = None) -> ChatService:
        """The conversation with this id, loaded from disk the first time."""
        at = session_id or DEFAULT_CHAT_ID
        found = self._live.get(at)
        if found is not None:
            return found
        service = ChatService(SessionLink(self._link, at), self._make_brain(),
                              model_label=self.model_label, session_id=at)
        service.restore()
        self._live[at] = service
        return service

    def new(self) -> ChatService:
        """A conversation nobody has used yet, with an id of its own.

        The id is the clock, not a counter: a counter has to be stored somewhere
        to survive a restart, and the place it would be stored is the thing that
        breaks. It is never shown - the name is - so it only has to be unique.
        """
        at = "s%d" % int(time.time() * 1000)
        while at in self._live or store.load_chat(at) is not None:
            at += "x"
        return self.get(at)

    def listing(self) -> List[dict]:
        """Every conversation, saved or only live, newest first.

        A conversation opened a moment ago has nothing on disk yet, and leaving
        it out would make the column disagree with the page it is drawn beside.
        """
        rows = {r["id"]: dict(r) for r in store.known_chats()}
        for at, service in self._live.items():
            row = rows.setdefault(at, {"id": at, "saved": "", "turns": 0})
            row["name"] = service.name
            row["turns"] = sum(1 for e in service.history if e.get("kind") == "you")
            row["live"] = True
        out = list(rows.values())
        out.sort(key=lambda r: (r.get("saved") or "", r["id"]), reverse=True)
        return out

    def knows(self, session_id: str | None) -> bool:
        """Whether this conversation exists, WITHOUT bringing it into being.

        ⛔ THE QUESTION EVERY REQUEST HAS TO ASK BEFORE `get`. Building what it
        does not find is right for a caller that MEANS to start a conversation -
        `new`, an embedder, a test - and wrong for a request that only means to
        look at one. Measured: a page left open on a session somebody deleted
        went on asking `/live/browsers` every three seconds, and one of those
        questions was enough to declare the session again. The delete worked,
        answered `forgotten:true`, closed the browsers, erased the file - and the
        row came back on its own, empty and unnamed, for as long as that tab
        stayed open. Every visible signal said the delete had failed.

        ⛔ AND IT ASKS ABOUT BOTH HALVES OF A SESSION, because a session is a
        conversation AND its browsers and either half can be the only one on
        disk. An agent client that opens a browser in session `work` and never
        touches this interface writes the browsers and no transcript; opening
        `?s=work` here has to work, and asking only about transcripts would have
        refused it. That is the same defect this method exists to fix, made one
        step further along - which is why it is written into the one question
        rather than into the routes that ask it.

        Each half is asked of whoever owns it: what is in memory of this
        registry, what is on disk of the store. The default is always known
        because it is the conversation a page with no id gets, and on a fresh
        install nothing has written it down yet.
        """
        at = session_id or DEFAULT_CHAT_ID
        return (at == DEFAULT_CHAT_ID or at in self._live
                or store.load_chat(at) is not None
                or store.load(at) is not None)

    def rename(self, session_id: str, name: str) -> bool:
        clean = " ".join((name or "").split())[:80]
        if not clean:
            return False
        service = self.get(session_id)
        service.name = clean
        service.save()
        return True

    async def forget(self, session_id: str) -> bool:
        """Delete a conversation AND the browsers that belonged to it.

        ⛔ Both halves, because they are one session. Erasing only the chat file
        would leave up to eight engines running with nothing left that names
        them - 6.5 GB, measured, unreachable and unkillable short of the task
        manager. `session_forget` on the server is the tool that does the other
        half, and it exists for exactly this.

        Refused while that conversation is mid-run: the same reason `reset` is.

        ⛔ AND `False` MEANS THAT AND NOTHING ELSE. It used to mean "there was
        nothing to erase" as well, and the two are opposite news: the page reads
        it and says "that session is still working, so it was not deleted", which
        for a session somebody else had already deleted is the wrong sentence in
        both halves. The caller asked for it to be gone; if it is gone, the
        answer is yes.
        """
        service = self._live.get(session_id)
        if service is not None and service.busy:
            return False
        try:
            await self._link.call("session_forget", {"session_id": session_id})
        except Exception:
            # The browsers could not be closed - the server is gone, or it
            # refused. The conversation is still deleted: leaving it listed
            # because something else failed would tell somebody the delete did
            # not work, when the half they were looking at did.
            pass
        self._live.pop(session_id, None)
        store.erase_chat(session_id)
        return True
