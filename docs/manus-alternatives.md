---
title: "Manus alternatives"
description: "Manus survived a $2B acquisition and a forced unwinding inside nine months. The alternatives in September 2026: hosted general agents, the open-source stack Manus itself was built on, and what each choice trades away."
parent: "Alternatives and Comparisons"
nav_order: 17
---

# Manus alternatives

People search for a Manus alternative for two different reasons, and they
need different answers. The first group hit a limit in the product: cost,
task fit, or the ceiling any hosted agent has. The second group watched the
ownership news - acquired by Meta for about $2 billion in December 2025,
ordered unwound by Chinese regulators in April 2026, bought back by a
Tencent-led consortium by August - and decided they would rather not build
a workflow on top of a company whose owner changed three times in a year.
Both groups end up at the same fork: another hosted general agent, or open
software you run yourself. This page walks both prongs, plus the section
most Manus comparisons skip: the open-source component that was found doing
Manus's browsing in the first place.

The disclosure that this wiki attaches to every comparison: AIHawk, whose
wiki this is, appears in the open-source list below. Facts about Manus and
every other tool were checked against their own pages or press coverage on
2026-09-03, and the sources are at the bottom.

## The year Manus had, in one paragraph each

**The product worked.** Manus launched on 6 March 2025, went viral off an
agent demo, and by its own blog post of 17 December 2025 had crossed $100M
in annual recurring revenue eight months after launch, with total run-rate
above $125M and growth of more than 20% month over month. The same post
counts more than 80 million virtual computers created for tasks. Whatever
else is true, the demand it found was real.

**The ownership did not hold.** Butterfly Effect, Manus's Chinese-founded,
Singapore-incorporated parent, agreed to a roughly $2 billion acquisition
by Meta in December 2025. Around April 2026, Chinese regulators ordered
the deal unwound on national security grounds, citing technology export
controls and foreign investment rules. By June, Meta had cut Manus off
from its internal systems and halted data sharing; by July, Tencent was in
talks to become the largest outside shareholder; in August, a Tencent-led
consortium including HongShan bought the company back at the original
price and Manus returned to operating as an independent company.

**Why it matters for your choice.** None of that stopped the product from
shipping. But if you are choosing an agent to embed in real workflows, the
episode is a live demonstration of the thing this wiki keeps writing about
hosted agents generally: the product you rent sits inside somebody's
corporate strategy, and regulators, acquirers and boards can all move it
without asking you. With Manus the data question was explicit - part of
the unwinding was Meta halting data sharing between the companies - and
the question "who exactly holds my sessions and files now?" got three
different answers in nine months.

## What Manus is, so the alternatives line up

Manus is a hosted general agent: you give it a goal, it plans, spins up a
cloud virtual computer, browses, writes files, runs code, and comes back
with results. That is a wider brief than a pure browser agent, and it is
the frame for comparing anything to it. An alternative needs to answer at
least the browsing-and-acting half; the closer it also gets to files,
code and long multi-step plans, the closer it is to the whole product.

## browser use vs Manus

This deserves its own section because the two names are entangled in a way
most comparison pages get wrong. In March 2025, shortly after the viral
launch, an X user named Jian got Manus to reveal its sandbox runtime and
found it running Claude Sonnet with access to 29 tools, using the
open-source library browser-use for its web browsing. Manus's chief
researcher Yichao "Peak" Ji confirmed the spirit of the finding, saying
the agent "relies heavily on open-source technologies and wouldn't exist
without open source".

So "browser use vs Manus" is not two rival products; it is a component
versus a product built above that layer. browser-use is an MIT-licensed
Python library, about 112k GitHub stars as of this writing, that connects
an LLM of your choice to a Chromium-family browser. Manus at the time
wrapped that layer, and much else, in a planner, a cloud sandbox and a
subscription. If what you valued in Manus was the browsing, the raw
ingredient is free and self-hostable, and you assemble the rest. If what
you valued was not having to assemble anything, a library is not an
alternative for you, and the hosted rows below are. browser-use has since
grown its own cloud offering as well, which sits somewhere between the
two - [browser-use alternatives](browser-use-alternatives.md) covers its
trade-offs properly.

## The hosted alternatives

**ChatGPT Work** (OpenAI, launched 9 July 2026) is the closest current
big-vendor analogue to Manus's brief: an agent that stays with a
multi-step task across apps and files and returns finished documents and
reports. It is deliverable-shaped rather than
watch-it-click-through-a-site shaped, and it lives entirely inside
OpenAI's product strategy, whose recent churn is documented on
[Is OpenAI Operator still available?](is-openai-operator-still-available.md).

**Gemini Agent** (Google, in the Gemini app since 18 November 2025) does
multi-step tasks that mix live web browsing with Google's tools, launched
for AI Ultra subscribers in the US and spreading down tiers during 2026.
It inherits Project Mariner's browser control work; that lineage and what
else Google offers is on
[Project Mariner is gone: what replaced it](project-mariner-is-gone.md).

Every row here shares the property the Manus story illustrated: your
sessions, files and history live with the vendor, and continuity depends
on decisions you do not get a vote in.

## The open-source route

Stars and licenses below were read from each repository on 2026-09-03.

| Project | Stars | License | What it is |
|---|---|---|---|
| [OpenManus](https://github.com/FoundationAgents/OpenManus) | ~58k | MIT | A community general agent built in Manus's image after the launch, when Manus was invite-only |
| [browser-use](https://github.com/browser-use/browser-use) | ~112k | MIT | The browsing layer itself; the component found inside Manus |
| [Skyvern](https://github.com/Skyvern-AI/skyvern) | ~23k | AGPL-3.0 | Vision-first browser workflows on Playwright, with a managed cloud |
| [Agent S](https://github.com/simular-ai/Agent-S) | ~12k | Apache-2.0 | Whole-desktop computer use, the widest environment of the open set |
| [AIHawk](https://github.com/feder-cr/AIHawk) | ~30k | MIT | Ours: an agent bound to its own source-patched Firefox |

OpenManus is the most literal alternative in the list: it exists because
Manus's launch was invite-only and the community built an open one. The
others each pick a different piece of the brief. What none of them gives
you is Manus's managed cloud sandbox; what all of them give you is code
you can read, run where you like, and keep through anybody's acquisition.

Where AIHawk fits, stated by the people who make it: its bet is the
browser rather than the planner. It drives a Firefox patched at the source
level so that what a page inspects reads as a normal desktop machine, it
runs on your hardware with your OpenRouter key or inside an MCP assistant
you already use, and its scope is browsing tasks, not Manus's
files-and-code sandbox. Windows and Linux only, and no promise of
guaranteed passage anywhere -
[that boundary is documented, not waved away](why-does-my-ai-agent-get-blocked.md).

## How to choose

- **You want the full plan-browse-code-files loop, managed for you.**
  Manus remains the incumbent at that brief; ChatGPT Work is the
  big-vendor rival. Read the ownership paragraph again before you embed
  either deeply.
- **You mostly need the browsing half.** An open browser agent covers it
  on your own machine; start from the table and
  [Choosing an AI browser agent](best-ai-browser-agent.md).
- **You want Manus's shape but open.** OpenManus, plus your own model key
  and patience: community recreations trail the product they mirror.
- **Your tasks touch accounts and data you cannot send to a third party.**
  That rules out the hosted rows entirely, and it is the strongest single
  reason this page's open half exists.

## Short answers to the questions that lead here

**Is Manus still available?** Yes. It operates as an independent company
again after the Meta acquisition was unwound; a Tencent-led consortium
bought it back at the original price in August 2026.

**Did Meta buy Manus?** It announced the roughly $2B acquisition in
December 2025 and completed it, then unwound it after Chinese regulators
ordered divestiture in April 2026 on national security grounds.

**Is Manus built on browser-use?** In March 2025 its sandbox was found
running the open-source browser-use library among 29 tools, and its chief
researcher said the agent "wouldn't exist without open source". The
company has shipped substantially since, so treat that as its documented
starting point rather than a statement about today's internals.

**What is the best free Manus alternative?** OpenManus is the closest in
shape; browser-use is the strongest single component; both are free
software, and you pay only for model tokens.

**Is there a Manus alternative that keeps data on my machine?** Any of the
open-source rows: they run locally, and the model you point them at is
the only outside party you introduce.

**Is Manus free, or is there a free tier?** It is a paid product with a limited
free plan below it, and the paid tiers are where the useful capacity sits.
Prices in this category move often enough that a number written here would be
wrong within a quarter, so check theirs;
[what is actually free in the agent stack](what-is-free-in-the-agent-stack.md)
explains why "free" means four different things across this field and which one
usually applies.

**Claude Code versus Manus?** Not the same shape of thing. Claude Code is a
coding assistant that runs on your machine and can be given tools, including a
browser through MCP; Manus is a hosted autonomous agent you send a task to. If
what you want is an agent that works inside a tool you already run, that is the
MCP route rather than either of them: [the MCP server](mcp-server.md).

**How do I cancel Manus?** Through Manus's own account settings, and their
support is the only accurate source for it - we do not run the product and will
not guess at somebody else's billing flow. If you are leaving because you want
the agent local and keyed to your own provider, the open-source route above is
the part of this page worth reading.

**Is AIHawk a Manus replacement?** Only for the browsing part of the
brief, and we maintain it, so get a second opinion from the table above.

**See also:** [browser-use alternatives](browser-use-alternatives.md) for
the component layer,
[Project Mariner is gone: what replaced it](project-mariner-is-gone.md)
for the parallel story at Google, and
[What is an AI web agent?](ai-web-agent-explained.md) if the category
itself is new to you.

## Sources

- [Manus: $100M ARR, $125M revenue run-rate](https://manus.im/blog/manus-100m-arr), fetched 2026-09-03: the revenue, growth and virtual-computer figures, dated 17 December 2025.
- [TechCrunch: Meta reportedly moves to unwind $2B Manus deal after Beijing's demand](https://techcrunch.com/2026/06/13/meta-reportedly-moves-to-unwind-2b-manus-deal-after-beijings-demand/), fetched 2026-09-03: the December 2025 deal, the April 2026 divestiture order and grounds, the systems cutoff and data-sharing halt, the Singapore relocation.
- [Crypto Briefing: Tencent leads effort to unwind Meta's $2B Manus acquisition](https://cryptobriefing.com/tencent-unwind-meta-manus-acquisition/), fetched 2026-09-03: the Tencent and HongShan consortium and the buyback at the original price. [CNBC: Manus to return as independent company](https://www.cnbc.com/2026/08/11/manus-china-meta-acquisition.html) and [Bloomberg: Tencent in talks to take big Manus stake](https://www.bloomberg.com/news/articles/2026-07-10/tencent-in-talks-to-become-largest-holder-of-manus-ft-reports-mrectviz), surfaced via search 2026-09-03.
- [The Decoder: Chinese AI agent Manus uses Claude Sonnet and open-source technology](https://the-decoder.com/chinese-ai-agent-manus-uses-claude-sonnet-and-open-source-technology/), fetched 2026-09-03: the March 2025 finding and the chief researcher's quotes.
- [Wikipedia: Manus (AI agent)](https://en.wikipedia.org/wiki/Manus_(AI_agent)), surfaced via search 2026-09-03, for the 6 March 2025 release date.
- The [OpenManus](https://github.com/FoundationAgents/OpenManus), [browser-use](https://github.com/browser-use/browser-use), [Skyvern](https://github.com/Skyvern-AI/skyvern), [Agent-S](https://github.com/simular-ai/Agent-S) and [AIHawk](https://github.com/feder-cr/AIHawk) repositories, stars and licenses read via the GitHub API 2026-09-03.
- [9to5Google on Gemini Agent's launch](https://9to5google.com/2025/11/18/gemini-3-pro-app/), fetched 2026-09-03; ChatGPT Work launch date per [Bloomberg](https://www.bloomberg.com/news/articles/2026-07-09/openai-unveils-chatgpt-work-agent-to-field-tasks-for-hours), surfaced via search 2026-09-03.

---

*Written by the maintainers of [AIHawk](https://github.com/feder-cr/AIHawk),
one of the open-source rows above. The Manus ownership saga is genuinely
useful to our argument, which is precisely why every beat of it is cited to
the reporting rather than told from memory.*
