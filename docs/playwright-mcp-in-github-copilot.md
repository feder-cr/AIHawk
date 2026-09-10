---
title: "A browser MCP server in GitHub Copilot: setup and limits"
description: "Give Copilot's agent mode a real browser through MCP. The config block, why isolated matters more in an editor, and the tool budget nobody warns about."
parent: "Using the Agent"
nav_order: 35
---

# A browser MCP server in GitHub Copilot

Copilot's agent mode can call MCP tools, which means it can drive a browser if
you give it one. The setup is short. What is worth reading is the part after
the setup, because an editor is a different environment from a chat client and
two of the defaults that are fine elsewhere are wrong here.

## The setup

Copilot reads MCP servers from a workspace file, `.vscode/mcp.json`, or from
your user settings if you want it in every project. The block is the same shape
every client uses: a command and its arguments.

For Microsoft's server:

```json
{
  "servers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--isolated"]
    }
  }
}
```

For this project's server the block is in
[the MCP server](mcp-server.md), which also lists the settings and every tool
with what it returns.

Then switch Copilot Chat to **agent mode**. Ask mode does not call tools, and
this is the single most common reason people conclude the server is not working
when it is registered correctly.

## Why `--isolated` matters more in an editor

The example above passes `--isolated` on purpose. In an editor you are very
likely to be the person who also has an MCP browser registered in a terminal
assistant, and two clients on one persistent profile produce
[browser is already in use](playwright-mcp-browser-already-in-use.md). An editor
is exactly where that collision shows up, because an editor is where people run
two assistants at once without noticing.

If you need to be logged in, prefer `--storage-state` over a shared persistent
profile, for the same reason.

## The tool budget, which nobody warns about

A browser server adds twenty-odd tool descriptions to the model's context on
every turn, and in an editor you probably already have several servers
registered. Copilot has a ceiling on how many tools it will offer at once, and
crossing it means some of them stop being available without a message that says
so.

The size of one browser server, measured on ours on 2026-09-10: **24 tools,
14,064 characters, about 3,500 tokens per turn.** Register two browser servers
in an editor that already has a file server and a search server and you are
spending a meaningful slice of the context window on tool descriptions before
your question arrives.

Two habits keep this from biting:

**Enable capabilities you use, not all of them.** `--caps` is additive on
Microsoft's server. Vision, pdf and devtools off unless a page forces it.

**Do not register two browser servers.** Overlapping tool names double the
context and make the model's choice worse. Pick one.

## What changes about how you prompt

In an editor the model has your repository in context, which is powerful and
also the source of the main failure mode: it will happily read the code and
guess what the page must look like rather than opening it.

- **Say "open the page" explicitly** when you want it observed rather than
  inferred. "Check whether the login form submits" reads code. "Open
  localhost:3000, fill the login form and tell me what happens" uses the browser.
- **Give it a stopping condition.** Same as anywhere else, and worse here,
  because an editor session is long and nobody is watching token spend.
  [Playwright MCP best practices](playwright-mcp-best-practices.md) has the rest.
- **Point it at your dev server, not production.** Obvious, routinely ignored,
  and the reason an agent once filled in a real form.

## When the browser is the wrong tool here

An editor already has the code. If the question is answerable from the source,
the browser is a slow way to answer it, and every browser step costs a round
trip. Reach for it when the question is about **what the running page does** -
a layout that breaks, a request that fires, a flow that only fails in a real
browser - and not when it is about what the code says.

And if what you want is a repeatable check rather than an answer today, write a
Playwright test instead and let the CLI run it.
[Playwright MCP vs the CLI](playwright-mcp-vs-cli.md) has the split.

## Short answers to the questions that lead here

**Does Copilot support MCP?** Yes, in agent mode. Ask mode does not call tools.

**Where does the config go?** `.vscode/mcp.json` for one workspace, user
settings for all of them.

**Why does Copilot not use the browser tools?** Almost always: not in agent
mode, or the tool ceiling is hit because several servers are registered.

**Can I use this with a local dev server?** Yes, and it is the best use of it in
an editor.

**Does it work in Cursor, Cline, Windsurf?** Yes, with a different top-level key
in the config file. [The MCP server](mcp-server.md) lists which key each client
expects, including the one that is not JSON.

**See also:** [Playwright MCP best practices](playwright-mcp-best-practices.md),
[running AIHawk with Claude Code](running-aihawk-with-claude-code.md), and
[using an agent to test your own site](ai-agent-to-test-website.md).

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10, for the package name, `--isolated`, `--storage-state` and `--caps`.
- GitHub's own documentation for Copilot agent mode and MCP configuration.

---

*Written while maintaining a competing MCP browser server. The example block
registers Microsoft's, because in an editor it is the one most readers already
have and the advice does not depend on which you chose.*
