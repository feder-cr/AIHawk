"""The agent loop in aihawk/agent.py, driven by a scripted model.

There is no OpenRouter key on this machine, so the model is replaced by a stub.
Everything else is real: the objects handed to the loop are the same classes the
production code would receive.

REAL SHAPES COPIED, AND WHERE THEY WERE READ

  mcp.types.Tool, ListToolsResult, CallToolResult, TextContent, ImageContent
      Built here as the genuine pydantic models from `mcp` 1.29.1, not as
      look-alikes, so a field the loop reads cannot exist here and be missing in
      production. Field lists read from `mcp.types` model_fields:
        Tool             name(req) title description inputSchema(req) outputSchema
                         icons annotations meta execution
        CallToolResult   meta content(req) structuredContent isError
        TextContent      type='text' text(req) annotations meta
        ImageContent     type='image' data mimeType annotations meta
      Note that `inputSchema` is REQUIRED on a real Tool, so the "tool with no
      inputSchema" case can only arrive as a duck-typed object or as an empty
      dict; both are covered.

  openai.types.chat.ChatCompletion / Choice / ChatCompletionMessage /
  ChatCompletionMessageFunctionToolCall / Function
      Also the genuine pydantic models from `openai` 3.7.0. This matters more
      than it looks: the loop calls `msg.model_dump()` and replays the result to
      the model, so the exact dict a real message produces is part of the
      contract under test. A hand-written stub with a hand-written model_dump
      would have tested the stub.

  The scripted client mirrors the surface `llm.make_client` returns, which is
  `openai.OpenAI`: the loop only ever touches `client.chat.completions.create`.

  The scripted MCP session mirrors `mcp.ClientSession` as `Link` uses
  it: `await mcp.list_tools()` returning a ListToolsResult, and
  `await mcp.call_tool(name, args)` returning a CallToolResult.

  Tool names and schemas are the real ones, taken from the server itself
  (session_new_page, session_list_pages, session_select_page, session_close_page,
  browser_navigate, browser_read_text, browser_snapshot, browser_read_html,
  browser_take_screenshot, browser_click, browser_click_at, browser_type,
  browser_press_key, browser_evaluate).

No test in this file starts a browser or spawns the MCP server.
"""
from __future__ import annotations

import copy
import inspect
import json

import pytest

import mcp.types as mt
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
    Function,
)

from aihawk.agent import SYSTEM_PROMPT, _result_text, mcp_tools_to_openai, run_task


# --------------------------------------------------------------------------
# real-shaped builders
# --------------------------------------------------------------------------

# The genuine inputSchema FastMCP derives from `browser_navigate(url: str,
# wait_until: str = "domcontentloaded")`, in the shape the loop forwards.
NAVIGATE_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "title": "Url"},
        "wait_until": {
            "type": "string",
            "title": "Wait Until",
            "default": "domcontentloaded",
        },
    },
    "required": ["url"],
}


def tool(name: str, description: str | None = "d", schema: dict | None = None) -> mt.Tool:
    """A real mcp.types.Tool. `inputSchema` is required by the model, so pass {}
    for the "server declared nothing" case."""
    return mt.Tool(
        name=name,
        description=description,
        inputSchema=NAVIGATE_SCHEMA if schema is None else schema,
    )


def tools_result(*tools: mt.Tool) -> mt.ListToolsResult:
    return mt.ListToolsResult(tools=list(tools))


def text_result(text: str) -> mt.CallToolResult:
    return mt.CallToolResult(content=[mt.TextContent(type="text", text=text)])


def assistant_tool_calls(*calls: tuple[str, str, str]) -> ChatCompletionMessage:
    """A real assistant message asking for tools. Each call is (id, name, arguments)."""
    return ChatCompletionMessage(
        role="assistant",
        content=None,
        tool_calls=[
            ChatCompletionMessageFunctionToolCall(
                id=cid, type="function", function=Function(name=name, arguments=args)
            )
            for cid, name, args in calls
        ],
    )


def assistant_answer(text: str | None) -> ChatCompletionMessage:
    """A real assistant message with no tool calls: the loop's stop condition."""
    return ChatCompletionMessage(role="assistant", content=text, tool_calls=None)


class ScriptedModel:
    """Stands in for the `openai.OpenAI` client `llm.make_client` returns.

    Only `chat.completions.create(**kwargs)` is exercised, which is all the loop
    uses. Every request is recorded in `self.requests` so a test can assert what
    the loop actually sent back, not merely what it returned.

    The recording is a DEEP COPY on purpose. The loop mutates one `messages`
    list in place across turns, so storing the argument by reference makes every
    recorded request point at the final state: turn 1 then appears to have
    carried the whole conversation, and any assertion about what was sent early
    silently measures the end. That was observed here before the copy was added.
    """

    def __init__(self, replies, *, repeat_last: bool = False):
        self.replies = list(replies)
        self.repeat_last = repeat_last
        self.requests: list[dict] = []
        self.chat = _Chat(self)

    def _create(self, kwargs: dict) -> ChatCompletion:
        self.requests.append(copy.deepcopy(kwargs))
        i = len(self.requests) - 1
        if i >= len(self.replies):
            if not self.repeat_last:
                raise AssertionError(
                    f"the loop asked the model {i + 1} times, the script has "
                    f"{len(self.replies)} replies"
                )
            i = len(self.replies) - 1
        msg = self.replies[i]
        return ChatCompletion(
            id="chatcmpl-test",
            created=0,
            model=kwargs.get("model", "stub"),
            object="chat.completion",
            choices=[
                Choice(
                    index=0,
                    finish_reason="tool_calls" if msg.tool_calls else "stop",
                    message=msg,
                )
            ],
        )


class _Chat:
    def __init__(self, owner: ScriptedModel):
        self.completions = _Completions(owner)


class _Completions:
    def __init__(self, owner: ScriptedModel):
        self._owner = owner

    def create(self, **kwargs) -> ChatCompletion:
        return self._owner._create(kwargs)


class ScriptedMCP:
    """Stands in for `mcp.ClientSession` after `initialize()`.

    `results` maps a tool name to what calling it returns; anything not named
    returns a short text result. Every call is recorded in order.
    """

    def __init__(self, tools=None, results=None, *, raises: Exception | None = None):
        self._tools = tools if tools is not None else tools_result(tool("browser_navigate"))
        self._results = results or {}
        self._raises = raises
        self.calls: list[tuple[str, dict]] = []
        self.list_tools_count = 0

    async def list_tools(self) -> mt.ListToolsResult:
        self.list_tools_count += 1
        return self._tools

    async def call_tool(self, name, arguments=None) -> mt.CallToolResult:
        self.calls.append((name, arguments))
        if self._raises is not None:
            raise self._raises
        return self._results.get(name, text_result(f"result of {name}"))


def messages_of(request: dict) -> list[dict]:
    return request["messages"]


def tool_messages(request: dict) -> list[dict]:
    return [m for m in request["messages"] if m.get("role") == "tool"]


# --------------------------------------------------------------------------
# mcp_tools_to_openai: the tool definitions handed to the model
# --------------------------------------------------------------------------

def test_definition_carries_exactly_the_three_fields_openai_requires():
    """Known-bad: emitting the MCP tool dict straight through, or naming the
    schema field `input_schema`. The OpenAI function-tool object is
    {"type": "function", "function": {name, description, parameters}} and an
    unexpected key at either level is rejected by the API."""
    defs = mcp_tools_to_openai(tools_result(tool("browser_navigate", "Go to a url.")).tools)

    assert len(defs) == 1
    assert set(defs[0]) == {"type", "function"}
    assert defs[0]["type"] == "function"
    fn = defs[0]["function"]
    assert set(fn) == {"name", "description", "parameters"}
    assert fn["name"] == "browser_navigate"
    assert fn["description"] == "Go to a url."
    assert fn["parameters"] == NAVIGATE_SCHEMA


def test_every_real_tool_name_survives_in_order():
    """Known-bad: a dict keyed by name (order lost, duplicates collapsed) or a
    filter that drops the session_* half. The model can only call what appears
    in this list."""
    names = [
        "session_new_page", "session_list_pages", "session_select_page",
        "session_close_page", "browser_navigate", "browser_read_text",
        "browser_snapshot", "browser_read_html", "browser_take_screenshot",
        "browser_click", "browser_click_at", "browser_type",
        "browser_press_key", "browser_evaluate",
    ]
    defs = mcp_tools_to_openai(tools_result(*[tool(n) for n in names]).tools)
    assert [d["function"]["name"] for d in defs] == names


def test_a_tool_with_no_description_becomes_an_empty_string_not_none():
    """`description` is optional on mcp.types.Tool and arrives as None.

    Known-bad: passing the None straight through. The measured behaviour is the
    empty string, and this test fails if the field goes missing too."""
    defs = mcp_tools_to_openai(tools_result(tool("browser_snapshot", None)).tools)
    fn = defs[0]["function"]
    assert "description" in fn
    assert fn["description"] == ""
    assert fn["description"] is not None


def test_a_description_longer_than_1024_characters_is_truncated_to_1024():
    """OpenAI caps a function description at 1024 characters and this is not
    hypothetical: the real `browser_click_at` docstring measures 1124 characters
    today, so one of the shipped tools is truncated on every run.

    Known-bad: dropping the [:1024] slice, which makes the API reject the whole
    request, or truncating to a different length."""
    long_desc = "x" * 1030 + "TAIL-THAT-MUST-BE-CUT"
    defs = mcp_tools_to_openai(tools_result(tool("browser_click_at", long_desc)).tools)

    got = defs[0]["function"]["description"]
    assert len(got) == 1024
    assert got == long_desc[:1024]
    assert "TAIL-THAT-MUST-BE-CUT" not in got


def test_a_description_of_exactly_1024_characters_is_kept_whole():
    """The boundary, asserted from the other side.

    Known-bad: [:1023], or a `> 1024` guard that lops a character off every
    description at the limit. The previous test alone cannot see that."""
    desc = "y" * 1023 + "Z"
    assert len(desc) == 1024
    defs = mcp_tools_to_openai(tools_result(tool("browser_snapshot", desc)).tools)
    got = defs[0]["function"]["description"]
    assert len(got) == 1024
    assert got.endswith("Z")


def test_a_short_description_is_not_padded_or_rewritten():
    defs = mcp_tools_to_openai(tools_result(tool("browser_read_text", "The visible text.")).tools)
    assert defs[0]["function"]["description"] == "The visible text."


def test_a_tool_with_no_input_schema_gets_a_valid_empty_object_schema():
    """A None `parameters` is rejected by the OpenAI API, so the fallback has to
    be a real JSON-Schema object.

    Two arrivals are covered: a duck-typed tool object with no `inputSchema`
    attribute at all, and a real Tool whose schema is the empty dict (the model
    makes the field required, so {} is what an argument-free tool can look like).

    Known-bad: `getattr(t, "inputSchema", None)` alone, which yields None for the
    first case and {} for the second, both of which the API refuses."""
    class _NoSchemaTool:
        name = "session_list_pages"
        description = "Every open tab."

    defs = mcp_tools_to_openai([_NoSchemaTool(), tool("session_close_page", "Close a tab.", {})])

    for d in defs:
        params = d["function"]["parameters"]
        assert params is not None
        assert isinstance(params, dict)
        assert params.get("type") == "object"
        assert params.get("properties") == {}
        assert params == {"type": "object", "properties": {}}


def test_the_fallback_schema_is_a_fresh_object_for_each_tool():
    """Known-bad: hoisting the default to a module-level constant, which makes
    every argument-free tool share one dict; a later caller that annotates or
    mutates one definition would silently edit all the others."""
    class _NoSchemaTool:
        def __init__(self, name):
            self.name = name
            self.description = ""

    defs = mcp_tools_to_openai([_NoSchemaTool("a"), _NoSchemaTool("b")])
    first = defs[0]["function"]["parameters"]
    second = defs[1]["function"]["parameters"]
    assert first == second
    assert first is not second

    first["properties"]["injected"] = {"type": "string"}
    assert second["properties"] == {}


def test_a_declared_schema_is_forwarded_unchanged_including_required():
    """Known-bad: rebuilding the schema and losing `required`, after which the
    model may omit `url` and browser_navigate is called with nothing to open."""
    defs = mcp_tools_to_openai(tools_result(tool("browser_navigate")).tools)
    params = defs[0]["function"]["parameters"]
    assert params["required"] == ["url"]
    assert params["properties"]["wait_until"]["default"] == "domcontentloaded"


def test_the_definitions_are_json_serialisable():
    """They are about to be sent over the wire, so a pydantic object left inside
    would fail at request time rather than here.

    Known-bad: forwarding `t.inputSchema` as a model instead of a dict."""
    defs = mcp_tools_to_openai(tools_result(tool("browser_type"), tool("browser_click")).tools)
    assert json.loads(json.dumps(defs)) == defs


def test_no_tools_produces_an_empty_list():
    """Pinned as a fact, not as an endorsement: OpenAI rejects `tools: []`, so a
    server that exposed nothing would fail at the first request rather than here.
    See the report."""
    assert mcp_tools_to_openai(tools_result().tools) == []


# --------------------------------------------------------------------------
# _result_text: what the browser sends back to the model
# --------------------------------------------------------------------------

def test_result_text_returns_the_text_of_a_text_content():
    assert _result_text(text_result("hello-from-the-page")) == "hello-from-the-page"


def test_result_text_is_empty_for_empty_or_missing_content():
    """Known-bad: indexing content[0] unguarded, which raises IndexError and
    kills the run on a tool that legitimately returns nothing."""
    assert _result_text(mt.CallToolResult(content=[])) == ""

    class _NoContent:
        pass

    assert _result_text(_NoContent()) == ""


def test_result_text_labels_a_non_text_content_instead_of_crashing():
    """A real ImageContent has no `text` attribute at all. browser_take_screenshot
    returns exactly that.

    Known-bad: `first.text`, which raises AttributeError. The measured behaviour
    is the placeholder, so the screenshot never reaches the model; that gap is in
    the report."""
    shot = mt.CallToolResult(
        content=[mt.ImageContent(type="image", data="aGk=", mimeType="image/png")]
    )
    assert _result_text(shot) == "[non-text result]"


def test_result_text_reads_only_the_first_content_block():
    """Pins measured behaviour that is also a defect: a multi-block result loses
    everything after the first block, silently.

    Known-bad, in the sense of what would break this assertion: joining the
    blocks. If someone does that deliberately this test should be updated, not
    deleted, because the current wording is what the model actually sees."""
    multi = mt.CallToolResult(
        content=[
            mt.TextContent(type="text", text="FIRST"),
            mt.TextContent(type="text", text="SECOND"),
        ]
    )
    assert _result_text(multi) == "FIRST"
    assert "SECOND" not in _result_text(multi)


def test_an_empty_text_block_is_reported_as_a_non_text_result():
    """Also measured behaviour and also a defect: an empty string is falsy, so a
    tool that correctly found nothing (an empty element read by
    browser_read_text) is described to the model as a non-text result, which is
    a different fact."""
    assert _result_text(text_result("")) == "[non-text result]"


# --------------------------------------------------------------------------
# the loop: stopping, ordering, ids, truncation, limits
# --------------------------------------------------------------------------

async def test_the_loop_stops_and_returns_the_text_when_the_model_answers():
    """Known-bad: looping until max_turns regardless, which burns 25 requests
    and then raises on a task that was already finished."""
    mcp = ScriptedMCP()
    model = ScriptedModel([assistant_answer("The heading is hello")])

    out = await run_task(mcp, "read the page", client=model, model="z-ai/glm-4.6")

    assert out == "The heading is hello"
    assert mcp.calls == []
    assert len(model.requests) == 1


async def test_a_final_answer_with_no_content_returns_the_empty_string():
    """A model can stop with content None. Known-bad: returning None, which the
    CLI would print as the string "None"."""
    out = await run_task(ScriptedMCP(), "t", client=ScriptedModel([assistant_answer(None)]), model="m")
    assert out == ""
    assert isinstance(out, str)


async def test_the_first_request_carries_the_system_prompt_the_task_and_the_tools():
    """Known-bad: dropping the system prompt (the model then has no instruction
    to stop calling tools), sending the task as a system message, or forgetting
    tool_choice, after which a model may answer from memory without ever opening
    the browser."""
    mcp = ScriptedMCP(tools=tools_result(tool("browser_navigate"), tool("browser_read_text")))
    model = ScriptedModel([assistant_answer("done")])

    await run_task(mcp, "open example and read it", client=model, model="z-ai/glm-4.6")

    req = model.requests[0]
    msgs = messages_of(req)
    assert msgs[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert msgs[1] == {"role": "user", "content": "open example and read it"}
    assert req["model"] == "z-ai/glm-4.6"
    assert req["tool_choice"] == "auto"
    assert req["temperature"] == 0
    assert [d["function"]["name"] for d in req["tools"]] == [
        "browser_navigate", "browser_read_text",
    ]


async def test_every_tool_call_in_one_message_runs_once_and_in_order():
    """Known-bad: executing only tool_calls[0], which is what a model asking for
    navigate + read_text in one message would silently lose."""
    mcp = ScriptedMCP(
        tools=tools_result(tool("browser_navigate"), tool("browser_type"), tool("browser_click"))
    )
    model = ScriptedModel([
        assistant_tool_calls(
            ("call_a", "browser_navigate", '{"url": "http://127.0.0.1:8000/form"}'),
            ("call_b", "browser_type", '{"selector": "#name", "text": "ada"}'),
            ("call_c", "browser_click", '{"selector": "#submit"}'),
        ),
        assistant_answer("submitted"),
    ])

    out = await run_task(mcp, "fill the form", client=model, model="m")

    assert out == "submitted"
    assert mcp.calls == [
        ("browser_navigate", {"url": "http://127.0.0.1:8000/form"}),
        ("browser_type", {"selector": "#name", "text": "ada"}),
        ("browser_click", {"selector": "#submit"}),
    ]


async def test_each_tool_result_is_returned_under_its_own_tool_call_id():
    """A mismatched or reused tool_call_id makes the next request fail, so the
    pairing is the load-bearing part.

    Known-bad: appending every result under msg.tool_calls[0].id, which passes a
    naive "the id is present" check while pairing every result with the wrong
    call."""
    mcp = ScriptedMCP(
        tools=tools_result(tool("browser_navigate"), tool("browser_read_text")),
        results={
            "browser_navigate": text_result("NAVIGATED"),
            "browser_read_text": text_result("PAGE-BODY"),
        },
    )
    model = ScriptedModel([
        assistant_tool_calls(
            ("call_nav", "browser_navigate", '{"url": "http://127.0.0.1"}'),
            ("call_read", "browser_read_text", '{"selector": "body"}'),
        ),
        assistant_answer("read it"),
    ])

    await run_task(mcp, "read", client=model, model="m")

    second = model.requests[1]
    results = tool_messages(second)
    assert [m["tool_call_id"] for m in results] == ["call_nav", "call_read"]
    assert [m["content"] for m in results] == ["NAVIGATED", "PAGE-BODY"]
    for m in results:
        assert m["role"] == "tool"
        assert set(m) >= {"role", "tool_call_id", "content"}


async def test_the_assistant_message_is_replayed_before_its_tool_results():
    """OpenAI refuses a tool message whose assistant message with the matching
    tool_calls is not already in the history.

    Known-bad: appending only the tool results and dropping msg.model_dump(),
    which produces "messages with role tool must be a response to a preceding
    message with tool_calls"."""
    mcp = ScriptedMCP(tools=tools_result(tool("browser_navigate")))
    model = ScriptedModel([
        assistant_tool_calls(("call_1", "browser_navigate", '{"url": "http://127.0.0.1"}')),
        assistant_answer("ok"),
    ])

    await run_task(mcp, "go", client=model, model="m")

    msgs = messages_of(model.requests[1])
    roles = [m["role"] for m in msgs]
    assert roles == ["system", "user", "assistant", "tool"]

    replayed = msgs[2]
    assert replayed["tool_calls"][0]["id"] == "call_1"
    assert replayed["tool_calls"][0]["function"]["name"] == "browser_navigate"
    assert msgs[3]["tool_call_id"] == "call_1"


async def test_the_whole_history_grows_and_is_resent_every_turn():
    """Known-bad: rebuilding `messages` per turn, or sending only the last
    exchange, after which the model forgets the task after the first tool call."""
    mcp = ScriptedMCP(tools=tools_result(tool("browser_navigate"), tool("browser_read_text")))
    model = ScriptedModel([
        assistant_tool_calls(("c1", "browser_navigate", '{"url": "http://127.0.0.1"}')),
        assistant_tool_calls(("c2", "browser_read_text", '{"selector": "body"}')),
        assistant_answer("done"),
    ])

    await run_task(mcp, "the original task", client=model, model="m")

    lengths = [len(messages_of(r)) for r in model.requests]
    assert lengths == [2, 4, 6]
    for r in model.requests:
        assert messages_of(r)[1] == {"role": "user", "content": "the original task"}


async def test_the_tool_definitions_are_listed_once_and_resent_unchanged():
    """Known-bad: calling list_tools inside the turn loop, which pays an MCP
    round trip per turn; or mutating tool_defs between turns, which makes the
    model's tool names drift from the server's."""
    mcp = ScriptedMCP(tools=tools_result(tool("browser_navigate"), tool("browser_read_text")))
    model = ScriptedModel([
        assistant_tool_calls(("c1", "browser_navigate", '{"url": "http://127.0.0.1"}')),
        assistant_tool_calls(("c2", "browser_read_text", "{}")),
        assistant_answer("done"),
    ])

    await run_task(mcp, "t", client=model, model="m")

    assert mcp.list_tools_count == 1
    assert len(model.requests) == 3
    first_tools = model.requests[0]["tools"]
    for r in model.requests[1:]:
        assert r["tools"] == first_tools


async def test_a_tool_result_longer_than_8000_characters_is_truncated_to_8000():
    """browser_read_text can return a whole page, and an untruncated result blows
    the context window a few turns later.

    The 8000th character is a marker, so an off-by-one (a [:7999] slice) fails
    here rather than passing on the length alone."""
    body = "a" * 7999 + "Z" + "b" * 1000
    mcp = ScriptedMCP(
        tools=tools_result(tool("browser_read_text")),
        results={"browser_read_text": text_result(body)},
    )
    model = ScriptedModel([
        assistant_tool_calls(("c1", "browser_read_text", '{"selector": "body"}')),
        assistant_answer("read"),
    ])

    await run_task(mcp, "read", client=model, model="m")

    sent = tool_messages(model.requests[1])[0]["content"]
    assert len(sent) == 8000
    assert sent.endswith("Z")
    assert "b" not in sent


async def test_a_result_at_or_below_the_limit_is_sent_whole():
    """Known-bad: an unconditional slice that also truncates, or a guard that
    trims short results. The exact-8000 case is the one a `> 8000` check gets
    wrong."""
    exact = "c" * 7999 + "E"
    mcp = ScriptedMCP(
        tools=tools_result(tool("browser_read_text")),
        results={"browser_read_text": text_result(exact)},
    )
    model = ScriptedModel([
        assistant_tool_calls(("c1", "browser_read_text", "{}")),
        assistant_answer("read"),
    ])

    await run_task(mcp, "read", client=model, model="m")

    sent = tool_messages(model.requests[1])[0]["content"]
    assert sent == exact
    assert len(sent) == 8000


async def test_max_turns_is_enforced_and_the_error_names_the_limit():
    """A model that keeps calling tools forever must stop costing money.

    Known-bad: `while True`, which never returns; or an error message that does
    not carry the number, leaving the operator with no idea what to raise."""
    mcp = ScriptedMCP(tools=tools_result(tool("browser_navigate")))
    model = ScriptedModel(
        [assistant_tool_calls(("c", "browser_navigate", '{"url": "http://127.0.0.1"}'))],
        repeat_last=True,
    )

    with pytest.raises(RuntimeError) as excinfo:
        await run_task(mcp, "loop forever", client=model, model="m", max_turns=3)

    assert "max_turns=3" in str(excinfo.value)
    assert len(model.requests) == 3
    assert len(mcp.calls) == 3


async def test_a_task_finishing_on_the_last_allowed_turn_still_returns():
    """The boundary from the other side. Known-bad: `range(max_turns - 1)`, which
    raises on a run that finished exactly within its budget."""
    mcp = ScriptedMCP(tools=tools_result(tool("browser_navigate")))
    model = ScriptedModel([
        assistant_tool_calls(("c1", "browser_navigate", '{"url": "http://127.0.0.1"}')),
        assistant_answer("finished on turn two"),
    ])

    out = await run_task(mcp, "t", client=model, model="m", max_turns=2)
    assert out == "finished on turn two"


async def test_max_turns_zero_asks_the_model_nothing_and_raises():
    """Known-bad: an off-by-one that grants one free turn to a caller who asked
    for none."""
    mcp = ScriptedMCP()
    model = ScriptedModel([assistant_answer("should never be reached")])

    with pytest.raises(RuntimeError) as excinfo:
        await run_task(mcp, "t", client=model, model="m", max_turns=0)

    assert "max_turns=0" in str(excinfo.value)
    assert model.requests == []


def test_the_shipped_default_turn_budget_is_25():
    """The CLI never passes max_turns, so this default is the cap every real run
    gets. Known-bad: lowering it to a number that cannot finish a multi-page
    task, which would only show up as a RuntimeError in front of a user."""
    assert inspect.signature(run_task).parameters["max_turns"].default == 25


async def test_empty_tool_arguments_become_an_empty_dict():
    """Models emit `arguments: ""` for a tool that takes nothing.

    Known-bad: `json.loads(call.function.arguments)`, which raises
    JSONDecodeError on the empty string and kills the run on the most ordinary
    call there is."""
    mcp = ScriptedMCP(tools=tools_result(tool("session_list_pages", "tabs", {})))
    model = ScriptedModel([
        assistant_tool_calls(("c1", "session_list_pages", "")),
        assistant_answer("listed"),
    ])

    await run_task(mcp, "list the tabs", client=model, model="m")

    assert mcp.calls == [("session_list_pages", {})]


async def test_arguments_are_parsed_from_json_not_forwarded_as_a_string():
    """Known-bad: passing call.function.arguments through untouched, after which
    the MCP server receives a string where it expects a mapping."""
    mcp = ScriptedMCP(tools=tools_result(tool("browser_click_at")))
    model = ScriptedModel([
        assistant_tool_calls(("c1", "browser_click_at", '{"x": 120, "y": 44.5, "ok": true}')),
        assistant_answer("clicked"),
    ])

    await run_task(mcp, "click", client=model, model="m")

    name, args = mcp.calls[0]
    assert isinstance(args, dict)
    assert args == {"x": 120, "y": 44.5, "ok": True}


async def test_malformed_tool_arguments_are_reported_back_and_the_run_continues():
    """Updated on purpose, exactly as the version before it asked to be.

    It used to pin the opposite - truncated JSON raising out of run_task - and
    said so while calling it a defect: a task twenty turns in lost everything
    because one message came back malformed, which happens routinely at length.
    The model is told instead, and gets to try again.

    The tool is NOT called with the broken arguments, which is the half that
    would be dangerous to lose: recovering must not mean guessing what was meant.
    """
    mcp = ScriptedMCP(tools=tools_result(tool("browser_navigate")))
    model = ScriptedModel([
        assistant_tool_calls(("c1", "browser_navigate", '{"url": "http://127.0.0.1"')),
        assistant_answer("recovered"),
    ])

    answer = await run_task(mcp, "go", client=model, model="m")

    assert answer == "recovered"
    assert mcp.calls == [], "the tool must not run with arguments that did not parse"
    assert len(model.requests) == 2, "the model was asked again after being told"
    fed_back = [m for m in model.requests[-1]["messages"] if m.get("role") == "tool"]
    assert fed_back and "JSON" in fed_back[-1]["content"]
    assert fed_back[-1]["tool_call_id"] == "c1"


async def test_a_failing_tool_is_reported_back_instead_of_ending_the_run():
    """Same family, from the browser side, and updated for the same reason.

    A timeout, a closed page, a refused connection: on a real site these are the
    normal texture of a task, not the end of one. The model sees the error as the
    tool's result and can try another way - which is the only thing that makes a
    twenty-step task on a page nobody controls survivable.

    What it must NOT do is swallow it: the text of the failure reaches the model
    intact, so it can tell a bad selector from a dead host.
    """
    boom = RuntimeError("Page.goto: net::ERR_CONNECTION_REFUSED")
    mcp = ScriptedMCP(tools=tools_result(tool("browser_navigate")), raises=boom)
    model = ScriptedModel([
        assistant_tool_calls(("c1", "browser_navigate", '{"url": "http://127.0.0.1:1"}')),
        assistant_answer("could not reach it"),
    ])

    answer = await run_task(mcp, "go", client=model, model="m")

    assert answer == "could not reach it"
    assert len(model.requests) == 2
    fed_back = [m for m in model.requests[-1]["messages"] if m.get("role") == "tool"]
    assert fed_back and "ERR_CONNECTION_REFUSED" in fed_back[-1]["content"]


async def test_an_error_flagged_result_is_still_fed_back_as_text():
    """isError is not read, so the model gets the message body with nothing
    marking it as a failure. Pinned because it decides what the model believes:
    the text has to survive even when the call failed, otherwise the model
    retries blind."""
    failed = mt.CallToolResult(
        content=[mt.TextContent(type="text", text="selector #missing not found")],
        isError=True,
    )
    mcp = ScriptedMCP(
        tools=tools_result(tool("browser_click")),
        results={"browser_click": failed},
    )
    model = ScriptedModel([
        assistant_tool_calls(("c1", "browser_click", '{"selector": "#missing"}')),
        assistant_answer("could not click"),
    ])

    out = await run_task(mcp, "click", client=model, model="m")

    assert out == "could not click"
    assert tool_messages(model.requests[1])[0]["content"] == "selector #missing not found"


async def test_a_screenshot_reaches_the_model_as_a_placeholder_only():
    """End to end through the loop, not just through _result_text: the model asks
    for browser_take_screenshot, which is one of the advertised tools, and the
    only thing that comes back is "[non-text result]". The image is dropped."""
    shot = mt.CallToolResult(
        content=[mt.ImageContent(type="image", data="aGk=", mimeType="image/png")]
    )
    mcp = ScriptedMCP(
        tools=tools_result(tool("browser_take_screenshot", "One screenshot.", {})),
        results={"browser_take_screenshot": shot},
    )
    model = ScriptedModel([
        assistant_tool_calls(("c1", "browser_take_screenshot", "{}")),
        assistant_answer("I cannot see the image"),
    ])

    await run_task(mcp, "look at the page", client=model, model="m")

    sent = tool_messages(model.requests[1])[0]["content"]
    assert sent == "[non-text result]"
    assert "aGk=" not in sent


async def test_two_calls_to_the_same_tool_keep_distinct_ids_and_results():
    """Known-bad: keying results by tool name, which collapses a repeated
    browser_read_text into one message and breaks the id pairing."""
    seen = []

    class _Alternating(ScriptedMCP):
        async def call_tool(self, name, arguments=None):
            self.calls.append((name, arguments))
            seen.append(arguments)
            return text_result(f"read #{len(seen)}")

    mcp = _Alternating(tools=tools_result(tool("browser_read_text")))
    model = ScriptedModel([
        assistant_tool_calls(
            ("c1", "browser_read_text", '{"selector": "h1"}'),
            ("c2", "browser_read_text", '{"selector": "p"}'),
        ),
        assistant_answer("both read"),
    ])

    await run_task(mcp, "read twice", client=model, model="m")

    results = tool_messages(model.requests[1])
    assert [m["tool_call_id"] for m in results] == ["c1", "c2"]
    assert [m["content"] for m in results] == ["read #1", "read #2"]
