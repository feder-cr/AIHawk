---
title: "Running AIHawk's browser from Claude Desktop"
description: "Adding the stealth browser to Claude Desktop via its JSON config - what changes in the app, first prompts to try, what tool calls and approvals look like, and the first-run issues."
parent: "Using the Agent"
nav_order: 8
---


# Running AIHawk's browser from Claude Desktop

Claude Desktop does not take the one-line command that Claude Code does; it
reads its MCP servers from a JSON settings file. The exact block to paste and
the file it goes in are documented once, in the
[server's README](https://github.com/feder-cr/invisible-playwright-mcp), and
this page deliberately does not duplicate them - configs copied into wikis rot.
What this page covers is everything around that block: what actually changes in
Desktop once the server is in, what to try first, what the tool calls look like
while Claude works, and the first-run issues that generate most of the
questions.

One boundary before anything else, because it decides whether to read on:
Claude Desktop runs on macOS and Windows, and AIHawk's engine ships for Windows
and Linux, with macOS unsupported. The overlap is Windows. On a Mac, Desktop
will start the server and the server will have no engine build to run; this
combination is a Windows setup today.

## What changes after the server is added

Mechanically: `pip install aihawk` and `invisible-playwright fetch` in a
terminal, then you edit the config (Desktop's Settings, under Developer, has an
Edit Config button that opens the right file), paste the server block from the
README, then quit Desktop completely and restart it. The full restart is not
superstition; Desktop loads MCP servers at startup, and the official MCP
quickstart lists "restart Claude Desktop completely" as the first
troubleshooting step for a server that does not appear.

After the restart, the same Claude you already talk to has a real browser. The
server exposes a flat set of tools in two families: session tools that manage
tabs (`session_new_page`, `session_list_pages` and friends) and page tools that
act on one (`browser_navigate`, `browser_read_text`, `browser_snapshot`,
`browser_click`, `browser_type`, `browser_take_screenshot`, and a few more).
Claude sees the list and decides when to use them; you do not invoke tools
yourself, you ask for outcomes.

Two things notably do not change. There is no new account and no new key: your
existing Claude subscription is the model, the server brings only the browser,
and the config block carries no secret. And nothing happens eagerly: no browser
launches at startup, and nothing downloads until the first instruction that
actually needs a page.

## First prompts to try

Start small and visible, because the first prompt doubles as the installation
test:

> Open https://books.toscrape.com/ and tell me the title and price of the
> first book on the page.

That one prompt exercises the whole path: server starts, engine found (or
fetched, see below), page loaded, text read, answer grounded in the page. The
example site is a sandbox built for practice, which is exactly what a first
run is.

Then something with a decision in it:

> On that same site, go to page two and tell me whether any book there is
> priced under ten pounds. Quote the cheapest one.

And when it is earning its keep, point it at your own work: a staging page or a
local dev server is the best second session, because you know the ground truth.
For anything form-shaped, [the forms page](ai-agent-fill-out-forms.md) is the
honest account of what to expect.

Keep early instructions to one clear step. The agent behind these tools works
observe-act-observe, and short instructions produce transcripts you can read
when something goes wrong, which at the start is the point.

## What the tool calls look like

Desktop makes the agent loop unusually visible, and it is worth watching once.
When Claude decides to act, the tool call appears in the conversation by name
with its arguments - `browser_navigate` with a URL, `browser_click` with a
selector - and by default Desktop asks for your approval before each action
runs. You can allow individually, and you can deny; nothing touches the page
without a click from you. The tool's result then returns into the
conversation: page text for the reading tools, an image for
`browser_take_screenshot`.

Two consequences of that design are worth naming. First, the approvals are a
feature, not friction: a browser that acts on the real web under your account
deserves a human gate, and the gate is also where you catch a wrong step before
it happens. Second, the browser itself is headless by default, so there is no
window to watch; the screenshot tool is your eyes. If you want an actual
window, the server reads `STEALTHFOX_HEADLESS=0` from its environment - set in
the same config block, and documented, like the rest of the server's
environment variables, in its README.

The server list itself lives behind the connectors control at the bottom of
Desktop's input box; the MCP quickstart walks the exact clicks. If the server
is missing from that list after a restart, the config did not load, and that
is a syntax or path problem, not an AIHawk one.

## Common first-run issues

In the order people hit them:

1. **The first real prompt hangs.** The engine is about a quarter of a
   gigabyte and is not fetched at install or at server start; it arrives on
   the first tool call that needs a page. On a slow connection that looks
   like Claude sitting silently on your instruction, and it can end in a
   timeout message that never mentions a download. Get it over with first, in
   a terminal where you can watch progress:

   ```bash
   invisible-playwright fetch
   ```

   The engine is cached afterwards and shared with every other way into
   AIHawk.

2. **The server never appears.** Almost always the restart (must be a full
   quit, not closing the window) or JSON syntax in the config. Desktop writes
   MCP logs - a general `mcp.log` plus a per-server log carrying the server's
   own errors - and the MCP quickstart documents where they live on each
   platform. Read the per-server log before guessing.

3. **The command is not found.** The config launches
   `invisible-playwright-mcp`, which `pip install aihawk` put on your PATH, and
   a GUI application does not always inherit your shell's PATH: a terminal
   that finds it does not guarantee Desktop does. If the per-server log shows
   a not-found error, give `command` the absolute path to the script
   (`where invisible-playwright-mcp` on Windows), or your Python's absolute
   path with `["-m", "invisible_playwright_mcp"]` as the arguments.

4. **It is a Mac.** No engine build, per the boundary at the top. Nothing to
   debug.

5. **A page loads but the site pushes back.** That is not a Desktop problem
   and usually not a browser problem; work through
   [why agents get blocked](why-does-my-ai-agent-get-blocked.md) before
   changing anything.

## Short answers to the questions that lead here

**How do I add AIHawk's browser to Claude Desktop?** `pip install aihawk` and
`invisible-playwright fetch` in a terminal, then paste the server block from
the [server README](https://github.com/feder-cr/invisible-playwright-mcp) into
Desktop's MCP config (Settings, Developer, Edit Config), then fully quit and
restart Desktop. The block and file path live in that README on purpose.

**Do I need an API key for this?** No. Your Claude subscription is the model;
the server only adds the browser, and its config block contains no secret. The
OpenRouter key belongs to a different way in, AIHawk's own interface
(`aihawk ui`), which requires one.

**Why does the first instruction take so long?** The engine downloads on the
first call that needs a page, about a quarter of a gigabyte, and nothing warns
you. Prefetch it with `invisible-playwright fetch` and the first
instruction behaves like every later one.

**Why can I not see the browser?** It runs headless by default; screenshots
through the `browser_take_screenshot` tool are the intended window. The
server's `STEALTHFOX_HEADLESS=0` environment variable shows a real window if
you want one.

**Does Claude act without asking me?** By default, no: Desktop asks approval
per tool call, and you can deny any of them. Treat that gate as part of the
workflow, especially for actions with consequences; the position on submissions
in [the forms page](ai-agent-fill-out-forms.md) applies here unchanged.

**Does this work on a Mac?** Not today. Desktop runs there, but the engine has
no macOS build, so the working combination is Windows (or Linux through other
clients).

## Sources

All retrieved 2026-09-03.

- [feder-cr/invisible-playwright-mcp](https://github.com/feder-cr/invisible-playwright-mcp),
  the server's README, for the config block, the tool list, the environment
  variables and the engine-download behavior.
- [Connect to local MCP servers (modelcontextprotocol.io)](https://modelcontextprotocol.io/quickstart/user),
  for Desktop's Edit Config flow, the restart requirement, per-action
  approvals, the connectors UI and the MCP log locations.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its README in
  this repository, for the platform support boundary and the shared engine
  cache.

**See also:** [running AIHawk with Claude Code](running-aihawk-with-claude-code.md),
[running AIHawk's browser from Cursor](running-aihawk-with-cursor.md),
[browser problem or model problem?](browser-problem-or-model-problem.md), and
the rest of [Using the Agent](guides-using-the-agent.md).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The config block
lives in one README and is linked from here rather than copied, because a
config duplicated into a wiki is a config that will one day be wrong in one of
the two places.*
