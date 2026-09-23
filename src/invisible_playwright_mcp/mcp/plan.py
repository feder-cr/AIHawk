"""The one place that decides how a session is launched, and says so out loud.

⛔ THIS MODULE EXISTS BECAUSE THE SAME FACT WAS COMPUTED IN TWO PLACES. The tool
that starts a session decided from its ARGUMENTS, and the browser launched from
`launch_kwargs(os.environ)`. Nothing kept them in agreement, so they drifted in
the way two copies always drift, and the answer handed back to the caller
described a browser that had not been started:

  * with a profile set in the environment, `identity.resolve_seed` never saw it,
    so the seed was drawn fresh on every session while the cookie jar persisted.
    Three sessions on one profile, three different fingerprints, one login. That
    is the exact tell `identity.py` was written to prevent, reintroduced by the
    code that called it.
  * the answer said `profile: none, so nothing survives this session` while a
    persistent profile was open.
  * `identity.py` was only ever reached from one optional tool, so the whole
    identity decision was skipped on the path the tool descriptions actively
    recommend ("you do not have to call it at all").

So there is now one function. It takes what the caller said and what the
environment says, decides everything once, and returns both the kwargs the
browser is launched with AND the sentence describing them. The sentence cannot
disagree with the launch because it is derived from the same object.

`config.launch_kwargs` was the second reader and is gone: it went on parsing
STEALTHFOX_PROXY after the exit had been decided here, so a malformed value
nobody was going to use still killed the session. Every STEALTHFOX_* variable
now has exactly one reader, and it is in this file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from . import identity
from .proxy import proxy_from_url

#: Passed for `profile` or `proxy` to mean "explicitly none", as opposed to
#: `None` which means "I did not say". Without the distinction a caller cannot
#: turn OFF something the environment set, and the one scenario that needs it -
#: checks that must not be linkable to each other - is unreachable.
NONE = ""

#: Words a caller passes when it meant NONE and echoed the answer back instead.
#: Each is a legal directory name, so without this they are created rather than
#: refused. Kept deliberately short: this catches an echo, not a typo, and a
#: longer list would start refusing directories people meant.
_NOT_A_PATH = frozenset({"none", "null", "nil", "no", "false", "undefined"})


def describe(kwargs: Mapping[str, Any], seed_from: str = "",
             exit_note: str = "", warnings=()) -> str:
    """The sentence a caller is told about a session, read from the KWARGS the
    browser was launched with.

    ⛔ It reads the launch, never the arguments that produced it. The answer
    used to be assembled from what the tool was CALLED with, so a profile
    arriving from the environment produced "profile: none, so nothing survives
    this session" over a browser holding a persistent profile - the caller was
    told the opposite of what happened, in the same breath as being told the
    seed. Anything derived from the launch cannot drift from it.

    `browser_open` knows two things this cannot: where the seed came from, and
    why there is no proxy. They are passed in rather than recomputed, and
    `browser_status` simply omits them.
    """
    profile = kwargs.get("profile_dir")
    proxy = kwargs.get("proxy") or {}
    seed = kwargs.get("seed")
    parts = [
        "identity: seed %s%s." % (seed, " (%s)" % seed_from if seed_from else ""),
        "exit: %s." % (proxy.get("server") or exit_note
                       or "this machine's own address, with no proxy in the way"),
        "profile: %s." % (profile or "none, so nothing survives this session"),
        "headless: %s." % ("yes" if kwargs.get("headless") else "no"),
    ]
    return " ".join(parts) + "".join("\nwarning: " + w for w in warnings)


@dataclass(frozen=True)
class SessionPlan:
    """Everything decided about one session, and where each part came from."""

    kwargs: dict
    seed: int
    seed_from: str
    exit: str
    profile: Optional[str]
    warnings: tuple = field(default=())

    # ⛔ `describe(self)` STOOD HERE AND WAS A SECOND MAPPING OF THIS OBJECT
    # ONTO THE SENTENCE. It forwarded all four fields to the function above, and
    # so did `work.open`, which is the only place the product ever says this out
    # loud - two copies of "which field is which parameter", free to disagree the
    # day a fifth field joins the sentence.
    #
    # It also described something that does not happen. A plan does not reach
    # the caller unchanged: between planning and launching, `work.open` can
    # rewrite the settings and the exit note, which is how the helper browser
    # comes to share `main`'s exit. The sentence a caller is told is read from
    # what was LAUNCHED, never from what was planned - the whole point of the
    # module function - and a method on the plan quietly offered the other
    # thing. Its six callers were all in one test file, and they now go through
    # the function the product goes through.


def _asked(explicit: Optional[str], env: Mapping[str, str], name: str) -> str:
    """The value this session was asked for: the caller's, or the environment's.

    ⛔ THE THREE-VALUED RULE, WRITTEN ONCE. `None` means the caller said
    nothing, so the environment decides; anything else is the caller's word,
    including `NONE` - the empty string - which is an explicit refusal and
    beats the environment. Without that distinction a caller cannot turn OFF
    what the environment turned on, and the one scenario that needs it, checks
    that must not be linkable to each other, is unreachable.

    It was spelled out in both resolvers below, in two different shapes, with
    the second one's docstring saying "same three-way rule as the profile" -
    a claim a reader had to go and verify, and a claim that stops being true
    the moment one of the two is edited.
    """
    return env.get(name, "") if explicit is None else explicit


def _resolve_profile(explicit: Optional[str], env: Mapping[str, str]) -> Optional[str]:
    """Which profile directory this session uses, as an absolute path.

    Three-valued through `_asked`: nothing said, an explicit refusal, or a
    value.

    ⛔ The path is made ABSOLUTE here. A relative path resolves against the
    SERVER PROCESS's working directory, which the caller cannot see and does not
    control: the same string is a different directory when the client is started
    from somewhere else, and the login that was there yesterday is silently
    gone. Resolving it here at least makes the answer able to say which
    directory was actually used.
    """
    chosen = _asked(explicit, env, "STEALTHFOX_PROFILE_DIR")
    if not chosen:
        return None
    if chosen.strip().lower() in _NOT_A_PATH:
        # ⛔ The answer says `profile: none, so nothing survives this session`,
        # and a caller reading its own transcript back passes that word as the
        # value. It is a legal directory name, so it would be CREATED: a brand
        # new empty profile, a sign-in wall, and nobody told that the profile
        # they meant was never opened. Refusing costs a message; accepting costs
        # a login.
        raise ValueError(
            "%r reads as a word rather than a directory. Pass \"\" to run with "
            "no profile at all, or a real path such as C:/tmp/acct-a. If you "
            "truly mean a directory of that name, give it as an absolute path."
            % chosen)
    return str(Path(chosen).expanduser().resolve())


def _resolve_proxy(explicit: Optional[str], env: Mapping[str, str]) -> Optional[dict]:
    """Where the traffic goes out.

    The same `_asked` rule as the profile, plus `STEALTHFOX_NO_PROXY`, which
    until now was read by nobody at all while sitting in client configuration
    files that looked like it worked.

    ⛔ The veto applies to the ENVIRONMENT's answer only. A caller that passed
    a proxy asked for that proxy, and a variable set for a different session is
    not a reason to refuse it; a caller that passed `NONE` is refused already,
    by `_asked` returning the empty string. So the veto is read only when the
    caller said nothing, which is what the branch below says out loud instead
    of leaving it to the order of two returns.
    """
    if explicit is None and env.get("STEALTHFOX_NO_PROXY", "") not in (
            "", "0", "false", "False"):
        return None
    return proxy_from_url(_asked(explicit, env, "STEALTHFOX_PROXY"))


def _describe_exit(proxy: Optional[dict], explicit: Optional[str],
                   env: Mapping[str, str]) -> str:
    """⛔ Names the VALUE, not the variable it came from.

    The answer used to say `exit: STEALTHFOX_PROXY`, which is a label. Somebody
    asked to reproduce yesterday's session cannot act on the name of an
    environment variable whose value has since changed, and the transcript that
    was supposed to make the session repeatable recorded nothing usable.

    Credentials are deliberately absent: `proxy_from_url` splits them into
    separate keys, so `server` is already scheme://host:port and safe to print.
    """
    if proxy is None:
        if explicit == NONE:
            return "this machine's own address, because you asked for no proxy"
        if env.get("STEALTHFOX_NO_PROXY", "") not in ("", "0", "false", "False"):
            return "this machine's own address, because STEALTHFOX_NO_PROXY is set"
        return "this machine's own address, with no proxy in the way"
    return proxy["server"]


def engine_here(env: Optional[Mapping[str, str]] = None) -> dict:
    """The engine THIS process was told to launch, if it was told one.

    ⛔ THE ENGINE IS A PROPERTY OF THE PROCESS, NOT OF THE SESSION, and keeping
    those two apart is the whole reason this exists. `WHO_A_BROWSER_IS` leaves
    `binary_path` out of what a session writes down, and rightly: it is a path
    on THIS machine, and a session carried to another one must resolve an engine
    rather than insist on a path that means nothing there. But leaving it out of
    the FILE was read as leaving it out of the browser, so a browser restored
    from a saved session came back without the engine the person had asked for.

    Measured 2026-09-09, and it is not only a developer's problem. Somebody
    running `invisible-playwright-mcp ui --binary <their build>` and reopening a session got
    browsers on a DIFFERENT engine than the one they named, silently; on a build
    whose seal has no published assets - anything built locally - they got no
    browser at all, because there was nothing to download and nothing to run.

    The transcript is what happened; the engine is what this build was asked
    for. Same shape as the system prompt, which a saved conversation used to
    carry back in place of the current one.
    """
    env = os.environ if env is None else env
    named = env.get("STEALTHFOX_BINARY")
    return {"binary_path": named} if named else {}


def launched_here(env: Optional[Mapping[str, str]] = None) -> dict:
    """What THIS process decides about every browser it starts, whoever the
    browser is: the engine it runs on, and whether its window is shown.

    ⛔ TWO THINGS A SAVED SESSION MUST NOT DECIDE, read in one place. The engine
    was already kept out of the file (`engine_here`, and the reason above).
    `headless` was not, until 2026-09-14: the interface restored a `main` that
    a headed process had saved and showed its window on screen, uncloaked, at a
    launch that had asked for nothing of the kind - while the helper beside it,
    planned from this environment, stayed hidden. A launch flag written into an
    identity file outlives the launch it described. So the restore now writes
    this over whatever the file says, and the planner reads the same function,
    which is what keeps the two from disagreeing.
    """
    env = os.environ if env is None else env
    decided: dict[str, Any] = {
        "headless": env.get("STEALTHFOX_HEADLESS", "1") != "0",
    }
    decided.update(engine_here(env))
    return decided


def plan_session(seed: Optional[int] = None, proxy: Optional[str] = None,
                 profile: Optional[str] = None,
                 env: Optional[Mapping[str, str]] = None) -> SessionPlan:
    """Decide everything about one session, once.

    Every argument is three-valued: `None` means the caller said nothing and the
    environment decides, `NONE` means an explicit refusal that beats the
    environment, and a value is a value.

    Raises `identity.IdentityConflict` when an explicit seed contradicts the one
    a profile already carries, and `ValueError` for an unusable proxy URL or an
    unreadable `STEALTHFOX_SEED`. Both are refusals rather than choices: going
    on would hand the caller a different person than the one they asked for.
    """
    env = os.environ if env is None else env

    directory = _resolve_profile(profile, env)
    chosen_proxy = _resolve_proxy(proxy, env)

    # ⛔ The RESOLVED profile, not the argument. Passing the argument is what let
    # an environment profile keep its cookies while drawing a new fingerprint
    # every session.
    chosen_seed, seed_from = identity.resolve_seed(seed, directory, env)

    warnings = []
    if directory is not None:
        warnings.extend(identity.check_exit(directory, chosen_proxy))

    # ⛔ BUILT HERE, NOT BY A SECOND READER OF THE SAME VARIABLES. This used to
    # call `launch_kwargs(env)` and then pop the three fields it had just
    # decided, which left that function still PARSING STEALTHFOX_PROXY after the
    # exit was settled. Measured: with `STEALTHFOX_NO_PROXY=1` and a malformed
    # `STEALTHFOX_PROXY`, the session died on a value nobody was going to use -
    # and it died the same way when the CALLER had passed a perfectly good
    # proxy. Popping a duplicate is not removing it; every STEALTHFOX_* variable
    # now has exactly one reader.
    kwargs: dict[str, Any] = {"seed": chosen_seed}
    kwargs.update(launched_here(env))
    if chosen_proxy is not None:
        kwargs["proxy"] = chosen_proxy
    if directory is not None:
        kwargs["profile_dir"] = directory

    return SessionPlan(
        kwargs=kwargs,
        seed=chosen_seed,
        seed_from=seed_from,
        exit=_describe_exit(chosen_proxy, proxy, env),
        profile=directory,
        warnings=tuple(warnings),
    )
