---
title: "Running invisible_playwright_mcp's browser from Claude Code"
description: "Two commands install the stealth browser in Claude Code as a plugin, with its MCP server and a setup skill. What happens on first run, which tools Claude gains, prompts to try first, and the two things that go wrong."
parent: "Using the Agent"
nav_order: 4
---


# Running invisible_playwright_mcp's browser from Claude Code

If you already use Claude Code, you do not need invisible_playwright_mcp's interface, its CLI, or
an OpenRouter key. Claude Code brings the model; you add the browser to it. The
browser is the same MCP server invisible_playwright_mcp itself talks to -
[the MCP server](mcp-server.md) -
so anything invisible_playwright_mcp's own interface can do, your assistant can do too, and that
is by construction: the interface holds no privileged access, it calls the same
tools over the same protocol as any other client.

This page is Claude Code specifically. Claude Desktop and Cursor take a config
file instead of a command, and have their own pages:
[Claude Desktop](running-aihawk-with-claude-desktop.md) and
[Cursor](running-aihawk-with-cursor.md). The config blocks themselves live in
the [MCP server page](mcp-server.md),
which is the one place they are kept current.

## The two lines

Two prerequisites, same as everywhere in this project: Python 3.11 or newer on
Windows (x86_64) or Linux (x86_64, arm64) - macOS is not supported, the last
engine build for it was `firefox-20` - and [uv](https://docs.astral.sh/uv/),
because the plugin runs the server with `uvx`. Then, once:

```bash
claude plugin marketplace add feder-cr/invisible_playwright_mcp
claude plugin install aihawk@feder-cr
```

The first line registers the invisible_playwright_mcp repository as a plugin marketplace, which
it is: the repository carries the marketplace file and is the plugin. The
second installs `aihawk` from it, at user scope by default, so it is available
in every project rather than only the directory you happened to be in. The
plugin brings two things: the MCP server, started as `uvx aihawk`, so there is
nothing to clone or pip-install first; and a `setup` skill that knows about
the engine download below, so Claude can walk you through it when
`browser_open` reports that the download failed. Start a fresh Claude Code session
afterwards if one was already open, and `/plugin` should list `aihawk` as
installed, with its server among the connected ones in `/mcp`.

If you registered the server by hand before the plugin existed, as an MCP
server named `stealth` running `uvx aihawk`, it keeps working under that name:
the plugin is the same server, plus the skill, under the name `aihawk`. Keep
one or the other, not both, or every tool shows up twice.

## First run: the download the server does on its own

Installing the server does not install the browser. The engine is a patched
Firefox of roughly a quarter of a gigabyte, and the server downloads it the
first time it starts, from the moment Claude Code connects it - so by the time
you type a first browsing prompt, it is usually there. If it is not yet,
`browser_open` does not sit there: it answers with how far the download is and
asks to be called again in a minute, and Claude does that on its own.

To get it over with in a terminal where you can watch the progress, or after a
download that failed:

```bash
uvx invisible-playwright fetch
```

It is cached afterwards and shared by every way into the engine, including
invisible_playwright_mcp's own interface if you later run that too.

## What Claude actually gains

A set of browser tools, prefixed with the server's name: `aihawk` from the
plugin, or whatever you chose when registering by hand. The
authoritative list is whatever `/mcp` shows for your installed server version;
the families, with the names invisible_playwright_mcp's own client code knows them by:

- **Navigation**: `browser_navigate`. A browser drives one page; when you
  need a second, `browser_open` opens the `support` browser beside it rather
  than a tab, so the two sites never share cookies or a fingerprint.
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

- **The server is not listed in `/mcp`.** Run `claude plugin list` in a
  terminal to see what is installed - or `claude mcp list`, for a server
  registered by hand, which also says at which scope. If the install command
  was run while a session was open, the running session may not know it yet;
  start a new one. If `uvx` is not on your PATH, the plugin can be installed
  and its server still fail to start - install uv and try `uvx aihawk` by
  hand, which surfaces the real error.
- **The first browsing prompt answers "the engine is downloading".** That is
  the server saying what it is doing, not a fault: ask again in a minute, or
  run the fetch command above in a terminal to watch it finish.
- **Tools appear but every call fails.** Try the one-line prompt above; if
  even `example.com` fails, the problem is below the model - the
  [browser-or-model page](browser-problem-or-model-problem.md) is the
  systematic version of that diagnosis, and blocks and challenge pages have
  [their own checklist](why-does-my-ai-agent-get-blocked.md).
- **You want a proxy, a fixed identity, or a persistent profile.** Those are
  server-side options, configured where the server is configured; the
  [MCP server page](mcp-server.md)
  documents them. This page deliberately does not duplicate that reference.

## Short answers to the questions that lead here

**How do I add invisible_playwright_mcp's browser to Claude Code?**
`claude plugin marketplace add feder-cr/invisible_playwright_mcp`, then
`claude plugin install aihawk@feder-cr`, once, with uv installed. New
sessions then have the browser tools in `/mcp`.

**Do I need an OpenRouter key for this?** No. The key is only for invisible_playwright_mcp's own
interface and CLI, where invisible_playwright_mcp must bring a model. In Claude Code, Claude is
the model.

**Why does the first browsing request say the engine is downloading?** The
engine, about a quarter of a gigabyte, is downloaded by the server itself when
it starts, and `browser_open` reports the progress rather than waiting. Run
`uvx invisible-playwright fetch` once in a terminal to do it up front instead.

**Is this different from what invisible_playwright_mcp's own UI drives?** No - same server, same
engine, same tools. The interface is just another MCP client of it, with no
privileged access.

**Does it work on macOS?** No. The engine ships for Windows and Linux only;
the last macOS build was `firefox-20`.

**Can Claude Code and the invisible_playwright_mcp UI share the setup?** The downloaded engine
is cached once and shared. The server process itself is per-client - each
client starts its own - so a page open in one is not visible in the other.

**What else should I register alongside it?** That is a question about your
whole tool budget rather than about this server, because every registered
server spends context on every turn:
[MCP servers for Claude Code](best-mcp-servers-for-claude-code.md) goes
through what is worth the slot, and
[how many MCP tools is too many](how-many-mcp-tools-is-too-many.md) has the
arithmetic measured on this one.

## Sources

All retrieved 2026-09-03.

- [feder-cr/invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), this repository's
  README (the verbatim install commands, the prerequisites and platforms, the
  engine download and prefetch, "anything the interface can do, your assistant
  can do too"), its `.claude-plugin/` (the plugin manifest and the marketplace
  file the first command registers) and source: `src/aihawk/link.py` and `src/aihawk/web.py` (the
  interface reaching the browser over MCP as an ordinary client),
  `src/aihawk/actions_help.py` (the tool names above), and `pyproject.toml`
  (the engine version floor, and the server that ships inside the package since 0.10.0).
- [The MCP server page](mcp-server.md),
  the server itself: config blocks for other clients, server-side options, and
  the current tool list.

**See also:** [running invisible_playwright_mcp with Claude Desktop](running-aihawk-with-claude-desktop.md),
[running invisible_playwright_mcp with Cursor](running-aihawk-with-cursor.md),
[how to extract data to CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md),
and [browser problem or model problem?](browser-problem-or-model-problem.md).

---

*From the [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) wiki. Claude Code is
the shortest route into this browser - a plugin, against a config file
everywhere else - and the README calls the engine fetch "the download nobody
warns you about", so consider yourself warned.*
