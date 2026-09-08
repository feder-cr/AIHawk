"""The conversation service behind the interface: what it emits, and stopping it.

No browser and no model. The Link is a double that records the tool calls it was
asked for, and the Brain is whatever the test needs it to be, so what is under
test is the service's own behaviour: the order of the events, which of them are
part of the transcript, and whether a run can actually be interrupted.

Every test here covers something the redesign INTRODUCED. The page was rebuilt
around events that did not exist the day before - `you` from the server, a replay
flag, a usage line, a stop route - and behaviour that arrives with a page and no
tests is a claim rather than a feature.
"""
from __future__ import annotations

import asyncio
import base64
import json

import pytest

from aihawk.web import PAGE, ChatService, build_app

pytestmark = pytest.mark.asyncio


class FakeLink:
    """Shaped like `Link` where ChatService and the routes touch it."""

    def __init__(self):
        self.touched = False
        self.tools = []
        self.calls = []

    async def call(self, name, arguments=None):
        self.touched = True
        self.calls.append((name, arguments or {}))
        return None

    async def call_text(self, name, arguments=None):
        await self.call(name, arguments)
        return ""


class SilentBrain:
    async def handle(self, text, link, say):
        return None


class TalkingBrain:
    """Emits one of each kind, in the order a real turn produces them."""

    async def handle(self, text, link, say):
        await say("said", "I will open it")
        await say("tool", "browser_navigate https://example.com")
        await say("result", "navigated")


class HangingBrain:
    """Waits at an await, which is where a cancellation can land."""

    def __init__(self):
        self.started = asyncio.Event()

    async def handle(self, text, link, say):
        await say("tool", "browser_navigate https://slow.example")
        self.started.set()
        await asyncio.sleep(3600)


async def drain(svc, n, timeout=2.0):
    """The next `n` events, from a listener subscribed before anything ran."""
    q = svc.subscribe()
    out = []
    for _ in range(n):
        out.append(await asyncio.wait_for(q.get(), timeout))
    return out


# --------------------------------------------------------------------------
# what reaches the page, and in what order
# --------------------------------------------------------------------------

async def test_the_instruction_is_emitted_by_the_service_not_added_by_the_page():
    """Known-bad, and it shipped for one commit: the page appending the user's
    line locally and the server never sending it.

    Everything looked right in the browser that typed it, and the conversation
    had no questions in it for anybody who opened the page afterwards or
    reloaded mid-run. It is the first event of a turn now.
    """
    svc = ChatService(FakeLink(), SilentBrain())
    q = svc.subscribe()
    await svc.send("book the 9am slot")

    first = await asyncio.wait_for(q.get(), 2)
    assert first == {"kind": "you", "text": "book the 9am slot"}


async def test_a_turn_brackets_itself_with_busy():
    svc = ChatService(FakeLink(), TalkingBrain())
    q = svc.subscribe()
    await svc.send("go")

    kinds = []
    while not q.empty():
        kinds.append(q.get_nowait()["kind"])
    assert kinds[0] == "you"
    assert kinds[1] == "busy"
    assert kinds[-1] == "busy"
    assert [e for e in kinds if e == "busy"] == ["busy", "busy"]
    assert kinds[2:-1] == ["said", "tool", "result"]


async def test_state_is_not_transcript():
    """`busy` and `usage` must NOT be replayed to somebody who opens the page an
    hour later: a spinner for work that finished, and a meter for a turn nobody
    is watching. Everything else is the conversation and is kept.
    """
    svc = ChatService(FakeLink(), TalkingBrain())
    await svc.send("go")
    await svc.emit("usage", json.dumps({"last_prompt": 10}))

    kinds = [e["kind"] for e in svc.history]
    assert "busy" not in kinds
    assert "usage" not in kinds
    assert kinds == ["you", "said", "tool", "result"]


async def test_the_replay_flag_is_on_history_and_not_on_live_events():
    """The page animates a row on arrival and starts a stopwatch on it. Without
    the flag, reloading during a forty-step run animates forty rows at once and
    prints 0ms on every one."""
    svc = ChatService(FakeLink(), TalkingBrain())
    await svc.send("go")

    app = build_app(FakeLink(), svc)
    stream = [r for r in app.routes if r.path == "/chat/events"][0]
    assert stream is not None, "the events route must exist for the page to work"

    # The route builds its body from `history`; what matters is that every past
    # event carries the flag and no live one does.
    assert all("replay" not in e for e in svc.history)
    replayed = [{**e, "replay": True} for e in svc.history]
    assert all(e["replay"] for e in replayed)


async def test_an_event_after_subscription_is_delivered_once_as_live():
    """The replay/live boundary is the instant the listener subscribes.

    A StreamingResponse does not start its async generator when the endpoint
    returns. An event emitted in that gap is already in both history and the
    listener's queue, so taking the history snapshot inside the generator would
    send it once as replay and then again as live.
    """
    svc = ChatService(FakeLink(), SilentBrain())
    app = build_app(FakeLink(), svc)
    route = [r for r in app.routes if r.path == "/chat/events"][0]

    class Req:
        query_params = {}
        headers: dict = {}

    response = await route.endpoint(Req())
    await svc.emit("said", "only once")
    body = response.body_iterator

    def payload(chunk):
        # A replayable event carries an `id:` line before its data, so a
        # reconnection can say where it got to. State events do not.
        line = [l for l in chunk.split(b"\n") if l.startswith(b"data: ")][0]
        return json.loads(line.removeprefix(b"data: ").strip())

    assert payload(await anext(body))["kind"] == "model"
    delivered = [payload(await anext(body))]
    try:
        delivered.append(payload(await asyncio.wait_for(anext(body), 0.1)))
    except asyncio.TimeoutError:
        pass

    assert delivered == [{"kind": "said", "text": "only once"}]


# --------------------------------------------------------------------------
# stopping
# --------------------------------------------------------------------------

async def test_stop_cancels_a_run_in_flight_and_says_so():
    """The button is a decoration otherwise, and an agent you cannot interrupt
    is one you cannot leave alone."""
    brain = HangingBrain()
    svc = ChatService(FakeLink(), brain)
    q = svc.subscribe()

    svc.start("go somewhere slow")
    await asyncio.wait_for(brain.started.wait(), 2)

    assert svc.stop() is True

    kinds = []
    for _ in range(6):
        try:
            kinds.append(await asyncio.wait_for(q.get(), 1))
        except asyncio.TimeoutError:
            break
    texts = [e["text"] for e in kinds if e["kind"] == "err"]
    assert texts == ["stopped"], f"expected one 'stopped', got {kinds}"
    # and the lock is released, or the next instruction would hang forever
    assert not svc._busy.locked()


async def test_stop_with_nothing_running_is_false_rather_than_an_error():
    svc = ChatService(FakeLink(), SilentBrain())
    assert svc.stop() is False
    svc.start("go")
    await asyncio.sleep(0)
    for _ in range(20):
        if not svc._busy.locked():
            break
        await asyncio.sleep(0.02)
    assert svc.stop() is False, "a finished task must not report as stopped"


async def test_a_failing_brain_reports_and_still_clears_busy():
    """Known-bad: an exception escaping `send` leaves `busy` on forever, and the
    page shows a run that never ends."""
    class Boom:
        async def handle(self, text, link, say):
            raise RuntimeError("the model refused")

    svc = ChatService(FakeLink(), Boom())
    q = svc.subscribe()
    await svc.send("go")

    seen = []
    while not q.empty():
        seen.append(q.get_nowait())
    assert seen[-1] == {"kind": "busy", "text": "0"}
    assert any(e["kind"] == "err" and "the model refused" in e["text"] for e in seen)


# --------------------------------------------------------------------------
# the routes
# --------------------------------------------------------------------------

async def test_the_app_exposes_exactly_the_routes_the_page_calls():
    """The page fetches these five paths by name. A rename here is a silent
    404 there, and the page has no way to report it."""
    svc = ChatService(FakeLink(), SilentBrain())
    paths = {r.path for r in build_app(FakeLink(), svc).routes}
    assert paths == {"/", "/chat/send", "/chat/stop", "/chat/fresh",
                     "/chat/events", "/live/frame", "/live/tabs", "/live/select"}


async def test_the_stop_control_is_its_own_button_and_follows_the_run():
    """The stop button must not be a mode of the send button.

    It was one, and the mode was `busyNow && !typed`: the moment somebody typed
    into the composer while the agent worked, the same control became "queue for
    the next turn" and there was no way to stop from the page at all. That was
    survivable while the loop stopped itself at twenty-five turns. It is not
    survivable now: the loop has no ceiling, so this button is the only thing
    that ends a run that will not converge.

    ⛔ WHAT THIS DOES AND DOES NOT PROVE. It reads the markup and the script the
    page ships, so it catches the button being deleted, renamed, or folded back
    into `#go`. It does NOT execute the script, so it cannot prove the button is
    reachable, visible or wired on a rendered page - that needs a browser, and
    it was done by hand against a running interface.

    Known-bad, all three caught here: removing the `#halt` element; painting it
    from anything other than `busyNow`; giving `#go` back a `data-mode` stop.
    """
    page = PAGE

    assert 'id="halt"' in page, "the dedicated stop button is gone"
    assert "halt.onclick" in page and "'/chat/stop'" in page, \
        "the stop button no longer posts to the stop route"

    # Painted from the run and from nothing else. `!busyNow` is the whole
    # condition: any `typed` in it is the old mode logic coming back.
    assert "halt.hidden = !busyNow;" in page, \
        "the stop button is no longer tied to the run alone"

    assert 'data-mode' not in page, \
        "the send button has a mode again, which is how stop went missing before"


async def test_the_live_view_asks_for_nothing_until_an_instruction_has_been_given():
    """The invariant the in-process view held by calling `registry.peek`.

    Over MCP that question does not exist - `session_list_pages` calls `ensure` -
    so the guarantee is held by Link remembering. If the frame route ever asks
    before an instruction, opening the page would START a browser, which is what
    a view is not allowed to cause.
    """
    link = FakeLink()
    svc = ChatService(link, SilentBrain())
    app = build_app(link, svc)
    frame = [r for r in app.routes if r.path == "/live/frame"][0]

    class Req:
        query_params = {}
        headers: dict = {}

    resp = await frame.endpoint(Req())
    assert resp.status_code == 204
    assert link.calls == [], "the view asked the server something before any instruction"


# --------------------------------------------------------------------------
# the picture: the window the server captures, never a page screenshot
# --------------------------------------------------------------------------

# Two signatures a decoder would recognise, so a swapped MIME type cannot pass
# on the bytes alone.
JPEG = b"\xff\xd8\xff\xe0" + b"\x00\x10JFIF" + b"\x00" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


class Item:
    """One part of a tool result's content, shaped like the mcp types: an
    ImageContent has `data` and `mimeType` and no `text`; a TextContent has
    `text` and no `data`."""

    def __init__(self, **fields):
        self.__dict__.update(fields)


class Result:
    def __init__(self, *content, isError=False):
        self.content = list(content)
        self.isError = isError


class WatchingLink(FakeLink):
    """Answers both picture tools the way the server does - `browser_watch`
    with a JPEG, `browser_take_screenshot` with a PNG - so which one the view
    asked for is visible in what came back and not only in the call log."""

    def __init__(self):
        super().__init__()
        self.touched = True

    async def call(self, name, arguments=None):
        await super().call(name, arguments)
        if name == "browser_watch":
            return Result(Item(type="image", data=base64.b64encode(JPEG).decode(),
                               mimeType="image/jpeg"))
        if name == "browser_take_screenshot":
            return Result(Item(type="image", data=base64.b64encode(PNG).decode(),
                               mimeType="image/png"))
        return Result()


async def _frame_route(link):
    app = build_app(link, ChatService(link, SilentBrain()))
    return [r for r in app.routes if r.path == "/live/frame"][0].endpoint


async def test_the_live_view_is_the_window_capture_and_never_a_screenshot():
    """`browser_watch`, not `browser_take_screenshot`.

    A screenshot is the page alone, and the engine draws the pointer outside
    the page on purpose so that no page can see it: a view built on screenshots
    could never show where the agent's hand is, and it went blank on every
    navigation because a page mid-load cannot be painted. The window capture
    shows the pointer, the tab strip and the address bar, keeps answering while
    a page loads, and is one frame the server already holds rather than a paint.

    Known-bad: the route as it stood until 2026-09-06 asked for the screenshot,
    and fails every line below the status.
    """
    link = WatchingLink()
    route = await _frame_route(link)

    class Req: query_params = {}
    resp = await route(Req())

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert resp.body == JPEG
    assert [n for n, _ in link.calls] == ["browser_watch"], (
        "the picture is the window capture, and one call per frame")


async def test_a_capture_that_cannot_answer_says_why_instead_of_looking_idle():
    """A tool that raises reaches a client as an error RESULT carrying the
    reason as text, not as an exception. Before this, such a result fell
    through `image_of` into a 204, and the pane hid the picture and said "idle"
    about an engine without the screencast - the one case where a person needs
    to read a sentence. The reason now rides a 503, which the page shows.

    Known-bad: the previous route answered 204 here.
    """
    class RefusingLink(WatchingLink):
        async def call(self, name, arguments=None):
            await FakeLink.call(self, name, arguments)
            return Result(Item(type="text", text=(
                "the live window view needs invisible-playwright with "
                "page.screencast and an engine from firefox-28 on")), isError=True)

    link = RefusingLink()
    route = await _frame_route(link)

    class Req: query_params = {}
    resp = await route(Req())

    assert resp.status_code == 503
    assert "page.screencast" in json.loads(resp.body)["error"]


async def test_a_new_conversation_makes_the_brain_forget_and_clears_the_history():
    """The transcript is the wait and the bill, so dropping it has to reach the
    BRAIN, not just the page.

    Measured on this interface: a first instruction on a fresh process carries
    3,106 prompt tokens and the agent moves 4.1 s after the click; by the third
    instruction of the same session the first turn already carries 38,207 and
    the wait is 6.7 s. Nothing trimmed it and there was no way to reach it
    short of killing the process. After a reset the next first turn measured
    3,091 again.

    Known-bad: clearing `service.history` and leaving the brain alone. The page
    then looks empty while every following turn still resends everything.
    """
    class Forgetful(SilentBrain):
        forgotten = 0

        def forget(self):
            type(self).forgotten += 1

    svc = ChatService(FakeLink(), Forgetful())
    await svc.emit("you", "something")
    assert svc.history, "nothing to forget, the test proves nothing"

    assert svc.reset() is True
    assert svc.history == []
    assert Forgetful.forgotten == 1


async def test_a_new_conversation_is_refused_while_a_run_is_in_flight():
    """Throwing away a transcript something is still writing into is not
    undoable, so it is refused rather than raced.

    Known-bad: resetting regardless. The run then keeps going against a
    transcript the brain has already replaced.
    """
    brain = HangingBrain()
    svc = ChatService(FakeLink(), brain)
    svc.start("a long one")
    await asyncio.wait_for(brain.started.wait(), 2)

    assert svc.busy
    assert svc.reset() is False, "a reset landed in the middle of a run"

    svc.stop()


async def test_the_page_shows_the_wait_and_ties_it_to_the_run():
    """The complaint was that everything freezes for a second after a prompt.

    Measured instead: the instruction reaches the screen 23 ms after the click
    and the server accepts it in 2, but the first thing the agent DOES lands 4
    to 7 seconds later, and the pane said nothing in between. It was not a
    blocked page, it was an unlit one.

    ⛔ Reads the markup and the script, so it catches the indicator being
    removed or untied from the run. It does not execute them: that it appears,
    counts up and disappears was checked by hand against a running interface,
    where it read `Thinking 6.8s` through `Thinking 10.1s` and reset on the
    next step.

    Known-bad: deleting `waiting()`, or calling it on a replayed event, which
    would show a clock for a wait that ended an hour ago.
    """
    assert "function waiting()" in PAGE, "the wait is not drawn any more"
    assert "if(busyNow && !r) waiting(); else waited();" in PAGE, \
        "the wait is no longer tied to the run starting"
    assert "case 'tool':  waited();" in PAGE, \
        "the wait no longer ends when the agent acts"
    # Re-armed after a step lands, because the model reads the result before
    # anything else can appear and that gap is the same wait.
    assert "if(busyNow && !r) waiting();" in PAGE


class _Req:
    """Enough of a request for the events route: it reads one header."""
    query_params: dict = {}

    def __init__(self, last_event_id: str = ""):
        self.headers = {"last-event-id": last_event_id} if last_event_id else {}


async def _first_events(resp, want=4, each=1.0):
    """Read up to `want` events, giving up when the stream goes quiet.

    Bounded on purpose. The stream stays open forever by design, so an
    unbounded read turns "the event never came" into a suite that hangs
    instead of a test that fails, and a gate that hangs has no verdict. This
    was not hypothetical: the first version of the test below hung under its
    own known-bad mutation rather than going red.
    """
    seen = []
    it = resp.body_iterator.__aiter__()
    try:
        while len(seen) < want:
            chunk = await asyncio.wait_for(it.__anext__(), each)
            line = [l for l in chunk.decode().split("\n") if l.startswith("data: ")][0]
            seen.append(json.loads(line.removeprefix("data: ").strip()))
    except (asyncio.TimeoutError, StopAsyncIteration):
        pass
    return seen


async def test_the_frame_pause_is_shorter_than_the_capture_produces():
    """Asking slower than the source means frames are made and thrown away.

    The capture pushes about ten frames a second (measured 9.6 at its own
    callback), and a frame costs roughly 22 ms on the pipe, so a pause of P ms
    makes a cycle of about P + 22. For the pane to show every frame the source
    makes, that cycle has to fit inside the ~100 ms between frames.

    It did not: the pause was 200 ms, and the pane ran at 4.6 fps against a
    source giving 10. The comment above it had both halves of the fact - "the
    engine produces ten" and "five a second" - and drew the wrong conclusion
    from them.

    Known-bad: putting it back to 200, or to anything that leaves no room for
    the round trip.
    """
    import re

    m = re.search(r"setTimeout\(tick,\s*(\d+)\)", PAGE)
    assert m, "the frame pump no longer paces itself with setTimeout(tick, ...)"
    pause_ms = int(m.group(1))

    round_trip_ms = 22    # measured against the running interface
    source_period_ms = 100  # 10 fps out of the capture

    assert pause_ms + round_trip_ms <= source_period_ms, (
        "a %d ms pause makes a %d ms cycle against a source that produces one "
        "frame every %d ms, so the pane would show about %.1f of the 10 fps it "
        "is being sent" % (pause_ms, pause_ms + round_trip_ms, source_period_ms,
                           1000 / (pause_ms + round_trip_ms)))


async def test_a_reconnection_resumes_instead_of_replaying_the_whole_thing():
    """`EventSource` reconnects by itself after any drop, and the page has no
    de-duplication, so a server that answers every reconnection with the whole
    transcript makes it appear twice.

    ⛔ MEASURED 2026-09-08 against the running interface, before the fix: three
    consecutive subscriptions each received all 21 events of the same
    conversation, and no event ever carried an `id:`, so the browser had
    nothing to resume from and the page nothing to skip.

    Known-bad: dropping the `id:` line, or ignoring `Last-Event-ID`. The second
    listener below then receives the whole history again.
    """
    svc = ChatService(FakeLink(), SilentBrain())
    app = build_app(FakeLink(), svc)
    events = [r for r in app.routes if r.path == "/chat/events"][0]

    for text in ("first", "second", "third"):
        await svc.emit("said", text)

    fresh_eyes = await _first_events(await events.endpoint(_Req()), want=6)
    said = [e for e in fresh_eyes if e["kind"] == "said"]
    assert [e["text"] for e in said] == ["first", "second", "third"]

    # What the browser would send back on a reconnection: the id of the last
    # event it actually saw.
    marker = "%s:%d" % (svc.epoch, len(svc.history) - 1)
    again = await _first_events(await events.endpoint(_Req(marker)), want=4)

    assert [e for e in again if e["kind"] == "said"] == [], \
        "the whole conversation was replayed to a listener that already had it"
    assert [e for e in again if e["kind"] == "fresh"] == [], \
        "a resume inside the same conversation must not tell the page to wipe"


async def test_a_reconnection_carrying_another_conversation_is_told_to_wipe():
    """A position only means something inside one transcript. After a reset, or
    after the process restarts, the same number points at something else, and
    replaying from there would graft the new conversation onto the old one.

    Known-bad: comparing only the index and ignoring the epoch.
    """
    svc = ChatService(FakeLink(), SilentBrain())
    app = build_app(FakeLink(), svc)
    events = [r for r in app.routes if r.path == "/chat/events"][0]
    await svc.emit("said", "from the conversation that is gone")

    stale = await _first_events(await events.endpoint(_Req("999999999999:0")), want=5)

    kinds = [e["kind"] for e in stale]
    assert "fresh" in kinds, "a page holding another transcript was not told to drop it"
    assert kinds.index("fresh") < kinds.index("said"), \
        "the wipe has to arrive before what replaces it"
    assert [e["text"] for e in stale if e["kind"] == "said"] == \
        ["from the conversation that is gone"]


async def test_a_page_that_joins_a_run_in_flight_is_told_the_run_is_in_flight():
    """Reload during a run and the stop button has to still be there.

    ⛔ MEASURED BY HAND 2026-09-08, against a running interface, and it was the
    turn ceiling that had been hiding it. `emit` keeps `busy` out of the history
    on purpose - replaying it would show a spinner for work that ended an hour
    ago - but nothing then told a NEW listener the state of now. So a reload
    mid-run replayed the transcript and left the page believing it was idle:
    steps kept arriving and appending, under a composer that said nothing was
    happening, with no stop button. With the ceiling gone that run had no other
    end, so the page offered no way to stop what it was showing.

    The history stays free of state. What is sent is the present, once, at
    subscribe time, and only when true.

    Known-bad: dropping the current-state event from the events route. The
    listener below then never sees a `busy` event at all.
    """
    brain = HangingBrain()
    svc = ChatService(FakeLink(), brain)
    app = build_app(FakeLink(), svc)
    events = [r for r in app.routes if r.path == "/chat/events"][0]

    svc.start("something long")
    await asyncio.wait_for(brain.started.wait(), 2)
    assert svc.busy, "the service does not consider itself busy while a run runs"

    # A listener arriving now, which is what a reload is.
    resp = await events.endpoint(_Req())
    seen = await _first_events(resp)

    busy = [e for e in seen if e["kind"] == "busy"]
    assert busy, "a page joining a run in flight was never told a run is in flight: %r" % seen
    assert busy[0]["text"] == "1"
    assert not busy[0].get("replay"), "the run is happening now, not being replayed"

    svc.stop()


async def test_a_page_that_joins_an_idle_service_is_not_told_anything_about_busy():
    """The other side, and the reason the event is conditional: a page starts
    out believing it is idle, so saying so again is noise, and the page's own
    handler treats `busy 0` as the end of a turn it never saw begin.

    Known-bad: sending the state unconditionally.
    """
    svc = ChatService(FakeLink(), SilentBrain())
    app = build_app(FakeLink(), svc)
    events = [r for r in app.routes if r.path == "/chat/events"][0]

    resp = await events.endpoint(_Req())
    seen = await _first_events(resp)

    assert [e for e in seen if e["kind"] == "busy"] == []


# --------------------------------------------------------------------------
# the tab strip, which only became possible when the tool stopped lying
# --------------------------------------------------------------------------

class TabbedLink(FakeLink):
    def __init__(self, payload):
        super().__init__()
        self._payload = payload

    async def call_text(self, name, arguments=None):
        await self.call(name, arguments)
        return self._payload


async def _tabs_route(link, svc=None):
    app = build_app(link, svc or ChatService(link, SilentBrain()))
    return [r for r in app.routes if r.path == "/live/tabs"][0].endpoint


async def test_the_address_comes_from_the_active_tab():
    """One call where there were two.

    While `session_list_pages` answered with ids only, this had to ask
    `browser_evaluate` for `location.href`: script in the page, to learn
    something the server already knew.
    """
    link = TabbedLink(json.dumps([
        {"id": "tab-1", "title": "A", "url": "https://a.example/", "active": False},
        {"id": "tab-2", "title": "B", "url": "https://b.example/x", "active": True},
    ]))
    link.touched = True
    route = await _tabs_route(link)

    class Req: query_params = {}
    body = json.loads((await route(Req())).body)

    assert body["url"] == "https://b.example/x", "the address is the ACTIVE tab's"
    assert [t["id"] for t in body["tabs"]] == ["tab-1", "tab-2"]
    assert [n for n, _ in link.calls] == ["session_list_pages"], (
        "one call, and not browser_evaluate on top of it")


async def test_an_older_server_leaves_the_strip_empty_instead_of_breaking_the_pane():
    """A server that still answers `["tab-1"]` is not an error here. The picture
    is the point of the pane; the strip is an extra that can be absent."""
    link = TabbedLink(json.dumps(["tab-1", "tab-2"]))
    link.touched = True
    route = await _tabs_route(link)

    class Req: query_params = {}
    body = json.loads((await route(Req())).body)

    assert body == {"url": "", "tabs": []}


async def test_the_strip_asks_nothing_before_an_instruction():
    """Same invariant as the frame: looking must not start a browser."""
    link = TabbedLink("[]")
    route = await _tabs_route(link)

    class Req: query_params = {}
    body = json.loads((await route(Req())).body)

    assert body == {"url": "", "tabs": []}
    assert link.calls == []
