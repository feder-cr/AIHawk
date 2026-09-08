#!/usr/bin/env python3
"""Render the Jekyll docs/ tree into a GitHub wiki checkout.

Usage: build_wiki.py <docs_dir> <out_dir> [--pixels <owner/repo>]

A GitHub wiki is a flat set of <Page>.md files with no Jekyll front matter and a
_Sidebar.md for navigation. This converter, for every docs/*.md:
  - strips the YAML front matter (the body already starts with the H1),
  - rewrites internal links [x](slug.md[#a]) -> [x](slug[#a]) (wiki has no .md),
  - names the page by its slug (stable URLs matching the docs site), except
    index.md -> Home.md (the wiki landing page),
  - and, with --pixels, gives the page its view counter (see
    scripts/sync_article_pixels.py for what that number is and is not).
and then generates _Sidebar.md mirroring the parent/has_children/nav_order tree.

The pixel goes into the WIKI only, never back into docs/. The wiki is the
surface that ranks and the surface readers land on; the .md in the repository
is served as a JSON payload React mounts, and a counter there would measure
almost nothing while putting markup into the source tree.

Without --pixels (a local preview) no pixel is written at all, rather than one
addressed to a guessed repository. A wiki published that way would count
nothing while looking entirely normal, so publish-wiki.yml passes the flag AND
runs `sync_article_pixels.py --check` over the output before pushing.
"""
import os, re, sys

from sync_article_pixels import pixel_tag

DOCS = sys.argv[1]
OUT = sys.argv[2]
#: `owner/repo` the pixels address, or None. Not read from the environment
#: here: the caller that knows it is the workflow, and a fallback to
#: GITHUB_REPOSITORY would make a local run behave differently depending on
#: what happens to be exported.
PIXELS = sys.argv[sys.argv.index("--pixels") + 1] if "--pixels" in sys.argv else None

def parse(path):
    t = open(path, encoding="utf-8").read()
    fm, body = {}, t
    m = re.match(r'^---\n(.*?)\n---\n?(.*)$', t, re.S)
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r'([A-Za-z_]+):\s*(.*?)\s*$', line)
            if mm:
                v = mm.group(2)
                if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                    v = v[1:-1]
                fm[mm.group(1)] = v
        body = m.group(2)
    return fm, body.lstrip("\n")

# Subdirectories are walked, not skipped. `docs/` grew `integrations/` with nine
# pages, and a converter reading only the flat level dropped all nine AND left
# every link into them pointing at a wiki page that does not exist - nine dead
# links across eight pages, invisible because the pages themselves rendered.
# A wiki is flat, so a subdirectory page is named by its own slug, except an
# `index`/`README` inside a directory, which takes the DIRECTORY's name so that
# a `](integrations/)` link has somewhere to land.
pages = {}
sources = {}
for dirpath, _dirnames, filenames in os.walk(DOCS):
    rel = os.path.relpath(dirpath, DOCS).replace(os.sep, "/")
    for f in sorted(filenames):
        if not f.endswith(".md"):
            continue
        stem = f[:-3]
        if rel == ".":
            slug = stem
            src = stem
        elif stem in ("index", "README"):
            slug = rel.split("/")[-1]
            src = rel
        else:
            slug = stem
            src = rel + "/" + stem
        if slug in pages:
            raise SystemExit(
                "two docs pages want the same flat wiki name %r: %s and %s. "
                "A wiki has no directories, so this has to be resolved in "
                "docs/ rather than silently letting one overwrite the other."
                % (slug, sources[slug], src))
        pages[slug] = parse(os.path.join(dirpath, f))
        sources[slug] = src

valid = set(pages.keys())
#: Every way a doc page can be addressed from another one, mapped to its flat
#: wiki name: bare slug, `dir/slug`, either with `.md`, and `dir/` on its own.
addressable = {src: slug for slug, src in sources.items()}
for slug, src in sources.items():
    if "/" in src:
        addressable.setdefault(src.split("/")[-1], slug)
# `dir/` on its own is how a page links to a directory index, and it needs the
# trailing form for EVERY source, not only the ones that already carry a slash:
# `integrations/README.md` has the source `integrations`, so the first cut of
# this left `](integrations/)` as the single dead link out of 325 pages.
for src in list(addressable):
    addressable.setdefault(src + "/", addressable[src])

def rewrite(body):
    def repl(m):
        target, anchor = m.group(1), (m.group(2) or "")
        hit = addressable.get(target) or (target if target in valid else None)
        if hit:
            return "](" + ("Home" if hit == "index" else hit) + anchor + ")"
        return m.group(0)
    # `[a-z0-9/-]` and an optional `.md`: a link into a subdirectory carries the
    # slash and may or may not carry the extension, and the first version of
    # this pattern matched neither.
    return re.sub(r'\]\(([a-z0-9/\-]+)(?:\.md)?(#[A-Za-z0-9\-]+)?\)', repl, body)

def with_pixel(name, body):
    """Put the page's view counter just under its H1.

    Under and not above: the H1 is what the reader and every renderer expect
    first, and a wiki page whose source starts with an <img> renders an empty
    first line in some previews. Every page in both corpora starts with an H1
    once the front matter is off - measured, 524 of 524 - so this is a uniform
    position rather than a heuristic, and a page that ever stops starting with
    one gets its pixel appended instead of silently misplaced.
    """
    if not PIXELS:
        return body
    tag = pixel_tag(PIXELS, name)
    lines = body.split("\n")
    if lines and lines[0].startswith("# "):
        return "\n".join([lines[0], "", tag] + lines[1:])
    return body.rstrip("\n") + "\n\n" + tag


os.makedirs(OUT, exist_ok=True)
written = 0
for slug, (fm, body) in pages.items():
    name = "Home" if slug == "index" else slug
    open(os.path.join(OUT, name + ".md"), "w", encoding="utf-8", newline="\n").write(
        with_pixel(name, rewrite(body)) + "\n")
    written += 1

def title_of(slug):
    return pages[slug][0].get("title", slug)

def link(slug):
    return "[%s](%s)" % (title_of(slug), "Home" if slug == "index" else slug)

def children_of(group_title):
    kids = [(s, fm) for s, (fm, b) in pages.items() if fm.get("parent") == group_title]
    kids.sort(key=lambda x: int(x[1].get("nav_order", "999")))
    return kids

toplevel = [(s, fm) for s, (fm, b) in pages.items() if not fm.get("parent") and s != "index"]
toplevel.sort(key=lambda x: int(x[1].get("nav_order", "999")))

lines = ["### " + link("index"), ""]
for slug, fm in toplevel:
    t = title_of(slug)
    # The group header is a page too: bold AND a link, so the three hub pages
    # are reachable from every wiki page instead of being named and unlinked.
    lines.append("**%s**" % link(slug))
    for cs, cfm in children_of(t):
        if cfm.get("has_children") == "true":
            lines.append("- %s" % link(cs))
            for gs, gfm in children_of(cfm.get("title", cs)):
                lines.append("  - %s" % link(gs))
        else:
            lines.append("- %s" % link(cs))
    lines.append("")
open(os.path.join(OUT, "_Sidebar.md"), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

print("wrote %d pages + _Sidebar.md to %s" % (written, OUT))
