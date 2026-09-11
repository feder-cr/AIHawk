from aihawk.runner import child_env


def test_child_env_maps_options_and_omits_key():
    env = child_env(
        {"proxy": "http://u:p@h:8080", "seed": 42, "headed": True, "binary": "C:/ff.exe"},
        {"PATH": "/x", "OPENROUTER_API_KEY": "secret"},
    )
    assert env["STEALTHFOX_PROXY"] == "http://u:p@h:8080"
    assert env["STEALTHFOX_SEED"] == "42"
    assert env["STEALTHFOX_HEADLESS"] == "0"
    assert env["STEALTHFOX_BINARY"] == "C:/ff.exe"
    assert env["PATH"] == "/x"                      # unrelated base env preserved
    assert "OPENROUTER_API_KEY" not in env          # the key must NOT reach the child


def test_child_env_defaults_headless_and_omits_absent():
    env = child_env({}, {})
    assert "STEALTHFOX_HEADLESS" not in env       # default (headless) => don't set
    assert "STEALTHFOX_PROXY" not in env
    assert "STEALTHFOX_SEED" not in env
    assert "STEALTHFOX_PROFILE_DIR" not in env


def test_child_env_maps_profile_dir():
    env = child_env({"profile_dir": "C:/prof"}, {})
    assert env["STEALTHFOX_PROFILE_DIR"] == "C:/prof"


def test_child_env_maps_session_id_and_it_is_not_a_stealthfox_name():
    """⛔ THIS IS THE WHOLE MECHANISM BY WHICH TWO CONVERSATIONS BECOME TWO
    PROCESSES, one env var, read once by the child at import
    (`aihawk.mcp.server._SESSION_ID`). It is not `STEALTHFOX_*` on purpose:
    those are what the ENGINE reads, and this is which saved file the SERVER
    itself persists its two browsers to - a fact about the interface's own
    bookkeeping, not about stealth.

    Known-bad: name it `STEALTHFOX_SESSION_ID`, which nothing in `plan.py`
    would ever read, so the browser boots correctly and reopening a
    conversation never finds what it saved.
    """
    env = child_env({"session_id": "lavoro"}, {})
    assert env["AIHAWK_SESSION_ID"] == "lavoro"


def test_child_env_omits_session_id_when_absent():
    env = child_env({}, {})
    assert "AIHAWK_SESSION_ID" not in env
