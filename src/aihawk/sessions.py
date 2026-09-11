"""Every conversation this interface holds, and the way in to one.

Split out of `web.py` on 2026-09-10. The classes are the same bytes they were -
except for how a conversation reaches its browsers, rewritten on 2026-09-11 when
MCP stopped having a session concept at all. See the class docstring below.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Mapping, Optional

from .chat import ChatService, DEFAULT_CHAT_ID
from .link import Link
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
    that is true rather than nearly true - but what makes it true changed on
    2026-09-11. It used to be one shared MCP connection with the id imposed on
    every call, because MCP itself understood "session" as a tool argument. It
    does not any more: no tool takes one, none can be listed, none can be
    reached from another. So the id can no longer be a value passed over an
    open connection - it has to be which CONNECTION exists at all, and that
    means one conversation, one spawned server PROCESS, its `AIHAWK_SESSION_ID`
    set at the moment it is started. Two ids would have been easier only in the
    sense that it used to be true; it is not the shape MCP has any more.

    Conversations are built ON DEMAND and read from disk the first time they are
    asked for, which now means spawning their process the first time too - the
    same lazy cost `browser_open` already pays for a browser, paid once more, one
    layer up, for the connection that reaches it. They are not all loaded at
    startup: a transcript is thousands of lines and somebody with twenty
    sessions wants a column of names, not twenty processes to draw it.
    """

    def __init__(self, opts: Mapping[str, Any], key: Optional[str], make_brain,
                model_label: str = "no model") -> None:
        self._opts = dict(opts)
        self._key = key
        self._make_brain = make_brain
        self.model_label = model_label
        self._live: Dict[str, ChatService] = {}
        # ⛔ A SEAM FOR TESTS, NOT A SECOND WAY TO PRODUCE A CONNECTION IN THE
        # PRODUCT. Real code never reassigns this: `get` always spawns
        # `Link(dict(opts, session_id=at), key=key).open()`. A test that wants
        # many conversations without many real processes sets this to a
        # function of its own, so what is under test is `Sessions` deciding
        # WHICH conversation gets WHICH connection - never `Link` itself,
        # which has its own tests, and never a real subprocess, which
        # `tests/mcp_server/test_stdio_e2e.py` is where that gets proven.
        self._open_link = self._spawn_link

    async def _spawn_link(self, session_id: str) -> Link:
        return await Link(dict(self._opts, session_id=session_id),
                          key=self._key).open()

    @classmethod
    def around(cls, service: "ChatService") -> "Sessions":
        """A registry holding one conversation somebody else built.

        For callers that make the conversation themselves - the tests do, and so
        would anything embedding this - so that having one conversation does not
        require a second code path through the routes. One path means the single
        case is exercised by the same code the many-session case uses. It never
        spawns anything of its own: the one conversation it holds already has
        its connection, and `get` finds it in `_live` before reaching for `_opts`.
        """
        got = cls({}, None, lambda: service._brain, service.model_label)
        got._live[service.session_id] = service
        return got

    async def close_all(self) -> None:
        """Close every conversation's own connection, for a clean shutdown.

        ⛔ THERE IS NO LONGER ONE CONNECTION TO CLOSE - there are as many as
        conversations were ever asked for, each its own process. `Link.close`
        already swallows what closing can throw, so nothing here needs to.
        """
        for service in self._live.values():
            await service.link.close()

    async def get(self, session_id: str | None = None) -> ChatService:
        """The conversation with this id, loaded from disk the first time.

        ⛔ SPAWNS ITS OWN SERVER, THE FIRST TIME, because that is now the only
        way one conversation's browsers stay apart from another's: each gets
        its own process, with `AIHAWK_SESSION_ID` set to this id, so the server
        inside never has more than the one thing to persist and never anything
        to confuse it with.
        """
        at = session_id or DEFAULT_CHAT_ID
        found = self._live.get(at)
        if found is not None:
            return found
        link = await self._open_link(at)
        service = ChatService(link, self._make_brain(),
                              model_label=self.model_label, session_id=at)
        service.restore()
        self._live[at] = service
        return service

    async def new(self) -> ChatService:
        """A conversation nobody has used yet, with an id of its own.

        The id is the clock, not a counter: a counter has to be stored somewhere
        to survive a restart, and the place it would be stored is the thing that
        breaks. It is never shown - the name is - so it only has to be unique.
        """
        at = "s%d" % int(time.time() * 1000)
        while at in self._live or store.load_chat(at) is not None:
            at += "x"
        return await self.get(at)

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

    async def rename(self, session_id: str, name: str) -> bool:
        clean = " ".join((name or "").split())[:80]
        if not clean:
            return False
        service = await self.get(session_id)
        service.name = clean
        service.save()
        return True

    async def forget(self, session_id: str) -> bool:
        """Delete a conversation AND the browsers that belonged to it.

        ⛔ BOTH HALVES, BECAUSE THEY ARE ONE SESSION, AND HOW THE SECOND HALF
        HAPPENS CHANGED WITH EVERYTHING ELSE ON 2026-09-11. There used to be a
        tool, `session_forget`, that closed the browsers of a session named on
        an open connection shared with every other conversation. There is no
        such tool now, and there could not be one that stayed inside the rule
        the owner set: MCP cannot be asked to operate on a piece of work that
        is not its own. So this reaches for the ONLY thing that was ever
        really being asked for - closing that conversation's OWN connection,
        which is that conversation's OWN server process, and closing that ends
        it exactly the way a standalone client disconnecting always has: the
        stdio EOF this sends is what `_lifespan` in `mcp/server.py` already
        closes every browser on, the same path every such client relies on,
        not a new one built for this.

        The saved browser file is erased directly, by calling into `store` in
        this same package - not over MCP, because MCP has no tool that reaches
        a piece of work other than its own, and this IS the process whose own
        file it is (or was, if it was never brought up this run). That call is
        a plain function, not a wire protocol: it costs nothing to make and
        asks nothing of anybody.

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
        if service is not None:
            # Closes silently: `Link.close` already swallows what closing can
            # throw, because a connection being torn down on purpose is not a
            # failure to report back.
            await service.link.close()
        self._live.pop(session_id, None)
        store.erase(session_id)
        store.erase_chat(session_id)
        return True
