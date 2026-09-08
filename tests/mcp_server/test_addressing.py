"""Every tool addresses ONE browser, and a caller that names none keeps the old one.

The registry has kept browsers by key since it was written, and it already gets
the hard parts right: one lock per key so two callers racing start one browser
rather than two, the configuration remembered so a rebuild is the SAME PERSON,
tab numbering that does not restart across a rebuild. All of it was unreachable,
because every tool called `registry.ensure()` with no argument. The key is now
composed from two optional parameters, `session_id/browser_id`, so that
behaviour starts working per browser without a line of the registry moving.

⛔ THE FAILURE THIS FILE EXISTS FOR IS SILENT. One call left without an address
reads one browser while the calls around it write another: no exception, no red
test, just a tool answering confidently about the wrong page. Behaviour tests
only cover the calls somebody thought to test, so the last two tests read the
SOURCE and refuse a registry call that carries no address, and a tool that
reaches the registry without offering a way to say which browser it means.

No browser starts here. The registry takes a factory and the actions are
replaced by a stub that answers with the session it was handed, so what a tool
did is observable as the browser it reached for.
"""
from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

from aihawk.mcp import actions, server
from aihawk.mcp.registry import DEFAULT_SESSION_ID, SessionRegistry

SERVER_PY = pathlib.Path(inspect.getfile(server))

#: The registry methods that take a browser address. Derived from the registry
#: instead of typed out, so a method added there is guarded the day it exists.
ADDRESSABLE = {
    name for name, fn in inspect.getmembers(SessionRegistry, inspect.isfunction)
    if not name.startswith("_") and "session_id" in inspect.signature(fn).parameters
}


class _Recording:
    """A session that launches nothing and reports itself alive."""

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
    rather than `SessionRegistry` for the same reason one step further out: the
    product's registry writes its sessions down, and a bare one does not.
    """
    reg = server.new_registry(factory=_Recording,
                              defaults=lambda: {"seed": 7, "headless": True})
    monkeypatch.setattr(server, "registry", reg)
    return reg


@pytest.fixture
def echo(monkeypatch):
    """Every action replaced by one that answers with the session it was given,
    so a tool's return value IS the browser it reached."""
    async def _echo(session, *args, **kwargs):
        return session

    for name in ("new_page", "list_pages", "navigate", "read_text", "snapshot",
                 "read_html", "click", "type_text", "press_key", "evaluate"):
        monkeypatch.setattr(actions, name, _echo)


def _key(session_id=DEFAULT_SESSION_ID, browser_id=server.DEFAULT_BROWSER_ID):
    """The key a browser is expected under, built from the two constants rather
    than from `addressed`, which is the thing under test."""
    return "%s/%s" % (session_id, browser_id)


# --- naming nothing keeps today's behaviour ---------------------------------

async def test_a_caller_that_names_nothing_reaches_the_same_one_browser(registry, echo):
    """⛔ THE PROMISE OF THE WHOLE CHANGE. Clients written before browsers had
    names send neither id, and have to land exactly where they always did.

    Three tools, and deliberately not three of a kind: `session_new_page` and
    `browser_navigate` go through `_retrying`, `browser_read_text` calls
    `ensure` itself. They compose the key in two different places, so a change
    that addresses only one of them leaves two halves of one session looking at
    different browsers - and both calls still succeed, which is what makes it
    the dangerous shape rather than a crash.

    Two known-bad inputs, one for each assertion:

    * leave any single tool calling `registry.ensure()` bare -> it lands on
      "default" while its neighbours land on "default/main", and the first
      assertion goes red;
    * drop the `or DEFAULT_SESSION_ID` / `or DEFAULT_BROWSER_ID` fallbacks in
      `addressed` -> an unnamed caller is filed under "None/None", every tool
      agrees with every other, and only the second assertion sees it.
    """
    first = await server.session_new_page()
    second = await server.browser_read_text()
    third = await server.browser_navigate("http://127.0.0.1/")

    assert first is second is third, (
        "one caller that named nothing was given more than one browser")
    assert registry.ids() == [_key()], (
        "a caller that named nothing landed on %r" % registry.ids())


# --- two browsers, one session ----------------------------------------------

async def test_two_browser_ids_in_one_session_are_two_browsers(registry, echo):
    """Known-bad: have `addressed` ignore `browser_id`. Both calls then land on
    one key, the second returns the first browser, and a caller driving two
    accounts is driving one."""
    a = await server.browser_read_text(browser_id="a")
    b = await server.browser_read_text(browser_id="b")

    assert a is not b, "two browser ids were served by one browser"
    assert registry.ids() == [_key(browser_id="a"), _key(browser_id="b")], (
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
      the DEFAULT browser is closed while the caller was working on another one,
      and the last assertion goes red.
    """
    main = await server.browser_read_text()
    other = await server.browser_read_text(browser_id="b")

    failures = {"left": 1}

    async def _fails_once(session, *args, **kwargs):
        if failures["left"]:
            failures["left"] -= 1
            raise RuntimeError("the browser went away between two calls")
        return session

    monkeypatch.setattr(actions, "new_page", _fails_once)
    rebuilt = await server.session_new_page(browser_id="b")

    assert rebuilt is not other, "the browser that failed was handed back, not rebuilt"
    assert other.closed, "the failing browser was dropped without being closed"
    assert registry.peek(_key()) is main and not main.closed, (
        "recovery on one browser closed another one")


# --- two sessions -----------------------------------------------------------

async def test_two_session_ids_do_not_share_a_browser(registry, echo):
    """Known-bad: have `addressed` ignore `session_id`. Both callers then share
    one browser, which is the cookie jar of one person handed to another."""
    a = await server.browser_read_text(session_id="one")
    b = await server.browser_read_text(session_id="two")

    assert a is not b, "two sessions were served by one browser"
    assert registry.ids() == [_key("one"), _key("two")], (
        "the two sessions are filed under %r" % registry.ids())


async def test_starting_a_session_does_not_restart_another_ones_browser(registry, echo):
    """`session_start` is the one tool that REPLACES a browser, which makes an
    unaddressed one the loudest version of this defect: somebody choosing an
    identity in their own session closes the browser of a session they cannot
    see, and both callers are told it worked.

    Known-bad: `registry.restart(**chosen.kwargs)`, the call this replaced. The
    default key is restarted whatever the caller named, so a third browser
    appears, the named session keeps its old one, and two assertions go red.
    """
    mine = await server.browser_read_text(session_id="one")
    theirs = await server.browser_read_text(session_id="two")

    # proxy and profile are said out loud as "none" so the environment cannot
    # decide either: this test is about WHICH browser was restarted.
    answer = await server.session_start(seed=4242, proxy="", profile="",
                                        session_id="one")
    assert not answer.startswith("refused"), answer

    restarted = registry.peek(_key("one"))
    assert restarted is not mine and mine.closed, (
        "the named session's browser was not the one restarted")
    assert restarted.kwargs.get("seed") == 4242, (
        "the restarted browser is not the person that was asked for")
    assert registry.peek(_key("two")) is theirs and not theirs.closed, (
        "starting one session restarted another one's browser")
    assert registry.ids() == [_key("one"), _key("two")], (
        "session_start opened a browser nobody asked for: %r" % registry.ids())


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
#: browser - they are the persistence of the whole session - so `addressed()`
#: has nothing to compose from, and requiring it there would mean writing a call
#: that means nothing to satisfy a scanner.
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
                (k.value for k in node.keywords if k.arg == "session_id"), None)
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

    An unaddressed call does not fail. It looks at the default browser while its
    neighbours look at the caller's, and every tool answers normally: the tab
    that is not there, the text of the wrong page, a click that lands somewhere
    nobody is watching. One call is enough, and there are twenty of them in the
    module, so the property is asserted over the source rather than sampled.

    Known-bad, run before this was trusted: turn any one
    `registry.ensure(addressed(session_id, browser_id))` back into
    `registry.ensure()`.
    """
    unaddressed, checked = _scan_registry_calls()

    assert not unaddressed, (
        "these reach the registry with no browser named, so they act on the "
        "default one whatever the caller asked for: %s" % unaddressed)
    # 20 today. A floor rather than the number, because the point is that the
    # scan found the calls at all: a scan that matches nothing passes the
    # assertion above without reading a line of the module.
    assert len(checked) >= 18, (
        "only %d registry calls were found in %s; has the module moved?"
        % (len(checked), SERVER_PY.name))


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
            if isinstance(inner.func, ast.Name) and inner.func.id == "_retrying":
                found.add(node.name)
    return found


async def test_every_tool_that_reaches_a_browser_offers_a_way_to_name_it():
    """A tool that touches a browser with no way to say WHICH one always means
    the default, and a caller holding two browsers simply cannot use it - the
    surface would be addressable in fifteen places and mute in three.

    Which tools need an address is read from the code rather than listed here,
    so one written later is covered the day it is written. The check is against
    the SCHEMA the server publishes, not the Python signature: a parameter the
    client cannot see is a parameter that does not exist.

    ⛔ TWO EXEMPTIONS, and both are about the QUESTION rather than about the
    tool. `browser_list` asks which browsers a SESSION holds and `session_forget`
    deletes a whole session, closing every browser in it; neither is a question
    one browser can answer, so both take a session and no browser on purpose.
    They reach the registry per browser - that is what makes the scan find them -
    but the browsers are the ones the session already has, not one a caller
    named.

    Exempting them by name rather than by loosening the rule to "one of the two"
    keeps the rule able to catch the case it exists for: a tool that acts on a
    browser and cannot say which.

    Known-bad: delete `session_id` and `browser_id` from any one tool.
    """
    ASKS_ABOUT_THE_SESSION = {"browser_list", "session_forget"}
    needing = _tools_that_reach_a_browser() - ASKS_ABOUT_THE_SESSION
    assert len(needing) >= 18, (
        "only %d tools were found reaching a browser; has the module moved? %r"
        % (len(needing), sorted(needing)))

    published = {t.name: set(t.inputSchema.get("properties", {}))
                 for t in await server.mcp.list_tools()}
    gone = sorted(ASKS_ABOUT_THE_SESSION - set(published))
    assert not gone, (
        "exempted from needing a browser id, but the server no longer offers "
        "them: %r. An exemption that names nothing exempts nothing." % gone)
    unknown = sorted(needing - set(published))
    assert not unknown, "found in the source but not registered: %r" % unknown

    mute = {name: sorted(published[name]) for name in sorted(needing)
            if not {"session_id", "browser_id"} <= published[name]}
    assert not mute, (
        "these act on a browser the caller cannot name, so they always act on "
        "the default one: %s" % mute)
