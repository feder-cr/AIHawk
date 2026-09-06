"""The OpenRouter key must never reach the browser child process.

`runner.child_env` builds the environment handed to the stdio child that runs
`aihawk.mcp`, which in turn launches Firefox. The key belongs to
the parent only: the parent talks to OpenRouter, the child talks to a browser.
A commit in this repository calls the removal a security fix, and the history
carries a PR titled "Replace the committed API key", so the guarantee is not
theoretical.

Every test below names the known-bad input that breaks it. The two tests marked
xfail(strict=True) assert guarantees the code does NOT yet provide: they are
reachable leaks, not accepted trade-offs, and the strict marker turns the suite
red the moment somebody fixes `child_env` without deleting the marker.

None of these tests launch a browser or spawn the MCP server. The one test that
exercises `drive` replaces the transport with fakes.
"""
from __future__ import annotations

import contextlib
import os
import sys

import pytest

from aihawk import agent as agent_mod
from aihawk import link as link_mod
from aihawk import llm as llm_mod
from aihawk import runner
from aihawk.runner import child_env

# A sentinel that cannot occur by accident inside PATH or any other real value.
KEY = "sk-or-v1-TESTSENTINEL-do-not-ship-0123456789"
KEY_NAME = "OPENROUTER_API_KEY"


def values_carrying(env, needle):
    """Names of every variable whose VALUE contains `needle`."""
    return sorted(name for name, value in env.items() if needle in str(value))


# ---------------------------------------------------------------------------
# the key is removed
# ---------------------------------------------------------------------------


def test_child_env_strips_the_key_by_name():
    """Known-bad: delete the `env.pop("OPENROUTER_API_KEY", None)` line and the
    child inherits the key verbatim under its own name."""
    env = child_env({}, {"PATH": "/x", KEY_NAME: KEY})
    assert KEY_NAME not in env
    assert env["PATH"] == "/x", "unrelated base variables must survive"


def test_no_variable_name_matches_the_key_name_in_any_case():
    """The pop is exact-match, so this asserts the OUTCOME rather than the call.

    Known-bad: replace the pop with `env.pop("OPENROUTER_KEY", None)` - a
    plausible typo that leaves the real name in place and that a test asserting
    `"OPENROUTER_KEY" not in env` would happily pass.
    """
    env = child_env({}, {KEY_NAME: KEY, "PATH": "/x"})
    assert [n for n in env if n.upper() == KEY_NAME] == []


def test_the_key_string_appears_in_no_value_at_all():
    """The guarantee that matters is about the VALUE, not the name: scan the
    whole dict.

    Known-bad: `env.pop(KEY_NAME)` replaced by `env[KEY_NAME] = ""`, which
    satisfies a name-only assertion in some shapes and, more importantly, any
    future change that copies the key into a second variable for the child.
    """
    base = {"PATH": "/x", "HOME": "/home/u", KEY_NAME: KEY, "AIHAWK_MODEL": "z-ai/glm-4.6"}
    env = child_env({"proxy": "http://h:1", "seed": 7, "binary": "C:/ff.exe"}, base)
    assert values_carrying(env, KEY) == []


def test_the_key_string_appears_in_no_value_when_it_is_also_an_option():
    """A user who passes the key as a proxy password or a profile path would be
    doing something strange, but the STEALTHFOX_* values are the ones this code
    writes itself, so they are the ones it is responsible for.

    Known-bad: a future `env["STEALTHFOX_OPENROUTER_KEY"] = key` added to give
    the child a model of its own.
    """
    env = child_env({"proxy": "http://h:1", "seed": 1}, {KEY_NAME: KEY})
    stealthfox = {n: v for n, v in env.items() if n.startswith("STEALTHFOX_")}
    assert stealthfox, "the fixture must actually produce STEALTHFOX_ values"
    assert values_carrying(stealthfox, KEY) == []


# ---------------------------------------------------------------------------
# case: what os.environ does here, measured rather than assumed
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="os.environ is case-sensitive off Windows")
def test_windows_normalises_a_lowercase_name_so_the_exact_pop_still_catches_it(monkeypatch):
    """Measured on this machine: `os.environ` is `os._Environ` with
    `encodekey = str.upper`, so `set openrouter_api_key=...` in the shell is
    stored and enumerated as OPENROUTER_API_KEY. The exact-match pop therefore
    covers every case variant that a Windows shell can produce.

    This test asserts the platform contract as well as the outcome, so that if a
    future Python stops upper-casing, the failure names the reason instead of
    looking like a regression in child_env.

    Known-bad: on a Python where `dict(os.environ)` preserved the caller's case,
    the pop would miss and the child would inherit the key. That is exactly the
    xfail below, reached through a plain mapping.
    """
    monkeypatch.setenv("openrouter_api_key", KEY)
    assert os.environ.get(KEY_NAME) == KEY, "Windows environ no longer upper-cases names"
    assert "openrouter_api_key" not in dict(os.environ)

    env = child_env({}, os.environ)
    assert values_carrying(env, KEY) == []


def test_a_case_variant_name_in_a_plain_mapping_is_stripped_too():
    """Known-bad is the current code: `env.pop("OPENROUTER_API_KEY", None)`
    against a mapping holding `openrouter_api_key`."""
    env = child_env({}, {"PATH": "/x", "openrouter_api_key": KEY})
    assert values_carrying(env, KEY) == []


def test_a_duplicate_of_the_key_under_another_name_is_stripped_too():
    """Known-bad is the current code: the same secret under OPENAI_API_KEY is
    copied straight into the child environment."""
    env = child_env({}, {"PATH": "/x", KEY_NAME: KEY, "OPENAI_API_KEY": KEY})
    assert values_carrying(env, KEY) == []




# ── what the mutation test asked for ────────────────────────────────────────
#
# The two xfails above this line were deleted when child_env started removing by
# value as well as by name. Mutating that code afterwards showed the suite was
# thinner than it looked: four of five mutations survived, and two of them
# survived because nothing here exercised the path at all.
#
# The rest survived because child_env removes the key three ways that overlap:
# collection is case-insensitive, removal by name is case-insensitive, and
# removal also matches by VALUE. Break any one and a lowercase variable is
# still removed by another, so the guarantee holds and the suite is right to
# stay green. Breaking two together does fail, which is what says the
# redundancy is real rather than a gate that cannot see.
#
# So these tests pin the GUARANTEE - after child_env, no variable carries the
# key, whatever it was called - and not the three mechanisms. Pinning each
# mechanism would assert the implementation, and would go red on a rewrite
# that kept the promise.


def test_a_key_that_was_never_in_the_environment_still_scrubs_its_copies():
    """The command-line case, which reading the environment cannot cover.

    `--openrouter-key` puts the key in no variable at all, so there is nothing
    for child_env to find by name - while a copy of that same string under
    OPENAI_API_KEY is sitting right there. This is why child_env takes `key`.

    Known-bad is the version that does not: drop the `key` parameter from the
    collection and this environment reaches the browser with the secret in it.
    """
    env = child_env({}, {"PATH": "/x", "OPENAI_API_KEY": KEY}, key=KEY)
    assert values_carrying(env, KEY) == []
    assert env["PATH"] == "/x", "it removed more than the secret"


def test_a_lowercase_variable_and_its_copy_both_go():
    """The POSIX case with a copy, which neither half covers alone.

    A lowercase `openrouter_api_key` is a different variable to the shell and
    the same secret to anything reading the process environment, and the copy
    under a second name can only be found by matching the value.
    """
    env = child_env({}, {"PATH": "/x", "openrouter_api_key": KEY,
                         "OPENAI_API_KEY": KEY})
    assert values_carrying(env, KEY) == []
    assert env["PATH"] == "/x"


def test_an_empty_variable_is_not_treated_as_a_secret():
    """Otherwise a guard that removes by value removes the whole environment.

    Two things stop it, and the second one was nearly deleted for looking
    redundant. Collection filters on the value being truthy, and `if key:`
    rejects an empty key; `secrets.discard("")` then catches what either of
    those would let through.

    Mutating `discard` away alone changes nothing, which read as dead code and
    was written up as dead code here. It is not: mutate away the truthiness
    filter as well and this test fails, because the empty string becomes a
    secret and every empty variable in the environment matches it. Each line
    is the other's backstop, and a single-line mutation cannot tell the
    difference between a backstop and a spare part.
    """
    env = child_env({}, {"PATH": "/x", "EMPTY": "", "OPENROUTER_API_KEY": ""},
                    key="")
    assert env["PATH"] == "/x"
    assert env["EMPTY"] == "", "an empty variable was mistaken for the secret"


def test_the_options_still_arrive_when_the_environment_is_being_scrubbed():
    """The scrub rewrites the dict the options are then written into, so the two
    halves meet. A filter that returned a new mapping and dropped the writes
    would leave the browser with no proxy and no seed, silently."""
    env = child_env({"proxy": "socks5://proxy.example.com:1080", "seed": 4242},
                    {"OPENROUTER_API_KEY": KEY, "PATH": "/x"})
    assert env["STEALTHFOX_PROXY"] == "socks5://proxy.example.com:1080"
    assert env["STEALTHFOX_SEED"] == "4242"
    assert values_carrying(env, KEY) == []
# ---------------------------------------------------------------------------
# what SHOULD reach the child does
# ---------------------------------------------------------------------------


def test_every_option_maps_to_its_stealthfox_name():
    """Known-bad: rename any one of these to a name the MCP server does not read
    (STEALTHFOX_PROXY_URL, STEALTHFOX_HEADED) and the option becomes a silent
    no-op - the run still succeeds, just without the proxy or the seed."""
    env = child_env(
        {
            "proxy": "http://u:p@h:8080",
            "seed": 42,
            "headed": True,
            "binary": "C:/ff.exe",
            "profile_dir": "C:/prof",
        },
        {"PATH": "/x"},
    )
    assert env["STEALTHFOX_PROXY"] == "http://u:p@h:8080"
    assert env["STEALTHFOX_SEED"] == "42"
    assert env["STEALTHFOX_HEADLESS"] == "0"
    assert env["STEALTHFOX_BINARY"] == "C:/ff.exe"
    assert env["STEALTHFOX_PROFILE_DIR"] == "C:/prof"


def test_seed_zero_is_a_seed_and_not_an_absent_option():
    """Known-bad: `if opts.get("seed") is not None` weakened to
    `if opts.get("seed")`. Seed 0 is a valid deterministic fingerprint, and
    dropping it silently hands the run a random identity instead - a failure
    that no exception reports and that every other seed test misses."""
    env = child_env({"seed": 0}, {})
    assert env["STEALTHFOX_SEED"] == "0"


def test_absent_options_add_no_variable_rather_than_an_empty_one():
    """An empty string is not the same as unset: the child reads these with
    os.environ.get, so STEALTHFOX_PROXY="" is a truthy PRESENCE for any code
    that checks membership, and can select a proxy path with no proxy.

    Known-bad: rewriting the body as unconditional
    `env["STEALTHFOX_PROXY"] = str(opts.get("proxy") or "")` for each option.
    """
    env = child_env({}, {"PATH": "/x"})
    assert [n for n in env if n.startswith("STEALTHFOX_")] == []

    explicit_none = child_env(
        {"proxy": None, "seed": None, "headed": False, "binary": None, "profile_dir": None},
        {"PATH": "/x"},
    )
    assert [n for n in explicit_none if n.startswith("STEALTHFOX_")] == []


def test_no_emitted_variable_is_an_empty_string():
    """The class assertion behind the test above: whatever options exist now or
    later, none of them may be emitted empty.

    Known-bad: an option added later that maps a falsy value through str().
    """
    env = child_env({"proxy": "", "binary": "", "profile_dir": "", "seed": 3}, {"PATH": "/x"})
    assert [n for n, v in env.items() if v == ""] == []


def test_headed_false_sets_nothing_so_the_default_stays_headless():
    """Known-bad: `env["STEALTHFOX_HEADLESS"] = "0" if opts.get("headed") else "1"`
    looks harmless and pins the value, removing the server's own default."""
    env = child_env({"headed": False}, {})
    assert "STEALTHFOX_HEADLESS" not in env


def test_the_result_is_a_plain_str_to_str_dict():
    """StdioServerParameters declares env as dict[str, str] and validates it, so
    a non-str value raises at spawn time rather than at build time.

    Known-bad: dropping the str() around opts["seed"], which is typed int by the
    CLI, so the failure only appears when --seed is actually used.
    """
    env = child_env({"seed": 42, "proxy": "http://h:1"}, {"PATH": "/x"})
    assert type(env) is dict
    assert all(isinstance(n, str) and isinstance(v, str) for n, v in env.items())


# ---------------------------------------------------------------------------
# the base environment is not mutated
# ---------------------------------------------------------------------------


def test_the_base_mapping_is_not_mutated():
    """Known-bad: `env = base_env` instead of `env = dict(base_env)`. The pop
    then deletes the key from the caller's mapping - and the real caller passes
    os.environ, so the parent loses its own key. The first run works, and a
    second run in the same process cannot authenticate."""
    base = {"PATH": "/x", KEY_NAME: KEY}
    before = dict(base)
    env = child_env({"proxy": "http://h:1"}, base)

    assert base == before, "child_env must not touch the mapping it was given"
    assert base[KEY_NAME] == KEY
    assert env is not base


def test_os_environ_itself_survives_the_call(monkeypatch):
    """The same guarantee against the mapping the production path actually
    passes, which is os._Environ and not a dict.

    Known-bad: the aliasing bug above, which a dict-only test still catches, plus
    any future in-place scrub such as `base_env.pop(...)` before copying.
    """
    monkeypatch.setenv(KEY_NAME, KEY)
    env = child_env({"seed": 1}, os.environ)
    assert os.environ[KEY_NAME] == KEY
    assert KEY_NAME not in env


# ---------------------------------------------------------------------------
# the wiring: child_env being correct is worthless if drive does not use it
# ---------------------------------------------------------------------------


def _conversation_returning(box):
    """A stand-in for `agent.Conversation` that records what `drive` built it with.

    Shaped like the real one where drive touches it: constructed with (client,
    model) and run with (task, call_tool, tools). Anything else would pass while
    drive was calling something that does not exist.
    """

    class _Convo:
        def __init__(self, client, model, **kw):
            box["client"] = client
            box["model"] = model

        async def run(self, task, call_tool, tools, **kw):
            box["task"] = task
            return "FINAL"

    return _Convo


class _FakeSession:
    def __init__(self, read, write):
        self.read, self.write = read, write

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def list_tools(self):
        # Link asks for the tool list as soon as it opens, so a session double
        # that cannot answer is a double of an older Link.
        class _R:
            tools = []
        return _R()

    async def initialize(self):
        return None


async def test_the_link_hands_the_child_the_scrubbed_environment(monkeypatch):
    """No browser and no child process: the transport and the session are
    replaced, and only the StdioServerParameters are read.

    This is the test that fails if somebody bypasses the helper. Known-bad:
    `env=dict(os.environ)` in `Link.open`, or dropping the `env=` argument, both
    of which leave every child_env test above green while the key ships to the
    child (the first) or every STEALTHFOX_* option silently stops working (the
    second).

    ⛔ It used to run through `runner.drive`, behind the `aihawk do` subcommand
    removed on 2026-09-03. `drive` was only ever a Link opened and closed around
    one task, so the guarantee never belonged to it: it belongs to `Link`, which
    is what the interface uses, and that is where it is asserted now.
    """
    monkeypatch.setenv(KEY_NAME, KEY)
    captured = {}

    @contextlib.asynccontextmanager
    async def fake_stdio_client(params):
        captured["params"] = params
        yield ("read", "write")

    # Patched in `link`, not in `runner`: spawning lives there so that one place
    # knows the command, the arguments and the child environment. A test that
    # reached into `runner` for it would be asserting against a module that does
    # not make the decision.
    monkeypatch.setattr(link_mod, "stdio_client", fake_stdio_client)
    monkeypatch.setattr(link_mod, "ClientSession", _FakeSession)

    link = await link_mod.Link({"proxy": "http://h:1", "seed": 5}, key=KEY).open()
    try:
        params = captured["params"]
        assert params.command == sys.executable
        assert params.args == ["-m", "aihawk"]

        child = params.env
        assert child is not None, "an explicit environment is what carries the options"
        assert KEY_NAME not in child
        assert values_carrying(child, KEY) == []
        assert child["STEALTHFOX_PROXY"] == "http://h:1"
        assert child["STEALTHFOX_SEED"] == "5"
        assert os.environ[KEY_NAME] == KEY, "the parent keeps its own key"
    finally:
        await link.close()


async def test_the_child_never_gets_the_key_even_when_the_parent_holds_it(monkeypatch):
    """The other half, at the boundary that still exists.

    Known-bad: passing the key into the child to let the server call the model
    itself, which would make every assertion above pointless while the interface
    still answered correctly.
    """
    monkeypatch.setenv(KEY_NAME, KEY)
    seen = {}

    @contextlib.asynccontextmanager
    async def fake_stdio_client(params):
        seen["env"] = params.env
        yield ("read", "write")

    monkeypatch.setattr(link_mod, "stdio_client", fake_stdio_client)
    monkeypatch.setattr(link_mod, "ClientSession", _FakeSession)

    link = await link_mod.Link({}, key=KEY).open()
    try:
        assert values_carrying(seen["env"], KEY) == [], "the child must not have it"
    finally:
        await link.close()


def test_the_parent_client_is_the_one_that_gets_the_key(monkeypatch):
    """And it has to reach SOMETHING, or the interface has no model.

    The pairing matters: a version that scrubs the key everywhere passes the two
    tests above and cannot talk to OpenRouter at all. This drives the real
    command, because `cli.ui` is what builds the client now.
    """
    from click.testing import CliRunner

    import aihawk.cli as climod

    seen = {}
    monkeypatch.setenv(KEY_NAME, KEY)
    monkeypatch.setattr(llm_mod, "make_client",
                        lambda key: seen.setdefault("client", {"api_key": key}))

    class _Stop(Exception):
        pass

    def stop(*a, **k):
        raise _Stop

    monkeypatch.setattr(link_mod, "Link", stop)
    CliRunner().invoke(climod.main, ["ui"])

    assert seen.get("client") == {"api_key": KEY}, (
        "the parent client never got the key, so nothing can call the model")
