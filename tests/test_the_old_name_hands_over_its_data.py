"""Abandoning a name must not lose what was saved under it.

The package, the command, the module, the environment variables, the session
directory and the browser's own keys all carried the product's previous brand
until 2026-09-23. Renaming code is free. Renaming a NAME THAT SOMEBODY'S DATA IS
FILED UNDER is not: the data does not move with the literal, so the process
simply looks somewhere empty, and there is nothing to see except that everything
is gone.

Three kinds of saved thing, one rule each, and this file is all three:

  the session directory   moved onto the new name, once, and the move is said
                          out loud
  the environment         the retired name still ANSWERS, and says so
  the browser's keys      the value is carried across on the first read

⛔ EVERY CASE HERE IS THE ONE NOBODY WOULD RUN BY HAND. A developer's machine has
the new directory already, the new variables set, and an empty localStorage: the
upgrade path is exactly the state a person who has been using the product is in
and the person writing the code is not.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess

import pytest

from invisible_playwright_mcp import env as environment
from invisible_playwright_mcp import storage
from invisible_playwright_mcp.ui import PAGE

NODE = shutil.which("node")


# --- the environment -------------------------------------------------------


def test_the_new_name_is_what_gets_read():
    assert environment.read(environment.MODEL, {environment.MODEL: "new"}) == "new"


def test_the_retired_name_still_answers():
    """Somebody who set the old one finds it working, not ignored.

    Known-bad: drop the fallback from `env.read`. Every existing configuration
    then reads as unset, which for the model means silently falling back to the
    default and for the home means silently using a different directory.
    """
    # Reaching into the private set on purpose: the deduplication is what these
    # cases are about, so knowing it exists is their job. It had a public
    # `forget_what_was_said()` for one run, and the surface gate refused a
    # function in the product that only a test calls.
    environment._SAID.clear()
    was = environment.RETIRED[environment.MODEL]
    assert environment.read(environment.MODEL, {was: "old"}) == "old"


def test_the_new_name_wins_when_both_are_set():
    """The more recent decision, the same ordering that makes the shell beat
    `.env`. Known-bad: return the retired value first, and somebody who set the
    new name to fix something finds the old one still in charge."""
    environment._SAID.clear()
    was = environment.RETIRED[environment.MODEL]
    both = {environment.MODEL: "new", was: "old"}
    assert environment.read(environment.MODEL, both) == "new"


def test_a_name_that_was_never_retired_has_no_fallback():
    """⛔ THE FALLBACK IS PER NAME, NOT A PREFIX SWAP. Read as a rule about
    prefixes it would answer for every `INVISIBLE_MCP_*` name anybody invents,
    including one whose old spelling means something else entirely."""
    assert environment.read("INVISIBLE_MCP_INVENTED", {"AIHAWK_INVENTED": "x"}) is None


def test_the_retired_name_says_so_once(caplog):
    """⛔ A SILENT FALLBACK IS HOW A RETIRED NAME BECOMES PERMANENT. It has to
    be heard, and heard once: a warning on every lookup is a warning people
    filter out, and `read` is called per request.

    On the logger rather than a print, because stdout is the MCP protocol
    channel and a print there corrupts the stream.
    """
    environment._SAID.clear()
    was = environment.RETIRED[environment.HOME]
    with caplog.at_level(logging.WARNING, logger="invisible_playwright_mcp"):
        for _ in range(3):
            environment.read(environment.HOME, {was: "/somewhere"})
    said = [r for r in caplog.records if was in r.getMessage()]
    assert len(said) == 1, "the notice was given %d times, not once" % len(said)
    assert environment.HOME in said[0].getMessage(), (
        "the notice does not name the variable to rename it to: %r"
        % said[0].getMessage())


def test_every_retired_name_is_answered_for():
    """⛔ THE MAP IS THE CONTRACT, so nothing may be in it that `read` ignores.
    An entry nobody reads is a promise of compatibility that is not kept."""
    for new, was in environment.RETIRED.items():
        environment._SAID.clear()
        assert environment.read(new, {was: "v"}) == "v", (
            "%s is in RETIRED and does not answer for %s" % (was, new))


# --- the session directory -------------------------------------------------


@pytest.fixture()
def a_machine(tmp_path, monkeypatch):
    """A system data directory of our own, with no override set.

    The override has to go: `conftest.py` points it at a temporary directory for
    the whole suite, and every case below is about the branch that runs when
    nobody has set it.
    """
    monkeypatch.delenv(environment.HOME, raising=False)
    monkeypatch.delenv(environment.RETIRED[environment.HOME], raising=False)
    base = tmp_path / "data"
    base.mkdir()
    monkeypatch.setattr(storage, "_base", lambda: base)
    return base


def _a_session_in(directory, name="kept.json"):
    (directory / "sessions").mkdir(parents=True, exist_ok=True)
    (directory / "sessions" / name).write_bytes(b'{"browsers": {}}')


def test_the_old_directory_is_moved_onto_the_new_name(a_machine):
    """The upgrade path, and the whole reason this function exists.

    Known-bad: delete the call in `cli.py`. Everything here still passes and
    every user's logins disappear on upgrade, which is why the call has a test
    of its own below.
    """
    old = a_machine / storage.RETIRED_DIRECTORY
    _a_session_in(old)

    moved = storage.carry_over_the_old_directory()

    assert moved == a_machine / storage.DIRECTORY
    assert (moved / "sessions" / "kept.json").is_file(), (
        "the session did not arrive under the new name")
    assert not old.exists(), "the old directory is still there, so a later run "\
                             "would find both and stop carrying anything over"
    assert storage.home() == moved


def test_it_does_nothing_when_the_new_directory_is_already_there(a_machine, monkeypatch):
    """⛔ NO MERGE, ON PURPOSE. Folding an older tree into the live one would
    have to decide which copy of a session wins, and there is no right answer to
    that: the live one is the live one, and the old tree is left where it is for
    somebody to look at.

    ⛔ AND THE ASSERTION IS THAT NOTHING WAS ATTEMPTED, not that nothing
    happened. Written the obvious way - both trees populated, then check they did
    not merge - it passed with the `new.exists()` guard REMOVED: `os.replace`
    onto a non-empty directory fails by itself, the swallow catches it, and the
    outcome is identical to the correct one. The guard would have been untested
    and the test would have looked like it covered it. What it does cover that
    way is the platform, and on POSIX a new directory that happens to be EMPTY
    is replaced rather than refused.
    """
    old = a_machine / storage.RETIRED_DIRECTORY
    new = a_machine / storage.DIRECTORY
    _a_session_in(old, "was.json")
    _a_session_in(new, "is.json")

    tried = []
    monkeypatch.setattr(os, "replace", lambda a, b: tried.append((a, b)))

    assert storage.carry_over_the_old_directory() is None
    assert tried == [], (
        "a move was attempted with the new directory already there: %r" % (tried,))
    assert (old / "sessions" / "was.json").is_file(), "the old tree was touched"
    assert not (new / "sessions" / "was.json").exists(), "the trees were merged"


def test_it_does_nothing_when_there_is_nothing_to_carry(a_machine):
    assert storage.carry_over_the_old_directory() is None
    assert not (a_machine / storage.DIRECTORY).exists(), (
        "an empty directory was created where the answer was 'nothing to do'")


def test_it_does_nothing_when_the_home_is_pointed_somewhere(a_machine, monkeypatch):
    """The caller named a directory. Moving one they did not name is not this
    function's business, and doing it anyway would move data out from under
    somebody who had put it where they wanted it."""
    _a_session_in(a_machine / storage.RETIRED_DIRECTORY)
    monkeypatch.setenv(environment.HOME, str(a_machine / "elsewhere"))

    assert storage.carry_over_the_old_directory() is None
    assert (a_machine / storage.RETIRED_DIRECTORY).is_dir()


def test_a_directory_that_will_not_move_does_not_stop_the_start(a_machine, monkeypatch):
    """⛔ REFUSING TO START IS WORSE THAN NOT CARRYING. The sessions stay
    readable under the old name and the next run tries again; a raised exception
    here would be a product that will not open because of a directory the person
    never asked about."""
    _a_session_in(a_machine / storage.RETIRED_DIRECTORY)

    def refuses(*args, **kwargs):
        raise OSError("in use")

    monkeypatch.setattr(os, "replace", refuses)
    assert storage.carry_over_the_old_directory() is None


def test_the_documented_directory_is_the_one_the_code_uses():
    """⛔ A PATH IN PROSE HAS NO LINK BACK TO THE CODE, AND THIS ONE DRIFTED
    WITHIN A DAY. `docs/mcp-server.md` names the default for all three platforms,
    and the package rename left it saying `invisible_playwright_mcp` - the
    module's spelling - while the directory is the product's. A reader following
    it looks in a folder that does not exist and concludes their sessions are
    gone: the same outcome as losing them, reached by reading instead of running.

    ⛔ AND IT CHECKS EVERY PATH IN THE ROW, NOT THAT THE ROW MENTIONS THE
    NAME. Written as `storage.DIRECTORY in row`, it passed with the Windows path
    put back to the module's spelling, because the macOS and Linux paths beside
    it still carried the right one: a row naming three platforms could be wrong
    about one of them and read as covered.
    """
    import pathlib as _pathlib
    import re as _re

    doc = (_pathlib.Path(__file__).resolve().parents[1] / "docs" / "mcp-server.md"
           ).read_text(encoding="utf-8")
    row = [line for line in doc.split("\n") if environment.HOME in line]
    assert row, "%s is not documented at all" % environment.HOME

    named = set(_re.findall(r"/([A-Za-z0-9_.-]*playwright[A-Za-z0-9_.-]*)", row[0]))
    assert named == {storage.DIRECTORY}, (
        "the row for %s documents %r as the directory; the code uses %r, and a "
        "reader following a path that does not exist concludes their sessions "
        "are gone" % (environment.HOME, sorted(named), storage.DIRECTORY))


def test_the_startup_edge_actually_carries_it_over(a_machine):
    """⛔ THE FUNCTION BEING RIGHT IS HALF OF IT. Nothing above notices if
    nobody calls it, and the call is one line at one edge: measured by running
    the CLI rather than by reading it, because "is it wired up" is not a
    question source can answer.
    """
    from click.testing import CliRunner

    from invisible_playwright_mcp import cli

    _a_session_in(a_machine / storage.RETIRED_DIRECTORY)
    result = CliRunner().invoke(cli.main, ["ui", "--help"])

    assert result.exit_code == 0, result.output
    assert (a_machine / storage.DIRECTORY / "sessions" / "kept.json").is_file(), (
        "the CLI started without carrying the old directory over")


# --- what the browser keeps ------------------------------------------------


@pytest.mark.skipif(not NODE, reason="needs node to EXECUTE the page")
def test_a_value_saved_under_the_retired_key_is_carried_across():
    """⛔ THE KEYS ARE PER ORIGIN, AND THE ORIGIN DOES NOT CHANGE. The interface
    is served from the same 127.0.0.1 before and after, so those entries are
    still in the browser of everybody who used it, and one of the three holds an
    unsent draft.

    The real `carried` is sliced out of the assembled page, never doubled: a
    double would pass while the page did something else, which is the rule this
    suite already applies to `wipe`.
    """
    code = PAGE[PAGE.index("<script"):]
    src = code[code.index("const STORE ="):]
    src = src[:src.index("\n}\n") + 3]

    harness = [
        "const store = {'aihawk.rail': '1'};",
        "globalThis.localStorage = {",
        "  getItem(k){ return k in store ? store[k] : null; },",
        "  setItem(k, v){ store[k] = String(v); },",
        "  removeItem(k){ delete store[k]; }};",
        src,
        "const got = carried(STORE + 'rail');",
        "process.stdout.write(JSON.stringify({got, keys: Object.keys(store)}));",
    ]
    done = subprocess.run([NODE, "-e", "\n".join(harness)], capture_output=True,
                          text=True, encoding="utf-8", timeout=30)
    assert done.returncode == 0, done.stderr
    out = json.loads(done.stdout)

    assert out["got"] == "1", "the retired key did not answer: %r" % (out,)
    assert out["keys"] == ["invisible-playwright-mcp.rail"], (
        "the value was not moved onto the new key and the old one removed, so "
        "the next read does the same work again: %r" % (out,))


@pytest.mark.skipif(not NODE, reason="needs node to EXECUTE the page")
def test_the_new_key_wins_and_a_blocked_store_answers_nothing():
    """Two cases in one run, because they share a harness: the new key is
    preferred when both are there, and a localStorage that THROWS - a private
    window, blocked site data - answers null instead of killing the page."""
    code = PAGE[PAGE.index("<script"):]
    src = code[code.index("const STORE ="):]
    src = src[:src.index("\n}\n") + 3]

    harness = [
        "const store = {'aihawk.rail': 'old', 'invisible-playwright-mcp.rail': 'new'};",
        "globalThis.localStorage = {",
        "  getItem(k){ return k in store ? store[k] : null; },",
        "  setItem(k, v){ store[k] = String(v); },",
        "  removeItem(k){ delete store[k]; }};",
        src,
        "const both = carried(STORE + 'rail');",
        "globalThis.localStorage = {getItem(){ throw new Error('blocked'); },",
        "  setItem(){ throw new Error('blocked'); },",
        "  removeItem(){ throw new Error('blocked'); }};",
        "const blocked = carried(STORE + 'rail');",
        "process.stdout.write(JSON.stringify({both, blocked}));",
    ]
    done = subprocess.run([NODE, "-e", "\n".join(harness)], capture_output=True,
                          text=True, encoding="utf-8", timeout=30)
    assert done.returncode == 0, done.stderr
    out = json.loads(done.stdout)

    assert out["both"] == "new", "the retired key won over the new one: %r" % (out,)
    assert out["blocked"] is None, (
        "a store that throws was not survived, so a browser with site data "
        "blocked gets a page that does not run: %r" % (out,))


@pytest.mark.skipif(not NODE, reason="needs node to EXECUTE the page")
def test_every_key_the_page_keeps_is_built_from_the_one_prefix():
    """⛔ A KEY SPELLED OUT IN ITS OWN FILE IS A KEY THE HAND-OVER CANNOT FIND.
    `carried` derives the retired name by swapping one prefix for the other, so
    a key that does not start with `STORE` reads as never having been saved."""
    code = PAGE[PAGE.index("<script"):]
    spelled = [line.strip() for line in code.split("\n")
               if "invisible-playwright-mcp." in line and "STORE" not in line
               and not line.strip().startswith("//")]
    assert spelled == [], (
        "these lines write the prefix out instead of using STORE: %r" % spelled)
