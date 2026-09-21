---
title: "Is OpenAI Operator still available?"
description: "No. Operator shut down on 31 August 2025, its successor agent mode was removed in August 2026, and Atlas closed the same month. The verified timeline and what to use instead."
parent: "Alternatives and Comparisons"
nav_order: 3
---

# Is OpenAI Operator still available?

No. Operator was shut down on 31 August 2025, about seven months after it
launched. The capability moved into ChatGPT agent, which was itself removed in
early August 2026. Atlas, OpenAI's standalone AI browser, shut down on
9 August 2026. As of this page's writing (September 2026), nothing OpenAI
offers carries the Operator name, and the closest living equivalents are
agentic browsing inside the ChatGPT desktop app and Chrome extension, the
ChatGPT Work agent, and a developer-only computer-use API.

That is the short answer. The rest of this page is the verified timeline,
because the churn confused a lot of people, and then the practical part: what
someone who wants that capability today can actually use.

A note on who is telling you this: this page lives on the wiki of
[AIHawk](https://github.com/feder-cr/aihawk_mcp_server), an open-source agent in the same
space, which appears once in the alternatives section below with that conflict
declared.

## The timeline, date by date

Every row was checked against OpenAI's own pages or mainstream reporting on
2026-09-03.

| Date | Event |
|---|---|
| 23 January 2025 | Operator announced as a research preview. |
| 1 February 2025 | Available to ChatGPT Pro subscribers in the US. |
| July 2025 | ChatGPT agent launches, merging Operator's "visual, GUI-based actions" with Deep Research; Operator's deprecation is announced. |
| 31 August 2025 | Standalone Operator shuts down. |
| October 2025 | Atlas launches: a Chromium-based AI browser, macOS first. |
| 9 July 2026 | ChatGPT Work launches: an agent for multi-step work across apps and files. |
| Early August 2026 | ChatGPT agent mode removed; OpenAI's help pages direct users to ChatGPT Work. Users on the OpenAI forum note it arrived without an advance deprecation notice. |
| 9 August 2026 | Atlas shuts down; its agentic browsing folds into the ChatGPT desktop app, the ChatGPT Chrome extension, and Codex. |

Three product generations in nineteen months, each replacing the last. If you
built a workflow on any of them, you have already migrated twice.

## What OpenAI offers today instead

**Agentic browsing in ChatGPT.** The Atlas shutdown notice says its
browser-based agentic work moved into the ChatGPT desktop app and the ChatGPT
Chrome extension. This is the nearest thing to Operator's original shape that
OpenAI still ships: the assistant can browse and act inside a browser context,
under your subscription.

**ChatGPT Work.** Launched 9 July 2026, described by OpenAI and press coverage
as an agent that gathers context across your apps and files and returns
finished documents, spreadsheets and reports, staying with a project for
hours. It is aimed at deliverables, not at interactively clicking through an
arbitrary website. The most-viewed forum thread about the agent mode removal
makes exactly that complaint: Work does not replicate "spawned a virtual
computer, opened a real browser, visually interpret rendered websites, clicked
through interfaces".

**The computer-use API.** For developers, OpenAI's computer use tool in the
Responses API drives a click-type-scroll loop over screenshots. It left its
research-preview phase: the current guide documents the tool (named
`computer`) driven by the current model ids it lists (`gpt-5.6-sol` and
`gpt-6-astra`, checked 2026-09-04),
with a migration path from the old `computer-use-preview` model. It is a
building block, not a product: you supply the browser or VM it acts on.

Whether any of these is "Operator, still available" depends on which half of
Operator you wanted: the hosted convenience survives in ChatGPT's browsing
mode; the watch-it-click-through-any-site agent, per OpenAI's own users, does
not have a direct heir inside ChatGPT today.

## If you want what Operator did, today

The capability did not die with the product; it moved out into the rest of
the field.

**Another vendor's browser agent.** Claude in Chrome became generally
available for paid Claude plans on 26 August 2026 and drives the Chrome you
already have. The architectural comparison with Operator's approach is on
[OpenAI Operator vs Claude computer use](openai-operator-vs-claude-computer-use.md).

**The open-source route.** Several maintained open projects do the
describe-a-task, watch-the-browser-work loop on your own machine with your own
model key: browser-use (~112k stars), Skyvern (~23k), Agent S3 (~12k) for
whole-desktop tasks, and AIHawk (~30k), our own, whose particular bet is
driving a Firefox patched at the source level so the browser reads as a normal
desktop machine rather than an automation build. The repo-by-repo survey with
licenses and trade-offs is
[Open-source Operator-style agents](openai-operator-open-source.md), and the
full hosted-plus-open landscape is
[OpenAI Operator alternatives](openai-operator-alternatives.md).

One thing to carry over from the Operator era regardless of route: no agent,
hosted or open, is guaranteed passage on every site. Operator itself had
sites it would not touch, and every alternative inherits some version of the
same boundary - [why an agent gets blocked](why-does-my-ai-agent-get-blocked.md)
is about which parts of that are the browser's fault and which are yours.

## Why this keeps happening, briefly

Reading the announcements together, a pattern is visible and worth naming
without editorializing: OpenAI has treated the browser agent as a feature in
search of its right container - standalone product, ChatGPT mode, standalone
browser, then back into ChatGPT and an extension. Coverage of the Atlas
shutdown quotes the conclusion that the browser is "a feature, not the
destination". For users, the practical lesson is less about OpenAI than about
hosted agents generally: a capability you rent can be reorganized out from
under you without a deprecation window, which the August 2026 agent-mode
removal demonstrated. It is the strongest argument the open-source column of
this wiki has, and it was written by events, not by us.

## Short answers to the questions that lead here

**Is OpenAI Operator still available?** No. It shut down 31 August 2025.

**Did ChatGPT agent replace it, and is that still there?** It did, in July
2025, and no: agent mode was removed in early August 2026. OpenAI's help
pages now point to ChatGPT Work.

**What happened to ChatGPT Atlas?** Shut down 9 August 2026, with agentic
browsing folded into the ChatGPT desktop app, the Chrome extension, and
Codex. It never left macOS while it lived, per coverage of the shutdown.

**Can I still access Operator if I pay for Pro?** No tier restores it. The
subscription route today is ChatGPT's built-in browsing agent and ChatGPT
Work.

**Is there an API version?** Yes: the computer use tool in the Responses
API, now generally available and driven by current models, where you provide
the environment it controls.

**What is the closest replacement I can run myself?** An open-source browser
agent with your own model key - see
[Open-source Operator-style agents](openai-operator-open-source.md).

**See also:** [OpenAI Operator alternatives](openai-operator-alternatives.md)
for the full option landscape,
[OpenAI Operator vs Claude computer use](openai-operator-vs-claude-computer-use.md)
for the two vendor architectures, and
[Choosing an AI browser agent](best-ai-browser-agent.md) for how to pick a
replacement that will not need replacing.

## Sources

- [Wikipedia: OpenAI Operator](https://en.wikipedia.org/wiki/OpenAI_Operator), retrieved 2026-09-03, for the January/February 2025 and 31 August 2025 dates and the August 2026 agent removal note.
- [OpenAI help: ChatGPT agent](https://help.openai.com/en/articles/11752874-chatgpt-agent) and [OpenAI help: Evolving Atlas into ChatGPT for browser-based agentic work](https://help.openai.com/en/articles/20001371-evolving-atlas-into-chatgpt-for-browser-based-agentic-work), surfaced via search 2026-09-03.
- [OpenAI community: "Agent Mode was removed with no real replacement"](https://community.openai.com/t/agent-mode-was-removed-with-no-real-replacement/1389601), retrieved 2026-09-03, for the removal, the "use Work" guidance, and the quoted capability description.
- [TechCrunch: OpenAI is shutting down Atlas](https://techcrunch.com/2026/07/09/openai-is-shutting-down-atlas-but-its-ai-browser-ambitions-are-still-growing/) and [Search Engine Land: OpenAI sets Aug. 9 end date for ChatGPT Atlas](https://searchengineland.com/openai-chatgpt-atlas-deprecation-482003), surfaced via search 2026-09-03.
- [Bloomberg: OpenAI launches ChatGPT Work](https://www.bloomberg.com/news/articles/2026-07-09/openai-unveils-chatgpt-work-agent-to-field-tasks-for-hours) and [The Next Web on the same launch](https://thenextweb.com/news/openai-chatgpt-work-agent-launch), surfaced via search 2026-09-03.
- [OpenAI computer use guide](https://developers.openai.com/api/docs/guides/tools-computer-use), fetched 2026-09-03: the tool is generally available, driven by current models, with a migration section from the old `computer-use-preview`.

---

*Kept current by the maintainers of [AIHawk](https://github.com/feder-cr/aihawk_mcp_server),
an open-source AI web agent. We have an interest in the answer being "no", so
every date above traces to OpenAI's own pages or mainstream reporting rather
than to us.*
