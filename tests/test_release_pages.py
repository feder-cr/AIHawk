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

ONE-DIRECTIONAL on purpose, for RELEASE PAGES. A release page for a version not
yet on the index is a normal intermediate state during a publish. An index
version with no release page is the thing that gets forgotten, precisely because
nothing breaks.

⛔ AND THE OTHER DIRECTION HAS A HOLE THAT COST A RELEASE ON 2026-09-14, WHICH
THE SECOND WALK BELOW CLOSES. `v0.56.0` was tagged, the publish workflow ran,
its `gate` job died on a 504 downloading the engine from GitHub Releases, and
`upload` was therefore SKIPPED. So the tag existed, main carried the bumped
version, and the index served nothing - a state indistinguishable from a
successful release unless somebody opens the run and reads it. Nothing in this
suite could see it: this file walks the INDEX, so a version that never reached
the index is not in anything it looks at, and `test_version_is_not_taken`
answers "free" for exactly that case, which is its correct answer.

A TAG is the durable artifact of an attempted release - the release page is not,
because a failed gate skips that too - so the second walk starts from tags, and
it is bounded by AGE rather than being forbidden outright: a tag pushed a minute
ago and not yet on the index is a publish in flight, which is normal, and one
from an hour ago is a release that silently shipped nothing.

Enabled by INVISIBLE_MCP_CHECK_RELEASES, which the `releases` CI job sets. It is one API
call per version against a network service, so it does not belong in the unit
suite, and a job that sets the variable itself cannot silently skip.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import urllib.error
import urllib.request

import pytest

PACKAGE = "invisible-playwright-mcp"
REPOSITORY = "feder-cr/invisible_playwright_mcp"

#: What the readers below answer when the index has never heard of the project.
#:
#: ⛔ THREE OUTCOMES, NOT TWO, AND THE THIRD ARRIVED AS AN UNHANDLED 404. Both
#: readers went straight to `json.load`, on the assumption that the project is
#: on the index - true every day until 2026-09-23, when the owner deleted it to
#: free a name and the package took a name that had never published anything.
#: All three tests here then died inside `urllib`, in a job CI runs with
#: `INVISIBLE_MCP_CHECK_RELEASES=1`, with a traceback about HTTP rather than a sentence
#: about releases.
#:
#: An empty version list and an absent project are NOT the same news: a project
#: that serves no usable version is the defect this file exists to report, while
#: a project that has published nothing has nothing to report on. So the second
#: skips and says why, and the assertion that catches the first stays.
NOT_ON_THE_INDEX = None

pytestmark = pytest.mark.skipif(
    os.environ.get("INVISIBLE_MCP_CHECK_RELEASES") != "1",
    reason="set INVISIBLE_MCP_CHECK_RELEASES=1 to check the index against GitHub releases",
)


def _releases_json():
    """The index's `releases` map, or NOT_ON_THE_INDEX when there is no project.

    Only a 404 is turned into an answer. Any other failure is left to raise:
    an unreachable index must not read as a project with no releases.
    """
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{PACKAGE}/json", timeout=30) as resp:
            return json.load(resp)["releases"]
    except urllib.error.HTTPError as failed:
        if failed.code == 404:
            return NOT_ON_THE_INDEX
        raise


def _skip_if_nothing_published(releases):
    if releases is NOT_ON_THE_INDEX:
        pytest.skip("the index has no project named %s, so nothing has been "
                    "published to check tags or release pages against" % PACKAGE)


def _index_versions():
    releases = _releases_json()
    _skip_if_nothing_published(releases)
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


#: How long a tag may exist without its version being on the index. A publish
#: takes about ten minutes when the engine downloads cleanly; this is loose
#: enough that a release in flight is never a red gate, and tight enough that a
#: failed one is red on the same afternoon.
PUBLISH_GRACE_MINUTES = 45


def _all_index_versions():
    """Every version the index has ever served, yanked ones included.

    ⛔ NOT the live list the walk above uses. A yank says nobody should install
    that version; it does not say it was never published, and a tag for a yanked
    version is a release that DID happen. Comparing tags against the live list
    would report every yank as a failed publish.
    """
    releases = _releases_json()
    _skip_if_nothing_published(releases)
    return {v for v, files in releases.items() if files}


def _github(path, headers):
    with urllib.request.urlopen(
            urllib.request.Request(f"https://api.github.com/repos/{REPOSITORY}/{path}",
                                   headers=headers), timeout=30) as resp:
        return json.load(resp)


def test_every_tag_older_than_the_grace_reached_the_index():
    """A tag that published nothing, said out loud.

    Measured 2026-09-14: `v0.56.0` was tagged and its publish run died in the
    gate on a 504 from GitHub's release assets, so `upload` was skipped and the
    index served nothing for ten minutes, with a red workflow as the only
    signal. Re-running the failed jobs published it. Had nobody looked, the next
    release would have been 0.57.0 and that version would simply not exist.

    Known-bad: point PACKAGE at a name this account does not publish, and every
    tag becomes a suspect.

    Cheap by construction: one call for the tags, one for the index, and one per
    SUSPECT, which on a healthy repository is none.
    """
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    tags, page = {}, 1
    while True:
        got = _github(f"tags?per_page=100&page={page}", headers)
        if not got:
            break
        for one in got:
            if re.fullmatch(r"v\d+\.\d+\.\d+", one["name"]):
                tags[one["name"][1:]] = one["commit"]["sha"]
        if len(got) < 100:
            break
        page += 1

    assert tags, "no version tag was found at all, so this walk is watching nothing"

    published = _all_index_versions()
    suspects = sorted(set(tags) - published,
                      key=lambda v: tuple(int(p) for p in v.split(".")))

    now = datetime.datetime.now(datetime.timezone.utc)
    stale = []
    for version in suspects:
        when = _github(f"commits/{tags[version]}", headers)["commit"]["committer"]["date"]
        at = datetime.datetime.fromisoformat(when.replace("Z", "+00:00"))
        old_by = (now - at).total_seconds() / 60
        if old_by > PUBLISH_GRACE_MINUTES:
            stale.append("v%s (tagged %d minutes ago)" % (version, old_by))

    assert not stale, (
        "tagged and never published: %s. The tag exists, the index does not "
        "serve that version, and a release from a later tag would leave it "
        "missing for good. Open the publish run for that tag and read which "
        "job failed; re-running the failed jobs is usually the whole fix."
        % ", ".join(stale))


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
