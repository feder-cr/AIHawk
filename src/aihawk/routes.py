"""The HTTP surface: one door per thing the page can ask for.

Every handler is a module-level function and finds the registry of
conversations on `request.app.state.sessions`. Until 0.52.0 all of them were
closures inside `build_app`, 297 lines deep, so that a reader looking for the
route that serves the frame had to find it inside a function that also built
the app - and a test could not import one handler without building all of
them. `build_app` now does the one thing its name says.
"""
from __future__ import annotations

import json
from typing import AsyncIterator, Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from .chat import ChatService, DEFAULT_CHAT_ID
from .link import image_of, answer_of
from . import __version__
from . import orcarouter, provider
from .mcp import DEFAULT_BROWSER_ID, NOT_OPEN
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


# ⛔ `NO_BROWSERS` STOOD HERE: AN EMPTY WORKSPACE HANDED BACK WHENEVER THE
# ANSWER COULD NOT BE READ. It was written for a server older than 0.18.0,
# which answered `browser_list` in prose - and there is no such server to talk
# to any more: the interface SPAWNS the one it ships with, `python -m aihawk`
# out of this same package, so the two versions cannot differ. What the
# constant still did was make a failure look exactly like an empty room. That
# was survivable while the body carried a `limit` no other path would produce;
# with `limit` gone in 0.55.0 the fallback became byte-identical to a genuine
# "nothing is open", so a link that had stopped answering drew the same
# picture as a session where nobody had opened anything.
#
# It is a 503 with the reason now, the same shape `/live/frame` already uses,
# and the page keeps the stage it has rather than emptying it.


# --- which conversation -------------------------------------------------------

async def named(sessions: Sessions, session_id: str | None) -> ChatService:
    """The conversation with this id, refusing one nobody declared.

    ⛔ ONE PLACE TURNS AN ID OFF THE WIRE INTO A CONVERSATION, because the id
    does not always arrive the same way: eight routes carry it in the query
    string and the rename carries it in the body. Written twice, the rename is
    where it would have gone on resurrecting deleted sessions after the eight
    beside it had stopped.

    ⛔ ASYNC, BECAUSE `get` SPAWNS A CONNECTION OF ITS OWN. Each conversation
    has its own MCP server process since the tool surface stopped taking a
    session argument, so the first ask for one may have to start it - the same
    lazy cost `browser_open` already pays, moved one level up.
    """
    if not sessions.knows(session_id):
        raise SessionGone(session_id or "")
    return await sessions.get(session_id)


async def which(request: Request) -> ChatService:
    """The conversation this request is about.

    ⛔ EVERY ROUTE GOES THROUGH HERE, the live ones included. A route that read
    the session id and a route that did not would act on two different
    conversations while the page showed one, and the way that fails is the
    picture on the right belonging to somebody else's browser. A caller that
    names nothing gets the default conversation, which is what every page
    written before this existed does.

    ⛔ AND IT REFUSES AN ID NOBODY DECLARED, instead of declaring it. A request
    is a way to look at a conversation, never a way to start one -
    `/sessions/new` is. See `Sessions.knows` for what a page left open on a
    deleted session did to it.
    """
    return await named(request.app.state.sessions, request.query_params.get("s"))


# --- the page and the sessions ------------------------------------------------

async def root(_request: Request) -> HTMLResponse:
    return HTMLResponse(PAGE)


async def listing(request: Request) -> JSONResponse:
    return JSONResponse({"sessions": request.app.state.sessions.listing(),
                         "default": DEFAULT_CHAT_ID})


async def new_session(request: Request) -> JSONResponse:
    service = await request.app.state.sessions.new()
    return JSONResponse({"id": service.session_id, "name": service.name})


async def rename_session(request: Request) -> JSONResponse:
    body = await request.json()
    at = (body or {}).get("id") or DEFAULT_CHAT_ID
    sessions = request.app.state.sessions
    service = await named(sessions, at)
    done = await sessions.rename(at, (body or {}).get("name", ""))
    return JSONResponse({"renamed": done, "name": service.name})


async def forget_session(request: Request) -> JSONResponse:
    body = await request.json()
    at = (body or {}).get("id")
    if not at:
        return JSONResponse({"error": "no id"}, status_code=400)
    return JSONResponse({"forgotten": await request.app.state.sessions.forget(at)})


def vanished(_request: Request, exc: Exception) -> JSONResponse:
    """410, because the conversation existed and does not any more.

    Not 404: the page asking is a page that HAD this conversation open, and the
    difference between "there is no such thing" and "this is over" is the
    difference between a page that says something wrong happened and a page
    that says what happened. It is also the only status the page reads as a
    reason to stop asking - anything else is a failure worth retrying.
    """
    return JSONResponse({"error": "this conversation was deleted",
                         "id": getattr(exc, "session_id", "")},
                        status_code=410)


# --- the conversation -----------------------------------------------------------

async def send(request: Request) -> JSONResponse:
    body = await request.json()
    text = (body or {}).get("text", "")
    if not text:
        return JSONResponse({"error": "empty"}, status_code=400)
    (await which(request)).start(text)
    return JSONResponse({"accepted": True})


async def stop(request: Request) -> JSONResponse:
    return JSONResponse({"stopped": (await which(request)).stop()})


async def fresh(request: Request) -> JSONResponse:
    service = await which(request)
    done = service.reset()
    if done:
        # Told to every listener, not just the tab that asked: two tabs on one
        # session must not disagree about what the conversation is.
        await service.emit("fresh", "1")
        service.save()
    return JSONResponse({"fresh": done})


async def events(request: Request) -> StreamingResponse:
    service = await which(request)
    q = service.subscribe()
    # Freeze the replay/live boundary while subscribing. StreamingResponse
    # starts `stream` later, so taking this snapshot inside it would let an
    # intervening event appear in both history and the listener's queue.
    history = list(service.history)
    # Taken with the snapshot, for the same reason: whether a run is in flight
    # is part of the state this listener is joining.
    joining_a_run = service.busy

    # ⛔ WHERE THIS LISTENER GOT TO, AND WHETHER IT IS EVEN THE SAME
    # CONVERSATION. `EventSource` reconnects by itself after any drop, and
    # until this was read the server answered every reconnection with the
    # whole transcript again, while the page - which has no de-duplication and
    # had never been given an id to resume from - appended a second copy of
    # everything. Measured: three consecutive subscriptions each received all
    # 21 events of the same conversation.
    #
    # What the header means, and why a position alone is not enough, is in
    # `resume_point`. It is not repeated here: written in both places it would
    # be two accounts of one rule, free to disagree.
    marker = request.headers.get("last-event-id") or ""
    resume_from, same_conversation = resume_point(marker, service.epoch)
    replay = history[resume_from:] if same_conversation else history

    async def stream() -> AsyncIterator[bytes]:
        try:
            yield sse({"kind": "model", "text": service.model_label})
            if not same_conversation and marker:
                # It reconnected carrying a position from another transcript,
                # so what it is still showing is not this one.
                #
                # ⛔ AND IT SAYS WHICH OF THE TWO THINGS THIS IS. `fresh` is
                # also what `/chat/fresh` emits when somebody presses Clear,
                # and the page answered both by wiping - which drops the
                # message they had typed and queued. Clearing a conversation
                # deliberately is one thing; reconnecting to a process that
                # restarted is another, and only one of them is a reason to
                # throw away somebody's sentence. The reason travels in the
                # text rather than in a new kind, the way `busy` already
                # carries "1" and "0": a page older than this server keeps
                # doing exactly what it did before instead of drawing a word
                # it has never heard of into the transcript.
                yield sse({"kind": "fresh", "text": "rewound"})
            # Flagged as replay so the page does not animate forty rows at once
            # and does not start a stopwatch on work that finished before this
            # listener existed. Numbered so the next reconnection can say where
            # it got to instead of starting over.
            for offset, past in enumerate(replay):
                yield sse({**past, "replay": True},
                          marker_at(service.epoch, resume_from + offset))
            # And then the CURRENT state, which the replay above cannot carry:
            # `emit` keeps `busy` out of the history on purpose, so a page
            # opened long after a run would not show a spinner for work that
            # ended an hour ago. That is right for a finished run and wrong for
            # one still going - the page would show a transcript growing under
            # a composer that says nothing is happening, and with no turn
            # ceiling the stop button is the only thing that ends such a run.
            # So it is sent as what it is, the present, and only when true: a
            # page starts out believing it is idle.
            # ⛔ AND IT IS SENT WHEN FALSE TOO, WHICH IS NOT SYMMETRY FOR ITS
            # OWN SAKE: without it the last thing the model said was never
            # drawn. The page holds one narration line back so that a sentence
            # with tool calls after it reads as their lead-in and one with
            # nothing after it reads as the answer, and the event that resolves
            # that lookahead is the end of the turn - which is a `busy` going
            # false. A replay carries no `busy` at all, so a page reopening a
            # FINISHED conversation sat holding its last sentence forever.
            # Measured on the developer's own saved session: 257 events ending
            # in `said`, and the answer to the last thing they asked was not on
            # the screen. Marked as replay so it flushes without animating one
            # row and without redrawing the session list, exactly like the
            # events above it.
            # The two are NOT one line with a conditional inside: the live one
            # must arrive unflagged or the page calls `waited()` where it
            # should call `waiting()`, and a run in progress would lose its
            # clock.
            if joining_a_run:
                yield sse({"kind": "busy", "text": "1"})
            else:
                yield sse({"kind": "busy", "text": "0", "replay": True})
            while True:
                event = await q.get()
                # Only what the history keeps is numbered: an id moves the
                # resume point, and `busy` is not a place to resume from.
                # Leaving the field out keeps the last one, which is what the
                # spec says and what is wanted here.
                if event["kind"] in ("busy", "fresh"):
                    yield sse(event)
                else:
                    yield sse(event, marker_at(service.epoch,
                                               len(service.history) - 1))
        finally:
            service.unsubscribe(q)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store"})


# --- the live browsers ----------------------------------------------------------

async def frame(request: Request) -> Response:
    """The window the active tab lives in, as `browser_watch` captures it.

    Not `browser_take_screenshot`: that is the page alone, and the engine draws
    the pointer outside the page on purpose, so no screenshot can show it. The
    window capture shows the pointer, the tab strip and the address bar, keeps
    answering while a page loads, and costs one frame the server already holds
    rather than a paint. The tool exists from 0.15.0 of the server, which is
    the floor pyproject declares.

    The strip and the address in the picture are pixels; the ones the page
    draws above it are the same facts as elements, and those can be clicked
    and copied. Both stay.

    ⛔ AND THERE IS NO GUARD HERE ANY MORE, WHICH IS THE POINT. There used to
    be one, reading whether this conversation had ever called anything, and it
    was armed by the one call that starts nothing - so the next frame through
    it started an engine: measured on 0.38.0, 9 firefox processes to 16 for a
    session nobody had asked anything, and the capture then failed anyway.
    Asking the free question here instead was tried and measured too, and it
    is the wrong place: `browser_list` costs 30 ms against the capture's 1, so
    paying it every frame caps the pane at 32 a second to answer a question
    whose answer is almost always yes. `browser_watch` refuses without
    starting now, so the cheap path is the common one and this route simply
    asks.
    """
    seen = await which(request)
    # ⛔ THE PANE SAYS WHICH BROWSER, and without that the workspace is one
    # picture drawn twice. `browser` is the caller's to choose here exactly as
    # `session_id` is not: which SESSION a request belongs to is decided by the
    # page's own url and imposed, while which BROWSER inside it a pane is
    # watching is what the pane is for.
    watching = request.query_params.get("b") or None
    try:
        result = await seen.link.call("browser_watch",
                                      {"browser": watching} if watching else {})
    except Exception as exc:
        return JSONResponse({"error": str(exc)[:200]}, status_code=503)
    got = image_of(result)
    if got is None:
        # A tool that raised reaches a client as an error RESULT with the
        # reason as text, not as an exception: an engine without the
        # screencast, or a window captured as nothing. That is a 503 with the
        # reason, never a 204, which would read as "nothing to look at" in the
        # one case where a person needs to read a sentence.
        # Both halves from `answer_of`, which is the one reader of this wire format:
        # this line used to spell the flag out for itself, beside a `text_of`
        # that the agent loop was separately copying. Three readers of one
        # result, now one.
        text, failed = answer_of(result)
        reason = text if failed else ""
        if reason and NOT_OPEN % (watching or DEFAULT_BROWSER_ID) not in reason:
            return JSONResponse({"error": reason[:200]}, status_code=503)
        # And one refusal is not a failure at all: a browser that is not
        # open is nothing to look at, which is the idle pane. Compared
        # against the sentence itself rather than guessed at from its shape -
        # the two ship in one package, so there is one string. A browser
        # that is GONE is a different sentence and a 503: the pane says it.
        return Response(status_code=204)
    jpeg, mime = got
    return Response(jpeg, media_type=mime, headers={"Cache-Control": "no-store"})


async def browsers(request: Request) -> JSONResponse:
    """The panes to draw: which browsers this session holds, and where.

    Asked of the server through the same tool an agent would call, because the
    interface has no privileged path to the browsers - and it starts nothing,
    so drawing the workspace can never cost an engine.

    ⛔ AND IT ASKS EVEN WHEN THIS CONVERSATION HAS DONE NOTHING. A session
    reopened after a restart has browsers it declared and no instruction yet,
    so a guard on "has this conversation called anything" would leave the
    workspace empty in exactly the case the declarations exist for - and the
    panes offering to wake them would never be drawn. `browser_list` starts
    nothing, by construction and by its own test, so asking is free.
    """
    seen = await which(request)
    try:
        said = await seen.link.call_text("browser_list")
    except Exception as exc:
        return JSONResponse({"error": str(exc)[:200]}, status_code=503)
    try:
        got = json.loads(said)
    except ValueError:
        got = None
    if not isinstance(got, dict):
        # Said rather than smoothed over: this is the tool answering something
        # other than its own JSON, which is either an error result carrying its
        # reason as text or a server that is not this one. Both are worth a
        # sentence; neither is an empty workspace.
        return JSONResponse({"error": said[:200] or "the workspace could not be read"},
                            status_code=503)
    # ⛔ AND THE BUILD RIDES ALONG, on the one question every page asks every
    # three seconds. A page left open across an upgrade goes on running the
    # script it was served, against a server that has moved: nothing says so
    # unless a route it asks for has gone away entirely, which most versions do
    # not do. The page keeps the first build it is told and says something the
    # moment that changes. It travels as a FIELD rather than as an event
    # because an older page ignores a field it does not know and would have
    # drawn an unknown event into the transcript as a sentence.
    return JSONResponse({"browsers": got.get("browsers") or [],
                         "focus": got.get("focus") or "",
                         "build": __version__})


# ⛔ `/live/address` STOOD HERE, AND THIS BRANCH IS WHAT MADE IT A DUPLICATE.
# It replaced `/live/tabs`, which asked the tab tool - a different question -
# and once both routes asked `browser_list` the page was paying a round trip
# every two seconds for a field the rows above already carry, on a second
# timer that could name a different moment. It is read in the page now, from
# the fleet it already holds, because which browser is being WATCHED is a fact
# of the page: a pinned pane changes it instantly and a server asked three
# seconds ago cannot know.


# --- the provider -----------------------------------------------------------------

def registry(request: Request) -> provider.ProviderState:
    """The provider state this app was built with.

    One object per app rather than one per request: which provider is chosen,
    which credential it holds and which model list it was given are facts about
    this process, not about a request, and a state built per request would
    forget the sign-in between two clicks.
    """
    return request.app.state.provider


async def provider_state(request: Request) -> JSONResponse:
    """What the panel draws: the provider, its credential, and its models.

    ⛔ THE KEY IS NOT IN THIS ANSWER. `Credential.as_state` returns a mask and
    four facts about the credential; the key itself never crosses this wire,
    because the page is a browser and a browser is not a place to hold one. The
    catalogue is fetched by the SERVER for the same reason.
    """
    return JSONResponse(registry(request).as_state())


async def provider_choose(request: Request) -> JSONResponse:
    """Point this interface at a provider, and at a model if one is named.

    ⛔ THE MODEL IS REVALIDATED HERE, NOT ASSUMED. A model id that the current
    provider's list does not offer is refused with the id in the answer rather
    than stored and left to fail at the first turn, where the reason would be
    nowhere near the cause.
    """
    body = await request.json()
    state = registry(request)
    asked = (body or {}).get("model")
    state.choose((body or {}).get("provider"), asked)
    refused = bool(asked) and not state.model
    return JSONResponse({**state.as_state(), "refused": refused, "note":
                         "That model is not in this provider's list, so it was "
                         "not selected." if refused else ""})


async def provider_key(request: Request) -> JSONResponse:
    """Adapter one: the key the user pasted.

    Kept only if it is a real string, and stored through the same path the
    sign-in uses, so there is one credential and one store. `remove` is how the
    user clears it, which is the only way a credential leaves this process
    without a replacement - a `401` marks it instead.
    """
    body = await request.json()
    state = registry(request)
    if (body or {}).get("remove"):
        provider.forget_credential()
        state.set_credential(None)
        return JSONResponse({**state.as_state(),
                             "note": "The OrcaRouter key was removed."})
    given = str((body or {}).get("key") or "").strip()
    if not given:
        return JSONResponse({"error": "no key"}, status_code=400)
    state.attempt += 1
    credential = orcarouter.Credential(given, method=orcarouter.BY_KEY,
                                       source="entered",
                                       generation=state.attempt)
    state.set_credential(credential)
    provider.save_credential(credential)
    await refresh_models(state)
    return JSONResponse({**state.as_state(), "note": "The OrcaRouter key was saved."})


async def provider_models(request: Request) -> JSONResponse:
    """The model list the dropdown draws, filtered by capability.

    ⛔ ONE ENDPOINT, AND THE FILTER IS ARGUED FOR RATHER THAN GUESSED. The
    catalogue is the only fact source for what a model can do, so a capability
    the catalogue does not mention is one the model is not offered for. A live
    answer replaces the seed entirely; a failed one falls back to the seed and
    says so, so the control never becomes a free-text box.
    """
    state = registry(request)
    capability = request.query_params.get("capability") or "chat"
    modality = request.query_params.get("modality") or None
    offered = state.offered(capability, modality)
    return JSONResponse({
        "source": state.source,
        "error": state.catalog_error,
        "capability": capability,
        "modality": modality,
        "selected": state.model,
        "models": [m.as_state() for m in offered],
    })


async def refresh_models(state: provider.ProviderState) -> None:
    """Ask the catalogue for this account's models, and take the answer.

    ⛔ THE SEED IS THE FALLBACK AND IT IS LABELLED. A discovery that fails
    leaves a usable, verified, short list and a source the panel can show,
    rather than an empty dropdown and a person typing a model id from memory.
    """
    credential = state.credential
    if credential is None or not credential.key:
        state.set_catalog(orcarouter.seed_models(), orcarouter.SEED_SOURCE,
                          "no credential")
        return
    try:
        found = await orcarouter.fetch_catalog(credential.key)
    except Exception as exc:
        state.set_catalog(orcarouter.seed_models(), orcarouter.SEED_SOURCE,
                          str(exc)[:200])
        return
    state.set_catalog(found, orcarouter.LIVE_SOURCE)


async def provider_refresh(request: Request) -> JSONResponse:
    """Ask for the catalogue again, on the user's command."""
    state = registry(request)
    await refresh_models(state)
    return JSONResponse(state.as_state())


async def provider_connect(request: Request) -> JSONResponse:
    """Adapter two, first half: start a PKCE sign-in and answer with the URL.

    ⛔ THE VERIFIER STAYS HERE. The page is given a URL to open and an attempt
    number; the verifier, the state and the loopback port never leave this
    process, and the comparison that guards the code happens on this side.
    """
    state = registry(request)
    state.attempt += 1
    login = orcarouter.PkceLogin()
    url = login.start()
    request.app.state.logins[state.attempt] = login
    return JSONResponse({"attempt": state.attempt, "url": url,
                         "callback": login.callback_url})


async def provider_login(request: Request) -> JSONResponse:
    """Adapter two, second half: wait for the code, exchange it, persist it.

    ⛔ THE ATTEMPT NUMBER IS CHECKED BEFORE ANYTHING IS WRITTEN. A code that
    arrives for an attempt the user has already abandoned - because they
    cancelled, or started another one - must not become this process's
    credential: the answer is a refusal that names the attempt, and the live
    credential is untouched.
    """
    body = await request.json()
    state = registry(request)
    attempt = int((body or {}).get("attempt") or 0)
    login = request.app.state.logins.get(attempt)
    if login is None or attempt != state.attempt:
        return JSONResponse({"error": "that sign-in is no longer the current one"},
                            status_code=409)
    code = str((body or {}).get("code") or "").strip()
    if code:
        login.submit(code)
    try:
        code = await login.wait(timeout=float((body or {}).get("wait") or 300))
        credential = await login.exchange(code)
    except orcarouter.PkceError as exc:
        login.close()
        request.app.state.logins.pop(attempt, None)
        if attempt == state.attempt:
            state.attempt += 1
        return JSONResponse({"error": str(exc)}, status_code=400)
    finally:
        login.close()
    request.app.state.logins.pop(attempt, None)
    if attempt != state.attempt:
        # ⛔ THE STALE ANSWER IS DISCARDED, NOT WRITTEN. A second sign-in that
        # started while this one was in the air owns the credential now, and a
        # late success must not overwrite it - that is how a page ends up
        # holding an account the user did not choose.
        return JSONResponse({"error": "a newer sign-in replaced this one"},
                            status_code=409)
    state.attempt += 1
    credential.generation = state.attempt
    state.set_credential(credential)
    provider.save_credential(credential)
    await refresh_models(state)
    return JSONResponse({**state.as_state(), "note": "Signed in to OrcaRouter."})


async def provider_cancel(request: Request) -> JSONResponse:
    """Release a sign-in attempt: its listener, its code and its slot.

    ⛔ EVERY WAY OUT COMES THROUGH HERE, and the browser can reach it on the way
    out of the page. A `pagehide` cancels with `keepalive`, which outlives the
    document being torn down; the body it sends is JSON, and a body that will
    not parse is read as "cancel the current attempt" rather than answered with
    a 400 - a page leaving must not be told its request was malformed when the
    request was exactly the one this route is for.
    """
    state = registry(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    attempt = int((body or {}).get("attempt") or state.attempt)
    login = request.app.state.logins.pop(attempt, None)
    if login is not None:
        login.close()
    if attempt == state.attempt:
        state.attempt += 1
    return JSONResponse({"cancelled": login is not None, "attempt": state.attempt})


async def provider_reauth(request: Request) -> JSONResponse:
    """A `401` from the relay: mark THIS credential, do not refresh anything.

    ⛔ A DURABLE KEY HAS NO REFRESH GRANT, and this route is the one that
    refuses to pretend otherwise. What a `401` means is that the user revoked
    the app or the key, and the honest answer is to mark the exact credential
    generation that made the rejected request as needing a new sign-in. A late
    failure from an old generation is ignored rather than applied to whatever
    is current, because the alternative is a freshly reauthorized credential
    being marked broken by a request made before it existed.
    """
    body = await request.json()
    state = registry(request)
    generation = int((body or {}).get("generation") or 0)
    credential = state.credential
    if credential is None:
        return JSONResponse({"marked": False, "reason": "no credential"})
    if generation and generation != credential.generation:
        return JSONResponse({"marked": False, "reason": "a stale generation"})
    credential.needs_reauth = True
    return JSONResponse({"marked": True, "generation": credential.generation,
                         "note": "OrcaRouter refused the key, so it needs signing "
                                 "in again. Nothing was deleted; sign in to "
                                 "replace it.", **state.as_state()})


def build_app(sessions: Sessions, state: Optional[provider.ProviderState] = None) -> Starlette:
    """The app: these routes, over this registry of conversations."""
    app = Starlette(exception_handlers={SessionGone: vanished}, routes=[
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
        # The provider, added with OrcaRouter: which model, which credential,
        # which models the account can actually call.
        Route("/provider/state", provider_state),
        Route("/provider/choose", provider_choose, methods=["POST"]),
        Route("/provider/key", provider_key, methods=["POST"]),
        Route("/provider/models", provider_models),
        Route("/provider/refresh", provider_refresh, methods=["POST"]),
        Route("/provider/connect", provider_connect, methods=["POST"]),
        Route("/provider/login", provider_login, methods=["POST"]),
        Route("/provider/cancel", provider_cancel, methods=["POST"]),
        Route("/provider/reauth", provider_reauth, methods=["POST"]),
    ])
    app.state.sessions = sessions
    app.state.provider = state or provider.ProviderState()
    #: The sign-in attempts in flight, by attempt number. Here rather than in
    #: the provider state because a login is not a fact the page is told about
    #: - it is a listener this process holds and must release.
    app.state.logins = {}
    return app
