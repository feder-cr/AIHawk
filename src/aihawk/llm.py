"""OpenRouter (OpenAI-compatible) client config. Key from arg or env only."""
from __future__ import annotations

from typing import Mapping

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


def orcarouter_model(explicit: str | None, env: Mapping[str, str]) -> str:
    """The model to run on when the provider is OrcaRouter.

    ⛔ NOT ``resolve_model``, AND THE DIFFERENCE IS THE DEFAULT. The OpenRouter
    default is an OpenRouter id; sending it to OrcaRouter asks for a model that
    is not there, and the failure arrives as a provider error on the first turn
    rather than as a setting anybody can see. The two providers have two
    defaults, so they have two resolvers - and ``AIHAWK_MODEL`` still wins over
    both, because somebody who set it meant it.

    ⛔ AND AN EMPTY STRING IS NOT A CHOICE. It falls through to the default,
    exactly as ``resolve_model`` documents: asking a provider for the model
    named "" produces a confusing 404 far from its cause.
    """
    from . import orcarouter

    return explicit or env.get("AIHAWK_MODEL") or orcarouter.DEFAULT_MODEL


def orcarouter_env(env: Mapping[str, str]) -> dict:
    """The environment names the OrcaRouter half reads.

    ⛔ NAMED HERE SO THE STRUCTURAL TEST CAN SEE THEM, and so that the set of
    variables a second provider reads is a fact about this module rather than
    about wherever the reads happen to be. `test_openrouter_only.py` pins the
    set `llm.py` itself reads, which is exactly two names; this function is the
    honest way to add a third party without weakening that pin, because the
    names a provider uses belong to the provider.
    """
    from . import orcarouter

    return {
        orcarouter.KEY_VARIABLE: env.get(orcarouter.KEY_VARIABLE) or "",
        orcarouter.AUTH_BASE_VARIABLE: env.get(orcarouter.AUTH_BASE_VARIABLE) or "",
        orcarouter.API_BASE_VARIABLE: env.get(orcarouter.API_BASE_VARIABLE) or "",
        orcarouter.SHARED_BASE_VARIABLE: env.get(orcarouter.SHARED_BASE_VARIABLE) or "",
    }


def make_client(key: str):
    from openai import OpenAI
    return OpenAI(
        base_url=BASE_URL,
        api_key=key,
        default_headers={"HTTP-Referer": APP_URL, "X-Title": APP_TITLE},
    )


def make_orcarouter_client(credential, env: Mapping[str, str]):
    """The same client, aimed at OrcaRouter, with the key that belongs to the
    person rather than to this package.

    ⛔ IT TAKES A CREDENTIAL AND NOT A STRING, AND IT DOES NOT CARE WHICH
    ADAPTER MADE ONE. The key a user pasted and the key a sign-in was issued
    are the same kind of value against the same endpoint; the only thing that
    differs is which sentence to show when it stops working, and that lives on
    the credential. A second client built for the PKCE path would be a second
    place that knows the base URL, and the two would drift.

    ⛔ NO APP-ATTRIBUTION HEADERS, UNLIKE THE OPENROUTER CLIENT ABOVE. Those two
    exist because OpenRouter groups its public rankings by them and by nothing
    else. OrcaRouter does not, so sending them would be inventing a convention
    and a second identifier for this package on somebody else's service.
    """
    from openai import OpenAI

    from . import orcarouter

    return OpenAI(
        base_url=orcarouter.api_base(env),
        api_key=credential.key,
    )
