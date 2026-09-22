"""Both halves of a session read and delete their file through one function.

⛔ WHAT WAS DUPLICATED HERE WAS A RULE, NOT A VALUE, WHICH IS WHY THE FIRST
PASS MISSED IT. When `invisible_playwright_mcp.storage` was carved out, the three things it took
were the ones that carry a VALUE somebody could get wrong: where the data
lives, how an id becomes a file name, how a file is replaced without a torn
read. Reading and deleting were left behind in both halves as four lines each,
and they looked like plumbing.

They are not plumbing. `load` answering None for a file that will not parse is
a DECISION - the alternative is raising on a server's first call because
something once wrote a broken byte - and it was written twice, in
`invisible_playwright_mcp.mcp.store` and in `invisible_playwright_mcp.chats`, with only one of the two explaining
itself. Deleting was the same again, and both copies answered a bool that
neither caller read and whose `False` meant "there was nothing there" and "it
could not be deleted", which are opposite news.

So this asserts the wiring rather than the behaviour: whatever the one
function does, both halves do. A copy coming back in either file is a copy
this cannot see any other way, because two identical implementations agree on
every input by construction - which is exactly why the duplication survived a
refactor that went looking for it.
"""
from __future__ import annotations

import json

from invisible_playwright_mcp import chats, storage
from invisible_playwright_mcp.mcp import store


def test_both_halves_read_through_the_one_reader(tmp_path, monkeypatch):
    """Known-bad: give either module back its own `json.loads` and its own
    try/except. It passes every test about saved sessions and conversations,
    and fails here."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    asked = []

    real = storage.read_json
    monkeypatch.setattr(storage, "read_json", lambda where: asked.append(where) or real(where))
    monkeypatch.setattr(store, "read_json", storage.read_json)
    monkeypatch.setattr(chats, "read_json", storage.read_json)

    store.save("work", {"main": {"seed": 1}}, focus="main")
    chats.save_chat("work", "a name", [], [])

    assert store.load("work")["browsers"] == {"main": {"seed": 1}}
    assert chats.load_chat("work")["name"] == "a name"
    assert len(asked) == 2, (
        "one of the two halves parses its own file: %r" % (asked,))


def test_both_halves_delete_through_the_one_eraser(tmp_path, monkeypatch):
    """Known-bad: give either module back its own `unlink` and try/except."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    asked = []

    real = storage.erase
    monkeypatch.setattr(storage, "erase", lambda where: asked.append(where) or real(where))
    monkeypatch.setattr(store, "_erase", storage.erase)
    monkeypatch.setattr(chats, "_erase", storage.erase)

    store.save("work", {"main": {}}, focus="main")
    chats.save_chat("work", "a name", [], [])
    assert store.path_of("work").is_file() and chats.chat_path("work").is_file()

    store.erase("work")
    chats.erase_chat("work")

    assert len(asked) == 2, (
        "one of the two halves deletes its own file: %r" % (asked,))
    assert not store.path_of("work").is_file()
    assert not chats.chat_path("work").is_file()


def test_erasing_something_that_is_not_there_is_not_a_failure(tmp_path, monkeypatch):
    """⛔ AND IT ANSWERS NOTHING, where both copies answered a bool nobody
    read. `Sessions.forget` carries the scar of that ambiguity in its own
    docstring: it once answered `False` for a session somebody else had
    already deleted, and the page told the person it was still working.

    Known-bad: let the exception out. Deleting a conversation that another tab
    deleted a second earlier then fails instead of being already done.
    """
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    assert store.erase("never-existed") is None
    assert chats.erase_chat("never-existed") is None


def test_a_file_that_will_not_parse_reads_as_nothing_saved(tmp_path, monkeypatch):
    """The decision itself, asserted once instead of twice: half a JSON
    document is exactly as usable as no document.

    Known-bad: let `json.JSONDecodeError` out of `read_json`. A server whose
    saved file was truncated by a full disk then cannot start.
    """
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    store.save("work", {"main": {"seed": 1}}, focus="main")
    chats.save_chat("work", "a name", [], [])

    for where in (store.path_of("work"), chats.chat_path("work")):
        whole = where.read_bytes()
        where.write_bytes(whole[:len(whole) // 2])

    assert store.load("work") is None
    assert chats.load_chat("work") is None
    # And a file that is simply absent reads the same way, which is the half
    # that makes the decision safe to rely on.
    assert store.load("never-existed") is None
    assert chats.load_chat("never-existed") is None


def test_the_saved_session_is_json_an_outside_reader_can_use(tmp_path, monkeypatch):
    """The file is a join between two PROGRAMS, so its shape is a contract and
    not an implementation detail: the MCP server writes it, the interface reads
    the same directory to know a session exists at all."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    where = store.save("work", {"main": {"seed": 1, "proxy": None}}, focus="main")

    got = json.loads(where.read_bytes().decode("utf-8"))
    assert got["id"] == "work" and got["focus"] == "main"
    assert got["browsers"]["main"]["seed"] == 1
    assert "name" not in got, (
        "the copy of `id` is back in the file that two programs share")
