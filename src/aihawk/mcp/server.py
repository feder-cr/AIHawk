"""MCP server exposing browser_* tools over stealth sessions.

Tool names mirror the Microsoft Playwright MCP so prompts stay portable.
Config comes from STEALTHFOX_* env vars; a session starts lazily on first use.

Every tool here is a wrapper. The operations live in `actions.py` and the
sessions live in `registry.py`, so every client drives the browser through
exactly the same code rather than through a second implementation that would
drift from this one.

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

from mcp.server.fastmcp import FastMCP, Image

from . import actions, identity, plan
from .registry import DEFAULT_SESSION_ID, SessionRegistry

# Kept for callers that imported it from here. The implementation moved.
_json_capped = actions.json_capped

registry = SessionRegistry()


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
in a way that gets the session blocked."""


mcp = FastMCP("stealth", instructions=INSTRUCTIONS, lifespan=_lifespan)


#: The browser a caller means when it names nothing. Callers that were written
#: before browsers had names send neither id and must keep behaving exactly as
#: they did, so both defaults exist and resolve to one browser in one session.
DEFAULT_BROWSER_ID = "main"

#: Up to eight browsers in one session, and the ceiling is a measurement rather
#: than a taste: eight live browsers were measured at 61 processes and 6,515 MB
#: on 2026-09-08, with the eighth taking 13.6 s to start against the first one's
#: 6.8. The design that goes with this number is in the workbench, under
#: `docs_research/chat-ui-performance/30-PROGETTO-sessioni-e-otto-browser.md`.
MAX_BROWSERS_PER_SESSION = 8


#: Which browser a session's unaddressed commands land on. A session with one
#: browser never touches this; a session with several needs somewhere to say
#: "this one for now", or every call would have to repeat the id and the first
#: one forgotten would act on a browser nobody meant.
_focus: dict = {}


def focused(session_id: str | None = None) -> str:
    """The browser this session's unaddressed commands go to."""
    return _focus.get(session_id or DEFAULT_SESSION_ID, DEFAULT_BROWSER_ID)


def browsers_in(session_id: str | None = None) -> list:
    """The browsers this session has, by id.

    Read from the registry's keys rather than from a list kept beside them,
    because a second list is a second truth: a browser dropped by a failed retry
    would still be in it, and the ceiling would refuse a slot that is free.
    """
    prefix = "%s/" % (session_id or DEFAULT_SESSION_ID)
    return sorted(k[len(prefix):] for k in registry.ids() if k.startswith(prefix))


def addressed(session_id: str | None = None, browser_id: str | None = None) -> str:
    """The registry key for one browser inside one session.

    ⛔ The registry stores browsers by string key and knows nothing about
    sessions, and that is deliberate: everything it already gets right - one
    lock per key so two callers racing start one browser rather than two, the
    configuration remembered so a rebuild is the SAME PERSON with the same seed
    and the same exit, tab numbering that does not restart across a rebuild -
    starts working per BROWSER the moment the key names one. Composing here buys
    all of it without touching a line of it.

    Everything in this module addresses through this function. A single call
    that still reaches for the bare default would look at one browser while its
    neighbours wrote to another, and nothing would raise.
    """
    return "%s/%s" % (session_id or DEFAULT_SESSION_ID,
                      browser_id or focused(session_id))


async def _retrying(fn, *args, session_id=None, browser_id=None, **kwargs):
    """Run an action on one browser, and on failure rebuild it once and retry.

    A browser that died between two calls is the ordinary case here, not an
    exotic one: the object is still intact, so the failure surfaces inside the
    action rather than when the session was handed out.

    The rebuild is addressed too. Dropping and re-ensuring the DEFAULT key while
    the action was aimed at another browser would kill a browser nobody asked
    about and hand back the wrong one, which is the same class of mistake as
    rebuilding from the environment: it succeeds, and it succeeds at the wrong
    thing.
    """
    at = addressed(session_id, browser_id)
    session = await registry.ensure(at)
    try:
        return await fn(session, *args, **kwargs)
    except Exception:
        await registry.drop(at)
        session = await registry.ensure(at)
        return await fn(session, *args, **kwargs)


# --- the browsers a session holds ------------------------------------------

@mcp.tool()
async def browser_open(browser_id: str | None = None, seed: int | None = None,
                       proxy: str | None = None, profile: str | None = None,
                       session_id: str | None = None) -> str:
    """Open ANOTHER browser in this session, and make it the one commands go to.

    A session can hold several browsers at once, each with its own tabs, its own
    cookies and its own identity: one for the dashboard, one for the docs, one
    logged in as somebody else. They do not share anything, so work in one
    cannot disturb another.

    Give `browser_id` a name you will recognise, or let one be chosen. `seed`,
    `proxy` and `profile` decide who this browser is, exactly as in
    session_start, and they apply to this browser alone.

    Opening one takes several seconds and costs real memory, so open what you
    need and close what you stop using: browser_close frees it.
    """
    at_session = session_id or DEFAULT_SESSION_ID
    have = browsers_in(at_session)

    if browser_id is None:
        # Never a name already in use, and never one that was in use earlier in
        # this session: reusing it would hand somebody a browser they think they
        # opened and somebody else thinks they still hold.
        n = 1
        while ("b%d" % n) in have:
            n += 1
        browser_id = "b%d" % n
    elif browser_id in have:
        return ("session %s already has a browser called %s. Use it by naming "
                "it, or close it first." % (at_session, browser_id))

    if len(have) >= MAX_BROWSERS_PER_SESSION:
        # The ceiling says what it costs, because a refusal that only says "no"
        # invites the reader to raise the number.
        return ("session %s already holds %d browsers, which is the limit. "
                "Eight live browsers were measured at 61 processes and about "
                "6.5 GB, with the eighth taking twice as long to start as the "
                "first, so the ceiling is a real cost and not a formality. "
                "Close one with browser_close before opening another. Open "
                "now: %s." % (at_session, len(have), ", ".join(have)))

    at = addressed(at_session, browser_id)
    settings = plan.plan_session(seed=seed, proxy=proxy, profile=profile).kwargs
    try:
        await registry.restart(at, **settings)
    except Exception as exc:
        return "browser %s could not start: %s" % (browser_id, exc)

    _focus[at_session] = browser_id
    return ("browser %s is open in session %s and is now the one unaddressed "
            "commands go to. %s" % (browser_id, at_session,
                                    plan.describe(registry.config(at) or {})))


@mcp.tool()
async def browser_close(browser_id: str | None = None,
                        session_id: str | None = None) -> str:
    """Close one browser of this session and free what it was holding.

    The tabs it had are gone with it. The other browsers in the session are not
    touched, and neither is the conversation.

    Closing FORGETS who that browser was: a later browser opened under the same
    name is a new stranger, not the same person resumed. That is deliberate -
    a browser somebody shut down should not come back wearing its old identity.
    """
    at_session = session_id or DEFAULT_SESSION_ID
    name = browser_id or focused(at_session)
    existed = await registry.forget(addressed(at_session, name))

    if _focus.get(at_session) == name:
        _focus.pop(at_session, None)
    left = browsers_in(at_session)
    if not existed:
        return "session %s has no browser called %s." % (at_session, name)
    return ("browser %s is closed. Still open in session %s: %s."
            % (name, at_session, ", ".join(left) if left else "none"))


@mcp.tool()
async def browser_list(session_id: str | None = None) -> str:
    """Which browsers this session holds, and which one commands go to.

    Starts nothing: it reports what is running, so asking is free.
    """
    at_session = session_id or DEFAULT_SESSION_ID
    have = browsers_in(at_session)
    if not have:
        return ("session %s has no browser open yet. The next tool that needs a "
                "page will open one, or call browser_open to choose who it is."
                % at_session)

    here = focused(at_session)
    rows = []
    for name in have:
        session = registry.peek(addressed(at_session, name))
        where = ""
        if session is not None:
            try:
                pages = await session.describe_pages()
                where = "; ".join(p["url"] or "blank" for p in pages) or "no tabs"
            except Exception:
                where = "tabs unreadable"
        else:
            where = "not up; the next command restarts it as the same person"
        rows.append("%s%s: %s" % (name, " (commands go here)" if name == here else "",
                                 where))
    return "session %s holds %d of %d browsers. %s" % (
        at_session, len(have), MAX_BROWSERS_PER_SESSION, " | ".join(rows))


@mcp.tool()
async def browser_focus(browser_id: str, session_id: str | None = None) -> str:
    """Choose which browser this session's unaddressed commands go to.

    Every tool can still name a browser and reach it whatever the focus is; this
    only decides where the ones that name none land, so a run of commands on one
    browser does not have to repeat its id.
    """
    at_session = session_id or DEFAULT_SESSION_ID
    have = browsers_in(at_session)
    if browser_id not in have:
        return ("session %s has no browser called %s. Open: %s."
                % (at_session, browser_id, ", ".join(have) if have else "none"))
    _focus[at_session] = browser_id
    return "commands without a browser_id now go to %s." % browser_id


# --- who is browsing -------------------------------------------------------

@mcp.tool()
async def session_status(session_id: str | None = None,
                         browser_id: str | None = None) -> str:
    """Who is browsing right now: the identity, the exit, the profile and the tabs.

    Ask whenever you need to know which person the browser currently is, or from
    where its traffic leaves. The seed is what you would pass to `session_start`
    to become this person again, so this is also how you record a session that
    is worth repeating.

    It starts nothing. If no browser is running yet it says so, because until
    one is running there is no identity to report.

    session_id and browser_id are optional. Leave them out and this reports the
    default browser, as before; name them when a session holds more than one.
    """
    at = addressed(session_id, browser_id)
    config = registry.config(at)
    if config is None:
        return ("no browser is running yet, so there is no identity to report. "
                "The next tool that needs a page will start one, or call "
                "session_start to choose who it is.")

    session = registry.peek(at)
    tabs = "no tabs open"
    if session is not None:
        try:
            rows = await session.describe_pages()
            tabs = ", ".join(
                "%s%s %s" % (r["id"], "*" if r["active"] else "", r["url"] or "blank")
                for r in rows) or "no tabs open"
        except Exception:
            tabs = "tabs unreadable"
    else:
        tabs = "the browser is not up; the next tool restarts it as this person"

    return plan.describe(config) + " tabs: %s." % tabs


@mcp.tool()
async def session_start(seed: int | None = None, proxy: str | None = None,
                        profile: str | None = None,
                        session_id: str | None = None,
                        browser_id: str | None = None) -> str:
    """Start a browsing session as a particular person, and say who that is.

    Call this when you want to control WHO is browsing: a fresh stranger, the
    same person as last time, or a saved profile that is already logged in
    somewhere. Calling it closes whatever browser is open and starts another,
    so anything not saved in a profile is gone.

    You do not have to call it at all. The first tool that needs a page starts a
    session on its own; `session_status` then tells you who that turned out to
    be.

    A browser holds ONE identity, and this replaces it. Two identities in the
    same browser are visited in turn, never at the same time, so a task that
    needs both accounts live at once is worth saying so rather than
    half-starting.

    seed     the browser identity. Same seed, same fingerprint, every time.
             Leave it out and one is drawn, and the answer tells you which, so
             you can ask for it again later.
    profile  a directory that keeps cookies and logins between sessions. A
             profile also KEEPS ITS SEED: the first session on a new one stores
             the identity inside it, and every session after reuses it, so a
             login does not come back wearing different hardware. Pass "" to
             insist on no profile at all, which is how you get sessions a site
             cannot link to each other. A relative path is resolved against the
             server's own directory, so the answer reports the full path it
             used.
    proxy    where the traffic goes out, as `http://user:pass@host:port` or
             `socks5://host:port`. Pass "" to insist on going out from this
             machine's own address. A profile does NOT pin its exit the way it
             pins its seed: timezone, locale and geography come from the exit,
             so the same login arriving from another country is as visible as
             one arriving on different hardware. You are warned when a profile's
             exit changes, but only when YOU change it - a provider that rotates
             its own addresses behind one host and port looks identical here.

    session_id and browser_id are optional. Leave them out and this starts the
    default browser, as before; name them to say WHICH browser becomes this
    person, when a session holds more than one.
    """
    try:
        chosen = plan.plan_session(seed, proxy, profile, os.environ)
    except (identity.IdentityConflict, ValueError) as exc:
        # Refused, not guessed. Every case here is one where continuing would
        # hand the caller a different person than the one they asked for, and
        # the old session is deliberately left running: a refusal must not cost
        # somebody the browser they already had.
        return "refused: %s" % exc

    try:
        await registry.restart(addressed(session_id, browser_id), **chosen.kwargs)
    except Exception as exc:
        # ⛔ Said plainly, because the dangerous reading is "that failed, carry
        # on". Nothing is running now, and every later tool will repeat this
        # refusal rather than quietly starting a browser without the exit that
        # was asked for.
        return ("the session did NOT start: %s\n"
                "Nothing is browsing, and the tools will keep refusing until a "
                "session_start works. A proxy that is down is the usual cause; "
                "try another exit, or pass proxy=\"\" to go out from this "
                "machine knowing that is what you are doing." % exc)
    return "session started. " + chosen.describe()


# --- pages -----------------------------------------------------------------

@mcp.tool()
async def session_new_page(session_id: str | None = None,
                           browser_id: str | None = None) -> str:
    """Open a new tab and make it the active one. Returns its page id.

    Tabs persist across calls and across clients, so this is how you keep one
    page while working on another rather than navigating back and forth.

    session_id and browser_id are optional. Leave them out and the tab opens in
    the default browser, as before; name them when a session holds more than
    one, because a tab belongs to the browser it was opened in."""
    return await _retrying(actions.new_page,
                           session_id=session_id, browser_id=browser_id)


@mcp.tool()
async def session_list_pages(session_id: str | None = None,
                             browser_id: str | None = None) -> str:
    """Every open tab: id, title, url, and which one is active.

    Use it before session_select_page: the id alone does not tell you which tab
    you are switching to.

    session_id and browser_id are optional. Leave them out and this lists the
    default browser's tabs, as before; name them when a session holds more than
    one, since each browser numbers its own tabs."""
    return await actions.list_pages(
        await registry.ensure(addressed(session_id, browser_id)))


@mcp.tool()
async def session_select_page(page_id: str, session_id: str | None = None,
                              browser_id: str | None = None) -> str:
    """Switch the active tab. Every other browser_* tool acts on it.

    Take the id from session_list_pages or from session_new_page.

    session_id and browser_id are optional. Leave them out and this switches the
    default browser's tab, as before; name them when a session holds more than
    one, and use the browser the page id came from."""
    return actions.select_page(
        await registry.ensure(addressed(session_id, browser_id)), page_id)


@mcp.tool()
async def session_close_page(page_id: str = "", session_id: str | None = None,
                             browser_id: str | None = None) -> str:
    """Close a tab, or the active one when page_id is left out.

    session_id and browser_id are optional. Leave them out and this closes a tab
    of the default browser, as before; name them when a session holds more than
    one."""
    return await actions.close_page(
        await registry.ensure(addressed(session_id, browser_id)), page_id)


# --- reading ---------------------------------------------------------------

@mcp.tool()
async def browser_navigate(url: str, wait_until: str = "domcontentloaded",
                           session_id: str | None = None,
                           browser_id: str | None = None) -> str:
    """Go to a url in the active tab, opening one if none exists.

    Answers with the HTTP status the server gave and the url actually landed
    on, which is not always the one asked for: a redirect to a login wall or a
    regional domain shows up here. Read the status before trusting the page -
    a 404 or a 403 still has a document, and reading it as content is the
    mistake this reply exists to prevent.

    wait_until is "domcontentloaded" by default, which returns as soon as the
    markup is parsed. Use "load" when the page needs its images and stylesheets,
    or "networkidle" for a single-page app that fetches its content after
    load.

    session_id and browser_id are optional. Leave them out and this drives the
    default browser, as before; name them when a session holds more than one."""
    return await _retrying(actions.navigate, url, wait_until=wait_until,
                           session_id=session_id, browser_id=browser_id)


@mcp.tool()
async def browser_read_text(selector: str = "body", max_chars: int = 6000,
                            session_id: str | None = None,
                            browser_id: str | None = None) -> str:
    """The visible text of an element, with the markup gone.

    The cheapest way to read a page. Narrow the selector when you know where the
    answer is; use browser_read_html instead when the structure matters, or
    browser_snapshot when you need something to click.

    Long text is cut at max_chars (6000 by default) and the cut is marked in
    what comes back, so text that ends without that marker is the whole thing.

    session_id and browser_id are optional. Leave them out and this reads the
    default browser, as before; name them when a session holds more than one."""
    return await actions.read_text(
        await registry.ensure(addressed(session_id, browser_id)),
        selector, max_chars)


@mcp.tool()
async def browser_snapshot(max_chars: int = 0, session_id: str | None = None,
                           browser_id: str | None = None) -> str:
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

    session_id and browser_id are optional: without them this snapshots the
    default browser, as before. Name them to reach one of several.
    """
    return await actions.snapshot(
        await registry.ensure(addressed(session_id, browser_id)), max_chars)


@mcp.tool()
async def browser_read_html(mode: str = "form", session_id: str | None = None,
                            browser_id: str | None = None) -> str:
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

    session_id and browser_id are optional: without them this reads the default
    browser, as before. Name them to reach one of several.
    """
    return await actions.read_html(
        await registry.ensure(addressed(session_id, browser_id)), mode)


@mcp.tool()
async def browser_take_screenshot(session_id: str | None = None,
                                  browser_id: str | None = None) -> Image:
    """One screenshot of the active tab, on demand.

    session_id and browser_id are optional. Leave them out and this pictures the
    default browser, as before; name them when a session holds more than one."""
    png = await actions.screenshot_png(
        await registry.ensure(addressed(session_id, browser_id)))
    return Image(data=png, format="png")


@mcp.tool()
async def browser_watch(session_id: str | None = None,
                        browser_id: str | None = None) -> Image:
    """The whole browser window as a person at the machine sees it: tab strip,
    address bar, the page and the pointer, from a live capture kept running on
    the active tab. For watching the work, not for acting on it: the picture
    is window pixels, so do not feed its coordinates to browser_click_at; use
    browser_take_screenshot for that.

    session_id and browser_id are optional. Leave them out and this watches the
    default browser, as before; name them to watch one of several."""
    jpeg = await actions.watch_jpeg(
        await registry.ensure(addressed(session_id, browser_id)))
    return Image(data=jpeg, format="jpeg")


# --- acting ----------------------------------------------------------------

@mcp.tool()
async def browser_click(selector: str, session_id: str | None = None,
                        browser_id: str | None = None) -> str:
    """Click the first element matching a CSS selector.

    Scrolls it into view and waits for it to be clickable. When no selector can
    describe the target, use browser_click_at with coordinates from
    browser_snapshot.

    session_id and browser_id are optional. Leave them out and this clicks in
    the default browser, as before; name them when a session holds more than
    one, and use the browser the selector came from."""
    return await actions.click(
        await registry.ensure(addressed(session_id, browser_id)), selector)


@mcp.tool()
async def browser_click_at(x: float, y: float, hold_seconds: float = 0.0,
                           session_id: str | None = None,
                           browser_id: str | None = None) -> Image:
    """Click (or press-and-hold) a raw viewport coordinate instead of a
    selector - for targets a selector cannot reliably reach: a slider track, a
    canvas-drawn captcha, or a precise point inside a wider element. Moves the
    pointer there first (no teleport), then down, then up, holding first if
    hold_seconds is set. Returns a screenshot taken right after release.

    hold_seconds needs invisible-playwright 0.9.0 or newer to mean anything. In
    every earlier version the wait it is built on returned instantly, so the
    press and the release happened in the same frame and the hold never
    happened - on the one tool that exists for sliders and press-and-hold
    challenges. The floor in pyproject.toml is set accordingly.

    Coordinates are relative to the VIEWPORT, not to the page, so the ones in a
    snapshot go stale the moment anything scrolls: a click, a keypress, a lazy
    image loading in above the fold. Nothing raises when that happens - the
    click simply lands on whatever is at that spot now. Take a fresh snapshot
    after anything that could have moved the page, and prefer browser_click with
    the element's `selector` whenever it has one.

    session_id and browser_id are optional. Leave them out and this clicks in
    the default browser, as before; name them when a session holds more than
    one, and use the browser the coordinates came from."""
    png = await actions.click_at(
        await registry.ensure(addressed(session_id, browser_id)),
        x, y, hold_seconds)
    return Image(data=png, format="png")


@mcp.tool()
async def browser_type(selector: str, text: str, session_id: str | None = None,
                       browser_id: str | None = None) -> str:
    """Fill a field, replacing whatever it holds.

    This sets the value rather than typing key by key, so it will not fire the
    per-keystroke handlers an autocomplete needs. For those, click the field and
    use browser_press_key.

    session_id and browser_id are optional. Leave them out and this types into
    the default browser, as before; name them when a session holds more than
    one."""
    return await actions.type_text(
        await registry.ensure(addressed(session_id, browser_id)), selector, text)


@mcp.tool()
async def browser_select_option(selector: str, value: str,
                                session_id: str | None = None,
                                browser_id: str | None = None) -> str:
    """Choose an option in a dropdown (`<select>`), by its visible label or by
    its value.

    Use this rather than clicking the dropdown and pressing arrow keys: a click
    plus arrows cannot tell you which row it landed on, and setting the value
    through browser_evaluate changes it without the page seeing a real
    interaction.

    session_id and browser_id are optional. Leave them out and this chooses in
    the default browser, as before; name them when a session holds more than
    one."""
    return await actions.select_option(
        await registry.ensure(addressed(session_id, browser_id)), selector, value)


@mcp.tool()
async def browser_press_key(key: str, session_id: str | None = None,
                            browser_id: str | None = None) -> str:
    """Press a key on whatever has focus: "Enter", "Tab", "Escape",
    "ArrowDown", "Control+a", or a single character.

    session_id and browser_id are optional. Leave them out and the key goes to
    the default browser, as before; name them when a session holds more than
    one."""
    return await actions.press_key(
        await registry.ensure(addressed(session_id, browser_id)), key)


@mcp.tool()
async def browser_evaluate(expression: str, session_id: str | None = None,
                           browser_id: str | None = None) -> str:
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

    session_id and browser_id are optional. Leave them out and this reads the
    default browser, as before; name them when a session holds more than one."""
    return await actions.evaluate(
        await registry.ensure(addressed(session_id, browser_id)), expression)


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
