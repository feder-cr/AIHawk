"""What version the code being imported actually is.

⛔ AN INSTALL RECORD IS NOT A DESCRIPTION OF THE CODE, AND FOR AN EDITABLE
INSTALL IT STOPS BEING ONE THE MOMENT SOMEBODY PULLS. `importlib.metadata`
answers about the DISTRIBUTION the installer put there. For a wheel that is the
same artifact as the code, so the number is right and there is nothing truer to
read. For `pip install -e` the metadata is written once and the code keeps
moving, and nothing says the two have parted.

Measured on the machine this is developed on: the record said 0.54.0 while the
tree it points at said 0.68.8, fourteen patch releases apart, and the tree was
fully up to date at the time - pulling does not touch the record, which is what
makes this a defect in the code rather than a stale checkout.

⛔ AND THE NUMBER WAS BEING ADVERTISED. `mcp/server.py` sets the `initialize`
handshake's `serverInfo.version` from it, under a comment saying the field
exists so a client can "correlate a defect with a release"; the interface puts
the same number in the `build` field it serves. That handshake had already been
wrong once, advertising the MCP SDK's version for every build of this package,
and the remedy replaced it with a number that is also not ours in the install
mode the maintainers use every day.

⛔ A TEST HELD IT IN PLACE, AND THE WAY IT DID IS THE LESSON. It asserted that
the string `importlib.metadata` appeared in the source: a MECHANISM standing in
for the property that was actually wanted, which is `derived, never typed`. The
mechanism was the wrong one, so the test pinned the defect. This module answers
the property instead, and its test asserts the property.

The version of the code is:

  - a normal install: the install record, because the metadata and the code
    came out of the same build;
  - an editable install: the version the SOURCE TREE declares, because that is
    the code that will run, plus a `+editable` local segment (PEP 440) so it
    can never be read as the published release of the same number. An editable
    tree can carry uncommitted work, so a bare `0.68.8` would invite a bug
    report against a release that does not contain the code being run.

Which of the two an install is comes from what the installer WROTE, not from a
guess about `__file__`: PEP 610 puts `direct_url.json` beside the metadata,
carrying `dir_info.editable` and the source directory. A wheel install has no
such file at all.

The install record stays, under a name that cannot be mistaken for the version:
`pip`, `pip check` and anything reading `.dist-info` see that number, and
diagnosing the skew needs both. `invisible_core` made this same split first,
deriving its `__version__` from the seal it ships and naming the record
`__install_record_version__`; this is that decision, in the package that needed
it next.

⛔ AND `invisible_playwright` CARRIES THIS SAME READING, DELIBERATELY NOT SHARED,
SO A CORRECTION HERE IS WORTH LOOKING AT THERE. Putting it in one place would
mean `invisible_core`, and this package does not depend on the core: it would
gain one for eighty lines of standard library, on top of a package the wrapper
already pins exactly, which is a second constraint on the same distribution from
two directions. Nor is there one mechanism to unify - the core derives from an
artifact it PACKAGES, which is a different reading for a different reason. No
FACT is duplicated here: each package answers about itself. The mechanism is,
and naming the twin is the whole of what stops that from rotting.
"""
from __future__ import annotations

import json
import tomllib
from importlib.metadata import Distribution, PackageNotFoundError, distribution
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

#: What this package is called on the index, which is the dashed form: the
#: underscored one is the MODULE. `importlib.metadata` normalises the two to the
#: same distribution, so both resolve - and that is exactly why the wrong one
#: would never announce itself.
DISTRIBUTION = "invisible-playwright-mcp"

#: What a version says when there is nothing at all to read.
UNKNOWN = "0+unknown"

#: PEP 440 local segment marking a tree that is not a published artifact.
EDITABLE = "+editable"


def source_tree(dist: Distribution) -> Path | None:
    """The directory an EDITABLE install points at, or None for a normal one.

    Everything here is read from the record the installer wrote. The absence of
    `direct_url.json` is how a wheel install says it is one.
    """
    written = dist.read_text("direct_url.json")
    if not written:
        return None
    try:
        record = json.loads(written)
    except ValueError:
        return None
    if not isinstance(record, dict):
        return None
    if not (record.get("dir_info") or {}).get("editable"):
        return None
    url = record.get("url") or ""
    if not url.startswith("file:"):
        # An editable install of something fetched over the network leaves no
        # directory here to read, so the record is still the best there is.
        return None
    return Path(url2pathname(urlparse(url).path))


def declared_by(tree: Path) -> str | None:
    """The version that source tree declares, or None when it does not say one.

    `pyproject.toml` is where the version lives and the metadata is a copy of it
    taken at build time, so this goes back to the source of the copy rather than
    adding a second source. A tree declaring `dynamic = ["version"]` says
    nothing readable without running its build backend, and answering None there
    falls back to the record, which is the same answer as before this module.
    """
    try:
        parsed = tomllib.loads(
            (tree / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    declared = (parsed.get("project") or {}).get("version")
    return declared if isinstance(declared, str) and declared else None


def versions(name: str = DISTRIBUTION) -> tuple[str, str]:
    """(the version of the CODE, the version in the install record).

    The two differ exactly when the install is editable and the tree has moved
    since it was installed, which on a machine where this is developed is most
    of the time. `name` is a parameter so the behaviour can be tested against a
    real editable install of a real distribution rather than against a double.
    """
    try:
        dist = distribution(name)
    except PackageNotFoundError:
        # A checkout on `sys.path` with nothing installed: no record to be
        # stale, and no recorded tree to read.
        return UNKNOWN, ""
    record = dist.version
    tree = source_tree(dist)
    if tree is None:
        return record, record
    declared = declared_by(tree)
    if declared is None:
        return record, record
    # Marked even when the two numbers agree: an editable tree is not the
    # published artifact whatever it declares, and that is what the marker says.
    return declared + EDITABLE, record


__version__, __install_record_version__ = versions()

__all__ = ["__version__", "__install_record_version__", "versions",
           "source_tree", "declared_by", "DISTRIBUTION", "EDITABLE", "UNKNOWN"]
