"""OpenRouter (OpenAI-compatible) client config. Key from arg or env only.

⛔ ORCAROUTER'S BASE URL IS NOT WRITTEN HERE, AND THAT IS THE ONE STRUCTURAL
RULE THIS FILE KEEPS. A second provider's host in this module is a second
provider the module can be asked for, and the resolution order, the key names
and the origin policy for OrcaRouter all live in `aihawk.orcarouter`, where
they are tested against the real thing. What is here is the two functions the
interface calls, and each one delegates: `orcarouter_client` builds a client
from a base URL the other module owns, and `orcarouter_env` asks the other
module what the environment holds. Written out here instead, the two would be
free to disagree - and the disagreement would be about which company the key
is sent to.
"""
from __future__ import annotations

from typing import Mapping

from . import orcarouter

BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "z-ai/glm-5.3-flash"

#: App attribution for the public rankings at https://openrouter.ai/apps.
#: OpenRouter groups usage by these two headers and by nothing else: without
#: them every request is anonymous traffic on the key, so the app appears
#: nowhere however much it is used. They are constants rather than settings
#: because they name THIS package, not the person running it.
APP_URL = "https://github.com/feder-cr/aihawk_mcp_server"
APP_TITLE = "AIHawk"


def resolve_key(explicit: str | None, env: Mapping[str, str]) -> str:
    key = explicit or env.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError(
            "no OpenRouter key: pass --openrouter-key or set OPENROUTER_API_KEY"
        )
    return key


def resolve_model(explicit: str | None, env: Mapping[str, str]) -> str:
    return explicit or env.get("AIHAWK_MODEL") or DEFAULT_MODEL


def make_client(key: str):
    from openai import OpenAI
    return OpenAI(
        base_url=BASE_URL,
        api_key=key,
        default_headers={"HTTP-Referer": APP_URL, "X-Title": APP_TITLE},
    )


def orcarouter_client(key: str):
    """The same client shape, aimed at OrcaRouter's inference origin.

    ⛔ THE SAME SHAPE ON PURPOSE. OrcaRouter is an OpenAI-compatible gateway,
    so the agent loop, the tool definitions and the streaming path are
    unchanged; what differs is the base URL and the fact that the key came
    from one of two adapters. `orcarouter.origins` is the only thing that
    answers where that is, so the host is not written twice.

    No app-attribution headers: those two are OpenRouter's ranking mechanism
    and mean nothing to another gateway, and sending another company's
    attribution fields to OrcaRouter would be a claim about who is calling.
    """
    from openai import OpenAI
    return OpenAI(base_url=orcarouter.origins()[1], api_key=key)


def orcarouter_env(env: Mapping[str, str] | None = None) -> str:
    """The OrcaRouter key in this environment, or empty.

    Here so the interface has one place to ask, and in `orcarouter` so the
    answer is the one the rest of the OrcaRouter code already uses.
    """
    return orcarouter.key_from_environment(env)
