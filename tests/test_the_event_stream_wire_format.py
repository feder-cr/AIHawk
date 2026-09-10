"""The exact bytes on the wire, which nothing else in this suite looks at.

⛔ EVERY OTHER TEST OF THE STREAM SPLITS ON `data: ` AND DECODES THE JSON, so it
sees the CONTENT and never the FRAMING: not the `id:` line that lets a dropped
connection resume where it was, not the blank line that ends an event, not the
order of the two, not which events are numbered and which are deliberately not.
A page that reconnects reads the framing and nothing else, so until this file
existed a change to it would have shipped green.

⛔ AND IT DRIVES THE APPLICATION DIRECTLY INSTEAD OF THROUGH A CLIENT. A test
client reassembles the response and hands back a decoded body, which is the
projection this file exists to stop looking at; it also runs the application in
another thread's event loop, where the conversation built here does not live.
`send` is called with the literal messages the framework emits, so what is
asserted below is what goes out.

Written as a characterisation test BEFORE the framing was moved into one
function, so that the move could be shown to change nothing rather than argued
to.
"""
from __future__ import annotations

import asyncio
import contextlib
import json

import pytest

from aihawk.chat import ChatService
from aihawk.routes import build_app
from aihawk.sessions import Sessions

from test_web_service import FakeLink, HangingBrain, TalkingBrain

pytestmark = pytest.mark.asyncio


class Wire:
    """What the application sent, kept as the bytes it sent them in."""

    def __init__(self) -> None:
        self.status: int | None = None
        self.headers: dict[str, str] = {}
        self.chunks: list[bytes] = []
        self._bell = asyncio.Event()

    @property
    def raw(self) -> bytes:
        return b"".join(self.chunks)

    def events(self) -> list[bytes]:
        """The stream cut into its events, framing and all."""
        return [block for block in self.raw.split(b"\n\n") if block.strip()]

    async def send(self, message) -> None:
        if message["type"] == "http.response.start":
            self.status = message["status"]
            self.headers = {k.decode().lower(): v.decode()
                            for k, v in message["headers"]}
        elif message["type"] == "http.response.body":
            self.chunks.append(message.get("body", b""))
        self._bell.set()

    async def until(self, needle: bytes, timeout: float = 2.0) -> None:
        async def wait() -> None:
            while needle not in self.raw:
                self._bell.clear()
                if needle in self.raw:
                    return
                await self._bell.wait()
        try:
            await asyncio.wait_for(wait(), timeout)
        except asyncio.TimeoutError:  # pragma: no cover - a failure message
            raise AssertionError(
                "%r never went out; the stream held %r" % (needle, self.raw))


@contextlib.asynccontextmanager
async def listening(svc, headers=()):
    """One subscription to `/chat/events`, open for the body of the block."""
    app = build_app(svc.link, Sessions.around(svc))
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": "/chat/events", "raw_path": b"/chat/events",
        "query_string": b"", "root_path": "",
        "headers": [(b"host", b"testserver")] + list(headers),
        "client": ("test", 1), "server": ("testserver", 80),
    }

    async def receive():
        # The connection stays open: this listener is never the one that hangs
        # up, so nothing here may answer `http.disconnect`.
        await asyncio.sleep(3600)
        return {"type": "http.disconnect"}

    wire = Wire()
    task = asyncio.create_task(app(scope, receive, wire.send))
    try:
        yield wire
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


#: What the server sends last before it settles into waiting for live events,
#: in both directions of the branch that ends the opening burst.
SETTLED = b'"kind": "busy"'


async def talking(model_label="a model"):
    svc = ChatService(FakeLink(), TalkingBrain(), model_label=model_label)
    await svc.send("go")
    return svc


async def test_the_opening_burst_is_model_then_replay_then_the_present():
    """The order is the contract: which model is answering, then everything
    that was said, then whether a run is in flight right now.
    """
    svc = await talking()
    async with listening(svc) as wire:
        await wire.until(SETTLED)

        assert wire.status == 200
        assert wire.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert wire.headers["cache-control"] == "no-store"

        events = wire.events()
        assert events[0] == b'data: {"kind": "model", "text": "a model"}', (
            "the first event is not the model, or it carries an id it has no "
            "business carrying: %r" % events[0])
        assert events[-1] == b'data: {"kind": "busy", "text": "0", "replay": true}', (
            "a finished conversation does not end with the flush that draws "
            "its last answer: %r" % events[-1])
        assert len(events) == len(svc.history) + 2, (
            "the burst is not model + the whole transcript + the present: %r"
            % [e[:40] for e in events])


async def test_every_replayed_event_is_numbered_inside_this_transcript():
    """⛔ THE NUMBER IS THE WHOLE RESUME MECHANISM. Without the `id:` line a
    dropped connection has nothing to say when it comes back, and the page -
    which has no de-duplication - appends a second copy of the transcript.
    """
    svc = await talking()
    async with listening(svc) as wire:
        await wire.until(SETTLED)

        numbered = [e for e in wire.events() if e.startswith(b"id: ")]
        assert len(numbered) == len(svc.history), (
            "%d of %d replayed events are numbered"
            % (len(numbered), len(svc.history)))
        for position, block in enumerate(numbered):
            head, newline, body = block.partition(b"\n")
            assert head == b"id: %s:%d" % (svc.epoch.encode(), position), (
                "the resume point is not this transcript at this position: %r"
                % head)
            assert newline == b"\n" and body.startswith(b"data: "), (
                "the id and the data are not one event: %r" % block)
            assert json.loads(body.removeprefix(b"data: ")) == {
                **svc.history[position], "replay": True}


async def test_a_listener_that_says_where_it_got_to_is_not_sent_it_again():
    """`EventSource` reconnects by itself after any drop, and until the header
    was read the server answered every reconnection with the whole transcript.
    """
    svc = await talking()
    marker = ("%s:0" % svc.epoch).encode()
    async with listening(svc, [(b"last-event-id", marker)]) as wire:
        await wire.until(SETTLED)

        events = wire.events()
        replayed = [e for e in events if e.startswith(b"id: ")]
        assert len(replayed) == len(svc.history) - 1, (
            "resuming from position 0 replayed %d of %d events"
            % (len(replayed), len(svc.history)))
        assert replayed[0].startswith(b"id: %s:1" % svc.epoch.encode()), (
            "the replay did not carry on from where the page said it was: %r"
            % replayed[0])
        assert not any(b'"kind": "fresh"' in e for e in events), (
            "a page resuming its own transcript was told to drop it")


async def test_a_position_from_another_transcript_starts_over_and_says_so():
    """A position only means something inside one transcript. After a reset, or
    after the process restarts, the same number points at something else, so
    the page is told to drop what it holds rather than grow a chimera.
    """
    svc = await talking()
    async with listening(svc, [(b"last-event-id", b"an-older-epoch:3")]) as wire:
        await wire.until(SETTLED)

        events = wire.events()
        assert events[1] == b'data: {"kind": "fresh", "text": "1"}', (
            "the page was not told to drop the transcript it is showing: %r"
            % events[1])
        replayed = [e for e in events if e.startswith(b"id: ")]
        assert len(replayed) == len(svc.history), "the replay did not start over"
        assert replayed[0].startswith(b"id: %s:0" % svc.epoch.encode())


async def test_a_marker_that_is_not_a_position_is_not_a_resume_either():
    """⛔ AND A MARKER WITH NO POSITION IN IT AT ALL IS THE CASE THAT LOOKS
    HARMLESS. Before the epoch existed the marker was a bare index, so a page
    held open across that upgrade reconnects carrying something this format
    cannot read. Treating it as "this transcript, from the beginning" replays
    everything without telling the page to drop what it is already showing,
    which is the doubled transcript the epoch exists to prevent - and it says
    so only in the one branch nobody writes a test for.

    Found by a mutation that survived: with no header at all the two answers
    are indistinguishable, so the gate had to reach for the malformed one.
    """
    svc = await talking()
    async with listening(svc, [(b"last-event-id", b"an-older-format")]) as wire:
        await wire.until(SETTLED)

        events = wire.events()
        assert events[1] == b'data: {"kind": "fresh", "text": "1"}', (
            "a marker this format cannot read was taken for a position in this "
            "transcript: %r" % events[1])


async def test_a_listener_joining_a_run_is_told_the_present_unflagged():
    """⛔ THE TWO ARE NOT ONE LINE WITH A CONDITIONAL INSIDE. The live one must
    arrive unflagged or the page calls `waited()` where it should call
    `waiting()`, and a run in progress loses its clock.
    """
    brain = HangingBrain()
    svc = ChatService(FakeLink(), brain, model_label="a model")
    svc.start("something slow")
    await asyncio.wait_for(brain.started.wait(), 2.0)
    try:
        async with listening(svc) as wire:
            await wire.until(SETTLED)
            assert wire.events()[-1] == b'data: {"kind": "busy", "text": "1"}', (
                "a listener joining a run in flight was told the wrong thing: "
                "%r" % wire.events()[-1])
    finally:
        svc.stop()
        await asyncio.sleep(0)


async def test_a_live_event_is_numbered_and_live_state_is_not():
    """⛔ AN ID MOVES THE RESUME POINT, AND `busy` IS NOT A PLACE TO RESUME
    FROM. Numbering it would make a reconnection resume past a real event, and
    leaving the field out is what the spec says keeps the last id standing.
    """
    svc = await talking()
    async with listening(svc) as wire:
        await wire.until(SETTLED)
        opening = len(wire.raw)

        # Where the transcript is BEFORE the event, because `fresh` below joins
        # the history too and would move this number under the assertion.
        position = len(svc.history)

        await svc.emit("said", "and then this")
        await wire.until(b"and then this")
        await svc.emit("busy", "0")
        await svc.emit("fresh", "1")
        await wire.until(b'"kind": "fresh"')

        live = [b for b in wire.raw[opening:].split(b"\n\n") if b.strip()]
        assert live[0] == (b'id: %s:%d\ndata: {"kind": "said", "text": '
                           b'"and then this"}'
                           % (svc.epoch.encode(), position)), (
            "a live event is not numbered at its place in the transcript: %r"
            % live[0])
        assert live[1] == b'data: {"kind": "busy", "text": "0"}', (
            "live state came with an id, which moves the resume point past a "
            "real event: %r" % live[1])
        assert live[2] == b'data: {"kind": "fresh", "text": "1"}', (
            "a reset came with an id: %r" % live[2])


async def test_every_event_ends_with_a_blank_line():
    """The blank line is what ends an event for `EventSource`. Without it two
    events are read as one and the page sees neither.
    """
    svc = await talking()
    async with listening(svc) as wire:
        await wire.until(SETTLED)
        raw = wire.raw

    assert raw.endswith(b"\n\n"), "the last event was never terminated"
    for block in raw.split(b"\n\n")[:-1]:
        assert block.strip(), "an empty frame went out on the wire"
        assert block.endswith(b"}"), (
            "an event does not end where its JSON ends: %r" % block[-40:])
        assert block.count(b"\n") == (1 if block.startswith(b"id: ") else 0), (
            "an event carries a line that is neither its id nor its data: %r"
            % block)
