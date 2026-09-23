---
title: "How to add a browser to Codex as an MCP server"
description: "Two commands install the stealth browser in Codex as a plugin, with its MCP server and a setup skill. What happens on first run, which tools Codex gains, prompts to try first, and what goes wrong."
parent: "Using the Agent"
nav_order: 68
---


# How to add a browser to Codex as an MCP server

If you already use Codex, you do not need invisible_playwright_mcp's interface, its CLI, or an
OpenRouter key. Codex brings the model; you add the browser to it. The browser
is the same MCP server invisible_playwright_mcp itself talks to -
[the MCP server](mcp-server.md) -
so anything invisible_playwright_mcp's own interface can do, your assistant can do too, and that
is by construction: the interface holds no privileged access, it calls the same
tools over the same protocol as any other client.

This page is Codex specifically. [Claude Code](how-to-use-a-playwright-mcp-server-with-claude-code.md)
and [Gemini CLI](how-to-let-gemini-cli-use-a-browser.md) have their own pages, and the
clients that take a config file instead of a command have theirs:
[Claude Desktop](how-to-let-claude-desktop-control-a-browser.md),
[Cursor](how-to-add-a-browser-to-cursor-as-an-mcp-server.md), [Cline](how-to-add-a-browser-to-cline-as-an-mcp-server.md).
The config blocks themselves live in the [MCP server page](mcp-server.md), which
is the one place they are kept current.

## The two lines

Two prerequisites, same as everywhere in this project: Python 3.11 or newer on
Windows (x86_64) or Linux (x86_64, arm64) - macOS is not supported, the last
engine build for it was `firefox-20` - and [uv](https://docs.astral.sh/uv/),
because the plugin runs the server with `uvx`. Then, once:

```bash
codex plugin marketplace add feder-cr/invisible_playwright_mcp
codex plugin add invisible-playwright-mcp@feder-cr
```

The first line registers the invisible_playwright_mcp repository as a plugin marketplace, which
it is: the repository carries the marketplace file and is the plugin. The
second installs `invisible-playwright-mcp` from it. The plugin brings two things: the MCP server,
started as `uvx invisible-playwright-mcp`, so there is nothing to clone or pip-install first; and
a `setup` skill that knows about the engine download below, so Codex can walk
you through it if `browser_open` reports that the download failed. Check with
`codex mcp list`: the server `invisible_playwright_mcp` is there, enabled, running `uvx invisible-playwright-mcp`.
Start a fresh Codex session afterwards if one was already open.

Codex's own Plugins Directory does not list invisible_playwright_mcp, and will not: a listing
there requires an MCP server reachable over HTTPS, and this one runs on your
machine by design. The marketplace above is the whole install.

## First run: the download the server does on its own

Installing the plugin does not install the browser. The engine is a patched
Firefox of roughly a quarter of a gigabyte, and the server downloads it the
first time it starts, from the moment Codex connects it - so by the time you
type a first browsing prompt, it is usually there. If it is not yet,
`browser_open` does not sit there: it answers with how far the download is and
asks to be called again in a minute, and Codex does that on its own.

To get it over with in a terminal where you can watch the progress, or after a
download that failed:

```bash
uvx invisible-playwright fetch
```

It is cached afterwards and shared by every way into the engine, including
invisible_playwright_mcp's own interface if you later run that too.

## What Codex actually gains

A set of browser tools under the server's name, `invisible_playwright_mcp`. The authoritative
list is whatever `codex mcp list` and the session show for your installed
server version; the families, with the names invisible_playwright_mcp's own client code knows
them by:

- **Navigation**: `browser_navigate`. A browser drives one page; when you
  need a second, `browser_open` opens the `support` browser beside it rather
  than a tab, so the two sites never share cookies or a fingerprint.
- **Reading the page**: `browser_read_text`, `browser_read_html`, and
  `browser_snapshot` for a structural view of what is interactive.
- **Acting on the page**: `browser_click` and `browser_click_at`,
  `browser_type`, `browser_press_key`, and `browser_select_option` for
  dropdowns, added precisely so a model never has to fake a selection
  through script.
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

- **`invisible_playwright_mcp` is not in `codex mcp list`.** Run `codex plugin list` to see
  whether the plugin is installed and enabled, and whether the marketplace
  `feder-cr` is registered. If `uvx` is not on your PATH, the plugin can be
  installed and its server still fail to start - install uv and try
  `uvx invisible-playwright-mcp` by hand, which surfaces the real error.
- **The first browsing prompt answers "the engine is downloading".** That is
  the server saying what it is doing, not a fault: ask again in a minute, or
  run the fetch command above in a terminal to watch it finish.
- **Tools appear but every call fails.** Try the one-line prompt above; if
  even `example.com` fails, the problem is below the model - the
  [browser-or-model page](browser-problem-or-model-problem.md) is the
  systematic version of that diagnosis, and blocks and challenge pages have
  [their own checklist](why-does-my-ai-agent-get-blocked.md).
- **You want a proxy, a fixed identity, or a persistent profile.** Those are
  server-side options, read from the environment Codex was started in; the
  [MCP server page](mcp-server.md) documents them. This page deliberately
  does not duplicate that reference.

## Short answers to the questions that lead here

**How do I add invisible_playwright_mcp's browser to Codex?**
`codex plugin marketplace add feder-cr/invisible_playwright_mcp`, then
`codex plugin add invisible-playwright-mcp@feder-cr`, once, with uv installed. New sessions
then have the browser tools.

**Do I need an OpenRouter key for this?** No. The key is only for invisible_playwright_mcp's own
interface and CLI, where invisible_playwright_mcp must bring a model. In Codex, Codex is the
model.

**Why does the first browsing request say the engine is downloading?** The
engine, about a quarter of a gigabyte, is downloaded by the server itself when
it starts, and `browser_open` reports the progress rather than waiting. Run
`uvx invisible-playwright fetch` once in a terminal to do it up front instead.

**Is this different from what invisible_playwright_mcp's own UI drives?** No - same server, same
engine, same tools. The interface is just another MCP client of it, with no
privileged access.

**Does it work on macOS?** No. The engine ships for Windows and Linux only;
the last macOS build was `firefox-20`.

**Why not OpenAI's Plugins Directory?** Because a listing there requires the
MCP server to be reachable at a public HTTPS address, and this server runs on
your machine, where the browser is.

## Sources

All retrieved 2026-09-22.

- [feder-cr/invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), this repository's
  README (the verbatim install commands, the prerequisites and platforms, the
  engine download), its `.codex-plugin/` and `.agents/plugins/` (the plugin
  manifest and the marketplace file the first command registers) and source:
  `src/invisible_playwright_mcp/link.py` and `src/invisible_playwright_mcp/web.py` (the interface reaching the
  browser over MCP as an ordinary client), `src/invisible_playwright_mcp/actions_help.py` (the
  tool names above).
- [OpenAI, plugins for ChatGPT and Codex](https://developers.openai.com/plugins),
  the plugin package layout, and its submission page, which is where the
  public-HTTPS requirement for directory listings is stated.
- [The MCP server page](mcp-server.md),
  the server itself: config blocks for other clients, server-side options, and
  the current tool list.

**See also:** [running invisible_playwright_mcp with Claude Code](how-to-use-a-playwright-mcp-server-with-claude-code.md),
[running invisible_playwright_mcp with Gemini CLI](how-to-let-gemini-cli-use-a-browser.md),
[how to extract data to CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md),
and [browser problem or model problem?](browser-problem-or-model-problem.md).

---

*From the [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) wiki. Codex takes the
browser as a plugin, two commands and no config file, and the server says
"downloading" instead of making you wait, so the first prompt is never a
mystery.*
