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
from .registry import SessionRegistry

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


async def _retrying(fn, *args, **kwargs):
    """Run an action, and on failure rebuild the session once and retry.

    A browser that died between two calls is the ordinary case here, not an
    exotic one: the object is still intact, so the failure surfaces inside the
    action rather than when the session was handed out.
    """
    session = await registry.ensure()
    try:
        return await fn(session, *args, **kwargs)
    except Exception:
        await registry.drop()
        session = await registry.ensure()
        return await fn(session, *args, **kwargs)


# --- who is browsing -------------------------------------------------------

@mcp.tool()
async def session_status() -> str:
    """Who is browsing right now: the identity, the exit, the profile and the tabs.

    Ask whenever you need to know which person the browser currently is, or from
    where its traffic leaves. The seed is what you would pass to `session_start`
    to become this person again, so this is also how you record a session that
    is worth repeating.

    It starts nothing. If no browser is running yet it says so, because until
    one is running there is no identity to report.
    """
    config = registry.config()
    if config is None:
        return ("no browser is running yet, so there is no identity to report. "
                "The next tool that needs a page will start one, or call "
                "session_start to choose who it is.")

    session = registry.peek()
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
                        profile: str | None = None) -> str:
    """Start a browsing session as a particular person, and say who that is.

    Call this when you want to control WHO is browsing: a fresh stranger, the
    same person as last time, or a saved profile that is already logged in
    somewhere. Calling it closes whatever browser is open and starts another,
    so anything not saved in a profile is gone.

    You do not have to call it at all. The first tool that needs a page starts a
    session on its own; `session_status` then tells you who that turned out to
    be.

    There is only ONE browser. Two identities are visited in turn, never at the
    same time, so a task that needs both accounts live at once cannot be done
    here and is worth saying so rather than half-starting.

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
        await registry.restart(**chosen.kwargs)
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
async def session_new_page() -> str:
    """Open a new tab and make it the active one. Returns its page id.

    Tabs persist across calls and across clients, so this is how you keep one
    page while working on another rather than navigating back and forth."""
    return await _retrying(actions.new_page)


@mcp.tool()
async def session_list_pages() -> str:
    """Every open tab: id, title, url, and which one is active.

    Use it before session_select_page: the id alone does not tell you which tab
    you are switching to."""
    return await actions.list_pages(await registry.ensure())


@mcp.tool()
async def session_select_page(page_id: str) -> str:
    """Switch the active tab. Every other browser_* tool acts on it.

    Take the id from session_list_pages or from session_new_page."""
    return actions.select_page(await registry.ensure(), page_id)


@mcp.tool()
async def session_close_page(page_id: str = "") -> str:
    """Close a tab, or the active one when page_id is left out."""
    return await actions.close_page(await registry.ensure(), page_id)


# --- reading ---------------------------------------------------------------

@mcp.tool()
async def browser_navigate(url: str, wait_until: str = "domcontentloaded") -> str:
    """Go to a url in the active tab, opening one if none exists.

    Answers with the HTTP status the server gave and the url actually landed
    on, which is not always the one asked for: a redirect to a login wall or a
    regional domain shows up here. Read the status before trusting the page -
    a 404 or a 403 still has a document, and reading it as content is the
    mistake this reply exists to prevent.

    wait_until is "domcontentloaded" by default, which returns as soon as the
    markup is parsed. Use "load" when the page needs its images and stylesheets,
    or "networkidle" for a single-page app that fetches its content after
    load."""
    return await _retrying(actions.navigate, url, wait_until=wait_until)


@mcp.tool()
async def browser_read_text(selector: str = "body", max_chars: int = 6000) -> str:
    """The visible text of an element, with the markup gone.

    The cheapest way to read a page. Narrow the selector when you know where the
    answer is; use browser_read_html instead when the structure matters, or
    browser_snapshot when you need something to click.

    Long text is cut at max_chars (6000 by default) and the cut is marked in
    what comes back, so text that ends without that marker is the whole thing."""
    return await actions.read_text(await registry.ensure(), selector, max_chars)


@mcp.tool()
async def browser_snapshot(max_chars: int = 0) -> str:
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
    """
    return await actions.snapshot(await registry.ensure(), max_chars)


@mcp.tool()
async def browser_read_html(mode: str = "form") -> str:
    """The page's HTML, cleaned down to what is worth reading.

    Use this when the STRUCTURE matters - a form and its labels, a table, what
    a control is wired to. `browser_snapshot` gives a flat inventory of things
    to click; this keeps the markup and the relationships inside it.

    mode="form" keeps the interactive surface and the text explaining it,
    mode="text" returns the prose alone, mode="full" keeps the structure with
    the noise and the attribute soup removed.

    Unlike browser_read_text this is NOT capped: it returns the whole reduced
    page, which on a large one is tens of thousands of characters. That is
    deliberate, because cutting markup in the middle leaves tags that no longer
    mean anything - but it means the answer can be long. Reach for
    browser_snapshot when you only need something to click, or
    browser_read_text when you only need the words.
    """
    return await actions.read_html(await registry.ensure(), mode)


@mcp.tool()
async def browser_take_screenshot() -> Image:
    """One screenshot of the active tab, on demand."""
    png = await actions.screenshot_png(await registry.ensure())
    return Image(data=png, format="png")


@mcp.tool()
async def browser_watch() -> Image:
    """The whole browser window as a person at the machine sees it: tab strip,
    address bar, the page and the pointer, from a live capture kept running on
    the active tab. For watching the work, not for acting on it: the picture
    is window pixels, so do not feed its coordinates to browser_click_at; use
    browser_take_screenshot for that."""
    jpeg = await actions.watch_jpeg(await registry.ensure())
    return Image(data=jpeg, format="jpeg")


# --- acting ----------------------------------------------------------------

@mcp.tool()
async def browser_click(selector: str) -> str:
    """Click the first element matching a CSS selector.

    Scrolls it into view and waits for it to be clickable. When no selector can
    describe the target, use browser_click_at with coordinates from
    browser_snapshot."""
    return await actions.click(await registry.ensure(), selector)


@mcp.tool()
async def browser_click_at(x: float, y: float, hold_seconds: float = 0.0) -> Image:
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
    the element's `selector` whenever it has one."""
    png = await actions.click_at(await registry.ensure(), x, y, hold_seconds)
    return Image(data=png, format="png")


@mcp.tool()
async def browser_type(selector: str, text: str) -> str:
    """Fill a field, replacing whatever it holds.

    This sets the value rather than typing key by key, so it will not fire the
    per-keystroke handlers an autocomplete needs. For those, click the field and
    use browser_press_key."""
    return await actions.type_text(await registry.ensure(), selector, text)


@mcp.tool()
async def browser_select_option(selector: str, value: str) -> str:
    """Choose an option in a dropdown (`<select>`), by its visible label or by
    its value.

    Use this rather than clicking the dropdown and pressing arrow keys: a click
    plus arrows cannot tell you which row it landed on, and setting the value
    through browser_evaluate changes it without the page seeing a real
    interaction."""
    return await actions.select_option(await registry.ensure(), selector, value)


@mcp.tool()
async def browser_press_key(key: str) -> str:
    """Press a key on whatever has focus: "Enter", "Tab", "Escape",
    "ArrowDown", "Control+a", or a single character."""
    return await actions.press_key(await registry.ensure(), key)


@mcp.tool()
async def browser_evaluate(expression: str) -> str:
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
    answer rather than using it."""
    return await actions.evaluate(await registry.ensure(), expression)


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
