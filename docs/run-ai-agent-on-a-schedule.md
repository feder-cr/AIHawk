---
title: "Run an AI browser agent on a schedule"
description: "Why AIHawk's chat interface has no headless mode, the two ways to run a browser agent unattended, what a recurring run costs, and when a script beats an agent."
parent: "Using the Agent"
nav_order: 24
---


# Run an AI browser agent on a schedule

AIHawk's own interface has no headless mode: since 0.3.0 it is `aihawk ui`, a chat
window for a person watching, not a cron target. A scheduled run means one of two
routes instead: a non-interactive assistant command that still spends tokens, or the
invisible_playwright library driving fixed steps with no model at all.

## Why the interactive UI is the wrong shape for a cron job

`aihawk ui` serves a small local web app, chat on the left, a live browser pane on
the right, and it refuses to start without an OpenRouter key. That's a reasonable
design for a person typing an instruction and watching the pointer move, and the
wrong shape for a job starting at three in the morning with nobody at the keyboard.

There is nothing to point cron at either: AIHawk's CLI defines exactly one
subcommand, `ui`, running a server that only stops on Ctrl-C or a kill signal. No
`--once` flag, no run-and-exit mode. Putting the interface in cron either leaves that
server running unattended forever, key included, or means wrapping a tool that was
never built to be driven from outside its own chat box.

## Two ways to actually run something unattended

**An assistant's own non-interactive mode.** If you have already wired an assistant
to this browser over MCP, the same one-line attachment
[Claude Code uses](running-aihawk-with-claude-code.md), most such CLIs offer a way to
run one prompt and exit instead of opening a chat window. Cron calls that entry
point; the assistant calls the same browser tools it always does, and the process
ends when the task is done. Claude Code, for one, says it plainly in its own help
output: it "starts an interactive session by default, use -p/--print for
non-interactive output", which is the flag a crontab line wants. Check your own
assistant's help before writing the line, because the flag differs per tool. This
route still spends model
tokens every tick, because a model is still doing the deciding.

**The invisible_playwright library, with no model in the loop.** When the steps
between runs never change, same URL, same element, same field to read, write them
once against the library the engine ships as, instead of paying a model to redo the
same actions every time. The engine wiki has a page for exactly this route:
[scheduling invisible_playwright scrapes with cron](https://github.com/feder-cr/invisible_playwright/wiki/schedule-invisible-playwright-scrapes-with-cron).

```python
from invisible_playwright import InvisiblePlaywright

with InvisiblePlaywright(seed=11, profile_dir="/home/you/agent-runs/profile") as browser:
    page = browser.new_page()
    page.goto("https://example.com/status", wait_until="domcontentloaded")
    print(page.locator("#status").inner_text())
```

`seed` pins the browser's identity so a recurring check keeps looking like the same
returning visitor; `profile_dir` keeps cookies and any login across runs. No key, no
model, nothing to bill.

## What a scheduled run actually costs

Every tick through an assistant's model spends money whether or not a person reads
the answer. A job you forget about does not forget to charge you. The worked,
illustrative example on [which model to use](which-model-to-use-with-aihawk.md) puts
one 20-turn task at about $0.19 on the default model and about $0.96 on a frontier
one. A schedule multiplies that by frequency: every five minutes is 288 runs a day,
roughly $55 on the cheap end and $276 on the frontier one, for a job that may only
need to run once a morning.

The script route has no such multiplier. A launch of the library, a page load, a
short read, and it exits: seconds of wall clock and no model spend at all, the same
economics the
[page-monitoring guide](how-to-monitor-a-page-with-an-ai-agent.md) builds its whole
argument on. Frequency is nearly free on that side and a real bill on the other, which
is most of the decision right there.

## When nobody is watching and the agent gets stuck

In the interactive interface, a person watching the live pane notices a wrong click
and nudges the next instruction. On a schedule nobody is looking, so the real
question is not how to keep the run going, it is how loud the failure is when it
happens. One bound already exists: AIHawk's loop caps an instruction at 25 model
turns and stops with a plain error instead of looping forever.

What it can do instead is fail quietly. A cron job's non-zero exit code is one line
among hundreds unless something forwards it somewhere you check, and "stopped on turn
14 with an unreadable page" in a log file looks like success until you go looking for
an unrelated reason. When a run that worked for weeks starts failing, replay the
failing step against the library with no model attached: the same diagnosis
[browser problem or model problem?](browser-problem-or-model-problem.md) describes,
and it costs nothing because no model was ever involved.

## Where the output has to land

Cron's old habit of mailing stdout to a local user depends on a mail setup most
machines do not have configured, so anything a scheduled run prints without an
explicit destination just disappears. Redirect it somewhere dated instead:

```
17 6 * * *  /home/you/agent-runs/run_check.sh >> /home/you/agent-runs/$(date +\%F).log 2>&1
```

A file nobody opens is the same as no file. Point the log at whatever you already
read, a channel you already watch, a digest you already open, rather than inventing
one more place to check that quietly becomes one more tab nobody visits.

## The rule: match the tool to whether the task's shape ever changes

If every run does the identical thing, same URL, same element, same read, the model
is not deciding anything new tick to tick, and paying it every time buys nothing over
writing those steps once as a script. If the run genuinely needs judgment, does this
number mean something changed, is this the exception worth a look, the model earns
its place. But ask whether that judgment is needed on every tick, or only when a
cheap mechanical check flags something first: the two-stage pattern the
[monitoring guide](how-to-monitor-a-page-with-an-ai-agent.md) argues for is the
general shape this whole page has been describing, not a special case of it.

## Short answers to the questions that lead here

**Can I run AIHawk's own interface on a schedule?** Not as it ships: since 0.3.0 the
only subcommand is `ui`, a persistent chat server with no one-shot or headless mode.

**What's cheaper for a scheduled task, an agent or a script?** A script, whenever the
steps never change: the library run costs no model tokens at all. An agent earns its
cost only when each run needs a fresh judgment call.

**Does a scheduled agent run forever if something goes wrong?** No: one instruction
stops at 25 model turns with a plain error. The real risk on a schedule is a stopped
run nobody reads, not runaway spend.

**How do I know if a failing scheduled run is the site or the model?** Replay the
failing step with no model against the library: reproduces, browser side; works by
hand, the model was the variable.

**Where should a scheduled agent's output go?** A dated file, redirected explicitly,
read by a human on some cadence, somewhere you already look rather than a new place
invented just for this.

**See also:** [running the agent on a local model](ai-browser-agent-local-llm.md) if the token bill is what pushed you here, [Monitoring a page for changes with an AI agent](how-to-monitor-a-page-with-an-ai-agent.md),
[Browser problem or model problem?](browser-problem-or-model-problem.md), and
[Which model to use with AIHawk](which-model-to-use-with-aihawk.md).

## Sources

Retrieved 2026-09-05.

- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), this repo's README and
  `src/aihawk/cli.py`: the `ui` subcommand, its OpenRouter-key requirement, its
  run-until-interrupted server loop, and the `invisible-playwright fetch`
  prefetch command.

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. Built for a person
watching a live pane, this interface is the opposite of a cron job; the two routes
here fill that gap.*
