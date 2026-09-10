---
title: "Getting an AI agent to log into a website: three routes"
description: "Reuse a saved session, persist a profile, or type the password, which is the worst. What two-factor does, and the failures that start after you log in."
parent: "Using the Agent"
nav_order: 39
---

# Getting an AI agent to log into a website

There are three ways an agent ends up logged in, and the one people try first is
the worst of them. This page is the mechanics. Whether you should do it at all
is a different question with its own page:
[should you log your agent into accounts](should-you-log-your-ai-agent-into-accounts.md).

## The three routes

**Reuse a saved session.** You log in yourself, in a real browser, once. The
cookies and local storage are saved to a file. The agent starts from that state
and is already logged in. Nothing secret ever reaches the model, the flow has no
login step to get wrong, and any interactive check happened while a person was
present. This is the right answer for most cases and it is the one people skip.

Microsoft's server takes `--storage-state` for exactly this shape. This project
takes a persistent `profile_dir` per session.

**Persist a profile.** The agent has its own browser directory that survives
between runs. First run logs in, later runs do not. Cheaper to set up than a
storage state, and it accumulates history, which incidentally makes the browser
look less brand new. The cost is a lock: one live browser per directory, which
is how people meet
[browser is already in use](playwright-mcp-browser-already-in-use.md).

**Type the credentials.** The agent fills the form. This works and it is the
last resort, because the password is in the conversation, which means it is in
the model provider's request log, in your transcript, and in whatever you paste
that transcript into. It also fails on anything interactive.

## What two-factor does

It ends the fully unattended version of this, and that is the correct outcome
rather than an obstacle to route around.

- **Time-based codes.** An agent can be given a shared secret and generate them.
  That converts your second factor into a first factor stored next to the
  password, which is worth saying out loud before doing it.
- **Push or SMS.** A person has to approve. That is the design.
- **Passkeys.** Bound to a device and a browser profile. An agent in a fresh
  profile has nothing to present.

The workable pattern for anything with a second factor is the first route: a
person logs in, once, and the agent inherits the session until it expires. If
the session expires daily, this task is not a good candidate for automation and
that is useful information.

## After you are logged in, the failures change

**Sessions expire mid-run.** The agent is three steps into a flow and the next
page is a login form. Without a check for that, it will try to interact with the
form as though it were the page it expected, and the run's output is garbage
rather than an error. Test for "am I still logged in" between steps, not once at
the start.

**A logged-in agent can do damage.** Ordinary browsing is read-only; a
logged-in session is not. Delete buttons, send buttons, purchase buttons, all
reachable by the same click tool. Scope what the agent is asked to do, and
prefer an account with the least privilege that completes the task.

**Prompt injection matters now.** Text on a page arrives in the same channel as
your instruction. While logged out this produces a wrong answer; while logged in
it can produce an action taken with your credentials. This is the reason the
consumer agentic browsers are the subject of security advisories:
[what is an agentic browser](what-is-an-agentic-browser.md) has the wider
picture.

**The site may treat the session differently.** A logged-in account has a
history and is often challenged less. It is also attributable, and rate limits
per account are usually tighter than per address.

## Practical setup

- Log in by hand, in a headed browser, and save the state. Do the interactive
  parts while a person is there.
- Give the agent that state, not the password.
- Use a dedicated account where the site allows it, with the minimum
  permissions.
- Check the session is still alive between steps.
- Keep the state file out of your repository. It is a credential.

## Short answers to the questions that lead here

**Can an AI agent log into a website?** Yes, and it should usually inherit a
session a person created rather than performing the login.

**Is it safe to give an agent my password?** It goes into the conversation and
therefore into logs. Use a saved session instead.

**Can an agent handle two-factor?** Only time-based codes, and only by holding
the secret, which defeats the point of the second factor. Push and passkeys need
a person.

**Why does my agent get logged out?** Session expiry, a fresh profile every run,
or `--isolated`, which throws the profile away by design.

**Does logging in make blocking worse or better?** Usually better on the
challenge side, and worse on rate limits, because the limit is now attached to
your account.

**See also:** [should you log your agent into accounts](should-you-log-your-ai-agent-into-accounts.md),
[Playwright MCP best practices](playwright-mcp-best-practices.md), and
[writing tasks for a browser agent](writing-tasks-for-an-ai-browser-agent.md).

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10, for `--storage-state`, `--user-data-dir` and `--isolated`.
- [Same-Origin Policy for Agentic Browsers](https://arxiv.org/pdf/2606.14027), retrieved 2026-09-10, for the injection-with-authority problem.

---

*Written by a project whose server can hold a persistent profile. The page still
recommends the route where the password never reaches the agent, because that is
the one that fails least badly when something goes wrong.*
