"""The HTTP surface: one door per thing the page can ask for.

Split out of `web.py` on 2026-09-10. `build_app` is the same bytes it was.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from .chat import ChatService, DEFAULT_CHAT_ID
from .link import Link, image_of, text_of
from .mcp import NOTHING_RUNNING
from .sessions import SessionGone, Sessions
from .ui import PAGE


def sse(payload: dict, at: str | None = None) -> bytes:
    """One event, framed the way `EventSource` reads them.

    ⛔ ONE PLACE KNOWS THE FRAMING, where seven wrote it out by hand. The
    framing is three details a reader skims past - the `id:` line before the
    `data:` line, the single newline between them, the blank line that ends the
    event - and every one of them is load-bearing: a missing blank line makes
    two events arrive as one and neither is delivered. Written seven times it
    was seven chances to get one of them wrong in a way no test looked at.

    `at` is the resume point, and leaving it out is meaningful rather than
    lazy: an id MOVES that point, so state which is not a place to resume from
    is sent without one, and the spec then keeps the last id standing.
    """
    head = (b"id: " + at.encode() + b"\n") if at else b""
    return head + b"data: " + json.dumps(payload).encode() + b"\n\n"


def marker_at(epoch: str, position: int) -> str:
    """The resume point for this position of this transcript."""
    return "%s:%d" % (epoch, position)


def resume_point(marker: str, epoch: str) -> tuple[int, bool]:
    """Where a reconnecting listener got to, and whether it is even the same
    conversation. Answers `(the first event it still needs, same transcript)`.

    ⛔ THE EPOCH IS HALF THE ANSWER. A position only means something inside one
    transcript: after a reset, or after the process restarts, the same number
    points at something else entirely, so a mismatch is not a resume at all -
    it replays from the beginning and the page is told to drop what it holds
    rather than grow a chimera.

    Written beside `marker_at`, which is the only thing that produces what this
    reads, so the two cannot drift apart.
    """
    if ":" not in marker:
        return 0, False
    said, _, position = marker.partition(":")
    if said != epoch or not position.isdigit():
        return 0, False
    return int(position) + 1, True


#: The answer when there is nothing to say, in the shape of the answer when
#: there is. The page reads the same fields either way, so an empty reply that
#: omits a field is a reply the page cannot read - and both of these are given
#: on paths that exist precisely because something went wrong or is missing,
#: which is where a shape written out a second time drifts unnoticed.
NO_BROWSERS = {"browsers": [], "focus": "", "limit": 0}
NO_TABS = {"url": "", "tabs": []}


def build_app(link: Link, sessions: "Sessions") -> Starlette:
    def named(session_id: str | None) -> ChatService:
        """The conversation with this id, refusing one nobody declared.

        ⛔ ONE PLACE TURNS AN ID OFF THE WIRE INTO A CONVERSATION, because the
        id does not always arrive the same way: eight routes carry it in the
        query string and the rename carries it in the body. Written twice, the
        rename is where it would have gone on resurrecting deleted sessions
        after the eight beside it had stopped.
        """
        if not sessions.knows(session_id):
            raise SessionGone(session_id or "")
        return sessions.get(session_id)

    def which(request: Request) -> ChatService:
        """The conversation this request is about.

        ⛔ EVERY ROUTE GOES THROUGH HERE, the live ones included. A route that
        read the session id and a route that did not would act on two different
        conversations while the page showed one, and the way that fails is the
        picture on the right belonging to somebody else's browser. A caller that
        names nothing gets the default conversation, which is what every page
        written before this existed does.

        ⛔ AND IT REFUSES AN ID NOBODY DECLARED, instead of declaring it. A
        request is a way to look at a conversation, never a way to start one -
        `/sessions/new` is. See `Sessions.knows` for what a page left open on a
        deleted session did to it.
        """
        return named(request.query_params.get("s"))

    async def root(_request: Request) -> HTMLResponse:
        return HTMLResponse(PAGE)

    async def listing(_request: Request) -> JSONResponse:
        return JSONResponse({"sessions": sessions.listing(),
                             "default": DEFAULT_CHAT_ID})

    async def new_session(_request: Request) -> JSONResponse:
        service = sessions.new()
        return JSONResponse({"id": service.session_id, "name": service.name})

    async def rename_session(request: Request) -> JSONResponse:
        body = await request.json()
        at = (body or {}).get("id") or DEFAULT_CHAT_ID
        service = named(at)
        done = sessions.rename(at, (body or {}).get("name", ""))
        return JSONResponse({"renamed": done, "name": service.name})

    async def forget_session(request: Request) -> JSONResponse:
        body = await request.json()
        at = (body or {}).get("id")
        if not at:
            return JSONResponse({"error": "no id"}, status_code=400)
        return JSONResponse({"forgotten": await sessions.forget(at)})

    async def send(request: Request) -> JSONResponse:
        body = await request.json()
        text = (body or {}).get("text", "")
        if not text:
            return JSONResponse({"error": "empty"}, status_code=400)
        which(request).start(text)
        return JSONResponse({"accepted": True})

    async def stop(request: Request) -> JSONResponse:
        return JSONResponse({"stopped": which(request).stop()})

    async def fresh(request: Request) -> JSONResponse:
        service = which(request)
        done = service.reset()
        if done:
            # Told to every listener, not just the tab that asked: two tabs on
            # one session must not disagree about what the conversation is.
            await service.emit("fresh", "1")
            service.save()
        return JSONResponse({"fresh": done})

    async def events(request: Request) -> StreamingResponse:
        service = which(request)
        q = service.subscribe()
        # Freeze the replay/live boundary while subscribing. StreamingResponse
        # starts `stream` later, so taking this snapshot inside it would let an
        # intervening event appear in both history and the listener's queue.
        history = list(service.history)
        # Taken with the snapshot, for the same reason: whether a run is in
        # flight is part of the state this listener is joining.
        joining_a_run = service.busy

        # ⛔ WHERE THIS LISTENER GOT TO, AND WHETHER IT IS EVEN THE SAME
        # CONVERSATION. `EventSource` reconnects by itself after any drop, and
        # until this was read the server answered every reconnection with the
        # whole transcript again, while the page - which has no de-duplication
        # and had never been given an id to resume from - appended a second
        # copy of everything. Measured: three consecutive subscriptions each
        # received all 21 events of the same conversation.
        #
        # What the header means, and why a position alone is not enough, is in
        # `resume_point`. It is not repeated here: written in both places it
        # would be two accounts of one rule, free to disagree.
        marker = request.headers.get("last-event-id") or ""
        resume_from, same_conversation = resume_point(marker, service.epoch)
        replay = history[resume_from:] if same_conversation else history

        async def stream() -> AsyncIterator[bytes]:
            try:
                yield sse({"kind": "model", "text": service.model_label})
                if not same_conversation and marker:
                    # It reconnected carrying a position from another
                    # transcript, so what it is still showing is not this one.
                    yield sse({"kind": "fresh", "text": "1"})
                # Flagged as replay so the page does not animate forty rows at
                # once and does not start a stopwatch on work that finished
                # before this listener existed. Numbered so the next
                # reconnection can say where it got to instead of starting over.
                for offset, past in enumerate(replay):
                    yield sse({**past, "replay": True},
                              marker_at(service.epoch, resume_from + offset))
                # And then the CURRENT state, which the replay above cannot
                # carry: `emit` keeps `busy` out of the history on purpose, so a
                # page opened long after a run would not show a spinner for work
                # that ended an hour ago. That is right for a finished run and
                # wrong for one still going - the page would show a transcript
                # growing under a composer that says nothing is happening, and
                # with no turn ceiling the stop button is the only thing that
                # ends such a run. So it is sent as what it is, the present, and
                # only when true: a page starts out believing it is idle.
                # ⛔ AND IT IS SENT WHEN FALSE TOO, WHICH IS NOT SYMMETRY FOR
                # ITS OWN SAKE: without it the last thing the model said was
                # never drawn. The page holds one narration line back so that a
                # sentence with tool calls after it reads as their lead-in and
                # one with nothing after it reads as the answer, and the event
                # that resolves that lookahead is the end of the turn - which
                # is a `busy` going false. A replay carries no `busy` at all, so
                # a page reopening a FINISHED conversation sat holding its last
                # sentence forever. Measured on the developer's own saved
                # session: 257 events ending in `said`, and the answer to the
                # last thing they asked was not on the screen.
                # Marked as replay so it flushes without animating one row and
                # without redrawing the session list, exactly like the events
                # above it.
                # The two are NOT one line with a conditional inside: the live
                # one must arrive unflagged or the page calls `waited()` where
                # it should call `waiting()`, and a run in progress would lose
                # its clock.
                if joining_a_run:
                    yield sse({"kind": "busy", "text": "1"})
                else:
                    yield sse({"kind": "busy", "text": "0", "replay": True})
                while True:
                    event = await q.get()
                    # Only what the history keeps is numbered: an id moves the
                    # resume point, and `busy` is not a place to resume from.
                    # Leaving the field out keeps the last one,
                    # which is what the spec says and what is wanted here.
                    if event["kind"] in ("busy", "fresh"):
                        yield sse(event)
                    else:
                        yield sse(event, marker_at(service.epoch,
                                                   len(service.history) - 1))
            finally:
                service.unsubscribe(q)

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store"})

    async def frame(request: Request) -> Response:
        """The window the active tab lives in, as `browser_watch` captures it.

        Not `browser_take_screenshot`: that is the page alone, and the engine
        draws the pointer outside the page on purpose, so no screenshot can
        show it. The window capture shows the pointer, the tab strip and the
        address bar, keeps answering while a page loads, and costs one frame
        the server already holds rather than a paint. The tool exists from
        0.15.0 of the server, which is the floor pyproject declares.

        The strip and the address in the picture are pixels; the ones the
        page draws above it are the same facts as elements, and those can be
        clicked and copied. Both stay.

        ⛔ AND THERE IS NO GUARD HERE ANY MORE, WHICH IS THE POINT. There used
        to be one, reading whether this conversation had ever called anything,
        and it was armed by the one call that starts nothing - so the next
        frame through it started an engine: measured on 0.38.0, 9 firefox
        processes to 16 for a session nobody had asked anything, and the
        capture then failed anyway. Asking the free question here instead was
        tried and measured too, and it is the wrong place: `browser_list` costs
        30 ms against the capture's 1, so paying it every frame caps the pane
        at 32 a second to answer a question whose answer is almost always yes.
        `browser_watch` refuses without starting now, so the cheap path is the
        common one and this route simply asks.
        """
        seen = which(request)
        # ⛔ THE PANE SAYS WHICH BROWSER, and without that the workspace is one
        # picture drawn eight times. `browser_id` is the caller's to choose here
        # exactly as `session_id` is not: which SESSION a request belongs to is
        # decided by the page's own url and imposed, while which BROWSER inside
        # it a pane is watching is what the pane is for.
        watching = request.query_params.get("b") or None
        try:
            result = await seen.link.call("browser_watch",
                                          {"browser_id": watching} if watching else {})
        except Exception as exc:
            return JSONResponse({"error": str(exc)[:200]}, status_code=503)
        got = image_of(result)
        if got is None:
            # A tool that raised reaches a client as an error RESULT with the
            # reason as text, not as an exception: an engine without the
            # screencast, or a window captured as nothing. That is a 503 with
            # the reason, never a 204, which would read as "nothing to look at"
            # in the one case where a person needs to read a sentence.
            reason = text_of(result) if getattr(result, "isError", False) else ""
            if reason and NOTHING_RUNNING not in reason:
                return JSONResponse({"error": reason[:200]}, status_code=503)
            # And one refusal is not a failure at all: a browser that is not
            # running is nothing to look at, which is the idle pane. Compared
            # against the sentence itself rather than guessed at from its
            # shape - the two ship in one package, so there is one string.
            return Response(status_code=204)
        jpeg, mime = got
        return Response(jpeg, media_type=mime, headers={"Cache-Control": "no-store"})

    async def browsers(request: Request) -> JSONResponse:
        """The panes to draw: which browsers this session holds, and where.

        Asked of the server through the same tool an agent would call, because
        the interface has no privileged path to the browsers - and it starts
        nothing, so drawing the workspace can never cost an engine.

        ⛔ AND IT ASKS EVEN WHEN THIS CONVERSATION HAS DONE NOTHING, which is
        the opposite of what the picture and the tab strip do. Those may not ask
        before an instruction because asking STARTS a browser; `browser_list` is
        the one question that starts nothing, by construction and by its own
        test. Copying the guard here looked prudent and was a bug: a session
        reopened after a restart has browsers it declared and no instruction
        yet, so the workspace would have been empty in exactly the case the
        declarations exist for - and the panes offering to wake them would
        never have been drawn.
        """
        seen = which(request)
        try:
            got = json.loads(await seen.link.call_text("browser_list"))
        except Exception:
            # An older server answered this in prose. The workspace then draws
            # nothing rather than half of something, and the single live pane -
            # which does not need this - keeps working.
            return JSONResponse(NO_BROWSERS)
        if not isinstance(got, dict):
            return JSONResponse(NO_BROWSERS)
        return JSONResponse({"browsers": got.get("browsers") or [],
                             "focus": got.get("focus") or "",
                             "limit": got.get("limit") or 0})

    async def tabs(request: Request) -> JSONResponse:
        """Every tab, and which one is current.

        ONE call where there were two. It asks `session_list_pages`, which since
        0.9.0 of the server answers with id, title, url and active - the four
        fields its description had always promised and had never returned. While
        it returned ids only this had to ask `browser_evaluate` for
        `location.href` instead, which is script in the page to learn something
        the server already knew.

        A stale or older server is not an error here: anything that does not
        parse into those fields leaves the strip empty and the address blank,
        and the pane keeps working as a picture.
        """
        seen = which(request)
        # ⛔ WHICH BROWSER, like the frame route beside it. The address above the
        # stage has to be the address of the screen being looked at, and with
        # more than one screen the answer stopped being "the focused one" the
        # moment clicking a screen became a way to look somewhere else.
        watching = request.query_params.get("b") or None
        try:
            raw = await seen.link.call_text(
                "session_list_pages",
                {"browser_id": watching} if watching else None)
            rows = json.loads(raw)
        except Exception:
            return JSONResponse(NO_TABS)
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            return JSONResponse(NO_TABS)
        here = next((r for r in rows if r.get("active")), rows[0] if rows else {})
        return JSONResponse({"url": here.get("url") or "", "tabs": rows})

    async def select(request: Request) -> JSONResponse:
        body = await request.json()
        page_id = (body or {}).get("id", "")
        if not page_id:
            return JSONResponse({"error": "no id"}, status_code=400)
        await which(request).link.call("session_select_page", {"page_id": page_id})
        return JSONResponse({"ok": True})

    async def vanished(_request: Request, exc: Exception) -> JSONResponse:
        """410, because the conversation existed and does not any more.

        Not 404: the page asking is a page that HAD this conversation open, and
        the difference between "there is no such thing" and "this is over" is
        the difference between a page that says something wrong happened and a
        page that says what happened. It is also the only status the page reads
        as a reason to stop asking - anything else is a failure worth retrying.
        """
        return JSONResponse({"error": "this conversation was deleted",
                             "id": getattr(exc, "session_id", "")},
                            status_code=410)

    return Starlette(exception_handlers={SessionGone: vanished}, routes=[
        Route("/", root),
        Route("/sessions", listing),
        Route("/sessions/new", new_session, methods=["POST"]),
        Route("/sessions/rename", rename_session, methods=["POST"]),
        Route("/sessions/forget", forget_session, methods=["POST"]),
        Route("/chat/send", send, methods=["POST"]),
        Route("/chat/stop", stop, methods=["POST"]),
        Route("/chat/fresh", fresh, methods=["POST"]),
        Route("/chat/events", events),
        Route("/live/frame", frame),
        Route("/live/browsers", browsers),
        Route("/live/tabs", tabs),
        Route("/live/select", select, methods=["POST"]),
    ])
