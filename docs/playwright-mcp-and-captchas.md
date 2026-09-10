---
title: "Playwright MCP and captchas: what actually gets you past"
description: "A model reading the image is not the answer, because most challenges show nothing to read. What the score is made of, and the three routes that do work."
parent: "When the Agent Gets Blocked"
nav_order: 7
---

# Playwright MCP and captchas

An agent driving a browser meets a challenge and stops. The obvious next thought
is that a vision model could just read it. That thought is wrong for reasons
worth knowing, and the useful routes past a challenge are not the ones people
try first.

## Why a model reading the image is not the answer

**Most modern challenges are not an image test.** reCAPTCHA v3 and Turnstile in
its managed mode present no puzzle at all most of the time. They score the
session from signals gathered before and during the page: the address, the
connection, how the pointer moved, how quickly the form was filled, whether the
browser has a history. A model with perfect vision has nothing to look at,
because the decision was already made.

**When there is a visible puzzle, the puzzle is the smallest part.** The token
the server accepts is produced by client-side code that observed the interaction
that produced it. Getting the right answer to the question is not the same as
having the token issued, which is why "the model can read the letters" does not
translate into a working session.

**And the challenge is often the symptom.** A challenge shown to you and not to
your colleague on the same site is a statement about your address and your
pacing. Solving it does not change either, so it comes back.

## What actually gets you past one

**Fix what triggered it.** The three levers, in the order they pay:

- **The address.** A datacenter address is pre-judged.
  [Playwright MCP with a proxy](playwright-mcp-with-a-proxy.md) covers the
  routing and the three leaks that survive it.
- **The pacing.** Forty pages in forty seconds is not a person.
- **The browser.** A stock automation build has observable properties that a
  hand-driven browser does not. This is the axis where engine-modified servers
  differ, and it is the third of three for a reason:
  [why an agent gets blocked](why-does-my-ai-agent-get-blocked.md).

**Use the sanctioned door.** A surprising share of the sites people fight have
an API, a data export, or a documented feed. It is faster, it does not break
next month, and it is allowed. This is the answer people skip because it feels
like giving up, and it is usually the correct one.

**Hand the challenge to a person.** If the flow is interactive and occasional,
a headed browser where you solve it yourself, once, and then keep the session,
is entirely legitimate. `--storage-state` on Microsoft's server exists partly
for this shape: solve it in a real browser, save the state, start from there.

## What this project does not do

**AIHawk does not solve captchas, and does not promise non-detection.** The
engine is a Firefox patched at the C++ source, which changes what a page can
observe about the browser. It does not read a challenge, does not fetch a token,
and does not repair an address's reputation or an agent's rhythm.

We say this plainly because the category does not. Several MCP servers in this
space advertise a bypass of a named challenge product or an AI solver as a
headline feature. Those may work; we have not verified them and we do not repeat
them as fact. [Stealth MCP servers compared](stealth-mcp-servers-compared.md)
names them with the same caveat.

The reason for the restraint is not only honesty. A tool that promises to defeat
a challenge attracts people whose actual problem is an address, and it fails
them, loudly, in a way that is nobody's fault but the promise's.

## Short answers to the questions that lead here

**Can Playwright MCP solve a captcha?** No. It can drive a browser to a page
that has one.

**Can a vision model solve it?** Sometimes it can answer the visible puzzle.
That is usually not what the site is measuring, and it is not what issues the
token.

**Why do I get a challenge every time and my browser does not?** Fresh profile,
different address, and a rhythm no person produces. In that order of likelihood.

**Is there an MCP server that gets past Cloudflare?** Several claim it. Treat a
claim as a claim, and read
[Cloudflare and Playwright MCP](cloudflare-and-playwright-mcp.md) for what the
challenge is reading.

**Is it legal to bypass a captcha?** Depends where you are and what the site's
terms say, and it is a question for the site's terms rather than for us. The
practical answer is that a challenge is a site telling you it does not want this
traffic, and there is usually a sanctioned route that does not involve arguing
with it.

**See also:** [can an AI agent solve a captcha](can-an-ai-agent-solve-a-captcha.md)
for the category-level answer,
[Playwright MCP session getting blocked](playwright-mcp-blocked.md) for
attributing the failure, and
[when the agent gets blocked](guides-when-the-agent-gets-blocked.md).

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10, for `--storage-state` and the capability model.
- The engine wiki's explainers on the challenge products, which describe the mechanisms rather than defeating them.

---

*Written by a project that would sell more if it claimed otherwise. The section
saying what AIHawk does not do is the point of the page, not a disclaimer at the
bottom of it.*
