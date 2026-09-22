---
title: "Gemini computer use vs Claude computer use"
description: "Both vendors' screenshot-loop APIs are alive and current, which makes this the rare comparison in the series with two living sides. Model lineups, environments, costs and safety posture, verified against both docs."
parent: "Alternatives and Comparisons"
nav_order: 18
---

# Gemini computer use vs Claude computer use

This series has compared a dead product to a living tool before. This page
is the other kind: both sides exist, both are documented, and both were
verified against the vendors' own pages for this comparison on 2026-09-03.
The occasion for it is Google's side of the fence settling down. Project
Mariner, the consumer experiment, shut down on 4 May 2026, and what
remains at Google for builders is exactly what Anthropic has offered all
along: a computer use capability in the API, where your code owns the
environment and the model supplies the next action. Two vendors, one
architecture, real differences in the details.

Disclosure: this page sits on the wiki of
[invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), an open-source agent in the
same category. It appears in exactly one labeled aside near the end and
nowhere else. Everything about the two vendors traces to their live
documentation, quoted or paraphrased with dates.

## One architecture, two dialects

Both tools run the same loop. Your application captures a screenshot and
sends it with the task; the model returns an action; your code executes
that action against a display you control; a fresh screenshot goes back;
repeat until done. Neither vendor hosts the browser or the desktop for
you. That is the deal in both cases: the capability is a building block,
and the environment, the guardrails and the runtime are yours to build.

The dialects differ in shape. Gemini returns a suggested action as a
function call with coordinates normalized to a 0-999 grid that you scale
to your actual viewport. Claude's current toolset exposes 17 member
tools - screenshot, the click family, drag, scroll, type, key, hold_key,
wait, and a zoom action that captures a region at full resolution -
with pixel coordinates against the screenshot you sent.

## Model lineup and status, as the docs state them

**Google.** The capability began as a dedicated model:
`gemini-2.5-computer-use-preview-10-2025`, introduced 7 October 2025 and
built on Gemini 2.5 Pro. It has since become a tool that mainline models
call. The docs today recommend `gemini-3.8-flash` and list several other
Gemini 3-family models, with the 2.5 preview model kept as the legacy
entry. Two things worth reading closely: the tool rides current flagship
models rather than a frozen specialist, and the docs still carry the
caveat that "as a Preview capability, Computer Use may contain errors
and security vulnerabilities" - their words, worth pricing in.

**Anthropic.** The current toolset version is
`computer_toolset_20260801`, which needs no beta header on the Claude API
and Google Cloud and is supported by the current model families,
including Claude Fable 5.1, Mythos 5.1, Opus 5 and Sonnet 5; some cloud
platforms carry it as beta. Older models (the Opus and Sonnet 4.x lines)
use the earlier `computer_20251124` tool version, which does require a
beta header. The toolset is generally available rather than preview.

If you want a one-line status difference: Anthropic's tool has crossed
into GA on its home platform; Google's is newer to the tool form and
still labels the capability Preview.

## Environments each is built for

Google's docs describe three targets: browser control as the primary and
most mature case, mobile with Android-optimized behavior including app
launching, and desktop via OS-level cursor commands. The original
2.5-era blog was explicit that the model was "primarily optimized for
web browsers" and "not yet optimized for desktop OS-level control";
the desktop support has grown since, but the browser-first center of
gravity remains visible in the docs.

Anthropic's tool is environment-agnostic by construction: it emits
generic display actions, and whatever you can render to a screenshot -
a browser in a container, a full desktop VM - is fair game. Anthropic
publishes a reference container with a virtual display and browser as a
starting point. In practice most deployments of either tool are browser
deployments, which is why this page lives in a browser-agent wiki.

## Benchmarks, quoted rather than adjudicated

Google's launch material claims leading results for browser control on
Online-Mind2Web, WebVoyager and AndroidWorld, and cites 70%+ accuracy at
around 225 seconds latency on Browserbase's Online-Mind2Web harness.
Anthropic's computer use documentation does not publish a comparable
benchmark table on the tool page, so this wiki has no like-for-like
number to set beside Google's, and we are not going to manufacture one.
Treat each vendor's figures as that vendor's claim on that vendor's
chosen harness, and if the decision matters, run both against your own
task; an afternoon of real runs beats every table in this category.

## Cost mechanics

Both are standard token-priced API calls, and in both the dominant cost
is the same: screenshots. Anthropic's docs are usefully concrete here -
roughly 1,000 to 1,800 input tokens per screenshot, a stricter per-image
limit once a request carries more than 20 images, and for the current
toolset a resolution ceiling of 2576 pixels on the long edge. Google's
computer use docs do not publish per-screenshot token figures in the
same way, so budget by measuring a real session. Either way, a long
agentic browse is mostly paying to look at the screen again, and the
loop's step count matters more than the per-token rate.

## Safety posture

The two postures rhyme. Gemini's tool takes per-category safety
configuration - categories such as financial transactions, communication
tools and account creation can be set to require explicit user
confirmation - and offers prompt injection detection as an opt-in flag.
Google's launch material also describes a per-step safety service
assessing each proposed action, and lists categories of action the model
is trained to refuse outright. Claude's toolset ships prompt injection
classifiers that flag suspect content in screenshots and steer the model
to ask for confirmation, and the docs recommend dedicated VMs or
containers with minimal privileges, domain allowlists, keeping
credentials away from the model, and human confirmation for consequential
actions.

The practical reading is the same for both: these tools are built to act
under supervision inside an environment you have deliberately bounded,
and if your plan involves handing one your main browser profile and
walking away, neither vendor's design agrees with your plan.

## The scorecard

| Axis | Gemini computer use | Claude computer use |
|---|---|---|
| Status on 2026-09-03 | Tool available; capability labeled Preview in docs | Current toolset GA, no beta header on Claude API |
| Current naming | Computer use tool; `gemini-3.8-flash` recommended, `gemini-2.5-computer-use-preview-10-2025` legacy | `computer_toolset_20260801`; `computer_20251124` for older models |
| Action encoding | Function call, 0-999 normalized coordinates | 17 member tools, pixel coordinates, includes zoom |
| Environment focus | Browser first; Android-optimized mobile; desktop cursor commands | Whatever you render; reference container published |
| Published benchmark claims | Online-Mind2Web, WebVoyager, AndroidWorld leadership | None on the tool page |
| Screenshot cost guidance | Not published per screenshot | ~1,000-1,800 tokens each, documented limits |
| Prompt injection handling | Opt-in detection flag | Classifiers on by design, confirmation steering |
| Consumer sibling | Gemini Agent; auto browse in Chrome | Claude in Chrome extension |

**An aside from the maintainers, labeled as such:** our project,
[invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), is not a third column of
this table - it is an already-assembled agent rather than an API building
block, it drives its own source-patched Firefox, and it can sit under
either vendor's models via OpenRouter or an MCP assistant. If you were
reading this page because you want the loop without building the loop,
that is the shelf it sits on, next to the others surveyed in
[Open-source computer-use agents](computer-use-agent-open-source.md). We
make it, so audit that claim like everything else here.

## Choosing between them

Pick Gemini's tool if your agents already live on Google's stack, your
tasks are browser-and-Android shaped, and you want the newest mainline
models carrying the capability. Pick Claude's if you want the GA
contract, the finer-grained action vocabulary, and documentation that
prices its own screenshots. Both choices leave every hard operational
question - the environment, the egress, the pacing, what the site sees -
on your desk. Those questions have their own pages here:
[what a page can tell about its visitor](why-does-my-ai-agent-get-blocked.md)
and [when Claude computer use reads as a bot](claude-computer-use-detected-as-bot.md),
which applies nearly unchanged to Gemini-driven environments.

## Short answers to the questions that lead here

**Which is better, Gemini or Claude computer use?** Neither on paper.
Google publishes stronger browser benchmark claims; Anthropic ships the
GA contract and more operational detail. Run both on your task.

**Is Gemini computer use generally available?** The tool is available
via the Gemini API, AI Studio and Vertex AI, and the docs still label
Computer Use a Preview capability. Anthropic's current toolset is GA on
the Claude API.

**What model do I use for Gemini computer use?** The docs recommend
`gemini-3.8-flash` today; `gemini-2.5-computer-use-preview-10-2025` is
the legacy dedicated model.

**Do these replace Project Mariner or Operator?** They are the developer
halves that outlived both consumer products; the consumer replacements
are covered on [Project Mariner is gone](project-mariner-is-gone.md) and
[Is OpenAI Operator still available?](is-openai-operator-still-available.md).

**Can either drive my real browser?** They emit actions; what gets
driven is whatever environment you provide. The vendors' consumer
siblings (auto browse in Chrome, Claude in Chrome) are the
drive-your-own-browser products.

**Do they solve captchas or guarantee access to sites?** No. Both
vendors' safety material points the opposite direction, and sites remain
free to challenge any visitor.

**See also:** [OpenAI Operator vs Claude computer use](openai-operator-vs-claude-computer-use.md)
for the earlier chapter of this series,
[Project Mariner is gone: what replaced it](project-mariner-is-gone.md)
for Google's consumer arc, and
[Open-source computer-use agents](computer-use-agent-open-source.md) for
the pre-assembled open versions of this loop.

## Sources

- [Gemini API: Computer use documentation](https://ai.google.dev/gemini-api/docs/computer-use), fetched 2026-09-03: model naming and recommendations, the action loop, normalized coordinates, environment support, safety categories, the opt-in prompt injection flag, and the Preview caveat quoted above.
- [Google: Introducing the Gemini 2.5 Computer Use model](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/gemini-computer-use-model/), fetched 2026-09-03: the 7 October 2025 introduction, benchmark claims, the Browserbase harness figure, the browser-first optimization quotes, and the per-step safety service.
- [Anthropic: Computer use tool documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool), fetched 2026-09-03: toolset versions, model support and beta-header rules, the 17 member tools, screenshot token figures and image limits, prompt injection classifiers, and the security recommendations.
- [TechSpot on the Project Mariner shutdown](https://www.techspot.com/news/112334-project-mariner-dead-but-google-browser-controlling-ai.html), fetched 2026-09-03, for the 4 May 2026 date.
- [Anthropic: Claude in Chrome general availability](https://claude.com/blog/claude-in-chrome-generally-available), surfaced via search 2026-09-03, for the consumer-sibling row.

---

*Refereed by the maintainers of [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp),
an open-source agent that competes with both tools compared here. Our one
paragraph is labeled; the rest is the vendors' own documentation, cited so
you can check our whistle-blowing against the rulebook.*
