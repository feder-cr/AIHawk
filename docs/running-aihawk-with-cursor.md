---
title: "Running AIHawk's browser from Cursor"
description: "Adding the stealth browser to Cursor via mcp.json - what a real browser adds to an editor workflow, project vs global config, first prompts, and the first-run issues."
parent: "Using the Agent"
nav_order: 9
---


# Running AIHawk's browser from Cursor

Cursor reads MCP servers from a JSON file, at one of two levels its docs
define: `.cursor/mcp.json` inside a project, for tools scoped to that project,
or `~/.cursor/mcp.json` in your home directory, for tools available everywhere.
The block to paste is the same either way and it lives in the
[server's README](https://github.com/feder-cr/invisible-playwright-mcp), which
this page links rather than copies. What belongs here is the Cursor-side story:
what a browser is actually for inside an editor, how Cursor runs the tools,
what to try first, and the first-run issues.

The platform boundary first: AIHawk's engine ships for Windows (x86_64) and
Linux (x86_64, arm64). There is no macOS build, so on a Mac, Cursor will start
the server and the server will have nothing to run. This combination works on
Windows and Linux today.

## What a browser adds to an editor, honestly

Cursor's agent already reads your code and can search the web. A driveable
browser is a different capability, and it is worth being precise about when it
earns its place, because for a quick documentation lookup it is overkill:

- **Research that means driving pages, not fetching them.** Docs behind a
  version switcher, a changelog that loads on scroll, a comparison that
  requires clicking through three product pages: anything where the answer
  requires acting on the page rather than downloading it once.
- **Testing your own web app through a realistic browser.** This is the
  editor-native use. Point the agent at your dev server and have it register a
  user, walk the checkout wizard, or hammer the validation on the form you
  just wrote, then report what it saw. The browser is a real patched Firefox,
  so what it renders and the events it sends are what a person's browser would
  render and send, real key presses and clicks rather than scripted value
  injection. Since the same agent also sees your code, "try to reproduce the
  bug in the app, then look at the handler and tell me why" is one
  conversation.
- **Reading pages that push back on plain fetchers.** A page that returns
  little or nothing to a simple HTTP fetch may read fine through a real
  browser. Where a site pushes back beyond that, the honest map of why is
  [the blocked page](why-does-my-ai-agent-get-blocked.md), and no tool
  promises you through it.

What it does not add: speed. A browser session plus model turns is the slow,
deliberate path. If a `curl` would answer the question, the browser is the
wrong tool, the same boundary
[the scraping comparison](ai-browser-agents-vs-traditional-scraping.md) draws
at length.

## Config: project or global, and how Cursor runs the tools

Two terminal steps come first, `pip install aihawk` and
`invisible-playwright fetch`; the JSON only tells Cursor how to start what they
installed. Choose the level by audience. Global (`~/.cursor/mcp.json`) makes the browser
available in every project, which fits a personal research tool. Project-level
(`.cursor/mcp.json`) travels with the repository, which fits a team that wants
"the agent can drive our staging app" to be part of the checkout. The server's
block contains a command and arguments, no key and no secret - Cursor brings
the model, and there is nothing to sign up for on the AIHawk side - so
committing it is as safe as config-committing gets; whether your
team wants editor tooling in the repo is a team question, not a security one.

On the running side, Cursor's own docs state the two behaviors that matter:
the agent uses MCP tools automatically when it judges them relevant, and it
asks for your approval before running a tool by default, with settings that
let allowlisted tools run without asking. Servers can also be toggled on and
off from Cursor's settings without deleting their config. Practical
consequences: you do not call tools, you describe outcomes and approve steps;
and if you stop wanting the browser in a project, the toggle beats editing
JSON.

The tools themselves come in two families: session tools for tabs
(`session_new_page` and friends) and page tools (`browser_navigate`,
`browser_read_text`, `browser_snapshot`, `browser_click`, `browser_type`,
`browser_take_screenshot`, among others). You will see these names in the
agent's transcript as it works, each gated by an approval until you loosen
that.

## First prompts to try

The first prompt is the installation test, so make it small and checkable:

> Open https://books.toscrape.com/ and tell me the title and price of the
> first book on the page.

The example site is a sandbox built for practice. If that works, the whole
path works: server started, engine present, page loaded, text read.

Then the editor-native one, against something you own:

> Start the dev server's page at http://localhost:3000. Register a new user
> through the signup form with placeholder data, do not submit the final
> step, and list every validation message you encounter on the way.

Two notes on that prompt. "Do not submit" is deliberate: keeping the
consequential click human is the standing advice from
[the forms page](ai-agent-fill-out-forms.md), and it applies to your own app
the moment the data is real. And the localhost target keeps your first
sessions where mistakes are free.

The browser is headless by default, so the agent's screenshots
(`browser_take_screenshot`) are your view of what happened. When you would
rather watch it drive your app, the server reads `STEALTHFOX_HEADLESS=0` from
its environment, set in the same config block; the README documents the rest
of the environment variables (a persistent profile directory and a fixed
identity seed are the two most useful for repeated testing).

## Common first-run issues

1. **The first page-touching prompt stalls.** The engine, about a quarter of
   a gigabyte, is not fetched at install or server start; it downloads on the
   first tool call that needs a page, and on a slow connection that reads as
   the agent hanging, sometimes ending in a timeout that never mentions a
   download. Prefetch it once, in a terminal where you can watch:

   ```bash
   invisible-playwright fetch
   ```

   The engine is cached and shared with every other way into AIHawk.

2. **The server does not appear in Cursor's MCP list.** Check the JSON, check
   the file is at one of the two documented locations, and check that
   `invisible-playwright-mcp` resolves for Cursor: `pip install aihawk` put it
   on your PATH, but an editor does not always inherit your shell's PATH, so
   one working terminal is no guarantee. If it is not found, give `command`
   the absolute path to the script (`where invisible-playwright-mcp` on
   Windows, `which` elsewhere), or your Python's absolute path with
   `["-m", "invisible_playwright_mcp"]` as the arguments.

3. **Tools exist but every step asks permission.** That is the documented
   default, and while you are learning what the browser does, leave it on.
   Cursor's settings allow allowlisting once you trust the pattern; loosen
   deliberately, not on day one.

4. **It is a Mac.** No engine build; nothing to debug.

5. **A public site loads oddly or pushes back.** Before touching config,
   separate the layers: [browser problem or model problem](browser-problem-or-model-problem.md)
   for the local half, and [why agents get blocked](why-does-my-ai-agent-get-blocked.md)
   for the site half.

## Short answers to the questions that lead here

**How do I add AIHawk's browser to Cursor?** `pip install aihawk` and
`invisible-playwright fetch` in a terminal, then paste the block from the
[server README](https://github.com/feder-cr/invisible-playwright-mcp) into
`.cursor/mcp.json` in a project or `~/.cursor/mcp.json` globally, both
locations per Cursor's own MCP docs. No key, no signup; Cursor's model does
the thinking.

**Should the config be project-level or global?** Global for a personal
research tool, project-level when a team wants the capability versioned with
the repo. The block carries no secrets, so the choice is about scope, not
safety.

**Does Cursor's agent use the browser on its own?** It selects MCP tools
automatically when relevant, but by default each tool run waits for your
approval; allowlisting for automatic runs is a setting you opt into later.

**What is this actually good for in an editor?** Driving and testing your own
web app through a realistic browser, and research that requires acting on
pages rather than fetching them. For lookups a plain search answers, skip the
browser.

**Why is the first instruction so slow?** Engine download: a quarter of a
gigabyte on the first call that needs a page, silent from the editor's side.
`invisible-playwright fetch` in a terminal moves that cost to a moment you
choose.

**Can I watch the browser work?** By default no, it is headless and the
screenshot tool is the window. Set `STEALTHFOX_HEADLESS=0` in the server's
environment block to get a real window, which is genuinely useful when it is
driving your own app.

## Sources

All retrieved 2026-09-03.

- [Cursor docs: Model Context Protocol](https://cursor.com/docs/context/mcp),
  for the two config locations, automatic tool use with default approval, and
  server toggling.
- [feder-cr/invisible-playwright-mcp](https://github.com/feder-cr/invisible-playwright-mcp),
  the server's README, for the config block, tool list, environment variables
  and engine-download behavior.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its README in
  this repository, for platform support, the real-input-events behavior and
  the shared engine cache.

**See also:** [running AIHawk with Claude Code](running-aihawk-with-claude-code.md),
[running AIHawk's browser from Claude Desktop](running-aihawk-with-claude-desktop.md),
[getting an AI agent to fill out forms](ai-agent-fill-out-forms.md), and
[extracting data to a CSV](how-to-extract-data-to-csv-with-an-ai-agent.md).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The strongest
Cursor use the maintainer has seen is the least glamorous: the agent filling
out your own half-built form, badly, and telling you exactly where it broke.*
