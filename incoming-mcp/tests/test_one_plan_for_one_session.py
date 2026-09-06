"""What a session is told must be what the browser was launched with.

⛔ THESE ARE ALL THE SAME DEFECT SEEN FROM DIFFERENT SIDES. The tool that starts
a session decided from its ARGUMENTS while the browser launched from
`launch_kwargs(os.environ)`, so the two drifted the way two copies of a fact
always drift. The worst of it was not a confusing sentence:

  * with a profile set in the environment the identity decision never saw it, so
    the seed was drawn fresh every session while the cookie jar persisted. One
    login, three fingerprints. That is the exact tell `identity.py` exists to
    prevent, reintroduced by the code that called it.
  * the answer said `profile: none, so nothing survives this session` over a
    browser holding a persistent profile.
  * a caller could not turn OFF an environment profile, because `if profile:`
    cannot tell "I said no" from "I said nothing".

`plan_session` is now the only thing that decides, and `describe` reads the
kwargs it produced rather than the arguments that produced them. No browser
starts here: that is the point of having one pure function decide.
"""
from __future__ import annotations

import json

import pytest

from invisible_playwright_mcp import identity, plan


def _seed_of(profile):
    return json.loads((profile / identity.IDENTITY_FILE).read_text(encoding="utf-8"))["seed"]


# -- the environment profile, which is where the tell lived ------------------

def test_a_profile_from_the_environment_keeps_its_seed(tmp_path):
    """The load-bearing one. Known-bad is passing the ARGUMENT profile to the
    identity decision: the seed is then redrawn every session while the cookies
    persist, which is a stronger signal than either half alone."""
    env = {"STEALTHFOX_PROFILE_DIR": str(tmp_path / "person")}

    seeds = {plan.plan_session(env=env).seed for _ in range(3)}
    assert len(seeds) == 1, (
        "three sessions on one profile produced %d identities: %r" % (len(seeds), seeds))


def test_the_answer_describes_the_browser_that_started(tmp_path):
    """Known-bad is building the sentence from the arguments: with the profile
    coming from the environment it then reads "profile: none" over a persistent
    profile, telling the caller the opposite of what happened."""
    directory = tmp_path / "person"
    plan_ = plan.plan_session(env={"STEALTHFOX_PROFILE_DIR": str(directory)})

    assert plan_.kwargs["profile_dir"] == str(directory.resolve())
    assert "none, so nothing survives" not in plan_.describe()
    assert str(directory.resolve()) in plan_.describe()


def test_describe_reads_the_kwargs_not_the_arguments():
    """The property that makes the class of bug impossible rather than fixed:
    anything derived from the launch cannot describe a different browser."""
    text = plan.describe({"seed": 4242, "profile_dir": "C:/x", "headless": False,
                          "proxy": {"server": "socks5://h:1080"}})
    assert "4242" in text and "C:/x" in text
    assert "socks5://h:1080" in text
    assert "headless: no" in text


# -- saying no, as opposed to saying nothing ---------------------------------

def test_an_empty_profile_turns_off_the_environment_one(tmp_path):
    """⛔ The scenario this unlocks is a real one: checks that must not be
    linkable to each other. Known-bad is `if profile:`, which cannot tell a
    refusal from a silence, and leaves the environment's profile in place while
    reporting that there is none."""
    env = {"STEALTHFOX_PROFILE_DIR": str(tmp_path / "person")}

    said_nothing = plan.plan_session(env=env)
    said_no = plan.plan_session(profile=plan.NONE, env=env)

    assert "profile_dir" in said_nothing.kwargs
    assert "profile_dir" not in said_no.kwargs
    assert said_no.profile is None


def test_an_empty_proxy_turns_off_the_environment_one():
    env = {"STEALTHFOX_PROXY": "socks5://host.invalid:1080"}

    assert "proxy" in plan.plan_session(env=env).kwargs
    assert "proxy" not in plan.plan_session(proxy=plan.NONE, env=env).kwargs


def test_two_sessions_that_said_no_to_the_profile_are_two_people(tmp_path):
    """The whole point of saying no: without a profile there is nothing to
    remember, so each session is a different stranger."""
    env = {"STEALTHFOX_PROFILE_DIR": str(tmp_path / "person")}
    seeds = {plan.plan_session(profile=plan.NONE, env=env).seed for _ in range(8)}
    assert len(seeds) > 6, "sessions that refused the profile shared an identity"


def test_no_proxy_from_the_environment_is_honoured():
    """STEALTHFOX_NO_PROXY sat in client configuration files looking like it
    worked, and was read by nothing at all."""
    env = {"STEALTHFOX_PROXY": "socks5://host.invalid:1080",
           "STEALTHFOX_NO_PROXY": "1"}
    result = plan.plan_session(env=env)
    assert "proxy" not in result.kwargs
    assert "STEALTHFOX_NO_PROXY" in result.exit


def test_no_proxy_switched_off_does_not_suppress_the_proxy():
    """The case that must NOT fire: a variable set to 0 is a variable turned
    off, not a variable present."""
    env = {"STEALTHFOX_PROXY": "socks5://host.invalid:1080",
           "STEALTHFOX_NO_PROXY": "0"}
    assert "proxy" in plan.plan_session(env=env).kwargs


# -- seeds ------------------------------------------------------------------

def test_seed_zero_is_a_seed():
    """Known-bad is `seed or None`, which swallows 0 and hands back a stranger
    while reporting a drawn seed. Zero is an ordinary number to ask for."""
    assert plan.plan_session(seed=0, env={}).seed == 0


def test_an_explicit_seed_survives_an_environment_profile(tmp_path):
    directory = tmp_path / "person"
    env = {"STEALTHFOX_PROFILE_DIR": str(directory)}

    assert plan.plan_session(seed=4242, env=env).seed == 4242
    assert _seed_of(directory) == 4242, "the profile did not keep what it was given"


def test_a_seed_contradicting_an_environment_profile_is_refused(tmp_path):
    """The refusal has to reach the environment profile too, or the guarantee
    only holds for profiles named in the call."""
    directory = tmp_path / "person"
    env = {"STEALTHFOX_PROFILE_DIR": str(directory)}
    plan.plan_session(seed=4242, env=env)

    with pytest.raises(identity.IdentityConflict):
        plan.plan_session(seed=99, env=env)


# -- paths ------------------------------------------------------------------

def test_a_relative_profile_is_reported_as_an_absolute_path(tmp_path, monkeypatch):
    """A relative path resolves against the SERVER's working directory, which
    the caller cannot see. Reporting the full path is the least that can be
    done about it."""
    monkeypatch.chdir(tmp_path)
    result = plan.plan_session(profile="acct-a", env={})

    assert result.profile == str((tmp_path / "acct-a").resolve())
    assert result.profile in result.describe()


def test_the_word_none_is_refused_rather_than_created(tmp_path, monkeypatch):
    """⛔ The answer says `profile: none, so nothing survives this session`, and
    a caller reading its own transcript back passes that word as the value.
    "none" is a legal directory name, so it was CREATED: an empty profile, a
    sign-in wall, and no sign that the intended profile was never opened.
    """
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError) as caught:
        plan.plan_session(profile="none", env={})

    assert '""' in str(caught.value), "the refusal does not say how to mean none"
    assert not (tmp_path / "none").exists(), "a directory was created anyway"


def test_a_real_directory_that_happens_to_be_named_none_still_works(tmp_path):
    """The case that must NOT fire. The guard catches an echoed word, not a
    path, so anyone who means it can say so."""
    directory = tmp_path / "none"
    assert plan.plan_session(profile=str(directory), env={}).profile == str(directory)


# -- the exit, which a profile does not own ---------------------------------

def test_a_profile_returning_through_another_exit_is_warned_about(tmp_path):
    """⛔ The half nothing mentioned. Timezone, locale and geography come from
    the exit, so a login returning from another country is the same class of
    tell as one returning on different hardware."""
    directory = str(tmp_path / "person")

    plan.plan_session(profile=directory, proxy="socks5://exit-a.invalid:1080", env={})
    second = plan.plan_session(profile=directory, proxy="socks5://exit-b.invalid:1080", env={})

    assert second.warnings, "the exit changed under a profile and nothing said so"
    assert "exit-a.invalid" in second.warnings[0] and "exit-b.invalid" in second.warnings[0]
    assert "warning:" in second.describe()


def test_the_same_exit_is_not_warned_about(tmp_path):
    """The case that must NOT fire. A check that fires every time is one people
    learn to ignore."""
    directory = str(tmp_path / "person")
    plan.plan_session(profile=directory, proxy="socks5://exit-a.invalid:1080", env={})
    again = plan.plan_session(profile=directory, proxy="socks5://exit-a.invalid:1080", env={})

    assert not again.warnings, "an unchanged exit produced %r" % (again.warnings,)


def test_the_first_session_on_a_profile_is_not_warned_about(tmp_path):
    """Nothing to compare against yet, so nothing to say."""
    result = plan.plan_session(profile=str(tmp_path / "person"),
                               proxy="socks5://exit-a.invalid:1080", env={})
    assert not result.warnings


def test_losing_the_proxy_under_a_profile_is_warned_about(tmp_path):
    """Going from an exit to no exit is the biggest change of all, and reads as
    'no proxy' rather than as a missing value."""
    directory = str(tmp_path / "person")
    plan.plan_session(profile=directory, proxy="socks5://exit-a.invalid:1080", env={})
    second = plan.plan_session(profile=directory, proxy=plan.NONE, env={})

    assert second.warnings
    assert "no proxy" in second.warnings[0]


def test_the_country_selector_in_the_username_is_noticed(tmp_path):
    """⛔ THE CASE THE CHECK EXISTS FOR, and the first version was blind to it.

    Rotating pools put the exit selector in the CREDENTIALS, not the host: one
    gateway, `host:port` identical forever, and the country chosen by a username
    like `user-country-fr-...`. Comparing the credential-free server alone, two
    deliberately different countries looked like the same exit, so the check was
    silent on exactly the change it was written to report.
    """
    directory = str(tmp_path / "person")
    gateway = "http://gw.example:8000"

    plan.plan_session(profile=directory,
                      proxy="http://user-country-fr-sess-a1b2:pw@gw.example:8000", env={})
    second = plan.plan_session(profile=directory,
                               proxy="http://user-country-cl-sess-9z8y:pw@gw.example:8000", env={})

    assert second.warnings, (
        "the country changed on the same gateway and nothing said so")
    assert "credentials" in second.warnings[0], (
        "the warning names two identical hosts without explaining what moved")
    assert gateway in second.warnings[0]


def test_the_same_credentials_on_the_same_gateway_are_not_warned_about(tmp_path):
    """The counter-case for the digest: comparing more must not mean warning
    more often."""
    directory = str(tmp_path / "person")
    url = "http://user-country-fr-sess-a1b2:pw@gw.example:8000"

    plan.plan_session(profile=directory, proxy=url, env={})
    assert not plan.plan_session(profile=directory, proxy=url, env={}).warnings


def test_only_the_password_changing_is_not_an_exit_change(tmp_path):
    """A rotated password is the same exit. Warning on it would be a false
    alarm, and false alarms are what teach people to skip the line."""
    directory = str(tmp_path / "person")

    plan.plan_session(profile=directory, proxy="http://u:old@gw.example:8000", env={})
    assert not plan.plan_session(profile=directory,
                                 proxy="http://u:rotated@gw.example:8000", env={}).warnings


def test_remembering_the_exit_stores_no_credentials(tmp_path):
    """⛔ A profile directory is a thing people copy, sync and occasionally
    commit. What is written there must not be a password."""
    directory = tmp_path / "person"
    plan.plan_session(profile=str(directory),
                      proxy="socks5://user:hunter2@exit-a.invalid:1080", env={})

    written = (directory / identity.IDENTITY_FILE).read_text(encoding="utf-8")
    assert "hunter2" not in written and "user" not in written
    assert "exit-a.invalid" in written


# -- the exit is a value, not a label ---------------------------------------

def test_the_exit_is_reported_as_a_value(tmp_path):
    """Known-bad is `exit: STEALTHFOX_PROXY`, the NAME of a variable. Somebody
    reproducing yesterday's session cannot act on the name of something whose
    value has since changed."""
    env = {"STEALTHFOX_PROXY": "socks5://exit-a.invalid:1080"}
    result = plan.plan_session(env=env)

    assert result.exit == "socks5://exit-a.invalid:1080"
    assert "STEALTHFOX_PROXY" not in result.describe()


def test_a_proxy_password_is_never_in_the_answer():
    result = plan.plan_session(proxy="socks5://user:hunter2@exit-a.invalid:1080", env={})
    assert "hunter2" not in result.describe()


def test_a_bare_session_carries_no_settings_at_all():
    """⛔ THE CONTRACT THAT SENDS EVERY CALLER THROUGH THE PLANNER, and it cost a
    red CI to write down.

    `StealthSession.__init__` used to fall back to `launch_kwargs(os.environ)`,
    which made it a third place that decided how a browser is configured. Removing
    that was right - deciding is this module's job and only its job - but it means
    a bare `StealthSession()` now carries NOTHING, including no `headless`, so it
    launches HEADED. That passes on any desktop and dies on a runner with
    `no DISPLAY environment variable specified`, which is exactly how it reached
    CI: green locally on Windows, red on all three Python versions on Linux.

    Production never builds one bare - `registry.ensure` and `registry.restart`
    both come from `plan_session` - and this pins the reason, so the next caller
    that reaches for `StealthSession()` finds out here instead of on a runner.
    """
    from invisible_playwright_mcp.session import StealthSession

    assert StealthSession()._kwargs == {}, (
        "a bare session grew a default again; whatever supplies it is now a "
        "second place that decides how a browser is launched")

    planned = plan.plan_session(env={}).kwargs
    assert planned["headless"] is True, (
        "the planner is the only source of headless, and it stopped saying so")
