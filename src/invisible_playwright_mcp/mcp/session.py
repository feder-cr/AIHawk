"""One InvisiblePlaywright browser and the page it drives. The browser is
ALWAYS launched by InvisiblePlaywright, never Playwright directly, so the full
stealth stack applies.

⛔ ONE PAGE, AND NO BOOKKEEPING OF ITS OWN. Until 0.53.0 this kept a map of
tab ids to pages, an active id, a counter that survived rebuilds, and a page
lookup with a strict path for named tabs and a fallback for the rest - the
machinery of the tab tools, which went on 2026-09-11 when a browser became one
page. The context already knows its pages; the page a command drives is the
newest live one; that is the whole of it.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from ..quiet import swallow

from invisible_playwright.async_api import InvisiblePlaywright, TargetClosedError


class StealthSession:
    def __init__(self, **kwargs: Any) -> None:
        # ⛔ NO FALLBACK TO THE ENVIRONMENT. This used to be
        # `kwargs or launch_kwargs(os.environ)`, which made this a THIRD place
        # that decided how a browser is configured, behind the tool arguments
        # and `plan_session`. A session now uses what it is handed and nothing
        # else; deciding is `plan.plan_session`'s job, and only its job.
        self._kwargs = kwargs
        self._ipw: Any = None
        # `Any` rather than the engine's own types, which this package does not
        # resolve: an attribute left to be inferred from `None` makes every later
        # use read as an error on a type that cannot have one.
        self._browser: Any = None
        self._context: Any = None
        # The live window capture on a page: the latest JPEG frame and the
        # event that says one has arrived, keyed by the page object. Started
        # lazily by `watch_frame`, stopped with the session.
        self._watch: dict[int, dict[str, Any]] = {}
        # The clock a frame's age is read from. An attribute so a test can move
        # time instead of sleeping through STALE_AFTER.
        self._clock = time.monotonic

    async def _attach(self, result) -> None:
        """`InvisiblePlaywright.__aenter__()` returns a Browser in ephemeral
        mode, or a persistent BrowserContext directly when profile_dir is
        set (that object has no .new_context()). Branch on capability so
        both paths are exercised."""
        if hasattr(result, "new_context"):        # a Browser (ephemeral mode)
            self._browser = result
            self._context = await result.new_context()
        else:                                     # a persistent BrowserContext (profile_dir)
            self._context = result

    async def start(self) -> None:
        self._ipw = InvisiblePlaywright(**self._kwargs)
        await self._attach(await self._ipw.__aenter__())

    def is_usable(self) -> bool:
        """Whether this object is worth handing out, asked WITHOUT talking to
        the browser.

        ⛔ AND THAT IS THE LIMIT, MEASURED, BECAUSE THE NAME IT HAD -
        `is_alive` - PROMISED MORE THAN ANY LOCAL QUESTION CAN ANSWER. With
        the engine ended from outside, this object goes on reporting a
        connected browser: measured 2026-09-14 against firefox-30, the
        process killed and `is_connected()` still true six seconds later,
        with `page.url` answering from cache the whole time. Nothing local
        can see a process that is gone; what sees it is the first ROUND TRIP,
        which raises `TargetClosedError` - `page.title()` and
        `context.new_page()` both, measured the same day.

        So this catches the two failures that ARE local: a session that never
        finished starting, which leaves the context unset, and one this
        process closed. Anything unexpected while asking counts as unusable:
        the cost of dropping a good browser is one `browser_open`, and the
        cost of keeping a bad one is an error that names nothing.
        """
        try:
            if self._context is None:
                return False
            if self._browser is not None and not self._browser.is_connected():
                return False
            return True
        except Exception:
            return False

    # --- the page ---------------------------------------------------------------

    def pages(self) -> list:
        """The live pages of the context, in the order they were opened.

        A page can appear without `new_page` being called - a target with
        `_blank`, or `window.open` - and closed ones are left out, so a tab a
        site closed does not come back as a handle that raises on the next
        tool.
        """
        if self._context is None:
            return []
        return [p for p in getattr(self._context, "pages", [])
                if not (getattr(p, "is_closed", None) and p.is_closed())]

    async def new_page(self):
        return await self._context.new_page()

    def page(self):
        """The page a command drives: the newest live one.

        Newest and not first, because a site that opens a page of its own has
        moved the person's attention there, and acting on the one behind it
        would be acting where nobody is looking.
        """
        live = self.pages()
        if not live:
            raise RuntimeError("this browser has no page open; browser_navigate opens one")
        return live[-1]

    async def describe_pages(self) -> list[dict]:
        """Each page as url, title and whether it is the one a command drives.

        Title costs a round trip per page and url does not, so a page that will
        not answer contributes what it can rather than failing the whole list -
        a page mid-navigation must not make the others unreadable. A closed
        target is the exception: see below.
        """
        live = self.pages()
        out: list[dict] = []
        for page in live:
            row = {"active": page is live[-1], "url": "", "title": ""}
            # ⛔ `page.url` IS CACHED AND `page.title()` IS A ROUND TRIP, and
            # that is the whole difference between a row that reports and a
            # row that pretends. A browser whose engine has been killed goes
            # on answering its url from memory, so a description built out of
            # urls alone reads exactly like a healthy one - measured
            # 2026-09-14, a status answering "page: https://..." over a
            # process that no longer existed.
            with swallow("a page that cannot say where it is answers blank"):
                row["url"] = page.url
            # A title that will not come is ordinary - a page mid-navigation
            # must not make the others unreadable - but a CLOSED TARGET is
            # the browser being gone, and it goes to the caller, which is the
            # only thing that can say so.
            with swallow("a page mid-navigation cannot say its title",
                         unless=(TargetClosedError,)):
                row["title"] = await page.title()
            out.append(row)
        return out

    # --- the window -------------------------------------------------------------

    #: The bound the window frame is scaled to fit. The frame is the whole
    #: window, chrome included, so this is a ceiling on the picture handed to
    #: whoever is watching, not a viewport size; the engine never scales up.
    WATCH_SIZE = {"width": 1280, "height": 800}

    #: Frames a second to ask the engine for.
    #:
    #: ⛔ THE WRAPPER'S DEFAULT IS TEN AND THIS IS SOMEBODY WATCHING, which is
    #: the case the parameter exists for. The default is ten because a batch
    #: job that never looks at a frame should not pay for a live view: measured
    #: 2026-09-08, ten costs 257 KB/s and twenty-five costs 629. Here there IS
    #: somebody looking, so the bandwidth buys something.
    WATCH_FPS = 25

    #: A capture that has delivered nothing for this long is not a quiet page:
    #: it is a capture that has stopped. The engine delivers at WATCH_FPS
    #: whether or not anything on the page changed - measured 2026-09-14 on a
    #: page that never moves: 93 frames in 4 s, the longest gap 78 ms - so two
    #: seconds of silence is fifty missing frames.
    #:
    #: ⛔ A FRAME SERVED WITHOUT AN AGE IS A FROZEN PANE THAT LOOKS LIVE. The
    #: engine's window capture can end for good on its own: the WebRTC capturer
    #: it rests on reports a PERMANENT error the first time a headed window is
    #: minimised, the capture timer is cancelled, and nothing tells the client.
    #: This method then answered the last frame it held, forever, and the pane
    #: showed a search page while the browser was two sites further on. Now a
    #: frame older than this is a reason to stop and start the capture again;
    #: a restart that stays silent is dropped with the reason, so the pane says
    #: what is wrong instead of showing where the browser was.
    STALE_AFTER = 2.0

    async def watch_frame(self, timeout: float = 3.0) -> bytes:
        """The latest JPEG frame of the WINDOW the page lives in.

        `page.screenshot()` is the content viewport and can never show the
        pointer, which the engine draws in the browser chrome precisely so
        that no page can see it. A person watching an agent work wants the
        pointer, the tab strip and the address bar, and that is what the
        engine's screencast captures: the window, through the operating
        system, in the parent process, with nothing injected into the page.

        The capture is started on first use and kept running for the life of
        the page, so the frame answered here is at most a twenty-fifth of a
        second old - and if it is older than STALE_AFTER the capture is
        started again, because the engine does not say when one ends.
        """
        page = self.page()
        key = id(page)
        state = self._watch.get(key)
        if (state is not None and state["latest"]
                and self._clock() - state["at"] > self.STALE_AFTER):
            await self._stop_watch(key)
            state = None
        if state is None:
            state = {"page": page, "latest": b"", "arrived": asyncio.Event(),
                     "at": self._clock()}

            def on_frame(frame: dict) -> None:
                state["latest"] = frame["data"]
                state["at"] = self._clock()
                state["arrived"].set()

            try:
                await page.screencast.start(on_frame=on_frame,
                                            size=dict(self.WATCH_SIZE),
                                            fps=self.WATCH_FPS)
            except Exception as refused:
                # The installed engine or wrapper predates the screencast.
                # Say which feature is missing rather than surfacing a
                # protocol sentence about a guid.
                raise RuntimeError(
                    "the live window view needs invisible-playwright with "
                    "page.screencast and an engine from firefox-28 on: the "
                    "browser answered %s" % refused) from refused
            self._watch[key] = state
        if not state["latest"]:
            try:
                await asyncio.wait_for(state["arrived"].wait(), timeout)
            except asyncio.TimeoutError:
                # Dropped, not kept: a capture that delivered nothing from the
                # start may have died at birth - the engine ends one on a
                # minimised window without a word - and keeping it would make
                # every later look wait on a capture that cannot answer. The
                # next look starts its own, which succeeds the moment the window
                # can be captured again.
                await self._stop_watch(key)
                raise RuntimeError(
                    "the window capture started but no frame arrived in "
                    "%.0f s; a minimised window is captured as nothing" % timeout)
        return state["latest"]

    async def _stop_watch(self, key: int) -> None:
        state = self._watch.pop(key, None)
        if state is None:
            return
        with swallow("the page may already be gone, and the engine stops the "
                     "capture with the page either way"):
            await state["page"].screencast.stop()

    # --- the end ----------------------------------------------------------------

    async def close(self) -> None:
        for key in list(self._watch):
            await self._stop_watch(key)
        if self._context is not None:
            with swallow("a context already gone cannot be closed twice"):
                await self._context.close()
            self._context = None
        if self._ipw is not None:
            try:
                await self._ipw.__aexit__(None, None, None)
            finally:
                self._ipw = None
                self._browser = None
