"""MCP server exposing two stealth browsers, `main` and `support`.

⛔ THERE IS NO SESSION CONCEPT HERE, AND THAT IS DELIBERATE - not an omission,
and not the same claim this file made a day earlier when a session held up to
eight named browsers. This process serves exactly ONE piece of work: the two
fixed browsers above, and nothing a tool can enumerate, name or reach a SECOND
one of. `AIHAWK_SESSION_ID`, read once from the environment near the top of
this file, decides which saved file that one piece of work persists to - set
by whoever spawns this process, never by a tool argument, never published in
a schema, never something a model can read or pass. A model working through
this server cannot ask "what else is there" because there is no "else" to ask
about.

Tool names mirror the Microsoft Playwright MCP so prompts stay portable, with
one deliberate departure: there are no tab tools. A browser here drives ONE
page. Playwright's MCP offers `browser_tab_*` and this server briefly did too;
they were removed because the case they serve is better served by `support` -
a second tab carries the identity's cookies and fingerprint to the second
site, which is the one thing the two browsers exist to keep apart.

Config comes from STEALTHFOX_* env vars. `browser_open` starts a browser lazily
if nothing has, exactly as before.

Every tool here is a wrapper. The operations live in `actions.py` and the
browsers live in `registry.py`, so every client drives them through exactly
the same code rather than through a second implementation that would drift
from this one.

Transport is stdio by default, which is what existing clients expect. Set
STEALTHFOX_MCP_TRANSPORT=http to serve over streamable HTTP instead, which is
what lets more than one client attach to the same live browser.

THERE IS NO INTERFACE HERE, and that is the point rather than an omission. This
package served a two-pane page and a live view until 0.9.0, reaching the browser
through `registry` because it was in the same process. Both moved to `aihawk`,
which now reaches the browser over MCP like anybody else. What that buys is not
tidiness: it means no client has a privileged path, so the tools below are
provably sufficient for the flagship interface, because the flagship interface
is a client of them. A page kept inside the server is a page whose needs quietly
become the server's requirements.
"""
from __future__ import annotations

import asyncio
import atexit
import os
from contextlib import asynccontextmanager
from typing import Literal

from mcp.server.fastmcp import FastMCP, Image

from . import NOTHING_RUNNING, actions, identity, plan, store
from .registry import BrowserRegistry

# Kept for callers that imported it from here. The implementation moved.
_json_capped = actions.json_capped

def new_registry(**kwargs) -> BrowserRegistry:
    """A registry wired to write its sessions down.

    ⛔ ONE CONSTRUCTOR, USED BY THE SERVER AND BY THE TESTS. A test that builds
    a bare `BrowserRegistry` is testing a registry the product does not have,
    and the wiring below - the thing that makes a session survive the process -
    would be exercised by nothing. It is a function rather than a line because
    the tests need to build one with a factory that launches no browser, and
    the alternative was each of them repeating the wiring or, more likely, not.
    """
    reg = BrowserRegistry(**kwargs)
    reg.on_change = lambda key: remember()
    return reg


registry = new_registry()


#: Set by main(). Over stdio the SDK enters the lifespan once per process, so
#: its exit is where the browsers get closed; over streamable HTTP it enters
#: it once per client, where closing would kill the browser on every detach.
_close_on_lifespan_exit = False


@asynccontextmanager
async def _lifespan(_server):
    """Closes every browser on the way out, but only over stdio.

    Over streamable HTTP the SDK enters this per MCP session, which is per
    CLIENT, not once per process. Measured: with a client attached the machine
    had 7 firefox processes, and one second after that client disconnected it
    had 1 again. Closing here would therefore kill the browser every time
    somebody detached, which is the exact behaviour the registry exists to
    remove; there the close stays at process exit, below.

    Over stdio `Server.run` enters this exactly once, and its exit is the last
    moment the event loop that opened the browsers is still running. That is
    the moment to close them: the atexit hook below runs in a NEW loop, and a
    Playwright object closed from a loop other than its own never answers.
    Measured on Linux, 2026-09-06: a client that closed stdin with a page open
    waited 180 s for the process and gave up; with no page it took 0.2 s.
    """
    try:
        yield {}
    finally:
        if _close_on_lifespan_exit:
            await registry.close_all()


def _close_sessions_at_exit() -> None:
    """Best effort shutdown of every browser when the process itself ends,
    for the HTTP transport, where the lifespan cannot do it.

    A browser left behind is not a small leak here: Firefox launches a whole
    tree of processes, and an orphaned one goes on holding its profile
    directory and its port. Bounded, because this runs in a fresh event loop
    and an await on an object from the finished one does not return: ten
    seconds, then the process is allowed to end.
    """
    try:
        asyncio.run(asyncio.wait_for(registry.close_all(), 10))
    except Exception:
        pass


atexit.register(_close_sessions_at_exit)


# The ladder, stated once. Each tool's own description says what that tool does;
# nothing said which to REACH FOR FIRST, and a model that cannot find a way down
# the ladder invents one. Measured 2026-09-02, first run with a real model: it
# went from "click the select" straight to running `s.value='beta'` as script,
# skipping the two rungs in between - coordinates, and a screenshot - because
# nothing had told it they were rungs.
INSTRUCTIONS = """Drive the page the way a person would. Everything here goes
through the real pointer and the real keyboard.

Try things in this order. It matters, because a page can tell the difference.

1. A named tool with a selector: browser_click, browser_type,
   browser_select_option, browser_press_key. browser_snapshot gives you the
   selector for each element - pass it verbatim, it is built to be unambiguous.

2. Coordinates. browser_snapshot reports `at: [x, y]` for every element it
   lists, in viewport pixels. browser_click_at takes exactly those and moves the
   pointer there. This is the rung for anything a selector does not describe: a
   canvas, a slider, a map, a custom widget built out of divs.

3. Your eyes. browser_take_screenshot, find the thing in the picture, then
   browser_click_at on where it is. For what the snapshot does not list at all.

4. browser_evaluate, to READ what none of the above can see.

browser_evaluate refuses the obvious ways to act on the page, and names the tool
to use instead: assigning to value, checked or selected, or calling click(),
dispatchEvent(), submit() or requestSubmit(). All of those skip the keyboard and
the pointer, so the event arrives with isTrusted false - the single clearest
signal that something other than a person is driving, and avoiding it is what
this browser is for. When you want that, rung 2 or rung 3 is what you actually
want.

That refusal is a guardrail on the obvious road, not a wall around the field.
JavaScript has unlimited ways to say the same thing and this catches the ones
worth catching, so DO NOT read a silent pass as permission: if you find a way to
change the page through browser_evaluate, that is the bug, and saying so in your
answer is worth more than using it.

You do not need script to read state back, either. The snapshot carries
`checked` for a checkbox or radio and `value` for a select, alongside the text.

If you get to the bottom of the ladder and still cannot do the thing, say so in
your answer. A task reported as impossible is worth more than a task completed
in a way that gets you blocked.

There are two browsers, and every tool takes `browser`.

`main` is your own identity: its page, its cookies, its logins, its
fingerprint. That is where the work happens, and it is where a command goes
when it says nothing.

`support` is a helper for anything that must NOT touch that identity. The case
it exists for: you are signing up somewhere and need a mailbox for the
verification, so you open `support`, go to a throwaway-mail site there, take the
address, type it into the form in `main`, and come back to `support` for the
link. A second page inside `main` would carry the same cookies and the same
fingerprint to both sites, and then the account and the mailbox are one person
to anyone looking.

Each browser drives ONE page, and there is no way to open, list, choose or
close another: browser_navigate opens the page and every other tool acts on
it. When you need a second page, that is what `support` is. Going somewhere
else and coming back is a navigation, not a second window.

Open it with browser_open when the task needs it, and close it with
browser_close as soon as the task no longer needs it, before you give your
answer: it costs a real browser, it is not saved, and it goes away when this
server does. There is no third browser and no way to get one from here -
`main` and `support` are the whole of what this gives you."""


mcp = FastMCP("stealth", instructions=INSTRUCTIONS, lifespan=_lifespan)


#: The browser a caller means when it names nothing. Callers that were written
#: before browsers had names send neither id and must keep behaving exactly as
#: they did, so both defaults exist and resolve to one browser in one session.
DEFAULT_BROWSER_ID = "main"

#: The other one. See MAX_BROWSERS_PER_SESSION for why there are exactly two.
SUPPORT_BROWSER_ID = "support"

#: What a tool accepts for `browser`: a ROLE, never a name a caller invents.
Browser = Literal["main", "support"]

#: TWO browsers in one session, with fixed roles, and the number is a decision
#: rather than a measurement - which is the opposite of what it was until
#: 2026-09-11.
#:
#: It used to be eight, and the eight was measured: 61 processes and 6,515 MB,
#: the eighth taking 13.6 s to start against the first one's 6.8. Nothing about
#: that stopped being true. What changed is what a session MEANS. Identity lives
#: on the browser - seed, fingerprint, profile - so a session holding eight
#: browsers held eight identities while everything above it, the transcript and
#: the saved state and anything a person attaches to a session, was addressed
#: to one. "Whose is this?" had two possible answers and no way to choose.
#:
#: So a session is ONE identity, `main`, plus ONE helper beside it, `support`,
#: for the things that must not touch that identity: a temporary mailbox to
#: receive a verification, a lookup, a second opinion on a page. It is a
#: browser and not a tab because a tab would share cookies and fingerprint with
#: the site the identity is being built on, and the whole point of the helper
#: is that it does not. The helper is not saved and not restored - it dies with
#: the process - because a helper that survives IS a second identity, which is
#: the thing this number exists to rule out.
#:
#: The roles are NAMES A CALLER CANNOT INVENT. `browser` on every tool is a
#: closed choice, `main` or `support`, so nothing here ever holds a browser
#: called `b3` or `walmart-jobs` again. Everything that handled several - the
#: addressing, the registry keys - is still here and still correct, doing the
#: same job for two that it did for eight. The design that went with the eight
#: is in the workbench, under
#: `docs_research/chat-ui-performance/30-PROGETTO-sessioni-e-otto-browser.md`.
MAX_BROWSERS_PER_SESSION = 2


# ⛔ `_focus` STOOD HERE, an empty dict kept alive because the tests
# patched it. Nothing in the product had written to it since `browser_focus`
# was removed: with two fixed roles there is nothing to remember, because a
# command is about `main` unless it says `support`. State the product does
# not use, kept so a fixture can reset it, is the fixture holding the
# product's shape - so it is gone from both.



#: ⛔ WHERE THIS PROCESS'S OWN PIECE OF WORK COMES FROM, AND THE ONLY PLACE
#: THAT KNOWS IT EXISTS. Read from the environment ONCE, exactly like
#: `STEALTHFOX_SEED` or `STEALTHFOX_PROXY` in `plan.py` - never a tool
#: argument, never a name in a published schema, never something a model can
#: read, pass, list or invent. There is exactly one of these for the life of
#: the process, and nothing below can ask about, name, or reach a second one.
#:
#: Whoever spawns this process decides the value. The interface spawns one
#: server PER CONVERSATION and sets this to that conversation's own id, so two
#: conversations are two PROCESSES, each with its own saved browser on disk -
#: the join between "which conversation" and "which browsers it opened" is now
#: which process is running, not an argument any tool reads. A standalone
#: client (`uvx aihawk`, or this module run directly) never sets it and lands
#: on the same name every caller landed on before this had a name at all:
#: `DEFAULT_SESSION_ID`.
#:
#: The file on disk is unaffected: `store.save`/`load`/`erase` still take a
#: plain string and still write `sessions/<that string>.json`, exactly as
#: before. A file saved by an earlier build is found under the same name it
#: was saved under; nothing here migrates it.
_SESSION_ID = os.environ.get("AIHAWK_SESSION_ID") or store.DEFAULT_SESSION_ID

#: Whether the saved browser has been read into the registry yet. A single
#: flag and not a set keyed by id, because this process holds the one piece of
#: work named above and there is only ever one thing to restore.
_restored = False


def restore() -> bool:
    """Read the saved browser back, if there is one and it has not been read
    yet.

    Declares it rather than starting it: the identity comes back immediately
    and costs nothing, and the engine comes back when something is actually
    aimed at it. Answers whether anything was read.
    """
    global _restored
    if _restored:
        return False
    _restored = True
    saved = store.load(_SESSION_ID)
    if not saved:
        return False
    held = saved.get("browsers") or {}
    if held:
        # ⛔ A FILE WRITTEN BY AN OLDER BUILD CAN NAME EIGHT BROWSERS AND CALL
        # THEM ANYTHING, and this is the only door left that either can come
        # through: nothing in this process makes a browser outside the two
        # roles any more. A file saved by 0.38.0 with ten browsers called
        # `b-tech` and `walmart-jobs` would otherwise restore all ten under
        # those names.
        #
        # What comes back is ONE browser, as `main`: the one the file says was
        # in focus, because that is the browser the person left in front of
        # them, else the first by name. The rest are dropped from this
        # PROCESS and not deleted from the file - nothing here rewrites it
        # until it changes, and a build that gets rolled back should find
        # what it left. A saved `support` cannot exist from this build and is
        # not restored from an older one either: the helper is not an
        # identity.
        keep = saved.get("focus") if saved.get("focus") in held else None
        keep = keep or sorted(held)[0]
        held = {DEFAULT_BROWSER_ID: held[keep]}
    for name, config in held.items():
        key = "%s/%s" % (_SESSION_ID, name)
        # The identity is DECLARED - the browser does not start - and the tabs
        # are OWED, to be reopened by the wake that starts it. Kept apart from
        # the identity on purpose: `declare` writes the launch settings, and a
        # list of urls is not one of them. Handing them to the registry would
        # make it carry a fact about pages, which is the one thing it has
        # deliberately never known.
        owed = config.pop("urls", None)
        # ⛔ AND THE ENGINE COMES FROM THIS PROCESS, NOT FROM THE FILE. The file
        # deliberately does not carry `binary_path` - it is a path on this
        # machine, and a process started on another one must resolve an engine
        # rather than insist on one that is not there. Leaving it out of the
        # file was read as leaving it out of the BROWSER, so a restored browser
        # came back without the engine the person had named on the command
        # line: on a locally built one, with nothing to download, it could not
        # start at all. What the file says is who this browser is; what this
        # build was asked to run it on is not the file's to say.
        registry.declare(key, dict(config, **plan.engine_here()))
        if owed:
            _tabs_owed[key] = list(owed)
    return True


def focused() -> str:
    """The browser a command that names none is about: always `main`.

    Still a function, because every caller went through it while it could
    answer several things, and it still triggers the one-time restore - that
    is where a saved browser is read back in, and callers rely on the side
    effect.
    """
    restore()
    return DEFAULT_BROWSER_ID


#: The launch settings that say WHO a browser is, and so the ones a saved file
#: carries. Everything else in the launch kwargs describes the machine it ran
#: on, and writing those down would restore a browser onto the wrong one.
#:
#: ⛔ THESE ARE THE LAUNCH KWARGS' OWN NAMES, NOT THE TOOL ARGUMENTS' NAMES, and
#: the difference is not cosmetic. This list said `profile` for its first day,
#: which is what `browser_open` calls it; the launch kwarg is `profile_dir`, so
#: the filter matched nothing and the profile was the one field never saved -
#: the one field that carries the cookies and the logins a reopened browser is
#: FOR. Nothing failed: every browser came back with the right seed and the
#: right exit, logged out.
#:
#: `binary_path` is deliberately absent. It is a path on this machine, and a
#: browser reopened where that path means nothing must resolve an engine
#: rather than insist on one that is not there.
WHO_A_BROWSER_IS = ("seed", "proxy", "profile_dir", "headless")


def browsers_in() -> list:
    """The browsers here, by id, running or only declared.

    Read from the registry's own memory rather than from a list kept beside it,
    because a second list is a second truth: a browser dropped by a failed retry
    would still be in it, and the ceiling would refuse a slot that is free.

    Declared counts. A browser restored from a saved file has not started yet -
    it starts when something is aimed at it - but it holds a slot and it is one
    of the two here too.
    """
    restore()
    prefix = "%s/" % _SESSION_ID
    return sorted(k[len(prefix):] for k in registry.declared()
                  if k.startswith(prefix))


def remember() -> None:
    """Write the browsers held here down, as they stand now.

    Called after anything that changes what is HELD rather than on a timer, so
    the file on disk is never a version that existed only between two ticks.
    Hooked into the REGISTRY, through `new_registry`, whenever a browser gains
    or loses an identity - that is every way one comes to exist, including the
    lazy auto-start a caller that never calls `browser_open` uses.

    ⛔ A WRITE THAT FAILS COSTS THE SAVED FILE AND NOTHING ELSE. By the time
    this runs the browser is already built and correct, so a full disk or a
    home directory somebody made read-only must not turn a working
    `browser_open` into an error. Guarded here rather than at the call sites
    because this is the only function that writes: a guard at the callers
    would be one per caller, and the next caller would be the one without it.
    """
    prefix = "%s/" % _SESSION_ID
    browsers = {}
    for key in registry.declared():
        if not key.startswith(prefix):
            continue
        config = registry.config(key) or {}
        wrote = {k: v for k, v in config.items() if k in WHO_A_BROWSER_IS}
        # Where it was, so reopening gives back the work and not only the
        # person. A browser that has never been looked at contributes nothing
        # rather than an empty list: an empty list would mean "it had no tabs",
        # which is a different thing from "nobody has asked yet" and would wipe
        # the pages of a browser that is up and busy.
        been = _seen_tabs.get(key)
        if been:
            wrote["urls"] = been
        name = key[len(prefix):]
        if name == SUPPORT_BROWSER_ID:
            # ⛔ THE HELPER IS NOT WRITTEN DOWN. A support browser that comes
            # back after a restart is a second identity, which is exactly what
            # having two fixed roles exists to rule out. It lives for the task
            # and dies with the process.
            continue
        browsers[name] = wrote
    try:
        if not browsers:
            store.erase(_SESSION_ID)
            return
        store.save(_SESSION_ID, browsers, focus=DEFAULT_BROWSER_ID)
    except Exception:
        pass


def addressed(browser_id: str | None = None) -> str:
    """The registry key for one of the two browsers here.

    ⛔ The registry stores browsers by string key and knows nothing about what
    the key means, and that is deliberate: everything it already gets right -
    one lock per key so two callers racing start one browser rather than two,
    the configuration remembered so a rebuild is the SAME PERSON with the same
    seed and the same exit, tab numbering that does not restart across a
    rebuild - starts working per BROWSER the moment the key names one.
    Composing here buys all of it without touching a line of it.

    Everything in this module addresses through this function. A single call
    that still reaches for the bare default would look at one browser while its
    neighbours wrote to another, and nothing would raise.
    """
    restore()
    return "%s/%s" % (_SESSION_ID, browser_id or DEFAULT_BROWSER_ID)


#: Where each browser's tabs were, by composed key. Written whenever a browser
#: is handed out or listed, read by `remember` when the session is written down.
#:
#: ⛔ A CACHE AND NOT A SECOND TRUTH, and the difference is which way it flows.
#: The tabs live in the running browser; this only remembers what they were the
#: last time anybody looked, because `remember` is called from a synchronous
#: hook and asking a browser for its tabs is asynchronous. So it is at most one
#: command stale, and a session that ends between two looks comes back one
#: command behind rather than empty.
_seen_tabs: dict = {}

#: Tabs a saved session declared and that have not been reopened yet, by key.
#: Emptied by the wake that uses them, so a browser is restored ONCE: after that
#: its tabs are its own business and reopening them would fight the caller.
_tabs_owed: dict = {}


def _note_tabs(key: str, urls) -> None:
    """Remember where this browser's tabs are, and write it down if it moved.

    ⛔ ON THE CHANGE AND NOT ON EVERY COMMAND, and the difference is a disk
    write thirteen times a second. Every tool call passes through `ready`, and
    the live view's frames are tool calls: saving from there unconditionally
    would put the session file in the path of the frame pump. Pages move rarely
    compared to how often a browser is touched, so comparing first turns "every
    command" into "every navigation", which is what the file is actually about.
    """
    if urls is None:
        return
    fresh = [u for u in urls if u]
    if _seen_tabs.get(key) == fresh:
        return
    _seen_tabs[key] = fresh
    remember()


async def ready(browser_id=None):
    """This browser, started, and back where it was.

    ⛔ ONE FUNNEL, AND THAT IS THE WHOLE POINT OF IT EXISTING. Every tool used to
    write `registry.ensure(addressed(...))` for itself - fourteen of them, plus
    the retry - so "what it takes to hand somebody a usable browser" was a fact
    known in fifteen places. The moment it stopped being just `ensure` - a
    declared browser now has tabs owed to it - fifteen places would have had to
    learn the same new step, and the one that did not would hand back a browser
    that came home empty. The rule this follows is the project's: after the fix,
    the places that know a thing are one.

    Reopening happens ONCE per browser and only for a page a SAVED file
    declared. A browser that has been woken owns where it goes next, and a wake
    that kept reopening would fight whoever is using it.

    ⛔ ONE PAGE, WHICH IS WHAT MAKES THE REST OF THIS SURFACE TRUE. This loop
    used to reopen every url the file held, one `new_page` each - so a saved
    file was the one input that could put a browser into a state the
    instructions call impossible ("there is no way to open, list, choose or
    close another"), with no tool left to inspect or close the extras. It also
    made `browser_status` blame the site for pages this function had opened.
    The file still records every url it saw, because that is an observation
    and a browser can legitimately hold several; what is restored is the one
    the browser was ON, which is the LAST of them - the same page the old loop
    left active, since every `new_page` moved the active one along.
    """
    at = addressed(browser_id)
    owed = _tabs_owed.pop(at, None)
    session = await registry.ensure(at)
    if owed:
        try:
            await session.new_page()
            await actions.navigate(session, owed[-1])
        except Exception:
            # A url that will not load must not cost the browser. It is up, it
            # is the right person, and refusing to hand it back would turn a
            # stale bookmark into a session somebody cannot use.
            pass
    try:
        # The urls only. `describe_pages` also fetches each tab's TITLE, which
        # is a round trip per tab, and this runs on every command - including
        # every frame of the live view, twenty-five times a second.
        _note_tabs(at, session.where_pages_are())
    except Exception:
        pass
    return session


def looking(browser_id=None):
    """This browser only if it is ALREADY running. Never starts one.

    ⛔ A QUESTION IS NOT A COMMAND, AND `ready` CANNOT TELL THEM APART, because
    it starts whatever it resolves. That is exactly right for an instruction
    and exactly wrong for a look, and the difference is measurable: on 0.38.0,
    drawing the live panes of a conversation nobody had asked anything took the
    machine from 9 firefox processes to 16, roughly 800 MB and seven seconds,
    and `browser_watch` then answered an error - so the engine the look had
    started was not even used for the look.

    `registry.peek` has said this was needed since the day it was written -
    "for callers that want to know whether a browser is up, such as a live
    view" - and had no callers. What kept it unused was a belief written down
    in the interface beside the flag it invented instead: "over MCP there is no
    way to ask is one running without starting one". There is; this is it.

    A browser this answers `None` for is not gone, it is asleep: it was
    declared and has not been needed yet, and the next COMMAND aimed at it
    still starts it as the same person, through `ready`. Only looking stopped
    waking it.
    """
    return registry.peek(addressed(browser_id))


async def _retrying(fn, *args, browser_id=None, **kwargs):
    """Run an action on one browser, and on failure rebuild it once and retry.

    A browser that died between two calls is the ordinary case here, not an
    exotic one: the object is still intact, so the failure surfaces inside the
    action rather than when it was handed out.

    The rebuild is addressed too. Dropping and re-ensuring the DEFAULT key while
    the action was aimed at the other browser would kill a browser nobody asked
    about and hand back the wrong one, which is the same class of mistake as
    rebuilding from the environment: it succeeds, and it succeeds at the wrong
    thing.
    """
    at = addressed(browser_id)
    session = await ready(browser_id)
    try:
        return await fn(session, *args, **kwargs)
    except Exception:
        # ⛔ THE TABS ARE OWED AGAIN, or the recovery gives back half a browser.
        # `drop` keeps the identity on purpose - the replacement is the same
        # person - and until this line the pages were not part of "the same":
        # a browser that died mid-command came back correct and empty, and the
        # only way to notice was to go looking for your own work. What it had
        # is what was last seen, which is what would have been saved had the
        # process ended instead.
        been = _seen_tabs.get(at)
        if been:
            _tabs_owed[at] = list(been)
        await registry.drop(at)
        session = await ready(browser_id)
        return await fn(session, *args, **kwargs)


# --- the two browsers -------------------------------------------------------

@mcp.tool()
async def browser_open(browser: Browser | None = None, seed: int | None = None,
                       proxy: str | None = None, profile: str | None = None) -> str:
    """Open `main` or `support`, or reopen one as somebody else.

    `main` is your own identity: its page, cookies, fingerprint, logins.
    `support` is a helper beside it for what must not touch that identity - a
    temporary mailbox for a verification, a lookup the site must not connect to
    the account. They share nothing. `support` is yours to manage: open it when
    the task needs a second identity, and close it with browser_close as soon
    as the task no longer needs it, before you answer. It is not saved.

    Called on a browser that is already up, this REOPENS it with the settings
    given, and what it held is gone.

    seed     the identity; same seed, same fingerprint. Left out, one is drawn.
    profile  a directory keeping cookies, logins and the seed between opens;
             "" means none.
    proxy    the exit, `http://user:pass@host:port` or `socks5://host:port`;
             "" means this machine's own address; left out for `support`, it
             shares the exit `main` has.
    """
    # ⛔ THE DESCRIPTION ABOVE IS WHAT THE MODEL READS, AND IT IS CUT AT 1024
    # CHARACTERS BY THE API. The version before this one was 1996: the model
    # saw it end mid-word inside the paragraph about profiles, and the sentence
    # that told it to close the helper was past the cut. A gate in the server
    # tests now holds every tool's description under the limit. What was cut
    # from here, kept for a reader of the source: a profile also keeps its
    # seed, so a login does not come back wearing different hardware; a profile
    # does NOT pin its exit - timezone, locale and geography come from the
    # exit, so the same login arriving from another country is as visible as
    # one arriving on different hardware; and `support` takes a proxy of its
    # own only when it is meant to look different from `main`.
    role = browser or DEFAULT_BROWSER_ID

    if role not in (DEFAULT_BROWSER_ID, SUPPORT_BROWSER_ID):
        # ⛔ THE SCHEMA ALREADY REFUSES THIS AND THIS STILL REFUSES IT. `browser`
        # is a Literal, so a model that invents a name is turned back by the
        # protocol before it reaches here - but the schema is not the only door:
        # the interface and the tests call these functions directly, and a
        # third browser called `b3` is the thing two fixed roles exist to rule
        # out.
        return ("there are two browsers here: `main`, your own identity, and "
                "`support`, the helper beside it. There is no %r." % role)

    try:
        chosen = plan.plan_session(seed=seed, proxy=proxy, profile=profile)
    except (identity.IdentityConflict, ValueError) as exc:
        # Refused, not guessed. Every case here is one where continuing would
        # hand the caller a different person than the one they asked for, and
        # whatever is already running is deliberately left alone: a refusal
        # must not cost somebody the browser they already had.
        return "refused: %s" % exc
    settings = chosen.kwargs

    at = addressed(role)
    main_config = registry.config(addressed())
    if role == SUPPORT_BROWSER_ID and proxy is None and main_config is not None:
        # ⛔ THE HELPER INHERITS THE EXIT, BY DEFAULT AND ON PURPOSE. A helper
        # that came out through a different address than the identity it helps
        # would be the one thing on the wire saying "these two are not the same
        # person, and yet they work together". Its FINGERPRINT is its own - a
        # fresh seed unless given - because the two must not read as one browser
        # either. Same exit, different person: a colleague at the next desk.
        #
        # Copied AFTER planning and as the resolved dict, not passed in as a
        # url: the plan takes a url and `main` holds the dict it was launched
        # with, and re-deriving one from the other is a second reader of the
        # same fact. And it copies the ABSENCE too: a `main` that goes out
        # direct has no `proxy` key, so the helper goes out direct as well,
        # rather than picking up an environment proxy `main` never used. Only
        # when `main` has not been declared at all is the environment left to
        # decide, which is what `main` itself will do when it starts.
        settings.pop("proxy", None)
        if main_config.get("proxy"):
            settings["proxy"] = main_config["proxy"]
    try:
        await registry.restart(at, **settings)
    except Exception as exc:
        # ⛔ Said plainly, because the dangerous reading is "that failed, carry
        # on". Nothing is running there now, and every later tool will repeat
        # this refusal rather than quietly starting a browser without the exit
        # that was asked for.
        return ("the %s browser did NOT start: %s\n"
                "Nothing is browsing there, and the tools will keep failing "
                "until browser_open succeeds. A proxy that is down is the "
                "usual cause; try another exit, or pass proxy=\"\" to go out "
                "from this machine knowing that is what you are doing."
                % (role, exc))

    remember()
    return "the %s browser is open. %s" % (role, plan.describe(registry.config(at) or {}))


@mcp.tool()
async def browser_close(browser: Browser | None = None) -> str:
    """Close one browser and free what it was holding.

    The page it had is gone with it. The other browser is not touched.

    Closing FORGETS who that browser was: opening it again is a new stranger,
    not the same person resumed. That is deliberate - a browser somebody shut
    down should not come back wearing its old identity.
    """
    name = browser or DEFAULT_BROWSER_ID
    existed = await registry.forget(addressed(name))

    left = browsers_in()
    remember()
    if not existed:
        return "the %s browser is not open." % name
    return ("the %s browser is closed. Still open: %s."
            % (name, ", ".join(left) if left else "none"))


@mcp.tool()
async def browser_list() -> str:
    """Which of the two browsers are open, where each one is, and which one
    the commands that name none go to.

    Answers JSON: `focus`, `limit`, `note`, and `browsers` - each with `id`,
    `running`, `focused`, `url` (the page it is on) and `urls` (every page it
    holds, which is more than one only when a site opened one). A browser that
    is not running has been declared and has not been needed yet; the next
    command aimed at it starts it as the same person.

    Starts nothing: it reports what is running, so asking is free.
    """
    have = browsers_in()
    here = focused()
    rows = []
    for name in have:
        session = registry.peek(addressed(name))
        # `urls` is a list, or None for "running and unreadable" - the two are
        # different answers and the pane draws them differently, which is why
        # the type says so rather than collapsing the second into an empty list.
        urls: list | None = []
        here_url, running = "", session is not None
        if session is not None:
            try:
                pages = await session.describe_pages()
                urls = [p["url"] or "" for p in pages]
                # ⛔ WHICH PAGE IS THE LIVE ONE, and it has to come from here
                # now. The interface used to learn the address from the tab
                # tool, which marked the active row; with the tab tools gone
                # this is the only tool that still knows, and the answer the
                # address bar needs is the ACTIVE page rather than the first -
                # a site that opens one of its own makes those two different,
                # and `session.page()` drives the newest live one.
                shown = next((p for p in pages if p["active"]), pages[0] if pages else None)
                here_url = (shown["url"] or "") if shown else ""
                _note_tabs(addressed(name), urls)
            except Exception:
                # Readable as a state rather than as an absence: a browser whose
                # pages cannot be read is not a browser with no pages, and a pane
                # drawing "nothing open" over a live window would be a lie.
                running, urls = True, None
        rows.append({"id": name, "running": running, "focused": name == here,
                     "url": here_url, "urls": urls})
    # ⛔ JSON, WHERE THIS ANSWERED PROSE UNTIL 0.18.0, and the reason is the
    # stated architecture rather than taste: the interface is a client of these
    # tools like anybody else, with no privileged path, so a workspace that has
    # to draw one pane per browser needs this question answered in a shape a
    # program can read. The alternative was the page parsing a sentence, which
    # is two readers of one wire format, or a second tool saying the same thing,
    # which is two sources for one fact. Models read JSON from these tools
    # without trouble; `note` carries the sentence that used to be the whole
    # answer, because "there is nothing here yet" is worth saying in words.
    return actions.json_capped({
        "focus": here,
        "limit": MAX_BROWSERS_PER_SESSION,
        "browsers": rows,
        "note": ("no browser open yet. The next tool that needs a page will open "
                 "one, or call browser_open to choose who it is."
                 if not rows else
                 "%d of %d browsers. Commands that name none go to %s."
                 % (len(rows), MAX_BROWSERS_PER_SESSION, here)),
    })


# ⛔ `browser_focus` STOOD HERE AND IS GONE WITH THE THING IT CHOSE BETWEEN. It
# said which of several browsers unaddressed commands land on. There are two
# now, with fixed roles, and a command is about `main` unless it says
# `support` - every time, on every tool. A focus would be hidden state a model
# has to track, and the way that fails is a command meant for the identity
# landing in the helper because the previous one did.


# --- who is browsing ---------------------------------------------------------

@mcp.tool()
async def browser_status(browser: Browser | None = None) -> str:
    """Who is browsing right now: the identity, the exit, the profile and the page.

    Ask whenever you need to know which person the browser currently is, or
    from where its traffic leaves. The seed is what you would pass to
    `browser_open` to become this person again, so this is also how you
    record an identity worth repeating.

    It starts nothing. If no browser is running yet it says so, because until
    one is running there is no identity to report.

    `browser` is `main` unless you say `support`, and they share nothing.
    """
    at = addressed(browser)
    config = registry.config(at)
    if config is None:
        return ("no browser is running yet, so there is no identity to "
                "report. The next tool that needs a page will start one, or "
                "call browser_open to choose who it is.")

    session = registry.peek(at)
    if session is None:
        where = "the browser is not up; the next tool restarts it as this person"
    else:
        try:
            rows = await session.describe_pages()
            here = next((r for r in rows if r["active"]), rows[0] if rows else None)
            where = (here["url"] or "blank") if here else "no page open yet"
            # ⛔ COUNTED, AND NOT BLAMED ON ANYBODY. A caller cannot make,
            # choose or close a page, so the honest report of a second one is
            # that it is there - not who opened it. The first version of this
            # line said "the site has opened %d more", and measured on a
            # restored browser it was false: `ready` was opening them itself,
            # one per saved url. Fixing that left this sentence true, and it
            # still does not say it, because a confident wrong cause is the
            # defect this project removed from `navigate` ("navigated to
            # {url}" whatever happened). Counted, never named: naming them
            # would offer a vocabulary nothing here accepts.
            if len(rows) > 1:
                where += " (%d other pages are open in this browser)" % (len(rows) - 1)
        except Exception:
            where = "the page is unreadable"

    return plan.describe(config) + " page: %s." % where


# ⛔ THE FOUR TAB TOOLS STOOD HERE AND ARE GONE (2026-09-11, owner's decision:
# "si usa solo la tab principale e stop, se servono altre tab abbiamo il
# browser di support"). A browser drives ONE page. The answer to "I need a
# second page" is not a second tab, it is `support` - which is a better answer
# for the case that actually comes up, because a tab in `main` carries the
# identity's cookies and fingerprint to the second site while `support` does
# not. That argument was already written in the instructions this server hands
# every model; the tools contradicted it.
#
# What the removal does NOT claim is that a browser has exactly one page. A
# site opens one whenever it likes - `target=_blank`, `window.open` - so the
# machinery that decides WHICH page a command acts on stays exactly as it was,
# in `session.page()`. What is gone is any way for a caller to make, list,
# choose or close one: `browser_navigate` opens the first page by itself, and
# everything else acts on the page that is there.


# --- reading ---------------------------------------------------------------

@mcp.tool()
async def browser_navigate(url: str, wait_until: str = "domcontentloaded",
                           browser: Browser | None = None) -> str:
    """Go to a url in this browser's page, opening it if none exists.

    Answers with the HTTP status the server gave and the url actually landed
    on, which is not always the one asked for: a redirect to a login wall or a
    regional domain shows up here. Read the status before trusting the page -
    a 404 or a 403 still has a document, and reading it as content is the
    mistake this reply exists to prevent.

    wait_until is "domcontentloaded" by default, which returns as soon as the
    markup is parsed. Use "load" when the page needs its images and stylesheets,
    or "networkidle" for a single-page app that fetches its content after
    load.

    `browser` is `main` unless you say `support`, and they share nothing."""
    return await _retrying(actions.navigate, url, wait_until=wait_until,
                           browser_id=browser)


@mcp.tool()
async def browser_read_text(selector: str = "body", max_chars: int = 6000,
                            browser: Browser | None = None) -> str:
    """The visible text of an element, with the markup gone.

    The cheapest way to read a page. Narrow the selector when you know where the
    answer is; use browser_read_html instead when the structure matters, or
    browser_snapshot when you need something to click.

    Long text is cut at max_chars (6000 by default) and the cut is marked in
    what comes back, so text that ends without that marker is the whole thing.

    `browser` is `main` unless you say `support`, and they share nothing."""
    return await actions.read_text(
        await ready(browser),
        selector, max_chars)


@mcp.tool()
async def browser_snapshot(max_chars: int = 0, browser: Browser | None = None) -> str:
    """Title, url, and the interactive elements that are actually visible.

    Each element carries a `selector` when one can reach it: pass that string to
    browser_click or browser_type VERBATIM. It is built to match exactly one
    element, which the obvious selector often does not - measured across 958
    elements on real pages, 88% could be addressed but only 48% unambiguously,
    and Playwright acts on the first match, so a caller aiming at the third of
    five identical links would silently hit the first.

    Elements with no `selector` carry `at`, the centre coordinates, for
    browser_click_at.

    Not the accessibility tree: on a real sign-up page a single country
    `<select>` contributes about two hundred `<option>` nodes, which fill the
    character cap before the form the caller was looking for appears at all.

    `browser` is `main` unless you say `support`, and they share nothing.
    """
    return await actions.snapshot(
        await ready(browser), max_chars)


@mcp.tool()
async def browser_read_html(mode: str = "form", browser: Browser | None = None) -> str:
    """The page's HTML, cleaned down to what is worth reading.

    Use this when the STRUCTURE matters - a form and its labels, a table, what
    a control is wired to. `browser_snapshot` gives a flat inventory of things
    to click; this keeps the markup and the relationships inside it.

    mode="form" keeps the interactive surface and the text explaining it,
    mode="text" returns the prose alone, mode="full" keeps the structure with
    the noise and the attribute soup removed.

    Unlike browser_read_text this is NOT capped: it returns the whole reduced
    page, tens of thousands of characters on a large one. Cutting markup in the
    middle leaves tags that mean nothing, so it is not cut - but the answer can
    be long. Reach for browser_snapshot when you only need something to click.

    `browser` is `main` unless you say `support`, and they share nothing.
    """
    return await actions.read_html(
        await ready(browser), mode)


@mcp.tool()
async def browser_take_screenshot(browser: Browser | None = None) -> Image:
    """One screenshot of this browser's page, on demand.

    `browser` is `main` unless you say `support`, and they share nothing."""
    png = await actions.screenshot_png(
        await ready(browser))
    return Image(data=png, format="png")


@mcp.tool()
async def browser_watch(browser: Browser | None = None) -> Image:
    """The whole browser window as a person at the machine sees it: tab strip,
    address bar, the page and the pointer, from a live capture kept running on
    that page. For watching the work, not for acting on it: the picture
    is window pixels, so do not feed its coordinates to browser_click_at; use
    browser_take_screenshot for that.

    Starts nothing. A browser that is not running has no window, so this
    refuses rather than opening one to photograph: a look is not a command, and
    the live panes call this many times a second.

    `browser` is `main` unless you say `support`, and they share nothing."""
    session = looking(browser)
    if session is None:
        # It REFUSES rather than answering the sentence, and only because the
        # type says so: this is declared to return an Image, and `Image | str`
        # is not a schema pydantic will build - measured, five test modules
        # refuse to import. A refusal reaches a client as an error result
        # carrying the reason, which every client already handles.
        raise RuntimeError(NOTHING_RUNNING)
    jpeg = await actions.watch_jpeg(session)
    return Image(data=jpeg, format="jpeg")


# --- acting ----------------------------------------------------------------

@mcp.tool()
async def browser_click(selector: str, browser: Browser | None = None) -> str:
    """Click the first element matching a CSS selector.

    Scrolls it into view and waits for it to be clickable. When no selector can
    describe the target, use browser_click_at with coordinates from
    browser_snapshot.

    `browser` is `main` unless you say `support`, and they share nothing."""
    return await actions.click(
        await ready(browser), selector)


@mcp.tool()
async def browser_click_at(x: float, y: float, hold_seconds: float = 0.0,
                           browser: Browser | None = None) -> Image:
    """Click (or press-and-hold) a raw viewport coordinate instead of a
    selector - for targets a selector cannot reliably reach: a slider track, a
    canvas-drawn captcha, a precise point inside a wider element. Moves the
    pointer there first (no teleport), then down, then up, holding first if
    hold_seconds is set. Returns a screenshot taken right after release.

    Coordinates are relative to the VIEWPORT, not to the page, so the ones in a
    snapshot go stale the moment anything scrolls. Nothing raises when that
    happens: the click lands on whatever is at that spot now. Take a fresh
    snapshot after anything that could have moved the page, and prefer
    browser_click with the element's `selector` whenever it has one.

    `browser` is `main` unless you say `support`, and they share nothing."""
    # hold_seconds needs invisible-playwright 0.9.0 or newer to mean anything:
    # in every earlier version the wait it is built on returned instantly, so
    # the press and the release happened in the same frame and the hold never
    # happened, on the one tool that exists for sliders and press-and-hold
    # challenges. The floor in pyproject.toml is set accordingly. Said here and
    # not in the description above, which the API cuts at 1024 characters.
    png = await actions.click_at(
        await ready(browser),
        x, y, hold_seconds)
    return Image(data=png, format="png")


@mcp.tool()
async def browser_type(selector: str, text: str, browser: Browser | None = None) -> str:
    """Fill a field, replacing whatever it holds.

    This sets the value rather than typing key by key, so it will not fire the
    per-keystroke handlers an autocomplete needs. For those, click the field and
    use browser_press_key.

    `browser` is `main` unless you say `support`, and they share nothing."""
    return await actions.type_text(
        await ready(browser), selector, text)


@mcp.tool()
async def browser_select_option(selector: str, value: str,
                                browser: Browser | None = None) -> str:
    """Choose an option in a dropdown (`<select>`), by its visible label or by
    its value.

    Use this rather than clicking the dropdown and pressing arrow keys: a click
    plus arrows cannot tell you which row it landed on, and setting the value
    through browser_evaluate changes it without the page seeing a real
    interaction.

    `browser` is `main` unless you say `support`, and they share nothing."""
    return await actions.select_option(
        await ready(browser), selector, value)


@mcp.tool()
async def browser_press_key(key: str, browser: Browser | None = None) -> str:
    """Press a key on whatever has focus: "Enter", "Tab", "Escape",
    "ArrowDown", "Control+a", or a single character.

    `browser` is `main` unless you say `support`, and they share nothing."""
    return await actions.press_key(
        await ready(browser), key)


@mcp.tool()
async def browser_evaluate(expression: str, browser: Browser | None = None) -> str:
    """READ from the page with JavaScript and get the result as JSON.

    For what the other tools cannot see: a computed style, a value held in a
    framework's state, the length of a list.

    Acting on the page is refused, and the refusal names the tool to use.
    Assigning to `value`, `checked` or `selected`, or calling `click()`,
    `dispatchEvent()`, `submit()` or `requestSubmit()`, changes the page without
    a real keystroke or pointer, and a page can tell. Use browser_click,
    browser_type or browser_select_option instead; they do the same thing
    through the pointer and the keyboard. Reading any of those properties is
    fine.

    The refusal catches the obvious spellings, not every possible one. A script
    that slips past it is still the wrong way to do the thing: report it in your
    answer rather than using it.

    `browser` is `main` unless you say `support`, and they share nothing."""
    return await actions.evaluate(
        await ready(browser), expression)


def main() -> None:
    global _close_on_lifespan_exit
    transport = os.environ.get("STEALTHFOX_MCP_TRANSPORT", "stdio").strip().lower()
    if transport in ("http", "streamable-http"):
        # streamable-http ships with the `mcp` package, which already requires
        # starlette and uvicorn, so serving over HTTP costs no new dependency.
        mcp.settings.host = os.environ.get("STEALTHFOX_MCP_HOST", "127.0.0.1")
        mcp.settings.port = int(os.environ.get("STEALTHFOX_MCP_PORT", "8765"))
        mcp.run(transport="streamable-http")
    else:
        _close_on_lifespan_exit = True
        mcp.run()


if __name__ == "__main__":
    main()
