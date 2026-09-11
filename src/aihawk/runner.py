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


def child_env(opts: Mapping[str, Any], base_env: Mapping[str, str],
              *, key: Optional[str] = None) -> dict:
    """The environment the browser server is started with.

    The removal is the point. Everything else is options travelling under the
    names the engine reads, and an absent option adds no variable at all rather
    than an empty one, because an empty STEALTHFOX_PROXY is not the same as no
    proxy.

    ⛔ IT REMOVES BY VALUE AS WELL AS BY NAME, and the two are not the same
    guarantee. Popping one exact name left the secret reachable two ways, both
    ordinary rather than exotic:

      * a lowercase `openrouter_api_key`, which survives on any case-sensitive
        platform, and this product runs on Linux;
      * the same string kept under a SECOND name. `OPENAI_API_KEY` holding an
        OpenRouter key is normal practice here, because the client is
        OpenAI-compatible and talks to OpenRouter through it.

    Neither is theoretical: the leak reaches the browser itself, not just the
    MCP server. `invisible_playwright._session.build_env` starts from the
    server process's own environment and hands that to the Firefox launch, so
    whatever survives here is inherited by the browser.

    Both were recorded as strict xfails in `tests/test_key_isolation.py`, each
    naming what would close it. This is that, so those markers are gone.

    `key` is the resolved key when the caller has one - passed on the command
    line, it never appears in `base_env` at all, so a copy of it under another
    name could not be found by reading the environment alone.
    """
    secrets = {value for name, value in base_env.items()
               if name.upper() == KEY_VARIABLE and value}
    if key:
        secrets.add(key)

    # An empty secret would match every empty variable, which is how a guard
    # like this turns into "delete most of the environment".
    secrets.discard("")

    env = {name: value for name, value in base_env.items()
           if name.upper() != KEY_VARIABLE and value not in secrets}

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
        # server per conversation; a client that never sets it - `uvx aihawk`
        # in Claude Desktop - lands on the one name every caller landed on
        # before this had a name at all.
        env["AIHAWK_SESSION_ID"] = str(opts["session_id"])
    return env
