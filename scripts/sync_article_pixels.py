#!/usr/bin/env python3
"""One view pixel per wiki page, and the release that holds them.

A GitHub wiki serves no per-page analytics. The repository traffic API reports
the ten most visited paths over fourteen days and nothing below that, so a
corpus of hundreds of wiki pages is invisible by construction: measured on this
repository, the whole wiki index sits at about thirty views per fortnight and
not one individual page reaches the top ten.

This gives every page a counter of its own, by the same mechanism the browser
launch counter has used since May: a release asset whose `download_count` is
incremented by GitHub on every fetch. Each wiki page embeds its own asset as a
1x1 transparent image, so one page view is one fetch is one count. The assets
live in a release tagged `article-views`, which is not a software release and
is created with `make_latest=false` so it never becomes the repository's
"Latest".

What the number is, said once so nobody reads it as more than it is:

  * It counts FETCHES, not people. A reader who opens a page twice counts
    twice, and there is no unique-visitor figure anywhere in it.
  * It counts every client that loads images, crawlers included. Image
    indexers and link unfurlers fetch it exactly like a browser does. At the
    per-page volumes above, that share is not small.
  * It undercounts readers who block images or read the page through a proxy
    that strips them.

It is a floor with noise on top, and it is the only per-page signal available.
GitHub's own `traffic/popular/paths` is the independent instrument that can
corroborate it: a page the pixel calls the most read should, eventually, show
up in that top ten.

Usage:

    python scripts/sync_article_pixels.py --repo owner/name wiki_build
    python scripts/sync_article_pixels.py --repo owner/name --check wiki_build
    python scripts/sync_article_pixels.py --selftest

`--check` is the gate: it refuses unless every built page carries exactly one
pixel, addressed to this repository and naming that page. It exists because
the injection happens in `build_wiki.py`, which falls back to no pixel at all
when it is not told which repository it is building for - and a wiki published
without pixels counts nothing while looking perfectly normal.

The sync NEVER deletes an asset. A page removed from `docs/` keeps its history,
and a renamed slug gets a new asset rather than inheriting the old one's count,
which is the truth: the wiki has no redirects, so a renamed page is a new URL.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path

#: The release that holds the pixels. Not a software release: `publish.yml`
#: reads `v*` tags and never looks at this one.
TAG = "article-views"

#: GitHub allows 1000 assets on a single release. Refusing well short of that
#: leaves room to notice and split into a second release, rather than finding
#: out from a failed upload on the day a page is published.
MAX_ASSETS = 1000
REFUSE_ABOVE = 950

#: `_Sidebar.md` is navigation injected into every page, not a page. A pixel
#: there would fire on every view of every page and drown its own signal.
NOT_A_PAGE = {"_Sidebar", "_Footer", "_Header"}

#: Any pixel, whichever repository or page it names. The check needs to see a
#: WRONG pixel, not only a missing one, so it matches the shape and compares
#: the parts afterwards.
PIXEL_RE = re.compile(
    r'<img src="https://github\.com/([^/"]+/[^/"]+)/releases/download/'
    + TAG + r'/([^"/]+)\.png" width="1" height="1" alt="">')


def pixel_bytes() -> bytes:
    """A 1x1 fully transparent PNG, built here rather than committed.

    68 bytes, and no image library on the runner. Transparent so it cannot
    show through any theme, and a real PNG so a browser that sniffs content
    types is not handed a text file with an image extension.
    """
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)   # 1x1, 8-bit RGBA
    idat = zlib.compress(b"\x00" + b"\x00\x00\x00\x00")   # one filtered row
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def pixel_tag(repo: str, page: str) -> str:
    """The exact markup a page carries.

    ONE definition, imported by `build_wiki.py` which writes it and by the
    check below which verifies it. Two copies of this string would agree today
    and drift the first time either side is edited, and the failure would be a
    wiki that silently stops counting.

    `alt=""` marks it decorative, so a screen reader skips it and a broken
    fetch leaves nothing visible. GitHub renders images from `github.com`
    directly rather than through its camo proxy, so the reader's browser asks
    GitHub for this asset and GitHub counts the request.
    """
    return ('<img src="https://github.com/%s/releases/download/%s/%s.png"'
            ' width="1" height="1" alt="">' % (repo, TAG, page))


def page_names(wiki_dir: str | Path) -> list[str]:
    """The built wiki pages that get a pixel, by page name (no extension)."""
    return sorted(p.stem for p in Path(wiki_dir).glob("*.md")
                  if p.stem not in NOT_A_PAGE)


def check(wiki_dir: str | Path, repo: str) -> list[str]:
    """Every page carries exactly one pixel, for THIS repo and THIS page."""
    problems = []
    for p in sorted(Path(wiki_dir).glob("*.md")):
        found = PIXEL_RE.findall(p.read_text(encoding="utf-8"))
        if p.stem in NOT_A_PAGE:
            if found:
                problems.append("%s is not a page and carries a pixel" % p.name)
            continue
        if not found:
            problems.append("%s carries no pixel" % p.name)
        elif len(found) > 1:
            problems.append("%s carries %d pixels" % (p.name, len(found)))
        else:
            got_repo, got_page = found[0]
            if got_repo != repo:
                problems.append("%s points at %s, not %s"
                                % (p.name, got_repo, repo))
            if got_page != p.stem:
                problems.append("%s carries the pixel of %s"
                                % (p.name, got_page))
    return problems


def _api(url: str, token: str, data: bytes | None = None,
         ctype: str = "application/json", method: str | None = None,
         tries: int = 5, sleep=time.sleep):
    """One API call, with the secondary rate limit handled rather than met.

    The first run on an existing corpus uploads one asset per page - 463 on
    the engine - and GitHub throttles bursts of content-creating requests with
    a 403 or 429 carrying `Retry-After`. Without this the first run is the one
    that fails, and it fails BEFORE the wiki push, so a hiccup here would block
    the publish entirely. Honouring the header is also what rule 11 asks for
    everywhere else this project talks to GitHub.

    A 404 is raised, not retried: `release()` reads one to decide the release
    has to be created.
    """
    for attempt in range(tries):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + token)
        req.add_header("Accept", "application/vnd.github+json")
        if data is not None:
            req.add_header("Content-Type", ctype)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last_try = attempt == tries - 1
            if e.code not in (403, 429, 500, 502, 503) or last_try:
                raise
            wait = e.headers.get("Retry-After")
            wait = int(wait) if wait and wait.isdigit() else 2 ** attempt
            print("[pixels] %s from GitHub, waiting %ds (attempt %d of %d)"
                  % (e.code, wait, attempt + 1, tries), file=sys.stderr)
            sleep(wait)


def release(repo: str, token: str) -> dict:
    """The pixel release, created on first use."""
    try:
        return _api("https://api.github.com/repos/%s/releases/tags/%s"
                    % (repo, TAG), token)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    body = ("One tiny image per wiki page. The download count of each asset is"
            " how many times that page was viewed. This is not a software"
            " release: see scripts/sync_article_pixels.py.")
    return _api("https://api.github.com/repos/%s/releases" % repo, token,
                json.dumps({"tag_name": TAG, "name": "Article views",
                            "body": body, "draft": False, "prerelease": False,
                            "make_latest": "false"}).encode(), method="POST")


def existing_assets(repo: str, rel_id: int, token: str) -> dict[str, int]:
    """Asset name -> download count, ALL of them.

    Paginated deliberately. The assets embedded in a release object are capped
    by the API, so reading them from there would silently report a corpus of
    hundreds of pages as a few dozen, and the sync would re-upload assets that
    already exist (which fails) or the reader would lose pages (which is
    worse, because it looks like zero views).
    """
    out: dict[str, int] = {}
    page = 1
    while True:
        batch = _api("https://api.github.com/repos/%s/releases/%d/assets"
                     "?per_page=100&page=%d" % (repo, rel_id, page), token)
        if not batch:
            return out
        for a in batch:
            out[a["name"]] = a["download_count"]
        page += 1


def sync(wiki_dir: str | Path, repo: str, token: str) -> int:
    pages = page_names(wiki_dir)
    rel = release(repo, token)
    have = existing_assets(repo, rel["id"], token)
    missing = [p for p in pages if p + ".png" not in have]
    total = len(have) + len(missing)
    if total > REFUSE_ABOVE:
        print("[pixels] REFUSING: %d assets would be on one release, and"
              " GitHub allows %d. Split the corpus across a second release"
              " before publishing more pages." % (total, MAX_ASSETS),
              file=sys.stderr)
        return 1
    if not missing:
        print("[pixels] %d pages, all already have an asset" % len(pages))
        return 0
    png = pixel_bytes()
    upload = rel["upload_url"].split("{")[0]
    for i, name in enumerate(missing, 1):
        _api("%s?name=%s.png" % (upload, name), token, png, "image/png", "POST")
        # Paced, not raced. A tenth of a second puts the whole first run under
        # a minute of added wall clock and keeps a 463-asset burst well inside
        # what GitHub serves without throttling; the retry above is what
        # catches it if this is not enough.
        if i % 50 == 0:
            print("[pixels] uploaded %d of %d" % (i, len(missing)))
        time.sleep(0.1)
    print("[pixels] %d pages, uploaded %d new asset(s): %s"
          % (len(pages), len(missing), ", ".join(missing[:10])
             + (" ..." if len(missing) > 10 else "")))
    return 0


def selftest() -> int:
    """Known-bad inputs. A check that has only ever passed is not a check."""
    import tempfile
    repo = "feder-cr/invisible_playwright"
    good = pixel_tag(repo, "a-page")
    cases = [
        ("a page with its own pixel passes",
         {"a-page.md": "# T\n\n" + good + "\n"}, 0),
        ("a page with no pixel fails",
         {"a-page.md": "# T\n\nbody\n"}, 1),
        ("a pixel for another repo fails",
         {"a-page.md": "# T\n\n" + pixel_tag("feder-cr/AIHawk", "a-page")}, 1),
        ("a pixel naming another page fails",
         {"a-page.md": "# T\n\n" + pixel_tag(repo, "other-page")}, 1),
        ("two pixels on one page fail",
         {"a-page.md": "# T\n\n" + good + "\n" + good}, 1),
        ("the sidebar without a pixel passes",
         {"a-page.md": "# T\n\n" + good, "_Sidebar.md": "### nav\n"}, 0),
        ("the sidebar WITH a pixel fails",
         {"a-page.md": "# T\n\n" + good,
          "_Sidebar.md": pixel_tag(repo, "_Sidebar")}, 1),
    ]
    bad = []
    for label, files, expected in cases:
        with tempfile.TemporaryDirectory() as d:
            for n, t in files.items():
                (Path(d) / n).write_text(t, encoding="utf-8")
            got = len(check(d, repo))
        ok = (got > 0) == (expected > 0)
        print("  %s  %s" % ("OK" if ok else "KO", label))
        if not ok:
            bad.append(label)

    with tempfile.TemporaryDirectory() as d:
        for n in ("one.md", "two.md", "_Sidebar.md", "notes.txt"):
            (Path(d) / n).write_text("x", encoding="utf-8")
        names = page_names(d)

    # The retry, against a server that throttles. Without these three cases the
    # backoff would be code that has never once run: the path only opens on a
    # 403 from a burst, which is exactly the run nobody gets to rehearse.
    import io
    real_urlopen = urllib.request.urlopen

    class _Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def _fake_opener(sequence):
        left = list(sequence)
        def opener(req, timeout=None):
            outcome = left.pop(0)
            if outcome is None:
                return _Resp(b'{"ok": true}')
            raise urllib.error.HTTPError(req.full_url, outcome, "throttled",
                                         {"Retry-After": "1"}, None)
        return opener

    slept = []
    api_cases = []
    for label, sequence, must_raise in (
            ("a 403 with Retry-After is retried and then passes", [403, None], False),
            ("a 429 is retried", [429, 429, None], False),
            ("a 404 is NOT retried: it is how a missing release is found",
             [404], True),
            ("the attempts run out and the error comes through", [403, 403, 403], True),
    ):
        urllib.request.urlopen = _fake_opener(sequence)
        try:
            _api("https://example.invalid/x", "t", tries=3,
                 sleep=lambda s: slept.append(s))
            raised = False
        except urllib.error.HTTPError:
            raised = True
        finally:
            urllib.request.urlopen = real_urlopen
        api_cases.append((label, raised == must_raise))
    api_cases.append(("l'wait viene dall'header Retry-After",
                      slept and all(s == 1 for s in slept)))
    for label, ok in api_cases:
        print("  %s  %s" % ("OK" if ok else "KO", label))
        if not ok:
            bad.append(label)

    png = pixel_bytes()
    extra = (
        ("the pixel is a PNG", png.startswith(b"\x89PNG\r\n\x1a\n")),
        ("the pixel is 1x1", struct.unpack(">II", png[16:24]) == (1, 1)),
        ("the pixel has an alpha channel", png[25] == 6),
        ("page_names lists the pages", names == ["one", "two"]),
    )
    for label, ok in extra:
        print("  %s  %s" % ("OK" if ok else "KO", label))
        if not ok:
            bad.append(label)
    print("selftest: %d cases, %d broken"
          % (len(cases) + len(extra) + len(api_cases), len(bad)))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("wiki_dir", nargs="?")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.wiki_dir or not a.repo:
        ap.error("a wiki directory and --repo (or GITHUB_REPOSITORY) are needed")
    if a.check:
        problems = check(a.wiki_dir, a.repo)
        for p in problems:
            print("[pixels] " + p, file=sys.stderr)
        print("[pixels] checked %d pages, %d problem(s)"
              % (len(page_names(a.wiki_dir)), len(problems)))
        return 1 if problems else 0
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("[pixels] no GITHUB_TOKEN", file=sys.stderr)
        return 1
    return sync(a.wiki_dir, a.repo, token)


if __name__ == "__main__":
    raise SystemExit(main())
