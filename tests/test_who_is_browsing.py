"""Who the browser is, decided per session, and remembered when it should be.

⛔ THE COMBINATION THAT MATTERS IS PROFILE WITHOUT A SEED. Somebody asks for a
profile because they want to stay logged in. Draw a fresh seed each time and the
same cookie jar comes back wearing different hardware on every visit: same
account, new screen, new GPU, new fonts. That is a stronger signal than either
half alone, and it is the one this module exists to prevent.

So the rules under test, in the order they decide:

  1. a profile's own seed wins, because it is what keeps a returning login
     consistent;
  2. an explicit seed that CONTRADICTS a profile is refused, never resolved -
     both readings are reasonable and picking one silently hands somebody the
     wrong person while looking like it worked;
  3. an environment seed is a default, not a decision, so a profile beats it
     quietly;
  4. with nothing said at all the seed is drawn - and REPORTED, because a random
     identity nobody wrote down is a session nobody can reproduce.

No browser starts here. `resolve_seed` is a pure function over a directory, and
that is the whole point: the decision is testable without launching anything.
"""
from __future__ import annotations

import json

import pytest

from invisible_playwright_mcp import identity


def _write(profile, seed):
    profile.mkdir(parents=True, exist_ok=True)
    (profile / identity.IDENTITY_FILE).write_text(
        json.dumps({"seed": seed}), encoding="utf-8")


# ── nothing said ────────────────────────────────────────────────────────────

def test_with_nothing_at_all_a_seed_is_drawn():
    seed, where = identity.resolve_seed(None, None, {})
    assert isinstance(seed, int) and 0 < seed <= identity.SEED_MAX
    assert "drawn" in where


def test_two_sessions_with_nothing_said_are_two_different_people():
    """The reason the default is random: two sessions must not be one person.

    Known-bad is a fixed fallback seed, which is what a "sensible default"
    usually looks like and which makes every user of this package share one
    fingerprint.
    """
    seeds = {identity.resolve_seed(None, None, {})[0] for _ in range(20)}
    assert len(seeds) > 15, (
        "20 sessions produced only %d identities; the default is not random"
        % len(seeds))


# ── a seed, no profile ──────────────────────────────────────────────────────

def test_an_explicit_seed_is_used_as_given():
    assert identity.resolve_seed(4242, None, {})[0] == 4242


def test_the_environment_supplies_a_default_when_nothing_is_asked():
    seed, where = identity.resolve_seed(None, None, {"STEALTHFOX_SEED": "77"})
    assert seed == 77
    assert "STEALTHFOX_SEED" in where


def test_an_explicit_seed_beats_the_environment():
    """The environment is a default sitting in a shell; the argument is a
    decision somebody just made."""
    assert identity.resolve_seed(4242, None, {"STEALTHFOX_SEED": "77"})[0] == 4242


def test_an_unreadable_environment_seed_says_which_variable_is_wrong():
    """Known-bad is what the server did before this module existed: a bare
    `ValueError: invalid literal for int() with base 10: 'abc'`, which names
    neither the variable nor what a good value looks like."""
    with pytest.raises(ValueError) as caught:
        identity.resolve_seed(None, None, {"STEALTHFOX_SEED": "abc"})
    assert "STEALTHFOX_SEED" in str(caught.value)
    assert "4242" in str(caught.value), "the message shows no example"


# ── a profile ───────────────────────────────────────────────────────────────

def test_a_new_profile_is_given_an_identity_and_keeps_it(tmp_path):
    """The load-bearing one. A profile that does not carry a seed gets one, and
    the NEXT session on it reads the same one back."""
    profile = tmp_path / "person"

    first, where = identity.resolve_seed(None, str(profile), {})
    assert "kept in the profile" in where

    second, again = identity.resolve_seed(None, str(profile), {})
    assert second == first, (
        "the same profile answered %d and then %d: a login on it would come "
        "back with different hardware" % (first, second))
    assert again == "the profile"


def test_a_profile_keeps_the_seed_it_was_created_with(tmp_path):
    profile = tmp_path / "person"
    identity.resolve_seed(4242, str(profile), {})
    assert identity.resolve_seed(None, str(profile), {})[0] == 4242


def test_a_profile_beats_the_environment_quietly(tmp_path):
    """An env seed was not a decision about this session. The profile wins and
    says so, rather than refusing over something the caller may not know is
    set."""
    profile = tmp_path / "person"
    _write(profile, 4242)

    seed, where = identity.resolve_seed(None, str(profile), {"STEALTHFOX_SEED": "77"})
    assert seed == 4242
    assert where == "the profile"


def test_a_seed_that_contradicts_the_profile_is_refused(tmp_path):
    """⛔ Refused, never resolved. "use this identity" and "use this profile's
    identity" are both reasonable readings, so choosing one silently gives
    somebody the wrong person while looking like it worked."""
    profile = tmp_path / "person"
    _write(profile, 4242)

    with pytest.raises(identity.IdentityConflict) as caught:
        identity.resolve_seed(99, str(profile), {})

    message = str(caught.value)
    assert "4242" in message and "99" in message, (
        "the refusal names neither number, so nobody can act on it: %s" % message)
    assert identity.IDENTITY_FILE in message, "it does not say how to start over"


def test_the_same_seed_as_the_profile_is_not_a_conflict(tmp_path):
    """Saying out loud what the profile already is must not be an error."""
    profile = tmp_path / "person"
    _write(profile, 4242)
    assert identity.resolve_seed(4242, str(profile), {})[0] == 4242


def test_two_profiles_are_two_people(tmp_path):
    a, _ = identity.resolve_seed(None, str(tmp_path / "one"), {})
    b, _ = identity.resolve_seed(None, str(tmp_path / "two"), {})
    assert a != b, "two profiles were given the same identity"


def test_a_corrupted_identity_file_does_not_stop_the_browser(tmp_path):
    """It is treated as absent and rewritten. Refusing to start because a JSON
    file is broken would be a browser nobody can launch over a file nobody knew
    existed."""
    profile = tmp_path / "person"
    profile.mkdir()
    (profile / identity.IDENTITY_FILE).write_text("{not json", encoding="utf-8")

    seed, _ = identity.resolve_seed(None, str(profile), {})
    assert isinstance(seed, int)
    assert identity.resolve_seed(None, str(profile), {})[0] == seed, (
        "the rewritten file is not being read back")


def test_the_identity_travels_inside_the_profile(tmp_path):
    """Copying a profile has to carry the person with it, or the copy is a
    different browser wearing the same cookies."""
    profile = tmp_path / "person"
    seed, _ = identity.resolve_seed(None, str(profile), {})

    import shutil

    copy = tmp_path / "copied"
    shutil.copytree(profile, copy)
    assert identity.resolve_seed(None, str(copy), {})[0] == seed
