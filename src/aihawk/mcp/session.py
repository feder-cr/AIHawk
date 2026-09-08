"""One InvisiblePlaywright browser, many tabs. The browser is ALWAYS launched
by InvisiblePlaywright, never Playwright directly, so the full stealth stack
applies."""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from invisible_playwright.async_api import InvisiblePlaywright


class StealthSession:
    def __init__(self, **kwargs: Any) -> None:
        # ⛔ NO FALLBACK TO THE ENVIRONMENT. This used to be
        # `kwargs or launch_kwargs(os.environ)`, which made this a THIRD place
        # that decided how a browser is configured, behind the tool arguments
        # and `plan_session`. A session now uses what it is handed and nothing
        # else; deciding is `plan.plan_session`'s job, and only its job.
        self._kwargs = kwargs
        self._ipw: Optional[InvisiblePlaywright] = None
        self._browser = None
        self._context = None
        self._pages: dict[str, Any] = {}
        self._active: Optional[str] = None
        self._counter = 0
        # page id -> the live window capture on that tab: the latest JPEG
        # frame and the event that says one has arrived. Started lazily by
        # `watch_frame`, stopped with the tab.
        self._watch: dict[str, dict[str, Any]] = {}

    def resume_numbering_after(self, highest: int) -> None:
        """Carry tab numbering forward from a session this one replaces.

        ⛔ Tab ids used to restart at `tab-1` on every rebuild, so an id a caller
        was still holding resolved to a DIFFERENT page instead of erroring -
        exactly what `page()` below refuses to do for a named tab, on the
        grounds that acting on the wrong tab with nothing said is worse than an
        error. A rebuild is common (any failure retries through one), and the
        identity work that keeps the same person across it also keeps the caller
        going, so the stale id is more reachable than it was, not less.

        Numbering continues instead, and a stale id now names nothing.
        """
        self._counter = max(self._counter, highest)

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

    async def new_page(self) -> str:
        self._counter += 1
        page_id = f"tab-{self._counter}"
        page = await self._context.new_page()
        self._pages[page_id] = page
        self._active = page_id
        return page_id

    def list_pages(self) -> list[str]:
        """The tabs this session knows about, including ones it did not open.

        A page can appear without `new_page` being called - a target with
        `_blank`, or `window.open` - and a caller that cannot name it cannot
        act on it. Adopting live pages from the context keeps the list honest.
        """
        if self._context is not None and hasattr(self._context, "pages"):
            for p in self._context.pages:
                # CLOSED pages are not adopted. Without this a tab that was
                # just closed comes straight back under a NEW id, because
                # `close_page` removes it from our own map while the context
                # can still list it - and then `page()` hands the caller a
                # handle that raises on the next tool.
                if getattr(p, "is_closed", None) is not None and p.is_closed():
                    continue
                if p not in self._pages.values():
                    self._counter += 1
                    pid = f"tab-{self._counter}"
                    self._pages[pid] = p
                    if not self._active:
                        self._active = pid
        return list(self._pages)

    async def describe_pages(self) -> list[dict]:
        """Each tab as id, title, url and whether it is the active one.

        `list_pages` answers with ids alone, which is enough for this session's
        own bookkeeping and not enough for a caller. Choosing a tab by id with
        no idea what is in it is choosing blind, and until 0.9.0 that is exactly
        what `session_list_pages` handed a model, while its description
        promised these four fields. The description was the sensible half, so
        the data moved to meet it.

        It lives here rather than in `actions` because `_pages` and `_active`
        are this object's business: a second reader of that dict would be a
        second place that has to be right about which tab is current.

        Title costs a round trip per tab and url does not, so a page that will
        not answer contributes what it can rather than failing the whole list -
        a tab mid-navigation must not make the others unreadable.
        """
        out: list[dict] = []
        for pid in self.list_pages():
            page = self._pages.get(pid)
            row = {"id": pid, "active": pid == self._active, "url": "", "title": ""}
            if page is not None:
                try:
                    row["url"] = page.url
                except Exception:
                    pass
                try:
                    row["title"] = await page.title()
                except Exception:
                    pass
            out.append(row)
        return out

    def select_page(self, page_id: str) -> None:
        if page_id not in self._pages:
            raise RuntimeError(f"no such tab: {page_id}")
        self._active = page_id

    def page(self, page_id: Optional[str] = None):
        """The active page, or any live one, rather than a closed handle.

        The recorded tab can be closed under us - by the site, or by a
        navigation that replaced it - and returning it produces an error from
        whatever tool touched it rather than from here. Falling back to a live
        page from the context keeps a session usable after that.
        """
        pid = page_id or self._active
        if pid is not None and pid in self._pages:
            p = self._pages[pid]
            if not p.is_closed():
                return p

        # A tab the caller NAMED is answered strictly. The fallback below
        # exists so a session survives losing its active tab; applied to an
        # explicit id it would hand back a DIFFERENT page under the name that
        # was asked for, which is worse than an error - the caller goes on
        # acting on the wrong tab and nothing says so.
        if page_id is not None:
            raise RuntimeError(f"no such tab: {page_id}")

        if self._context is not None and hasattr(self._context, "pages") and self._context.pages:
            for p in reversed(self._context.pages):
                if not p.is_closed():
                    self._counter += 1
                    new_pid = f"tab-{self._counter}"
                    self._pages[new_pid] = p
                    self._active = new_pid
                    return p

        raise RuntimeError("no such tab; open one with session_new_page")

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
    #:
    #: It is the last link of a chain that was slow in three places and is now
    #: fast in all three: the engine makes what it is asked for, the wrapper
    #: passes the request on (0.14.0, which the floor below requires), and the
    #: page asks often enough to collect them.
    WATCH_FPS = 25

    async def watch_frame(self, page_id: Optional[str] = None,
                          timeout: float = 3.0) -> bytes:
        """The latest JPEG frame of the WINDOW the active tab lives in.

        `page.screenshot()` is the content viewport and can never show the
        pointer, which the engine draws in the browser chrome precisely so
        that no page can see it. A person watching an agent work wants the
        pointer, the tab strip and the address bar, and that is what the
        engine's screencast captures: the window, through the operating
        system, in the parent process, with nothing injected into the page.

        The capture is started on first use and kept running for the life of
        the tab, so the frame answered here is at most a twenty-fifth of a
        second old. Stopped with the tab in `close_page`.
        """
        page = self.page(page_id)
        pid = next(k for k, v in self._pages.items() if v is page)
        state = self._watch.get(pid)
        if state is None:
            state = {"latest": b"", "arrived": asyncio.Event()}

            def on_frame(frame: dict) -> None:
                state["latest"] = frame["data"]
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
            self._watch[pid] = state
        if not state["latest"]:
            try:
                await asyncio.wait_for(state["arrived"].wait(), timeout)
            except asyncio.TimeoutError:
                raise RuntimeError(
                    "the window capture is running but no frame arrived in "
                    "%.0f s; a minimised window is captured as nothing" % timeout)
        return state["latest"]

    async def _stop_watch(self, pid: str) -> None:
        state = self._watch.pop(pid, None)
        page = self._pages.get(pid)
        if state is None or page is None:
            return
        try:
            await page.screencast.stop()
        except Exception:
            # The tab may already be gone; the engine stops the capture with
            # the page either way.
            pass

    async def close_page(self, page_id: Optional[str] = None) -> None:
        pid = page_id or self._active
        if pid is None or pid not in self._pages:
            return
        await self._stop_watch(pid)
        try:
            await self._pages[pid].close()
        except Exception:
            pass
        finally:
            self._pages.pop(pid, None)
            if self._active == pid:
                self._active = next(reversed(self._pages), None)

    async def close(self) -> None:
        for pid in list(self._pages):
            await self.close_page(pid)
        if self._context is not None:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        if self._ipw is not None:
            try:
                await self._ipw.__aexit__(None, None, None)
            finally:
                self._ipw = None
                self._browser = None
