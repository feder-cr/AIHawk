---
title: "Cloudflare and a browser MCP server: what is being read"
description: "A challenge is the visible end of a decision made earlier on. The three layers that feed it, why it works by hand, and the four things that change it."
parent: "When the Agent Gets Blocked"
nav_order: 8
---

# Cloudflare and a browser MCP server

Your agent opens a page and gets an interstitial instead. The same page in your
own browser, on the same machine, loads fine. That asymmetry is the whole
diagnostic, and it points away from the place people look first.

## What is being judged

A challenge is the visible end of a decision that started earlier. Three layers
feed it, and they are not equally weighted.

**The network path.** Where the connection came from and what kind of address it
is. A cloud host is a different category from a domestic connection before any
page has loaded. If your agent runs in a container on a rented machine, this
alone can decide the outcome, and nothing about your browser will change it.

**The connection's own shape.** The properties of the TLS handshake and the
HTTP/2 layer, which vary by client library and build. This is why a scripted
HTTP request and a real browser get different receptions from the same address:
they do not look alike underneath, whatever the headers say.

**The browser and the interaction.** What the page can observe once it runs:
whether the browser reports automation, whether the properties are internally
consistent, and how the pointer and keyboard behaved. A stock automation build
is a recognisable set of choices here.

Notice that the third layer, the one an MCP server can influence, is the last
one. That ordering is the reason most "Cloudflare blocks my MCP server" reports
are not about the MCP server.

## Why it works by hand and not for the agent

Four differences, all of which usually apply at once:

- **Your browser has been alive for months.** History, cookies, a profile that
  has existed. The agent's is minutes old, and with `--isolated` it is seconds
  old.
- **You are already known on that site.** A returning visitor with a session is
  a different proposition from a first request.
- **Your pointer moves like a hand.** The agent's does not, unless the layer
  under it is producing input at the OS level.
- **The build differs.** Your browser is a retail install; the agent's is
  whatever the server launched.

## What changes the outcome

**Warm the session in a real browser and reuse it.** Solve the interstitial
once, by hand, in a headed browser, then start the agent from that saved state.
`--storage-state` on Microsoft's server takes exactly this. It is the highest
value change in this list and the one most people skip because it feels manual.

**Move the address.** If you are on a cloud host, this is the first layer and it
is decisive. [Playwright MCP with a proxy](playwright-mcp-with-a-proxy.md), with
the three leaks that a proxy alone does not close.

**Slow down and vary.** Rate is judged. Identical intervals are judged harder
than fast ones.

**Change the browser, last.** This is where an engine-modified server differs
from a stock one, and it only matters once the first two layers are not the
cause. [Stealth MCP servers compared](stealth-mcp-servers-compared.md).

## What does not change it

Header spoofing on its own. A user-agent string that disagrees with everything
else the browser reports is worse than the honest one, because the disagreement
is itself a signal.

And no MCP server, this one included, gets you past a challenge as a property of
being that server. [Playwright MCP and captchas](playwright-mcp-and-captchas.md)
is the direct statement, and it applies whatever a README says.

## Before you spend a day on this

Ask whether the site has a documented API or an export. On a Cloudflare-fronted
site the answer is often yes, and the sanctioned route is faster to build,
stable across their next configuration change, and permitted. The instinct to
treat the challenge as the problem to solve is what turns an afternoon into a
week.

## Short answers to the questions that lead here

**Why does Cloudflare block my MCP browser?** Most often the address and the
freshness of the session, not the server.

**Does a stealth MCP server get past Cloudflare?** Not as a property. It changes
the third of three layers.

**Will a residential proxy fix it?** If the address was the cause, often. Test
before buying: run the same page from a phone hotspot.

**Can I reuse my own logged-in session?** Yes, and it is the most effective
single change. Save the storage state from a browser where you passed the
challenge.

**Is Turnstile the same as the interstitial?** Related but not identical. The
interstitial is the managed challenge in front of a page; Turnstile is the
widget a site embeds. Both score the session rather than only testing a puzzle.

**See also:** [Playwright MCP session getting blocked](playwright-mcp-blocked.md),
[why an agent gets blocked](why-does-my-ai-agent-get-blocked.md), and
[when the agent gets blocked](guides-when-the-agent-gets-blocked.md).

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10, for `--storage-state`, `--isolated` and the browser options.
- Cloudflare's own public documentation on managed challenges and Turnstile for what each product is.
- The engine wiki's transport-level notes for the second layer above.

---

*Written by a project whose engine sits in the third layer. The page says the
third layer is the last one to look at, which is inconvenient and correct.*
