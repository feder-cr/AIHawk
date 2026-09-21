---
title: "Skyvern alternatives"
description: "Skyvern's own README states that its anti-bot measures are exclusive to the managed cloud, and the core is AGPL-3.0. Which half of that sentence sent you looking, and which alternative actually answers it."
parent: "Alternatives and Comparisons"
nav_order: 14
---

# Skyvern alternatives

Skyvern keeps one of the most honest sentences in this category near the top
of its README, and this page is organized around it: "All of the core logic
powering Skyvern is available in this open source repository licensed under
the AGPL-3.0 License, with the exception of anti-bot measures available in
our managed cloud offering." Read on 2026-09-03, at roughly 22.9k GitHub
stars. Most projects bury a trade like that in a pricing page; Skyvern states
it in plain text, and it deserves credit for doing so. It also means the
search that brought you here is usually not "is Skyvern good" - it is - but
"which half of that sentence is a problem for me, and what answers it".

Disclosure before anything else: this wiki belongs to
[AIHawk](https://github.com/feder-cr/aihawk_mcp_server), an open-source agent that
competes with Skyvern and appears below as one of the alternatives. Every
claim about Skyvern here traces to its own repository, and where Skyvern is
the better tool this page says so.

## What Skyvern is, stated fairly

Python, Playwright underneath, AGPL-3.0, installable via pip or Docker
Compose, with Skyvern Cloud as the hosted option. The architectural bet is
vision: LLMs read the rendered page and plan actions against what they see,
rather than depending on XPath or CSS selectors, and the README describes the
result as a "Playwright-compatible SDK that adds AI functionality". On top of
that sit parameterized workflows: multi-step automations you define once and
rerun with different inputs. The bet - pay tokens to look at pixels so that a
site redesign does not break your script - is coherent, and for form-heavy
pages that change layout often it is the right one. Nothing below disputes
any of this.

## The two halves of the sentence

### The license half: AGPL-3.0

AGPL is strong copyleft that extends to network use: if you build Skyvern
into a service you offer to other people, you take on source-sharing
obligations that MIT and Apache tools do not carry. That is a one-line
summary, not legal advice, and for an individual automating their own
browser work the license costs nothing at all. But it is the single most
common reason companies evaluating Skyvern end up on a page like this one,
and it is why every other tool named below is MIT or Apache-2.0.

### The other half: the hard part lives in the cloud

The part of the sentence after the comma is the part self-hosters feel. What
the README calls anti-bot measures is precisely the piece kept out of the
repository, and two fair things need saying about that. First, it is a
legitimate design: code of that kind is kept private by essentially everyone
who ships it, because publishing it shortens its useful life, and the cloud
is what funds the open core. Second, the consequence for you: what `pip
install skyvern` runs locally is standard Playwright Chromium, and its
sessions answer a page's questions the way any stock automation build does.
That is not a Skyvern defect - it is the shared box of the whole
Playwright-Chromium class, documented on this wiki for browser-use in
[what configuration can and cannot change](browser-use-getting-blocked.md).
And before you attribute a challenged run to any tool, read
[why an agent gets blocked](why-does-my-ai-agent-get-blocked.md): machine
and network facts decide most of these outcomes, and nothing on this page
changes your IP.

## The alternatives, sorted by which half moved you

### browser-use: same class, different interaction model

Roughly 112.2k stars, MIT, Python. Not a workflow builder: you construct an
`Agent` with a task and a model, call `run()`, and its loop does the rest -
a conversational agent rather than a parameterized pipeline. If the license
half was your problem, this is the most direct swap in the same
Playwright-Chromium class. If the cloud half was, know that the structure
repeats: browser-use's README points production users at Browser Use Cloud
and describes it with features including what it calls built-in stealth and
proxy rotation - vendor claims we did not test. The MIT core runs locally
either way. Full treatment on
[browser-use alternatives](browser-use-alternatives.md).

### Stagehand: buy an SDK instead of a platform

Roughly 24.1k stars, MIT, TypeScript with Python and Go SDKs, built by
Browserbase. Three primitives - `act()`, `observe()`, `extract()` - on a
Playwright-style API, under the banner "Playwright was built for testing,
Stagehand is built for agents". This is the alternative for people who liked
Skyvern's Playwright compatibility more than they liked adopting a platform:
you keep your own loop and mix AI steps with plain deterministic calls in
the same script. The full referee comparison is
[Stagehand vs browser-use](stagehand-vs-browser-use.md), and the hosted
side of that ecosystem is covered in
[Browserbase alternatives](browserbase-alternatives.md).

### The UI-TARS class: put the capability in the model

UI-TARS (roughly 11.4k stars, Apache-2.0) is not a framework but a
vision-language agent model: the GUI-operating capability is trained into
the weights, and you bring your own scaffold or use its desktop companion.
It is the furthest departure on this page - no workflow engine, real
inference costs, research-grade edges - but if your read on Skyvern was
"vision-driven operation is the right idea", this is that idea without a
platform around it. Context in
[open-source computer-use agents](computer-use-agent-open-source.md).

### AIHawk: the hard part ships in the product - ours

Roughly 30k stars, MIT, and the conflict of interest from the top of the
page applies to this section. The contrast maps directly onto Skyvern's
sentence: where Skyvern's README places its anti-bot measures in the managed
cloud, AIHawk's equivalent hard part is the browser itself - a Firefox
patched at the C++ level (the invisible_playwright engine) that presents a
normal desktop fingerprint - and it ships inside the open-source product,
running on your machine. That is a different placement of the same problem,
not magic: we make no promise of non-detection anywhere, sites remain free
to challenge any visitor, and the engine wiki documents
[how to test the difference yourself](https://github.com/feder-cr/invisible_playwright/wiki/how-to-test-bot-detection)
rather than asking you to take a claim on faith. The interaction model is
also different in kind: AIHawk is a conversational agent that plugs into an
MCP assistant you already run (Claude Code, Claude Desktop, Cursor) or its
own local UI, not a vision-workflow engine, and it runs on Windows and Linux
only.

## Where Skyvern wins outright

Fairness requires its own section. The vision-workflow model is the most
resilient approach on this page to layout churn, and none of the
alternatives replaces it like for like: browser-use gives you an agent, not
rerunnable parameterized workflows; Stagehand gives you primitives, not a
workflow engine; AIHawk gives you a different browser and a conversational
loop, not structured pipelines. Skyvern also has a hosted option for teams
that want managed scale, a straightforward pip and Docker story, and the
rare virtue of a README that tells you its own limits. If neither the
license nor the placement of the hard part bothers you, stay on Skyvern and
close this tab; it is a good tool.

## Short answers to the questions that lead here

**Is Skyvern open source?** The core is, under AGPL-3.0. Its README states
the exception itself: the measures it describes as anti-bot are available in
the managed cloud offering, not the repository.

**Skyvern vs browser-use - what is the actual difference?** Same class
(LLM agents driving Playwright Chromium), different models of use:
parameterized vision-workflows versus a conversational agent loop, AGPL
versus MIT. Neither changes what the browser underneath looks like.

**Is Skyvern free to self-host?** Yes, via pip or Docker, plus whatever
your model provider charges in tokens. The cloud is a paid product.

**Can self-hosted Skyvern handle sites that challenge automation?** Its
README reserves that category for the cloud. Self-hosted, you are running
standard Playwright Chromium, and outcomes mostly track the machine and
network facts covered in
[why an agent gets blocked](why-does-my-ai-agent-get-blocked.md).

**Is AIHawk better than Skyvern?** Not in general, and this is our own wiki
saying so. It differs where the browser itself or the AGPL is your problem;
Skyvern is better where workflow authoring, vision resilience to layout
change, or a hosted option matter.

**See also:** [Stagehand vs browser-use](stagehand-vs-browser-use.md) for
the SDK half of this page expanded,
[browser-use alternatives](browser-use-alternatives.md) for the mirror-image
survey, and [Choosing an AI browser agent](best-ai-browser-agent.md) for the
full decision framework.

## Sources

- The [Skyvern repository](https://github.com/Skyvern-AI/skyvern), retrieved
  2026-09-03: star count, license, the quoted README sentence, install
  paths, and the vision-LLM and Playwright-SDK descriptions.
- The [browser-use repository](https://github.com/browser-use/browser-use),
  retrieved 2026-09-03: star count, license, the agent API shape, and the
  cloud description quoted attributively.
- The [Stagehand repository](https://github.com/browserbase/stagehand),
  retrieved 2026-09-03: star count, license, languages, and API primitives.
- The [UI-TARS repository](https://github.com/bytedance/UI-TARS), retrieved
  2026-09-03: star count, license, and model positioning.

---

*Written while maintaining [AIHawk](https://github.com/feder-cr/aihawk_mcp_server),
which competes with Skyvern. That is why the page opens by crediting
Skyvern's honesty, closes its survey with where Skyvern wins, and quotes the
README instead of paraphrasing it.*
