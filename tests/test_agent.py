import pytest
from aihawk.agent import _result_text, mcp_tools_to_openai, run_task


class _Tool:
    def __init__(self, name): self.name = name; self.description = ""; self.inputSchema = {"type": "object", "properties": {}}


class _ToolsResult:
    def __init__(self, names): self.tools = [_Tool(n) for n in names]


class _Content:
    def __init__(self, text): self.text = text


class _CallResult:
    def __init__(self, text): self.content = [_Content(text)]


class _FakeMCP:
    def __init__(self): self.calls = []
    async def list_tools(self): return _ToolsResult(["browser_navigate", "browser_read_text"])
    async def call_tool(self, name, args): self.calls.append((name, args)); return _CallResult("PAGE TEXT")


class _Call:
    def __init__(self, name, arguments, cid="c1"):
        self.id = cid
        self.function = type("F", (), {"name": name, "arguments": arguments})()


class _Msg:
    def __init__(self, content=None, tool_calls=None):
        self.content = content; self.tool_calls = tool_calls
    def model_dump(self): return {"role": "assistant", "content": self.content}


class _Resp:
    def __init__(self, msg): self.choices = [type("C", (), {"message": msg})()]


class _FakeClient:
    """Scripted: first turn calls a tool, second turn returns a final answer."""
    def __init__(self): self.turn = 0
    class chat:  # noqa
        pass
    def __init__(self):
        self.turn = 0
        outer = self
        class _Completions:
            def create(self, **kw):
                outer.turn += 1
                if outer.turn == 1:
                    return _Resp(_Msg(tool_calls=[_Call("browser_read_text", '{"selector": "body"}')]))
                return _Resp(_Msg(content="The heading is hello"))
        self.chat = type("Chat", (), {"completions": _Completions()})()


def test_result_text_falls_back_for_non_text_content():
    none_text = type("Content", (), {"text": None})()
    result_with_none_text = type("Result", (), {"content": [none_text]})()
    assert _result_text(result_with_none_text)[0] == "[non-text result]"

    no_text_attr = type("Content", (), {})()
    result_without_text_attr = type("Result", (), {"content": [no_text_attr]})()
    assert _result_text(result_without_text_attr)[0] == "[non-text result]"


def test_mcp_tools_to_openai_shape():
    defs = mcp_tools_to_openai(_ToolsResult(["browser_navigate"]).tools)
    assert defs[0]["type"] == "function"
    assert defs[0]["function"]["name"] == "browser_navigate"


@pytest.mark.asyncio
async def test_run_task_drives_tools_then_returns_final_answer():
    mcp, client = _FakeMCP(), _FakeClient()
    out = await run_task(mcp, "read the page", client=client, model="x")
    assert out == "The heading is hello"
    assert mcp.calls == [("browser_read_text", {"selector": "body"})]
