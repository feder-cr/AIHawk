"""The version a change proposes must not already be on the index, unless
nothing that ships has moved since it was published.

⛔ MEASURED 2026-09-04, AND NOTHING SAW IT. `invisible_playwright_mcp 0.4.0` was published at
23:47. Over the following hours main gained two more changes - verbs for the
session tools, and a `.env` plus a raised dependency floor - while `pyproject`
still said `0.4.0`. So main carried content that was not the content of the
0.4.0 on the index, and no test, gate or workflow had an opinion about it.

The way that goes wrong is quiet, which is why it deserves a gate rather than a
habit. `publish.yml` asks the index first and treats an already-present version
as a deliberate no-op:

    200) present=yes
         "invisible-playwright-mcp $VERSION is already on the index. No-op, not a failure."

That is correct for a re-pushed or backfilled tag, and it cannot tell that case
apart from somebody forgetting to bump. So the release would have reported
success and shipped nothing, and the next person to look would find the feature
missing from a version that was tagged, released and green.

PULL REQUESTS ONLY, and that is the whole design. A pull request proposes new
content; if its version is already published, that content can never reach
anybody. On main straight after a release the version IS the published one until
somebody bumps, which is a normal resting state and not a defect, so a check
that ran there would be red for a reason nobody can act on - and a gate that is
red at rest is a gate people learn to skip.

⛔ AND "NEW CONTENT" MEANS WHAT THE INDEX SERVES, which the first version of
this file got wrong on its first day. It refused every pull request whose
version was published, and the first two after a release were the ledger the
publish workflow opens by itself and the changelog entry for that release. A
version bump on either would be a lie: nothing that ships had moved. The
question the gate asks now is the one it always meant. Since the tag of the
published version, has anything changed that goes into the wheel - the package
tree the build backend names, or `pyproject.toml`? The ledger, the changelog,
the tests, the workflows and the docs alter nothing anybody installs, so they
pass without a bump; a change under the package does not.

That needs the tag in the checkout, so the `version` CI job fetches the full
history. A version that is on the index with no tag in the clone is refused
outright rather than guessed at. The outcomes are free, taken-but-unmoved,
taken-and-moved, and cannot-tell, and only the third is a defect while the
fourth is a broken bench.

Enabled by INVISIBLE_MCP_CHECK_VERSION, which the `version` CI job sets itself, so it
cannot silently skip the way it does in a local run.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import urllib.error
import urllib.request

import pytest

PACKAGE = "invisible-playwright-mcp"

#: A tag far enough back that the package has certainly moved since, which
#: makes it the live known-bad for the diff half: a check that has only ever
#: said "unmoved" is not a check.
#:
#: ⛔ IT SAID "THE RELEASE BEFORE THE CURRENT LINE OF WORK" AND HAD NOT BEEN
#: TRUE FOR FIFTY VERSIONS. The assertion it backs was never wrong - the
#: package has certainly moved since 0.5.0 - but the sentence beside it
#: described a constant somebody would have to update every release, and
#: nobody did, so a reader reconciling the two would conclude the file had
#: been abandoned. What this value has to be is OLD and PRESENT in the clone;
#: naming it that way is what stops it from going stale again.
PREVIOUS_RELEASE_TAG = "v0.5.0"

ROOT = pathlib.Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not os.environ.get("INVISIBLE_MCP_CHECK_VERSION"),
    reason="set INVISIBLE_MCP_CHECK_VERSION=1 to ask the index (one network call)",
)


def _pyproject() -> dict:
    import tomllib

    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _declared_version() -> str:
    return _pyproject()["project"]["version"]


def _shipped_roots() -> tuple[str, ...]:
    """What the wheel carries, read from where the build backend declares it
    rather than typed here, so a moved package moves the gate with it."""
    packages = _pyproject()["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    return tuple(p.rstrip("/") + "/" for p in packages) + ("pyproject.toml",)


def _shipped(paths) -> list[str]:
    """The subset of `paths` that goes into the wheel.

    Pure on purpose: the known-bad below feeds it a list, no repository needed.
    """
    roots = _shipped_roots()
    return [p for p in paths if any(p == r or p.startswith(r) for r in roots)]


def _changed_since(tag: str):
    """Every path that differs between `tag` and the tree, or None when git
    cannot say: the tag is not in this checkout, or this is not a checkout.

    ⛔ None is not an empty list. An absent tag scored as "nothing changed"
    would pass exactly the case this file exists to refuse.
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", tag],
            cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, OSError):
        return None
    return [line.strip() for line in out.splitlines() if line.strip()]


#: `name>=X.Y.Z` at the head of a requirement, which is a version somebody
#: published. A two-part floor (`mcp>=1.8`) is deliberately not matched: the
#: index has `1.8.0`, and asking it about `1.8` gets a 404 that means nothing.
FLOOR = re.compile(r"^([A-Za-z0-9._-]+)\s*>=\s*(\d+\.\d+\.\d+)\s*(?:,|$)")


def _declared_floors():
    """(project, version) for every dependency floor this package declares.

    A project cannot depend on a version that was never on the index, and a
    floor that vanished from it is a package that can no longer be installed.
    So every one of these is a version the index must have, read from
    `pyproject.toml` rather than typed.
    """
    p = _pyproject()["project"]
    deps = list(p.get("dependencies") or [])
    for extra in (p.get("optional-dependencies") or {}).values():
        deps += list(extra)
    return [(m.group(1), m.group(2)) for m in (FLOOR.match(d) for d in deps) if m]


def _on_the_index(version: str, project: str = PACKAGE):
    """`True`, `False`, or None when the index would not say.

    ⛔ Three outcomes, not two. A network error is neither present nor absent,
    and scoring it as absent turns an unreachable index into a green gate -
    which is the failure this file exists to prevent, wearing a different hat.

    `project` is a parameter for one reason, and it is the known-bad below: the
    positive case has to ask about something that is certainly published, and
    this project is not that thing.
    """
    url = "https://pypi.org/pypi/%s/%s/json" % (project, version)
    try:
        with urllib.request.urlopen(url, timeout=20) as answer:
            return answer.status == 200
    except urllib.error.HTTPError as failed:
        if failed.code == 404:
            return False
        return None
    except Exception:
        return None


def test_the_declared_version_is_not_already_published():
    version = _declared_version()
    present = _on_the_index(version)

    if present is None:
        pytest.skip("the index did not answer; neither present nor absent")
    if not present:
        return

    changed = _changed_since("v" + version)
    if changed is None:
        pytest.fail(
            "pyproject declares %s and the index already serves it, but the tag "
            "v%s is not in this checkout, so whether the package moved since "
            "cannot be told. Fetch the tags: the version job checks out with "
            "fetch-depth 0 for this reason." % (version, version))

    moved = _shipped(changed)
    assert not moved, (
        "pyproject declares %s, the index already serves it, and %d file(s) "
        "that go into the wheel changed since v%s: %s. A release from here "
        "publishes nothing: publish.yml sees the version, reports 'already on "
        "the index. No-op, not a failure', and everything below it is skipped. "
        "Bump the version." % (version, len(moved), version, ", ".join(moved[:8])))


def test_the_check_can_tell_a_taken_version_from_a_free_one():
    """⛔ The known-bad input, run against the live index rather than a mock.

    A check that has only ever said "free" is not a check.

    ⛔ AND THE POSITIVE CASE USED TO BE OUR OWN `0.1.0`, ON THE REASONING THAT
    IT "was published and is not coming back". On 2026-09-23 the index answered
    404 for this project and the instrument's only positive case went red for a
    reason that had nothing to do with the instrument.

    ⛔ THAT 404 WAS THE DELETION, which for a few hours was taken for a
    transient: the owner deleted the old distribution that day to free the new
    name, and it propagated unevenly. The change below stands whichever it was,
    which is why it survived both readings: a gate that proves itself against ONE
    release of ONE project fails whenever that project is unreachable, whether
    the cause is a deletion or a bad minute at the index. What it needs is
    something that cannot be absent without the package being uninstallable.

    ⛔ THEN IT ASKED ABOUT A VERSION THAT WAS INSTALLED, and that was right
    about where published versions come from and wrong about where this test
    runs: the `version` CI job installs `pytest` and nothing else, so the
    metadata lookup raised `PackageNotFoundError` and the gate went red on its
    own instrument. One stale assumption replaced by an assumption about the
    environment.

    It now asks about the DECLARED dependency floors, which need nothing
    installed and are read from `pyproject.toml`. Every one of them is a version
    somebody published, the first the index confirms is the one that counts, and
    no single project's disappearance can turn this gate red by itself. The
    negative case stays ours, because a version far past anything real is free
    whether or not the project exists.
    """
    floors = _declared_floors()
    assert floors, (
        "no dependency declares a three-part floor, so the positive case has "
        "nothing to ask the index about and this check cannot prove itself")

    answers = []
    for project, version in floors:
        answers.append(_on_the_index(version, project=project))
        if answers[-1] is True:
            break
    taken = True if any(a is True for a in answers) else (
        None if all(a is None for a in answers) else False)
    free = _on_the_index("99.99.99")

    if taken is None or free is None:
        pytest.skip("the index did not answer; neither present nor absent")

    assert taken is True, "the check cannot see a version that IS published"
    assert free is False, "the check calls an unpublished version taken"


def test_the_check_can_tell_a_shipped_change_from_one_that_does_not_ship():
    """⛔ The known-bad for the diff half, with no repository involved.

    The ledger, the changelog, a test, a workflow and a doc must not count. A
    file under the package and `pyproject.toml` must. And a sibling of the
    package whose name merely starts the same way must not.
    """
    package = _shipped_roots()[0]
    quiet = [
        "PUBLISHED.json", "CHANGELOG.md", "README.md", "docs/index.md",
        "tests/test_version_is_not_taken.py", ".github/workflows/ci.yml",
        package.rstrip("/") + "_notes.md",
    ]
    loud = [package + "__init__.py", package + "deep/inside.py", "pyproject.toml"]

    assert _shipped(quiet) == []
    assert _shipped(quiet + loud) == loud


def test_the_diff_half_sees_a_release_that_did_move_the_package():
    """The live known-bad: from the previous release's tag to here the package
    moved, so the shipped set is non-empty. Skipped, not passed, when the tag
    is not in this clone."""
    changed = _changed_since(PREVIOUS_RELEASE_TAG)
    if changed is None:
        pytest.skip("%s is not in this checkout" % PREVIOUS_RELEASE_TAG)
    assert _shipped(changed), (
        "no shipped file differs from %s, so the diff half sees nothing"
        % PREVIOUS_RELEASE_TAG)
