"""How the browser server is started, and what the child is allowed to know.

`child_env` is the security-relevant half and it lives here alone: the OpenRouter
key is removed from the environment the engine is started with, and the browser
options are the only things added. The child drives a browser; it has no use for
a model key, and the cheapest way to keep a secret out of a process is not to
hand it over.

Spawning is `Link`'s. This module used to build its own StdioServerParameters as
well, which meant two places knew the command, the arguments and the environment
of the child - and a change to how the server is launched had to be made twice
or be wrong once.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional


#: The one name the key is expected under. Compared case-insensitively, because
#: on POSIX `openrouter_api_key` is a different variable to the shell and the
#: same secret to anyone reading the process environment.
KEY_VARIABLE = "OPENROUTER_API_KEY"


def without_key(base_env: Mapping[str, str], *, key: Optional[str] = None) -> dict:
    """`base_env` with the model key gone: by name, and by every other name
    carrying the same value.

    ⛔ ONE PLACE KNOWS WHAT COUNTS AS THE KEY, because there are now two callers
    and they are the same question asked from opposite ends. `child_env` builds
    the environment for a process about to start; `forget_key` strips the
    environment of a process already running. Written twice, one of them would
    have learned about a new alias and the other would not.

    The two halves of the removal are not one guarantee:

      * a lowercase `openrouter_api_key`, which survives on any case-sensitive
        platform, and this product runs on Linux;
      * the same string kept under a SECOND name. `OPENAI_API_KEY` holding an
        OpenRouter key is normal practice here, because the client is
        OpenAI-compatible and talks to OpenRouter through it.

    `key` is the resolved key when the caller has one: passed on the command
    line it never appears in the environment at all, so a copy of it under
    another name could not be found by reading the environment alone.
    """
    secrets = {value for name, value in base_env.items()
               if name.upper() == KEY_VARIABLE and value}
    if key:
        secrets.add(key)

    # An empty secret would match every empty variable, which is how a guard
    # like this turns into "delete most of the environment".
    secrets.discard("")

    return {name: value for name, value in base_env.items()
            if name.upper() != KEY_VARIABLE and value not in secrets}


def forget_key(env) -> list:
    """Take the model key out of a LIVE environment, this process's own.
    Answers the names it removed, so a caller can say so rather than doing it
    silently.

    ⛔ THIS EXISTS BECAUSE `child_env` WAS UNDONE HALF A SECOND AFTER IT RAN, by
    the child itself. Measured 2026-09-16 against the published 0.68.2: the
    interface strips the key from the environment it hands over, by name and by
    value, and every one of the twenty-two cases in `test_key_isolation.py`
    passes. Then the child - which is `python -m invisible_playwright_mcp`, the same click group -
    reads `.env` from the directory it inherited, finds `OPENROUTER_API_KEY` in
    it, and puts it straight back. The interface said so out loud and nobody was
    reading: `env      .env: OPENROUTER_API_KEY` is printed twice at startup,
    once by each process, and that line names only what was APPLIED, which is to
    say only what was not already there.

    What it costs is the guarantee the stripping was written for, because
    `invisible_playwright._session.build_env` seeds the Firefox launch from this
    process's own environment. Proven by calling it: the key arrives in the
    engine's environment.

    ⛔ AND IT IS NOT A GUARD ON "WAS I SPAWNED BY THE INTERFACE". The browser
    server has no use for a model key whoever started it, so somebody running
    `uvx invisible-playwright-mcp` in a shell that exports one, or beside a `.env` that holds one,
    has exactly the same exposure and was never told. Reading the environment
    covers the file, the export and any alias at once, which a guard on the
    file alone would not.
    """
    keep = without_key(env)
    gone = [name for name in list(env) if name not in keep]
    for name in gone:
        del env[name]
    return gone


def child_env(opts: Mapping[str, Any], base_env: Mapping[str, str],
              *, key: Optional[str] = None) -> dict:
    """The environment the browser server is started with.

    The removal is the point. Everything else is options travelling under the
    names the engine reads, and an absent option adds no variable at all rather
    than an empty one, because an empty STEALTHFOX_PROXY is not the same as no
    proxy.

    ⛔ THE REMOVAL ITSELF IS `without_key`, ABOVE, AND THE ACCOUNT OF WHY IT
    TAKES TWO FORMS LIVES THERE. It was written out here while this was the
    only caller; there are two now, and a rule kept in the docstring of one of
    them is a rule the other never learns.

    Neither form is theoretical: the leak reaches the browser itself, not just
    the MCP server. `invisible_playwright._session.build_env` starts from the
    server process's own environment and hands that to the Firefox launch, so
    whatever survives is inherited by the engine.

    ⛔ AND THIS ALONE IS NOT ENOUGH, which is what 0.68.2 shipped. Handing over
    a clean environment does not keep the child clean: it reads `.env` on its
    own way up and takes the key back. `forget_key` is the other half, and the
    server calls it for itself.
    """
    env = without_key(base_env, key=key)

    if opts.get("proxy"):
        env["STEALTHFOX_PROXY"] = str(opts["proxy"])
    if opts.get("seed") is not None:
        env["STEALTHFOX_SEED"] = str(opts["seed"])
    if opts.get("headed"):
        env["STEALTHFOX_HEADLESS"] = "0"
    if opts.get("binary"):
        env["STEALTHFOX_BINARY"] = str(opts["binary"])
    if opts.get("profile_dir"):
        env["STEALTHFOX_PROFILE_DIR"] = str(opts["profile_dir"])
    if opts.get("session_id"):
        # ⛔ NOT A STEALTHFOX_* NAME, ON PURPOSE. Those are what the ENGINE
        # reads; this is which saved file the SERVER itself persists its two
        # browsers to, and the server has no session concept beyond reading
        # this one value once, at import. The interface sets it to spawn one
        # server per conversation; a client that never sets it - `uvx invisible-playwright-mcp`
        # in Claude Desktop - lands on the one name every caller landed on
        # before this had a name at all.
        env["AIHAWK_SESSION_ID"] = str(opts["session_id"])
    return env
