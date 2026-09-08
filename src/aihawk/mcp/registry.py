"""Sessions, owned here rather than by whoever happens to be connected.

The server used to hold one session in a module global and close it when the
client went away. That made the browser a property of the connection, which
blocked three things at once: only one client could ever attach, the session
could not outlive the process that served it, and nothing but a tool call could
reach the page.

So sessions live here, keyed by id, and a client is just something that borrows
one. Closing happens when the process shuts down, or when someone asks - not
when a client disconnects.
"""
from __future__ import annotations

import asyncio
from typing import Dict, Optional

from .session import StealthSession

# The id used by callers that do not ask for one. Existing stdio clients send no
# session id and must keep behaving exactly as they did, which means they all
# land here, on one shared session, as before.
DEFAULT_SESSION_ID = "default"


def _is_usable(session) -> bool:
    """Whether a stored session can still be handed out.

    Two failures are handled, and they are different:

    * A session whose browser has DIED under it. The object is intact, so
      nothing raises until a tool touches the page, and then it raises somewhere
      unhelpful.
    * A session that never finished starting, which leaves `_context` unset.

    Anything unexpected while checking counts as unusable: the cost of throwing
    away a good session is one relaunch, and the cost of keeping a bad one is an
    error that names nothing.
    """
    try:
        if session._browser is not None and not session._browser.is_connected():
            return False
        return session._context is not None
    except Exception:
        return False


class SessionRegistry:
    """Sessions by id, created on demand, closed on request or at shutdown."""

    def __init__(self, factory=StealthSession, defaults=None,
                 on_change=None) -> None:
        self._factory = factory
        self._defaults = defaults
        #: Called with a key whenever WHO that key is has changed - gained an
        #: identity or lost one. See `_changed`.
        self.on_change = on_change
        self._sessions: Dict[str, StealthSession] = {}
        #: What each id was last STARTED with, kept across the death of the
        #: session object so a rebuild can be the same person. See `ensure`.
        self._configs: Dict[str, dict] = {}
        #: A session_start that FAILED, by id. Kept so `ensure` refuses with
        #: the real reason instead of quietly building a different browser.
        self._refusals: Dict[str, Exception] = {}
        #: The highest tab number each id has handed out, across rebuilds.
        #: Numbering must not restart, or an id a caller still holds names a
        #: DIFFERENT page instead of nothing. See `_adopt_numbering`.
        self._tabs: Dict[str, int] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def _default_config(self) -> dict:
        # Late import: the planner reads config and identity, which have no
        # business importing the registry back.
        if self._defaults is not None:
            return self._defaults()
        from .plan import plan_session
        return plan_session().kwargs

    def config(self, session_id: str = DEFAULT_SESSION_ID) -> Optional[dict]:
        """What this id was started with, for callers that have to report it."""
        return self._configs.get(session_id)

    def _changed(self, session_id: str) -> None:
        """Say that this key's identity was gained or lost.

        ⛔ THIS EXISTS SO THE SERVER DOES NOT HAVE TO REMEMBER TO REMEMBER. The
        first version of persistence wrote the session down after `browser_open`,
        `browser_close` and `browser_focus`, and that is three of the five places
        a browser gets an identity: `session_start` was missed, and so was the
        lazy auto-start every existing client uses - so the ONE session almost
        everybody has was the one never written down. Adding the fourth and fifth
        call would leave the same defect one refactor away, because the thing
        that knows a browser became somebody is this class, not its callers.

        Fired only where `_configs` actually gains or loses an entry, which is
        rare: a browser starting or being deliberately forgotten. Not on `drop`,
        which keeps the identity so the same person comes back, and not on
        `close_all`, where every identity is discarded at once because the
        PROCESS is ending - writing then would erase every saved session at
        shutdown, which is the opposite of what saving them is for.

        A callback that raises must not cost the caller their browser: the
        browser is already built and correct, and failing to write a file down
        is not a reason to hand back an error instead of it.
        """
        if self.on_change is None:
            return
        try:
            self.on_change(session_id)
        except Exception:
            pass

    def _lock(self, session_id: str) -> asyncio.Lock:
        # One lock per id, so two clients racing to first-use the same session
        # start one browser rather than two. Without it the second caller finds
        # an empty slot while the first is still awaiting start().
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    def peek(self, session_id: str = DEFAULT_SESSION_ID) -> Optional[StealthSession]:
        """The session as it stands, without starting anything. For callers that
        want to know whether a browser is up, such as a live view."""
        return self._sessions.get(session_id)

    def ids(self) -> list:
        return sorted(self._sessions)

    async def ensure(self, session_id: str = DEFAULT_SESSION_ID) -> StealthSession:
        """The session for this id, started and usable.

        A start that FAILS must not poison the id. The original bug here stored
        the session before awaiting `start()`, so a start that raised left a
        half-built object behind: every later call found something non-None,
        skipped the start, and died on `'NoneType' object has no attribute ...`,
        an error that names nothing and, on a stdio server, ended the whole
        conversation. The two ways to hit it are ordinary - a stale
        INVISIBLE_SEAL_FILE, and a proxy that is down when the first tool runs.

        So a session is stored only once it has actually started.

        ⛔ AND A REBUILD IS THE SAME PERSON, WHICH IS WHY `_configs` EXISTS.
        Every browsing tool runs through `_retrying`, which on any exception
        drops the session and calls this again. Building the replacement from
        the environment - what this did until now - meant one timeout silently
        replaced the caller's seed, profile AND PROXY with whatever the shell
        happened to hold, so the traffic left from the host's own address while
        the tool reported success. A dead browser between two calls is the
        ordinary case here, so the common path was the one that deanonymised.

        A remembered exit that is DOWN now makes the rebuild fail twice instead
        of succeeding without it. That is the intended trade: a suppressed
        signal is a failure, not a pass, and failing loudly beats succeeding
        from the wrong address.
        """
        # Whether this call is what gave the key an identity. Read after the
        # lock is released, so the callback - which writes a file - runs with
        # nobody waiting behind it.
        became = False
        async with self._lock(session_id):
            existing = self._sessions.get(session_id)
            if existing is not None and not _is_usable(existing):
                await self._discard(session_id)
                existing = None

            if existing is None:
                refusal = self._refusals.get(session_id)
                if refusal is not None:
                    raise refusal
                config = self._configs.get(session_id)
                if config is None:
                    config = self._default_config()
                session = self._factory(**config)
                self._adopt_numbering(session_id, session)
                await session.start()
                self._sessions[session_id] = session
                self._configs[session_id] = config
                became = True
            else:
                session = existing
        if became:
            self._changed(session_id)
        return session

    async def restart(self, session_id: str = DEFAULT_SESSION_ID,
                      **kwargs) -> StealthSession:
        """Close whatever is on this id and start a session with THESE settings.

        `ensure` builds from the environment, which is right for a caller that
        never says anything. This is for one that does: the identity, the exit
        and the profile are decided per session, and the only way to change
        them is a browser that has not started yet.

        ⛔ The old session is closed FIRST and unconditionally. Starting the new
        one first would leave two browsers alive if the second start failed,
        and the one still holding the profile directory is the one nobody has a
        handle to any more.
        """
        async with self._lock(session_id):
            await self._discard(session_id)
            session = self._factory(**kwargs)
            self._adopt_numbering(session_id, session)
            try:
                await session.start()
            except Exception as exc:
                # ⛔ A FAILED START MUST NOT FALL BACK TO THE ENVIRONMENT, and
                # leaving the id empty is exactly that fallback with an extra
                # step. Measured: restart with a proxy raised, the id was empty,
                # and the next `ensure` built a session with no proxy at all -
                # so a caller who asked for an exit, was told it failed, and
                # carried on, went out from this machine's own address while
                # every tool answered normally. Same leak as rebuilding from the
                # shell, one call later and on the likelier path.
                #
                # The refusal is remembered instead, and `ensure` re-raises it
                # until somebody starts a session that works. Lazy auto-start
                # survives for a caller that never said anything; it must not
                # resurrect after a caller said something and it did not work.
                self._refusals[session_id] = exc
                self._configs.pop(session_id, None)
                raise
            self._refusals.pop(session_id, None)
            self._sessions[session_id] = session
            # Recorded only after a start that worked, and recorded LAST, so a
            # refused or failed start leaves the previous identity in place
            # rather than arming recovery with settings that do not launch.
            self._configs[session_id] = dict(kwargs)
        self._changed(session_id)
        return session

    def _adopt_numbering(self, session_id: str, session) -> None:
        """Continue this id's tab numbering in the session replacing it."""
        mark = self._tabs.get(session_id, 0)
        # The factory is pluggable, so a stand-in need not offer this.
        if mark and hasattr(session, "resume_numbering_after"):
            session.resume_numbering_after(mark)

    async def _discard(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return
        self._tabs[session_id] = max(self._tabs.get(session_id, 0),
                                     getattr(session, "_counter", 0) or 0)
        try:
            await session.close()
        except Exception:
            # A session being discarded is already suspect; a failure to close
            # it cleanly must not stop the replacement from starting.
            pass

    async def drop(self, session_id: str = DEFAULT_SESSION_ID) -> None:
        """Throw a session away so the next `ensure` builds a fresh one."""
        async with self._lock(session_id):
            await self._discard(session_id)

    def declare(self, session_id: str, config: dict) -> None:
        """Say who a browser WILL be, without starting it.

        ⛔ This is what makes reopening a saved session cheap. A browser costs
        about 800 MB and seven to fourteen seconds to start, measured, so
        reopening a session that declared eight of them must not start eight of
        them: they are declared here, and the first command aimed at one is what
        actually launches it - as the right person, because the config is
        already remembered.

        It writes `_configs` and nothing else, which is the same memory `ensure`
        already consults and `drop` already preserves. A declared browser is
        therefore indistinguishable from one whose browser died a moment ago,
        and that is the point: the recovery path was already correct.

        It does NOT fire `_changed`. This is how a session is READ BACK, and
        reporting a change here would write straight back out what was just read
        in - harmless, but it would make the hook mean "something happened"
        instead of "somebody became somebody", which is the distinction the hook
        exists to carry.
        """
        self._configs[session_id] = dict(config)

    def declared(self) -> list:
        """Every browser this registry knows of, running or only declared."""
        return sorted(set(self._sessions) | set(self._configs))

    async def forget(self, session_id: str = DEFAULT_SESSION_ID) -> bool:
        """Close this browser and forget who it was. Answers whether it existed.

        ⛔ `drop` and this one differ in exactly the way `close_all` explains,
        and picking the wrong one is a leak rather than an inconvenience. `drop`
        is RECOVERY: the browser died under a caller who is still working, so
        the identity, the profile and the exit are kept and the replacement is
        the same person. This is a DELIBERATE close, and a browser that came
        back wearing an identity its owner had shut down would hand the next
        caller a person they never asked for - the same leak `close_all` refuses,
        one browser at a time.
        """
        async with self._lock(session_id):
            existed = session_id in self._sessions or session_id in self._configs
            await self._discard(session_id)
            self._configs.pop(session_id, None)
            self._refusals.pop(session_id, None)
        if existed:
            self._changed(session_id)
        return existed

    async def close_all(self) -> None:
        """Shut every session down. Called when the PROCESS ends, not when a
        client disconnects - that difference is the reason this class exists.

        ⛔ This FORGETS, where `drop` remembers, and the difference is the whole
        point of the memory. `drop` is recovery: the browser died and the same
        person has to come back. This is a deliberate close, and a closed
        session that resurrected wearing its old proxy and its old profile would
        be a leak in the other direction - a caller who shut a session down and
        later let a tool auto-start one would silently get the old identity.
        """
        for session_id in list(self._sessions):
            await self._discard(session_id)
        self._configs.clear()
        self._refusals.clear()
