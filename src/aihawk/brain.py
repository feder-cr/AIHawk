"""What turns a typed sentence into browser actions, and narrates while it does.

The shell was built with this slot deliberately empty and a stub in it, so that
the seam a model plugs into would be exercised rather than imagined. This module
fills the slot with the one implementation that ships:

`OpenRouterBrain` is the product: the shared agent loop, narrating each step.
A loop that returns an answer after ninety seconds of silence is a batch job;
the same loop narrating each step is something a person can watch, interrupt
and trust. The narration is not logging bolted on, it is the feature.

There used to be a second implementation here, a literal-command placeholder
that drove the browser with no model. It was removed in 0.4.0: driving the
engine by hand without a model is what the invisible_playwright library is
for, with Playwright's whole API instead of six commands. The tests never
depended on it - they bring their own stub brains - and neither should you.
"""
from __future__ import annotations

from typing import Awaitable, Callable

from . import actions_help
from .agent import Conversation
from .link import Link

Say = Callable[[str, str], Awaitable[None]]


class Brain:
    """One method, on purpose.

    Whatever fills this slot - a model, a script, a recorded trace - receives
    what the user said, a way to act, and a way to narrate. Nothing above it
    needs to know which of those it is.
    """

    async def handle(self, text: str, link: Link, say: Say) -> None:
        raise NotImplementedError


class OpenRouterBrain(Brain):
    """The product: the shared loop, narrating each step as it takes it.

    The loop itself is `agent.Conversation`. This
    class supplies the two things that differ: a transcript that survives an
    instruction, so the follow-up box means something, and a narrator, so the
    work is visible while it happens rather than only when it ends.

    Briefly there were two loops. That is how a README sentence promising "same
    machinery" goes false with nobody editing it, and why this one is four lines.
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
        """
        if messages:
            self._convo.messages = list(messages)
        if usage:
            self._convo.usage.update(usage)

    @property
    def usage(self) -> dict:
        return self._convo.usage

    @property
    def messages(self) -> list:
        return self._convo.messages

    async def handle(self, text: str, link: Link, say: Say) -> None:
        # Nothing is caught here. There used to be a handler for the turn
        # ceiling, the one failure a person could act on by narrowing the task;
        # the ceiling is gone, and every remaining failure is either the
        # cancellation the stop button raises or something the interface's own
        # handler already reports.
        await self._convo.run(text, link.call, link.tools,
                              say=say, describe=actions_help.summarise)
