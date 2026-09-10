---
title: "Stealth MCP servers compared: Camoufox, nodriver, Patchright"
description: "The MCP servers built on modified engines rather than a stock automation build: what each engine really changes, and which claims we could not verify."
parent: "Alternatives and Comparisons"
nav_order: 27
---

# Stealth MCP servers compared

Most browser MCP servers drive a stock automation build. A small, young cluster
does not: wrappers around Camoufox, nodriver and Patchright, plus this project.
This page is what separates them, and it starts with the disclosure, because
one of the entries is ours and because two of the others make claims we could
not check.

## What the engines are, before the wrappers

The wrapper is thin. What you are choosing is the engine.

**Camoufox** is a Firefox fork with anti-fingerprinting work done in the C++
source and driven over Juggler rather than CDP. Around 11.1k stars when the
2026 stealth-browser survey read it in August 2026, and actively pushed. The
significant property is where the changes live: in the engine, so a page cannot
observe the patching the way it can observe a script that rewrites properties
after load.

**nodriver** is the successor line to undetected-chromedriver: Chromium, driven
over CDP directly with no WebDriver layer. Around 4.6k stars in the same survey,
with its last push in May 2026, which is worth knowing before you build on it.

**Patchright** is a patched Playwright driver: same API you know, with the
best-known Playwright tells removed. Around 4.1k stars, pushed in August 2026.
It is the smallest change of the three and the easiest to adopt, because your
existing code keeps working.

**This project's engine** is
[invisible-playwright](https://github.com/feder-cr/invisible_playwright), a
Firefox patched at the C++ source with the identity derived from a seed, so two
runs with the same seed present the same browser.

Camoufox and this engine are the same family of idea and are genuine
alternatives to each other. nodriver and Patchright are the Chromium answer to
the same question.

## The wrappers

**mcp-camoufox** exposes Camoufox over MCP with a large tool surface, installed
through npx. **mcp-stealth-chrome** wraps nodriver together with a TLS-spoofing
HTTP client. **patchright-mcp-lite** is the opposite design: four tools, one
job. **AIHawk** is ours, and the server ships inside the same package as the
interface: [the MCP server](mcp-server.md) has the config block.

Tool count is the axis these wrappers advertise on and it is the least useful
one. A hundred tools is a hundred descriptions in the model's context on every
turn, and a larger set to choose wrongly from. What matters is whether the model
can read state without scripting, reach what selectors cannot, and fall back to
JavaScript for the remainder. [How the tools are shaped](mcp-tool-design.md)
argues that in full.

## The claims we could not verify

Two of these projects advertise capabilities in their own repository text that
we did not test and are not repeating as fact: a "proven" one-line bypass of a
specific challenge product, and a vision-based solver for another. They may
work. We have not run them, and a claim in a README is a claim.

We are explicit about this because the same restraint applies to us in the other
direction: **AIHawk does not solve captchas and does not promise
non-detection.** A patched engine changes what the browser looks like. It does
not read a challenge for you, it does not repair a datacenter IP's reputation,
and it does not slow down an agent that is clicking faster than a person could.
[Can an AI agent solve a captcha](can-an-ai-agent-solve-a-captcha.md) is the
longer answer, and it is the same answer we would give about anyone's tool.

If you are evaluating any server in this category, the useful test is not
reading claims. It is running the same page through two of them from the same
IP, and this wiki's engine documents
[how to test that yourself](https://github.com/feder-cr/invisible_playwright/wiki/how-to-test-bot-detection).

## Choosing

- **You are already on Playwright and want the obvious tells gone:**
  Patchright, because your code does not change.
- **You want Firefox with engine-level work and a mature project:** Camoufox,
  or ours. Camoufox has the larger community; ours has seed-derived identity and
  the agent interface in the same package.
- **You are committed to Chromium and want no WebDriver layer:** nodriver, with
  the maintenance tempo noted.
- **You want the smallest thing that works:** patchright-mcp-lite.
- **Your problem is not the browser:** none of these. Read
  [why an agent gets blocked](why-does-my-ai-agent-get-blocked.md) and check the
  IP, the pacing and the rate limit first. That is the majority case, and this
  entire page is about the minority one.

## Short answers to the questions that lead here

**What is a stealth browser MCP server?** An MCP server whose browser is a
modified engine rather than a stock automation build, so what a page can observe
about the browser differs.

**Is there a Camoufox MCP server?** Yes, as a community wrapper. Camoufox itself
is the engine, not the server.

**Does a stealth MCP server get past Cloudflare?** Not as a property of being a
stealth MCP server. [Cloudflare and Playwright MCP](cloudflare-and-playwright-mcp.md)
goes through what a challenge is actually reading.

**Is Patchright the same as playwright-stealth?** No. playwright-stealth patches
the page from JavaScript after load; Patchright patches the driver. The engine
wiki has the distinction in detail.

**Which one is safest to depend on?** Judge by push date and issue tempo, not by
star count. The survey figures above are dated for that reason.

**See also:** [Choosing an MCP server for browser automation](best-mcp-server-for-browser-automation.md),
[Playwright MCP alternatives](playwright-mcp-alternative.md), and
[open-source agentic browsers](agentic-browser-open-source.md).

## Sources

- [Stealth browsers 2026: nodriver, Camoufox, Patchright](https://proxycove.com/en/blog/stealth-browsers-2026-nodriver-camoufox-patchright-benchmark), retrieved 2026-09-10, for star counts and last-push dates as of August 2026.
- [RobithYusuf/mcp-camoufox](https://github.com/RobithYusuf/mcp-camoufox) and [RobithYusuf/mcp-stealth-chrome](https://github.com/robithyusuf/mcp-stealth-chrome), retrieved 2026-09-10, for the wrappers and their own claims.
- [patchright-mcp-lite](https://glama.ai/mcp/servers/dylangroos/patchright-mcp-lite), retrieved 2026-09-10.
- [invisible-playwright](https://github.com/feder-cr/invisible_playwright), this project's engine.

---

*Written while maintaining one of the servers listed. The section naming the
unverified claims applies to us first: the paragraph saying what AIHawk does not
do is there so the rest of the page can be read as description rather than
advertising.*
