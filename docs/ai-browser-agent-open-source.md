---
title: "Open-source AI browser agents"
description: "The open-source agents that drive a real browser - browser-use, agent-browser, Skyvern, Stagehand, Nanobrowser, BrowserOS, AIHawk - compared by license, engine and how each reads a page."
parent: "Alternatives and Comparisons"
nav_order: 7
---


# Open-source AI browser agents

An AI browser agent is a language model wired to a real browser: you state a goal in
plain language, the model looks at the page, decides an action, the browser performs
it, and the loop repeats until the goal is done or the model gives up. This page maps
the open-source projects that actually do that today, with one disclosure before
anything else: AIHawk is one of the entries and this is AIHawk's wiki, so read the
comparison knowing who wrote it. Every claim about the other projects below was read
from that project's own repository on 2026-09-03, star counts included. Stars drift
daily; treat them as order-of-magnitude, not scoreboard.

If you are new to the category itself, start with
[what an AI web agent is](ai-web-agent-explained.md) and come back. And if what you
picture is an agent looking at raw pixels and clicking screen coordinates, that is a
different category with different trade-offs, covered in
[open-source computer-use agents](computer-use-agent-open-source.md).

## What qualifies for this page

Three tests, applied to every entry:

1. **Open source in the useful sense.** A license and a repository you can run
   yourself, not a waitlist with a GitHub page in front of it.
2. **A real browser.** The agent drives an actual browser engine that executes
   JavaScript and renders pages, not an HTTP client with a model attached.
3. **The model decides.** An LLM chooses the next action from what is on the page,
   rather than replaying a recorded script.

Several entries also sell a hosted cloud on top of the open code. That is noted where
it changes what the open part actually contains.

## The projects

### browser-use

The largest project in the category by a wide margin: 112.1k stars, Python, MIT
licensed. It drives a browser through Playwright and gives the model both views of a
page at once, a structured DOM representation plus screenshots. It supports many
model providers, including its own trained models, the major APIs, and local models
through Ollama. The company behind it also runs a paid hosted cloud; the library is
the open part, and it is the default answer to "which one do most people use". If you
are evaluating it against alternatives, there is a dedicated page for that:
[browser-use alternatives](browser-use-alternatives.md).

### agent-browser

41.9k stars, Rust, Apache-2.0, from Vercel's labs organization. It is a CLI rather
than a framework: a native binary with a background daemon, built to be called by a
coding agent you already run (Claude Code, Cursor and similar), which is where the
model in the loop comes from. It downloads Chrome for Testing locally and drives it
over CDP, and it addresses elements through deterministic "refs" instead of
screenshots, which keeps token cost down. Cloud browsers are pluggable rather than
bundled: a provider flag can point the same commands at hosted vendors including
Browserless, Browserbase, Browser Use and Kernel. The star count deserves one honest
caveat: the repository dates to January 2026, so those 41.9k stars accrued in about
eight months on the strength of the Vercel name; treat them as attention, not yet as
miles.

### Stagehand

24.1k stars, TypeScript with Python and Go interfaces, MIT licensed, maintained by
Browserbase. Stagehand is not a finished agent you hand a task to; it is an SDK for
building browser agents, with Playwright-style methods and self-healing actions. Its
own framing is the useful one: "Playwright was built for testing, Stagehand is built
for agents". Pick it when you are writing the agent yourself and want the
acting-on-a-page layer solved.

### Skyvern

22.9k stars, Python. It combines Playwright with vision language models to interact
with pages, aimed at repeatable browser workflows, self-hosted via pip or Docker or
through its managed cloud. The license detail is worth knowing before you commit:
AGPL-3.0, and the README states that its anti-bot measures are an exception,
available in the managed cloud offering rather than in the open code.

### Nanobrowser

13.7k stars, TypeScript, Apache-2.0. Structurally different from everything above:
it is a Chrome extension, so it drives the browser you already run (Chrome and Edge
are supported; Firefox and Safari are not). Inside it runs a multi-agent design, a
planner and a navigator cooperating on a task. It positions itself as a free,
local-privacy alternative to OpenAI Operator, with your own API keys and a long list
of supported providers including Ollama for local models.

### BrowserOS

13.5k stars, AGPL-3.0. Here the browser itself is the project: a Chromium fork with
agent capabilities built in, shipping both a daily-driver browser with an embedded
agent and a secondary browser that external agents control. Agents connect over the
Model Context Protocol, and local models are supported through Ollama and LM Studio.
Choose it when you want the agent living inside the browser as a product, not a
library in your code.

### AIHawk

30.3k stars, Python, MIT. This one is ours, so the disclosure from the top of the
page applies to this paragraph most of all. AIHawk started as a job-application bot,
which is where the star count and the TechCrunch, Business Insider and Wired coverage
came from, and it is now a general web agent. There are two ways in: add its MCP
server (`invisible-playwright-mcp`) to an assistant that can run tools, such as
Claude Code, Claude Desktop or Cursor, where the assistant brings the model, or run
`aihawk ui` with an OpenRouter key and get a chat interface with a live browser
view (the key is required; model-free browser driving is the underlying
library's job).

The structural difference from every other entry is the browser. Everything above
drives Chromium, Chrome or a fork of them; AIHawk drives a Firefox patched at the
C++ level, the invisible_playwright engine, built so that what fingerprinting scripts
read from it is internally consistent. That matters on pages that push back, and the
honest boundary matters just as much: the engine addresses the browser fingerprint
layer, and it does not fix a bad exit IP, a rate limit, or robotic pacing. Those
layers are yours regardless of the agent you pick; the breakdown is in
[why agents get blocked](why-does-my-ai-agent-get-blocked.md). Platform limits are
real too: Python 3.11+, Windows and Linux, no macOS support.

One near miss before the table, for completeness: Notte (~2k stars) pairs an agent
framework with its own hosted browser infrastructure, but it is licensed SSPL-1.0,
which the OSI has not approved as open source, so it fails this page's first test
rather than its second or third.

## The differences that decide the choice

| Project | Stars (2026-09-03) | Language | License | Browser it drives | How it reads a page |
|---|---|---|---|---|---|
| browser-use | 112.1k | Python | MIT | Playwright-driven browser | DOM plus screenshots |
| agent-browser | 41.9k | Rust | Apache-2.0 | local Chrome for Testing via CDP, pluggable cloud browsers | CLI commands, deterministic element refs |
| Stagehand | 24.1k | TypeScript, Python, Go | MIT | Playwright-compatible runtime | structured actions, DOM-first |
| Skyvern | 22.9k | Python | AGPL-3.0 (anti-bot parts cloud-only) | Playwright | vision LLM plus page structure |
| Nanobrowser | 13.7k | TypeScript | Apache-2.0 | your own Chrome or Edge | in-page, multi-agent |
| BrowserOS | 13.5k | TypeScript, C++ | AGPL-3.0 | its own Chromium fork | agent embedded, MCP tools |
| AIHawk | 30.3k | Python | MIT | patched Firefox (invisible_playwright) | structured snapshots plus screenshots over MCP |

A few honest cuts through the table:

- **Most people, most tasks:** browser-use. Largest community, most examples, and
  model quality usually matters more than framework choice for ordinary tasks.
- **You are writing your own agent:** Stagehand, and it is one of two entries here
  that are honest about being a building block rather than a product.
- **Your agent is a coding assistant in a terminal:** agent-browser, the other
  building block, a CLI shaped for exactly that loop on a stock Chrome.
- **Zero infrastructure, your own browser:** Nanobrowser. An extension is also the
  easiest thing on this page to try and to remove.
- **The browser as the product:** BrowserOS.
- **Repeatable workflows with a vision-first reading of the page:** Skyvern, with
  the AGPL and the cloud-only anti-bot carve-out weighed first.
- **Pages that resist automation, or plugging a browser into Claude Code:** AIHawk,
  from the people telling you so, with the layer boundaries stated above.

## Short answers to the questions that lead here

**Which open-source browser agent is the biggest?** browser-use, at 112.1k stars as
of 2026-09-03, roughly four times the next entry. Stars measure attention, not fit,
but attention buys examples and answered issues.

**Are these actually free?** The code is. The model tokens are not: every entry needs
an LLM, and on hosted APIs that is a per-task cost. Several projects also sell hosted
clouds; the open repositories are what this page compared.

**Which ones run with local models?** browser-use, Nanobrowser and BrowserOS all
document local-model support through Ollama (BrowserOS also LM Studio). Expect a
capability drop against frontier hosted models on long multi-step tasks.

**What is the difference from a computer-use agent?** A browser agent reads page
structure and acts on elements; a computer-use agent looks at screen pixels and
clicks coordinates, so it can drive anything on screen at a cost in precision and
tokens. The category comparison is on
[the computer-use page](computer-use-agent-open-source.md).

**Do open-source agents get blocked more than commercial ones?** Blocking does not
check your license. It checks the browser fingerprint, the exit IP, the request
volume and the pacing, and most agents on this page inherit a stock automation
fingerprint. The layer-by-layer breakdown is in
[why agents get blocked](why-does-my-ai-agent-get-blocked.md).

**Which one should I use with Claude Code?** AIHawk's MCP server is built for exactly
that, one `claude mcp add` command, and this is its wiki saying so, which is why the
sentence carries a disclosure instead of a superlative.

## Sources

All retrieved 2026-09-03. Star counts and claims were read from each project's own
repository page on that date.

- [browser-use/browser-use](https://github.com/browser-use/browser-use)
- [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser)
- [browserbase/stagehand](https://github.com/browserbase/stagehand)
- [Skyvern-AI/skyvern](https://github.com/Skyvern-AI/skyvern)
- [nanobrowser/nanobrowser](https://github.com/nanobrowser/nanobrowser)
- [browseros-ai/BrowserOS](https://github.com/browseros-ai/BrowserOS)
- [nottelabs/notte](https://github.com/nottelabs/notte), for the near-miss note.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its README in this
  repository.

**See also:** [open-source computer-use agents](computer-use-agent-open-source.md),
[what is an AI web agent?](ai-web-agent-explained.md),
[choosing an AI browser agent](best-ai-browser-agent.md),
[browser-use alternatives](browser-use-alternatives.md), and - if you landed
here from Operator's shutdown -
[open-source Operator-style agents](openai-operator-open-source.md), which
frames the overlapping repos by what Operator specifically did.

---

*This page is part of the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. AIHawk
is the entry above with the patched Firefox underneath; the other five projects were
described from their own repositories, and where one of them fits your case better,
the table says so.*
