---
title: "Playwright MCP session blocked: four causes, four fixes"
description: "Four failures all report as blocked and need opposite responses. How to tell an empty snapshot from a challenge from a rate limit from real detection."
parent: "When the Agent Gets Blocked"
nav_order: 6
---

# Playwright MCP session getting blocked

"Blocked" covers four failures that look the same from inside a chat window and
need completely different responses. Getting the attribution right is most of
the work, because three of the four are not detection at all.

## Tell them apart first

**The snapshot is empty or missing what you can see in a browser.** Not blocked.
The page rendered its content after the snapshot was taken, or the content is
inside an iframe the snapshot did not descend into, or it is drawn on a canvas
that has no accessibility representation. Ask for the snapshot again after the
page settles, or take a screenshot and compare: if the screenshot has the
content and the tree does not, this is your case.

**A page that says something about verifying you are human.** A challenge. This
is a judgement made mostly before your page interaction, on the address and the
connection. [Cloudflare and Playwright MCP](cloudflare-and-playwright-mcp.md)
covers what one is actually reading.

**It worked for a while and then stopped.** A rate limit, almost always. The
signature is that it is time-based rather than immediate, and that waiting fixes
it. No browser setting reaches this. Slow down.

**It fails immediately, on the first request, from this machine only.** Now you
have a candidate for either the address or the browser. Those two are separable
and the next section separates them.

## Address or browser

Run the same page from the same machine in an ordinary browser you use by hand.

- **The hand browser is fine, the agent is not:** the browser is a candidate.
  Same address, different result.
- **Both are refused:** the address. Nothing about your server or engine matters
  yet, and switching servers will waste a day.

Then run the agent from a different network, a phone hotspot is enough.

- **Different network, works:** confirmed address.
- **Different network, still refused:** now it is the browser or the pacing.

This costs ten minutes and is the difference between fixing the problem and
switching tools at random.
[Why an agent gets blocked](why-does-my-ai-agent-get-blocked.md) has the longer
version of the same reasoning.

## What each cause actually responds to

**Address.** A proxy, and the type matters:
[Playwright MCP with a proxy](playwright-mcp-with-a-proxy.md), including the
three leaks that a proxy does not close by itself.

**Pacing.** Fewer actions per minute, and pauses that are not identical. An
agent under a model is naturally slower than a script, which helps, but a model
told to check forty pages will do it in a rhythm no person has.

**The browser.** This is the one where the server choice matters, and only here.
A stock automation build is a specific set of observable choices that no flag
changes. Engine-modified alternatives exist and
[stealth MCP servers compared](stealth-mcp-servers-compared.md) lists them,
along with the claims among them that we could not verify.

**The snapshot.** Not blocked. Read again, or screenshot.

## What none of it responds to

A challenge you are meant to solve interactively stays a challenge. This project
does not solve captchas and does not claim non-detection:
[can an AI agent solve a captcha](can-an-ai-agent-solve-a-captcha.md) is the
direct answer, and it applies to every tool in this category regardless of what
its README says.

If a site is refusing an agent deliberately and consistently, that is a decision
the site made. The useful question at that point is whether the data is
available another way, not which server to try next.

## Short answers to the questions that lead here

**Why does Playwright MCP get blocked and my normal browser does not?** Usually
not the same test. Your normal browser has history, a profile and a session; the
agent's is fresh. Sometimes it is the address. Occasionally it is the automation
build.

**Does `--isolated` make blocking worse?** It can. A profile with no history is
one more thing that is unusual, though far less decisive than the address.

**Will a different MCP server fix it?** Only if the browser was the cause, which
is the least common of the four. Attribute first.

**Is a headless browser more likely to be blocked?** Headless is detectable in
its own right, and running headed costs you nothing on a desktop. Try headed
before concluding anything.

**Why does it work locally but fail on the server?** The classic case, and it is
the machine and the address rather than the code: no GPU, a container font set,
a datacenter address.

**See also:** [when the agent gets blocked](guides-when-the-agent-gets-blocked.md),
[browser-use getting blocked](browser-use-getting-blocked.md), and
[Claude computer use detected as a bot](claude-computer-use-detected-as-bot.md).

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10, for the snapshot model and the isolation options.
- The engine wiki's [how to test bot detection](https://github.com/feder-cr/invisible_playwright/wiki/how-to-test-bot-detection) for running the comparison yourself.

---

*Written while maintaining a server whose differentiator is the browser. The
page puts the browser fourth out of four causes, because that is where it
belongs by frequency.*
