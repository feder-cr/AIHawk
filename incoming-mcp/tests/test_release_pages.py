"""Every version on the index needs a GitHub release carrying it.

Measured 2026-09-02, on this repository: FIVE published versions, five tags, and
ZERO releases. The rule has existed for months and the two sibling packages each
have a test enforcing it. This one did not, so nothing here ever said so, and the
gap grew one release at a time without anything downstream breaking.

That is the whole reason this file exists. The releases were backfilled by hand
the same day, and a gap fixed by hand and guarded by nothing reopens on the next
release.

The release page is where a reader looks for what changed. Without it `git
describe` has nothing to say and there is no commit anybody can point at as the
source of the version they have.

WALKS EVERY VERSION, not the latest. The sibling test read `info.version` until
2026-08-02, so the moment a release shipped without its page the NEXT release
hid the omission: the check moved on and the old gap stayed behind it. Eleven
published versions across three packages turned out to have no release, three of
them published after the backfill that test was written to protect.

ONE-DIRECTIONAL on purpose. A release for a version not yet on the index is a
normal intermediate state during a publish. An index version with no release is
the thing that gets forgotten, precisely because nothing breaks.

Enabled by MCP_CHECK_RELEASES, which the `releases` CI job sets. It is one API
call per version against a network service, so it does not belong in the unit
suite, and a job that sets the variable itself cannot silently skip.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

PACKAGE = "invisible-playwright-mcp"
REPOSITORY = "feder-cr/invisible-playwright-mcp"

pytestmark = pytest.mark.skipif(
    os.environ.get("MCP_CHECK_RELEASES") != "1",
    reason="set MCP_CHECK_RELEASES=1 to check the index against GitHub releases",
)


def _index_versions():
    with urllib.request.urlopen(f"https://pypi.org/pypi/{PACKAGE}/json", timeout=30) as resp:
        releases = json.load(resp)["releases"]
    # Yanked versions are skipped: a yank says nobody should install this, and
    # demanding a release page for it asks for the opposite of what the yank said.
    live = [v for v, files in releases.items()
            if files and not all(f.get("yanked") for f in files)]
    return sorted(live, key=lambda v: tuple(int(p) for p in v.split(".")))


def test_every_published_version_has_a_release_page():
    versions = _index_versions()
    assert versions, f"the index serves no usable version of {PACKAGE}"

    # Authenticated when a token is around, which on a GitHub runner it always
    # is. Unauthenticated the API allows 60 calls an hour per IP and this walk
    # wants one per version. Never printed.
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    missing, drafts, empty = [], [], []
    checked = 0
    cut_short = None
    for version in versions:
        url = f"https://api.github.com/repos/{REPOSITORY}/releases/tags/v{version}"
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=headers), timeout=30) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                missing.append(version)
                checked += 1
                continue
            if exc.code in (403, 429):
                # NOT an unconditional skip. Abandoning the walk here would
                # throw away every violation already in hand, so a rate limit
                # two versions in would report PASS over a real gap. A gate that
                # discards its own findings on an unrelated error is worse than
                # no gate.
                cut_short = (version, exc.code)
                break
            raise
        checked += 1
        if payload.get("draft") is not False:
            drafts.append(version)
        if not (payload.get("body") or "").strip():
            empty.append(version)

    problems = []
    if missing:
        problems.append(f"published with no release page: {', '.join(missing)}")
    if drafts:
        problems.append(f"release is still a draft: {', '.join(drafts)}")
    if empty:
        problems.append(f"release page says nothing: {', '.join(empty)}")
    if cut_short:
        problems.append(
            f"the walk stopped at {cut_short[0]} on HTTP {cut_short[1]} after "
            f"{checked} of {len(versions)} versions, so the rest is unknown")
    assert not problems, "; ".join(problems)


def test_the_walk_covers_more_than_the_latest_version():
    """A guard on the guard.

    The defect this file inherits was not a missing check, it was a check that
    looked at one version and claimed to look at all of them. If the index ever
    serves a single version this test is vacuous, and it says so rather than
    passing quietly.
    """
    versions = _index_versions()
    assert len(versions) > 1, (
        "only one version on the index, so the walk above proves nothing about "
        "older releases; revisit when a second version ships")
