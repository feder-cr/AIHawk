---
title: "OpenAI Operator alternatives"
description: "Operator shut down in August 2025 and its successor inside ChatGPT was removed a year later. The real alternative landscape in September 2026, hosted and open source, compared by the axes that matter."
parent: "Alternatives and Comparisons"
nav_order: 1
---

# OpenAI Operator alternatives

If you are looking for an Operator alternative in September 2026, you are really
looking for the capability Operator demonstrated: you describe a task in plain
language and an AI drives a real browser until the task is done. Operator itself
shut down on 31 August 2025. The ChatGPT agent mode that absorbed it was removed
in early August 2026, and Atlas, OpenAI's standalone AI browser, shut down on
9 August 2026. So "alternative" no longer means "a substitute for a living
product". It means the whole category, and the category has real options.

One disclosure before the list: this page lives on the wiki of
[invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), which appears below as one of
those options. Every claim about another tool here traces to that tool's own
site, repository, or documentation, retrieved on 2026-09-03, and where another
tool covers more than ours does, the page says so.

## What Operator was, briefly

Operator launched as a research preview for ChatGPT Pro subscribers in the US
on 1 February 2025. It drove a web browser to fill forms, place orders, and
click through pages on the user's behalf. In July 2025 OpenAI folded its
"visual, GUI-based actions" into ChatGPT agent, and the standalone preview was
shut down on 31 August 2025. The successor churned again in 2026. The full
timeline, with what OpenAI offers today, is on
[Is OpenAI Operator still available?](is-openai-operator-still-available.md) -
this page will not repeat it.

## The axes that separate the alternatives

Every tool below answers the same three questions differently, and the answers
matter more than any feature list:

- **Open source or hosted.** Can you read the code and run it yourself, or is
  it a service that can change or disappear under you? Operator's own history
  is the argument for caring about this.
- **Who brings the model.** Some tools are inseparable from one vendor's
  model. Others take your API key and let you pick.
- **What browser it drives, and how.** A hosted browser in a vendor's cloud, a
  screenshot-and-coordinates loop over a VM, a stock automation build of
  Chromium driven over an automation protocol, or a browser patched at the
  source level to present a normal desktop fingerprint. When a site inspects
  its visitor, this axis is the one that decides what the site sees.

## The landscape at a glance

Star counts and statuses were read from each project's repository or vendor
pages on 2026-09-03 and will drift.

| Tool | Open source | Model | What it drives | Where it runs |
|---|---|---|---|---|
| ChatGPT agentic browsing (desktop app + Chrome extension) | No | OpenAI's, via subscription | Your Chrome, or browsing inside the ChatGPT app | Your machine + OpenAI |
| Claude in Chrome | No | Anthropic's, via subscription | Your installed Chrome | Your machine |
| Claude computer use (API tool) | Tool spec is public; you build the rest | Anthropic models, your API key | Whatever environment you provide | Your infrastructure |
| [browser-use](https://github.com/browser-use/browser-use) | Yes, MIT (~112k stars) | Your key, or their cloud and models | Chromium-family browser via automation protocol | Your machine or their cloud |
| [Skyvern](https://github.com/Skyvern-AI/skyvern) | Yes, AGPL-3.0 (~23k stars) | Your key, or their cloud | Playwright-driven browser, vision-LLM based | Your machine or their cloud |
| [Agent S3](https://github.com/simular-ai/Agent-S) | Yes, Apache-2.0 (~12k stars) | Your key | The whole desktop GUI, not only a browser | Your machine |
| [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) | Yes, MIT (~30k stars) | Your OpenRouter key, or your MCP assistant's model | Its own Firefox, patched at the C++ level | Your machine |

## The vendor routes that remain

**OpenAI's own answer** to "I want what Operator did" is no longer a product
named anything like Operator. Agentic browsing now lives inside the ChatGPT
desktop app and the ChatGPT Chrome extension, where Atlas's capabilities were
folded when it shut down, and ChatGPT Work (launched 9 July 2026) handles
longer multi-step tasks across apps and files. Users on OpenAI's own forum have
pointed out that none of these reproduces the old agent mode's interactive
website navigation exactly. Developers can build with the computer use tool in
the Responses API, now generally available and driven by current models (the
old `computer-use-preview` model has a documented migration path to it).

**Anthropic's answer** comes in two shapes. Claude in Chrome, the browser
extension, became generally available for paid Claude plans on 26 August 2026
and drives the Chrome you already have. For builders, the computer use tool in
the Claude API is a screenshot-and-coordinates loop where you supply the whole
environment. [OpenAI Operator vs Claude computer use](openai-operator-vs-claude-computer-use.md)
compares those two architectures properly.

Both routes are good if you are already paying that vendor and your tasks fit
inside their safety envelope. Neither is open source, and both tie the agent to
one vendor's models.

## The open-source field

**browser-use** is the category leader by adoption: roughly 112k stars, MIT
licensed, a $17M seed round in March 2025, and a hosted cloud. It drives a
Chromium-family browser and supports multiple model providers with your own
keys. If you want the largest community and the most examples, start there.
[browser-use alternatives](browser-use-alternatives.md) covers where its
trade-offs bite and what sits next to it.

**Skyvern** (~23k stars, AGPL-3.0) takes a vision-first approach: LLMs and
computer vision map what is on screen to actions instead of relying on brittle
selectors, on top of Playwright. It also runs a managed cloud with features the
self-hosted version does not include.

**Agent S3** from Simular (~12k stars, Apache-2.0) is a computer-use framework
rather than a browser agent: it operates the whole desktop GUI and reports
72.6% on the OSWorld benchmark, which its paper describes as above the human
baseline on that suite. If your task spans desktop applications and not just
the web, it is the strongest open option we found.

The deeper survey of open repositories, including two unrelated projects that
both answer to the name "open operator", is on
[Open-source Operator-style agents](openai-operator-open-source.md).

## Where invisible_playwright_mcp fits, stated by its maintainer

invisible_playwright_mcp is open source (MIT), takes your OpenRouter key or plugs into an MCP
assistant you already run (Claude Code, Claude Desktop, Cursor), and its
differentiator is the browser itself: it drives a Firefox patched at the C++
level so that what a page inspects looks like a normal desktop browser, not a
stock automation build. The engine's mechanics are documented on the
[invisible_playwright wiki](https://github.com/feder-cr/invisible_playwright/wiki/do-websites-know-you-are-using-a-script).

The honest limits: it is Windows and Linux only, no macOS. You bring the model
and pay for tokens. A hardened browser does not repair a bad egress IP, robotic
pacing, or a per-account limit, and nothing here promises you will not be
detected - [that boundary has its own page](why-does-my-ai-agent-get-blocked.md).
And it has a fraction of browser-use's community.

## How to choose

- **Already paying for ChatGPT or Claude, task is occasional?** Use that
  vendor's browsing agent and stop reading.
- **Need code you can read, run, and keep?** The open-source field above.
- **Largest ecosystem and Chromium is fine?** browser-use.
- **Tasks that leave the browser for the desktop?** Agent S3.
- **Sites inspect your browser and a stock automation build gets challenged?**
  That is the case invisible_playwright_mcp's engine was built for, with the caveat paragraph
  above in full force.
- **Undecided?** Run two of them against your actual task for an afternoon.
  A live trial beats this table, and we wrote the table.

The broader decision framework, beyond replacing Operator specifically, is on
[Choosing an AI browser agent](best-ai-browser-agent.md).

## Short answers to the questions that lead here

**What replaced OpenAI Operator?** Inside OpenAI: ChatGPT agent (July 2025),
then agentic browsing in the ChatGPT desktop app and Chrome extension plus
ChatGPT Work (2026). Outside OpenAI: the tools in the table above.

**Is there a free Operator alternative?** The open-source agents are free
software; you still pay for model tokens unless you run a local model where a
tool supports one. invisible_playwright_mcp's UI requires its key outright (since 0.4.0), on the
argument that an agent without a model is not an agent at all.

**Which alternative is most like Operator?** browser-use's cloud or Skyvern's
cloud are closest in shape, a hosted browser doing your task. On your own
machine, any of the open agents above.

**Do any of these guarantee they will not be blocked?** No, and distrust any
page that says otherwise. The browser's fingerprint is one factor; the IP,
the account, and the pacing are yours either way.

**Can I use Claude or GPT models with the open-source agents?** browser-use
and Skyvern take multiple providers' keys. invisible_playwright_mcp takes any OpenRouter model
id, or inherits whatever model your MCP assistant runs.

**See also:** [Is OpenAI Operator still available?](is-openai-operator-still-available.md)
for the full shutdown timeline,
[Open-source Operator-style agents](openai-operator-open-source.md) for the
repo-by-repo survey, and
[OpenAI Operator vs Claude computer use](openai-operator-vs-claude-computer-use.md)
for the two big-vendor architectures side by side.

## Sources

- [Wikipedia: OpenAI Operator](https://en.wikipedia.org/wiki/OpenAI_Operator), for the launch, deprecation and shutdown dates, retrieved 2026-09-03.
- [OpenAI help: ChatGPT agent](https://help.openai.com/en/articles/11752874-chatgpt-agent) and [OpenAI help: Evolving Atlas into ChatGPT](https://help.openai.com/en/articles/20001371-evolving-atlas-into-chatgpt-for-browser-based-agentic-work), surfaced via search 2026-09-03.
- [OpenAI community: "Agent Mode was removed with no real replacement"](https://community.openai.com/t/agent-mode-was-removed-with-no-real-replacement/1389601), retrieved 2026-09-03.
- [TechCrunch on the Atlas shutdown](https://techcrunch.com/2026/07/09/openai-is-shutting-down-atlas-but-its-ai-browser-ambitions-are-still-growing/) and [Bloomberg on the ChatGPT Work launch](https://www.bloomberg.com/news/articles/2026-07-09/openai-unveils-chatgpt-work-agent-to-field-tasks-for-hours), surfaced via search 2026-09-03.
- [OpenAI computer use guide](https://platform.openai.com/docs/guides/tools-computer-use), surfaced via search 2026-09-03.
- [Anthropic: computer use tool documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool), retrieved 2026-09-03; Claude in Chrome general availability per coverage surfaced via search the same day.
- The [browser-use](https://github.com/browser-use/browser-use), [Skyvern](https://github.com/Skyvern-AI/skyvern), [Agent-S](https://github.com/simular-ai/Agent-S) and [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) repositories, retrieved 2026-09-03.
- [SiliconANGLE on browser-use's $17M seed](https://siliconangle.com/2025/03/23/browser-use-raises-17m-help-steer-ai-agents-internet/), surfaced via search 2026-09-03.

---

*Written while maintaining [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), an
open-source AI web agent in exactly this space. The comparison above is the one
we would want to read ourselves, which is why the disclosure sits at the top
and every claim about another tool traces to that tool's own material.*
