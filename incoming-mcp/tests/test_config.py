"""Every STEALTHFOX_* variable, and the one reader that turns it into a launch.

⛔ THESE TESTS USED TO EXERCISE `config.launch_kwargs`, WHICH IS GONE. It was the
second place that read these variables: `plan_session` decided the seed, the exit
and the profile, then called `launch_kwargs` and popped the three fields it had
just decided. Popping a duplicate is not removing it, and the leftover half went
on PARSING `STEALTHFOX_PROXY` after the exit was already settled.

Measured before the deletion, and both cases are in here as tests now:

  * `STEALTHFOX_NO_PROXY=1` with a malformed `STEALTHFOX_PROXY` killed the
    session on a value nobody was going to use;
  * so did a perfectly good proxy passed by the CALLER, because the environment
    was still parsed on the way past.

What the old tests checked is all still checked; it is just asked of the
function that now answers for it.
"""
from __future__ import annotations

import pytest

from invisible_playwright_mcp import plan


def test_an_empty_environment_still_produces_a_launchable_session():
    kwargs = plan.plan_session(env={}).kwargs

    assert kwargs["headless"] is True, "headless is the default"
    assert isinstance(kwargs["seed"], int), "a session always has an identity"
    assert "proxy" not in kwargs and "profile_dir" not in kwargs
    assert "binary_path" not in kwargs


def test_headless_can_be_turned_off():
    assert plan.plan_session(env={"STEALTHFOX_HEADLESS": "0"}).kwargs["headless"] is False


def test_the_seed_comes_from_the_environment():
    assert plan.plan_session(env={"STEALTHFOX_SEED": "42"}).kwargs["seed"] == 42


def test_a_proxy_url_is_split_into_server_and_credentials():
    kwargs = plan.plan_session(env={"STEALTHFOX_PROXY": "http://u:p@h.example:8080"}).kwargs

    assert kwargs["proxy"] == {"server": "http://h.example:8080",
                               "username": "u", "password": "p"}


def test_the_binary_and_the_profile_reach_the_launch(tmp_path):
    kwargs = plan.plan_session(
        env={"STEALTHFOX_BINARY": "C:/ff.exe",
             "STEALTHFOX_PROFILE_DIR": str(tmp_path / "prof")}).kwargs

    assert kwargs["binary_path"] == "C:/ff.exe"
    assert kwargs["profile_dir"] == str((tmp_path / "prof").resolve())


# -- the variable nobody is going to use must not be able to refuse ---------

def test_a_broken_proxy_is_not_parsed_when_no_proxy_is_set():
    """⛔ Known-bad is a second reader. This raised `ValueError: proxy URL
    'not-a-url' is missing a scheme or host` for a session that had already
    decided not to use a proxy at all."""
    result = plan.plan_session(env={"STEALTHFOX_PROXY": "not-a-url",
                                    "STEALTHFOX_NO_PROXY": "1"})
    assert "proxy" not in result.kwargs


def test_a_broken_proxy_is_not_parsed_when_the_caller_supplied_one():
    """The same defect from the side that matters more: the caller said exactly
    where to go out, and a stale variable in the shell refused the session."""
    result = plan.plan_session(proxy="socks5://good.invalid:1080",
                               env={"STEALTHFOX_PROXY": "not-a-url"})
    assert result.kwargs["proxy"] == {"server": "socks5://good.invalid:1080"}


def test_a_broken_proxy_is_not_parsed_when_the_caller_refused_one():
    result = plan.plan_session(proxy=plan.NONE,
                               env={"STEALTHFOX_PROXY": "not-a-url"})
    assert "proxy" not in result.kwargs


def test_a_broken_proxy_that_IS_going_to_be_used_still_refuses():
    """The case that must NOT be silenced. Ignoring the three above must not
    turn into ignoring a proxy the session actually needs: that would launch on
    the host's own address while the caller believed it was proxied."""
    with pytest.raises(ValueError):
        plan.plan_session(env={"STEALTHFOX_PROXY": "not-a-url"})
