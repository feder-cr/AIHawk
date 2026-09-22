"""Every third-party module this package imports is one it declares.

⛔ A DIRECT IMPORT OF A TRANSITIVE DEPENDENCY IS A BET ON SOMEBODY ELSE'S
PYPROJECT. `src/invisible_playwright_mcp/mcp/server.py` says `from pydantic import Field` and
`pyproject.toml` did not mention pydantic at all: it arrived because `mcp`
requires it. That works until `mcp` stops requiring it, or moves to a major this
code cannot use, and then `invisible_playwright_mcp` fails at IMPORT for every user who installs
it - with a traceback that names pydantic and a cause that is nowhere near it.

Nothing could have caught it either. Every environment that has `mcp` has
pydantic, so the suite is green, the CI is green, a clean-environment check is
green, and the wheel is broken only in a future that has not happened yet. The
same is true of `httpx`, which the interface-to-real-server test imports and
which also arrives through `mcp`.

The rule is the one this repository already applies to the engine and to the
core pin, moved one layer out: use what you declare. It is not about pinning
tightly - the floors here are the lowest that are true - it is about the
declaration existing at all, so a resolver can be told and a reader can see it.

⛔ WHAT THIS DOES NOT SEE, because a green says what it checked. It reads
IMPORTS, so a dependency reached by `importlib.import_module` with a computed
name is invisible; and it says nothing about whether a floor is high enough,
which is a question only a resolver can answer. It also leaves the pytest
PLUGINS alone: `pytest-asyncio` is never imported by anything and is declared
correctly, because a plugin is loaded by pytest rather than by the code.
"""
from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"

#: Index name -> the module names that installing it provides, listed only where
#: the two differ. Everything else imports under its own name.
PROVIDES = {
    "invisible-playwright": {"invisible_playwright"},
    "python-dotenv": {"dotenv"},
}

def _ours() -> set:
    """Module names that live in this repository, so a bare import of one is not
    a third-party dependency.

    ⛔ RESOLVED FROM THE TREE, NOT LISTED. A hand-written list was the first
    version and it was already wrong on its first run: it named five helpers and
    missed `test_web_service`, which `test_the_event_stream_wire_format.py`
    imports because the suite's convention here is a bare import between test
    modules. A list of local names is a second declaration of what the directory
    already says, and it goes stale the next time somebody adds a helper.
    """
    out = {"invisible_playwright_mcp"}
    for folder in (ROOT / "tests", ROOT / "scripts"):
        if folder.is_dir():
            out |= {p.stem for p in folder.rglob("*.py")}
    return out


def _bare_name(requirement: str) -> str:
    for sep in (">=", "==", "<=", "~=", "!=", "<", ">", "[", ";"):
        requirement = requirement.split(sep)[0]
    return requirement.strip().lower()


def _declared() -> dict:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    out = {"runtime": set()}
    for requirement in data.get("dependencies", []):
        out["runtime"] |= PROVIDES.get(_bare_name(requirement),
                                       {_bare_name(requirement).replace("-", "_")})
    for group, requirements in data.get("optional-dependencies", {}).items():
        out[group] = set()
        for requirement in requirements:
            out[group] |= PROVIDES.get(_bare_name(requirement),
                                       {_bare_name(requirement).replace("-", "_")})
    return out


def _optional(tree: ast.Module) -> set:
    """Modules imported inside a `try` whose handler catches ImportError.

    ⛔ AN IMPORT WRITTEN THAT WAY IS DECLARING ITSELF OPTIONAL, and demanding a
    dependency for it would be a red gate on a correct line - which is how gates
    teach people to work around them. The sibling package `invisible_core` has
    exactly one: `from packaging.markers import Marker`, inside a function,
    returning "cannot tell" when it is absent, with a docstring that says in so
    many words that packaging is not one of its runtime dependencies. A first
    run of this scan across the siblings accused that line, and it was the scan
    that was wrong.

    The exemption is structural, like the registration one next door: it is the
    shape of the code that declares the intent, not a name on a list.
    """
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        catches = any(
            "ImportError" in ast.unparse(h.type) if h.type else False
            for h in node.handlers)
        if not catches:
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Import):
                out.update(a.name.split(".")[0] for a in inner.names)
            elif isinstance(inner, ast.ImportFrom) and inner.module:
                out.add(inner.module.split(".")[0])
    return out


def _imported(folder: Path) -> dict:
    """Top-level module name -> the files that import it, optional ones aside."""
    out: dict = {}
    ours = _ours()
    for path in sorted(folder.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        optional = _optional(tree)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if (name in sys.stdlib_module_names or name in ours
                        or name in optional):
                    continue
                # Relative to the repository where it can be - the message is
                # for somebody reading a failure - and absolute otherwise, so
                # the known-bad cases below can hand this a temporary directory.
                try:
                    where = str(path.relative_to(ROOT))
                except ValueError:
                    where = str(path)
                out.setdefault(name, set()).add(where)
    return out


def test_the_package_declares_everything_it_imports():
    """Known-bad is the state this file was written in: `from pydantic import
    Field` in the server, and no pydantic in `pyproject.toml`."""
    declared = _declared()["runtime"]
    missing = {name: sorted(files)
               for name, files in _imported(ROOT / "src").items()
               if name not in declared}
    assert not missing, (
        "the package imports %d module(s) it does not declare:\n  %s\n"
        "They reach it through somebody else's dependencies today, and stop "
        "the day that somebody drops them."
        % (len(missing), "\n  ".join("%s  (%s)" % (n, ", ".join(f))
                                     for n, f in sorted(missing.items()))))


def test_the_suite_declares_everything_it_imports():
    """The same question for `[project.optional-dependencies] test`, which is
    what CI installs. Known-bad is `httpx`, which the real-server test imports
    and which arrives through `mcp`."""
    allowed = _declared()["runtime"] | _declared().get("test", set())
    missing = {name: sorted(files)
               for name, files in _imported(ROOT / "tests").items()
               if name not in allowed}
    assert not missing, (
        "the suite imports %d module(s) nothing declares:\n  %s"
        % (len(missing), "\n  ".join("%s  (%s)" % (n, ", ".join(f))
                                     for n, f in sorted(missing.items()))))


def test_the_scan_is_looking_at_something():
    """⛔ A GREEN SAYS WHAT IT CHECKED. If the walk found no imports at all -
    a wrong root, an AST shape that stopped matching - both tests above would
    pass on an empty set and say nothing."""
    from_package = _imported(ROOT / "src")
    assert len(from_package) >= 5, (
        "only %d third-party modules found in src; the scan has gone blind"
        % len(from_package))
    assert "mcp" in from_package, "the scan cannot even see the MCP SDK"
    declared = _declared()
    assert len(declared["runtime"]) >= 6, (
        "only %d runtime dependencies parsed out of pyproject" % len(declared["runtime"]))


def test_an_import_that_declares_itself_optional_is_left_alone(tmp_path):
    """The case that must NOT fire, taken from a real line in a sibling package.

    `invisible_core.pin` does this and is right to: the module is used if it is
    there, and its absence is answered "cannot tell" rather than as a failure.
    A gate that demanded a dependency for it would be red on correct code."""
    module = tmp_path / "pin.py"
    module.write_text(
        "def evaluate(marker):\n"
        "    try:\n"
        "        from packaging.markers import Marker\n"
        "    except ImportError:\n"
        "        return None\n"
        "    return bool(Marker(marker).evaluate())\n", encoding="utf-8")
    assert "packaging" not in _imported(tmp_path)


def test_an_unguarded_import_of_the_same_module_is_still_caught(tmp_path):
    """And the other side of it, so the exemption cannot be read as "packaging
    is fine": at module level, with nothing catching ImportError, it is a
    dependency like any other."""
    module = tmp_path / "pin.py"
    module.write_text("from packaging.markers import Marker\n", encoding="utf-8")
    assert "packaging" in _imported(tmp_path)


def test_a_missing_declaration_is_what_it_catches():
    """The known-bad input, run against the reader rather than the real file, so
    the gate has seen its own failure at least once."""
    healthy = PYPROJECT.read_text(encoding="utf-8")
    assert "mcp>=" in healthy, "the requirement moved; this mutation is stale"
    broken = tomllib.loads(healthy.replace('"mcp>=1.8,<2",\n', ""))["project"]
    assert not any(r.startswith("mcp") for r in broken["dependencies"]), (
        "the mutation did not apply, so a survivor here would say nothing")
