"""Nothing in the product may exist only for the suite.

⛔ THIS IS A GATE ON A CLASS, NOT A LIST OF NAMES THAT WERE REMOVED. Seven
surfaces came out of `src/invisible_playwright_mcp` in one audit and every one of them was the
same shape: a function, a constant or a method with no caller in the product,
kept alive by the tests that had grown up around it.

  * `agent.run_task` - a second way to run the agent loop, taking an object
    shaped like the pre-`Link` world. About twenty-five tests, zero product
    callers. It is now `tests/_loop.py`.
  * `Sessions.around` - a constructor whose docstring offered "and so would
    anything embedding this", a user that does not exist. Eleven callers, all
    tests. It is now `tests/_sessions.py`.
  * `SessionPlan.describe` - a second mapping of a plan onto the sentence a
    caller is told, beside the one in `work.open`. Six callers, all tests.
  * `clean.relevance` and `clean.clean_stats` - fifty-seven lines of scoring and
    seven figures of savings, arriving dead with the server on 2026-09-06 and
    never called by anything. `clean_stats` was even in `__all__`.
  * `clean.BLOCK_TAGS` - a tuple nothing read.
  * `Sessions._open_link` as an attribute reassigned from outside - a seam that
    worked and that nothing declared. It is a parameter now.

A list of those seven names would stop those seven. The defect is not the seven:
it is that a surface can be added, be used only by its own tests, and look
exactly like a surface the product depends on. So the question this asks is the
general one - is this named anywhere in `src`? - and the answer has to be yes.

⛔ WHAT IT LOOKS AT, MEASURED, BECAUSE A GREEN SAYS WHAT IT CHECKED AND NOT WHAT
EXISTS. Two scans, and they answer two different questions.

  * `unnamed` - top-level functions, classes and upper-case constants across the
    package: 178 of them in 25 modules, with 18 more exempt because they are
    registered (below). A name at module level is unambiguous, so counting is
    enough.
  * `uncalled` - methods: 47 of them, out of the 59 defined. The twelve left out
    are methods of a class WITH A BASE, which may be satisfying somebody else's
    contract so the caller is the base's, and methods carrying a decorator,
    which can hand them somewhere this cannot follow. Counting is NOT enough
    here, and saying so is what the first version of this file did instead of
    doing the work:
    `plan.describe(...)` and `SessionPlan.describe(...)` are the same attribute
    name, so a scan that counts names cannot tell the dead method from the live
    function beside it. It is separated by resolving the OWNER - an attribute on
    a name that this file imported as a MODULE is the module's function and
    never the method - which is exactly the confusion that let
    `SessionPlan.describe` live, and it is now the thing the scan looks for.

Anything nested inside a function is out of scope for both: it cannot be reached
from outside in the first place. So is the page - `src/invisible_playwright_mcp/ui/js` and
`src/invisible_playwright_mcp/ui/css` are product surface too, and they were scanned the same way
by hand: 109 top-level JS bindings, all named by another file or by the markup,
and 49 CSS classes, all applied. They carry no gate here because the page is one
concatenated script and its own gates live in
`tests/test_the_browser_workspace.py`.

⛔ WHAT EXCUSES A DEFINITION IS BEING REGISTERED, WHICH IS STRUCTURAL. A
decorator spelled `.tool`, `.command` or `.group` hands the object to somebody
else - FastMCP's registry, click's - and the call that follows happens over a
wire or from a shell, where no scan of this tree can see it. `@dataclass`,
`@contextmanager` and `@asynccontextmanager` do NOT excuse anything: they wrap
the object and hand it straight back, so it is still called by name and still has
to be.

⛔ AND `__all__` IS NOT EVIDENCE. It is the claim under audit - "this module
exports this" - so a name that appears only there counts as unused. That is
exactly where `clean_stats` was hiding: exported, tested, called by nobody.
"""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "invisible_playwright_mcp"

#: A decorator spelling that hands the object to a registry. See the module
#: docstring: this is the whole exemption, and it is deliberately not a list of
#: function names.
REGISTERED = (".tool", ".command", ".group")


def _defined(tree: ast.Module):
    """(name, line, registered) for every top-level surface of one module."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            registered = any(any(m in ast.unparse(d) for m in REGISTERED)
                             for d in node.decorator_list)
            yield node.name, node.lineno, registered
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                # Upper-case only: a lower-case module-level assignment is
                # usually a value being built, not a surface being offered.
                if isinstance(t, ast.Name) and t.id.isupper() and len(t.id) > 2:
                    yield t.id, node.lineno, False


def _named(tree: ast.Module):
    """Every name this module NAMES: reads, attributes, imports, and the words
    of its strings - except the strings inside `__all__`, for the reason in the
    module docstring.

    A definition never names itself here: a `def` is not an `ast.Name`, and an
    assignment's target is a `Store`, not a `Load`. So a count of zero means
    nothing else in the package mentions it.
    """
    in_all = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            in_all.update(id(child) for child in ast.walk(node.value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            yield node.id
        elif isinstance(node, ast.Attribute):
            yield node.attr
        elif isinstance(node, ast.alias):
            yield node.name.split(".")[-1]
            if node.asname:
                yield node.asname
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # Strings count, because a name can genuinely be reached through
            # one. `__all__` is the exception and it is handled above.
            if id(node) not in in_all:
                yield from node.value.split()


def unnamed(sources: dict) -> list:
    """Every top-level surface in these modules that no module names.

    Takes the sources as a mapping so the known-bad cases below are dictionaries
    rather than a directory somebody has to write to disk first.
    """
    trees = {where: ast.parse(text) for where, text in sources.items()}
    named = set()
    for tree in trees.values():
        named.update(_named(tree))
    out = []
    for where, tree in trees.items():
        for name, line, registered in _defined(tree):
            if not registered and name not in named:
                out.append("%s:%d %s" % (where, line, name))
    return sorted(out)


def _module_aliases(tree: ast.Module, known: set) -> set:
    """The names that, in THIS file, stand for a module rather than an object.

    `import x`, `import x.y as z`, and `from . import plan` where a module of
    that name exists. Anything else imported from a module is a function or a
    class, and an attribute on one of those is not a module's function.
    """
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.add(a.asname or a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name in known:
                    out.add(a.asname or a.name)
    return out


def _on_an_object(tree: ast.Module, known: set):
    """Every attribute name reached on something that is NOT a module.

    ⛔ THIS IS THE WHOLE IDEA, and it is why methods can be scanned at all.
    `plan.describe(...)` resolves `plan` to a module, so it is the module's
    function and says nothing about any method. `self.describe(...)`,
    `SessionPlan.describe(...)` and `whatever.describe(...)` all could be the
    method, and all count.

    Deliberately generous in that second half: an arbitrary expression counts as
    a reference to EVERY method of that name. It errs by letting something live,
    never by accusing it.
    """
    aliases = _module_aliases(tree, known)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            owner = node.value
            if isinstance(owner, ast.Name) and owner.id in aliases:
                continue
            yield node.attr
        elif (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and node.value.isidentifier()):
            # A method can genuinely be reached by string, through `getattr` or
            # a table of verbs.
            #
            # ⛔ WHOLE-STRING ONLY, AND THE FIRST VERSION SPLIT STRINGS INTO
            # WORDS. That version let the known-bad mutation SURVIVE: the
            # docstrings in `plan.py` name `describe` in prose, so the prose
            # kept the method alive. It is the most repeated defect in this
            # project - writing the check against the comment beside the code
            # instead of against the code - met inside the tool built to find
            # it. Measured: the universe of attribute names went from 4,798 to
            # 500 when the prose stopped counting, so nine tenths of what was
            # keeping methods alive was sentences.
            yield node.value


def uncalled(sources: dict) -> list:
    """Every method in these modules that nothing reaches on an object.

    Dunders are out: the interpreter calls them. So is anything decorated - a
    decorator can hand the method somewhere this cannot follow - and so is any
    method of a class with a base, which may be satisfying somebody else's
    contract.
    """
    trees = {where: ast.parse(text) for where, text in sources.items()}
    known = {Path(where).stem for where in sources}
    reached = set()
    for tree in trees.values():
        reached.update(_on_an_object(tree, known))
    out = []
    for where, tree in trees.items():
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if node.bases:
                continue
            for child in node.body:
                if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if child.name.startswith("__") or child.decorator_list:
                    continue
                if child.name not in reached:
                    out.append("%s:%d %s.%s"
                               % (where, child.lineno, node.name, child.name))
    return sorted(out)


def _product() -> dict:
    return {str(p.relative_to(SRC)): p.read_text(encoding="utf-8")
            for p in sorted(SRC.rglob("*.py"))}


def test_every_surface_the_product_offers_is_one_the_product_names():
    """The gate itself. A failure names the file, the line and the surface, and
    the fix is one of two things: call it, or delete it. Moving it into the
    suite, as the seven above were moved, counts as deleting it."""
    left = unnamed(_product())
    assert not left, (
        "%d surface(s) in src/invisible_playwright_mcp that nothing in src/invisible_playwright_mcp names:\n  %s\n"
        "Each is either dead or exists only for the tests. If the suite wants "
        "it, it belongs in the suite." % (len(left), "\n  ".join(left)))


def test_every_method_the_product_defines_is_one_the_product_reaches():
    """The half the first version of this file declared impossible.

    A failure names the file, the line and `Class.method`. The fix is the same
    two: call it, or delete it."""
    left = uncalled(_product())
    assert not left, (
        "%d method(s) in src/invisible_playwright_mcp that nothing reaches on an object:\n  %s\n"
        "An attribute on an imported MODULE does not count - that is the "
        "module's function, not this method." % (len(left), "\n  ".join(left)))


def test_the_gate_is_looking_at_the_whole_package():
    """⛔ A GREEN SAYS WHAT IT CHECKED. A scan that silently stopped finding
    definitions - a walk rooted at the wrong directory, an AST shape that stopped
    matching - would print the same clean line as a healthy package. The floors
    are well under the measured 178 across 25 modules, so ordinary growth never
    touches this and a collapse does."""
    sources = _product()
    assert len(sources) >= 20, "only %d modules found under %s" % (len(sources), SRC)
    judged = sum(1 for text in sources.values()
                 for _, _, registered in _defined(ast.parse(text)) if not registered)
    assert judged >= 120, "only %d definitions judged; the scan has gone blind" % judged

    # The method half has its own two floors, and the second one is the one that
    # caught a blind gate: if the set of attribute names collapses, every method
    # looks dead, and if it explodes, every method looks alive. It was 4,798
    # when prose was leaking into it and 500 when it stopped.
    known = {Path(where).stem for where in sources}
    methods = sum(1 for text in sources.values()
                  for node in ast.parse(text).body
                  if isinstance(node, ast.ClassDef) and not node.bases
                  for child in node.body
                  if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and not child.name.startswith("__") and not child.decorator_list)
    assert methods >= 30, "only %d methods judged; the scan has gone blind" % methods
    # ⛔ AND A CEILING TOO, because this number is the one the docstring above
    # publishes and a hand-written figure goes stale the day somebody changes
    # what is excluded. It was written as 59 first - the count BEFORE the
    # exclusions - which is how a perimeter stops describing the gate that
    # carries it.
    assert methods <= 120, "%d methods judged; the exclusions have stopped applying" % methods
    reached = set()
    for text in sources.values():
        reached.update(_on_an_object(ast.parse(text), known))
    assert 150 <= len(reached) <= 2000, (
        "%d attribute names reached on an object. Far below and every method "
        "reads as dead; far above and prose is leaking in again, which is how "
        "the known-bad mutation survived the first time." % len(reached))


# --- known-bad inputs. A gate that has only ever printed PASS is not a gate ---

def test_a_function_nobody_calls_is_caught():
    """`clean.relevance`, in miniature: fifty-seven lines nothing ever called."""
    assert unnamed({"a.py": "def relevance(node):\n    return 1\n"}) == ["a.py:1 relevance"]


def test_a_constant_nobody_reads_is_caught():
    """`clean.BLOCK_TAGS`, in miniature."""
    assert unnamed({"a.py": "BLOCK_TAGS = ('div', 'p')\n"}) == ["a.py:1 BLOCK_TAGS"]


def test_a_class_nobody_builds_is_caught():
    assert unnamed({"a.py": "class Helper:\n    pass\n"}) == ["a.py:1 Helper"]


def test_a_method_shadowed_by_a_module_function_of_the_same_name_is_caught():
    """⛔ `SessionPlan.describe` ITSELF, IN MINIATURE, and the reason this half
    exists. `plan.describe(...)` in `work.py` is the MODULE's function; the
    method beside it had six callers, all tests. A scan that counts names sees
    one `describe` reached and calls it a day."""
    left = uncalled({
        "plan.py": "def describe(kwargs):\n    return str(kwargs)\n\n\n"
                   "class SessionPlan:\n    kwargs = {}\n\n"
                   "    def describe(self):\n        return describe(self.kwargs)\n",
        "work.py": "from . import plan\n\n\n"
                   "def open_it(settings):\n    return plan.describe(settings)\n",
    })
    assert left == ["plan.py:8 SessionPlan.describe"]


def test_prose_naming_a_method_does_not_keep_it_alive():
    """⛔ THE MUTATION THAT SURVIVED THE FIRST VERSION OF THIS SCAN. Strings were
    split into words, so a docstring saying "describe() reads the KWARGS" was
    counted as reaching the method. The check was satisfied by the comment beside
    the code, which is the most repeated defect in this project."""
    left = uncalled({
        "plan.py": '"""The module. `describe()` reads the KWARGS, never the'
                   ' arguments."""\n\n\n'
                   "class SessionPlan:\n"
                   '    """A plan. Ask describe for the sentence."""\n\n'
                   "    def describe(self):\n        return 1\n",
    })
    assert left == ["plan.py:7 SessionPlan.describe"]


def test_a_method_reached_only_through_the_module_alias_is_still_caught():
    """The same rule stated the other way round: importing the module under a
    different name must not launder the reference."""
    left = uncalled({
        "plan.py": "def go():\n    return 1\n\n\nclass P:\n    def go(self):\n"
                   "        return 2\n",
        "work.py": "from . import plan as planner\n\n\n"
                   "def run():\n    return planner.go()\n",
    })
    assert left == ["plan.py:6 P.go"]


def test_exporting_it_is_not_using_it():
    """⛔ THE HIDING PLACE `clean_stats` USED. It was in `__all__`, it had a
    test, and no caller. If `__all__` counted as a reference this gate would
    pass it, which is the whole reason for the exception in `_named`."""
    source = "__all__ = ['clean_stats']\n\n\ndef clean_stats(a, b):\n    return {}\n"
    assert unnamed({"a.py": source}) == ["a.py:4 clean_stats"]


def test_a_surface_only_the_tests_use_is_caught():
    """The seven removed this day were all this: alive in `tests/`, unnamed in
    `src`. The mapping handed in is the PRODUCT, so a caller outside it cannot
    keep a surface alive - which is the point."""
    product = {"agent.py": "def run_task(mcp, task):\n    return task\n"}
    assert unnamed(product) == ["agent.py:1 run_task"]


def test_a_decorator_that_only_wraps_does_not_excuse_it():
    """⛔ `@dataclass` and `@contextmanager` hand the object straight back, so it
    is still called by name. Known-bad is excusing anything decorated, which
    would have let `SessionPlan` through had it ever lost its callers."""
    source = ("from dataclasses import dataclass\n\n\n"
              "@dataclass\nclass Plan:\n    x: int = 0\n")
    assert unnamed({"a.py": source}) == ["a.py:5 Plan"]


# --- the cases that must NOT fire --------------------------------------------

# ⛔ EACH FIXTURE BELOW ENDS AT A REGISTERED ENTRY POINT, exactly as the package
# does. Without one the toy module's own outermost function has no caller either
# and the gate reports IT - correctly, which is why these are written this way
# rather than by loosening the assertion to ignore whatever came back.

def test_a_function_called_from_another_module_is_left_alone():
    assert unnamed({
        "a.py": "def file_for(kind, at):\n    return kind + at\n",
        "b.py": "from .a import file_for\n\n\n@mcp.tool()\n"
                "def go():\n    return file_for('x', 'y')\n",
    }) == []


def test_a_function_called_only_inside_its_own_module_is_left_alone():
    """A private helper with one caller beside it is not dead. Known-bad is
    counting references across modules only, which would condemn most of
    `clean.py`."""
    assert unnamed({
        "a.py": "def _drop(t):\n    return t\n\n\n@mcp.tool()\n"
                "def clean(t):\n    return _drop(t)\n",
    }) == []


def test_a_registered_tool_is_left_alone():
    """The sixteen MCP tools have no caller in this tree and never will: they
    are called over a wire. Known-bad is a gate that demands an in-tree caller,
    which would condemn the product's entire public surface."""
    source = ("@mcp.tool(annotations=_says('Open a browser'))\n"
              "async def browser_open(browser=None):\n    return ''\n")
    assert unnamed({"server.py": source}) == []


def test_a_click_command_is_left_alone():
    source = ("@main.command()\n@click.option('--port')\n"
              "def ui(port):\n    return port\n")
    assert unnamed({"cli.py": source}) == []


def test_a_method_called_on_self_is_left_alone():
    """The commonest shape there is: `plan` is reached only through `self`.

    ⛔ AND THE FIXTURE NEEDS AN OUTER CALLER, which is the second time a
    must-not-fire case here was built too small. Without `server.py` the toy
    world has nothing reaching `open` either, so the gate reports it - correctly.
    The real package always has an outer caller; a two-line fixture does not
    unless it is given one."""
    assert uncalled({
        "work.py": "class Work:\n    def open(self):\n        return self.plan()\n\n"
                   "    def plan(self):\n        return 1\n",
        "server.py": "def browser_open(work):\n    return work.open()\n",
    }) == []


def test_a_method_reached_through_an_ordinary_expression_is_left_alone():
    """The generous half, on purpose: this scan cannot know what
    `self._live[at]` is, so any attribute on any expression counts. It errs by
    letting something live."""
    assert uncalled({
        "a.py": "class Service:\n    def save(self):\n        return 1\n",
        "b.py": "def go(registry, at):\n    return registry[at].save()\n",
    }) == []


def test_a_method_satisfying_somebody_elses_contract_is_left_alone():
    """A class with a base may be implementing an interface, and the caller is
    then the base's. Known-bad is a gate that condemns `OpenRouterBrain.handle`
    and teaches people to work around it."""
    assert uncalled({
        "a.py": "class Brain:\n    pass\n\n\nclass OpenRouterBrain(Brain):\n"
                "    def handle(self, text):\n        return text\n",
    }) == []


def test_a_name_reached_through_a_string_is_left_alone():
    """⛔ THE CASE THAT MAKES THE STRING RULE NARROW. A name can genuinely be
    reached by string - through `getattr`, through a table of verbs - and
    condemning it would push somebody to widen the exemptions instead. Only
    `__all__` is excluded, because only `__all__` is a claim about export rather
    than a use."""
    assert unnamed({
        "a.py": "def browser_navigate():\n    return 1\n",
        "b.py": "VERBS = {'browser_navigate': 'goes to a URL'}\n\n\n@mcp.tool()\n"
                "def say(name):\n    return VERBS[name]\n",
    }) == []
