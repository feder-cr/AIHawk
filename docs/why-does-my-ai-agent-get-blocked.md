---
title: "Why does my AI agent get blocked?"
description: "Four independent layers block agents - browser fingerprint, IP reputation, volume, behavioral rhythm. Which your framework can fix, and the order to check them in."
parent: "When the Agent Gets Blocked"
nav_order: 1
---


# Why does my AI agent get blocked?

Because of one of four things, and they are genuinely independent: the browser's
fingerprint, the IP's reputation, the volume of requests, or the rhythm of the
actions. A site can flag any one of them on its own, fixing one buys you nothing on
the other three, and most wasted debugging time in this area comes from fixing the
wrong layer, usually by swapping tools when the problem was the network, or swapping
networks when the problem was the tool.

This page is the map: what each layer is, which ones an agent framework can fix for
you, which ones nothing can fix for you, and the order to check them in. It stays at
the level of an agent user; the mechanism deep-dives live on the
invisible_playwright wiki and are linked where they belong, starting with the
overview of the whole model,
[how do websites detect bots](https://github.com/feder-cr/invisible_playwright/wiki/how-do-websites-detect-bots).

## Layer 1: the browser fingerprint

Before your agent takes a single action, the page has already read the browser. Two
kinds of reading happen. On the network, the TLS handshake itself has a shape, the
order of ciphers and extensions offered, and that shape identifies the software
sending it before any page content loads; automation stacks that are not real
browsers, or modified ones, produce shapes no retail browser produces. The
mechanics are on the wiki:
[JA3 and JA4, why a TLS fingerprint cannot be patched](https://github.com/feder-cr/invisible_playwright/wiki/ja3-ja4-tls-fingerprint).
In the page, JavaScript reads dozens of properties, canvas rendering, GPU strings,
fonts, screen values, timezone, and joins them. It is not looking for any single
rare value; it is looking for values that disagree with each other, a browser that
claims one operating system while rendering like another, or the known defaults of
an automation build.

**Can the framework fix it? Yes.** This is the one layer that is entirely the
tooling's job, because the fingerprint is a property of the browser the agent
ships. It is also where agent frameworks differ most: an agent driving a stock
automation browser inherits that browser's tells. AIHawk's browser is a real
Firefox patched at the C++ level (the invisible_playwright engine), built so that
what both kinds of reading see is a consistent, ordinary Firefox, and that is its
honest advantage on exactly this layer. Stated just as plainly: it does nothing for
the three layers below. A clean fingerprint on a flagged IP, over a rate limit, or
acting with machine rhythm still gets blocked, and any tool telling you otherwise
is describing one layer as if it were all four.

## Layer 2: IP and network reputation

Every request carries the address it came from, and the address carries history and
context you cannot see: what network announces it (a datacenter range or a
residential one), what else has been done from it, and how many other clients are
using it right now. Sites score this before your browser is even considered, and a
bad score blocks a perfect browser. The full mechanism, including why the network
operator matters more than the individual address, is on the wiki:
[ASN and IP reputation in bot detection](https://github.com/feder-cr/invisible_playwright/wiki/asn-and-ip-reputation-in-bot-detection).

**Can the framework fix it? No, and be suspicious of anything claiming to.** The
exit address is supplied by you: your machine's connection, or a proxy you
configure. What a good framework does is honor the choice cleanly; AIHawk's
`--proxy` option, for instance, routes egress through the proxy you give it and
aligns timezone and locale to the exit so the browser does not contradict its own
address. Choosing an exit worth using, an address that is not a datacenter range
and not shared with a crowd, is a purchasing decision, not a software feature.

## Layer 3: volume and rate

Sites count. Requests per minute from one address, pages per session, sessions per
account, and they act on thresholds long before anything sophisticated runs. Agents
trip this layer in a specific, self-inflicted way: retries. An agent that fails a
step tends to try again immediately, and a loop of failures becomes a burst of
identical requests, which reads as exactly what it is. One blocked response can
become a hard block purely through the agent's own persistence; that failure mode
has its own page,
[agent retry loops and rate limits](agent-retry-loops-rate-limits.md).

**Can the framework fix it? Only partly.** A framework can cap retries and space
its own requests, and an assistant driving a browser over MCP can be told to slow
down. But volume is mostly decided by what you ask for: "check these 400 pages" is
a volume decision made in the prompt, and no tooling downstream of the prompt can
unmake it. Rate limits are also legitimate; the responsible reading of a 429
response is to honor it, not to engineer around it.

## Layer 4: behavioral rhythm

Even with a clean browser, a clean address and modest volume, the way an agent acts
is measurable. An LLM loop emits actions with machine-regular gaps clustered around
the model's latency, pointers that arrive without travel, forms filled with no
reading time. Humans are ragged; loops are not. This signal needs no fingerprint
and no reputation database, just timestamps. The full anatomy is on
[the timing-signal page](ai-agent-timing-signal.md).

**Can the framework fix it? Partly, and honestly only partly.** The browser layer
can make individual actions human-shaped; AIHawk's engine, for example, moves the
pointer along curved paths rather than teleporting it, and the agent acts through
real input events rather than setting values from JavaScript, because pages can
tell the difference. What no browser can supply is the cadence between actions,
the pauses, the reading time, the irregularity, because that rhythm is produced by
the loop above the browser. With an agent you drive through prompts, pacing is
partly promptable: asking for one thing at a time, at human speed, is not a joke
instruction, it changes the emitted rhythm.

## The order to check them in

When an agent starts getting blocked, check cheapest and most-likely first, and
change one thing at a time or you will not know which change mattered.

1. **Same task by hand, same machine, same network.** Open the site yourself in a
   normal browser. Blocked too? The problem is layer 2 (or the site blocks your
   whole region or network); no agent-side change will help until the exit
   changes.
2. **Blocked on the very first page load, before the agent did anything?** Then
   volume and behavior are innocent, they have not happened yet. It is fingerprint
   or IP. If the same exit works by hand in a normal browser, suspect the agent's
   browser: this is the layer where
   [the tooling comparison](ai-browser-agent-open-source.md) genuinely differs.
3. **Blocked after many pages, or on retries?** Count your own requests, and read
   what the agent did when the first failure appeared. A retry storm in the
   transcript is layer 3, and the fix is caps and honoring limits, not stealth.
4. **Blocked mid-session, after actions on the page?** With the first three layers
   ruled out, look at rhythm: instant fills, zero think time, identical pacing
   between actions. That is layer 4, and it lives in how the agent is driven.

Two cluster pages apply this checklist to specific stacks people arrive from:
[Claude computer use detected as a bot](claude-computer-use-detected-as-bot.md) and
[browser-use getting blocked](browser-use-getting-blocked.md).

## What this means before you swap anything

The four layers assign responsibility cleanly, and it is worth saying who owns
what with no comfort in it:

- **Fingerprint: the framework's job.** If this layer is your problem, changing
  the agent's browser changes the outcome.
- **IP: your job.** Bought, not configured.
- **Volume: mostly your job.** The prompt decides the ask; the framework can only
  keep the ask from becoming a storm.
- **Rhythm: shared.** The browser shapes each action; the loop, and the way you
  drive it, shapes the cadence.

And one boundary that belongs on the funnel page of a cluster like this: none of
the above is a way around a site that has told you no. Sites signal their terms
through rate limits, robots policies and account rules; the four layers explain
why an agent doing legitimate work gets misread as hostile, and the fixes here are
about not being misread, not about defeating a refusal.

## Short answers to the questions that lead here

**Why is my agent blocked when the same site works in my normal browser?** Then
layer 2 is partly ruled out and the leading suspect is layer 1, the agent's
browser fingerprint, with the agent's own volume and rhythm next. Work through the
order above before swapping anything.

**Does a stealth browser make my agent unblockable?** No, and distrust the word.
It addresses one layer of four. A patched real Firefox like AIHawk's fixes what
the site reads from the browser; the IP, the volume and the pacing are untouched
by it, and any of the three can block you alone.

**Do I need a proxy for my agent?** If your own address is the problem, or the
task needs a different region, yes, and quality decides everything; a widely
shared or datacenter exit can be worse than none. See the wiki's
[IP-reputation page](https://github.com/feder-cr/invisible_playwright/wiki/asn-and-ip-reputation-in-bot-detection)
for what actually gets scored.

**Why did the agent work for ten pages and then get blocked?** That shape points
at layer 3. Look for a retry loop in the transcript first; agents amplify one
failure into a burst, which is the layer-3 signature.

**Can the site tell it is specifically an AI agent?** It can read signals that
correlate strongly with one: automation fingerprints and machine-regular action
timing. The rhythm signal is the agent-specific tell, covered on
[the timing-signal page](ai-agent-timing-signal.md).

**Which layer does AIHawk actually fix?** The fingerprint layer, because its
browser is a real Firefox patched at the C++ level rather than a stock automation
build, plus human-shaped individual actions. It does not fix IP reputation, volume
or the loop's cadence, and this wiki says so on every page that touches the
subject.

## Sources

All retrieved 2026-09-03.

- [How do websites detect bots](https://github.com/feder-cr/invisible_playwright/wiki/how-do-websites-detect-bots),
  the mechanism-level overview of the same four-layer model.
- [JA3 and JA4: why a TLS fingerprint cannot be patched](https://github.com/feder-cr/invisible_playwright/wiki/ja3-ja4-tls-fingerprint),
  for the network side of layer 1.
- [ASN and IP reputation in bot detection](https://github.com/feder-cr/invisible_playwright/wiki/asn-and-ip-reputation-in-bot-detection),
  for layer 2.
- [feder-cr/aihawk_mcp_server](https://github.com/feder-cr/aihawk_mcp_server), plus its README in this
  repository, for the engine, proxy and input-event claims about AIHawk.

**See also:** [the timing signal AI agents give off](ai-agent-timing-signal.md),
[agent retry loops and rate limits](agent-retry-loops-rate-limits.md),
[Claude computer use detected as a bot](claude-computer-use-detected-as-bot.md), and
[browser-use getting blocked](browser-use-getting-blocked.md).

---

*From the [AIHawk](https://github.com/feder-cr/aihawk_mcp_server) wiki. AIHawk's engine exists
for layer 1, which is why this page could afford to be blunt about the other three:
they are yours, whatever agent you run.*
