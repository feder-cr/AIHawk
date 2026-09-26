---
title: "How to let the AdaL CLI use a browser"
description: "Adding the stealth browser to the AdaL CLI with one slash command, no config file to edit - what a real browser adds to a terminal agent, the /mcp panel, first prompts, and the first-run issues."
parent: "Using the Agent"
nav_order: 86
---


# How to let the AdaL CLI use a browser

AdaL is a coding agent that lives in the terminal, from SylphAI. It adds MCP
servers with a slash command rather than a config file: there is no JSON to
paste and no file to hunt for, one line inside a running session registers
the server and AdaL keeps its own settings. The tool list and the
environment variables live in the
[MCP server page](mcp-server.md), which
this page links rather than copies, for the reason the
[Claude Desktop page](how-to-let-claude-desktop-control-a-browser.md) gives: a config
duplicated across two pages is a config that rots in one of the two places.

The platform boundary, stated before you spend time: invisible_playwright_mcp's engine ships
for Windows (x86_64) and Linux (x86_64, arm64), with no macOS build. AdaL
runs happily on a Mac; the server it starts there would have no engine to
run. This combination works on Windows and Linux today.

## The one line

Start AdaL in your working directory, then, inside the session:

`/mcp add stealth --command uvx --args "invisible-playwright-mcp"`

The name is what the panel calls it and you can choose another; the command
and the argument are the same `uvx invisible-playwright-mcp` every client runs, and they carry
no key and no secret. AdaL writes the entry into its own settings (the same
command with `--env "KEY=value"` on the end attaches environment variables,
which is how you pass the proxy or the headed flag), so there is nothing to
edit by hand afterwards. [uv](https://docs.astral.sh/uv/) must be installed
where the AdaL process finds it, which one working shell does not guarantee.

Nothing authenticates. The server runs on your machine, talks to no account,
and needs no sign-in from AdaL or from you; whatever model you already run
AdaL on does the thinking, and the server brings only the browser.

## Checking the add: the /mcp panel

"Added" is not "connected", which is the standing warning on the
[MCP server page](mcp-server.md) and applies
here as much as to the file-editing clients. AdaL keeps a panel, opened with
`/mcp`, where every registered server shows a status: connected, disabled,
or an error. From the same panel you can run a connection test, toggle the
server off without deleting its entry, and remove it. That test is the
fastest triage: it starts the server and lists its tools, so a `uvx` that
does not resolve on the AdaL process reads as an error there rather than as
a mystery later, and [a thirty-line MCP client](writing-an-mcp-client-in-python.md)
is the fallback when you want to prove the server alone.

The tools arrive with the names every other client sees: `browser_open` and
friends for the two browsers, and the page tools (`browser_navigate`,
`browser_read_text`, `browser_snapshot`, `browser_click`, `browser_type`,
`browser_take_screenshot`, among others). You do not call them by name; you
describe an outcome, AdaL picks the tools it judges relevant, and the calls
stay visible in the transcript as it works.

## What the browser is for inside a terminal agent

AdaL's center of gravity is your codebase and its terminal, so the browser
earns its place the way it does
[in Cursor](how-to-add-a-browser-to-cursor-as-an-mcp-server.md):
testing your own app through a realistic browser in the same conversation
that has your code open. "Open the dev server, walk the signup flow, then
look at the handler and explain the 500" is one request here, and the
worked version of that pattern, including what agent testing catches and
where it is honestly flaky, is on
[the website-testing page](ai-agent-to-test-website.md).
The second use is research that needs driving rather than fetching: pages
built by JavaScript, walks through paginated docs, which
[the research page](ai-agent-web-research.md) maps
against cheaper tools.

There is a third pairing worth naming, because the terminal is where it fits
best: AdaL is scriptable headless (`adal -q "..."` runs one query and
exits), so "this browser task, run nightly" is a cron line rather than an
app. The schedule pattern and what it costs are on
[run an AI browser agent on a schedule](run-ai-agent-on-a-schedule.md).

For a plain lookup AdaL's own web search already covers, skip the browser; a
session plus model turns is the slow path, and it should be spent where
acting on a page is the point.

## First prompts to try

The first prompt is the installation test, so make it small and checkable:

> Open https://books.toscrape.com/ and tell me the title and price of the
> first book on the page.

One navigation, one read, one grounded answer, and the whole chain is
verified: entry parsed, server started, engine present, page loaded. The
site is a sandbox built for practice.

Then the terminal-native one, against something you own:

> Start from http://localhost:3000. Try to register a new user with
> placeholder data, stop before the final submit, and list every validation
> message you saw. Then open the signup handler in this repo and tell me
> whether the messages match what the code enforces.

That second half is the reason to have a browser in a coding agent at all:
the observation and the code review happen in one context. "Do not submit"
is deliberate, the same keep-the-consequential-click-human position
[the forms page](ai-agent-fill-out-forms.md)
argues for everything form-shaped.

The browser is headless by default; `browser_take_screenshot` is how you see
the page. To watch it drive instead, remove the entry in the `/mcp` panel and
re-add it with `--env "STEALTHFOX_HEADLESS=0"`, or just run AdaL on a Windows
or Linux box where a window can appear. The live view of the whole window,
chrome and pointer included, is `browser_watch`, on
[watching the agent work](watching-the-agent-work.md). The rest of the
environment variables, a persistent profile directory and a fixed identity
seed among them, are on the [MCP server page](mcp-server.md).

## Common first-run issues

1. **The first page-touching prompt answers that the engine is downloading.**
   The engine, about a quarter of a gigabyte, is fetched by the server on its
   own from the moment AdaL starts it; a browser asked for before it is done
   is answered with the progress, and AdaL asks again a minute later. To
   prefetch it once, in a terminal where you can watch:

   ```bash
   uvx invisible-playwright fetch
   ```

   The engine is cached and shared with every other way into invisible_playwright_mcp.

2. **The server shows an error in the `/mcp` panel.** Check that `uvx`
   resolves for the process AdaL runs: the entry launches the server with
   `uvx`, so uv must be installed where the terminal finds it, which a shell
   alias does not guarantee. The panel's connection test is the quickest way
   to tell a broken registration from a broken server.

3. **The tools appear but nothing seems to use them.** Describe outcomes,
   not tool calls: the model picks tools when it judges them relevant, and a
   prompt that can be answered from memory will be. "Open this URL and read
   it" forces the browser; "what is on that site" may not.

4. **It is a Mac.** No engine build, per the boundary at the top; nothing to
   debug.

5. **A public site loads oddly or pushes back.** Separate the layers before
   touching config:
   [browser problem or model problem](browser-problem-or-model-problem.md)
   for the local half, and
   [why agents get blocked](why-does-my-ai-agent-get-blocked.md) for the
   site half.

## Short answers to the questions that lead here

**How do I add invisible_playwright_mcp's browser to AdaL?** Inside a session, run
`/mcp add stealth --command uvx --args "invisible-playwright-mcp"` and
check the `/mcp` panel for its status. No file to edit, no key, no signup;
AdaL's model does the thinking.

**Where does AdaL keep the config?** In its own settings, written by the
add command. There is no file to hand-edit, which is the point of the
slash-command route; changing the entry usually means removing it in the
`/mcp` panel and re-adding it with what changed.

**Do I need an API key for the browser?** No. The server's entry carries no
secret and there is nothing to sign up for; your existing AdaL model setup is
untouched. The OpenRouter key belongs to invisible_playwright_mcp's own interface
(`uvx invisible-playwright-mcp ui`), a different way in, and that one requires it.

**Why does the first instruction say the engine is downloading?** Engine
download: about a quarter of a gigabyte, started by the server when AdaL
starts it, reported by `browser_open` until it is done.
`uvx invisible-playwright fetch` in a terminal moves that wait to a moment
you choose.

**Can I watch it drive?** Headless by default, and `browser_take_screenshot`
shows the page. Re-add the entry with `--env "STEALTHFOX_HEADLESS=0"` to get
a real window, which is genuinely useful when it is testing your own app.
The whole window is `browser_watch`, on
[watching the agent work](watching-the-agent-work.md).

**Does this work on a Mac?** Not today: AdaL runs there, the engine does
not. Windows and Linux are the working platforms.

## Sources

All retrieved 2026-09-21.

- [AdaL docs: MCP servers](https://docs.sylph.ai/features/mcp-support-proposed/),
  for the slash-command add syntax, the `--command`, `--args`, `--env` and
  `--url` flags, the `/mcp` panel and its status labels, and the
  no-config-files framing.
- [The MCP server page](mcp-server.md), for the
  config block, the tool list, the environment variables, the engine-download
  behavior and the "added is not connected" warning.
- [feder-cr/invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), plus its README in
  this repository, for the platform boundary and the shared engine cache.

**See also:** [using a Playwright MCP server with Claude Code](how-to-use-a-playwright-mcp-server-with-claude-code.md),
[adding a browser to Codex as an MCP server](how-to-add-a-browser-to-codex-as-an-mcp-server.md),
[letting Gemini CLI use a browser](how-to-let-gemini-cli-use-a-browser.md), and
[using an AI agent to test your own website](ai-agent-to-test-website.md).

---

*From the [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) wiki. AdaL takes
the browser with one slash command and no config file, and the config canon
still lives in one place on purpose: this page is the tour around it, not a
copy of it.*
