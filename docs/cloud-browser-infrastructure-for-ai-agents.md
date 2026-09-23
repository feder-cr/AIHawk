---
title: "Cloud browser infrastructure for AI agents, explained"
description: "What the browser-infrastructure layer actually is, the real vendors in it - Browserbase, Steel, Browserless, Hyperbrowser, Anchor, Kernel, Airtop, Cloudflare, Lightpanda - and the honest question of whether you need the layer at all."
parent: "Alternatives and Comparisons"
nav_order: 11
---

# Cloud browser infrastructure for AI agents, explained

Search for "browser infrastructure for AI agents" and every result is a vendor
describing itself. That is not a criticism of the vendors; it is just what
happens in a young category where the only people writing about the layer are
the people selling it. This page is the missing neutral explainer: what the
layer is, who is actually in it, what they all have in common, and the
question the vendor pages skip, which is whether your setup needs the layer at
all.

Disclosure before anything else: this wiki belongs to
[invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), an open-source agent that ships
its own browser and runs locally, which is one of the two answers to that last
question. Our interest runs against the category, so read the closing section
knowing that, and read the vendor descriptions knowing that every fact in them
was checked against that vendor's own site, repository or docs on 2026-09-03.

## What the layer actually is

An AI browser agent has two halves. The agent loop - a model reading a page
and deciding the next action - is code you run or a product you use. The
browser that loop drives is a heavy, stateful, crash-prone OS process, and
"browser infrastructure" is the business of running that process for you,
somewhere else.

Concretely, a browser infrastructure vendor gives you an API that starts a
browser in their cloud and hands back a connection URL. Your code, unchanged,
connects to it over the same protocols it would use locally - Playwright,
Puppeteer, or raw CDP - and everything else is their problem: spawning and
recycling processes, keeping sessions alive between calls, session recordings
and live debug views, egress routing, and scaling from one browser to
hundreds. You pay per browser-hour, per credit, or per seat.

That is the whole idea. It is the same move as any managed service: the
database did not change when you stopped hosting it, and the browser does not
either.

## Why the category exists

Three facts about browsers make the business real. They are expensive to run
at density: a real page can hold a Chromium process at hundreds of megabytes,
so a fleet of fifty is a machine-sizing problem, not a loop. They are terrible
citizens in CI: no display, missing system dependencies, fonts, and sandbox
flags that differ per distro. And agent workloads are bursty: you want zero
browsers most of the day and two hundred for ten minutes.

If your agent is a product feature - a SaaS that browses on behalf of your
users - those three facts arrive on day one, and renting the layer is usually
the right call. Hold that thought against the closing section, because none of
the three facts applies to one person running one agent on one machine.

## The vendors, one honest line each

Facts below were read from each vendor's own site, pricing page or repository
on 2026-09-03; prices and star counts drift.

**[Browserbase](https://www.browserbase.com/)** is the category's mindshare
leader: a SaaS with a free tier (3 concurrent browsers, sessions capped at 15
minutes), then $20/mo, $99/mo and custom tiers, its homepage claiming
"10,000+ companies". Two things distinguish it beyond scale: it open-sourced
[Stagehand](https://github.com/browserbase/stagehand) (MIT, ~24.1k stars),
the SDK layer many agents use whether or not they buy Browserbase, and it
gives away [Director](https://www.browserbase.com/director), which turns
plain-English instructions into exportable Stagehand code. The open SDK is a
funnel to the paid cloud, and it is a good funnel because the SDK is good.

**[Steel](https://github.com/steel-dev/steel-browser)** is the credible
open-source answer: Apache-2.0, ~7.6k stars, a browser API you self-host with
a single `docker run` against their published image, driving Chrome over CDP
with Puppeteer, Playwright and Selenium support. If "open source" in this
category matters to you, this is the project to evaluate first.

**[Browserless](https://github.com/browserless/browserless)** is the veteran:
its repository dates to November 2017, years before agents were the customer,
and it has ~13.7k stars. Know the license before you build on it: the SPDX
line reads "SSPL-1.0 OR Browserless Commercial License". The SSPL is a
source-available license the OSI has not approved as open source, so
"self-hostable" and "open source" are not the same word here.

**[Hyperbrowser](https://hyperbrowser.ai/docs)** is a hosted SaaS selling
"fast, reliable cloud browsers and sandboxes for AI automation", reachable
over Playwright, Puppeteer and CDP, with scraping and crawl APIs alongside
the raw sessions.

**[Anchor Browser](https://anchorbrowser.io/)** is a SaaS whose pitch is the
browser build itself: its own Chromium fork it calls "humanized chromium",
sold in credit tiers from free (5 credits) through $50, $500 and $2,000 per
month, with $1.00 per credit overage. The fork's properties are Anchor's own
claims; we did not test them.

**[Kernel](https://www.kernel.sh/)** runs isolated Chromium sessions you
reach over Playwright, CDP or WebDriver BiDi, and is notable for meeting
agents where they now live: it also exposes a hosted MCP server, so a
tool-calling assistant can drive its browsers without you writing glue.

**[Airtop](https://www.airtop.ai/)** is a SaaS one level up the stack: less
"here is a browser" and more an agent-builder, where you describe a workflow
in plain language and it compiles it into a deterministic agent that runs on
a schedule on their cloud browsers.

**[Cloudflare](https://developers.cloudflare.com/browser-rendering/)** is the
big-cloud entrant. Its product, recently renamed Browser Run (formerly
Browser Rendering), runs headless Chrome on Cloudflare's network, driven over
Puppeteer, Playwright, CDP or Stagehand, with REST endpoints for one-shot
screenshots, PDFs and markdown. When a company that size treats the layer as
a platform primitive, the category has stopped being a startup experiment.

**[Lightpanda](https://github.com/lightpanda-io/browser)** is the odd one
out and the most interesting engineering bet on the list: not hosted
Chromium but a new headless browser written from scratch in Zig, AGPL-3.0,
~34.4k stars, claiming roughly 9x faster execution and 16x less memory than
Chrome on its own benchmark. The honesty is in its README too: it is beta,
web API coverage is partial, and some sites will error or crash. A browser
for machines, not yet a browser for the whole web.

**[BrowserStation](https://github.com/ReinforceNow/browserstation)** is the
newest self-host option: MIT, tiny today (~166 stars), Kubernetes-native via
Ray, each worker pod running a Chrome sidecar that exposes CDP, and
explicitly described by its authors as an open-source alternative to
Browserbase. Early, but the architecture is the one an infra team would ask
for.

One more entrant matters because of where it came from:
**[browser-use](https://browser-use.com/)**, the most-adopted open-source
agent framework, now sells "Browser Use Agents" and "Browser Infrastructure"
as its two commercial products. The agent side of the market arriving at
infra confirms the direction of the money: the layer is where browser-agent
companies monetize.

## The through-line: it is Chromium all the way down

Check the engine column across the list and one fact repeats. Every vendor
that names its browser runs Chrome, Chromium or a Chromium fork: Steel and
BrowserStation say Chrome, Kernel says Chromium, Anchor is a Chromium fork,
Cloudflare says headless Chrome. The vendors that do not name an engine still
speak CDP, which is Chromium's protocol. The only exception is Lightpanda,
which escaped Chromium by writing a new browser and is paying the price in
web compatibility.

Two consequences follow. The convenient one: your automation code is
portable, because the whole category standardized on one engine and its
protocols, and switching vendors is mostly a connection-string change. The
inconvenient one: a cloud browser is the same browser. Moving a stock
Chromium automation build from your laptop to a vendor's cloud changes where
it runs, not what a page inspecting it sees, and it typically swaps your
residential IP for datacenter egress, which is why most of these vendors also
sell proxy routing as an add-on. The layer solves operations. It does not
solve the questions covered in
[why does my AI agent get blocked](why-does-my-ai-agent-get-blocked.md), and
the serious vendors do not claim it does.

## When you need the layer, and when you do not

You need cloud browser infrastructure when the three facts from the top
apply: fleets of concurrent browsers, agents running in CI or on servers with
no display, bursty scale, sessions that must outlive any one machine, or a
product whose users bring the workload. If that is you, the split that
matters is managed versus self-host: Browserbase, Hyperbrowser, Anchor,
Kernel, Airtop and Cloudflare on one side; Steel, BrowserStation and (with
the license caveat) Browserless on the other.

You do not need it when the agent is yours, personal, and local. One person
running one agent for their own tasks has no fleet, no CI, and no burst; the
laptop that is already on is the infrastructure. This is invisible_playwright_mcp's route, and
the disclosure from the top applies in full: invisible_playwright_mcp ships its own browser, a
Firefox patched at the C++ level rather than a hosted Chromium, runs it on
your machine, and there is no per-hour or per-credit bill because there is no
vendor in the loop. Model tokens are the only metered cost. The trade is
real in both directions: you get no fleet, no managed scaling and no session
cloud, and it is Windows and Linux only. The bill that replaces the per-hour one
is disk and memory on your own machine, and it is smaller than the figures this
category usually quotes:
[what a self-hosted AI agent actually costs to run](self-hosted-ai-agent.md)
measures it at 613 MB installed and about 900 MB resident, with the model bill
kept separate. For what that local route looks like
against the rest of the agent field, see
[open-source AI browser agents](ai-browser-agent-open-source.md).

## Short answers to the questions that lead here

**What is browser infrastructure for AI agents?** A managed place for your
agent's browser process to run: a vendor API that starts browsers in their
cloud and hands your code a Playwright/CDP connection, plus the scaling,
session persistence and debugging around it.

**What is the best headless browser for AI agents?** The engine answer is
almost settled: the category runs Chromium, so the real choice is who
operates it (the vendors above) or whether you run it yourself. The one
non-Chromium bet, Lightpanda, is fast but openly partial on web
compatibility today.

**Is there an open-source Browserbase?** Steel (Apache-2.0) is the mature
answer; BrowserStation (MIT, Kubernetes-based) is the new one and describes
itself in exactly those words. Browserless self-hosts but is SSPL-licensed,
which is source-available, not OSI open source.

**Do I need cloud browsers to run an AI agent?** No. Every major open-source
agent runs on your own machine, and a local agent that ships its own browser
(invisible_playwright_mcp is one, disclosure above) has no infra bill at all. The layer earns
its cost at fleet scale, in CI, or inside products.

**How much does it cost?** Entry tiers are cheap ($0 to $99/mo across the
SaaS vendors above); the real spend is metered browser-hours, credits and
proxy gigabytes at scale, which is exactly when self-hosting starts to look
attractive.

**See also:** [Browserbase alternatives](browserbase-alternatives.md) for the
vendor-by-vendor version of this decision,
[browser-use alternatives](browser-use-alternatives.md) for the agent layer
above this one, and
[AI browser agents vs traditional scraping](ai-browser-agents-vs-traditional-scraping.md)
for whether you need a browser in the loop at all.

## Sources

All retrieved 2026-09-03. Star counts, prices and tier limits were read from
each project's own page on that date and will drift.

- [Browserbase](https://www.browserbase.com/), [its pricing page](https://www.browserbase.com/pricing), [its docs introduction](https://docs.browserbase.com/introduction) and [Director](https://www.browserbase.com/director).
- [browserbase/stagehand](https://github.com/browserbase/stagehand).
- [steel-dev/steel-browser](https://github.com/steel-dev/steel-browser).
- [browserless/browserless](https://github.com/browserless/browserless); creation date read from the repository's GitHub API record.
- [Hyperbrowser docs](https://hyperbrowser.ai/docs).
- [Anchor Browser](https://anchorbrowser.io/).
- [Kernel](https://www.kernel.sh/).
- [Airtop](https://www.airtop.ai/).
- [Cloudflare Browser Run](https://developers.cloudflare.com/browser-rendering/).
- [lightpanda-io/browser](https://github.com/lightpanda-io/browser).
- [ReinforceNow/browserstation](https://github.com/ReinforceNow/browserstation).
- [browser-use.com](https://browser-use.com/), for the two commercial products.

---

*Written while maintaining [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), a
local agent that exists so its users do not need this layer. That bias is
stated because it is real; the vendor facts above are theirs, checked against
their own pages.*
