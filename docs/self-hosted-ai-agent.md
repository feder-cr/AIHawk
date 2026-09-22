---
title: "Self-hosted AI agent: what one actually costs to run"
description: "The RAM and disk numbers people quote for a self-hosted agent are the model's, not the agent's. Both bills measured on one laptop, kept apart."
parent: "Using the Agent"
nav_order: 45
---

# Self-hosted AI agent: what one actually costs to run

A self-hosted AI agent is an agent whose moving parts run on hardware you
control rather than a vendor's: the thing that acts, and optionally the model
that decides what to do. **Those are two separate bills, and almost every guide
quotes only one of them.** Hosting
the agent, meaning the thing that opens a browser and acts on a page, cost
**613 MB of disk and about 900 MB of resident memory** on the machine measured
below, and the browser was on a page five seconds after a cold start. Hosting
the *model* is the separate bill, the one behind every "16 GB minimum" you have
read, and you only pay it if you decide to.

Keeping them apart is the whole point. If your editor or chat client already has
a model, the agent you add to it is a few hundred megabytes, not a workstation.

## The two bills nobody separates

Read any current self-hosting walkthrough and the stack is the same shape:
a container runner, a workflow tool, and a local model server. The
[n8n and Pinggy walkthrough](https://dev.to/lightningdev123/building-self-hosted-ai-agents-with-n8n-and-pinggy-a-developers-journey-3n4c)
and the
[Docker plus n8n plus LM Studio stack](https://aiagentssimplified.substack.com/p/build-a-local-ai-automation-stack)
are both built that way. So the hardware floors that circulate are the floors of
the **model**, and they scale with the weights rather than with the agent. The
[Argo](https://github.com/xark-argo/argo) project, which bundles a local model
server, states a minimum of "CPU >= 4 cores" and "RAM >= 8 GB". A practitioner
blueprint for running agents offline puts
[70B models at 64 GB of unified memory](https://dev.to/adithyasrivatsa/local-ai-agents-that-run-your-life-offline-the-self-hosted-micro-empire-blueprint-18c2)
and notes that the same model quantized to 4 bits still "eats 24 GB VRAM".

None of those numbers describes the agent. They describe inference. An agent
that gets its thinking from a client you already run, over the Model Context
Protocol, never pays them.
[AI browser agent with a local LLM](ai-browser-agent-local-llm.md) is the page
for the case where you do want to pay that second bill on purpose.

## What the agent itself installs

Measured on 2026-09-17, Windows 11, a clean virtual environment created with
`uv` and nothing warmed up except the engine cache:

| | |
|---|---|
| Python packages resolved and installed | **50** |
| Time for that install | **8 seconds** |
| Disk, the virtual environment | **65.7 MB** |
| Browser archive downloaded | **240.4 MB** (Windows), 262.0 MB (Linux x86_64), 253.4 MB (Linux arm64) |
| Browser unpacked on disk | **547.6 MB**, 180 files |
| **First-run total** | **613.3 MB** |

The download figures are the ones declared in the release the package is pinned
to, so they are what your connection actually moves; the 547.6 MB is what the
directory weighs afterwards, which is the number that matters for a small disk.
The split is worth noticing: the Python side is under a tenth of the total. A
self-hosted browser agent is, on disk, almost entirely a browser.

## What it costs while it runs

Five cold starts in a row, headless, each one opening a page served from
`127.0.0.1` so that no part of the number is somebody else's site being slow:

| | median | range |
|---|---|---|
| Browser up and ready | **5.28 s** | 4.73 to 6.18 |
| Up and first page rendered | **5.50 s** | 4.97 to 6.52 |
| Resident memory, whole process tree | **902 MB** | 879 to 911 |
| Processes | 9 | 9 to 10 |

The breakdown of that memory is the useful part, because it says where a limit
would bite. The Python process holding the session was **56 MB** with the
browser open, 46 MB before it. Everything else, **842 MB across 8 processes**,
was the browser: a 321 MB parent, a 285 MB content process, then five smaller
ones. Firefox is multiprocess, so a measurement that reads only the parent
reports about a third of the truth.

**What that buys you in practice: a 1 GB VPS will not hold this, and a 2 GB one
will**, with the caveat that the figure above is one blank local page. Real
pages with real JavaScript push content-process memory up, and the ceiling you
plan for should be the heaviest page you intend to drive, not this one.

## What leaves the machine

Three things, and only three, which is a shorter list than "self-hosted"
usually implies.

**The pages you ask for.** The browser fetches what you point it at, from your
address. That is the traffic you were expecting.

**A five-byte launch counter.** On startup the engine fetches one tiny release
asset, and the asset's download count is how many times the engine has been
started. There is no payload, no identifier and no second request. It is
declared as a preference rather than compiled in, which means you can turn it
off: pass `invisible_firefox.usage_ping.enabled` as `False` in the extra
preferences your session is built with. Verified while writing this page, the
value arrives in the composed preference set as a boolean.

**The model call, if there is one.** This is the fork that decides everything
else. Driven as an MCP server from a client such as an editor or a desktop
assistant, the agent makes **no model call at all**: the client's model does the
thinking and the server only moves the browser. That is checkable in one
command, and it was checked for this page: with every model key removed from the
environment, `python -m invisible_playwright_mcp` still completes the protocol handshake and
advertises its tools, because nothing in that path needs a model.
[The MCP server page](mcp-server.md) has the config block each client takes.

Driven instead through the bundled interface, `invisible-playwright-mcp ui`, there is one outbound
dependency, OpenRouter. The same key-free environment makes that command exit
with `no OpenRouter key`, which is the behaviour you want: it refuses rather
than quietly doing less.

## The part you cannot self-host, and the one you can

You can self-host the browser completely. The engine is a file on your disk, the
profile is a directory, and nothing about driving a page needs a third party.

You cannot self-host somebody else's model. If your agent's intelligence comes
from a hosted API, then the sentence "self-hosted agent" describes the hands and
not the head, and the page contents your agent reads are being sent to whoever
serves that model. That is not a hidden cost so much as an unstated one, and it
is the honest reason to care about the distinction: it is a data-flow question
before it is a bill.

The way to close it is to move the model, not the browser, and the price of
closing it is bill number two above.
[What is actually free in the agent stack](what-is-free-in-the-agent-stack.md)
walks the same layers with the money rather than the megabytes.

## What grows after the first run

The engine cache does not prune itself. Every time the pinned engine moves, the
new tree is unpacked beside the old one and the old one stays. On the machine
used for this page, which has taken every build since June, the cache held
**15 engine trees totalling 8.0 GB** for one agent that only ever uses the
current one.

Nothing is wrong when this happens, and the tooling agrees: `python -m
invisible_core doctor` lists every cached tree, marks the ones that are not the
sealed engine, and still finishes with `verdict : OK`, because a stale engine on
disk is not a fault. It is just disk. Run that command when a drive fills up,
and clear the trees you no longer need.

This is the one line of the self-hosting bill that arrives later than you
expect, which is why it is worth knowing before it does rather than after.

## Isolation, the thing practitioners actually worry about

Read what people building in this space are shipping and the recurring theme is
not cost, it is containment: a
[self-hosted isolated browser sandbox with a human able to step in over VNC](https://news.ycombinator.com/item?id=47353827),
a
[self-hosted MCP browser with isolated profiles and human-approved remote browsing](https://github.com/BK927/cloud-browser-mcp),
a
[thread specifically about sandboxing browser agents](https://news.ycombinator.com/item?id=45216460).

The concern is sound and it is not a hosting concern, it is a credentials
concern: an agent driving a browser you are logged into can do anything you can
do in that browser.
[Should you log your AI agent into your accounts](should-you-log-your-ai-agent-into-accounts.md)
is the page that takes that question seriously, including the cases where the
answer is no. Self-hosting changes who holds the session; it does not change
what the session permits.

## Short answers to the questions that lead here

**What is a self-hosted AI agent?** An agent whose moving parts run on hardware
you control. In practice that splits into the actor, meaning the browser or
tool-runner, and the model. Most guides bundle them; they cost very different
amounts and only one of them is optional.

**How much RAM does a self-hosted AI agent need?** For the agent alone, about
1 GB: measured here at 902 MB resident across the whole process tree, with the
browser accounting for 842 MB of it. If you also run the model locally, that
figure is dwarfed by the model's and you should size for the model.

**How do I build a self-hosted AI agent?** Decide the model question first,
because it sets the machine. If the model stays with your client, you are
installing a browser and a small Python package and wiring an MCP config. If the
model comes home too, you are building the stack the walkthroughs describe, and
their hardware floors apply.

**Does it need Docker?** Not for this one. It installs as a Python package and
unpacks a browser into a cache directory. Docker is common in these stacks
because a local model server and a workflow tool are easier to compose that way,
which is again the model's half of the bill and not the agent's.

**Is a self-hosted agent private?** Only as far as its model. The browser traffic
is yours and the one telemetry call is five bytes you can switch off, but a
hosted model sees the page content you feed it. That is the question to ask of
any product using the phrase.

**See also:**
[cloud browser infrastructure for AI agents](cloud-browser-infrastructure-for-ai-agents.md),
which is the same decision taken the other way and names the vendors in that
layer, and
[open-source agentic browsers](agentic-browser-open-source.md), which separates
what is open at each of the three layers.

## Sources

- All measurements taken 2026-09-17 on one Windows 11 machine: a clean `uv` virtual environment (50 packages, 65.7 MB), the sealed engine tree (547.6 MB, 180 files), five cold headless starts against a page served from `127.0.0.1`, and process memory read per process across the tree rather than from the parent alone.
- Archive sizes as declared by the pinned engine release: 240.4 MB Windows, 262.0 MB Linux x86_64, 253.4 MB Linux arm64.
- Model-side hardware floors, quoted from the pages themselves rather than from search results: [Argo's minimum requirements](https://github.com/xark-argo/argo) and the [local-agent blueprint](https://dev.to/adithyasrivatsa/local-ai-agents-that-run-your-life-offline-the-self-hosted-micro-empire-blueprint-18c2), both retrieved 2026-09-17. A widely repeated set of per-precision GPU figures for an 8B model was dropped from this page because the system card it is attributed to could not be retrieved to confirm it.
- Practitioner discourse on isolation: [Verge Browser](https://news.ycombinator.com/item?id=47353827), [cloud-browser-mcp](https://github.com/BK927/cloud-browser-mcp) and [Sandboxing Browser AI Agents](https://news.ycombinator.com/item?id=45216460), retrieved 2026-09-17.

---

*Written by the maintainer of the agent being measured, so treat the numbers as
a disclosed interest and the method as the part to copy: the install was clean,
the page was local, the runs were repeated, and the memory was read across the
whole process tree. Measure yours the same way and the comparison means
something.*
