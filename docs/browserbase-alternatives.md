---
title: "Browserbase alternatives"
description: "Two different searches hide in this query: another place to run cloud browser fleets (Steel, BrowserStation, Browserless, Hyperbrowser, Anchor), or an agent that removes the infra bill entirely. Both halves, honestly."
parent: "Alternatives and Comparisons"
nav_order: 12
---

# Browserbase alternatives

"Browserbase alternatives" is two different searches wearing one query, and
the honest first step is deciding which one is yours. Either you need what
Browserbase actually sells - managed browser fleets in the cloud - and want a
different vendor or a self-hosted version of the same thing. Or you arrived
here from the top of the funnel, wanting "an agent that browses", found that
the famous name in the space is an infrastructure company, and what you
actually need is an agent, at which point the infrastructure bill is optional.

This page answers both, with the disclosure up front: it lives on the wiki of
[invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), an open-source local agent that
appears in the second half. Every claim about Browserbase and the other
vendors below was read from their own sites, pricing pages and repositories
on 2026-09-03.

## What Browserbase gets right, first

Fairness before alternatives. Browserbase is the mindshare leader of the
[browser infrastructure category](cloud-browser-infrastructure-for-ai-agents.md)
and earned it. The pricing is legible: a free tier (3 concurrent browsers,
sessions capped at 15 minutes), a $20/mo Developer tier with 100 browser
hours then $0.12/hr, a $99/mo Startup tier with 500 hours, and custom above
that. Its homepage claims "10,000+ companies building beyond the API"; that
is the company's own number, but the ecosystem gravity around it is checkable
another way: it open-sourced [Stagehand](https://github.com/browserbase/stagehand)
(MIT, ~24.1k stars), an SDK for browser agents that people use who never buy
the cloud, and it gives away [Director](https://www.browserbase.com/director),
which turns plain-English instructions into working agents and exports real
Stagehand code. A vendor whose free, open layers are this good is not one you
leave casually.

So the reasons to look elsewhere are specific, not general: you want open
source you can self-host and audit; you want to own the metered costs at
scale; you want a different point on the price curve; or, second half of the
page, you never needed managed fleets at all.

## Half one: you need cloud browser fleets, elsewhere

If concurrent browsers in the cloud are genuinely your requirement - a
product feature, CI, scale beyond one machine - these are the real
alternatives, one line of facts each, read from their own pages on
2026-09-03.

| Alternative | Open? | The one-line honest version |
|---|---|---|
| [Steel](https://github.com/steel-dev/steel-browser) | Apache-2.0, ~7.6k stars | The credible open-source answer: a browser API you self-host with one `docker run`, Chrome over CDP, Puppeteer/Playwright/Selenium supported, plus a paid cloud if you want one |
| [BrowserStation](https://github.com/ReinforceNow/browserstation) | MIT, ~166 stars | New and small, but architecturally serious: Kubernetes plus Ray, Chrome sidecars exposing CDP, self-described as an open-source alternative to Browserbase |
| [Browserless](https://github.com/browserless/browserless) | SSPL-1.0 OR commercial, ~13.7k stars | The veteran (repo since 2017), Docker-deployable, but the SSPL is source-available, not OSI-approved open source; read the license before you build on it |
| [Hyperbrowser](https://hyperbrowser.ai/docs) | SaaS | Hosted sessions plus scraping and crawl APIs, reachable over Playwright, Puppeteer and CDP |
| [Anchor Browser](https://anchorbrowser.io/) | SaaS | Sells its own Chromium fork it calls "humanized chromium", in credit tiers from free to $2,000/mo; the fork's properties are Anchor's claims, untested by us |
| [Kernel](https://www.kernel.sh/) | SaaS | Chromium sessions over Playwright, CDP or WebDriver BiDi, and a hosted MCP server so tool-calling assistants can drive it directly |
| [Cloudflare Browser Run](https://developers.cloudflare.com/browser-rendering/) | Big-cloud SaaS | Headless Chrome on Cloudflare's network, driven over Puppeteer, Playwright, CDP or Stagehand; the safe-default choice if you are already on Workers |

Three notes the table cannot hold. First, Steel is the head-to-head
comparison most people searching this query actually want: open code, Apache
license, self-host by default, cloud optional - the inverse of Browserbase's
shape. Second, if your reason for leaving is price at scale, self-hosting
moves the spend from browser-hours to your own compute and the engineering
time to run it; that trade has a break-even, not a winner, and
[what a self-hosted AI agent costs to run](self-hosted-ai-agent.md) puts one
side of it in megabytes rather than adjectives. Third, every entry
in the table, Browserbase included, runs Chromium or speaks its protocol, so
switching vendors changes your operations and your bill, not what a website
sees when it inspects the browser. The category-wide explainer covers that
through-line:
[cloud browser infrastructure for AI agents](cloud-browser-infrastructure-for-ai-agents.md).

## Half two: what you wanted was an agent, and the bill is optional

Now the other search. If you are one person or one team wanting tasks done
in a browser - not building a product that hosts browsers for others - then
managed fleets are an answer to a question you do not have. An agent that
runs on your own machine does the browsing where you are, and the
infrastructure line item is zero because there is no infrastructure vendor.

The open-source agent field is surveyed properly on
[open-source AI browser agents](ai-browser-agent-open-source.md); the short
version relevant here:

- **browser-use** (MIT, the most-adopted agent framework) runs locally
  against a Chromium-family browser, and its company also now sells hosted
  infrastructure if you later grow into wanting it.
- **Stagehand itself is MIT**, which is worth restating in a page about its
  maker: the SDK layer is not what you pay Browserbase for; the managed
  fleet is. If your usage of Browserbase is "I like Stagehand", the code is
  open. How Stagehand compares to the agent frameworks is its own page:
  [Stagehand vs browser-use](stagehand-vs-browser-use.md).
- **invisible_playwright_mcp** (MIT, ~30k stars) - ours, disclosure above. It runs locally and
  ships its own browser: a Firefox patched at the C++ level rather than a
  stock Chromium build, driven through an MCP server from an assistant you
  already run (Claude Code, Claude Desktop, Cursor) or from its own UI with
  an OpenRouter key. The costs are model tokens and nothing else.

And the concessions, because this half is where our interest lives:
a local agent gives you no fleet, no concurrency beyond your machine, no
session cloud, no CI story, and invisible_playwright_mcp specifically is Windows and Linux
only. A hardened browser changes what a page reads from the browser; it does
not change your IP, your pacing, or a site's limits, and nothing here
promises otherwise -
[why agents get blocked](why-does-my-ai-agent-get-blocked.md) draws that
boundary in full. If your workload is a product's workload, half one is your
half.

## How to decide

- **You operate browser fleets for a product or pipeline, want managed:**
  stay on Browserbase, or price Hyperbrowser, Kernel, Anchor and Cloudflare
  against your usage shape.
- **Same requirement, but open source and self-hosted:** Steel first;
  BrowserStation if you are Kubernetes-native and early-adopter tolerant;
  Browserless only after reading the SSPL.
- **You want an agent for your own tasks on your own machine:** the agent
  field above; the infra bill disappears. invisible_playwright_mcp is our entry in it,
  conflict of interest noted.
- **You mainly want Stagehand:** it is MIT; you can use it without the
  cloud, and [Stagehand vs browser-use](stagehand-vs-browser-use.md) maps
  that choice.

## Short answers to the questions that lead here

**What is the best open-source alternative to Browserbase?** Steel
(Apache-2.0) is the mature one: self-hosted browser API, Chrome over CDP,
one Docker command to try. BrowserStation (MIT) is the newer
Kubernetes-native option. Browserless self-hosts but is SSPL-licensed, which
is not OSI open source.

**Is Browserbase free?** It has a real free tier: 3 concurrent browsers, 1
browser hour, 15-minute session cap (read 2026-09-03). Paid starts at
$20/mo. Stagehand and Director are free layers around the paid cloud.

**Can I self-host Browserbase?** No; the cloud is the product. Stagehand,
its MIT SDK, runs wherever you want. For the managed fleet itself, the
self-host equivalents are Steel and BrowserStation.

**Do I need Browserbase to run an AI browser agent?** No. Every major
open-source agent runs on your own machine. The cloud earns its cost at
fleet scale, in CI, or inside products; for personal and single-machine use,
a local agent (invisible_playwright_mcp among them, disclosure above) has no infra cost at
all.

**Is Browserbase open source?** The platform is not; Stagehand (MIT) and
Director's exported code are the open layers. That split - open SDK, paid
cloud - is the category's standard shape, not a Browserbase quirk.

**See also:**
[Cloud browser infrastructure for AI agents](cloud-browser-infrastructure-for-ai-agents.md)
for the whole category explained,
[Stagehand vs browser-use](stagehand-vs-browser-use.md) for the SDK-level
choice, [open-source AI browser agents](ai-browser-agent-open-source.md) for
the agent field, and [browser-use alternatives](browser-use-alternatives.md)
for the same exercise applied to the biggest agent framework.

## Sources

All retrieved 2026-09-03; prices, limits and star counts were read from each
vendor's own page on that date and will drift.

- [Browserbase](https://www.browserbase.com/), [its pricing page](https://www.browserbase.com/pricing), [its docs](https://docs.browserbase.com/introduction) and [Director](https://www.browserbase.com/director).
- [browserbase/stagehand](https://github.com/browserbase/stagehand).
- [steel-dev/steel-browser](https://github.com/steel-dev/steel-browser).
- [ReinforceNow/browserstation](https://github.com/ReinforceNow/browserstation).
- [browserless/browserless](https://github.com/browserless/browserless).
- [Hyperbrowser docs](https://hyperbrowser.ai/docs).
- [Anchor Browser](https://anchorbrowser.io/).
- [Kernel](https://www.kernel.sh/).
- [Cloudflare Browser Run](https://developers.cloudflare.com/browser-rendering/).
- [browser-use.com](https://browser-use.com/), for its hosted infrastructure product.

---

*Written while maintaining [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp),
which competes with exactly one half of this page. That is why the other
half opens with what Browserbase gets right and sends you to Steel, not to
us.*
