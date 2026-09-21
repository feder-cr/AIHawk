---
title: "Project Mariner is gone: what replaced it"
description: "Google's landing page says Project Mariner shut down on 4 May 2026, with no announcement. Where the capability went - Gemini Agent, Chrome's auto browse, the Gemini API computer use tool - and what to use today."
parent: "Alternatives and Comparisons"
nav_order: 16
---

# Project Mariner is gone: what replaced it

Project Mariner is gone. Google's own landing page for the experiment records
the service as shut down on 4 May 2026, and the capability did not die with
it: it was folded into Gemini Agent inside the Gemini app, into Chrome's
auto browse feature, and into a computer use tool in the Gemini API that
developers can call today. If you subscribed to Google AI Ultra partly for
Mariner, those three are where your money now points. If you wanted the
capability without a Google subscription attached to it, the last section of
this page is the part written for you.

A disclosure before anything else: this page lives on the wiki of
[AIHawk](https://github.com/feder-cr/aihawk_mcp_server), an open-source agent in the
same category, which appears in that last section with the conflict stated.
Every date and claim here was checked against Google's pages or press
coverage of them on 2026-09-03.

## What Mariner was

Google announced Project Mariner in December 2024 as one of the first AI
systems designed to control a web browser on a user's behalf. It worked the
way most of the category still works: take a screenshot, identify the text
and the buttons, click and type the way a person would, repeat until the
task is done. Access came through the Google AI Ultra subscription at $250
per month, which made it one of the most expensive ways to try a browser
agent that has ever been offered.

It was always labeled an experiment, and Google was explicit that it was a
research vehicle rather than a product. That label turned out to be a
precise description of its life expectancy.

## How it ended

There was no blog post and no deprecation window. Press coverage in early
May 2026 noticed that Mariner's landing page had quietly changed to say the
service ended on 4 May 2026, and that the page now points users at other
Google products for the same work: Gemini Agent for complex tasks, and AI
Mode in Search for research-shaped ones. The shutdown landed about two
weeks before Google I/O 2026, which is consistent with a consolidation
ahead of the event rather than a retreat from the category, because the
capability itself shipped again in three places.

If this story sounds familiar, it is because OpenAI ran the same arc first:
Operator shut down in August 2025, its successor agent mode was removed a
year later, and the Atlas browser closed the same month. The pattern is
documented on
[Is OpenAI Operator still available?](is-openai-operator-still-available.md),
and the lesson transfers unchanged: a hosted agent is a feature inside
someone else's product strategy, and it moves when the strategy moves.

## Where the capability went

Three heirs, each a different shape, all verified against Google's material
this session.

### Gemini Agent, for subscribers

Gemini Agent arrived in the Gemini app on 18 November 2025, alongside
Gemini 3 Pro, as an experimental feature for Google AI Ultra subscribers in
the US. Google's own framing was direct about the lineage: it "brings what
Google has learned with Project Mariner to the Gemini app". It handles
multi-step tasks that mix live web browsing with Google's own tools -
inbox triage, reminders, research tasks like pricing a rental car within a
budget - and it asks for confirmation before sending emails, making
purchases, and other consequential actions. During 2026 an Agent Mode
toggle spread further down the subscription tiers.

This is the closest thing to "Mariner, continued" for a person rather than
a developer, with one honest caveat: it is an agent that lives inside
Google's assistant and acts across Google's surfaces, not a general
watch-it-drive-any-site tool you aim wherever you like.

### Auto browse in Chrome, for the browser itself

On 28 January 2026 Google began rolling out auto browse, a Gemini
3-powered agent inside Chrome, to AI Pro and AI Ultra subscribers in the
US. Describe a chore - fill this form, compare these prices, book this
slot - and Chrome opens a visually distinct tab, drives the page itself,
and shows a step-by-step action log in a side panel. There is a daily
limit on agentic actions, purchases and social posts require manual
confirmation, and a Take over task button hands the tab back to you at any
point. It reached Android later in the year.

Auto browse is the most literal answer to "what replaced Mariner",
because it is the same capability in the same browser, now shipped as a
Chrome feature instead of a standalone experiment.

### The computer use tool, for developers

The Gemini API kept the machinery and dropped the product. Google
introduced a dedicated Gemini 2.5 Computer Use model on 7 October 2025,
built on Gemini 2.5 Pro, and described it at the time as primarily
optimized for web browsers and not yet optimized for desktop OS-level
control. Since then the offering has evolved from a dedicated model into a
computer use tool that current mainline models call: the docs today
recommend `gemini-3.8-flash`, list several other Gemini 3-family models,
and keep `gemini-2.5-computer-use-preview-10-2025` as the legacy entry.

The loop is the standard one for the category: you send a screenshot and a
task, the model returns a suggested UI action with coordinates normalized
to a 0-999 grid, your code executes it and sends back a fresh screenshot.
Browser control is the primary target, with Android-optimized mobile
support and OS-level cursor commands for desktop. Safety is configurable
per category - financial transactions and account creation can be set to
require confirmation - and prompt injection detection is available as an
opt-in. Worth knowing before you build on it: Google's docs still label
Computer Use a Preview capability that "may contain errors and security
vulnerabilities", in the docs' own words.

## If you want the capability without the subscription

Everything above requires either a Google subscription or a Google API
bill, and all of it can be reorganized again, as 4 May demonstrated. The
open-source column of this category runs on your machine with a model key
you choose, and it survives vendor strategy changes by not having a vendor.

The maintained options, with stars read from each repository on 2026-09-03:
[browser-use](https://github.com/browser-use/browser-use) (~112k stars,
MIT) is the adoption leader and drives Chromium-family browsers;
[Skyvern](https://github.com/Skyvern-AI/skyvern) (~23k, AGPL-3.0) takes a
vision-first approach on Playwright; [Agent S](https://github.com/simular-ai/Agent-S)
(~12k, Apache-2.0) operates the whole desktop, which makes it the nearest
open relative of Mariner's screenshot generality; and
[AIHawk](https://github.com/feder-cr/aihawk_mcp_server) (~30k, MIT), our own project,
pairs the agent with a Firefox patched at the source level so that what a
page inspects looks like a normal desktop browser rather than an
automation build. Ours is the one claim on this page we cannot make
neutrally, so weigh it accordingly, and note its limits: Windows and Linux
only, and you bring the model.

None of these, ours included, promises a site will not push back. That
boundary belongs to every agent in the category and has
[its own page](why-does-my-ai-agent-get-blocked.md). The fuller landscape,
hosted and open, is on
[OpenAI Operator alternatives](openai-operator-alternatives.md) and
[Open-source computer-use agents](computer-use-agent-open-source.md), and
the two big-vendor APIs that survived their consumer products are compared
on [Gemini computer use vs Claude computer use](gemini-computer-use-vs-claude-computer-use.md).

## Short answers to the questions that lead here

**Is Project Mariner still available?** No. Its landing page records the
service as ended on 4 May 2026.

**Did Google announce the shutdown?** Not with a blog post. The landing
page changed, press coverage noticed, and the page now redirects users to
Gemini Agent and AI Mode.

**What replaced Project Mariner?** For subscribers, Gemini Agent in the
Gemini app (since 18 November 2025) and auto browse in Chrome (since
28 January 2026). For developers, the computer use tool in the Gemini API.

**Was Mariner folded into Gemini?** Yes, in Google's own words: Gemini
Agent "brings what Google has learned with Project Mariner to the Gemini
app", and the Gemini API carries the browser-control tooling.

**Do I still need Ultra to get the capability?** Auto browse reaches AI
Pro as well as Ultra in the US; Gemini Agent launched Ultra-first. The API
route is pay-per-token, and the open-source route needs no Google
subscription at all.

**Is there an open-source equivalent?** Several maintained projects do
the same describe-a-task, watch-the-browser-work loop on your own machine;
see the section above.

**See also:** [Is OpenAI Operator still available?](is-openai-operator-still-available.md)
for the same arc at OpenAI,
[Gemini computer use vs Claude computer use](gemini-computer-use-vs-claude-computer-use.md)
for the developer tooling that outlived both consumer products, and
[Choosing an AI browser agent](best-ai-browser-agent.md) for how to pick a
replacement that will not need replacing.

## Sources

- [TechSpot: Project Mariner is dead, but Google's browser-controlling AI plans live on](https://www.techspot.com/news/112334-project-mariner-dead-but-google-browser-controlling-ai.html), fetched 2026-09-03: the 4 May 2026 date from Google's landing page, the $250 Ultra tier, the December 2024 announcement, and the Gemini Agent / AI Mode redirection.
- Additional shutdown coverage surfaced via search 2026-09-03: [Digital Trends](https://www.digitaltrends.com/computing/google-pulls-the-plug-on-project-mariner-the-ai-agent-that-browsed-the-web-like-a-human/), [Technobezz](https://www.technobezz.com/news/google-quietly-shut-down-project-mariner-on-may-4-without-public-announcement) and [Android Headlines](https://www.androidheadlines.com/2026/05/google-shuts-down-project-mariner-ai-agent.html).
- [9to5Google: Gemini app rolling out Gemini 3 Pro and Gemini Agent](https://9to5google.com/2025/11/18/gemini-3-pro-app/), fetched 2026-09-03: the 18 November 2025 launch, Ultra-only US availability, the Mariner lineage quote, and the confirmation behavior.
- [9to5Google: Chrome rolling out Gemini 3-powered auto browse](https://9to5google.com/2026/01/28/chrome-gemini-auto-browse/), fetched 2026-09-03: the 28 January 2026 rollout, AI Pro and Ultra tiers, daily action limits, the action log and Take over task.
- [Google: Introducing the Gemini 2.5 Computer Use model](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/gemini-computer-use-model/), fetched 2026-09-03, and the [Gemini API computer use docs](https://ai.google.dev/gemini-api/docs/computer-use), fetched 2026-09-03: model naming, the action loop, environment support, safety options and the Preview caveat.
- The [browser-use](https://github.com/browser-use/browser-use), [Skyvern](https://github.com/Skyvern-AI/skyvern), [Agent-S](https://github.com/simular-ai/Agent-S) and [AIHawk](https://github.com/feder-cr/aihawk_mcp_server) repositories, star counts and licenses read via the GitHub API 2026-09-03.

---

*Maintained by the team behind [AIHawk](https://github.com/feder-cr/aihawk_mcp_server),
an open-source AI web agent. We benefit when readers conclude that hosted
agents are impermanent, which is exactly why every date above traces to
Google's own pages or to coverage of them rather than to our say-so.*
