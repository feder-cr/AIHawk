"""Every tool addresses ONE browser, and a caller that names none reaches `main`.

The registry has kept browsers by key since it was written, and it already gets
the hard parts right: one lock per key so two callers racing start one browser
rather than two, the configuration remembered so a rebuild is the SAME PERSON,
tab numbering that does not restart across a rebuild. All of it was unreachable,
because every tool called `registry.ensure()` with no argument. The key is now
composed by `addressed(browser_id)` from this process's own identity plus the
one optional parameter every tool publishes, `browser`, so that behaviour works
per browser without a line of the registry moving.

⛔ THE FAILURE THIS FILE EXISTS FOR IS SILENT. One call left without an address
reads one browser while the calls around it write another: no exception, no red
test, just a tool answering confidently about the wrong page. Behaviour tests
only cover the calls somebody thought to test, so the last two tests read the
SOURCE and refuse a registry call that carries no address, and a tool that
reaches the registry without offering a way to say which browser it means.

No browser starts here. The registry takes a factory and the actions are
replaced by a stub that answers with the browser it was handed, so what a tool
did is observable as the browser it reached for.
"""
from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

from aihawk.mcp import actions, server
from aihawk.mcp.registry import BrowserRegistry

SERVER_PY = pathlib.Path(inspect.getfile(server))

#: The registry methods that take a browser address. Derived from the registry
#: instead of typed out, so a method added there is guarded the day it exists.
#: Its parameter is `key` since the registry stopped calling browsers sessions;
#: if that name moves again this set empties and the test below says so.
ADDRESSABLE = {
    name for name, fn in inspect.getmembers(BrowserRegistry, inspect.isfunction)
    if not name.startswith("_") and "key" in inspect.signature(fn).parameters
}


class _Recording:
    """A browser that launches nothing and reports itself alive."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._browser = None
        self._context = object()
        self.closed = False

    async def start(self):
        pass

    async def close(self):
        self.closed = True


@pytest.fixture
def registry(monkeypatch):
    """The REAL registry, with nothing behind it that opens a browser.

    Real on purpose, and built by the server's own constructor. What the tools
    have to get right is the key they hand it, and a stand-in would have to
    reimplement the per-key locking and discarding the assertions below lean on -
    at which point the tests would be measuring the stand-in. `new_registry`
    rather than `BrowserRegistry` for the same reason one step further out: the
    product's registry writes what it holds down, and a bare one does not.
    """
    reg = server.new_registry(factory=_Recording,
                              defaults=lambda: {"seed": 7, "headless": True})
    monkeypatch.setattr(server, "registry", reg)
    return reg


@pytest.fixture
def echo(monkeypatch):
    """Every action replaced by one that answers with the browser it was given,
    so a tool's return value IS the browser it reached."""
    async def _echo(session, *args, **kwargs):
        return session

    for name in ("navigate", "read_text", "snapshot",
                 "read_html", "click", "type_text", "press_key", "evaluate"):
        monkeypatch.setattr(actions, name, _echo)


def _key(browser_id=server.DEFAULT_BROWSER_ID):
    """The key a browser is expected under, built from this process's own
    identity rather than from `addressed`, which is the thing under test."""
    return "%s/%s" % (server._SESSION_ID, browser_id)


# --- naming nothing keeps today's behaviour ---------------------------------

async def test_a_caller_that_names_nothing_reaches_the_same_one_browser(registry, echo):
    """⛔ THE PROMISE OF THE WHOLE CHANGE. Clients written before browsers had
    names send no `browser`, and have to land exactly where they always did.

    Three tools, and deliberately not three of a kind: `browser_navigate` goes
    through `_retrying`, `browser_read_text` and `browser_snapshot` call
    `ready` themselves. They compose the key in two different places, so a
    change that addresses only one of them leaves two calls looking at
    different browsers - and both calls still succeed, which is what makes it
    the dangerous shape rather than a crash.

    Two known-bad inputs, one for each assertion:

    * leave any single tool calling `registry.ensure()` bare -> it lands on
      "default" while its neighbours land on "default/main", and the first
      assertion goes red;
    * drop the `or DEFAULT_BROWSER_ID` fallback in `addressed` -> an unnamed
      caller is filed under "default/None", every tool agrees with every
      other, and only the second assertion sees it.
    """
    first = await server.browser_snapshot()
    second = await server.browser_read_text()
    third = await server.browser_navigate("http://127.0.0.1/")

    assert first is second is third, (
        "one caller that named nothing was given more than one browser")
    assert registry.ids() == [_key()], (
        "a caller that named nothing landed on %r" % registry.ids())


# --- two browsers, one process ----------------------------------------------

async def test_main_and_support_are_two_different_browsers(registry, echo):
    """Known-bad: have `addressed` ignore `browser_id`. Both calls then land on
    one key, the second returns the first browser, and `support` is `main`
    wearing a different name."""
    main = await server.browser_read_text()
    support = await server.browser_read_text(browser="support")

    assert main is not support, "the two roles were served by one browser"
    assert registry.ids() == [_key(), _key("support")], (
        "the two browsers are filed under %r" % registry.ids())


async def test_a_rebuild_of_one_browser_leaves_the_others_alone(registry, echo,
                                                                monkeypatch):
    """⛔ `_retrying` drops and re-ensures on ANY failure, so the drop is as
    addressed as the action, or recovery becomes the way browsers get killed.

    A browser that died between two calls is the ordinary case here, so this is
    the common path rather than an exotic one.

    Two known-bad inputs:

    * `await registry.drop()` in `_retrying`, which is what the code said before
      browsers had names: the failing browser is never thrown away, so it is
      handed back instead of rebuilt and the third assertion goes red;
    * `await registry.drop(addressed())`, the same mistake spelled the new way:
      `main` is closed while the caller was working on `support`, and the last
      assertion goes red.
    """
    main = await server.browser_read_text()
    support = await server.browser_read_text(browser="support")

    failures = {"left": 1}

    async def _fails_once(session, *args, **kwargs):
        if failures["left"]:
            failures["left"] -= 1
            raise RuntimeError("the browser went away between two calls")
        return session

    # `browser_navigate` is the one tool left that goes through `_retrying`,
    # which is the machinery under test here.
    monkeypatch.setattr(actions, "navigate", _fails_once)
    rebuilt = await server.browser_navigate("http://127.0.0.1/", browser="support")

    assert rebuilt is not support, "the browser that failed was handed back, not rebuilt"
    assert support.closed, "the failing browser was dropped without being closed"
    assert registry.peek(_key()) is main and not main.closed, (
        "recovery on one browser closed another one")


async def test_opening_one_browser_does_not_restart_the_other(registry, echo):
    """`browser_open` is the one tool that REPLACES a browser, which makes an
    unaddressed one the loudest version of this defect: opening `support`
    would close `main`'s browser instead, and the tool reports success either
    way.

    Known-bad: `registry.restart(**settings)` with no key, which is what the
    call looked like before a browser had an address of its own. `main` is
    restarted whatever `browser` named, a browser appears where nobody asked
    for one, and two assertions go red.
    """
    main = await server.browser_read_text()
    support = await server.browser_read_text(browser="support")

    answer = await server.browser_open(browser="support", seed=4242,
                                       proxy="", profile="")
    assert not answer.startswith("refused"), answer

    rebuilt = registry.peek(_key("support"))
    assert rebuilt is not support, "the named browser was not the one restarted"
    assert rebuilt.kwargs.get("seed") == 4242, (
        "the restarted browser is not the person that was asked for")
    assert registry.peek(_key()) is main and not main.closed, (
        "opening one browser restarted the other one")
    assert registry.ids() == [_key(), _key("support")], (
        "browser_open opened a browser nobody asked for: %r" % registry.ids())


# --- the ones a behaviour test cannot reach ---------------------------------

def test_the_registry_still_has_methods_worth_guarding():
    """The two structural tests below derive what they guard from the registry
    rather than from a list typed here. A rename that empties that derivation
    would leave them green over an unguarded module, so the derivation itself is
    asserted before it is trusted."""
    assert {"ensure", "peek", "config", "drop", "restart"} <= ADDRESSABLE, (
        "the registry no longer takes an address on the methods the server "
        "calls, so the scan below guards nothing: %r" % sorted(ADDRESSABLE))


def test_the_exempted_helpers_are_still_the_ones_they_name():
    """An exemption that names nothing exempts nothing, and reads as though it
    does - which is worse than no exemption at all, because the next reader
    takes it for a description of the module.
    """
    absent = sorted(n for n in WALK_KEYS_THE_REGISTRY_ALREADY_HOLDS
                    if not callable(getattr(server, n, None)))
    assert not absent, (
        "exempted from the address scan but no longer in the server: %r. "
        "Either the function was renamed, in which case rename it here, or it "
        "is gone, in which case delete the exemption." % absent)


#: The two functions that walk keys the registry ALREADY holds, rather than
#: composing one for a caller.
#:
#: ⛔ EXEMPTED BY NAME, for the same reason `browser_list` is exempted below:
#: loosening the rule would cost it the case it exists for. `remember` iterates
#: `registry.declared()`, whose entries are composed keys by construction, and
#: asks `registry.config(key)` about each; `restore` writes one back with
#: `registry.declare("%s/%s" % ...)`. Neither is answering a caller who named a
#: browser - they are the persistence of everything this process holds - so
#: `addressed()` has nothing to compose from, and requiring it there would mean
#: writing a call that means nothing to satisfy a scanner.
#:
#: The names are asserted to still exist before they are trusted: an exemption
#: that has rotted into a name nothing matches protects nothing while reading as
#: though it does.
WALK_KEYS_THE_REGISTRY_ALREADY_HOLDS = {"remember", "restore"}


def _scan_registry_calls():
    """Every `registry.<addressable>(...)` in the server, and whether it carries
    an address.

    Read per enclosing function, because `_retrying` addresses once into a local
    and then uses it three times: a name is accepted only where it was bound to
    `addressed(...)` in scope.
    """
    tree = ast.parse(SERVER_PY.read_text(encoding="utf-8"))
    unaddressed, checked = [], {}

    for holder in ast.walk(tree):
        if (isinstance(holder, (ast.FunctionDef, ast.AsyncFunctionDef))
                and holder.name in WALK_KEYS_THE_REGISTRY_ALREADY_HOLDS):
            continue
        if not isinstance(holder, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        bound = set()
        for node in ast.walk(holder):
            if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "addressed"):
                bound |= {t.id for t in node.targets if isinstance(t, ast.Name)}

        for node in ast.walk(holder):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "registry"
                    and node.func.attr in ADDRESSABLE):
                continue
            checked[node.lineno] = "%s: registry.%s" % (holder.name, node.func.attr)
            given = node.args[0] if node.args else next(
                (k.value for k in node.keywords if k.arg == "key"), None)
            composed_here = (isinstance(given, ast.Call)
                             and isinstance(given.func, ast.Name)
                             and given.func.id == "addressed")
            composed_earlier = isinstance(given, ast.Name) and given.id in bound
            if not (composed_here or composed_earlier):
                unaddressed.append("line %d, %s" % (node.lineno, checked[node.lineno]))

    return unaddressed, checked


def test_no_registry_call_in_the_server_is_left_without_an_address():
    """⛔ THE ONE THAT CANNOT BE WRITTEN AS A BEHAVIOUR TEST, because it is
    about the calls nobody wrote a behaviour test for.

    An unaddressed call does not fail. It looks at `main` while its neighbours
    look at `support`, and every tool answers normally: the tab that is not
    there, the text of the wrong page, a click that lands somewhere nobody is
    watching. One call is enough, and there are ten of them in the module, so
    the property is asserted over the source rather than sampled.

    Known-bad, run before this was trusted: turn any one
    `registry.ensure(addressed(browser_id))` back into `registry.ensure()`.
    """
    unaddressed, checked = _scan_registry_calls()

    assert not unaddressed, (
        "these reach the registry with no browser named, so they act on the "
        "default one whatever the caller asked for: %s" % unaddressed)
    # ⛔ THE FLOOR WENT FROM 18 TO 10 ON PURPOSE, AND THE SCAN GOT STRONGER
    # RATHER THAN WEAKER. In 0.19.0 the fourteen tools that each wrote
    # `registry.ensure(addressed(...))` for themselves were moved onto one
    # funnel, `ready`, because "what it takes to hand somebody a usable browser"
    # had stopped being just `ensure` - a declared browser now has tabs owed to
    # it - and fifteen places would have had to learn the same new step. So
    # there are fewer registry calls to guard because there are fewer places
    # able to get it wrong. Lowering a floor is normally how a gate is quietly
    # switched off, which is why the reason is written here and why the
    # companion test below asserts that the funnel is what the tools use.
    assert len(checked) >= 10, (
        "only %d registry calls were found in %s; has the module moved?"
        % (len(checked), SERVER_PY.name))


def test_no_tool_reaches_for_a_browser_on_its_own():
    """⛔ THE GUARANTEE THAT REPLACED THE ONE ABOVE, and it is stronger than
    what it replaced. The floor on registry calls fell from 18 to 10 when the
    tools were moved onto `ready`; a lower floor on its own is how a gate gets
    switched off, so this says the thing the floor used to imply and says it
    directly: no TOOL touches the registry itself.

    It matters because `ready` is no longer a synonym for `ensure`. A browser
    restored from a saved file has tabs owed to it, and a tool that called
    `ensure` for itself would hand back that browser with none of its pages -
    a browser that is right about who it is and wrong about where it was.

    Known-bad: put `await registry.ensure(addressed(browser_id))` back into
    any one tool. The scan above still passes, because that call IS addressed;
    only this one sees it.
    """
    tree = ast.parse(SERVER_PY.read_text(encoding="utf-8"))
    #: The four that legitimately act on the registry rather than ask it for a
    #: browser to drive: opening one, closing one, reporting who is running,
    #: and listing what is open.
    NOT_DRIVING_A_PAGE = {"browser_open", "browser_close", "browser_status",
                          "browser_list"}
    rogue = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decorated = any(
            isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
            and d.func.attr == "tool" for d in node.decorator_list)
        if not decorated or node.name in NOT_DRIVING_A_PAGE:
            continue
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Attribute)
                    and isinstance(inner.func.value, ast.Name)
                    and inner.func.value.id == "registry"):
                rogue.append("%s: registry.%s" % (node.name, inner.func.attr))
    assert not rogue, (
        "these reach the registry themselves instead of asking `ready` for a "
        "browser, so a browser restored from disk comes back without its "
        "tabs: %s" % rogue)


def _tools_that_reach_a_browser():
    """The `@mcp.tool()` functions whose own body reaches the registry, whether
    directly or through `_retrying`."""
    tree = ast.parse(SERVER_PY.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decorated = any(
            isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
            and d.func.attr == "tool" for d in node.decorator_list)
        if not decorated:
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            if (isinstance(inner.func, ast.Attribute)
                    and isinstance(inner.func.value, ast.Name)
                    and inner.func.value.id == "registry"
                    and inner.func.attr in ADDRESSABLE):
                found.add(node.name)
            if (isinstance(inner.func, ast.Name)
                    and inner.func.id in ("_retrying", "ready")):
                found.add(node.name)
    return found


async def test_every_tool_that_reaches_a_browser_offers_a_way_to_name_it():
    """A tool that touches a browser with no way to say WHICH one always means
    `main`, and a caller working in `support` simply cannot use it - the
    surface would be addressable in most places and mute in a few.

    Which tools need an address is read from the code rather than listed here,
    so one written later is covered the day it is written. The check is against
    the SCHEMA the server publishes, not the Python signature: a parameter the
    client cannot see is a parameter that does not exist.

    ⛔ ONE EXEMPTION, and it is about the QUESTION rather than about the tool.
    `browser_list` asks which of the two browsers are open in THIS process, and
    that question has no second one to ask it about - it is not one browser
    telling you about itself, so it takes no `browser` at all. It reaches the
    registry once per browser it lists - that is what makes the scan find it -
    but the browsers are the ones this process already has, not one a caller
    named.

    Exempting it by name rather than by loosening the rule to "most of them"
    keeps the rule able to catch the case it exists for: a tool that acts on a
    browser and cannot say which.

    Known-bad: delete `browser` from any one other tool.
    """
    ASKS_ABOUT_EVERYTHING_OPEN = {"browser_list"}
    needing = _tools_that_reach_a_browser() - ASKS_ABOUT_EVERYTHING_OPEN
    # ⛔ THE FLOOR HAS DROPPED TWICE IN ONE DAY AND BOTH DROPS ARE WRITTEN DOWN,
    # because a number that falls on its own with nothing said about why is how
    # a gate goes quiet without anybody deciding that. 18 -> 17 when
    # `session_start` folded into `browser_open`. 17 -> 14 when the four tab
    # tools were removed: three of them reached a browser through `ready` or
    # `_retrying` and were counted here, while `browser_tab_list` went through
    # `looking` and never was. Fewer tools reach a browser because there are
    # fewer tools, not because fewer of them are addressed.
    assert len(needing) >= 14, (
        "only %d tools were found reaching a browser; has the module moved? %r"
        % (len(needing), sorted(needing)))

    tools = await server.mcp.list_tools()
    published = {t.name: t.inputSchema.get("properties", {}) for t in tools}
    gone = sorted(ASKS_ABOUT_EVERYTHING_OPEN - set(published))
    assert not gone, (
        "exempted from needing a browser, but the server no longer offers "
        "it: %r. An exemption that names nothing exempts nothing." % gone)
    unknown = sorted(needing - set(published))
    assert not unknown, "found in the source but not registered: %r" % unknown

    mute = {name: sorted(published[name]) for name in sorted(needing)
            if not {"browser"} <= set(published[name])}
    assert not mute, (
        "these act on a browser the caller cannot name, so they always act on "
        "`main`: %s" % mute)

    # ⛔ AND THE NAME IS A ROLE, NOT A STRING. This is the half that keeps the
    # eight browsers from coming back: not as a decision to restore them, but
    # as one tool that needed to name something and took a `str`, and then a
    # second for symmetry. A process holds `main` and `support`; anything else
    # is a name a caller invented, and the schema is where that is refused -
    # before a model spends a turn on it.
    loose = {}
    for name, props in sorted(published.items()):
        spec = props.get("browser")
        if spec is None:
            continue
        allowed = set()
        for branch in spec.get("anyOf") or [spec]:
            allowed |= set(branch.get("enum") or ())
        if allowed != {"main", "support"}:
            loose[name] = spec
    assert not loose, (
        "`browser` is not the closed pair of roles on these, so a caller can "
        "invent a name: %s" % loose)
    assert "browser_id" not in {k for p in published.values() for k in p}, (
        "a tool offers a free-form browser id, which is the eight browsers "
        "coming back one signature at a time")
