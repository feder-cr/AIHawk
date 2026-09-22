"""aihawk CLI: serve the page that drives a stealth browser with an LLM."""
from __future__ import annotations

import asyncio
import os
import sys

import click

from . import orcarouter
from .llm import BASE_URL, orcarouter_env, resolve_key, resolve_model
from .runner import forget_key

#: The file read at startup, in the directory the command is run from.
#:
#: ⛔ CWD ONLY, not a search upwards. `find_dotenv` walks parent directories,
#: which means running the command from a subfolder can silently pick up
#: somebody else's file - a different key, a different browser - and nothing on
#: screen says which one was used. One predictable location is worth more than
#: the convenience.
ENV_FILE = ".env"


def load_env_file(directory=None) -> dict:
    """Read `.env` from `directory` (default: the current one) into the process.

    ⛔ IT NEVER OVERRIDES A VARIABLE THAT IS ALREADY SET, and that ordering is
    the whole design. A variable exported in the shell is something the user
    just did; a line in a file is something they did once, weeks ago. The recent
    decision wins, so the precedence a reader can rely on is:

        --flag  >  the environment  >  .env  >  the default

    Returns what it actually applied, so the caller can say so rather than
    leaving the user to guess whether the file was found at all.
    """
    from pathlib import Path

    path = Path(directory or Path.cwd()) / ENV_FILE
    if not path.is_file():
        return {}

    # dotenv rather than a hand-rolled parser: quoting, `export ` prefixes,
    # comments and multi-line values are all things a hand-rolled one gets
    # wrong on somebody else's machine, months later.
    from dotenv import dotenv_values

    applied = {}
    for name, value in dotenv_values(path).items():
        if value is None or name in os.environ:
            continue
        os.environ[name] = value
        applied[name] = value
    return applied


BROWSER_OPTIONS = [
    click.option("--proxy", default=None, help="Proxy URL for the stealth browser."),
    click.option("--seed", type=int, default=None, help="Deterministic fingerprint seed."),
    click.option("--headed", is_flag=True, help="Run the browser headed."),
    click.option("--binary", default=None, help="Path to a specific engine binary."),
    click.option("--profile-dir", default=None,
                 help="Persistent profile dir; logins survive across runs."),
]


def browser_options(fn):
    for opt in reversed(BROWSER_OPTIONS):
        fn = opt(fn)
    return fn


class _EngineLine:
    """One terminal line that follows the download, redrawn in place.

    On a terminal every whole percent is drawn; anywhere else (a log, a pipe)
    every tenth, because a carriage return in a file is not a redraw and a
    thousand of them is a wall of text.
    """

    def __init__(self, echo, tty: bool) -> None:
        self._echo = echo
        self._step = 1 if tty else 10
        self._drawn = None

    def _draw(self, text: str) -> None:
        self._echo("\rbrowser  %-40s" % text, nl=False)

    def progress(self, done: int, total: int) -> None:
        pct = int(done * 100 / total) if total else 0
        bucket = pct // self._step
        if bucket == self._drawn:
            return
        self._drawn = bucket
        self._draw("downloading %3d%%  %d MB" % (pct, done // (1 << 20)))

    def status(self, phase: str) -> None:
        if phase != "downloading":
            self._draw(phase)

    def done(self) -> None:
        self._draw("ready")
        self._echo("")


def engine_on_disk(binary, echo=click.echo, fetch=None, tty=None) -> None:
    """Have the browser on disk before anything is served.

    The servers this interface spawns would download it themselves, one per
    conversation, and from here that moment used to be invisible: this command
    printed "server connected" while nothing had been downloaded, and the
    first message then sat for a minute with nothing moving. So the download
    happens in front of the person, on one line that follows it, before the
    port opens; the spawned servers then find the cache. A given --binary
    skips it here the way it skips the download everywhere else; the server
    still checks that binary against the seal when it launches.
    """
    from .engine import FETCH_BY_HAND, Engine

    if binary:
        echo("browser  %s" % binary)
        return
    line = _EngineLine(echo, tty=sys.stdout.isatty() if tty is None else tty)
    engine = Engine(fetch=fetch, listener=line)
    if engine.run() is None:
        echo("")
        raise click.ClickException(
            "the engine download failed: %s. Run it again, or by hand: %s"
            % (engine.error, FETCH_BY_HAND))
    line.done()


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx) -> None:
    """Drive a stealth browser with an LLM.

    Without a subcommand this is the MCP server over stdio: `uvx aihawk` is
    what an assistant registers, `python -m aihawk` is what the interface
    spawns. `aihawk ui` is the interface, which brings a model.

    The model comes from OpenRouter and nowhere else: pass --openrouter-key or
    set OPENROUTER_API_KEY. Without one the interface refuses to start - an
    agent is a model with a browser, and there is no half of it to serve. To
    drive the browser by hand without a model, use the invisible_playwright
    library directly: same engine, Playwright's whole API.

    Said here rather than only in the subcommand because this is the first page
    anybody reads, and a key requirement discovered from an error message is a
    key requirement discovered too late.

    A `.env` in the directory you run from is read first, so the key and the
    browser path can live in a file instead of a shell profile. It never
    overrides something already in the environment.

    Serving as the MCP server, this process then drops the model key from its
    own environment whatever it came from, because a browser server has no use
    for one and the engine it launches inherits what this holds.
    """
    applied = load_env_file()
    serving = ctx.invoked_subcommand is None
    if serving:
        # ⛔ A BROWSER SERVER HAS NO USE FOR A MODEL KEY, AND WHATEVER THIS
        # PROCESS HOLDS THE ENGINE INHERITS. This is where 0.68.2 handed it
        # back: the interface strips the key from the environment it gives the
        # child, carefully and with twenty-two tests behind it, and then the
        # child runs this very function, finds the key in `.env`, and puts it
        # straight back. The line below printed it twice, once per process, and
        # that was the whole visible evidence.
        #
        # Read from the environment rather than filtered out of the file, so it
        # covers the same key arriving any other way - exported in the shell by
        # somebody running `uvx aihawk` by hand, or under an alias. The reason
        # is on `runner.forget_key`.
        #
        # The names are dropped from what gets REPORTED too: saying a file
        # applied something this process then threw away is a line that is not
        # true by the time anybody reads it.
        for name in forget_key(os.environ):
            applied.pop(name, None)
    if applied:
        # Names, never values: this line exists so a reader knows the file was
        # found, and printing what was in it would put the key on the terminal.
        # On stderr when serving, because stdout is then the protocol channel.
        click.echo("env      %s: %s" % (ENV_FILE, ", ".join(sorted(applied))),
                   err=serving)
    if serving:
        _serve()


def _serve() -> None:
    """The MCP server over stdio: the whole of `aihawk` with no subcommand.

    stdout is the protocol channel, so nothing is printed there. A person at a
    terminal gets one line on stderr saying what is waiting; a client gets the
    protocol and nothing else.
    """
    if sys.stdin.isatty():
        click.echo("aihawk: MCP server over stdio, waiting for a client. "
                   "For the interface: aihawk ui --openrouter-key ...", err=True)
    from .mcp.server import main as serve
    serve()


@main.command()
@click.option("--openrouter-key", default=None,
              help="OpenRouter API key (or env OPENROUTER_API_KEY). One of the "
                   "two providers: the interface does not start without a model.")
@click.option("--orcarouter-key", default=None,
              help="OrcaRouter API key (or env ORCAROUTER_API_KEY). The other "
                   "provider: an sk-orca-... key from the console.")
@click.option("--provider", default=None,
              help="Which provider this run uses: openrouter (the default), "
                   "orcarouter, or orcarouter-oauth.")
@click.option("--orcarouter-connect", is_flag=True,
              help="Sign in with an OrcaRouter account (OAuth 2.0 + PKCE) "
                   "instead of pasting a key.")
@click.option("--model", default=None, help="Model id (or env AIHAWK_MODEL).")
@click.option("--host", default="127.0.0.1", show_default=True,
              help="Interface bind address. Leave it on loopback unless you mean it.")
@click.option("--port", type=int, default=8765, show_default=True)
@browser_options
def ui(openrouter_key, orcarouter_key, provider, orcarouter_connect, model,
       host, port, proxy, seed, headed, binary, profile_dir):
    """Serve the two-pane interface: conversation left, live browser right.

    Requires a model: an agent is a model with a browser, and without the model
    there is nothing honest to serve. OpenRouter is the default and needs
    --openrouter-key or OPENROUTER_API_KEY. OrcaRouter is the other provider
    and has two ways in - paste an sk-orca-... key with --orcarouter-key, or
    sign in with --orcarouter-connect and a browser. Driving the browser by
    hand, no model and nothing spent, is the invisible_playwright library's
    job - same engine, Playwright's whole API.
    """
    from .agent import OpenRouterBrain
    from .chat import DEFAULT_CHAT_ID
    from .llm import make_client, orcarouter_client
    from .provider import ProviderState, load_credential
    from .routes import build_app, refresh_models
    from .sessions import Sessions

    # ⛔ THE RULE LIVES IN `llm.resolve_key`, AND UNTIL NOW THIS RE-IMPLEMENTED
    # IT. Both said the same thing - the flag beats the variable, an empty one
    # counts as absent, nothing at all is a refusal - which is exactly the
    # shape that goes wrong quietly: `resolve_key` carried a dozen assertions
    # pinning those edges and had no caller in the product, so the tested copy
    # and the running copy were different code. Either could have drifted
    # without a red test.
    #
    # What stays here is the PRESENTATION, which is genuinely the CLI's: a
    # ClickException prints one line and exits 1 where a RuntimeError dumps a
    # traceback, and the sentence names the library for somebody who wanted a
    # browser rather than an agent.
    #
    # ⛔ AND ORCAROUTER IS RESOLVED THROUGH ITS OWN MODULE, never by reading a
    # second variable name here. Which names count, what order they are read in
    # and which origin the result is spent against are `aihawk.orcarouter`'s
    # answers, and a copy of them in the CLI is a copy that can disagree.
    chosen = (provider or "").strip().lower()
    orcarouter_env_key = orcarouter_env(os.environ)
    # ⛔ AN EXPLICIT `--provider openrouter` IS A CHOICE, NOT A DEFAULT. Without
    # this the flag was read as "nobody said", so a shell that happens to export
    # ORCAROUTER_API_KEY turned a named OpenRouter run into an OrcaRouter one -
    # the key that got spent was not the one that was asked for.
    named_openrouter = chosen == "openrouter"
    wants_orcarouter = bool(orcarouter_connect or orcarouter_key or
                            chosen.startswith("orcarouter") or
                            (not named_openrouter and not openrouter_key and
                             orcarouter_env_key and
                             not os.environ.get("OPENROUTER_API_KEY")))
    if orcarouter_connect:
        chosen = "orcarouter-oauth"
    elif wants_orcarouter and not chosen.startswith("orcarouter"):
        chosen = "orcarouter"
    if not wants_orcarouter:
        try:
            key = resolve_key(openrouter_key, os.environ)
        except RuntimeError:
            raise click.ClickException(
                "no model key. Pass --openrouter-key or set "
                "OPENROUTER_API_KEY for OpenRouter, or pass --orcarouter-key "
                "or set ORCAROUTER_API_KEY for OrcaRouter - or sign in with "
                "--orcarouter-connect. To drive the browser without a model, "
                "use the invisible_playwright library directly: same engine, "
                "Playwright's whole API.")
    else:
        key = orcarouter_key or orcarouter_env_key
    mdl = resolve_model(model, os.environ)
    state = ProviderState()
    if wants_orcarouter:
        # ⛔ A FLAG THAT NAMES A PROVIDER AND A KEY THAT BELONGS TO ANOTHER IS
        # REFUSED, not quietly spent. Sending an OpenRouter key to OrcaRouter
        # (or the reverse) is a 401 whose message says nothing about the cause.
        if orcarouter_key and openrouter_key and orcarouter_key == openrouter_key:
            raise click.ClickException(
                "--orcarouter-key and --openrouter-key are the same value; "
                "they are two different providers.")
        if key:
            state.set_credential(orcarouter.Credential(
                key, method=orcarouter.BY_KEY, source="environment"))
        else:
            # ⛔ A CREDENTIAL FROM AN EARLIER RUN IS REUSED, NOT ASKED FOR AGAIN.
            # There is a cap of ten PKCE-issued keys per user per day, and a
            # client that signs in on every launch locks its own users out by
            # lunchtime - so the stored credential is read here, through the one
            # loader that also knows where it lives.
            state.set_credential(load_credential(os.environ))
        state.choose(chosen, model or os.environ.get("AIHAWK_MODEL") or None)
        # ONE client, a brain PER CONVERSATION, whichever provider it is: the
        # client is a connection and the brain is a transcript.
        client = orcarouter_client(key or "no-key-yet")
        mdl = state.model or orcarouter.DEFAULT_MODEL
        click.echo("model    %s via %s (%s)"
                   % (mdl, orcarouter.origins()[1],
                      "a sign-in, no key yet" if not key else "api key"))
    else:
        state.choose("openrouter", mdl)
        client = make_client(key)
        click.echo("model    %s via %s" % (mdl, BASE_URL))
    # After the key, so a refusal costs nobody a quarter-gigabyte download;
    # before the link, so the spawned servers find the engine on disk.
    engine_on_disk(binary)

    opts = {"proxy": proxy, "seed": seed, "headed": headed,
            "binary": binary, "profile_dir": profile_dir}

    async def serve() -> None:
        import uvicorn

        sessions = Sessions(
            opts, key,
            lambda: OpenRouterBrain(client, mdl, model_of=lambda: state.model),
            model_label=state.model_label() or mdl)
        # ⛔ THE DEFAULT CONVERSATION IS STARTED EAGERLY, EVERY OTHER ONE
        # LAZILY. Every conversation spawns its own server now, on first use -
        # `Sessions.get` - and the interface used to open ONE connection at
        # boot just to prove the server starts and to report its tool count.
        # Asking for `default` here reproduces exactly that boot experience:
        # it is the conversation almost every install actually opens first,
        # and its connection is real rather than a throwaway diagnostic one.
        default = await sessions.get(DEFAULT_CHAT_ID)
        click.echo("server   connected, %d tools" % len(default.link.tools))
        click.echo("open     http://%s:%d" % (host, port))
        if wants_orcarouter and not key:
            # ⛔ SAID OUT LOUD, BECAUSE THE COMMAND DID NOT DO WHAT IT WAS
            # ASKED. There is no credential yet, so the panel has to be opened
            # and the sign-in pressed; a run that starts quietly and fails at
            # the first message would look like a model that is broken.
            click.echo("connect  open the panel and press Connect with "
                       "OrcaRouter, or pass --orcarouter-key")
        await refresh_models(state)
        app = build_app(sessions, state)
        server = uvicorn.Server(uvicorn.Config(app, host=host, port=port,
                                               log_level="warning"))
        try:
            await server.serve()
        finally:
            await sessions.close_all()

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
