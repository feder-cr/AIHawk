---
title: "Open-source Operator-style agents"
description: "The open-source agents that do what Operator did, repo by repo: browser-use, Skyvern, Agent S3, invisible_playwright_mcp, and the two unrelated projects both called open-operator, with stars and activity as found."
parent: "Alternatives and Comparisons"
nav_order: 2
---

# Open-source Operator-style agents

Operator is gone, but the thing it demonstrated - tell an AI what you want,
watch it drive a browser until it is done - is now better represented in open
source than it ever was as a hosted preview. This page goes through the open
repositories one by one: what each actually is, its license, and its scale as
read from GitHub on 2026-09-03. The hosted-versus-open landscape, and what
happened to Operator itself, are on
[OpenAI Operator alternatives](openai-operator-alternatives.md) and
[Is OpenAI Operator still available?](is-openai-operator-still-available.md);
this page does not repeat them.

Disclosure first: this wiki belongs to invisible_playwright_mcp, one of the projects below. Star
counts and descriptions were read from each repository this session, and the
projects that are bigger, older, or broader than ours are described as exactly
that.

## What "Operator-style" means here

An Operator-style agent takes a goal in natural language, drives a real
browser or desktop, looks at what came back, and decides the next action
itself. That excludes plain automation frameworks (you write the steps) and
excludes chat assistants that only summarize pages. Every entry below clears
that bar or is included to clear up a naming collision.

## The repositories

### browser-use - the biggest, by far

[github.com/browser-use/browser-use](https://github.com/browser-use/browser-use).
Roughly 112k stars, MIT license, and the description reads "Make websites
accessible for AI agents. Automate tasks online with ease." It drives a
Chromium-family browser, supports OpenAI, Google and Anthropic models with
your own keys plus its own optimized models through a unified key, and has an
active commit history in the five figures. There is also a hosted cloud, which
is out of scope for this page.

If you are new to the category, start here: the community, the examples, and
the integrations are the largest in the field. The reasons someone eventually
looks past it are real but narrower than its size, and they get their own page
in [browser-use alternatives](browser-use-alternatives.md).

### Skyvern - vision-first browser workflows

[github.com/Skyvern-AI/skyvern](https://github.com/Skyvern-AI/skyvern).
About 23k stars, AGPL-3.0. Description: "Automate browser based workflows with
AI". Its distinctive bet is using vision LLMs and computer vision to understand
the page and map elements to actions, instead of depending on selectors that
break when a layout changes. It runs on Playwright underneath and is actively
developed. Note the license: AGPL-3.0 carries obligations MIT does not, which
matters if you embed it in a product. A managed cloud exists with capabilities
the open repository does not include.

### Agent S3 - the whole desktop, not just the browser

[github.com/simular-ai/Agent-S](https://github.com/simular-ai/Agent-S).
About 12k stars, Apache-2.0, from Simular. Description: "Agent S: an open
agentic framework that uses computers like a human". This is a computer-use
agent: it operates the GUI of the machine, browser included but not only. The
Agent S3 release (October 2025, with a TMLR 2026 paper) reports 72.6% on
OSWorld, which the project describes as above the human baseline on that
benchmark. If Operator appealed to you because it could do things, not only
web things, this is the most capable open framework we verified.

The trade-off is the mirror of its breadth: a screenshot-driven desktop agent
is heavier per action than a browser-native one, and
[reading the DOM versus reading pixels](https://github.com/feder-cr/invisible_playwright/wiki/dom-reading-vs-screenshot-agents)
is a real architectural fork, not a detail.

### invisible_playwright_mcp - ours, with the browser as the differentiator

[github.com/feder-cr/invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp). About 30k
stars, MIT (distributions before 2 September 2026 remain AGPL-3.0). The stars
predate the current shape: the project began as a job-application bot and is
becoming a general web agent, which its own description says plainly.

What makes it different in this list is not the agent loop, it is what the
loop drives: a Firefox patched at the C++ level so the browser presents a
normal desktop fingerprint rather than announcing itself as an automation
build. It runs two ways: as an MCP server added to an assistant you already
have (Claude Code, Claude Desktop, Cursor), or as its own local UI with an
OpenRouter key, chat on the left and the live browser on the right. Python
3.11+, Windows and Linux only - no macOS, and that is a real gap next to every
other entry here. A hardened browser is also not a promise of passage:
[what it cannot fix](why-does-my-ai-agent-get-blocked.md) is documented as
carefully as what it can.

### The two projects both called "open operator"

The name collision costs people time, so here it is untangled.

**[browserbase/open-operator](https://github.com/browserbase/open-operator)**
(~2k stars, MIT) was a template for building web agents with Stagehand on
Browserbase, and its README called itself a proof of concept rather than a
product. It was archived on 20 May 2026 and is read-only; the code moved into
a demos repository. Do not adopt it expecting maintenance - its value today is
as a worked example of the Stagehand/Browserbase stack.

**[All-Hands-AI/open-operator](https://github.com/All-Hands-AI/open-operator)**
(~428 stars, MIT), from the OpenHands organization, is not an agent at all: its
description is "Open-source resources on agents for computer use", a curated
reference covering benchmarks and implementations. Useful reading, wrong shelf
if you wanted software to run.

## Reading the table honestly

| Repo | Stars (2026-09-03) | License | Scope | Status |
|---|---|---|---|---|
| browser-use | ~112k | MIT | Browser agent | Active |
| invisible_playwright_mcp | ~30k | MIT | Browser agent | Active |
| Skyvern | ~23k | AGPL-3.0 | Browser workflows | Active |
| Agent-S | ~12k | Apache-2.0 | Desktop computer use | Active |
| browserbase/open-operator | ~2k | MIT | Template | Archived 2026-05-20 |
| All-Hands-AI/open-operator | ~428 | MIT | Resource list | Maintained |

Two cautions about this table, because a table flattens things. Stars measure
attention, not fitness for your task, and part of invisible_playwright_mcp's count is heritage
from its job-bot era. And "active" was judged from commit and issue activity
visible on the repo pages this session, which is a snapshot, not a guarantee.

## How to pick from the open field

- **Most examples, largest community, Chromium acceptable:** browser-use.
- **Layout-fragile workflows you want vision to absorb:** Skyvern, minding
  the AGPL.
- **Tasks that span desktop apps:** Agent S3.
- **Sites that inspect the browser, or you want the agent inside your
  existing MCP assistant:** invisible_playwright_mcp, with our conflict of interest noted and
  the macOS gap admitted.
- **You want to survey the space first:** the All-Hands resource list, then
  come back.

Whatever you pick, run it against your real task before committing. Every
project above is a `pip install` or a `uvx` away, which is the whole point of
this list existing.

## Short answers to the questions that lead here

**Is there an open-source version of OpenAI Operator?** Not a clone of the
product, but several open agents do what it did: browser-use, Skyvern, Agent
S3, and invisible_playwright_mcp are the ones this page verified.

**Which open-source browser agent has the most stars?** browser-use, at
roughly 112k when read on 2026-09-03.

**Is "open operator" a real project?** Two are: an archived Browserbase
template and an OpenHands resource list. Neither is a maintained agent
product.

**Do these need an OpenAI or Anthropic subscription?** No. They take API keys
(or, for invisible_playwright_mcp's MCP route, ride the assistant you already run). Model usage
is pay-per-token to whichever provider you choose.

**Are open agents as good as the hosted ones were?** On desktop benchmarks
the open field now leads: Agent S3 reports 72.6% on OSWorld where OpenAI's
computer-use model reported 38.1%. Benchmarks are not your workload, but the
direction is clear.

**See also:** [OpenAI Operator alternatives](openai-operator-alternatives.md)
for the hosted options next to these,
[open-source AI browser agents](ai-browser-agent-open-source.md) for the same
space compared without the Operator frame,
[browser-use alternatives](browser-use-alternatives.md) for the leader's
trade-offs in detail, and
[Choosing an AI browser agent](best-ai-browser-agent.md) for the decision
framework above the level of any one repo.

## Sources

- The [browser-use](https://github.com/browser-use/browser-use),
  [Skyvern](https://github.com/Skyvern-AI/skyvern),
  [Agent-S](https://github.com/simular-ai/Agent-S),
  [browserbase/open-operator](https://github.com/browserbase/open-operator),
  [All-Hands-AI/open-operator](https://github.com/All-Hands-AI/open-operator)
  and [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) repositories, all retrieved
  2026-09-03; stars, licenses, descriptions and archive status as shown there
  that day.
- [OpenAI computer use guide](https://platform.openai.com/docs/guides/tools-computer-use),
  surfaced via search 2026-09-03, for the 38.1% OSWorld figure quoted in the FAQ.

---

*Maintained alongside [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), one of the
repositories on this list. The star counts that beat ours are printed anyway,
because a survey that hides the bigger projects is an ad, not a survey.*
