---
title: "Which MCP servers are worth adding to Claude Code"
description: "Claude Code already does files, shell and git natively, so most starter lists recommend things it does not need. What is actually missing, and what each addition costs."
parent: "Alternatives and Comparisons"
nav_order: 34
---

# Which MCP servers are worth adding to Claude Code

The starter lists for this question have a problem: **most of what they
recommend, Claude Code already does.** It reads and writes files, runs shell
commands and drives git without any server at all. Adding a filesystem MCP
server to it duplicates a native capability and spends context doing it.

So the useful question is narrower: what can it *not* do, and is that gap worth
the context.

## What it already has

Files, shell, and anything reachable from a terminal. That last clause is
broader than it sounds - if a capability has a CLI, Claude Code can already use
it, and a server wrapping the same CLI adds a layer rather than a capability.

Before installing anything, the honest first question is whether the thing you
want has a command line. Very often it does, and you are done.

## What is genuinely missing

**A browser.** The clearest real gap: a terminal cannot render a page, run its
JavaScript or click anything. This is the category where a server adds
something a shell cannot reach, which is why browser servers are the most
installed. Which one depends on the job:
[choosing an MCP server for browser automation](best-mcp-server-for-browser-automation.md),
and if the job is debugging your own site rather than driving one,
[Playwright MCP vs Chrome DevTools MCP](playwright-mcp-vs-chrome-devtools-mcp.md).

**A structured view of a live system.** A database's schema and query results
arrive better through a typed tool than through parsing CLI output, and the
same goes for issue trackers with a real API.

**Something with no CLI at all.** Rarer than people assume, and the actual test
of whether a server is worth it.

## What each addition costs

Tool descriptions travel in the model's context on every turn, not once.
Measured on our own server's registry on 2026-09-13, with a tokenizer rather than a characters-per-token rule of thumb: **16 tools, 3,192 tokens resent every turn** (9,145 characters of description, plus the argument schemas that travel with them). Two servers of that
size on a long coding session is a meaningful slice of the window spent before
your question arrives, and it is worse than the tokens: overlapping verbs make
the model choose wrongly.
[How many MCP tools is too many](how-many-mcp-tools-is-too-many.md) has the
arithmetic.

There is also a ceiling you will not be told about. Clients cap how many tools
they offer at once, and crossing it silently drops some. If a tool you know
exists is being ignored, count your servers before debugging the server.

## A defensible default

- **One browser server.** Not two, ever - the overlap is total.
- **Your database, read-only**, if the assistant is working against real data.
- **Nothing else until something specific fails**, because the failure tells you
  which server you actually needed.

This project's own server is the browser row, and its config block for Claude
Code is in [the MCP server](mcp-server.md). It is one entry in one category
rather than a recommendation for the set.

## Short answers to the questions that lead here

**What are the best MCP servers for Claude Code?** Whichever cover a capability
a terminal cannot reach. A browser is the common real one; filesystem servers
usually duplicate what it already has.

**Do I need a filesystem MCP server with Claude Code?** No. It reads and writes
files natively.

**How many should I install?** As few as do the job. Every one costs context on
every turn and adds verbs to choose wrongly between.

**Are there free MCP servers for Claude Code?** Most are open source. The model
tokens are billed by your plan either way, and a long agentic session is
turn-heavy.

**Why is my MCP server not showing up in Claude Code?** Usually the config file
or the tool ceiling. Check the config block first, then count how many tools all
your servers expose together.

**See also:** [how to choose among MCP servers](best-mcp-servers.md),
[MCP on GitHub](mcp-servers-on-github.md) for judging one before installing it,
and [running AIHawk's browser from Claude Code](running-aihawk-with-claude-code.md).

## Sources

- [The Model Context Protocol documentation](https://modelcontextprotocol.io/docs/learn/server-concepts), retrieved 2026-09-11, for `tools/list` and the shape of a tool declaration.
- This project's own MCP server registry, enumerated on 2026-09-13, for the 16 tools and the 3,192 tokens measured above.

---

*Written while maintaining one of the browser servers this page says you should
install exactly one of. The first section argues that most starter
recommendations are unnecessary, which includes anyone recommending ours for a
job a terminal already does.*
