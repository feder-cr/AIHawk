"""The loop: model, tools, browser, repeat until it answers.

ONE loop. There were briefly two, which is how a README sentence saying "same
machinery" becomes false without anybody editing it: the second copy gets a fix,
the first does not, and the two answers diverge for a task that looks identical
from outside. They were merged, so this loop now has exactly one consumer in
the product: the interface, through `OpenRouterBrain` at the end of this file.
The suite drives the same loop, through a four-line helper that lives in the
suite rather than here.

The narration is a parameter rather than a mode. The interface passes the
callback that pushes events to the page; a caller that wants an answer and no
transcript passes nothing. A loop that knows whether it is being watched is a
loop with two behaviours to test.
"""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable, List, Optional

from . import actions_help
from .link import answer_of

SYSTEM_PROMPT = (
    "You are a browser automation agent. You control a real, stealth Firefox "
    "browser ONLY through the provided tools. Inspect pages with "
    "browser_read_text / browser_snapshot / browser_read_html before acting on "
    "them. A person may be watching the browser while you work, so prefer one "
    "clear action at a time over long chains. When the task is done: first close "
    "the support browser with browser_close if you opened it and nothing more "
    "needs it, then reply with the answer, and call no more tools after that. "
    "Report only what the page "
    "actually shows. Say plainly what failed and what you could not check: the "
    "person reading is deciding what to do next. Write the way a competent "
    "colleague talks: the answer first, then what supports it. Do not announce "
    "what you are about to say, do not repeat the question back, and do not end "
    "by summarising what you just wrote - say it once. Prose by default. Use a "
    "heading, a list or a table only when the content really is one; a bold "
    "label in front of every paragraph is a template, not writing. Never use "
    "emoji: not as a status marker in front of a line, not as a bullet, not for "
    "emphasis, not one. Say in words whether something worked. Write every "
    "dash as a plain hyphen."
)
#: ⛔ THE EMOJI RULE IS FLAT, BECAUSE THE CONDITIONAL ONE WAS READ AS PERMISSION.
#: It used to say an emoji "is fine where it carries something the words do not,
#: and wrong as a status marker at the head of every line", and the answers came
#: back with a tick at the head of every line. A rule with an exception in it is
#: a rule the model satisfies by finding the exception.

#: ⛔ THE END-OF-TURN SENTENCE USED TO FORBID THE CALL THAT CLOSES `support`.
#: It said "reply with the answer and do NOT call any more tools", and the
#: only text that said to close the helper was the server's instructions,
#: which the loop never sent. Measured 2026-09-12 with the real model on a
#: task that needs both browsers: six runs out of six left `support` open,
#: and in the owner's own sessions one conversation of 247 steps used it 29
#: times and never closed it. The order is now part of the sentence about
#: ending, because that is the moment the model was told to stop.


def system_message(instructions: str = "") -> dict:
    """The one system message, from this build's prompt plus what the server
    says about itself.

    ⛔ ONE FUNCTION, THREE WRITERS. The message was assembled in the
    constructor, in the brain's restore and nowhere else, and the server's
    instructions - the only text that defines what `support` is for and that
    whoever opens it closes it - were in neither. They travel with the link
    and are refreshed at the start of every run, so a restored transcript and
    a new one carry the same current instructions.

    ⛔ AND THE TWO HALVES SAY DIFFERENT THINGS NOW. This prompt used to open
    with "open the browser with browser_open before anything else; if a tool
    answers that the browser is not open or is gone, call browser_open and
    carry on" - which is the server's first paragraph, in other words, glued
    to it a few lines later. The model read the same rule twice in one
    message, and two copies of a rule are two things to keep in agreement.

    The rule belongs to the server: it is a fact about the tools, and a
    standalone client that never sees this prompt still has to be told it.
    What is left here is what this loop owns - how the agent behaves, and how
    it WRITES.

    ⛔ AND MOVING IT MEANS THE SERVER MUST ACTUALLY STILL SAY IT, which is a
    thing to hold rather than to trust. A first draft of this change also made
    an empty `instructions` append a warning for the model to read; that was
    dropped, because the link launches this very server, so arriving here with
    nothing means the handshake failed and a sentence in the prompt helps
    nobody in that state. What guards the move instead is a gate over the
    server's own text: the rule has one home, and the gate says the home is
    not empty.
    """
    text = SYSTEM_PROMPT
    if instructions:
        text += chr(10) + chr(10) + instructions.strip()
    return {"role": "system", "content": text}


def said_only(messages) -> List[dict]:
    """The messages that are a TRANSCRIPT, which is everything anybody said.

    The system message is not one of them. It is what this build asks the model
    to be, it is rebuilt from `SYSTEM_PROMPT` plus the server's own instructions
    on every run, and a copy of it travelling with a conversation is a copy of
    CODE inside a file of DATA.

    ⛔ THE HALF THAT READS THIS RULE HAS EXISTED SINCE 2026-09-08; THE HALF THAT
    WRITES IT DID NOT. `remember` dropped the saved system message on the way
    in, because restoring it wholesale put an OLD prompt back and every change
    to the instructions reached new conversations only. Nothing stopped `save`
    from writing it, so every saved conversation went on carrying one - measured
    on the developer's own file, 1205 characters that nothing would ever read.
    Harmless in itself, and exactly the shape this project keeps finding one
    step later: the remedy for a stale duplicate is to stop WRITING it, not to
    keep remembering to ignore it.

    One function, both callers, so the two halves cannot come to disagree about
    what a transcript is.
    """
    return [m for m in messages or [] if m.get("role") != "system"]


Say = Callable[[str, str], Awaitable[None]]


async def _silent(_kind: str, _text: str) -> None:
    """The default narrator: says nothing, for a caller that wants an answer
    rather than a transcript."""


def mcp_tools_to_openai(tools) -> List[dict]:
    """MCP tool descriptions as OpenAI function definitions.

    Two details are load-bearing and both come from the API rejecting the
    alternative: `parameters` must be an object and never None, and the
    description is truncated because a long one is rejected rather than trimmed.
    """
    out = []
    for t in tools:
        out.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": (getattr(t, "description", "") or "")[:1024],
                "parameters": getattr(t, "inputSchema", None) or {"type": "object", "properties": {}},
            },
        })
    return out


# ⛔ `_result_text` STOOD HERE AND IT WAS `link.answer_of` WRITTEN OUT AGAIN. Five
# lines, the `[non-text result]` literal included, reading the same wire format
# from the same objects - while `text_of` in that module carried a docstring
# saying it was shared with this loop precisely so the two could not drift. It
# was not shared; it was copied. Both copies had tests, so either could have
# moved alone and stayed green.
#
# The loop reads `link.answer_of` now, and the measured account of why the flag is
# read at all travels with it. What is NOT here is an alias keeping the old
# name alive: the tests that held this function moved to the function, the way
# `run_task` and `Sessions.around` moved to the suite that was their only
# caller.


#: How much of a tool result the WATCHER is shown, and how much the MODEL is
#: sent. Two different jobs - the page is a window on the work, the message list
#: is what every later turn pays for - so the two numbers differ on purpose.
SHOWN, SENT = 1200, 8000


def shorten(text: str, limit: int, where: str) -> str:
    """`text` cut to `limit`, saying so whenever it cuts.

    ⛔ IT CUT IN SILENCE, AND THE PERSON WATCHING GOT THE SMALLER COPY. A read
    of a real page is tens of kilobytes; the page showed the first 1200
    characters, stopping mid-word with no ellipsis, no count and no hint that
    anything had been removed, while the line below handed the model nearly
    seven times as much. Somebody expanding a step to audit what the agent saw
    read a partial page as the whole one. The product's whole claim is that you
    can watch what it does, and the watcher was the one being given less.

    Both callers say it now, because the model reading a truncated page without
    being told is the same defect one level up: it can ask for the rest, but
    only if it knows there is a rest.

    The marker starts on a new line so the page files the result into an
    expandable block rather than onto the step row, and it is ASCII: a
    non-ASCII character on a line this server may print is a known way to kill
    the process on Windows.
    """
    if len(text) <= limit:
        return text
    return "%s\n[... %d more characters, not %s]" % (
        text[:limit], len(text) - limit, where)


def unknown_tool(name: str, known) -> str:
    """What the model is told when it calls a tool this server does not have.

    Written for the mistake actually made rather than for a typo in general:
    the names it reaches for are the old session tools, and what they used to
    do - find or start a session - is a thing that no longer needs doing.
    """
    return ("There is no tool called %s here. The two browsers, main and support, "
            "are already there: nothing has to be listed, started or chosen before "
            "acting, and every tool takes `browser` to say which one. Go straight to "
            "the task with one of: %s." % (name, ", ".join(known)))


class Conversation:
    """One transcript, and the loop that grows it.

    Kept as an object because the interface needs the transcript to survive an
    instruction: "and now sort them by price" only means something if the model
    still knows what "them" was. `do` throws the object away after one call and
    gets the old one-shot behaviour for free.
    """

    #: Ceiling on ONE reply, and it is set rather than left to the provider.
    #: Without it the provider assumes the model's maximum - 65536 on a current
    #: OpenAI model - and a credit-limited key is refused with a 402 before any
    #: work happens, quoting a token budget rather than naming the task. It is
    #: also the wrong shape for this loop: a turn is a sentence of reasoning and
    #: a tool call, not an essay, and the only turn that wants room is the last
    #: one. Generous for that, sixteen times smaller than the default.
    MAX_TOKENS = 8192

    def __init__(self, client, model: str, *,
                 max_tokens: int = MAX_TOKENS) -> None:
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.messages: List[dict] = [system_message()]
        self.tool_defs: Optional[List[dict]] = None
        self.usage = {"prompt": 0, "completion": 0, "calls": 0, "last_prompt": 0}

    @property
    def known(self) -> List[str]:
        """The tool names this server has, read off the definitions.

        ⛔ DERIVED, WHERE IT WAS A SECOND COPY ASSIGNED INSIDE A BRANCH. It was
        written in `run`, under `if self.tool_defs is None`, which is the one
        line that builds the definitions - so the list existed only when that
        branch had run, and it was the only attribute of this class not
        declared in `__init__`. A conversation whose definitions arrived any
        other way had no `known` at all, and the failure landed on the line
        below that tells a model it asked for a tool nobody has: an
        `AttributeError` in the handler for somebody else's mistake.

        Initialising it to an empty list in `__init__` would have been worse
        than the crash, because an empty list is a legal answer: every tool the
        model asked for would be refused as unknown, quietly and wrongly. The
        fact is a property of `tool_defs`, so it is read from `tool_defs`.
        """
        return [d["function"]["name"] for d in self.tool_defs or []]

    def _note_usage(self, resp) -> None:
        u = getattr(resp, "usage", None)
        if u is None:
            return
        last = getattr(u, "prompt_tokens", 0) or 0
        self.usage["prompt"] += last
        self.usage["completion"] += getattr(u, "completion_tokens", 0) or 0
        self.usage["calls"] += 1
        # The LAST turn's prompt, kept beside the running totals and not folded
        # into them. Each turn is sent the whole transcript, so the newest prompt
        # size IS the current occupancy of the context window; adding them up
        # counts every earlier turn again and races past any limit within a few
        # messages, which would make a meter built on it worse than none.
        self.usage["last_prompt"] = last

    async def run(self, task: str, call_tool, tools, *, say: Say = _silent,
                  describe=None, instructions: str = "") -> str:
        """Run one instruction to an answer.

        `call_tool(name, args)` performs a tool call and returns the MCP result;
        `tools` is the server's tool list. Both are passed rather than a session,
        so this has no opinion about how the browser is reached - which is what
        lets the interface serialise its calls against the frame pump.
        """
        if self.tool_defs is None:
            self.tool_defs = mcp_tools_to_openai(tools)
        # Refreshed every run rather than set once: the instructions belong to
        # the server the link is talking to now, and a transcript restored from
        # disk arrived with a system message this process did not write.
        self.messages[0] = system_message(instructions)
        self.messages.append({"role": "user", "content": task})

        # No turn ceiling. There was one, and what it did in practice was end
        # long tasks that were going fine with "task did not finish within
        # max_turns=25" - a task the person had watched work for twenty-five
        # steps, thrown away one step before it might have answered, with the
        # transcript at its largest and every one of those steps already paid
        # for. A number cannot tell a loop that is stuck from a task that is
        # simply long, and guessing wrong costs the whole run.
        #
        # What stops a run instead is the person watching it: the interface
        # keeps the task handle and the send button becomes a stop button while
        # work is in flight, so a cancel lands at the next tool call. That is a
        # judgement about THIS run rather than a constant chosen in advance,
        # and unlike the ceiling it can also stop a run on turn three.
        while True:
            # IN A THREAD, and that is what makes the stop button work. The
            # client is synchronous, so called here it would occupy the event
            # loop for the whole request: measured at zero scheduler slices
            # during a 300 ms call, which means `/chat/stop` cannot be served,
            # no event reaches the page and the live pane does not repaint -
            # for the entire time the model is thinking, which is exactly when
            # somebody reaches for stop.
            #
            # It is also a cancellation point, so a stop lands here rather than
            # waiting for the turn to reach its next tool call. What it does
            # NOT do is unsend the request: the thread runs to completion and
            # its answer is dropped, so a run stopped mid-turn still pays for
            # the reply it never used.
            resp = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model, messages=self.messages,
                tools=self.tool_defs, tool_choice="auto", temperature=0,
                max_tokens=self.max_tokens,
            )
            # Counted, saved with the transcript, and not announced:
            # the page drew it in a meter that is gone. The accounting
            # stays, because it is what the conversation cost; the
            # event went, because an event nobody draws is drawn as
            # raw JSON at the end of the transcript.
            self._note_usage(resp)
            msg = resp.choices[0].message
            self.messages.append(msg.model_dump())

            if getattr(msg, "content", None):
                await say("said", msg.content)
            if not msg.tool_calls:
                return msg.content or ""

            for call in msg.tool_calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError as exc:
                    # Recoverable: telling the model its arguments were unreadable
                    # lets it try again. Raising would end the whole task over one
                    # malformed message.
                    await say("err", f"{name}: unreadable arguments ({exc})")
                    self.messages.append({"role": "tool", "tool_call_id": call.id,
                                          "content": f"arguments were not valid JSON: {exc}"})
                    continue

                await say("tool", f"{name} {describe(name, args)}".strip()
                          if describe else name)
                # ⛔ A TOOL THE MODEL REMEMBERS AND THIS SERVER DOES NOT HAVE.
                # Earlier public versions of this server had session_list,
                # session_start and session_status, and a model trained on
                # that repository reaches for them: measured 2026-09-13 with
                # the real model, `session_list` as the FIRST call in six runs
                # out of twelve, on a page that never mentions the word. The
                # server answered `Unknown tool: session_list` and nothing
                # else, so the model guessed again. The loop knows the real
                # list, so it answers here - no round trip - and says what
                # the model was looking for: nothing has to be listed or
                # started, the two browsers are already there.
                if name not in self.known:
                    text = unknown_tool(name, self.known)
                    await say("err", text)
                    self.messages.append({"role": "tool", "tool_call_id": call.id,
                                          "content": text})
                    continue
                try:
                    text, failed = answer_of(await call_tool(name, args))
                except Exception as exc:
                    text = f"{type(exc).__name__}: {exc}"
                    await say("err", text)
                else:
                    await say("err" if failed else "result",
                              shorten(text, SHOWN, "shown"))
                self.messages.append({"role": "tool", "tool_call_id": call.id,
                                      "content": shorten(text, SENT, "sent")})


# ⛔ `run_task` STOOD HERE AND THE PRODUCT NEVER CALLED IT. Four lines over
# `Conversation`, kept because about twenty-five tests drove the loop through
# it - which its own docstring said, and which is the whole objection: a second
# entry point to the one loop, and the second one is the one nobody ships.
#
# It was not merely unused. It took an object with `.list_tools()` and
# `.call_tool()`, the MCP session shape the product wrapped when `Link` arrived,
# while the product passes `link.call` and `link.tools` straight to
# `Conversation.run`. So this file offered two ideas of how a tool is reached
# and only one of them was real - and the single end-to-end test of the loop
# reached PAST the Link for `link.session` to use the other one.
#
# The four lines moved to `tests/_loop.py`, where the convenience belongs and
# where nothing can mistake them for API; the end-to-end test now drives the
# canonical path. One way to run a turn.


# --- what the interface plugs in ----------------------------------------------

class Brain:
    """One method, on purpose.

    Whatever fills this slot - a model, a script, a recorded trace - receives
    what the user said, a way to act, and a way to narrate. Nothing above it
    needs to know which of those it is. The tests bring stub brains of their
    own; the product ships exactly one, below.
    """

    async def handle(self, text: str, link, say: Say) -> None:
        raise NotImplementedError


class OpenRouterBrain(Brain):
    """The product: the loop above, narrating each step as it takes it.

    A loop that returns an answer after ninety seconds of silence is a batch
    job; the same loop narrating each step is something a person can watch,
    interrupt and trust. The narration is not logging bolted on, it is the
    feature. This class supplies the two things `Conversation` does not: a
    transcript that survives an instruction, so the follow-up box means
    something, and a narrator, so the work is visible while it happens.

    It lived in a module of its own, `brain.py`, until 0.52.0: twenty-one
    lines of code forwarding to this file, beside a docstring about a second
    implementation removed in 0.4.0. One consumer of one loop is one file.
    """

    def __init__(self, client, model: str) -> None:
        self._convo = Conversation(client, model)

    def forget(self) -> None:
        """Drop the transcript and start a new one, same client and model.

        A new `Conversation` rather than a trimmed one: what makes the wait
        grow is the transcript being resent whole every turn, and half a
        transcript is a compromise nobody asked for - either the follow-up box
        still means something or it does not.
        """
        self._convo = Conversation(self._convo.client, self._convo.model)

    def remember(self, messages: list, usage: dict | None = None) -> None:
        """Take up a transcript that was written down, and continue it.

        The twin of `forget`, and the reason it exists is the same one stated
        there from the other side: what the follow-up box means is the
        transcript. A session reopened with the page showing the conversation
        and the model holding nothing would answer "and now sort them by price"
        with a question about what "them" is - worse than an empty chat, because
        it looks like it remembers.

        Written into the conversation this brain already has rather than by
        building a new one: the client and the model are this process's, and the
        file has no business deciding either.

        ⛔ AND THE SYSTEM MESSAGE IS THIS PROCESS'S TOO, FOR THE SAME REASON.
        A saved transcript carries the instructions as they were on the day the
        conversation started, so restoring it wholesale put an OLD prompt back
        and every change to `SYSTEM_PROMPT` reached new conversations only.
        Found on 2026-09-08 while telling the model to stop decorating answers
        with ticks and crosses: the change would have left every conversation
        anybody had open still doing it, forever, and the file would have won
        against the code with nothing saying so. The transcript is what was
        SAID; the instructions are what this build asks for.
        """
        if messages:
            self._convo.messages = [system_message()] + said_only(messages)
        if usage:
            self._convo.usage.update(usage)

    @property
    def usage(self) -> dict:
        return self._convo.usage

    @property
    def messages(self) -> list:
        return self._convo.messages

    async def handle(self, text: str, link, say: Say) -> None:
        # Nothing is caught here. There used to be a handler for the turn
        # ceiling, the one failure a person could act on by narrowing the task;
        # the ceiling is gone, and every remaining failure is either the
        # cancellation the stop button raises or something the interface's own
        # handler already reports.
        await self._convo.run(text, link.call, link.tools,
                              instructions=getattr(link, "instructions", ""),
                              say=say, describe=actions_help.summarise)
