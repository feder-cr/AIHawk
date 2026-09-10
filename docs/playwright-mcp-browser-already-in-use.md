---
title: "Playwright MCP: browser is already in use, and the fix"
description: "The error means a profile directory is locked, not that a browser is running. The four ways a lock survives, and how to tell stale from a real client."
parent: "Using the Agent"
nav_order: 32
---

# Playwright MCP: browser is already in use

The message reads roughly:

```text
Browser is already in use for /path/to/mcp-chrome, use --isolated to run
multiple instances of the same browser
```

**It is a lock on a profile directory, not a statement about a running
browser.** A persistent profile can only be opened by one browser instance at a
time, and Playwright MCP defaults to a single fixed profile directory. Anything
that took that lock and did not give it back produces this, including a process
that is no longer alive.

Microsoft's own documentation states the constraint directly: a persistent
profile can only be used by one browser instance at a time, so concurrent MCP
clients sharing the same workspace will conflict.

## The four ways you get here

**A second client.** You have the server registered in two places - your editor
and a terminal assistant, say - and both are alive. Both want the same profile.
This is the case the error is actually written for, and it is most common in an
editor: [a browser MCP server in GitHub Copilot](playwright-mcp-in-github-copilot.md)
covers why.

**A previous run that was killed.** The session ended by something other than a
clean close, so the lock file outlived the process. Nothing is running and the
error still fires. This is the most common one and the most confusing, because
your process list is empty.

**A close that did not reset the server's own state.** Reported repeatedly
against the upstream server: after `browser_close`, the internal "in use" flag
is not always cleared, so the next navigate fails with the same message even
though the browser is gone. Restarting the MCP server clears it.

**An install that half-started a browser.** `browser_install` can leave an
instance that holds the profile without being usable, which leaves the server's
idea of the state and the actual state disagreeing.

## Fixing it

**If you want concurrent clients, use `--isolated`.** The profile lives in
memory for the session and nothing is shared, so two clients stop fighting. The
cost is that you start logged out every time, which for exploration is usually
what you wanted anyway.

**If you want the profile, give each client its own.** Choosing this
deliberately rather than by accident is the second of the four decisions in
[Playwright MCP best practices](playwright-mcp-best-practices.md).
`--user-data-dir <path>` with a different path per client. You keep persistence and lose the collision.
Note that this is a command-line option on the server, so if your client only
lets you register a command with no arguments, you may not be able to reach it
without editing the config block by hand.

**If nothing is running, restart the server.** In an editor or a chat client
that means reloading the MCP connection, not just closing the tab. That clears
the in-memory flag from the third case above; if the message persists after a
genuine restart, the lock is on disk and the profile directory is the thing to
look at.

**Before deleting anything, check whether a browser really is alive.** A stale
lock and a live second client look identical in the error text and need opposite
fixes. Deleting a lock that a running browser holds corrupts the profile.

## Why this does not happen the same way here

[AIHawk](https://github.com/feder-cr/AIHawk)'s server is built around named
sessions and named browsers rather than one implicit profile: `session_start`,
`browser_open`, `browser_focus`, `session_list`. Two concurrent things are two
named things, and asking for a browser that is already open focuses it instead
of colliding with it. That is a design difference, not a claim of superiority
over Playwright MCP, and it comes with its own cost: you have to name things.

Where the same class of problem does reach us is persistent profiles, because
the constraint is the browser's, not the server's - the same reason a
[logged-in session has to be handled deliberately](ai-agent-login-to-a-website.md). One directory, one live
browser. If you point two sessions at the same `profile_dir`, the second one has
the same bad day.

## Short answers to the questions that lead here

**Why does it say the browser is in use when nothing is running?** Because the
lock is on the profile directory and can survive the process that took it, and
because the server keeps its own flag that a hard kill does not clear.

**Does `--isolated` lose my logins?** Yes. That is what isolated means. Use
`--storage-state` if you need a specific logged-in state without a shared
profile.

**Can I run two MCP browser clients at once?** Yes, with `--isolated` or with a
distinct `--user-data-dir` per client. Not on one shared persistent profile.

**Is this a bug?** Partly. The profile lock is a browser constraint and correct.
The flag not resetting after a close is tracked upstream as a defect.

**See also:** [Playwright MCP best practices](playwright-mcp-best-practices.md)
for the settings worth choosing on purpose,
[Playwright MCP vs the CLI](playwright-mcp-vs-cli.md), and
[the MCP server](mcp-server.md) for this project's session model.

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10, for `--isolated`, `--user-data-dir`, `--storage-state` and the documented one-instance-per-profile constraint.
- Upstream issues describing the failure modes above, retrieved 2026-09-10: [#942](https://github.com/microsoft/playwright-mcp/issues/942) (fails on first attempt), [#891](https://github.com/microsoft/playwright-mcp/issues/891) (lock on the fixed profile), [#1245](https://github.com/microsoft/playwright-mcp/issues/1245) (state not released after close), [#1294](https://github.com/microsoft/playwright-mcp/issues/1294) and [#1305](https://github.com/microsoft/playwright-mcp/issues/1305).

---

*Written while maintaining a competing MCP browser server. The section about our
own design says what it costs, and the last paragraph of it says where we have
the same problem.*
