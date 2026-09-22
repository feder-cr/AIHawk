"""One conversation: what was said, who is listening, and what it cost."""
from __future__ import annotations

import asyncio
import time
from typing import Dict, List, Optional

from .agent import Brain, said_only
from .link import Link
from .quiet import swallow
from . import chats
from . import orcarouter
from .storage import DEFAULT_SESSION_ID


#: The conversation a page that names none is in.
#:
#: ⛔ THE SAME OBJECT the server persists under, not a second string that
#: matches it. The point is not a coincidence: every client written before this
#: existed keeps landing on one conversation driving one browser. That was
#: declared twice - `"default"` here and `DEFAULT_SESSION_ID` in the mcp
#: package - with a comment saying the two had to agree and a test asserting
#: this one equalled the LITERAL `"default"`. Moving the server's default would
#: therefore have left the interface writing `chats/default.json` while the
#: server wrote `sessions/lavoro.json`, with the test that names the invariant
#: still green. One declaration cannot disagree with itself.
DEFAULT_CHAT_ID = DEFAULT_SESSION_ID

#: What a conversation is called before it has been asked anything.
UNNAMED = "New chat"

#: Kinds that are STATE rather than conversation: told to whoever is listening
#: NOW, and never written into the transcript.
#:
#: `busy` has been here from the start - replaying it to somebody who opens the
#: page later would show a spinner for work that finished an hour ago.
#:
#: ⛔ `fresh` JOINED IT IN 0.57.0, AND IT COULD EAT A TYPED SENTENCE. It is the
#: word that tells every page to wipe, and `reset` emits it immediately after
#: clearing the history - so it landed in the now-empty transcript and became
#: the ONE thing a cleared conversation had written down. Found by reading a
#: real saved file, not by a test: the developer's own `default.json` held
#: exactly one event, and it was this.
#:
#: What that costs is small and is the one thing this interface must not do. A
#: replayed `fresh` runs `wipe()` in the page, and `wipe()` calls
#: `setQueued(null)`: so a person who had typed a follow-up while the agent
#: worked, on a conversation that had been cleared at any point in its past,
#: lost that sentence the moment the stream reconnected from before the stored
#: `fresh` - which is exactly what a server restart does. Nothing said so.
#:
#: The live path is untouched: `/chat/fresh` still emits it and every listener
#: still wipes, which is what makes two tabs agree. A page that arrives LATER
#: needs no command, because what it is handed is already the empty transcript
#: the command would have produced.
NOT_SAID = ("busy", "fresh")


class ChatService:
    """One conversation, its listeners, and the link it drives."""

    def __init__(self, link: Link, brain: Brain,
                 model_label: str = "no model", *,
                 session_id: str = DEFAULT_CHAT_ID,
                 name: str | None = None) -> None:
        self._link = link
        self._brain = brain
        self._listeners: List[asyncio.Queue] = []
        self.history: List[Dict[str, str]] = []
        self.session_id = session_id
        self.name = name or UNNAMED
        self.model_label = model_label
        self._busy = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None
        #: The OrcaRouter key this conversation sends, when it is running on
        #: OrcaRouter at all. None under the default provider, where the key
        #: belongs to the process rather than to the conversation.
        self._credential = None
        #: Where a refused key is recorded, when this conversation is the one
        #: that found out. Set by the registry beside the credential.
        self._credentials = None
        #: Which conversation the history belongs to. A reconnecting page says
        #: how far it got with `Last-Event-ID`, and that position only means
        #: something inside one conversation: after a reset, or after the
        #: process restarts, the same number points at a different transcript.
        #: Counted from the clock so a restart cannot collide with the run
        #: before it.
        self._epoch = str(int(time.time() * 1000))

    @property
    def link(self):
        """The connection this conversation drives.

        Exposed because the LIVE routes need it: the picture and the address
        belong to THIS conversation's browsers, and there is no other
        connection to reach for - each conversation has its own server process
        since the tool surface stopped taking a session argument. Reaching for
        somebody else's would draw a browser the person is not looking at,
        which is a wrong answer that looks exactly like a right one.
        """
        return self._link

    def set_brain(self, brain: Brain, model_label: str) -> None:
        """Change the model behind this conversation, mid-flight.

        ⛔ THE MODEL IS A PROPERTY OF THE CONVERSATION, NOT OF THE PROCESS, and
        that is the whole reason this exists. `Sessions` builds every brain from
        one factory chosen at startup, which was right while there was one
        provider: the process held one key, so every conversation had to speak
        with it. A provider the user selects from a panel can be changed while
        the page is open, and if the brain were fixed at spawn the panel would
        be a control that draws a new name and sends the old provider's
        requests.

        ⛔ AND IT IS REPLACED RATHER THAN MUTATED. A `Conversation` holds the
        client it was built with and the model id it was built for, both of them
        in its own attributes; writing over them from here would be a second
        place that knows how a conversation is put together. A new brain starts
        from the system message and an empty transcript, which is the honest
        thing to do: the previous provider's messages are not this one's to
        continue.

        Refused while a run is in flight, for the same reason `reset` is: the
        running turn holds the old brain and swapping it mid-answer would drop
        the answer of a turn somebody is watching.
        """
        if self._busy.locked():
            return False
        self._brain = brain
        self.model_label = model_label
        return True

    def use_credential(self, credential, store=None) -> None:
        """Say which OrcaRouter key this conversation sends, and where a
        refusal of it is recorded.

        ⛔ SET BY THE REGISTRY, WHICH IS THE THING THAT KNOWS. A conversation
        does not choose a credential and cannot obtain one: the registry builds
        it once from the flag, the environment or the store, and hands the same
        one to every conversation. What the conversation needs it for is the
        one moment a request is REFUSED - the sentence a person needs then is
        about the key rather than the task, and the exact generation that was
        rejected has to be the one flagged so a sign-in that happened in
        between cannot be blamed for it.

        The store is passed with it rather than reached for, so this module
        does not need to know where a key lives - which is the whole point of
        having one place that does.
        """
        self._credential = credential
        self._credentials = store

    async def _refused(self, exc) -> bool:
        """Whether the provider refused the key, and if so, say so properly.

        ⛔ ONLY A 401, AND ONLY THE KEY THAT WAS ACTUALLY SENT. A rate limit, a
        5xx and a dropped connection are all failures this must not report as a
        dead key. And the flag is set on the GENERATION that was sent, so a
        sign-in that happened while this request was in the air - which has
        already moved the generation on - is never the credential a late answer
        to an old request disables.
        """
        if self._credential is None or not orcarouter.is_auth_failure(exc):
            return False
        store = self._credentials or orcarouter.Credentials()
        if store.mark_needs_reauth(self._credential.generation):
            await self.emit("auth", "reauth")
        await self.emit("err", "OrcaRouter refused the key this conversation was "
                        "using, so it has stopped until a new one is supplied. "
                        "Sign in again from the OrcaRouter panel, or paste a key.")
        return True

    def save(self) -> None:
        """Write this conversation down as it stands.

        Called when the conversation CHANGES - a turn ended, it was renamed, it
        was reset - and not on a timer, for the reason the browsers are saved
        the same way: a file written on a tick is a version of the session that
        existed only between two ticks.

        ⛔ BOTH TRANSCRIPTS, and saving only one would be a promise the other
        half cannot keep. The page draws `history`; the model holds `messages`.
        Reopening with only the first gives somebody a conversation they can
        read and cannot continue, under a follow-up box that still says "and now
        sort them by price" will work.

        The turn is already finished and answered, and losing it to a full disk
        would be a strange way to report a full disk.

        ⛔ WHAT GOES DOWN IS WHAT WAS SAID, AND THE SYSTEM MESSAGE IS NOT. It is
        what this build asks the model to be, rebuilt on every run from the
        prompt plus the server's own instructions, and `remember` has dropped
        the saved one on the way back in since 2026-09-08 - so writing it was
        writing something nothing would ever read. `said_only` is where that
        rule lives, for this side and that one.
        """
        with swallow("a write that fails costs the saved conversation and nothing else"):
            chats.save_chat(self.session_id, self.name, self.history,
                            said_only(getattr(self._brain, "messages", None)),
                            self.usage)

    def restore(self) -> bool:
        """Read this conversation back, if one was saved. Answers whether it was.

        The epoch is NOT restored, and that is deliberate: it says which
        transcript a page's positions belong to, and a page reconnecting from
        before the restart holds positions into a transcript this process never
        had. A new epoch makes it replay from the beginning instead of resuming
        into the middle of something else.
        """
        saved = chats.load_chat(self.session_id)
        if not saved:
            return False
        self.history = list(saved.get("history") or [])
        self.name = saved.get("name") or self.name
        messages = saved.get("messages") or []
        remember = getattr(self._brain, "remember", None)
        if callable(remember) and messages:
            remember(messages, saved.get("usage") or {})
        return True

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._listeners.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._listeners:
            self._listeners.remove(q)

    async def emit(self, kind: str, text: str) -> None:
        event = {"kind": kind, "text": text}
        if kind not in NOT_SAID:
            self.history.append(event)
        for q in list(self._listeners):
            q.put_nowait(event)

    def reset(self) -> bool:
        """Start a fresh conversation, keeping the browser where it is.

        ⛔ THIS IS A COST AND LATENCY CONTROL, not a tidiness feature, and
        until it existed there was no way to reach it short of killing the
        process. Every turn resends the whole transcript, so the transcript is
        the bill and it is also the wait: measured on this interface, a first
        instruction on a fresh process carries 3,106 prompt tokens and the
        agent moves 4.1 s after the click; by the third instruction of the same
        session the first turn already carries 38,207 and the wait is 6.7 s.
        Nothing trimmed it, so it only grew.

        The browser is deliberately left alone. Someone who has logged in
        somewhere and wants to drop the transcript should not lose the session
        they built, and the two have no reason to be tied.

        Refused while a run is in flight rather than cancelling it: throwing
        away a transcript that something is still writing into is the kind of
        surprise a person cannot undo.
        """
        if self.busy:
            return False
        forget = getattr(self._brain, "forget", None)
        if callable(forget):
            forget()
        self.history.clear()
        self._epoch = str(int(time.time() * 1000))
        return True

    @property
    def epoch(self) -> str:
        """Which transcript the history positions belong to."""
        return self._epoch

    @property
    def usage(self) -> dict:
        """What this conversation has cost, for the file it is saved into.

        Read through the brain rather than kept here: the brain owns the
        transcript, so it owns what the transcript has cost. It is no longer
        sent anywhere - the meter that drew it is gone - but it is still counted
        and still saved, so putting a number back on the screen is a question of
        where to draw it and not of measuring it again.
        """
        got = getattr(self._brain, "usage", None)
        return dict(got) if isinstance(got, dict) else {}

    @property
    def busy(self) -> bool:
        """Whether an instruction is in flight, for a listener joining now.

        The lock and not the task handle: the lock is held for exactly as long
        as `send` runs, which is the span the page draws as busy, while the
        handle survives its own task and would answer for a run that ended.
        """
        return self._busy.locked()

    def start(self, text: str) -> None:
        """Run an instruction detached, keeping the handle so it can be stopped.

        The task is held for exactly that reason. Firing and forgetting is one
        line shorter and makes the stop button a decoration.
        """
        self._task = asyncio.create_task(self.send(text))

    def stop(self) -> bool:
        t = self._task
        if t is not None and not t.done():
            t.cancel()
            return True
        return False

    async def send(self, text: str) -> None:
        async with self._busy:
            # Emitted here and not added by the page, so the instruction is part
            # of the transcript: somebody opening the page mid-run sees what was
            # asked, and a reload does not lose it. The page adding it locally is
            # one line shorter and leaves a conversation with no questions in it.
            if self.name == UNNAMED:
                # Named from what it was first asked, because a column of eight
                # rows that all say "New chat" is a column nobody can use, and
                # asking somebody to name a conversation before having it is
                # asking them to describe work they have not done yet.
                flat = " ".join(text.split())
                self.name = flat[:48] + ("..." if len(flat) > 48 else "")
            await self.emit("you", text)
            await self.emit("busy", "1")
            try:
                await self._brain.handle(text, self._link, self.emit)
            except asyncio.CancelledError:
                # The cancellation lands at the next await, and since the model
                # request runs in a thread that is either the request itself or
                # the tool call after it - so stop is prompt rather than "after
                # the step in flight", which is what this comment used to say
                # and what the loop used to do.
                #
                # Prompt is not free: a model request already sent finishes in
                # its thread and its answer is discarded, so a run stopped
                # mid-turn is still billed for that reply. Stopping cuts what
                # comes next, never what is already in the air.
                # ⛔ NOT AN ERROR. THE PERSON PRESSED THE BUTTON. This emitted
                # `err` with the single word `stopped`, so a deliberate and
                # correct action was answered with a red box, announced to a
                # screen reader as "error stopped", and any step in flight was
                # flipped to the failed state. The page treated the user's own
                # instruction as a fault.
                await self.emit("note", "Stopped.")
                raise
            except Exception as exc:
                # ⛔ A REFUSED KEY IS NOT A BROKEN TASK, AND IT WAS BEING SAID
                # AS ONE. Everything below this line is the right sentence for
                # a tool that failed and the wrong one for a credential: it
                # tells the person their instruction ended early, when what
                # happened is that the provider would not take the key - and
                # the one action that fixes it, signing in again, is not
                # mentioned anywhere on the page.
                if await self._refused(exc):
                    raise
                # ⛔ AND THIS PRINTED A PYTHON CLASS NAME AND THE PROVIDER'S
                # RAW JSON INTO THE CONVERSATION. It is the one line in the
                # product a person reads at the exact moment something has gone
                # wrong, and it said nothing about what to do next or about the
                # instruction they had just lost sight of. The detail stays -
                # it is the only clue when the cause is real - behind a sentence
                # that says what happened and what is still true.
                detail = " ".join(str(exc).split())
                await self.emit("err", "The turn ended early. What you asked is "
                                "still in the transcript, so you can send it "
                                "again once this is dealt with. (%s%s)"
                                % (type(exc).__name__,
                                   ": " + detail[:200] if detail else ""))
            finally:
                await self.emit("busy", "0")
                # After the turn and not during it: a transcript written
                # mid-run is a version of the conversation that existed for a
                # moment, and this is the moment it is worth keeping. Stopped
                # and failed runs are saved too - what was asked and how far it
                # got is exactly what somebody reopens the session to see.
                self.save()
