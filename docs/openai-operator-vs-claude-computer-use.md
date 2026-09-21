---
title: "OpenAI Operator vs Claude computer use"
description: "A hosted browser product that no longer exists versus an API building block that does: the two big-vendor approaches to browser agents compared on architecture, availability and cost."
parent: "Alternatives and Comparisons"
nav_order: 4
---

# OpenAI Operator vs Claude computer use

This comparison is lopsided in a way most pages about it do not admit: one
side no longer exists. OpenAI Operator shut down on 31 August 2025, and the
agent mode that absorbed it was removed from ChatGPT in August 2026. Claude
computer use is alive, documented, and available on the Claude API today. So
the honest version of this page is not a feature race - it is an explanation
of the two architectures, because the architectural fork they represent is
still the fork every current tool sits on.

Disclosure: this page is on the wiki of
[AIHawk](https://github.com/feder-cr/aihawk_mcp_server), an open-source agent that
appears in the closing section. Claims about OpenAI trace to their pages and
mainstream reporting; claims about Anthropic trace to their live
documentation, all retrieved 2026-09-03.

## Two architectures, not two versions of one thing

**Operator was a hosted product.** You subscribed to ChatGPT Pro, described a
task, and OpenAI's model drove a browser session for you, doing what its
successor's users later described as "visual, GUI-based actions": look at the
rendered page, click, type, hand control back for logins. The environment,
the browser, and the model all belonged to OpenAI. You brought a task and a
subscription.

**Claude computer use is an API tool, not a product.** Anthropic's
documentation is explicit about the division of labor: "When you use computer
use, Claude doesn't directly connect to this environment. Instead, your
application: receives Claude's tool use requests, translates them into actions
in your computing environment, captures the results... and returns these
results to Claude." Claude sends actions like `screenshot`, `left_click`, and
`type` with pixel coordinates; your code executes them against a display you
own, typically a container running a virtual display and a browser; the loop
repeats until the task is done.

The consequence of the fork is everything else on this page. A hosted product
is convenient and disposable - Operator's own history proved the second part.
An API building block is work up front and yours afterwards: the environment,
the browser choice, the guardrails, and the operating costs are all decisions
you get to make and have to make.

## Availability, verified this session

**Operator: unavailable.** No tier of ChatGPT restores it or its agent-mode
successor; OpenAI's help pages point long multi-step tasks at ChatGPT Work,
and browser-based agentic work at the ChatGPT desktop app and Chrome
extension. The full churn timeline is on
[Is OpenAI Operator still available?](is-openai-operator-still-available.md).
For developers, OpenAI's own entry in this architecture is the computer use
tool in the Responses API - out of its research-preview phase and generally
available, driven by current models such as `gpt-5.6`, and notably the same
shape as Anthropic's approach: a screenshot loop over an environment you
provide.

**Claude computer use: generally available on the API.** The current toolset
version (`computer_toolset_20260801`) needs no beta header and is supported by
the current model families on the Claude API and the major cloud platforms,
some marked beta. Anthropic publishes a reference environment (a container
with a virtual display and browser) as a starting point.

**The consumer-side counterpart.** If what you actually wanted was
Operator-as-a-user rather than computer-use-as-a-developer, Anthropic's
equivalent is Claude in Chrome, generally available to paid plans since
26 August 2026, which drives the Chrome you already run rather than a hosted
browser.

## What each costs

Operator's cost model was a subscription: it launched inside ChatGPT Pro. Its
API descendant, the computer use tool, is priced like any Responses API call:
standard token pricing for the model that drives it, multiplied by the
screenshot-heavy context a computer-use loop consumes.

Claude computer use is standard API token pricing with no special rate, and
the practical cost driver is screenshots: Anthropic's docs put each one at
roughly 1,000 to 1,800 tokens and recommend keeping no more than about twenty
in context. A long browsing session is mostly paying to re-look at the screen.
That is not a criticism of Anthropic; it is the tax the
screenshot-and-coordinates architecture itself levies, and OpenAI's version
pays it too.

## What each can and cannot do

**The screenshot loop is general.** Anything visible on a display is in
scope: browsers, desktop applications, dialogs. Agent benchmarks reflect the
generality: OpenAI reported 38.1% on OSWorld for its computer-use model, and
Anthropic's docs devote most of their length to environment setup and safety
because the tool will do whatever the pixels afford.

**Both vendors bound their agents deliberately.** Anthropic's docs recommend
sandboxed VMs, allowlisted domains, avoiding handing over credentials, and
human confirmation for consequential actions, and state that classifiers
screen for prompt injection and can steer the model to ask for confirmation.
Operator similarly declined categories of task while it existed. If your use
case sits near those edges, a vendor agent will keep declining, and that is
by design rather than a defect.

**Neither controls what the website sees very well.** A hosted browser or a
reference container is a recognizable environment:
[a headless server machine answers a page's questions differently from a
desktop](https://github.com/feder-cr/invisible_playwright/wiki/headless-browser-agent-on-a-server),
and [an agent's pacing is its own signal](ai-agent-timing-signal.md).
With computer use you at least own the environment and can improve it; with a
hosted product you could not.

## The scorecard

| Axis | Operator (historical) | Claude computer use (current) |
|---|---|---|
| Status on 2026-09-03 | Shut down 2025-08-31; successor mode removed 2026-08 | Available on the Claude API, current toolset GA |
| Shape | Consumer product | API tool inside your agent loop |
| Environment | OpenAI-hosted browser | Yours: VM/container, display, browser |
| Model | OpenAI's, fixed | Claude models, your API key |
| Cost | Subscription tier | Per token; screenshots dominate |
| Who fixes it when it breaks | Nobody, now | You, which cuts both ways |

## The third option

There is a paragraph missing from most Operator-versus-Claude pages, and it is
the one that changes the decision: you do not have to choose between a vendor
product and building a computer-use loop from scratch. Open-source agents ship
the loop already built, run on your machine, and take your model key -
browser-use and Skyvern drive Chromium-family browsers, Agent S3 does the
whole desktop, and our own AIHawk pairs the agent with a Firefox patched at
the C++ level so the browser itself presents a normal desktop fingerprint
instead of a reference container's. None of them, ours included, guarantees a
site will not push back - [that boundary is documented, not waved
away](why-does-my-ai-agent-get-blocked.md) - but all of them survive a vendor
reorg, which is more than one side of this page's title can say. The survey is
at [Open-source Operator-style agents](openai-operator-open-source.md).

## Short answers to the questions that lead here

**Which is better, Operator or Claude computer use?** The question expired:
Operator no longer exists. Its architectural heirs at OpenAI are ChatGPT's
built-in agentic browsing and the now generally available computer use API.

**Is Claude computer use a product I can just use?** Not by itself: it is an
API tool, and you supply the environment and the agent loop. The
consumer-shaped version is Claude in Chrome, on paid plans.

**Can Claude computer use control a real browser?** Yes: whatever browser you
put in the environment it controls, via screenshots and coordinates.

**Which is cheaper?** Not comparable in kind: Operator was a subscription;
computer use is per-token, with screenshots as the dominant cost. For steady
workloads, measure a real session before assuming either direction.

**Do either of them solve captchas or guarantee access to sites?** No, and
both vendors' materials point the other way: bounded action, confirmation for
consequential steps, and sites remain free to challenge any visitor.

**What if I want this without a big-vendor dependency?** The open-source
route in the previous section; start with
[Choosing an AI browser agent](best-ai-browser-agent.md).

**See also:** [Is OpenAI Operator still available?](is-openai-operator-still-available.md)
for the shutdown timeline this page leans on,
[OpenAI Operator alternatives](openai-operator-alternatives.md) for the whole
field, and [Open-source computer-use agents](computer-use-agent-open-source.md)
for the screenshot-loop architecture in open source.

## Sources

- [Anthropic: computer use tool documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool), retrieved 2026-09-03; quotes, toolset version, model support, screenshot token figures and safety guidance are from this page.
- [Wikipedia: OpenAI Operator](https://en.wikipedia.org/wiki/OpenAI_Operator), retrieved 2026-09-03, for launch and shutdown dates and the OSWorld figure.
- [OpenAI help: ChatGPT agent](https://help.openai.com/en/articles/11752874-chatgpt-agent), surfaced via search 2026-09-03, and the [OpenAI computer use guide](https://developers.openai.com/api/docs/guides/tools-computer-use), fetched 2026-09-03: generally available, driven by current models, migration section from `computer-use-preview`.
- [OpenAI community: "Agent Mode was removed with no real replacement"](https://community.openai.com/t/agent-mode-was-removed-with-no-real-replacement/1389601), retrieved 2026-09-03.
- Coverage of Claude in Chrome's general availability, surfaced via search 2026-09-03, including [Engadget on Cowork in the Chrome sidebar](https://www.engadget.com/2235919/claude-cowork-can-now-run-in-a-chrome-sidebar/).

---

*Written while maintaining [AIHawk](https://github.com/feder-cr/aihawk_mcp_server), an
open-source agent that competes with both approaches described here. That is
exactly why the quotes come from the vendors' own pages: grade our homework
against their material, not our summary of it.*
