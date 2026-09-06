"""The loop: model, tools, browser, repeat until it answers.

ONE loop. There were briefly two, which is how a README sentence saying "same
machinery" becomes false without anybody editing it: the second copy gets a fix,
the first does not, and the two answers diverge for a task that looks identical
from outside. They were merged, and later the second CALLER went too - the
`aihawk do` subcommand, removed on 2026-09-03 - so this loop now has exactly one
consumer in the product and one in the tests.

The narration is a parameter rather than a mode. `do` passes a sink that drops
everything, `ui` passes the thing that pushes events to the page, and neither
appears in here. A loop that knows whether it is being watched is a loop with two
behaviours to test.
"""
from __future__ import annotations

import json
from typing import Any, Awaitable, Callable, List, Optional

SYSTEM_PROMPT = (
    "You are a browser automation agent. You control a real, stealth Firefox "
    "browser ONLY through the provided tools. Inspect pages with "
    "browser_read_text / browser_snapshot / browser_read_html before acting on "
    "them. A person may be watching the browser while you work, so prefer one "
    "clear action at a time over long chains. When the task is done, reply with "
    "the answer in plain text and do NOT call any more tools. Report only what "
    "the page actually shows."
)

Say = Callable[[str, str], Awaitable[None]]


async def _silent(_kind: str, _text: str) -> None:
    """The default narrator: says nothing, so `do` prints only its answer."""


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


def _result_text(result) -> str:
    if not getattr(result, "content", None):
        return ""
    first = result.content[0]
    return getattr(first, "text", None) or "[non-text result]"


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

    def __init__(self, client, model: str, *, max_turns: int = 25,
                 max_tokens: int = MAX_TOKENS) -> None:
        self.client = client
        self.model = model
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.messages: List[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.tool_defs: Optional[List[dict]] = None
        self.usage = {"prompt": 0, "completion": 0, "calls": 0, "last_prompt": 0}

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
                  describe=None) -> str:
        """Run one instruction to an answer.

        `call_tool(name, args)` performs a tool call and returns the MCP result;
        `tools` is the server's tool list. Both are passed rather than a session,
        so this has no opinion about how the browser is reached - which is what
        lets the interface serialise its calls against the frame pump.
        """
        if self.tool_defs is None:
            self.tool_defs = mcp_tools_to_openai(tools)
        self.messages.append({"role": "user", "content": task})

        for _turn in range(self.max_turns):
            resp = self.client.chat.completions.create(
                model=self.model, messages=self.messages,
                tools=self.tool_defs, tool_choice="auto", temperature=0,
                max_tokens=self.max_tokens,
            )
            self._note_usage(resp)
            await say("usage", json.dumps(self.usage))
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
                try:
                    text = _result_text(await call_tool(name, args))
                except Exception as exc:
                    text = f"{type(exc).__name__}: {exc}"
                    await say("err", text)
                else:
                    await say("result", text[:1200])
                self.messages.append({"role": "tool", "tool_call_id": call.id,
                                      "content": text[:8000]})

        raise RuntimeError(f"task did not finish within max_turns={self.max_turns}")


async def run_task(mcp, task: str, *, client, model: str, max_turns: int = 25,
                   max_tokens: int = Conversation.MAX_TOKENS) -> str:
    """One instruction, one answer, no narration.

    Four lines over `Conversation`, and no longer called by the product: the
    `aihawk do` subcommand it was written for was removed on 2026-09-03. It is
    kept because the suite drives the loop through it - about twenty-five tests
    in test_agent_loop.py - and rewriting all of them onto `Conversation`
    directly would move a lot of code to delete four lines.
    """
    tools = (await mcp.list_tools()).tools
    convo = Conversation(client, model, max_turns=max_turns, max_tokens=max_tokens)
    return await convo.run(task, mcp.call_tool, tools)
