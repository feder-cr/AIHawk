"""This repository is public and English-only. This gate says so mechanically.

Why it exists, and it is not a style preference. On 2026-08-27 a whole new
subsystem - the `_juggler` client, its three generator scripts and its four
test files, about four thousand lines - was written in ITALIAN and committed
here: module names, class names, public method names, every comment. Nothing
caught it. The repo had been English since its first commit, `pytest` was green
throughout, and the pre-push hook had no opinion about the language a file is
written in.

A convention that lives only in the heads of the people writing the code is not
a convention, it is a habit, and a habit skips a session. It is the same lesson
this project already wrote down for gates: an invariant nobody can check is an
invariant that drifts.

    python scripts/check_english_only.py                # 1 if Italian is found
    python scripts/check_english_only.py --range A..B   # only what a push adds
    python scripts/check_english_only.py --selftest     # 9 mutations, 9 that must not fire

WHAT IT DOES NOT DO, said out loud because a gate whose limits are unstated
gets trusted too far. It does not detect Spanish, French or Portuguese. It does
not judge prose quality. It cannot see a single Italian noun with no Italian
function word near it: `def calcola(x)` on its own passes. What it catches is
Italian PROSE, which is what comments and docstrings are made of, and prose is
what actually happened.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Italian function words that are not English words, not Python keywords and
#: not plausible identifiers. ⛔ The list is deliberately CONSERVATIVE: every
#: entry was checked against this repo's existing English files, which must stay
#: silent. Words left OUT on purpose, with the reason, because the temptation to
#: add them will come back:
#:
#:   `del`   - a Python keyword.
#:   `in`, `a`, `di`, `da`, `no`, `se`, `si`, `e`, `o` - too short, and several
#:             are English words or ordinary variable names.
#:   `come`  - too easy to reach as a fragment of English prose.
#:   `solo`  - an English word.
#:   `la`, `le`, `il`, `lo`, `un` - one- and two-letter variable names.
#:
#: What is left is prose glue. If two of these appear in one file, that file is
#: not written in English.
ITALIAN = (
    "perche", "quindi", "questo", "questa", "queste", "questi", "quello",
    "quella", "quelle", "quelli", "della", "delle", "degli", "dello",
    "nella", "nelle", "negli", "dalla", "dalle", "dagli", "sulla", "sulle",
    "alla", "alle", "agli", "sono", "essere", "viene", "vengono", "invece",
    "anche", "senza", "ogni", "tutto", "tutti", "tutta", "tutte", "cosa",
    "dove", "quando", "sempre", "cioe", "piu", "gia", "adesso", "allora",
    "prima", "dopo", "sotto", "sopra", "dentro", "fuori", "verso",
    "niente", "nessuno", "nessuna", "qualcosa", "qualcuno", "molto",
    "poco", "troppo", "abbastanza", "soltanto", "oppure", "mentre",
    "finche", "affinche", "benche", "sebbene", "poiche", "siccome",
    "quale", "quali", "chiunque", "ovunque", "comunque", "dunque",
    "infatti", "inoltre", "tuttavia", "eppure", "ancora", "appena",
    "subito", "spesso", "raramente", "davvero", "proprio", "stesso",
    "stessa", "stesse", "stessi", "altro", "altra", "altre", "altri",
)

#: ⛔ TWO distinct words, not one occurrence. One is how a false positive is
#: born: a proper noun, a quoted string, a URL, a vendor name.
THRESHOLD = 2

#: What this gate does not own, and why each entry is here.
#:
#: ⛔ THE LAST ONE IS A SELF-EXEMPTION AND HAS TO BE JUSTIFIED, not hidden. This
#: file carries its own known-bad corpus: the mutations below ARE Italian prose,
#: because a gate that has only ever printed PASS is not a gate. The corpus has
#: to live somewhere, and the honest place is next to the check that uses it.
#: The exemption is exactly one path - never a prefix - and a must-not-fire case
#: at the bottom asserts that a sibling script is still covered.
EXCLUDED = (
    "src/invisible_playwright/_pw/",          # vendored upstream Playwright
    "src/invisible_playwright/_driver/",      # vendored Node driver bundle
    "src/invisible_playwright/_juggler/injected.js",   # extracted from the bundle
    "scripts/check_english_only.py",          # this file: the known-bad corpus
    # ⛔ `test_fork.py` carries Italian ON PURPOSE and it cannot be
    # translated: its known-bad fixture reproduces the JavaScript comment
    # that broke the driver bundle on 2026-08-24, and the defect IS the
    # trailing apostrophe of the Italian word `piu'`, which closes the
    # single-quoted string it sits in. Translate it and the mutation stops
    # reproducing the bug. Named file by file, never by folder.
    "tests/test_fork.py",
)

EXTENSIONS = (".py", ".md", ".toml", ".cfg", ".yml", ".yaml")


def italian_words(text: str) -> set:
    """The Italian function words present, as a set."""
    lowered = text.lower()
    return {w for w in ITALIAN
            if re.search(r"(?<![a-z0-9_])%s(?![a-z0-9_])" % w, lowered)}


#: The marker our patches carry inside vendored files.
#: ⛔ VENDORED IS NOT A BLANKET EXEMPTION, and this is the hole the first
#: version of this gate had. `_pw/` and `_driver/` are upstream code we do not
#: own, so scanning them whole would be noise - but they contain OUR patches,
#: and on 2026-08-27 seven of those blocks were in Italian and completely
#: invisible here: `_playwright.py`, `_driver.py`, `__main__.py` and four
#: blocks inside the two `_generated.py`. The exclusion is by FOLDER; what is
#: ours is identified by this marker, so inside an excluded path the gate reads
#: the marked blocks and nothing else.
OUR_MARKER = "MODIFIED by invisible_playwright"

#: ⛔ A PATCH BLOCK IS THE CONTIGUOUS RUN OF COMMENT LINES AROUND THE MARKER,
#: never a fixed number of lines. A fixed span was tried first and is wrong in
#: both directions: too small it truncates the 41-line block in `_driver.py`,
#: too large it reaches past a one-line comment into somebody else's code and
#: reports their words as ours. Measured with span 44: two files were flagged
#: for Italian that sat in upstream code below the patch.
COMMENT_STARTS = ("//", "#")
MAX_BLOCK = 80

#: ⛔ A LINE IS NOT A UNIT IN A BUNDLED FILE, and reading it as one made this
#: gate useless the first time it saw `coreBundle.js`: that file has lines of
#: 320.820 characters, because the injected sources are single-quoted strings
#: with their newlines written as two characters. Taking "16 lines after the
#: marker" there swallowed the entire injected script, so the gate reported
#: Italian that belonged to upstream code hundreds of kilobytes away from any
#: patch of ours. Above this width a line is scanned by CHARACTER window
#: instead.
LONG_LINE = 2000

#: How much of a long line belongs to one comment, and where it stops. The
#: literal two-character `\n` is the real line break inside those strings.
WINDOW = 700
BEFORE = 200
NL_LITERAL = chr(92) + "n"


def our_blocks(text: str) -> str:
    """Only the parts of a vendored file that OUR patches wrote."""
    lines = text.splitlines()
    kept: list = []
    for i, line in enumerate(lines):
        if OUR_MARKER not in line:
            continue
        if len(line) <= LONG_LINE:
            start = i
            while (start > 0
                   and lines[start - 1].strip().startswith(COMMENT_STARTS)
                   and i - start < MAX_BLOCK):
                start -= 1
            end = i
            while (end + 1 < len(lines)
                   and lines[end + 1].strip().startswith(COMMENT_STARTS)
                   and end - i < MAX_BLOCK):
                end += 1
            kept.extend(lines[start:end + 1])
            continue
        pos = 0
        while True:
            j = line.find(OUR_MARKER, pos)
            if j < 0:
                break
            end = line.find(NL_LITERAL, j)
            if not 0 < end - j < WINDOW:
                end = j + WINDOW
            kept.append(line[max(0, j - BEFORE):end])
            pos = j + 1
    return "\n".join(kept)


def inspect(path: str, text: str) -> tuple:
    """(is_italian, words) for one file.

    A pure function on (path, text): the selftest mutates here and never
    touches the disk, which is what makes the mutations cost nothing to run.
    """
    normalised = path.replace(chr(92), "/")
    if normalised in EXCLUDED:
        return (False, set())
    if any(e.endswith("/") and normalised.startswith(e) for e in EXCLUDED):
        # ⛔ Excluded as a FOLDER, but our own patches inside it are still ours.
        found = italian_words(our_blocks(text))
        return (len(found) >= THRESHOLD, found)
    if not normalised.endswith(EXTENSIONS):
        return (False, set())
    found = italian_words(text)
    return (len(found) >= THRESHOLD, found)


def tracked(rev_range=None) -> list:
    """The files to look at: everything tracked, or only what a range touches."""
    if rev_range:
        r = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=d", rev_range],
            cwd=ROOT, capture_output=True, text=True)
    else:
        r = subprocess.run(["git", "ls-files"], cwd=ROOT,
                           capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("git refused: %s" % r.stderr.strip()[:200])
    return [x for x in r.stdout.splitlines() if x.strip()]


def scan(paths) -> list:
    guilty = []
    for path in paths:
        f = ROOT / path
        if not f.exists():
            continue
        try:
            text = f.read_bytes().decode("utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        is_italian, found = inspect(path, text)
        if is_italian:
            guilty.append((path, sorted(found)))
    return guilty


# ── the selftest ────────────────────────────────────────────────────────────
def selftest() -> int:
    # ⛔ The known-bad corpus. It is Italian on purpose, and it is the reason
    # this file exempts itself above.
    ITA = ("# Questo commento e' scritto in italiano perche' nessuno "
           "controllava.\ndef f():\n    return 1\n")
    ENG = ("# This comment is in English, which is what the repo uses.\n"
           "def f():\n    return 1\n")
    bad = 0

    def expect(name, path, text, should_fire):
        nonlocal bad
        is_italian, found = inspect(path, text)
        if is_italian != should_fire:
            print("  %s: %s (words seen: %s)"
                  % ("SURVIVED" if should_fire else "FALSE POSITIVE",
                     name, sorted(found) or "none"))
            bad += 1
        else:
            print("  %s: %s" % ("killed" if should_fire else "silent", name))

    print("--- mutations that MUST fire ---")
    expect("an Italian comment in a .py", "src/x.py", ITA, True)
    expect("an Italian document", "README.md", ITA, True)
    expect("Italian inside a docstring", "src/x.py",
           'def f():\n    """Questo fa qualcosa, quindi serve."""\n', True)
    expect("Italian in a config file", "pyproject.toml",
           "# Questo pacchetto, quindi, dipende da\nname = 'x'\n", True)
    # ⛔ The real case: names translated, comments not. That is what a
    # half-finished translation looks like, and it is the likeliest way to
    # get this wrong a second time.
    expect("English names, Italian comments", "src/x.py",
           "def click(selector):\n"
           "    # Prima si risolve, poi si guarda dove sta, quindi si clicca.\n"
           "    return selector\n", True)
    expect("an Italian test", "tests/test_x.py",
           "def test_questo_funziona():\n"
           "    # Questo controlla che tutto sia a posto, quindi basta.\n"
           "    assert True\n", True)
    expect("Italian in a sibling script", "scripts/gen_x.py", ITA, True)
    expect("Italian in a workflow", ".github/workflows/ci.yml",
           "# Questo lavoro gira sempre, quindi non si salta.\nname: ci\n", True)

    # ⛔ The hole this gate had until 2026-08-27: `_pw/` is excluded as a
    # folder, and our own patches inside it went unread. Seven blocks were in
    # Italian, one of them in `_playwright.py`, which every user imports.
    OUR_ITA = "\n".join([
        "def upstream(self):",
        "    # MODIFIED by invisible_playwright: chromium e webkit non",
        "    # esistono piu' in questo fork, quindi il messaggio lo dice",
        "    # invece di lasciare un AttributeError.",
        "    raise ValueError('x')",
    ]) + "\n"
    expect("OUR patch inside a vendored file",
           "src/invisible_playwright/_pw/_impl/_playwright.py",
           OUR_ITA, True)

    print("--- cases that must NOT fire ---")
    expect("ordinary English", "src/x.py", ENG, False)
    # ⛔ One word is not prose, and this is the line that keeps false positives
    # out: a proper noun, a quoted string, a URL.
    expect("a single Italian word (a name, a quotation)", "src/x.py",
           "# The vendor is called Sempre, which is a name and not a sentence.\n",
           False)
    expect("vendored Playwright is not ours",
           "src/invisible_playwright/_pw/_impl/_page.py", ITA, False)
    expect("the vendored driver is not ours",
           "src/invisible_playwright/_driver/package/lib/x.py", ITA, False)
    # ⛔ But OUR patch inside a vendored file IS ours. Without this the gate
    # had a hole seven blocks wide, and the biggest of them sat in a file every
    # user imports.
    # ⛔ A minified line is not a unit: 320.820 characters of upstream code
    # around one patch of ours must not be read as part of it. Without the
    # character window this fired on `coreBundle.js` for Italian that belonged
    # to nobody.
    MINIFIED = ("var a=1;" + ("x" * 3000)
                + " // questo e' upstream, quindi non si guarda affatto "
                + ("y" * 3000)
                + " // MODIFIED by invisible_playwright: nothing to see here "
                + ("z" * 3000)
                + " // e anche questo e' upstream, dunque niente" + "\n")
    expect("a minified line around our patch",
           "src/invisible_playwright/_driver/package/lib/coreBundle.js",
           MINIFIED, False)
    expect("upstream code around our patch stays invisible",
           "src/invisible_playwright/_pw/_impl/_page.py",
           "\n".join(["# questo e' upstream, quindi non lo guardiamo affatto",
                      "def upstream_thing():",
                      "    return 1"]) + "\n", False)
    expect("a binary has no language", "assets/logo.png", ITA, False)
    # ⛔ The self-exemption must be ONE PATH, never a prefix: a prefix would
    # quietly stop covering every other script in the folder.
    expect("this file, which carries the corpus",
           "scripts/check_english_only.py", ITA, False)

    # ⛔ And the check that is worth more than all the others: the gate must be
    # SILENT on this repository as it stands. A gate born red on what already
    # exists teaches people to bypass it, and this project has written that
    # down twice.
    print("--- the real repository ---")
    try:
        noisy = scan(tracked())
        if noisy:
            print("  %d files are still in Italian:" % len(noisy))
            for path, found in noisy[:12]:
                print("      %-58s %s" % (path, ", ".join(found[:4])))
            if len(noisy) > 12:
                print("      ... and %d more" % (len(noisy) - 12))
            bad += 1
        else:
            print("  silent: no tracked file is in Italian")
    except RuntimeError as failure:
        print("  not verifiable (%s)" % failure)

    print()
    print("selftest: %s" % ("ALL GOOD" if not bad else "%d PROBLEMS" % bad))
    return 1 if bad else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--range", dest="rev_range",
                   help="only the files a range touches, e.g. origin/main..HEAD")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        return selftest()

    guilty = scan(tracked(a.rev_range))
    if not guilty:
        print("english only: clean")
        return 0
    print("%d file(s) are not in English:" % len(guilty))
    for path, found in guilty:
        print("   %-58s %s" % (path, ", ".join(found[:6])))
    print()
    print("This repository is public and English-only. Translate these files.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
