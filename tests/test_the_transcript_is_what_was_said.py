"""What goes into a saved conversation is what was SAID, and nothing else.

⛔ THE READING HALF OF THIS RULE HAS EXISTED SINCE 2026-09-08 AND THE WRITING
HALF DID NOT. `OpenRouterBrain.remember` drops the saved system message on the
way in, because restoring it wholesale put an OLD prompt back and every change
to the instructions reached new conversations only - a file winning against the
code with nothing saying so. Nothing stopped `ChatService.save` from writing
one, so every saved conversation went on carrying a copy of this build's
prompt: measured on the developer's own file, 1205 characters that nothing
would ever read.

That is not a defect of behaviour - the restore already ignores it - which is
exactly why it survived. It is a copy of CODE inside a file of DATA, and the
remedy for a stale duplicate is to stop WRITING it rather than to keep
remembering to ignore it.

Both halves are asserted here, on either side of the file: what is written
down, and what a build makes of a file somebody else wrote.
"""
from __future__ import annotations

import json

from invisible_playwright_mcp import chats
from invisible_playwright_mcp.agent import OpenRouterBrain, SYSTEM_PROMPT, said_only, system_message
from invisible_playwright_mcp.chat import ChatService


class FakeLink:
    """A link that is never spoken to: these tests never run the loop."""

    tools: list = []
    instructions = ""

    async def call(self, name, arguments=None):
        raise AssertionError("no test here drives a tool")


def a_conversation(session_id="work"):
    """The product's own brain, with a transcript somebody could have written."""
    brain = OpenRouterBrain(object(), "a-model")
    service = ChatService(FakeLink(), brain, session_id=session_id)
    assert brain.messages[0]["role"] == "system", (
        "the loop needs the prompt at the head of what it sends")
    brain.messages.append({"role": "user", "content": "find me the price"})
    brain.messages.append({"role": "assistant", "content": "it is 12 euros"})
    return service, brain


def test_a_saved_conversation_carries_no_system_message(tmp_path, monkeypatch):
    """Known-bad: hand `save_chat` the brain's messages unfiltered again. The
    file grows a system message that nothing will ever read, and the suite was
    green through every version that did it."""
    monkeypatch.setenv("INVISIBLE_MCP_HOME", str(tmp_path))
    service, _ = a_conversation()
    service.save()

    saved = json.loads(chats.chat_path("work").read_bytes().decode("utf-8"))
    assert [m["role"] for m in saved["messages"]] == ["user", "assistant"], (
        "the file carries something other than what was said: %r"
        % [m.get("role") for m in saved["messages"]])
    blob = json.dumps(saved)
    assert SYSTEM_PROMPT[:60] not in blob, (
        "this build's instructions are written into the conversation file")


def test_a_restored_conversation_leads_with_the_prompt_of_the_build_reading_it(
        tmp_path, monkeypatch):
    """The other half, and the reason the first one is safe: the prompt is not
    lost by not being saved, it is REBUILT.

    Known-bad: have `remember` take the file's messages wholesale. The restored
    conversation then has no system message at all, because the file no longer
    carries one - which is the failure that makes the two halves one rule
    rather than two choices.
    """
    monkeypatch.setenv("INVISIBLE_MCP_HOME", str(tmp_path))
    service, _ = a_conversation()
    service.save()

    again = ChatService(FakeLink(), OpenRouterBrain(object(), "a-model"),
                        session_id="work")
    assert again.restore() is True

    got = again._brain.messages
    assert [m["role"] for m in got] == ["system", "user", "assistant"], (
        "a restored conversation is not the prompt followed by what was said: "
        "%r" % [m.get("role") for m in got])
    assert got[0] == system_message(), (
        "the restored conversation leads with something other than what this "
        "build asks for")


def test_a_file_an_older_build_wrote_is_read_the_same_way(tmp_path, monkeypatch):
    """⛔ EVERY FILE ON DISK TODAY HAS ONE, so this is not a hypothetical. A
    build that stopped writing the system message still has to read the files
    written by every build before it, and read them the way it always did:
    the saved prompt is dropped, this build's is used.

    Known-bad: drop the filter in `remember`. The conversation then leads with
    a prompt from the day it was started, forever, which is the defect that
    filter was written for.
    """
    monkeypatch.setenv("INVISIBLE_MCP_HOME", str(tmp_path))
    chats.save_chat("old", "written by an older build", [], [
        {"role": "system", "content": "an old instruction, with emoji please"},
        {"role": "user", "content": "find me the price"},
        {"role": "assistant", "content": "it is 12 euros"},
    ])

    service = ChatService(FakeLink(), OpenRouterBrain(object(), "a-model"),
                          session_id="old")
    assert service.restore() is True

    got = service._brain.messages
    assert [m["role"] for m in got] == ["system", "user", "assistant"]
    assert got[0] == system_message(), "the file's prompt won against the code"
    assert "emoji please" not in json.dumps(got), (
        "the instructions of the day this conversation started are still in it")


def test_what_counts_as_a_transcript_is_decided_in_one_place():
    """`said_only` is the whole rule, and it is exercised directly so that the
    two callers are asserting the same thing rather than two similar things.

    A case that must NOT fire: everything that is not a system message stays,
    in order, untouched. A filter that is too eager is the same defect as one
    that is too lax, one step further along - it would silently shorten
    somebody's conversation.
    """
    said = [{"role": "user", "content": "one"},
            {"role": "assistant", "content": "two"},
            {"role": "tool", "tool_call_id": "x", "content": "three"}]
    assert said_only([system_message()] + said) == said
    assert said_only(said) == said
    assert said_only([]) == [] and said_only(None) == []
    assert said_only([system_message(), system_message()]) == []
