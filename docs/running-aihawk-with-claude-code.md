---
title: "Running AIHawk's browser from Claude Code"
description: "One command adds the stealth browser to Claude Code as an MCP server. What happens on first run, which tools Claude gains, prompts to try first, and the two things that go wrong."
parent: "Using the Agent"
nav_order: 4
---


# Running AIHawk's browser from Claude Code

If you already use Claude Code, you do not need AIHawk's interface, its CLI, or
an OpenRouter key. Claude Code brings the model; you add the browser to it. The
browser is the same MCP server AIHawk itself talks to -
[invisible-playwright-mcp](https://github.com/feder-cr/invisible-playwright-mcp) -
so anything AIHawk's own interface can do, your assistant can do too, and that
is by construction: the interface holds no privileged access, it calls the same
tools over the same protocol as any other client.

This page is Claude Code specifically. Claude Desktop and Cursor take a config
file instead of a command, and have their own pages:
[Claude Desktop](running-aihawk-with-claude-desktop.md) and
[Cursor](running-aihawk-with-cursor.md). The config blocks themselves live in
the [server's README](https://github.com/feder-cr/invisible-playwright-mcp),
which is the one place they are kept current.

## The three lines

One prerequisite, the same as everywhere in this project: Python 3.11 or newer
on Windows (x86_64) or Linux (x86_64, arm64) - macOS is not supported, the last
engine build for it was `firefox-20`. Then, once:

```bash
pip install aihawk
invisible-playwright fetch
claude mcp add --scope user stealth -- invisible-playwright-mcp
```

The first line installs AIHawk and, with it, the MCP server. The second
downloads the browser itself, a patched Firefox of roughly a quarter of a
gigabyte, once, in a terminal where you can watch it. Reading the third left to
right: `--scope user` registers the server at user scope, so it is available in
every project rather than only the directory you happened to be in; `stealth`
is the name it appears under; everything after `--` is the command Claude Code
will run to start the server, which the first line put on your PATH. Start a
fresh Claude Code session afterwards if one was already open, and `/mcp` should
list `stealth` among the connected servers.

## First run, if you skipped the fetch

Installing the server does not install the browser; the second line above
does. Skip it and the engine downloads on the first request that needs a page,
which, from inside a chat, looks like your first browsing prompt sitting there
doing nothing, and on a slow connection can end in a timeout message that says
nothing about a download. Run `invisible-playwright fetch` in a terminal
instead; it is cached afterwards and shared by every way into the engine,
including AIHawk's own interface if you later run that too.

## What Claude actually gains

A set of browser tools, prefixed with the server name you chose. The
authoritative list is whatever `/mcp` shows for your installed server version;
the families, with the names AIHawk's own client code knows them by:

- **Navigation and tabs**: `browser_navigate`, plus `session_new_page`,
  `session_select_page`, `session_close_page` and `session_list_pages` for
  working across tabs.
- **Reading the page**: `browser_read_text`, `browser_read_html`, and
  `browser_snapshot` for a structural view of what is interactive.
- **Acting on the page**: `browser_click` and `browser_click_at`,
  `browser_type`, `browser_press_key`, and - since server 0.10.0 -
  `browser_select_option` for dropdowns, added precisely so a model never has
  to fake a selection through script.
- **Seeing it**: `browser_take_screenshot`.

Behind the tools is the point of the exercise: a real patched Firefox that
drives pages through actual input events, not a headless toolkit. What that
buys, and what it honestly does not, is the
[blocked page's](why-does-my-ai-agent-get-blocked.md) subject.

## Three prompts to try first

Start small, so the first success and the first failure are both legible:

> Go to example.com and tell me the main heading on the page.

One navigation, one read. If this works, the server, the engine and the wiring
all work. Then something with a decision in it:

> Go to [paste the URL of a docs page you actually read] and find the section
> about installation. Quote the exact command it recommends.

Then something multi-step, the shape most real use takes:

> Open [paste the URL of a public page with a list on it], read the first ten
> entries, and give them to me as a table with a link column.

If that last shape is your actual goal, the
[extract-to-CSV page](how-to-extract-data-to-csv-with-an-ai-agent.md) takes it
the rest of the way. One habit worth forming from the start: ask for one page
and one outcome per prompt. The assistant sees the page only through tool
results, and short steps keep its context small and its mistakes cheap.

## Troubleshooting

- **`stealth` is not listed in `/mcp`.** Run `claude mcp list` in a terminal
  to see what is registered and at which scope. If the add command was run
  while a session was open, the running session may not know it yet; start a
  new one. If `invisible-playwright-mcp` is not on your PATH, the server can
  be registered and still fail to start: run it by hand in a terminal, which
  surfaces the real error, or register it as
  `python -m invisible_playwright_mcp` instead of the bare name.
- **The first browsing prompt hangs or times out.** Almost always the engine
  download. Run the prefetch command above and retry; afterwards a first page
  load is seconds, not minutes.
- **Tools appear but every call fails.** Try the one-line prompt above; if
  even `example.com` fails, the problem is below the model - the
  [browser-or-model page](browser-problem-or-model-problem.md) is the
  systematic version of that diagnosis, and blocks and challenge pages have
  [their own checklist](why-does-my-ai-agent-get-blocked.md).
- **You want a proxy, a fixed identity, or a persistent profile.** Those are
  server-side options, configured where the server is configured; the
  [server's README](https://github.com/feder-cr/invisible-playwright-mcp)
  documents them. This page deliberately does not duplicate that reference.

## Short answers to the questions that lead here

**How do I add AIHawk's browser to Claude Code?**
`pip install aihawk`, `invisible-playwright fetch`, then
`claude mcp add --scope user stealth -- invisible-playwright-mcp`, once. New
sessions then have the browser tools in `/mcp`.

**Do I need an OpenRouter key for this?** No. The key is only for AIHawk's own
interface and CLI, where AIHawk must bring a model. In Claude Code, Claude is
the model.

**Why does the first browsing request take so long?** The engine, about a
quarter of a gigabyte, downloads on the first request that needs a page. Run
`invisible-playwright fetch` once in a terminal to do it up front.

**Is this different from what AIHawk's own UI drives?** No - same server, same
engine, same tools. The interface is just another MCP client of it, with no
privileged access.

**Does it work on macOS?** No. The engine ships for Windows and Linux only;
the last macOS build was `firefox-20`.

**Can Claude Code and the AIHawk UI share the setup?** The downloaded engine
is cached once and shared. The server process itself is per-client - each
client starts its own - so a page open in one is not visible in the other.

## Sources

All retrieved 2026-09-03.

- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), this repository's
  README (the verbatim install, fetch and add commands, "anything the
  interface can do, your assistant can do too") and source: `src/aihawk/link.py` and `src/aihawk/web.py` (the
  interface reaching the browser over MCP as an ordinary client),
  `src/aihawk/actions_help.py` (the tool names above), and `pyproject.toml`
  (the server version floor and why `browser_select_option` is in it).
- [feder-cr/invisible-playwright-mcp](https://github.com/feder-cr/invisible-playwright-mcp),
  the server itself: config blocks for other clients, server-side options, and
  the current tool list.

**See also:** [running AIHawk with Claude Desktop](running-aihawk-with-claude-desktop.md),
[running AIHawk with Cursor](running-aihawk-with-cursor.md),
[how to extract data to CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md),
and [browser problem or model problem?](browser-problem-or-model-problem.md).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. Claude Code is
the shortest route into this browser - one command, against a config file
everywhere else - and the README puts the engine fetch right after the install,
so consider yourself warned.*
