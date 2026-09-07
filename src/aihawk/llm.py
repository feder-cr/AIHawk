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
APP_URL = "https://github.com/feder-cr/AIHawk"
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
