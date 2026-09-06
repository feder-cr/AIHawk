---
title: "browser-use getting blocked: what you can and cannot change"
description: "What browser-use's BrowserProfile can actually change when the agent gets blocked, what no configuration reaches, the agent-rhythm tell, and the MCP route to a different engine."
parent: "When the Agent Gets Blocked"
nav_order: 5
---


# browser-use getting blocked: what you can and cannot change

If your browser-use agent works on your laptop and gets challenge pages on a server,
the problem is usually not the agent and not the prompt. It is the browser it drives
and the machine that browser runs on - and only some of that is reachable from
configuration.

This page is the sorted version: what `BrowserProfile` actually exposes, which of
those settings are worth using, what no setting can reach, the tell that is specific
to agent-driven sessions, and the honest answer about swapping in a different
engine. All of the browser-use specifics below were re-checked against
`browser_use/browser/profile.py` on 2026-09-03.

## What browser-use gives you to change

`BrowserProfile` is browser-use's configuration surface: a template of launch and
context arguments handed to the browser session. The fields that matter for blocks:

| Field | What it does |
|---|---|
| `executable_path` | which browser binary to launch - documented as a Chromium-based executable |
| `channel` | a Chromium channel: `chromium`, `chrome`, the beta/dev/canary variants, the Edge variants |
| `user_data_dir` | a persistent profile directory |
| `proxy` | proxy settings (server, bypass, username, password) |
| `headless` | headless or headed |
| `args` | extra command-line arguments |
| `cdp_url` | attach to an already-running browser over CDP instead of launching one |

That is a real set of levers, and two of them are worth more than people use them
for.

### Point `executable_path` at your real Chrome

The field expects a Chromium-family browser - every value in the `channel` enum is
Chromium, Chrome or Edge, and there is no Firefox among them. Its practical use is
pointing at your installed Chrome rather than the bundled test Chromium.
[Those are not the same browser](https://github.com/feder-cr/invisible_playwright/wiki/chromium-is-not-chrome):
the codec set differs, the branding differs, and a real Chrome install is a far more
common thing to be than a bundled build.

### Give `user_data_dir` a past

Pointing this at a profile that has genuinely been used is the single
highest-value change available in the configuration, because it is the only one
that addresses history rather than hardware. An agent starting from an empty
profile is a browser that has never been anywhere, which is
[most of why a fresh browser scores badly](https://github.com/feder-cr/invisible_playwright/wiki/recaptcha-v3-score).
The traps - profile lock-in, pairing the profile with a consistent identity - are
covered in
[what a persistent profile fixes and breaks](https://github.com/feder-cr/invisible_playwright/wiki/persistent-profiles).

One thing not to over-credit: browser-use's default launch arguments already include
automation masking (`--disable-blink-features=AutomationControlled` and related
flags). That hides the crudest driver marker; it is surface-level, and it does
nothing for anything in the next section.

## What no configuration reaches

Everything about the machine. None of the fields above changes any of these, and on
a server all of them are true at once:

- **No GPU**, so WebGL reports
  [a software renderer](https://github.com/feder-cr/invisible_playwright/wiki/webgl-renderer-strings).
- **A container font set** that
  [does not match the claimed platform](https://github.com/feder-cr/invisible_playwright/wiki/headless-fonts-differ).
- **No audio device**, so
  [the audio values fall back to defaults](https://github.com/feder-cr/invisible_playwright/wiki/audiocontext-fingerprinting).
- **A screen with no taskbar** and
  [a default resolution](https://github.com/feder-cr/invisible_playwright/wiki/screen-size-headless-tells).
- **Codec support** that
  [describes a slim build rather than a desktop install](https://github.com/feder-cr/invisible_playwright/wiki/codec-fingerprinting).
- **A TLS handshake**
  [decided by the network stack before any page-level setting exists](https://github.com/feder-cr/invisible_playwright/wiki/ja3-ja4-tls-fingerprint).

This is why "works on my laptop, blocked in Docker" is the most common shape of the
problem: the agent is identical in both places, and the machine is not.
[The container version of the list](https://github.com/feder-cr/invisible_playwright/wiki/playwright-docker-detection)
goes through it in order.

## The tell that is specific to agent-driven sessions

browser-use sessions carry one signal ordinary scraping does not: the rhythm of the
think-act loop. The agent reads the page, calls a model, waits, then acts - so its
pauses cluster around model latency rather than reading speed, its pointer is still
during the pause, its actions land dead centre because coordinates come from page
structure rather than a hand, and it wastes no actions. No stealth setting in any
framework fixes this, because it is produced above the browser.
[The timing signal has its own page](ai-agent-timing-signal.md).

It also gives you the cheapest diagnostic there is: note *when* the block arrives. A
block at the first page load points at the machine or the address - the lists above.
A block that arrives after a few interactions points at behaviour or volume, and
[an agent's retry loop is usually the volume half](agent-retry-loops-rate-limits.md).

## Can I use a stealth Firefox with browser-use?

No, and it is better to say so plainly than to hand you a workaround that does not
work. browser-use drives its browser over the Chrome DevTools Protocol - the
configuration even exposes `cdp_url` for attaching to a running one - and its
executable and channel handling is Chromium-only. A Firefox binary in
`executable_path` is not a drop-in: the driver would be speaking a protocol the
browser does not implement.

The route that does accept a different engine is MCP, where the browser is a set of
tools rather than a CDP endpoint. Microsoft's
[Playwright MCP server](https://playwright.dev/docs/getting-started-mcp) takes
`--browser=firefox` (checked 2026-09-03), and
[the MCP server](mcp-server.md)
goes further: it ships a Firefox patched at the C++ level as the engine behind its
tools, so an MCP-speaking assistant - Claude Code, Claude Desktop, Cursor - drives a
browser whose fingerprint is set in its own source. Disclosure: that server and
this wiki have the same maintainer, and it is the route
[AIHawk](https://github.com/feder-cr/AIHawk) is built on.

State the trade fairly, because it is a real one: going to MCP means leaving
browser-use's agent loop and using an MCP-capable agent instead. Which side of the
trade matters depends on where your blocks come from - the first-load-versus-
after-interactions test above tells you. If your blocks are machine-shaped, the
engine matters and MCP is the door to a different engine. If they are
rhythm-shaped or volume-shaped, no engine swap will save you, in browser-use or
anywhere else.

## Conclusion

browser-use exposes enough configuration to fix the two things configuration can
fix: which browser binary runs, and whether the profile has a past. Point it at a
real Chrome and a used profile and you have taken the available wins. Everything
else divides into two piles. The machine-level tells are shared with every
automation tool and are fixed by changing the machine or the engine - neither of
which is a browser-use setting, and the engine route runs through MCP, not through
`executable_path`. The agent-rhythm and volume tells are specific to agents and are
not fixed by any fingerprint work at all. One observation - when does the block
arrive? - tells you which pile you are in.

## Short answers to the questions that lead here

**Why is my browser-use agent blocked on a server but not locally?** Because the
server has no GPU, few fonts, no audio device and a default screen, and the agent
is identical in both places. The machine changed, not the code.

**Can I set a custom browser in browser-use?** Yes: `executable_path` in
`BrowserProfile`, and it expects a Chromium-family binary. Pointing it at your real
installed Chrome rather than the bundled Chromium is worth doing.

**Can I use a stealth Firefox with browser-use?** No. It drives over CDP and its
browser handling is Chromium-only. The route that accepts a different engine is
MCP, with a different agent on top.

**Does a persistent profile help?** Yes, more than most settings, because it is the
only one that gives the browser a history. Read the traps first.

**Why do blocks arrive after a few actions rather than immediately?** That points
at behaviour or volume rather than fingerprint: the agent's rhythm and its retry
traffic are both visible only once it starts acting.

**Does adding a proxy fix it?** It changes where you come from, and that is all. If
the browser is announcing a server through its GPU, fonts and screen, the address
was not the problem.

## Sources

- `browser_use/browser/profile.py` on the browser-use main branch, retrieved
  2026-09-03: the `BrowserProfile` fields in the table above, the Chromium-only
  `channel` values, `executable_path` documented as a Chromium-based executable,
  `cdp_url`, and the automation-masking default launch arguments.
- [Playwright's MCP documentation](https://playwright.dev/docs/getting-started-mcp),
  retrieved 2026-09-03, which lists `firefox` among the supported `--browser`
  values - confirming the MCP route, unlike browser-use, is not Chromium-only.
- The machine-level surfaces are each documented on their own engine-wiki page,
  linked inline above.

**See also:** [the timing signal AI agents give off](ai-agent-timing-signal.md) and
[agent retry loops and rate limits](agent-retry-loops-rate-limits.md) for the two
agent-specific tells, [why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md)
for the order to check things in, and [browser-use alternatives](browser-use-alternatives.md)
for the wider landscape.

---

*Written while maintaining [AIHawk](https://github.com/feder-cr/AIHawk), which runs
on the patched-Firefox engine described above. This page says that engine does not
fit browser-use, because it does not, and a guide claiming otherwise would waste
your afternoon.*
