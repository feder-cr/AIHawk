"""The command line as a person meets it.

No browser and no model are involved: `Link` is replaced by a recorder that
stops the command the moment it would connect, so every test asserts what the
CLI decided and handed over, not what the browser did.

The theme of this file is the API key. `aihawk` takes an OpenRouter key and
nothing else, and a key that reaches the terminal is a key in a scrollback
buffer, a CI log and a screen recording. FAKE_KEY below carries the marker
CANARY on purpose so any echo of it, whole or truncated after the prefix, is
recognisable; test_the_key_detector_is_not_vacuous proves the detector can
actually see a leak instead of always printing PASS.

⛔ THIS FILE USED TO DRIVE `aihawk do`, WHICH NO LONGER EXISTS. The subcommand
was removed on 2026-09-03: one way in, and it is `ui`. Most of what was here
tested the option surface and the key handling, and both are still real, so
those tests moved onto `ui` rather than being deleted with the command. Four
guarantees genuinely died with it and are recorded here so nobody hunts for
them later:

  * "no key anywhere exits 1 and names both ways to supply one" - dead with
    `do`, reborn with 0.4.0: the literal-command placeholder was removed, so
    `ui` now refuses without a key too, and the refusal must also point at
    the invisible_playwright library as the model-free way to drive the
    engine (tested below);
  * "the TASK argument is required", "the task reaches drive verbatim" and "the
    result is printed verbatim with one trailing newline" - `ui` takes no task
    and prints no result.
"""
from __future__ import annotations

import traceback

import click
import pytest
from click.testing import CliRunner

import aihawk.cli as climod
import aihawk.link as link_mod
from aihawk.llm import BASE_URL, DEFAULT_MODEL
from aihawk.runner import child_env

# A key shaped like a real OpenRouter key, with a marker in the middle so that a
# partial echo ("sk-or-v1-CANARY...") trips the detector too.
FAKE_KEY = "sk-or-v1-CANARY-9f3b2a7c-do-not-echo"
KEY_MARKER = "CANARY"
DECOY_ENV_KEY = "sk-or-v1-CANARY-env-decoy-must-lose"

# Every option `aihawk ui` declares itself. --help is added by click at parse
# time and is not one of ours, so it is checked against the rendered help only.
DECLARED_OPTIONS = {
    "--openrouter-key",
    "--model",
    "--proxy",
    "--seed",
    "--headed",
    "--binary",
    "--profile-dir",
    "--host",
    "--port",
}


def key_leaked(text: str) -> bool:
    """True if a recognisable piece of FAKE_KEY appears in text."""
    return FAKE_KEY in text or KEY_MARKER in text


@pytest.fixture(autouse=True)
def clean_provider_env(monkeypatch):
    """No provider variable may reach a test from the developer's own shell.

    Known-bad this guards: a machine that happens to export OPENROUTER_API_KEY
    would turn the "no key anywhere" test green while the CLI was broken.
    """
    for name in ("OPENROUTER_API_KEY", "AIHAWK_MODEL", "OPENAI_API_KEY",
                 "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


class _Stop(Exception):
    """Raised by the recorder so the command stops before it serves anything."""


class LinkRecorder:
    """Stands in for `Link`: records how it was constructed, then stops.

    `ui` decides everything this file is about - which key, which model, which
    browser options - and then hands them to `Link`. Recording that hand-over is
    the last point where the decisions are visible and the first point where a
    real browser would be launched, so it is where the command is stopped.
    """

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, opts=None, *, key=None):
        self.calls.append({"opts": dict(opts or {}), "key": key})
        raise _Stop

    @property
    def call(self) -> dict:
        assert len(self.calls) == 1, f"expected one Link, got {len(self.calls)}"
        return self.calls[0]


@pytest.fixture
def link(monkeypatch):
    rec = LinkRecorder()
    monkeypatch.setattr(link_mod, "Link", rec)
    return rec


def run(*args, **kwargs):
    return CliRunner().invoke(climod.main, list(args), **kwargs)


def stopped_at_link(result) -> bool:
    """The command got as far as connecting, which is as far as we let it."""
    return isinstance(result.exception, _Stop)


# --------------------------------------------------------------------------
# the key: where it comes from
# --------------------------------------------------------------------------

def test_explicit_key_wins_and_the_environment_is_not_consulted(link, monkeypatch):
    """A flag beats a variable. The decoy in the environment must lose, and it
    is a DIFFERENT string so "the right one was used" is provable rather than
    inferred from both being present."""
    monkeypatch.setenv("OPENROUTER_API_KEY", DECOY_ENV_KEY)

    result = run("ui", "--openrouter-key", FAKE_KEY)

    assert stopped_at_link(result)
    assert link.call["key"] == FAKE_KEY
    assert link.call["key"] != DECOY_ENV_KEY


def test_key_is_taken_from_the_environment_when_the_flag_is_absent(link, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)

    result = run("ui")

    assert stopped_at_link(result)
    assert link.call["key"] == FAKE_KEY


def test_no_key_anywhere_is_refused_and_points_at_the_library(link):
    """An agent is a model with a browser; keyless there is nothing to serve.

    The refusal must name both ways to supply a key AND the model-free
    alternative, because "use the library" is the answer this error exists
    to teach.
    """
    result = run("ui")

    assert result.exit_code != 0, "keyless ui started: %r" % result.output
    assert link.calls == [], "the browser was launched before the refusal"
    assert "--openrouter-key" in result.output
    assert "OPENROUTER_API_KEY" in result.output
    assert "invisible_playwright" in result.output, (
        "the refusal does not point at the library: %r" % result.output)


def test_an_openai_key_in_the_environment_is_not_accepted(link, monkeypatch):
    """OPENAI_API_KEY is not OPENROUTER_API_KEY, and treating it as one would
    send somebody's OpenAI credential to a different company's endpoint.

    With no OpenRouter key anywhere, `ui` must refuse: what must NOT happen
    is that it starts with a model, holding the OpenAI key.
    """
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)

    result = run("ui")

    assert result.exit_code != 0, (
        "an OPENAI_API_KEY was accepted as an OpenRouter key: %r"
        % result.output)
    assert link.calls == [], "the browser was launched despite the refusal"


def test_the_command_offers_no_second_provider():
    """One provider, and the CLI must not imply otherwise.

    A flag named for another vendor would be a promise this package cannot keep:
    the loop talks to OpenRouter's endpoint and nothing else.
    """
    rendered = run("ui", "--help").output
    for foreign in ("--openai", "--anthropic", "--api-base", "--base-url"):
        assert foreign not in rendered, "the CLI offers %s" % foreign


def test_the_cli_does_not_put_the_key_into_its_own_environment(link, monkeypatch):
    """Resolving the key must not export it.

    Known-bad: a resolve step that does `os.environ.setdefault(...)` so the
    child inherits it "conveniently" - which is exactly what child_env then has
    to undo, and the two would fight silently.
    """
    import os

    result = run("ui", "--openrouter-key", FAKE_KEY)

    assert stopped_at_link(result)
    assert not any(key_leaked(v) for v in os.environ.values()), (
        "the CLI wrote the key into its own environment")


# --------------------------------------------------------------------------
# the options
# --------------------------------------------------------------------------

def test_every_option_reaches_the_link_with_the_right_name_and_type(link):
    """Each flag arrives under the name the rest of the code reads, and typed.

    `--seed` is the one worth typing: click is told `type=int`, and a string
    "4242" would travel all the way to the engine and change nothing there,
    because the value it compares against is a number.
    """
    result = run(
        "ui",
        "--openrouter-key", FAKE_KEY,
        "--proxy", "socks5://proxy.example.com:1080",
        "--seed", "4242",
        "--headed",
        "--binary", "C:/x/firefox.exe",
        "--profile-dir", "C:/profiles/one",
    )

    assert stopped_at_link(result)
    opts = link.call["opts"]
    assert opts["proxy"] == "socks5://proxy.example.com:1080"
    assert opts["seed"] == 4242 and isinstance(opts["seed"], int)
    assert opts["headed"] is True
    assert opts["binary"] == "C:/x/firefox.exe"
    assert opts["profile_dir"] == "C:/profiles/one"


def test_defaults_are_none_and_headless(link, monkeypatch):
    """With nothing passed but the key, nothing else is invented.

    ⛔ `--proxy` in particular must default to None and not to "": an empty
    string is a value, and STEALTHFOX_PROXY set to it is not the same as no
    proxy at all. (The key is supplied because since 0.4.0 a keyless `ui`
    refuses before it ever reaches the Link.)
    """
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)

    result = run("ui")

    assert stopped_at_link(result)
    opts = link.call["opts"]
    assert opts["proxy"] is None
    assert opts["seed"] is None
    assert opts["headed"] is False
    assert opts["binary"] is None
    assert opts["profile_dir"] is None
    assert link.call["key"] == FAKE_KEY


def test_the_model_default_is_named_and_used(link, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)

    result = run("ui")

    assert stopped_at_link(result)
    assert DEFAULT_MODEL in result.output
    assert BASE_URL in result.output


def test_the_option_names_are_the_ones_the_runner_reads(link):
    """Cross-module: the dict the CLI builds is fed to the real child_env.

    Two modules agreeing on a spelling is not something either can check alone.
    `child_env` reads opts by key with `.get()`, so a renamed key is not an
    error anywhere - the option simply stops having an effect.
    """
    result = run(
        "ui",
        "--openrouter-key", FAKE_KEY,
        "--proxy", "http://user:pass@proxy.example.com:8080",
        "--seed", "7",
        "--headed",
        "--binary", "C:/x/firefox.exe",
        "--profile-dir", "C:/profiles/two",
    )

    assert stopped_at_link(result)
    env = child_env(link.call["opts"], {"OPENROUTER_API_KEY": FAKE_KEY})
    assert env["STEALTHFOX_PROXY"] == "http://user:pass@proxy.example.com:8080"
    assert env["STEALTHFOX_SEED"] == "7"
    assert env["STEALTHFOX_HEADLESS"] == "0"
    assert env["STEALTHFOX_BINARY"] == "C:/x/firefox.exe"
    assert env["STEALTHFOX_PROFILE_DIR"] == "C:/profiles/two"


def test_without_headed_the_child_is_left_headless(link, monkeypatch):
    """The variable is written only to turn headless OFF, so its ABSENCE is the
    headless case. Writing "1" would be equally correct and is not what the
    engine reads."""
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)

    result = run("ui")

    assert stopped_at_link(result)
    assert "STEALTHFOX_HEADLESS" not in child_env(link.call["opts"], {})


def test_the_host_and_port_have_loopback_defaults(link):
    """The interface has no authentication, so the default must not expose it."""
    rendered = run("ui", "--help").output
    assert "127.0.0.1" in rendered
    assert "8765" in rendered


def test_a_non_numeric_seed_is_a_usage_error(link):
    """Click rejects it before anything runs: exit 2, and no Link at all."""
    result = run("ui", "--openrouter-key", FAKE_KEY, "--seed", "abc")

    assert result.exit_code == 2, result.output
    assert link.calls == [], "the command connected despite a bad option"


def test_an_unknown_option_is_a_usage_error(link):
    result = run("ui", "--openrouter-key", FAKE_KEY, "--nope")

    assert result.exit_code == 2, result.output
    assert link.calls == []


def test_the_link_is_opened_exactly_once(link):
    """One invocation, one browser. A retry loop around the connection would
    launch two and leave one behind."""
    run("ui", "--openrouter-key", FAKE_KEY)

    assert len(link.calls) == 1


# --------------------------------------------------------------------------
# help
# --------------------------------------------------------------------------

def test_group_help_works_and_names_openrouter():
    result = run("--help")

    assert result.exit_code == 0, result.output
    assert "OpenRouter" in result.output


def test_ui_help_names_openrouter_and_the_environment_variables():
    """The help has to say where a key can come from other than the flag."""
    result = run("ui", "--help")

    assert result.exit_code == 0, result.output
    for wanted in ("OPENROUTER_API_KEY", "AIHAWK_MODEL"):
        assert wanted in result.output, "the help never names %s" % wanted
    for option in DECLARED_OPTIONS:
        assert option in result.output, "the help never names %s" % option


def test_bare_invocation_shows_the_ui_command():
    """`aihawk` with no arguments lists what it can do rather than failing."""
    result = run()

    assert "ui" in result.output


# --------------------------------------------------------------------------
# the key must never be echoed - the point of this file
# --------------------------------------------------------------------------

def test_the_key_is_never_echoed_on_any_path(monkeypatch, link):
    """Success, failure, usage error, crash: none of them may print the key.

    The crash path is the one that matters. An exception carrying the key in
    its message, or a traceback with the call arguments in a frame, puts it in
    a log that outlives the terminal.
    """
    outputs = {}

    outputs["stopped_at_link"] = run("ui", "--openrouter-key", FAKE_KEY).output
    outputs["ui_help"] = run("ui", "--help").output
    outputs["unknown_option"] = run(
        "ui", "--openrouter-key", FAKE_KEY, "--nope").output

    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    outputs["from_env"] = run("ui").output
    outputs["help_with_key_in_env"] = run("ui", "--help").output
    monkeypatch.delenv("OPENROUTER_API_KEY")

    def explode(*a, **k):
        raise RuntimeError("the browser did not start")

    monkeypatch.setattr(link_mod, "Link", explode)
    crashed = run("ui", "--openrouter-key", FAKE_KEY)
    outputs["crash"] = crashed.output
    if crashed.exception is not None:
        outputs["traceback"] = "".join(
            traceback.format_exception(
                type(crashed.exception), crashed.exception,
                crashed.exception.__traceback__))

    leaked = {name: text for name, text in outputs.items() if key_leaked(text)}
    assert not leaked, "the key reached the output on: %s" % sorted(leaked)


def test_the_key_detector_is_not_vacuous(monkeypatch, link):
    """The test above is worth nothing if key_leaked can never fire.

    Known-bad on purpose: a command that echoes the key it was given. If this
    does not catch it, the assertion above is decoration.
    """
    assert key_leaked("prefix " + FAKE_KEY + " suffix")
    assert key_leaked("sk-or-v1-CANARY")
    assert not key_leaked("nothing to see here")

    @climod.main.command()
    @click.option("--openrouter-key", default=None)
    def leaky(openrouter_key):  # pragma: no cover - registered then removed
        click.echo("key is %s" % openrouter_key)

    try:
        out = run("leaky", "--openrouter-key", FAKE_KEY).output
        assert key_leaked(out), "the detector cannot see a real leak"
    finally:
        climod.main.commands.pop("leaky", None)


def test_the_key_option_cannot_echo_its_own_value_in_a_usage_error():
    """Click prints the offending value for some errors. The key option must
    never be the one that trips it, so it is a plain string with no type,
    no choice list and no callback that could reject and quote it."""
    param = next(p for p in climod.main.commands["ui"].params
                 if "--openrouter-key" in p.opts)
    assert param.type.name == "text", (
        "a typed --openrouter-key can have its value quoted back by click")
