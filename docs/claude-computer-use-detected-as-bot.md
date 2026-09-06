---
title: "Claude computer use detected as a bot"
description: "Claude computer use skips the usual automation flags because it clicks by pixel. What still gets it caught - the machine's fingerprint, the IP, the screenshot-click rhythm - and what helps, in order."
parent: "When the Agent Gets Blocked"
nav_order: 4
---


# Claude computer use detected as a bot

If Claude computer use is getting challenge pages or blocks, the cause is almost
certainly not the thing most bot-detection advice tells you to check. A
coordinate-clicking agent never sets off the classic automation flags, because it
never does the things those flags detect. What catches it is underneath and around
it: the fingerprint of the machine it runs on, the address it comes from, and the
rhythm of its screenshot-click loop.

This page goes through those in order - what the tool actually does on a page, why
the usual flags stay silent, what still gives it away, and what helps, ranked by how
much it moves.

## How computer use acts on a page

Claude's computer use tool works on screenshots and coordinates, and on nothing
else. The loop, per Anthropic's own documentation (retrieved 2026-09-03): your
application sends Claude a screenshot, Claude returns coordinate-based actions -
`left_click` at `[x, y]`, `type`, `key`, `scroll`, `wait` - your application
executes them on the actual desktop, and the loop repeats. Coordinates are in the
pixel space of the screenshot. The current toolset is `computer_toolset_20260801`.

Two details in that design matter for detection. First, the tool does not read the
DOM, parse HTML, or use an accessibility tree - it is purely visual. Second, *your
application executes the actions*: Anthropic's side returns intentions, and the code
that turns them into real mouse and keyboard events is yours, which will matter
later when we get to pacing.

## The tells it skips

Most advice about detected automation targets the DOM-automation layer:
[`navigator.webdriver`](https://github.com/feder-cr/invisible_playwright/wiki/navigator-webdriver-explained),
leftover automation globals, untrusted events dispatched from script, form fields
set from JavaScript. Those signals exist because a selector-driven script reaches
into the page and touches elements directly.

A computer-use agent does none of that. It never calls `querySelector`, never sets a
value from script, never dispatches a synthetic event at a node it located in the
DOM. Its click is a coordinate delivered through the input pipeline the way a real
click is. So that whole family of flags is not what catches it - not because
anything is hidden, but because the agent never generates them in the first place.

That is where people go wrong. They read that coordinate agents dodge the automation
flags and conclude detection is solved. It is not solved; it is bypassed at one
layer, and two other layers are completely untouched by that fact.

## What still gives it away

### 1. The machine it runs on

The agent clicks by pixel, but the click still lands in a browser, and that browser
answers JavaScript. The site's own scripts still ask the engine what it is: the
WebGL renderer string, the canvas hash, the fonts, the screen geometry, the audio
stack. None of that goes through the DOM the agent avoids.

And look at where computer use typically runs. Anthropic's docs recommend a
dedicated virtual machine or container with minimal privileges, and the reference
implementation is containerized (both retrieved 2026-09-03). Sensible for safety -
and a container answers the machine questions like a container:
[a software WebGL renderer](https://github.com/feder-cr/invisible_playwright/wiki/webgl-renderer-strings),
[a slim font set that does not match the claimed platform](https://github.com/feder-cr/invisible_playwright/wiki/headless-fonts-differ),
a virtual display with
[a screen geometry no desktop has](https://github.com/feder-cr/invisible_playwright/wiki/screen-size-headless-tells).
The whole list is on the engine wiki's
[container detection page](https://github.com/feder-cr/invisible_playwright/wiki/playwright-docker-detection).
The vision model driving the session is state of the art; the browser it is clicking
in reports a server.

### 2. The address

A datacenter IP is distrusted before the first byte of JavaScript runs, and no
property of the agent or the browser changes that. If the container from the
previous section is in a cloud, both tells arrive together.

### 3. The screenshot-click rhythm

The loop has a shape: screenshot, a pause while the model reads the image and
decides, then the action, then another screenshot. The pause is inference latency,
not human hesitation, so it repeats with a regularity no person produces. And when
the model returns several actions in one reply - the API supports batches, executed
sequentially in order - they land as a rapid chain with no reading time between
them. This is the general agent-timing problem, and it has
[a page of its own here](ai-agent-timing-signal.md).

## What actually helps, in order

1. **Put a real-looking machine under the agent.** This is the biggest lever,
   because the machine fingerprint is checked on every page and cannot be configured
   away from inside a stock build on a server. Either run the desktop on hardware
   that genuinely looks like a desktop, or give the model a browser whose identity
   is set in its own source. The second route exists today over MCP: instead of
   screenshotting a whole desktop, Claude Code, Claude Desktop or Cursor can drive a
   Firefox patched at the C++ level as a set of tools, via
   [invisible-playwright-mcp](https://github.com/feder-cr/invisible-playwright-mcp) -
   one line for Claude Code: `claude mcp add --scope user stealth --
   invisible-playwright-mcp`. Disclosure: that server and this wiki have the same
   maintainer, and it is the route [AIHawk](https://github.com/feder-cr/AIHawk)
   itself uses. For staying with the screenshot loop instead, the engine wiki shows
   [how to back a computer-use agent with a real browser engine](https://github.com/feder-cr/invisible_playwright/wiki/back-computer-use-agent-real-browser).
2. **Fix the exit.** A clean, residential-quality address, with the browser's
   timezone and locale agreeing with it. A perfect machine on a distrusted address
   still loses.
3. **Pace the executor.** Remember that your code executes the actions. That is
   where jitter lives: vary the delay before each action, do not fire a batch of
   actions back to back, and use the tool's own `wait` action between steps of a
   long task. This narrows the rhythm tell; it does not remove it, because the
   think-pause is still model latency.
4. **Do not let it retry into a wall.** A blocked step retried immediately, at
   machine speed, converts a behaviour flag into a volume flag.
   [Retry loops are their own failure mode](agent-retry-loops-rate-limits.md).
5. **Test like a site does.** Open a fingerprinting page in the agent's browser and
   in a normal browser on a normal machine, and compare field by field - and run it
   ten times, not once, because verdicts in this domain are not deterministic.

## Conclusion

Claude computer use moves the detection problem; it does not remove it. The
DOM-automation flags that dominate bot-detection advice are silent for it, because a
pixel click never produces them. What remains is the machine it runs on - usually a
container that answers like one - the address in front of it, and the machine-regular
rhythm of the screenshot-click loop. Fix them in that order: a real engine under the
agent, a clean exit, pacing in the executor, and a hard look at your retry
behaviour. Handle all of them and the agent looks like a person at a real computer.
Handle none and you have a brilliant model piloting an obvious server.

## Short answers to the questions that lead here

**Why is Claude computer use detected as a bot?** Usually the machine and the
address, not the automation. A container or server answers WebGL, font and screen
checks like a server, and a datacenter IP is distrusted on sight. The
screenshot-click rhythm adds a behaviour tell on top.

**Does Claude computer use set `navigator.webdriver`?** The tool itself does not
touch the page's JavaScript at all - it sends screenshots and coordinates. Whether
that flag is set depends on the browser you point it at; a stock automated build
sets its own flags regardless of who clicks.

**Can a site tell clicks come from Claude?** Not from the click mechanism, which
goes through the real input pipeline. What is visible is the rhythm: pauses centred
on model latency, batches of actions landing with no reading time between them.

**Does a better model fix detection?** No. The model chooses actions; detection
reads the machine, the address and the timing. Those do not improve with model
quality.

**What is the single highest-value fix?** The machine. Give the agent a browser that
reports a real desktop - via MCP with a patched engine, or by running on hardware
that is what it claims to be - before spending anything on the rest.

**Will that make it undetectable?** No, and distrust anyone who promises that. It
removes the machine fingerprint from the list of tells; the address, the volume and
the rhythm remain yours to manage.

## Sources

- Anthropic's [computer use tool documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool),
  retrieved 2026-09-03: the screenshot-to-coordinate loop, the
  `computer_toolset_20260801` action set, coordinates in screenshot pixel space,
  batch actions executed sequentially, the recommendation to run in a dedicated VM
  or container, and the fact that the caller's application executes the actions. The
  containerized reference implementation is
  [anthropic-quickstarts/computer-use-demo](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo).
- The engine wiki's machine-fingerprint pages linked above, which document each
  surface a container exposes and how it is read.

**See also:** [the timing signal AI agents give off](ai-agent-timing-signal.md) for
the rhythm tell in depth,
[browser-use getting blocked](browser-use-getting-blocked.md) for the contrasting
case of a DOM-driven agent, and
[why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md) for the
full sort.

---

*Written while maintaining [AIHawk](https://github.com/feder-cr/AIHawk), an AI agent
on a Firefox patched at the C++ level. The pattern in this page - clean automation
layer, guilty machine - is the single most common thing behind "my agent got
detected", whoever's agent it is.*
