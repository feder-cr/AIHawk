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

Config comes from STEALTHFOX_* env vars. Nothing here opens a browser but
`browser_open`; a tool whose browser is not open, or gone, says so and names
that call. `work.py` is where that rule lives.

Every tool here is a wrapper. The operations live in `actions.py` and the
browsers in `work.py`, so every client drives them through exactly the same
code rather than through a second implementation that would drift from this
one. (This said `registry.py` until 2026-09-16, a file that has not existed
since the eight-browser session became one piece of work - a present-tense
sentence pointing a reader at nothing.)

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
from typing import Annotated, Literal, Optional

from mcp.server.fastmcp import FastMCP, Image
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__, actions, store
from ..quiet import swallow
from .work import DEFAULT_BROWSER_ID, Work
# Reached by tests as `server.<name>`; the tools themselves no longer
# read them, because the piece of work answers with them.
from .work import MAX_BROWSERS_PER_SESSION, SUPPORT_BROWSER_ID  # noqa: F401

#: ⛔ WHERE THIS PROCESS'S OWN PIECE OF WORK COMES FROM, AND THE ONLY PLACE
#: THAT KNOWS IT EXISTS. Read from the environment ONCE, exactly like
#: `STEALTHFOX_SEED` or `STEALTHFOX_PROXY` in `plan.py` - never a tool
#: argument, never a name in a published schema, never something a model can
#: read, pass, list or invent. There is exactly one of these for the life of
#: the process, and nothing below can ask about, name, or reach a second one.
#:
#: Whoever spawns this process decides the value. The interface spawns one
#: server PER CONVERSATION and sets this to that conversation's own id, so two
#: conversations are two PROCESSES, each with its own saved browser on disk. A
#: standalone client (`uvx aihawk`, or this module run directly) never sets it
#: and lands on the same name every caller landed on before this had a name at
#: all: `DEFAULT_SESSION_ID`. Two standalone clients on one machine therefore
#: share a file, which is recorded as an open question in the workbench and
#: not decided here.
_SESSION_ID = os.environ.get("AIHAWK_SESSION_ID") or store.DEFAULT_SESSION_ID

#: The one piece of work this process serves: its two browsers, where they
#: were, and the file they are written to. Every tool below goes through it,
#: and a test installs one of its own here, built with a factory that
#: launches nothing - one object in place of the four globals this module
#: used to hold. The lifecycle is documented on the class.
work = Work(_SESSION_ID)


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
    somebody detached, which is the exact behaviour keeping the browsers in
    `Work` exists to remove; there the close stays at process exit, below.

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
            await work.close_all()


def _close_sessions_at_exit() -> None:
    """Best effort shutdown of every browser when the process itself ends,
    for the HTTP transport, where the lifespan cannot do it.

    A browser left behind is not a small leak here: Firefox launches a whole
    tree of processes, and an orphaned one goes on holding its profile
    directory and its port. Bounded, because this runs in a fresh event loop
    and an await on an object from the finished one does not return: ten
    seconds, then the process is allowed to end.
    """
    with swallow("ten seconds, then the process is allowed to end"):
        asyncio.run(asyncio.wait_for(work.close_all(), 10))



# The ladder, stated once. Each tool's own description says what that tool does;
# nothing said which to REACH FOR FIRST, and a model that cannot find a way down
# the ladder invents one. Measured 2026-09-02, first run with a real model: it
# went from "click the select" straight to running `s.value='beta'` as script,
# skipping the two rungs in between - coordinates, and a screenshot - because
# nothing had told it they were rungs.
INSTRUCTIONS = """Two browsers, `main` and `support`. OPEN `main` WITH browser_open
BEFORE ANYTHING ELSE: no other tool opens a browser, and every tool that finds
its browser not open answers with a sentence saying so instead of working.
With no arguments browser_open brings back the person this session already
was; pass a seed, a proxy or a profile only to be somebody else. If a tool
says the browser is gone, call browser_open again and carry on.

Drive the page the way a person would. Everything here goes
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

# ⛔ WHO THE CLIENT IS TALKING TO, AND WHY THIS REACHES PAST FastMCP.
# `initialize` carries a serverInfo with a name and a version, and a client
# uses them to say what it connected to and to correlate a defect with a
# release. FastMCP takes no `version=`: it builds the low-level Server without
# one, and that Server falls back to `importlib.metadata.version("mcp")`.
# Measured before this line existed: the handshake advertised `1.28.0`, the
# version of the SDK, for every build of this package. A client asking what it
# was driving got the number of a library we merely depend on.
# The field belongs to the low-level Server and is public there; only the
# FastMCP wrapper omits it, so setting it here is filling a gap, not reaching
# into something private. The name stays `stealth` on purpose: it is the key
# a person registering the server by hand was told to use (`claude mcp add
# ... stealth -- uvx aihawk`, the README's line until the plugin route) and
# it prefixes every tool such a client sees (`mcp__stealth__*`), so moving it
# would rename tools under people who already have them wired. The plugin's
# `.mcp.json` keys the same server as `aihawk`; that key is the client's and
# never passes through here.
mcp._mcp_server.version = __version__


def _says(title: str, *, read_only: bool = False, destructive: bool = False,
          open_world: bool = True) -> ToolAnnotations:
    """What a client may assume about a tool before it calls it.

    Every tool declares a title and states BOTH hints, never leaving one out:
    `read_only` (readOnlyHint) for a tool that changes nothing, so a client
    may run it without asking each time, and `destructive` (destructiveHint)
    for one that acts on the page or on a browser, which a client confirms.
    Anything that types, clicks, navigates or closes is `destructive` here: a
    form submitted or a page left behind cannot be undone from this side.
    `open_world` says the tool reaches the live web.

    ⛔ AND UNTIL 0.48.0 THERE WAS A THIRD GROUP, five tools that claimed to be
    the first while going through the wake funnel, which STARTS a real Firefox
    when none is running. A tool that can spawn a browser has modified its
    environment, so `readOnlyHint` was false in fact and true on the wire, and
    a client trusting it ran them unattended. Nothing starts a browser now
    but `browser_open` - every other tool goes through `Work.acting`, which
    answers a sentence instead - so the hint is true again. Stating both hints explicitly is what keeps that legible:
    an ABSENT hint and a hint set to false are different facts, and a client
    reading MCP's defaults treats a missing `destructiveHint` as true.

    The title lives in the annotations rather than on the tool because
    `FastMCP.tool(title=)` exists from mcp 1.10 and this package's floor is
    1.8, where annotations already carry one (measured on both wheels).
    """
    return ToolAnnotations(title=title, readOnlyHint=read_only,
                           destructiveHint=destructive, openWorldHint=open_world)


#: What a tool accepts for `browser`: a ROLE, never a name a caller invents.
#:
#: ⛔ AND THE SENTENCE EXPLAINING IT LIVES HERE, ONCE, ON THE PARAMETER. It was
#: the last line of THIRTEEN docstrings, word for word, which is thirteen places
#: to change it and thirteen chances for one of them to say something slightly
#: different. It also spent that budget in the wrong account: a description is
#: cut at 1024 characters before the model reads it, and `browser_open` was
#: sitting at 1021 - three characters from losing the sentence that says who
#: closes `support`, which is the exact defect its gate was written for.
#:
#: On the parameter it is better placed: a client shows it beside the argument
#: it describes, on every tool, whether or not that tool's description was long
#: enough to reach the end.
#:
#: ⛔ AND IT IS ONE LINE BECAUSE THE FIRST VERSION WAS FOUR, AND FOUR MADE THE
#: WHOLE CHANGE A LOSS. A schema travels with its tool on every turn exactly as
#: a description does, so thirteen copies in the schemas is the same duplication
#: as thirteen copies in the descriptions - moved, not removed, and the longer
#: sentence made it dearer. Measured with a tokenizer across both trees:
#: descriptions -256 tokens, schemas +900, complete definitions +617, which is
#: 16% MORE resent every turn for a change whose point was to spend less.
#:
#: What the model needs AT THE CALL is which browser it gets when it says
#: nothing. What `main` and `support` ARE is a paragraph, and it has one home:
#: the server's instructions, sent once per conversation rather than once per
#: tool. A gate below holds the complete definitions under what they cost
#: before, so this cannot quietly grow back.
Browser = Annotated[
    Optional[Literal["main", "support"]],
    Field(default=None,
          description="Defaults to `main`; `support` is the helper beside it."),
]


# --- the two browsers -------------------------------------------------------

@mcp.tool(annotations=_says("Open a browser", destructive=True, open_world=False))
async def browser_open(browser: Browser = None, seed: int | None = None,
                       proxy: str | None = None, profile: str | None = None) -> str:
    """Open `main` or `support`, or reopen one as somebody else.

    `support` is yours to manage: open it when the task needs a second
    identity, and close it with browser_close as soon as the task no longer
    needs it, before you answer. It is not saved.

    Called on a browser that is already up, this REOPENS it with the settings
    given, and what it held is gone.

    seed     the identity; same seed, same fingerprint. Left out, one is drawn.
    profile  a directory keeping cookies, logins and the seed between opens;
             "" means none. It keeps the SEED too, so a login does not come
             back on different hardware every visit.
    proxy    the exit, `http://user:pass@host:port` or `socks5://host:port`;
             "" means this machine's own address; left out for `support`, it
             shares the exit `main` has. A profile does NOT pin its exit, and
             a login arriving from a new country is as visible as one arriving
             on new hardware.
    """
    # ⛔ THE DESCRIPTION ABOVE IS WHAT THE MODEL READS, AND IT IS CUT AT 1024
    # CHARACTERS BY THE API. The version before this one was 1996: the model
    # saw it end mid-word inside the paragraph about profiles, and the sentence
    # that told it to close the helper was past the cut. A gate in the server
    # tests holds every tool's description under the limit.
    #
    # ⛔ AND IT SAT AT 1021 OF 1024 - three characters - while saying a third
    # time what `main` and `support` are: once in the server's instructions,
    # once on the `browser` parameter, once here. Removing the copy is what
    # bought the room for the two rules below it, which had been cut for space
    # and left in this comment where no model would ever read them. A repeated
    # sentence is not free here; it is spent out of the same 1024 characters
    # as the rules that only this tool can state.
    return await work.open(browser or DEFAULT_BROWSER_ID, seed=seed,
                           proxy=proxy, profile=profile)


@mcp.tool(annotations=_says("Close a browser", destructive=True, open_world=False))
async def browser_close(browser: Browser = None) -> str:
    """Close one browser and free what it was holding.

    The page it had is gone with it. The other browser is not touched.

    Who it was is kept: browser_open with no arguments brings the same person
    back. To be somebody else, pass a seed, a proxy or a profile.
    """
    return await work.close(browser or DEFAULT_BROWSER_ID)


@mcp.tool(annotations=_says("List the browsers", read_only=True, open_world=False))
async def browser_list() -> str:
    """Which of the two browsers are open, where each one is, and which one
    you are working in.

    Answers JSON: `focus`, the browser your last command acted in, or "" when
    none is open; `note`, which says how many are open and that a command
    naming no browser goes to `main`; and `browsers` - each row `id`, `url`
    (the page it is on) and `urls` (every page it holds, which is more than
    one only when a site opened one). Only open browsers are listed, so every
    row is one you can act on.

    Starts nothing: it reports what is open, so asking is free.
    """
    # ⛔ JSON, WHERE THIS ANSWERED PROSE UNTIL 0.18.0, and the reason is the
    # stated architecture rather than taste: the interface is a client of these
    # tools like anybody else, with no privileged path, so a workspace that has
    # to draw one pane per browser needs this question answered in a shape a
    # program can read. The alternative was the page parsing a sentence, which
    # is two readers of one wire format, or a second tool saying the same thing,
    # which is two sources for one fact. Models read JSON from these tools
    # without trouble; `note` carries the sentence that used to be the whole
    # answer, because "there is nothing here yet" is worth saying in words.
    return actions.json_capped(await work.listing())


# --- who is browsing ---------------------------------------------------------

@mcp.tool(annotations=_says("Who is browsing", read_only=True, open_world=False))
async def browser_status(browser: Browser = None) -> str:
    """Who is browsing right now: the identity, the exit, the profile and the page.

    Ask whenever you need to know which person the browser currently is, or
    from where its traffic leaves. The seed is what you would pass to
    `browser_open` to become this person again, so this is also how you
    record an identity worth repeating.

    It starts nothing: a browser that is not open, or gone, is answered with
    the sentence that says which.
    """
    return await work.status(browser or DEFAULT_BROWSER_ID)


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

@mcp.tool(annotations=_says("Go to a URL", destructive=True))
async def browser_navigate(url: str, wait_until: str = "domcontentloaded",
                           browser: Browser = None) -> str:
    """Go to a url in this browser's page, opening it if none exists.

    Answers with the HTTP status the server gave and the url actually landed
    on, which is not always the one asked for: a redirect to a login wall or a
    regional domain shows up here. Read the status before trusting the page -
    a 404 or a 403 still has a document, and reading it as content is the
    mistake this reply exists to prevent.

    wait_until is "domcontentloaded" by default, which returns as soon as the
    markup is parsed. Use "load" when the page needs its images and stylesheets,
    or "networkidle" for a single-page app that fetches its content after
    load."""
    return await work.acting(actions.navigate, url, wait_until=wait_until,
                             role=browser)


@mcp.tool(annotations=_says("Read the page text", read_only=True))
async def browser_read_text(selector: str = "body",
                            max_chars: int = actions.DEFAULT_MAX_CHARS,
                            browser: Browser = None) -> str:
    """The visible text of an element, with the markup gone.

    The cheapest way to read a page. Narrow the selector when you know where the
    answer is; use browser_read_html instead when the structure matters, or
    browser_snapshot when you need something to click.

    Long text is cut at max_chars (6000 by default) and the cut is marked in
    what comes back, so text that ends without that marker is the whole thing."""
    # ⛔ THE CAP WAS WRITTEN THREE TIMES: the constant in `actions.py`, this
    # signature, and the prose above. The signature was the copy worth removing
    # - nothing read it back, so it could drift from the constant in silence
    # and the tool would honour a number its own module did not declare.
    #
    # ⛔ THE PROSE COPY STAYS, AND A DRAFT THAT DELETED IT WAS WRONG. The
    # reasoning was that the schema already publishes `"default": 6000`, so the
    # sentence is a second copy - which is true and is not the whole story:
    # `test_the_two_readers_do_not_pretend_to_share_a_cap` holds that this
    # description declares its cap while `browser_read_html` declares it has
    # none, because a reader shown one and not the other assumes symmetry, and
    # the two differ by 34x on a large page. A number that has a reason to be
    # written twice gets a GATE, not a deletion: `test_the_cap_in_the_prose_is
    # _the_cap_the_tool_uses` ties this digit to the constant, so the copy
    # cannot drift even though it stays.
    return await work.acting(actions.read_text, selector, max_chars, role=browser)


@mcp.tool(annotations=_says("Snapshot the page", read_only=True))
async def browser_snapshot(max_chars: int = 0, browser: Browser = None) -> str:
    """Title, url, and the interactive elements that are actually visible.

    Each element carries a `selector` when one can reach it: pass that string to
    browser_click or browser_type VERBATIM rather than writing your own. It is
    built to match exactly ONE element, which the obvious selector often does
    not, and the driver acts on the first match - so a caller aiming at the
    third of five identical links would silently hit the first and be told it
    succeeded.

    Elements with no `selector` carry `at`, the centre coordinates, for
    browser_click_at.

    It lists what a caller can act on, and it is not the accessibility tree:
    one country `<select>` would otherwise fill the answer with its options
    before the form you were looking for appears.
    """
    # ⛔ THE MEASUREMENTS BEHIND THE TWO PARAGRAPHS ABOVE LIVE IN `actions.py`,
    # BESIDE THE CODE THEY JUSTIFY, and used to live here as well. The numbers
    # - 958 elements, 88% addressable and 48% unambiguous, two hundred option
    # nodes - are why the selector is BUILT and why the inventory is not the
    # accessibility tree. That is a developer's question. What the model needs
    # is the rule, and it keeps every rule those sentences carried.
    #
    # A measurement written in two places is a measurement that will be re-run
    # once and updated once, and the copy that stays wrong is the one a model
    # reads. It also spends the 1024 characters this description is cut at on
    # evidence for a reader who is not there.
    return await work.acting(actions.snapshot, max_chars, role=browser)


@mcp.tool(annotations=_says("Read the page HTML", read_only=True))
async def browser_read_html(mode: str = "form", browser: Browser = None) -> str:
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
    """
    return await work.acting(actions.read_html, mode, role=browser)


@mcp.tool(annotations=_says("Take a screenshot", read_only=True))
async def browser_take_screenshot(browser: Browser = None) -> Image:
    """One screenshot of this browser's page, on demand."""
    png = await work.acting(actions.screenshot_png, role=browser)
    return Image(data=png, format="png")


@mcp.tool(annotations=_says("Watch the browser window", read_only=True))
async def browser_watch(browser: Browser = None) -> Image:
    """The whole browser window as a person at the machine sees it: tab strip,
    address bar, the page and the pointer, from a live capture kept running on
    that page. For watching the work, not for acting on it: the picture
    is window pixels, so do not feed its coordinates to browser_click_at; use
    browser_take_screenshot for that.

    Starts nothing. A browser that is not open has no window, so this answers
    the sentence that says so, and the live panes - which call this many times
    a second - read that sentence as the idle pane."""
    # It REFUSES rather than answering the sentence as text, and only because
    # the type says so: this is declared to return an Image, and `Image | str`
    # is not a schema pydantic will build - measured, five test modules
    # refuse to import. A refusal reaches a client as an error result
    # carrying the reason, which every client already handles.
    jpeg = await work.acting(lambda session: session.watch_frame(), role=browser)
    return Image(data=jpeg, format="jpeg")


# --- acting ----------------------------------------------------------------

@mcp.tool(annotations=_says("Click an element", destructive=True))
async def browser_click(selector: str, browser: Browser = None) -> str:
    """Click the first element matching a CSS selector.

    Scrolls it into view and waits for it to be clickable. When no selector can
    describe the target, use browser_click_at with coordinates from
    browser_snapshot."""
    return await work.acting(actions.click, selector, role=browser)


@mcp.tool(annotations=_says("Click at a point", destructive=True))
async def browser_click_at(x: float, y: float, hold_seconds: float = 0.0,
                           browser: Browser = None) -> Image:
    """Click (or press-and-hold) a raw viewport coordinate instead of a
    selector - for targets a selector cannot reliably reach: a slider track, a
    canvas-drawn captcha, a precise point inside a wider element. Moves the
    pointer there first (no teleport), then down, then up, holding first if
    hold_seconds is set. Returns a screenshot taken right after release.

    Coordinates are relative to the VIEWPORT, not to the page, so the ones in a
    snapshot go stale the moment anything scrolls. Nothing raises when that
    happens: the click lands on whatever is at that spot now. Take a fresh
    snapshot after anything that could have moved the page, and prefer
    browser_click with the element's `selector` whenever it has one."""
    # hold_seconds needs invisible-playwright 0.9.0 or newer to mean anything:
    # in every earlier version the wait it is built on returned instantly, so
    # the press and the release happened in the same frame and the hold never
    # happened, on the one tool that exists for sliders and press-and-hold
    # challenges. The floor in pyproject.toml is set accordingly. Said here and
    # not in the description above, which the API cuts at 1024 characters.
    png = await work.acting(actions.click_at, x, y, hold_seconds, role=browser)
    return Image(data=png, format="png")


@mcp.tool(annotations=_says("Type into a field", destructive=True))
async def browser_type(selector: str, text: str, browser: Browser = None) -> str:
    """Fill a field, replacing whatever it holds.

    This sets the value rather than typing key by key, so it will not fire the
    per-keystroke handlers an autocomplete needs. For those, click the field and
    use browser_press_key."""
    return await work.acting(actions.type_text, selector, text, role=browser)


@mcp.tool(annotations=_says("Choose a dropdown option", destructive=True))
async def browser_select_option(selector: str, value: str,
                                browser: Browser = None) -> str:
    """Choose an option in a dropdown (`<select>`), by its visible label or by
    its value.

    Use this rather than clicking the dropdown and pressing arrow keys: a click
    plus arrows cannot tell you which row it landed on, and setting the value
    through browser_evaluate changes it without the page seeing a real
    interaction."""
    return await work.acting(actions.select_option, selector, value, role=browser)


@mcp.tool(annotations=_says("Press a key", destructive=True))
async def browser_press_key(key: str, browser: Browser = None) -> str:
    """Press a key on whatever has focus: "Enter", "Tab", "Escape",
    "ArrowDown", "Control+a", or a single character."""
    return await work.acting(actions.press_key, key, role=browser)


@mcp.tool(annotations=_says("Read the page with JavaScript", read_only=True))
async def browser_evaluate(expression: str, browser: Browser = None) -> str:
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
    return await work.acting(actions.evaluate, expression, role=browser)


def main() -> None:
    global _close_on_lifespan_exit
    transport = os.environ.get("STEALTHFOX_MCP_TRANSPORT", "stdio").strip().lower()
    if transport in ("http", "streamable-http"):
        # streamable-http ships with the `mcp` package, which already requires
        # starlette and uvicorn, so serving over HTTP costs no new dependency.
        mcp.settings.host = os.environ.get("STEALTHFOX_MCP_HOST", "127.0.0.1")
        # ⛔ NOT 8765, WHICH IS THE INTERFACE'S PORT. `aihawk ui` defaults to
        # 8765 (cli.py), and this default used to be the same number in a
        # module that does not know about that one. Nobody had hit it because
        # nothing sets STEALTHFOX_MCP_TRANSPORT=http on its own, so the two
        # defaults had never been asked for at the same time; the first person
        # to try would have got a bind error with no hint of why.
        mcp.settings.port = int(os.environ.get("STEALTHFOX_MCP_PORT", "8766"))
        atexit.register(_close_sessions_at_exit)
        mcp.run(transport="streamable-http")
    else:
        _close_on_lifespan_exit = True
        mcp.run()


if __name__ == "__main__":
    main()
