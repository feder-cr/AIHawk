import pytest
from aihawk.llm import DEFAULT_MODEL, resolve_key, resolve_model


def test_key_arg_wins_then_env_then_error():
    assert resolve_key("k1", {"OPENROUTER_API_KEY": "k2"}) == "k1"
    assert resolve_key(None, {"OPENROUTER_API_KEY": "k2"}) == "k2"
    with pytest.raises(RuntimeError):
        resolve_key(None, {})


def test_model_arg_env_default():
    assert resolve_model("m1", {"AIHAWK_MODEL": "m2"}) == "m1"
    assert resolve_model(None, {"AIHAWK_MODEL": "m2"}) == "m2"
    # Against the constant, never a copy of its value: a literal here drifts
    # from the exported default the day it is changed, and then the suite pins
    # a model nobody ships.
    assert resolve_model(None, {}) == DEFAULT_MODEL
