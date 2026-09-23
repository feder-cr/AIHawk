---
title: "Stagehand vs browser-use"
description: "An SDK for building browser agents versus a framework that ships one: what act(), observe() and extract() buy you against Agent().run(), which languages each serves, and which features sit behind each vendor's cloud."
parent: "Alternatives and Comparisons"
nav_order: 15
---

# Stagehand vs browser-use

This comparison reads like a rivalry and mostly is not one. Both projects
are MIT licensed, actively maintained, and descended from the same idea of
putting an LLM in charge of a Playwright-driven Chromium browser. The real
difference fits in one line: Stagehand is a kit for building an agent;
browser-use is an agent someone already built. Almost everything else on
this page is a consequence of that line.

Disclosure: this wiki belongs to
[invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), an open-source agent that
competes in the same space as both tools. Neither subject of this page is
ours, which is what makes it a referee page; our own tool appears exactly
once, near the end, clearly labeled. All facts were retrieved 2026-09-03
from the two repositories and Stagehand's documentation.

## Day one with each

**Stagehand** ([browserbase/stagehand](https://github.com/browserbase/stagehand),
roughly 24.1k stars, a monorepo with TypeScript, Python and Go packages,
built by Browserbase) gives you three primitives on a Playwright-style page
object: `act()` executes an action described in natural language,
`observe()` enumerates what is actionable on the page, and `extract()`
returns structured data against a schema. The README's positioning sentence
is the whole thesis: "Playwright was built for testing, Stagehand is built
for agents." The property that matters most in practice is that the
primitives are per-step: you can mix an AI-interpreted `act()` with plain
deterministic `goto`, `click` and `locator` calls in the same script, and
decide for every step how much model you want in the loop.

**browser-use** ([browser-use/browser-use](https://github.com/browser-use/browser-use),
roughly 112.2k stars, Python) is the most-starred project in the category,
and you do not write steps at all. You construct an `Agent` with a task
description and a model, call `run()`, and the loop - perceive the page,
decide, act, retry - is the product. It supports its own hosted models as
well as OpenAI, Anthropic and Google under your keys.

## The axis that decides it: who owns the loop

With an SDK, the agent loop is your code. Its memory, its retries, when it
gives up, what it logs, how it recovers from a half-finished form - all
yours. That costs you a design: nothing in Stagehand prevents you from
building a bad agent, and the blank page is real. What it buys is
embedding: agentic steps can go inside software you already have, an
existing test suite can adopt `act()` for its three most brittle steps
without adopting anything else, and every part you did not delegate to a
model stays deterministic.

With a framework, the loop arrives built and tuned, and you get a working
automation the first afternoon. The cost is opinion: when the built-in loop
does the wrong thing on your case, you are debugging someone else's control
flow and working through a framework's extension points rather than editing
your own.

The honest rule of thumb: teams that already have software and want agency
inside it lean Stagehand; teams whose deliverable is the automation itself
lean browser-use.

## Language ecosystems

Stagehand's monorepo is TypeScript-first with official Python and Go
packages. browser-use is Python, full stop. A TypeScript or Go shop
therefore chooses Stagehand almost by default, and a Python-native data
team will find browser-use the more natural fit - though the existence of
Stagehand's Python package means the language argument alone no longer
settles it in either direction.

## Who runs the browser

Both drive Chromium-family browsers, and both run locally by default.
Stagehand's browser configuration documents a local environment that "runs
browsers directly on your machine" with a custom Chrome path, a fixed CDP
debugging port and user-data persistence; Firefox and WebKit appear nowhere
in it. The docs are also candid about the vendor's preference:
"Browserbase recommends running Stagehand on Browserbase. A hosted browser
is what enables server-side caching and the Model Gateway."

browser-use has the same shape with a different vendor: local by default,
with the README pointing production users at Browser Use Cloud and
describing it with features including what it calls built-in stealth, proxy
rotation and CAPTCHA solving - vendor claims we did not test and quote as
theirs.

So the deciding question is not local-versus-cloud, since both offer both.
It is which features sit behind each cloud door: with Stagehand, caching
and the Model Gateway per its own docs; with browser-use, the
harder-environment features per its own README. And either way, both open
cores put a stock automation Chromium on the wire, and neither reaches the
machine and network facts that decide most challenge outcomes - the
groundwork is in [why an agent gets blocked](why-does-my-ai-agent-get-blocked.md)
and the infrastructure angle in
[cloud browser infrastructure for AI agents](cloud-browser-infrastructure-for-ai-agents.md).

## Where each one breaks first

Stagehand breaks first at the loop you have to write. Retries, memory
across steps, stopping conditions: browser-use ships all of it, and with
Stagehand you will reimplement some of it, well or badly. There is also
vendor gravity to read clearly: the docs tie the platform's most
interesting operational features to the hosted product, which is fair
business but belongs in your plan.

browser-use breaks first at the framework boundary. Embedding an
autonomous loop inside an existing product is harder than embedding a
function call, and disagreement with the loop's behavior sends you into
framework internals. The counterweight is community scale: at roughly
112.2k stars, the odds someone has already filed your exact issue are the
best in the category.

## How to choose

If you have an existing codebase - a Playwright test suite, a product, a
pipeline - and want to add agentic steps to it, take Stagehand. If you want
a working automation today and Python is acceptable, take browser-use. If
your constraint is TypeScript or Go, Stagehand is the only one of the two
on offer. And if you are really choosing infrastructure for a fleet of
agents rather than an API to write against, the browser and where it runs
matter more than the SDK - start from
[Browserbase alternatives](browserbase-alternatives.md) instead.

## If you would rather not build an agent at all

One labeled aside, and the disclosure from the top applies. Both subjects
of this page assume you want to assemble or adopt an agent loop around a
Chromium browser. If what you actually want is to hand browsing tasks to an
assistant you already run, our own
[invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) (roughly 30k stars, MIT) is an
agent that plugs into MCP assistants (Claude Code, Claude Desktop, Cursor)
and differs from both at the browser layer, driving a Firefox patched at
the C++ level rather than an automation-build Chromium. It is not an SDK,
it does not compete with Stagehand as one, and it makes no promise of
non-detection; if you are building, build with the two tools above. The
labeled comparison against this page's bigger subject is
[browser-use alternatives](browser-use-alternatives.md).

## Short answers to the questions that lead here

**Can I use Stagehand without Browserbase?** Yes. It is MIT licensed and
its documented local environment runs Chrome or Chromium directly on your
machine with your own model keys. Its docs add that server-side caching and
the Model Gateway are enabled by the hosted browser, so plan on Browserbase
if you want those two.

**Is Stagehand a framework like browser-use?** No. It is an SDK: primitives
to build an agent with, on a Playwright-style API. The loop is yours to
write, which is the point.

**Does browser-use support TypeScript?** The repository is Python. For a
TypeScript-native equivalent you are in Stagehand territory or writing the
loop yourself.

**Do either of them support Firefox?** No. Both drive Chromium-family
browsers; Stagehand's browser configuration documents Chrome and Chromium
only.

**Which is more popular?** browser-use by a wide margin - roughly 112.2k
stars against 24.1k, read 2026-09-03. Within the SDK-shaped lane, Stagehand
is the biggest thing there is.

**Are they free?** Both cores are MIT. You pay your model provider for
tokens either way, and both vendors run paid hosted products.

**See also:** [Browserbase alternatives](browserbase-alternatives.md) for
the hosted side of Stagehand's ecosystem,
[browser-use alternatives](browser-use-alternatives.md) for the survey
around this page's bigger subject,
[Skyvern alternatives](skyvern-alternatives.md) for the workflow-shaped
neighbor, and [Choosing an AI browser agent](best-ai-browser-agent.md) for
the full decision framework.

## Sources

- The [Stagehand repository](https://github.com/browserbase/stagehand),
  retrieved 2026-09-03: star count, license, languages, the three
  primitives, and the positioning quote.
- The [browser-use repository](https://github.com/browser-use/browser-use),
  retrieved 2026-09-03: star count, license, the `Agent` API shape, model
  providers, and the cloud description quoted attributively.
- The [Stagehand documentation home](https://docs.stagehand.dev/), retrieved
  2026-09-03: the "Browserbase recommends running Stagehand on Browserbase"
  quote.
- The [Stagehand browser configuration docs](https://docs.stagehand.dev/v3/configuration/browser),
  retrieved 2026-09-03: the local environment, Chrome path and CDP port
  options, and the absence of non-Chromium browsers.

---

*Written while maintaining [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp),
which competes with both tools compared here - reason enough to keep our
own tool out of the verdict and every load-bearing claim quoted from the
vendors' own material.*
