"""The OrcaRouter provider, against the real service, with the real key.

⛔ THESE ARE THE ONLY TESTS THAT LEAVE THE MACHINE, and they run through the
code this change adds rather than through a `curl` written beside it: the
catalogue goes through `orcarouter.fetch_catalog`, the account's models reach
the panel through `routes.refresh_models`, and the completion goes through the
client `llm.orcarouter_client` builds. A 200 from a separate command would
prove the endpoint answers; it would not prove the provider is wired to it.

Skipped when there is no key in the environment, so a checkout without one
still runs the suite. The key is read from the environment and never written
anywhere - not to a file, not to a failure message, not to a report.
"""

import asyncio
import os

import pytest

from aihawk import llm, orcarouter, provider, routes

KEY = os.environ.get("ORCAROUTER_API_KEY", "")

pytestmark = pytest.mark.skipif(
    not KEY, reason="no ORCAROUTER_API_KEY in the environment")


def test_the_live_catalogue_is_namespaced_and_non_empty():
    """The real `/v1/models`, parsed by the provider's own reader."""
    models = asyncio.run(orcarouter.fetch_catalog(KEY))
    assert models, "the live catalogue came back empty"
    for model in models:
        assert "/" in model.id, (
            "%r lost the vendor namespace the catalogue carries" % model.id)


def test_the_live_catalogue_can_be_narrowed_to_chat():
    """The `?capability=chat` filter, through `models_for`."""
    models = asyncio.run(orcarouter.fetch_catalog(KEY, capability="chat"))
    offered = orcarouter.models_for(models, "chat")
    assert offered, "no chat model survived the filter"
    assert all(m.id == m.id.strip() for m in offered)
    # And nothing that the catalogue declares as a non-text endpoint is in it.
    for model in offered:
        assert not (set(model.endpoints) & set(orcarouter.NON_CHAT_ENDPOINTS)), (
            "%s is a non-text model in the chat list" % model.id)


def test_the_live_models_reach_the_panel_through_the_provider_state():
    """Discovery, as the running server does it, and the model list it leaves."""
    state = provider.ProviderState()
    state.set_credential(orcarouter.Credential(KEY, method=orcarouter.BY_KEY))
    asyncio.run(routes.refresh_models(state))
    assert state.source == orcarouter.LIVE_SOURCE, (
        "discovery failed and fell back to the seed: %s" % state.catalog_error)
    assert state.models, "the live source left no models to choose from"
    offered = state.offered("chat")
    assert offered, "the live catalogue left nothing for the chat dropdown"
    assert all(m.id in [x.id for x in state.models] for m in offered)


def test_the_live_seed_is_a_subset_of_the_live_catalogue():
    """⛔ THE FALLBACK HAS TO BE VERIFIED, and this is the check that says so.

    The seed is what a person sees when discovery fails, so every id in it has
    to be one the service actually serves right now. If the catalogue ever
    drops one, this fails rather than the outage fallback quietly offering a
    model that answers 404.
    """
    live = {m.id for m in asyncio.run(orcarouter.fetch_catalog(KEY))}
    missing = [name for name in orcarouter.SEED_MODELS if name not in live]
    assert not missing, "the seed offers models the service does not: %s" % missing


def test_a_real_completion_through_the_client_the_provider_builds():
    """⛔ A REAL REQUEST, THROUGH `llm.orcarouter_client`, not a side `curl`.

    Walked over the catalogue until one answers, because a key carries its own
    model scope and the catalogue a key can read is not the set it can spend on.
    The assertion is that the client this change builds completes a turn against
    a model the same change discovered - which is the wiring, not the scope.
    """
    client = llm.orcarouter_client(KEY)
    models = asyncio.run(orcarouter.fetch_catalog(KEY))
    assert models, "no catalogue to choose a model from"
    order = sorted(models, key=lambda m: (m.id != orcarouter.DEFAULT_MODEL, m.id))
    answered, refused = [], []
    for model in order:
        try:
            answer = client.chat.completions.create(
                model=model.id,
                messages=[{"role": "user", "content": "Reply with the single word: ok"}],
                max_tokens=16,
            )
        except Exception as exc:
            refused.append("%s: %s" % (model.id, type(exc).__name__))
            continue
        answered.append((model.id, (answer.choices[0].message.content or "").strip()))
    assert answered, "the gateway answered nothing at all; refused: %s" % refused
    assert any(text for _, text in answered), (
        "every completion came back empty: %s" % answered)
