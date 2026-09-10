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
import re
import shutil
import subprocess

import pytest

from aihawk.link import text_of
from aihawk.web import PAGE, ChatService, Sessions, build_app

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
        # Through `text_of`, like the real link, so a double that answers a
        # tool answers it on BOTH doors. Overriding only `call` used to leave
        # `call_text` returning the empty string for the same tool, which is a
        # double that disagrees with itself.
        return text_of(await self.call(name, arguments))


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
    """`busy` must NOT be replayed to somebody who opens the page an hour later:
    a spinner for work that finished. Everything else is the conversation and is
    kept.

    It said `busy` and `usage`, and the second one is gone with the meter that
    drew it: the numbers are still counted and still saved with the transcript,
    they are simply not an event any more.
    """
    svc = ChatService(FakeLink(), TalkingBrain())
    await svc.send("go")

    kinds = [e["kind"] for e in svc.history]
    assert "busy" not in kinds
    assert kinds == ["you", "said", "tool", "result"]


async def test_the_replay_flag_is_on_history_and_not_on_live_events():
    """The page animates a row on arrival and starts a stopwatch on it. Without
    the flag, reloading during a forty-step run animates forty rows at once and
    prints 0ms on every one."""
    svc = ChatService(FakeLink(), TalkingBrain())
    await svc.send("go")

    app = build_app(FakeLink(), Sessions.around(svc))
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
    app = build_app(FakeLink(), Sessions.around(svc))
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
    # ⛔ THREE, AND FILTERED BY KIND. This used to read exactly two events and
    # compare the whole list, so it went red the day the stream gained a state
    # event it says nothing about - and had it kept reading two while gaining
    # one, a DUPLICATE would have arrived third and gone unseen, which is the
    # only thing this test exists to catch. It is about how many times `said` is
    # delivered, so it counts those and ignores the rest.
    delivered = []
    for _ in range(3):
        try:
            delivered.append(payload(await asyncio.wait_for(anext(body), 0.1)))
        except asyncio.TimeoutError:
            break

    assert [e for e in delivered if e["kind"] == "said"] == [
        {"kind": "said", "text": "only once"}], delivered


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
    """The page fetches these paths by name. A rename here is a silent 404
    there, and the page has no way to report it.

    ⛔ AND IT IS CHECKED BOTH WAYS, because one direction alone is half a gate.
    A route the page never calls is dead surface nobody notices; a path the page
    calls and the app does not serve is a button that does nothing. The set is
    written out rather than derived from the page, so ADDING a route is a
    deliberate edit here - which is what makes this the inventory of the surface
    rather than a restatement of it.
    """
    svc = ChatService(FakeLink(), SilentBrain())
    paths = {r.path for r in build_app(FakeLink(), Sessions.around(svc)).routes}
    assert paths == {"/",
                     # The session column, added in 0.17.0.
                     "/sessions", "/sessions/new", "/sessions/rename",
                     "/sessions/forget",
                     "/chat/send", "/chat/stop", "/chat/fresh", "/chat/events",
                     "/live/frame", "/live/tabs", "/live/select",
                     # The workspace, added in 0.18.0: which browsers to draw a
                     # pane for, and which one the commands go to.
                     # ⛔ AND FOUR THAT WENT AWAY IN 0.21.0: /live/open,
                     # /live/close, /live/watch and /live/wake. Browsers are
                     # opened, closed, focused and woken by ASKING - the agent
                     # already does all four when told to - and a control beside
                     # the chat is a second way to move the same thing, which is
                     # two things that can disagree about which browser is
                     # current.
                     "/live/browsers"}

    called = {m for m in re.findall(r"""fetch\(\s*[`'"]([^`'"?]+)""", PAGE)}
    unserved = sorted(called - paths)
    assert not unserved, "the page calls paths the app does not serve: %s" % unserved


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


async def test_the_live_view_never_causes_a_browser_to_start():
    """⛔ A VIEW DRAWS WHAT EXISTS AND MAY NOT BRING IT INTO EXISTENCE. Asking
    for a picture of a browser that is not running would START one, 800 MB and
    seven seconds nobody asked for, to draw a pane for a conversation that has
    done nothing.

    The assertion is on WHICH tools were called and not on how many, and that
    is the whole lesson of [B201]. This used to say `link.calls == []`, which
    was the same thing only while the view asked nothing at all; the moment it
    asked the one free question, `== []` would have had to be relaxed, and the
    relaxation people reach for is a count. `browser_list` is free by
    construction and `browser_watch` is not free at all, so naming them is the
    assertion that keeps meaning what it means.

    Known-bad: a guard that reads whether any call has been made on the link.
    That is armed by `browser_list` itself, so the next view through it starts
    an engine - measured on 0.38.0, 9 processes to 16.
    """
    link = FakeLink()
    svc = ChatService(link, SilentBrain())
    app = build_app(link, Sessions.around(svc))
    frame = [r for r in app.routes if r.path == "/live/frame"][0]

    class Req:
        query_params = {}
        headers: dict = {}

    resp = await frame.endpoint(Req())
    assert resp.status_code == 204
    assert [n for n, _ in link.calls] == ["browser_watch"], (
        "the pane asks for the picture and nothing else: %s"
        % [n for n, _ in link.calls])


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


#: What `browser_list` answers when there is something to look at. A double
#: that can hand back a picture is a double with a browser running, so it has
#: to say so: the views ask this first and draw nothing when the answer is no.
RUNNING = ('{"session": "default", "focus": "main", "limit": 8, '
           '"browsers": [{"id": "main", "running": true, "focused": true, '
           '"urls": []}]}')


class WatchingLink(FakeLink):
    """Answers both picture tools the way the server does - `browser_watch`
    with a JPEG, `browser_take_screenshot` with a PNG - so which one the view
    asked for is visible in what came back and not only in the call log."""

    async def call(self, name, arguments=None):
        await super().call(name, arguments)
        if name == "browser_list":
            return Result(Item(type="text", text=RUNNING))
        if name == "browser_watch":
            return Result(Item(type="image", data=base64.b64encode(JPEG).decode(),
                               mimeType="image/jpeg"))
        if name == "browser_take_screenshot":
            return Result(Item(type="image", data=base64.b64encode(PNG).decode(),
                               mimeType="image/png"))
        return Result()


async def _frame_route(link):
    app = build_app(link, Sessions.around(ChatService(link, SilentBrain())))
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
        """The browser IS running - that is the point: the refusal has to be
        about the screencast and not about there being nothing to look at."""

        async def call(self, name, arguments=None):
            await FakeLink.call(self, name, arguments)
            if name == "browser_list":
                return Result(Item(type="text", text=RUNNING))
            return Result(Item(type="text", text=(
                "the live window view needs invisible-playwright with "
                "page.screencast and an engine from firefox-28 on")), isError=True)

    link = RefusingLink()
    route = await _frame_route(link)

    class Req: query_params = {}
    resp = await route(Req())

    assert resp.status_code == 503
    assert "page.screencast" in json.loads(resp.body)["error"]


async def test_nothing_to_look_at_is_the_idle_pane_and_not_an_error():
    """⛔ THE TWO REFUSALS ARRIVE THE SAME WAY AND MEAN OPPOSITE THINGS. A tool
    that refuses reaches a client as an error result carrying a sentence, and
    the route above turns that into a 503 the page shows in words. That is
    right for a capture that is broken and wrong for a browser that simply is
    not running, which is not a failure at all: it is the ordinary state of a
    conversation nobody has asked anything, and the pane should sit idle.

    Since 0.39.0 `browser_watch` refuses rather than starting a browser to
    photograph, so this refusal became the COMMON case - every poll of a fresh
    session - and without this the pane would show an error banner from the
    moment it opened.

    Told apart by comparing against the sentence itself, which both sides
    import from one place. Known-bad: `if reason:` on its own, which was what
    the route said before the refusal existed, and any edit to the shared
    sentence that leaves the two copies to drift.
    """
    from aihawk.mcp import NOTHING_RUNNING

    class AsleepLink(WatchingLink):
        async def call(self, name, arguments=None):
            await FakeLink.call(self, name, arguments)
            return Result(Item(type="text", text=NOTHING_RUNNING), isError=True)

    link = AsleepLink()
    route = await _frame_route(link)

    class Req: query_params = {}
    resp = await route(Req())

    assert resp.status_code == 204, (
        "a browser that is not running was reported as a failure, so the pane "
        "shows an error banner instead of sitting idle: %s"
        % getattr(resp, "body", b"")[:120])


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


async def test_the_stage_asks_for_frames_at_a_rate_it_has_measured():
    """Asking slower than the source means frames are made and thrown away, and
    asking faster than the pipe can carry means every click queues behind a
    picture. Both edges, and both numbers measured rather than chosen.

    ⛔ THE PACE IS NO LONGER ONE LITERAL, because the stage is no longer one
    screen. It is a rate per screen, decided by how many screens are drawn, and
    the loop's pause is derived from it. The old gate read `setTimeout(tick,
    18)` and asserted on 18; then it read a table of three entries. Both of
    those are gone: what the page declares now is a function, so this gate runs
    it - which is also the only way to ask what it answers for three screens, a
    case a table of 1, 2 and 4 could not express and a four-up layout produces
    the moment three browsers are running.

    ⛔ AND THE COST OF A FRAME WAS WRONG BY A FACTOR OF FOUR. This file said 22
    ms of pipe, and everything about the old design followed from it: one live
    pane, seven previews at one every 400 ms, and a comment explaining that
    eight panes would need 2.3 seconds of pipe per second. Measured again on
    2026-09-09 with four real browsers over the same Link the interface uses, a
    frame costs 5 to 6 ms - the capture already runs inside the engine, and the
    server hands over the latest picture rather than taking one. Four panes
    polled as fast as the answers came back delivered 80 frames a second in
    total, about 20 each, and an action still landed in 49 ms against 40 with a
    single pane.

    Known-bad, three: ask for fewer frames at one-up than the engine is told to
    produce, which throws away what was made; raise the table until the total
    passes what the pipe was measured to carry; or schedule the pump from a
    second place, which is how a pace stops being a thing anybody can read.
    """
    import re

    # ⛔ THE CODE, NOT THE PROSE BESIDE IT, and this gate learned that the hard
    # way: a comment explaining why the pause is NOT 500 contained the literal
    # `setTimeout(tick, 500)`, and the scan read the explanation as the pump.
    code = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    code = re.sub(r"^\s*//.*$", "", code, flags=re.M)

    assert len(re.findall(r"setTimeout\(tick,", code)) == 1, (
        "the pump is scheduled from more than one place, so its pace is no "
        "longer one number anybody can read")
    # ⛔ AND THE RATE IS PACED ON THE STAGE, NOT ON THE BUTTON. A layout is a
    # ceiling on how many screens you watch at once; how many there ARE is a
    # different number, and pacing two browsers as though they were four gave
    # them half the frames the measurement says they can have.
    assert "fps(onScreen()) * onScreen()" in code, (
        "the pause is no longer derived from the screens actually on the stage")

    decl = re.search(r"const LAYOUTS = \[[^\]]*\];\s*"
                     r"const TOPRATE = \d+, CEILING = \d+;\s*"
                     r"const fps = \(n\) => .+", code)
    assert decl, "the stage no longer declares the pace it keeps"

    node = shutil.which("node")
    if not node:  # pragma: no cover - every runner here has one
        pytest.skip("needs node to EXECUTE the pace")

    # ⛔ EXECUTED, NOT READ. The pace used to be a literal table a regex could
    # check entry by entry. It is a function now, so the only honest way to ask
    # what it answers for three screens is to run it - and three screens is a
    # real case the table never had, because a four-up layout with three
    # browsers running draws exactly three.
    js = decl.group(0) + chr(10) + (
        "process.stdout.write(JSON.stringify("
        "[LAYOUTS, CEILING, [1,2,3,4].map(n => fps(n))]));")
    done = subprocess.run([node, "-e", js], capture_output=True, text=True,
                          encoding="utf-8", timeout=30)
    assert done.returncode == 0, "the pace threw: %s" % done.stderr
    layouts, ceiling, each = json.loads(done.stdout)

    assert layouts == [1, 2, 4], "the layouts on offer are %s" % layouts

    from aihawk.mcp.session import StealthSession

    assert each[0] >= StealthSession.WATCH_FPS, (
        "one screen is asked for %d frames a second while the engine is told to "
        "produce %d: the difference is made, held and thrown away, which is the "
        "defect this gate was written for"
        % (each[0], StealthSession.WATCH_FPS))

    #: Measured 2026-09-09, four browsers, this pipe. 80 frames a second cost
    #: about half of it, so a quarter of the pipe is the budget spent.
    A_FRAME_MS, A_QUARTER_MS = 6, 250
    assert ceiling * A_FRAME_MS <= A_QUARTER_MS, (
        "the stage may ask for %d frames a second, which at about %d ms apiece "
        "is %d ms of every second - the agent's clicks go down the same pipe"
        % (ceiling, A_FRAME_MS, ceiling * A_FRAME_MS))
    for screens, rate in enumerate(each, start=1):
        assert rate >= 1, "%d screens are paced at %d frames a second" % (screens, rate)
        assert screens * rate <= ceiling, (
            "%d screens at %d frames a second each is %d requests a second, over "
            "the %d the pipe was measured to have room for"
            % (screens, rate, screens * rate, ceiling))

async def test_the_answer_is_built_from_nodes_and_never_from_html():
    """The model's Markdown is drawn, and it is drawn without `innerHTML`.

    The answer `The main heading says **"Example Domain"**` used to reach the
    screen with its asterisks, because everything in this page is built with
    `textContent`. That invariant is not the oversight - it is why the pane is
    safe: the text was written by a model that had just read arbitrary web
    pages, so its content is chosen by whoever wrote the last page it visited.

    ⛔ THE INVARIANT IS THE TEST. `innerHTML` must not appear in the page at
    all, and the renderer must build elements instead. Known-bad, and the whole
    reason this test exists: someone reaching for a Markdown library that
    returns an HTML string and assigning it, which is the documented road to
    exfiltration through an injected image.
    """
    # The ASSIGNMENT and not the word: both this file and the page discuss
    # `innerHTML` in prose precisely because neither may use it, and a check
    # tripped by the sentence explaining the rule is the defect this project
    # writes down most often.
    import re

    assert not re.search(r"innerHTML\s*=", PAGE), \
        "something assigns HTML now, and the text it assigns comes from the web"
    assert "insertAdjacentHTML" not in PAGE and "document.write" not in PAGE, \
        "another way into the parser was opened"
    assert "function rich(" in PAGE and "createTextNode" in PAGE, \
        "the answer is no longer built from nodes"
    # The two marks the model actually emits, and the fence.
    assert "el('strong'" in PAGE and "el('code'" in PAGE and "el('em'" in PAGE
    # Never built from model text: one is the exfiltration vector, the other has
    # no reason to be clickable next to a browser this page is already driving.
    assert "el('img'" not in PAGE and "el('a'" not in PAGE


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
    app = build_app(FakeLink(), Sessions.around(svc))
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
    app = build_app(FakeLink(), Sessions.around(svc))
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
    app = build_app(FakeLink(), Sessions.around(svc))
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


async def test_a_page_that_joins_an_idle_service_is_told_the_turn_is_over():
    """⛔ THIS TEST ASSERTED THE OPPOSITE UNTIL 2026-09-08, AND THE OPPOSITE COST
    THE LAST ANSWER OF EVERY CONVERSATION SOMEBODY REOPENED.

    It read: a page starts out believing it is idle, so saying so again is
    noise, and the page's own handler treats `busy 0` as the end of a turn it
    never saw begin. Both halves are true and the conclusion was still wrong,
    because after a REPLAY the turn being ended is one that really did end. The
    page holds one narration line back so that a sentence followed by tool calls
    reads as their lead-in and a sentence with nothing after it reads as the
    answer, and the only event that resolves that lookahead is the end of the
    turn. `emit` keeps `busy` out of the history on purpose, so a reopened
    conversation replayed everything and then sat holding its last sentence,
    forever, with nothing else coming.

    Measured on the developer's own saved session: 257 events ending in `said`,
    and the answer to the last thing they asked was not on the screen. Nothing
    was red. The suite tests the routes and reads the page as a string, and the
    page is correct here - it is the stream that never said the turn was over.

    Known-bad: make the event conditional on `joining_a_run` again. The last
    event below stops being a `busy`, and a person reopening a conversation
    loses its answer.
    """
    svc = ChatService(FakeLink(), SilentBrain())
    svc.history = [{"kind": "you", "text": "what is on the page"},
                   {"kind": "said", "text": "Three roles, all remote."}]
    app = build_app(FakeLink(), Sessions.around(svc))
    events = [r for r in app.routes if r.path == "/chat/events"][0]

    resp = await events.endpoint(_Req())
    seen = await _first_events(resp)

    busy = [e for e in seen if e["kind"] == "busy"]
    assert busy, (
        "a page reopening a finished conversation was never told the turn "
        "ended, so the last thing the model said stays held and is never "
        "drawn: %r" % seen)
    assert busy[0]["text"] == "0"
    assert busy[0].get("replay"), (
        "the end of a turn that finished before this listener existed must be "
        "flagged as replay, or the page animates a row and redraws the session "
        "list for a turn nobody watched")
    said = [i for i, e in enumerate(seen) if e["kind"] == "said"]
    assert said and seen.index(busy[0]) > said[-1], (
        "the turn was declared over before the sentence it ends was replayed")


# --------------------------------------------------------------------------
# the tab strip, which only became possible when the tool stopped lying
# --------------------------------------------------------------------------

class TabbedLink(FakeLink):
    """`session_list_pages` answers `payload`; `browser_list` answers that the
    browser is running, because a session with tabs to list has one."""

    def __init__(self, payload, running=True):
        super().__init__()
        self._payload = payload
        self._running = running

    async def call_text(self, name, arguments=None):
        await self.call(name, arguments)
        if name == "browser_list":
            return RUNNING if self._running else '{"focus": "", "browsers": []}'
        return self._payload


async def _tabs_route(link, svc=None):
    app = build_app(link, Sessions.around(svc or ChatService(link, SilentBrain())))
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
    route = await _tabs_route(link)

    class Req: query_params = {}
    body = json.loads((await route(Req())).body)

    assert body["url"] == "https://b.example/x", "the address is the ACTIVE tab's"
    assert [t["id"] for t in body["tabs"]] == ["tab-1", "tab-2"]
    assert [n for n, _ in link.calls] == ["session_list_pages"], (
        "the tabs in ONE call, and not browser_evaluate on top of it")


async def test_an_older_server_leaves_the_strip_empty_instead_of_breaking_the_pane():
    """A server that still answers `["tab-1"]` is not an error here. The picture
    is the point of the pane; the strip is an extra that can be absent."""
    link = TabbedLink(json.dumps(["tab-1", "tab-2"]))
    link.touched = True
    route = await _tabs_route(link)

    class Req: query_params = {}
    body = json.loads((await route(Req())).body)

    assert body == {"url": "", "tabs": []}


async def test_the_strip_never_causes_a_browser_to_start():
    """Same invariant as the frame, and it has to be stated the same way.

    `session_list_pages` resolves the browser through `ready`, which STARTS it,
    so an empty strip drawn by asking is an empty strip that cost an engine.
    Measured on 0.38.0: 9 processes before, 16 after, and the answer was
    `{"url": "", "tabs": []}` either way.

    Known-bad: a guard that reads whether any call has been made on the link.
    """
    link = TabbedLink("[]", running=False)
    route = await _tabs_route(link)

    class Req: query_params = {}
    body = json.loads((await route(Req())).body)

    assert body == {"url": "", "tabs": []}
    assert [n for n, _ in link.calls] == ["session_list_pages"], (
        "the strip asks once and reads the answer: %s"
        % [n for n, _ in link.calls])
