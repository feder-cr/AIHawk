"""aihawk CLI: serve the page that drives a stealth browser with an LLM."""
from __future__ import annotations

import asyncio
import os
import sys

import click

from .llm import BASE_URL, resolve_key, resolve_model

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

    The MCP server fetches it on its own the first time it starts, but from
    here that moment used to be invisible: this command printed "browser ready"
    while nothing had been downloaded, and the first message then sat for a
    minute with nothing moving, or died on a slow line with an error that named
    a timeout. So the download happens in front of the person, on one line that
    follows it, before the port opens. A given --binary skips it here the way it
    skips the download everywhere else; the server still checks that binary
    against the seal when it launches.
    """
    if binary:
        echo("browser  %s" % binary)
        return
    if fetch is None:
        from invisible_core import ensure_binary
        fetch = ensure_binary
    line = _EngineLine(echo, tty=sys.stdout.isatty() if tty is None else tty)
    fetch(progress=line.progress, status=line.status)
    line.done()


@click.group()
def main() -> None:
    """Drive a stealth browser with an LLM.

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
    """
    applied = load_env_file()
    if applied:
        # Names, never values: this line exists so a reader knows the file was
        # found, and printing what was in it would put the key on the terminal.
        click.echo("env      %s: %s" % (ENV_FILE, ", ".join(sorted(applied))))


@main.command()
@click.option("--openrouter-key", default=None,
              help="OpenRouter API key (or env OPENROUTER_API_KEY). Required: "
                   "the interface does not start without a model.")
@click.option("--model", default=None, help="Model id (or env AIHAWK_MODEL).")
@click.option("--host", default="127.0.0.1", show_default=True,
              help="Interface bind address. Leave it on loopback unless you mean it.")
@click.option("--port", type=int, default=8765, show_default=True)
@browser_options
def ui(openrouter_key, model, host, port, proxy, seed, headed, binary, profile_dir):
    """Serve the two-pane interface: conversation left, live browser right.

    Requires an OpenRouter key: an agent is a model with a browser, and
    without the model there is nothing honest to serve. Driving the browser
    by hand, no model and nothing spent, is the invisible_playwright
    library's job - same engine, Playwright's whole API.
    """
    from .brain import OpenRouterBrain
    from .link import Link
    from .llm import make_client
    from .web import ChatService, build_app

    key = openrouter_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise click.ClickException(
            "no OpenRouter key. Pass --openrouter-key or set "
            "OPENROUTER_API_KEY. To drive the browser without a model, use "
            "the invisible_playwright library directly: same engine, "
            "Playwright's whole API.")
    mdl = resolve_model(model, os.environ)
    brain = OpenRouterBrain(make_client(key), mdl)
    label = mdl
    click.echo("model    %s via %s" % (mdl, BASE_URL))

    opts = {"proxy": proxy, "seed": seed, "headed": headed,
            "binary": binary, "profile_dir": profile_dir}

    # Before the port opens and before the server is spawned: the download,
    # if there is one, happens here where it can be watched.
    engine_on_disk(binary)

    async def serve() -> None:
        import uvicorn

        link = await Link(opts, key=key).open()
        click.echo("server   connected, %d tools" % len(link.tools))
        click.echo("open     http://%s:%d" % (host, port))
        service = ChatService(link, brain, model_label=label)
        app = build_app(link, service)
        server = uvicorn.Server(uvicorn.Config(app, host=host, port=port,
                                               log_level="warning"))
        try:
            await server.serve()
        finally:
            await link.close()

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
