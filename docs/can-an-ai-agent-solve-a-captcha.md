---
title: "Can an AI agent solve a captcha? The honest answer"
description: "Usually no, and not because the model is not smart enough. Most challenges ask no question at all. What the score reads, and the three routes that work."
parent: "When the Agent Gets Blocked"
nav_order: 9
---

# Can an AI agent solve a captcha?

**Usually no, and the reason is not that the model is not smart enough.** A
modern challenge is not a puzzle waiting to be answered. It is a score computed
from your session, and most of the time it shows nothing to read at all.

This page is the honest version of a question that has a lot of dishonest
answers, including in this product category.

## The intuition, and where it breaks

The intuition is reasonable: models can read distorted text and identify traffic
lights, therefore an agent should be able to click through. Three things break
it.

**Most challenges do not ask a question.** reCAPTCHA v3 has no interactive
element. Turnstile in its usual mode has a widget that resolves without asking
anything. Both produce a score from the address, the connection, the browser's
observable properties and the interaction history. There is no image, so vision
is irrelevant.

**When there is a puzzle, answering it is not the transaction.** The site does
not accept your answer. It accepts a token, issued by the challenge provider's
client-side code, which observed how the answer was produced. Right answer,
wrong provenance, no token.

**The challenge is usually a symptom.** Being shown one at all is the signal. It
means something about the session was already unusual, and the same something
will be true on the next page. Solving instances of a symptom is an infinite job.

There are narrow exceptions. Old-style text-in-an-image challenges on small
sites are readable, and some accessibility paths exist for reasons that have
nothing to do with automation. Neither is what people are hitting in 2026.

## What the score is made of

Roughly in order of weight:

- **Where the request came from.** Address type and reputation. A cloud host is
  a category, not a detail.
- **How the connection looks underneath.** Handshake and protocol-level
  properties that differ between a real browser build and a scripted client.
- **What the browser reports.** Automation flags, and whether the reported
  properties agree with each other.
- **How the interaction went.** Pointer paths, timing, whether the form was
  filled faster than a person can read it.

An agent can influence the last two and, with a proxy, the first. It cannot
argue with any of them by being clever.

## The three routes that work

**Remove the reason.** Better address, slower and less regular pacing, a browser
that is not a stock automation build. In that order, because that is the order
of weight. [Why an agent gets blocked](why-does-my-ai-agent-get-blocked.md) has
the attribution procedure, which is worth ten minutes before any of this.

**Use the sanctioned route.** Many sites people fight have an API, a feed or an
export. Faster to build, stable, and permitted. This is the answer that feels
like losing and is usually correct.

**Put a person in the loop, once.** For an occasional interactive flow: solve it
by hand in a headed browser, save the session state, and let the agent continue
from there. This is legitimate, it is what the state-saving options in these
servers are for, and it is the pattern most working setups actually use.

## What this project does, and does not

[AIHawk](https://github.com/feder-cr/AIHawk) drives a Firefox patched at the C++
source. That changes what a page can observe about the browser, which is one of
four inputs above, and the third by weight. **It does not solve captchas, and we
do not claim non-detection.**

We are explicit because several tools in this category are not. A repository
description promising a proven bypass of a named challenge product, or an AI
solver for another, is a claim; we have not verified those and do not repeat
them. [Stealth MCP servers compared](stealth-mcp-servers-compared.md) names them
with that caveat attached.

The practical cost of the overpromise falls on the reader: someone whose real
problem is a datacenter address installs a tool sold on defeating challenges,
and it does not work, because the tool was never addressing their cause.

## Short answers to the questions that lead here

**Can an AI agent bypass a captcha?** Not as a capability. It can avoid
triggering one, which is a different and more achievable thing.

**Can an AI agent pass a captcha?** Sometimes, when the challenge is scoring a
session that looks fine. That is passing by not being suspicious, not by solving.

**Does browser-use or Playwright MCP solve captchas?** No. Neither claims to.

**Are there tools that solve them?** Paid services exist that route challenges
to human workers or specialised models. They are outside what this project does
and outside what it will advise on.

**Why do I get a captcha when I use an agent but not by hand?** Fresh session,
different address, and machine-speed interaction. Usually all three.

**Is it against the rules to get around one?** A challenge is a site saying it
does not want this traffic. The site's terms are the place that answers this,
and the sanctioned route usually exists.

**See also:** [Playwright MCP and captchas](playwright-mcp-and-captchas.md),
[Cloudflare and a browser MCP server](cloudflare-and-playwright-mcp.md), and
[when the agent gets blocked](guides-when-the-agent-gets-blocked.md).

## Sources

- Public documentation from the challenge providers on scoring-based challenges (reCAPTCHA v3, Turnstile), which describe the mechanism in their own words.
- The engine wiki's explainers on the individual challenge products, written to describe how they work rather than how to defeat them.

---

*Written by a project that sells a browser, in a category where claiming to
defeat challenges is normal marketing. Saying no here costs us the search
result and keeps the page true.*
