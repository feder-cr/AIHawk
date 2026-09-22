"""Who the browser is for one session: the seed, and where it is remembered.

⛔ THE SEED AND THE PROFILE ARE ONE DECISION, NOT TWO, and getting that wrong is
the reason this module exists rather than a couple of lines in the server.

A profile directory is asked for because somebody wants to stay logged in. If
the seed is drawn fresh each time, the same cookie jar comes back wearing
different hardware on every visit: same account, same session cookies, a new
screen, a new GPU, new fonts. That is a stronger signal than either half on its
own, and it is exactly the class of tell this product exists to remove.

So a profile OWNS its seed. The first session on a new profile draws one and
writes it inside; every session after that reads it back. "This profile is this
person" becomes true by construction, and the caller never has to remember a
number to stay consistent.

Without a profile there is nothing to remember, so the seed is drawn fresh and
every session is a different stranger - which is the right default for somebody
who has not thought about it.

⛔ AND A DRAWN SEED IS ALWAYS REPORTED. A random identity that is not written
down cannot be reproduced, and this project debugs by re-running the same seed.
The caller is told which one it got, every time, so a session that went wrong is
still a session somebody can repeat.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Mapping, Optional

#: Where a profile keeps its seed. Inside the profile directory on purpose: it
#: travels with the thing it identifies, so copying a profile to another machine
#: carries the identity with it rather than silently changing it.
IDENTITY_FILE = ".stealth-identity.json"

#: A drawn seed is a number somebody may have to type back. 31 bits keeps it
#: short enough to read off a terminal and copy without mistakes, and the engine
#: takes any int.
SEED_MAX = 2 ** 31 - 1


class IdentityConflict(ValueError):
    """An explicit seed contradicts the one the profile already carries."""


def _read(profile: Path) -> dict:
    """The whole record, or an empty one.

    ⛔ A corrupted identity file must not stop the browser from starting.
    Refusing to launch over a JSON file nobody knew existed is a worse failure
    than the one it would report, so it is treated as absent and rewritten.
    """
    path = profile / IDENTITY_FILE
    if not path.is_file():
        return {}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return record if isinstance(record, dict) else {}


def _write(profile: Path, **fields) -> None:
    """Merge `fields` into the record. The only writer, so the file's shape is
    known in one place and a new field cannot erase an old one."""
    profile.mkdir(parents=True, exist_ok=True)
    record = _read(profile)
    record.update(fields)
    (profile / IDENTITY_FILE).write_bytes(
        json.dumps(record, indent=1).encode("utf-8"))


def _stored(profile: Path) -> Optional[int]:
    value = _read(profile).get("seed")
    return int(value) if isinstance(value, int) else None


def _remember(profile: Path, seed: int) -> None:
    _write(profile, seed=seed)


def _exit_id(proxy: Optional[dict]) -> Optional[str]:
    """A short digest of the exit AS DECLARED, including the username.

    The username is what selects the country on most rotating pools, so it has
    to take part in the comparison - and it is credential-shaped, so it must not
    be written down. A digest does both. The password is left out entirely: it
    never distinguishes one exit from another, so including it would add risk
    and no information.
    """
    if not proxy:
        return None
    material = "%s\n%s" % (proxy.get("server", ""), proxy.get("username", ""))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def check_exit(profile: str, proxy: Optional[dict]) -> list:
    """Warn when a profile comes back through a different exit, and remember it.

    ⛔ A PROFILE OWNS ITS SEED FOR A REASON THAT APPLIES JUST AS MUCH TO ITS
    EXIT, and until now only half of it was enforced. The argument in this
    module's docstring is that a login returning with different hardware is a
    stronger signal than either half alone. Timezone, locale and geography are
    derived from the proxy exit, so a login returning from another country is
    the same signal on the other half of the identity - and it was the half
    nothing mentioned anywhere.

    It WARNS rather than refuses, which is deliberately not what the seed does.
    A contradicting seed is refused because "use this identity" and "use this
    profile's identity" are both reasonable readings and picking one silently
    hands somebody the wrong person. An exit is not symmetric: somebody changing
    proxy usually means it, exits go down and get replaced, and refusing would
    block a session over a decision the caller already made. So it is said out
    loud and the caller decides.

    ⛔ IT COMPARES THE USERNAME TOO, WITHOUT STORING IT, and the first version of
    this did not - which made it blind to the case it claims to catch. Providers
    put the exit selector in the CREDENTIALS, not in the host: one gateway,
    `host:port` identical forever, and the country chosen by a username like
    `user-country-fr-sess-a1b2`. Comparing the credential-free `server` alone,
    two deliberately different countries looked like the same exit. So the
    comparison is over a digest of server plus username, and only the digest and
    the server are written down: the username is not recoverable from the file,
    and the password never reaches it.

    ⛔ AND IT STILL ONLY SEES WHAT WAS DECLARED. A provider that rotates its own
    addresses behind one unchanged URL is invisible from here, because nothing
    in the declaration moves. This catches a caller who CHANGED the exit, never
    a provider that rotated it. The tool description carries the same caveat: a
    check believed to be wider than it is, is worse than one nobody trusts.

    Two outcomes are right here, unlike a check that MEASURES something. There
    is no "could not be established" case to score, because the thing compared
    is the caller's own declaration, which is always known at this point.
    """
    directory = Path(profile)
    current = proxy["server"] if proxy else None
    identifier = _exit_id(proxy)
    record = _read(directory)

    warnings = []
    if "exit_id" in record and record["exit_id"] != identifier:
        same_host = record.get("exit") == current and current is not None
        warnings.append(
            "this profile last went out through %s and is now using %s.%s The "
            "timezone, locale and geography a site sees come from the exit, so "
            "this login is arriving from somewhere else than it did before."
            % (record.get("exit") or "no proxy", current or "no proxy",
               " The host is the same, so the change is in the credentials -"
               " which is where providers put the country." if same_host else ""))

    _write(directory, exit=current, exit_id=identifier)
    return warnings


def resolve_seed(explicit: Optional[int], profile: Optional[str],
                 env: Optional[Mapping[str, str]] = None) -> tuple:
    """Return `(seed, where)` for one session, remembering it when there is a
    profile.

    The order, and each step is a decision rather than a fallback:

      1. the profile's own seed, if it has one. It is the most specific thing
         anybody said, and it is what keeps a returning login consistent.
      2. an explicit seed from the caller.
      3. STEALTHFOX_SEED from the environment, which is a default for callers
         that never say anything, not a place to choose from.
      4. a fresh random one.

    ⛔ Step 1 beats step 2 only by REFUSING, never by choosing. If the caller
    names a seed and the profile carries a different one, both readings are
    reasonable - "use this identity" and "use this profile's identity" - and
    picking one silently would give somebody the wrong person while looking like
    it worked. It raises instead, and the message names both numbers.

    An ENV seed that disagrees with a profile does not raise: it was not a
    decision about this session, it was a default sitting in a shell. The
    profile wins, and `where` says so.
    """
    env = env or {}
    directory = Path(profile).expanduser() if profile else None

    carried = _stored(directory) if directory is not None else None
    if carried is not None:
        if explicit is not None and explicit != carried:
            raise IdentityConflict(
                "this profile is seed %d and you asked for %d. A profile keeps "
                "one identity, or the cookies it holds would come back wearing "
                "different hardware. Use seed %d, or point at another profile, "
                "or delete %s inside it to start over."
                % (carried, explicit, carried, IDENTITY_FILE))
        return carried, "the profile"

    if explicit is not None:
        seed, where = int(explicit), "you asked for it"
    elif env.get("STEALTHFOX_SEED"):
        try:
            seed = int(env["STEALTHFOX_SEED"])
        except ValueError:
            raise ValueError(
                "STEALTHFOX_SEED is %r, which is not a whole number. It is the "
                "browser identity, so it has to be an integer such as 4242."
                % env["STEALTHFOX_SEED"])
        where = "STEALTHFOX_SEED"
    else:
        seed, where = random.randrange(1, SEED_MAX), "drawn for this session"

    if directory is not None:
        _remember(directory, seed)
        where += ", and now kept in the profile"
    return seed, where
