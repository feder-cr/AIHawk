---
title: "Running AIHawk's browser from Cline"
description: "Adding the stealth browser to Cline via its MCP settings JSON - the Configure tab route, approvals and autoApprove, first prompts, and the first-run issues."
parent: "Using the Agent"
nav_order: 15
---


# Running AIHawk's browser from Cline

Cline, the open-source coding agent that lives in VS Code, takes its MCP
servers as JSON entries under an `mcpServers` key, edited from inside the
extension: the MCP Servers icon in Cline's top toolbar, then the Configure
tab, then the Configure MCP Servers button, which opens the settings file for
editing. That path, and the field names an entry takes, are from Cline's own
MCP documentation. The block to paste is the same one every JSON-configured
client uses and it lives in the
[server's README](https://github.com/feder-cr/invisible-playwright-mcp),
which this page links rather than copies, for the reason the
[Claude Desktop page](running-aihawk-with-claude-desktop.md) gives: a config
duplicated into a wiki is a config that rots in one of the two places.

The platform boundary, stated before you spend time: AIHawk's engine ships
for Windows (x86_64) and Linux (x86_64, arm64), with no macOS build. VS Code
and Cline run happily on a Mac; the server they start there would have no
engine to run. This combination works on Windows and Linux today.

## What changes after the server is added

After `pip install aihawk` and `invisible-playwright fetch` in a terminal,
paste the README's block under `mcpServers` in the file the Configure tab
opens, and Cline gains the browser as a set of tools. A server entry in that
file carries a `command` and `args` (here: `invisible-playwright-mcp`, which
the install put on your PATH, and no arguments), an optional `env` map, and two Cline-side
fields worth knowing from day one: `disabled`, which switches a server off
without deleting its entry, and `autoApprove`, a list of tool names allowed
to run without asking you each time.

The tools arrive in the same two families every other client sees: session
tools for tabs (`session_new_page` and friends) and page tools
(`browser_navigate`, `browser_read_text`, `browser_snapshot`,
`browser_click`, `browser_type`, `browser_take_screenshot`, among others).
Cline decides when a tool is relevant to your request and asks your approval
before running it; you describe outcomes and approve steps rather than
invoking anything by name. Cline's docs advise limiting `autoApprove` to
safe tools, and on a browser that acts on the real web the reading tools are
the sane candidates while the acting ones stay gated - the same
keep-the-consequential-click-human position
[the forms page](ai-agent-fill-out-forms.md) argues for everything
form-shaped.

Nothing else changes. There is no new account and no key on the AIHawk side:
whatever model you already run Cline on does the thinking, the server brings
only the browser, and the config block carries no secret. Nothing launches
eagerly either; the browser exists from the first instruction that needs a
page.

## What the browser is for inside Cline

Cline's center of gravity is your codebase, so the browser earns its place
the same way it does [in Cursor](running-aihawk-with-cursor.md): testing
your own app through a realistic browser, in the same conversation as the
agent that has your code open. "Open the local dev server, walk the signup
flow, then look at the handler and explain the 500" is one request here.
The worked version of that pattern, including what agent testing catches and
where it is honestly flaky, is on
[the website-testing page](ai-agent-to-test-website.md). The second use is
research that needs driving rather than fetching - pages built by
JavaScript, walks through paginated docs - which
[the research page](ai-agent-web-research.md) maps against cheaper tools.

For a plain lookup Cline's normal abilities already cover, skip the browser;
a session plus model turns is the slow path, and it should be spent where
acting on a page is the point.

## First prompts to try

The first prompt is the installation test, so make it small and checkable:

> Open https://books.toscrape.com/ and tell me the title and price of the
> first book on the page.

One approved navigation, one read, one grounded answer, and you have
verified the whole chain: config parsed, server started, engine present,
page loaded. The site is a sandbox built for practice.

Then the Cline-native one, against something you own:

> Start from http://localhost:3000. Try to register a new user with
> placeholder data, stop before the final submit, and list every validation
> message you saw. Then open the signup handler in this repo and tell me
> whether the messages match what the code enforces.

That second half is the reason to have a browser in a coding agent at all:
the observation and the code review happen in one context.

The browser is headless by default; the agent's screenshots
(`browser_take_screenshot`) are your window. To watch it drive - worth doing
at least once against your own app - set `STEALTHFOX_HEADLESS=0` in the
server entry's `env` map. The README documents the rest of the environment
variables; a persistent profile directory and a fixed identity seed are the
two most useful for repeated testing sessions.

## Common first-run issues

1. **The first page-touching prompt stalls.** The engine is a separate
   download of about a quarter of a gigabyte, fetched on the first tool call
   that needs a page, not at install. Inside an editor that reads as the
   agent hanging on an approved step, and a slow connection can turn it into
   a timeout that never mentions a download. Prefetch it once, in a terminal
   where you can watch:

   ```bash
   invisible-playwright fetch
   ```

   The engine is cached and shared with every other way into AIHawk.

2. **The server never appears.** Check the JSON you pasted (a trailing comma
   is the classic), and check that `invisible-playwright-mcp` resolves for
   the process VS Code runs: `pip install aihawk` put it on your PATH, but an
   editor does not always inherit your shell's PATH, so one working terminal
   is no guarantee. If it is not found, give `command` the absolute path to
   the script (`where invisible-playwright-mcp` on Windows, `which`
   elsewhere), or your Python's absolute path with
   `["-m", "invisible_playwright_mcp"]` as the arguments. The `disabled`
   field is also worth a glance before deeper debugging.

3. **Every step asks permission.** That is the design default, and while you
   are learning what the browser does, keep it. Loosen deliberately by
   adding read-only tools to `autoApprove` once the pattern is boring;
   Cline's own security note points the same way.

4. **It is a Mac.** No engine build, per the boundary at the top; nothing to
   debug.

5. **A public site loads oddly or pushes back.** Separate the layers before
   touching config:
   [browser problem or model problem](browser-problem-or-model-problem.md)
   for the local half,
   [why agents get blocked](why-does-my-ai-agent-get-blocked.md) for the
   site half.

## Short answers to the questions that lead here

**How do I add AIHawk's browser to Cline?** `pip install aihawk` and
`invisible-playwright fetch` in a terminal; then MCP Servers icon in Cline's
toolbar, Configure tab, Configure MCP Servers, then paste the block from the
[server README](https://github.com/feder-cr/invisible-playwright-mcp) under
`mcpServers` and save. No key, no signup; Cline's model does the thinking.

**Does Cline use the browser automatically?** It picks tools it judges
relevant, and by default asks approval per run. The `autoApprove` list makes
chosen tools run unasked; keep it to reading tools while the browser is new.

**Do I need an API key for the browser?** No. The server's block carries no
secret and there is nothing to sign up for; your existing Cline model setup
is untouched. The OpenRouter key belongs to AIHawk's own interface
(`aihawk ui`), a different way in, and that one requires it.

**Why is the first instruction so slow?** Engine download: about a quarter
of a gigabyte on the first call that needs a page, silent from the editor's
side. `invisible-playwright fetch` in a terminal moves that wait to a
moment you choose.

**Can I watch it drive?** Headless by default, screenshots as the window.
Set `STEALTHFOX_HEADLESS=0` in the server entry's `env` to get a real
window, which is genuinely useful when it is testing your own app.

**Does this work on a Mac?** Not today: Cline runs there, the engine does
not. Windows and Linux are the working platforms.

## Sources

All retrieved 2026-09-03.

- [Cline docs: configuring MCP servers](https://docs.cline.bot/mcp/configuring-mcp-servers),
  for the Configure-tab route, the `mcpServers` JSON shape, the `disabled`
  and `autoApprove` fields, and the limit-autoApprove security advice, with
  [the MCP overview](https://docs.cline.bot/mcp/mcp-overview) for the
  transport picture.
- [feder-cr/invisible-playwright-mcp](https://github.com/feder-cr/invisible-playwright-mcp),
  the server's README, for the config block, the tool list, the environment
  variables and the engine-download behavior.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its README in
  this repository, for the platform boundary and the shared engine cache.

**See also:** [running AIHawk with Claude Code](running-aihawk-with-claude-code.md),
[running AIHawk's browser from Claude Desktop](running-aihawk-with-claude-desktop.md),
[running AIHawk's browser from Cursor](running-aihawk-with-cursor.md), and
[using an AI agent to test your own website](ai-agent-to-test-website.md).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. Fourth client,
same block, same README: the config canon lives in one place on purpose, and
this page is the tour around it, not a copy of it.*
