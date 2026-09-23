---
title: "browser-use alternatives"
description: "browser-use is the category leader and deserves it. The verified reasons people still look past it - Chromium-only scope, the CDP detection surface, a cloud-shaped roadmap - and what actually sits next to it."
parent: "Alternatives and Comparisons"
nav_order: 5
---

# browser-use alternatives

Start with the part a page like this usually buries: browser-use is good. It
is the most adopted open-source browser agent by a wide margin - roughly 112k
GitHub stars when read on 2026-09-03, MIT licensed, actively developed, backed
by a $17M seed round in March 2025, with support for multiple model providers
under your own keys. If you have no specific reason to look elsewhere, it is
the reasonable default, and nothing below changes that.

This page is for people who do have a specific reason. It goes through the
reasons that are real and verifiable, then the alternatives, one of which is
ours: this wiki belongs to [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), so
read the comparison knowing who wrote it. No claim here about browser-use goes
beyond what its own repository and configuration surface show.

## The verified reasons people look for an alternative

### It is Chromium-family only

browser-use drives a Chromium-family browser, and its configuration surface
says so structurally: the browser-profile code is Chrome logic - locating a
Chrome executable, deriving Chrome user-data directories, Chromium channel
types. There is no Firefox path. That is a coherent engineering choice, not a
flaw, but it means every browser-use session inherits the Chromium automation
stack whole: the same build type, the same driving protocol, the same
well-studied tells. If your problem is specifically that this stack is being
recognized, no browser-use setting reaches it. The mechanics are documented on
the engine wiki:
[what browser-use configuration can and cannot change](browser-use-getting-blocked.md)
and [why a bundled Chromium is not Chrome](https://github.com/feder-cr/invisible_playwright/wiki/chromium-is-not-chrome).

### The detection surface, and where it actually lives

The most common shape of the complaint is "works on my laptop, challenged on
the server". That is usually not browser-use's fault: a server has no GPU, a
container font set, no audio device, and an IP with a datacenter reputation,
and no agent framework fixes machine-level facts. But the parts that are the
stack's own - a stock automation build, driven over CDP, with
[the protocol itself observable in ways a page can probe](https://github.com/feder-cr/invisible_playwright/wiki/bidi-vs-cdp-detection) -
travel with browser-use wherever it runs. Before switching tools over this,
read [why an agent gets blocked](why-does-my-ai-agent-get-blocked.md) and
attribute your failure correctly; switching agents does not change your IP.

### The center of gravity is moving cloudward

The project's README today gives most of its space to Browser Use Cloud: a
hosted agent with rotating egress, integrations, persistence, and a unified
API key that also unlocks the company's own optimized models. Reasonable
business, genuinely useful for teams that want managed scale. But if you came
to open source to keep the agent local, keyed to providers you chose, some of
the ecosystem's energy is now pointed somewhere you do not want to go. The
open MIT core still works standalone; you should just know which direction
the wind blows. As of 2026-09-03 the split is explicit on browser-use's own
site, which sells two commercial products, "Browser Use Agents" and "Browser
Infrastructure" (managed cloud browsers for your own code) - the
[infrastructure layer itself is explained here](cloud-browser-infrastructure-for-ai-agents.md).

### What is not on this list

No invented grievances: we found no verified problem with browser-use's agent
quality, its maintenance tempo, or its community, and its issue tracker is the
normal noise of a project its size. If someone tells you browser-use is
"broken" or "always detected", ask for the same specificity this page tries
to practice.

## The first alternative is configuring browser-use better

Boundary honesty: if you are on browser-use and mostly happy, try its own
levers before switching. Point `executable_path` at a real installed Chrome
rather than the bundled build, and give `user_data_dir` a profile with real
history - the second one addresses the thing hardest for any fresh browser to
fake, which is having existed yesterday.
[What a persistent profile fixes and breaks](https://github.com/feder-cr/invisible_playwright/wiki/persistent-profiles)
covers the trade. If that clears your problem, keep the ecosystem you already
know and close this tab.

## The alternatives, honestly labeled

**Skyvern** ([repo](https://github.com/Skyvern-AI/skyvern), ~23k stars,
AGPL-3.0). Vision-LLM driven workflows on Playwright: it reads the rendered
page rather than depending on selectors, which trades token cost for
resilience to layout changes. Still Chromium underneath, so it is an
alternative agent, not an alternative detection surface. Mind the AGPL if you
embed it.

**Agent S3** ([repo](https://github.com/simular-ai/Agent-S), ~12k stars,
Apache-2.0). A different scope entirely: an open computer-use framework that
operates the whole desktop, reporting 72.6% on OSWorld. If your automation
keeps leaving the browser for spreadsheets and dialogs, this is the switch
that actually addresses it.

**invisible_playwright_mcp** ([repo](https://github.com/feder-cr/invisible_playwright_mcp), ~30k stars, MIT) -
ours. The differentiator against browser-use is the browser, not the agent
loop: invisible_playwright_mcp drives a Firefox patched at the C++ level (the
invisible_playwright engine), a real browser presenting a normal desktop
fingerprint, rather than a stock automation build driven over CDP. Identity is
derived from a seed, so a failing run replays exactly. It plugs into an MCP
assistant you already run (Claude Code, Claude Desktop, Cursor) or runs its
own local UI with an OpenRouter key.

Where browser-use covers more, plainly: it has several times our community
and integrations, it supports macOS and we do not (Windows and Linux only),
its cloud exists if you want managed scale and we have none, and its
documentation surface for the agent loop is larger. And the hardened browser
is an advantage only where the browser was your problem: it does not repair
an IP's reputation, robotic pacing, or a site's rate limits, and we make no
promise of non-detection anywhere - the engine wiki documents
[how to test the difference yourself](https://github.com/feder-cr/invisible_playwright/wiki/how-to-test-bot-detection)
rather than asking you to believe a claim.

## How to decide in one pass

- **Happy with browser-use, occasional challenge pages:** real Chrome binary,
  used profile, better egress. Stay.
- **Layouts keep breaking your flows:** Skyvern.
- **The task leaves the browser:** Agent S3.
- **The browser itself is what gets recognized, or you want the agent inside
  your MCP assistant, or you need runs to replay deterministically:** invisible_playwright_mcp,
  conflict of interest noted.
- **You want a hosted service:** Browser Use Cloud or Skyvern's cloud - both
  vendors' own material describes them; we did not test either.

## Short answers to the questions that lead here

**What is the best alternative to browser-use?** Wrong axis. Skyvern changes
the perception approach, Agent S3 changes the scope, invisible_playwright_mcp changes the
browser. Pick by which of those three is your actual problem.

**Does browser-use work with Firefox?** Its configuration expects a
Chromium-family browser; the profile and channel machinery is Chrome logic.
If you need Firefox, you need a different stack.

**Is browser-use detectable?** Any automation stack is a set of observable
choices, and a stock Chromium over CDP is the most-studied set there is. But
most "detected" reports are machine and IP facts no framework fixes.
Attribute first, switch second.

**Is browser-use free?** The MIT core is. Model tokens cost whatever your
provider charges, and the cloud is a paid product.

**Is invisible_playwright_mcp better than browser-use?** Not in general, and this is our own
wiki saying so. It is better specifically where a real-fingerprint Firefox
and reproducible identity matter, and worse on ecosystem size, macOS, and
managed hosting.

**See also:** [Choosing an AI browser agent](best-ai-browser-agent.md) for
the full decision framework,
[OpenAI Operator alternatives](openai-operator-alternatives.md) for the
hosted end of the field, and
[AI browser agents vs traditional scraping](ai-browser-agents-vs-traditional-scraping.md)
for whether you need an agent at all.

## Sources

- The [browser-use repository](https://github.com/browser-use/browser-use), retrieved 2026-09-03: stars, license, description, model support and the cloud material.
- [browser-use.com](https://browser-use.com/), retrieved 2026-09-03, for the two commercial products named above.
- [SiliconANGLE: Browser Use raises $17M](https://siliconangle.com/2025/03/23/browser-use-raises-17m-help-steer-ai-agents-internet/), surfaced via search 2026-09-03.
- [browser-use getting blocked: what you can and cannot change](browser-use-getting-blocked.md), this wiki's own analysis, which reads `BrowserProfile`'s fields from browser-use's source.
- The [Skyvern](https://github.com/Skyvern-AI/skyvern), [Agent-S](https://github.com/simular-ai/Agent-S) and [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) repositories, retrieved 2026-09-03.

---

*Written while maintaining [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), a
direct competitor to the tool this page is about. That is why the first
section praises browser-use, the second tells you how to stay on it, and every
critical claim points at its own repository.*
