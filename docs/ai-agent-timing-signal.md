---
title: "The timing signal AI agents give off"
description: "An AI agent's think-act loop emits machine-regular gaps, model-latency pauses and dead-centre clicks. Why no fingerprint work fixes that, and what pacing actually helps."
parent: "When the Agent Gets Blocked"
nav_order: 2
---


# The timing signal AI agents give off

The browser under your agent can be flawless - a real engine, a real fingerprint, a
clean driver surface - and the session can still read as automated for a reason that
has nothing to do with the browser: the rhythm of the loop driving it.

Every AI agent, invisible_playwright_mcp included, runs a think-act cycle. It looks at the page, sends
what it sees to a model, waits for the model to decide, performs the action, and looks
again. That cycle has a shape, and the shape is measurable from the other side of the
connection. If your agent gets through the first page load fine and gets challenged a
few interactions later, this page is probably about your problem: the block that
arrives after actions, not before them, is usually a behaviour verdict, not a
fingerprint one.

## What the rhythm looks like from the site's side

A behavioural check does not read the GPU string or the canvas hash. It reads the
stream of events a session produces over time, and an agent loop left to its own
timing produces four things a person does not:

- **Gaps that cluster.** Between one action and the next sits a wait for the model.
  That wait is not random the way a human pause is: it clusters around the model's
  inference latency, step after step, run after run. A person's pauses spread wide
  and ragged - a one-second glance here, an eight-second read there. The individual
  number is not the tell; the shape of the distribution is.
- **Stillness inside the pause.** A person reading a page drifts the pointer, scrolls
  a little, hovers over things. An agent's pointer sits perfectly still for two
  seconds and then arrives exactly where it needs to be.
- **Actions that land dead centre, instantly.** Coordinates computed from page
  structure or from a screenshot land on the centre of the target, with no approach,
  no overshoot, no correction, and no reading time in front of the click.
- **No wasted actions.** People scroll past things, open the wrong tab, hover over
  what they never click, change their minds. An agent performs exactly the actions
  the task needs and nothing else, which is efficient and visible.

None of that appears in any fingerprint report, which is exactly why it deserves its
own page: it is a separate signal, read by a separate part of a detection system, and
it survives every fingerprint fix.

## Why a perfect fingerprint does not touch it

A fingerprint is a photograph; behaviour is a motion study. Making the photograph
perfect does nothing to the motion study.

invisible_playwright_mcp runs on a Firefox patched at the C++ level (the
[invisible_playwright](https://github.com/feder-cr/invisible_playwright) engine), and
that engine's job is the photograph: the rendering, the driver surface and the network
handshake read as a genuine Firefox rather than an automated build. That is real, and
it is most of what agents are blocked for. It is also not everything, and the honest
boundary matters: the engine controls what the browser *is*, not the cadence at which
the loop above it decides to act. The cadence is produced by the model and the
harness calling it, above the browser, out of the engine's reach. The engine wiki's
[testing method](https://github.com/feder-cr/invisible_playwright/wiki/how-to-test-bot-detection)
lists behaviour among the things no in-page test suite covers, for the same reason.

## What the layer under invisible_playwright_mcp already covers

Part of the motion problem does live below the loop, and that part is handled there,
so you should know which part it is before trying to fix it yourself.

- **The pointer path.** When the agent clicks, the engine arcs the pointer to the
  target on a curved, human-shaped path rather than teleporting it. An individual
  click's motion is covered; the gap before the click is not, because the loop decides
  when the click happens. The boundary between pointer realism and fingerprint realism
  is drawn in detail on
  [the engine wiki](https://github.com/feder-cr/invisible_playwright/wiki/ghost-cursor-human-mouse).
- **Real input, not script shortcuts.** invisible_playwright_mcp drives the page the way a person would:
  the pointer moves and keys are pressed, and it refuses to set a form field from
  JavaScript even when that would be quicker, because a page can tell the difference.
- **Read before act.** invisible_playwright_mcp's system prompt instructs the model to inspect the page
  before acting on it and to prefer one clear action at a time over long chains. That
  produces read-shaped traffic in front of actions instead of blind action bursts.

What none of that covers is the distribution of gaps between steps. That is the
model's latency wearing a trench coat, and it is visible no matter how good each
individual action looks.

## What actually helps

Be clear-eyed about what you control. If you run an off-the-shelf agent - invisible_playwright_mcp's
interface, or an assistant driving the browser over MCP - the loop's internal timing
is not a knob you turn. What you control is everything around the loop, and that is
where the wins are:

- **Fewer, larger tasks.** One instruction that reads five prices in one visit
  produces one session with a natural arc. Five separate instructions produce five
  bursts, each starting cold on the same site.
- **No fixed schedule.** Running the same task from a timer every ten minutes turns
  the task itself into a metronome. If something must repeat, vary the interval.
- **Space out repeat visits.** The rhythm tell compounds with the volume tell, and
  the volume half is [a page of its own](agent-retry-loops-rate-limits.md).
- **Do not re-run a blocked task immediately.** A challenge answered by the identical
  session ten seconds later confirms the verdict.

If you are building your own harness above an agent loop - executing its actions
yourself, or scripting the engine directly through its Python library - you own the timing, and then the rule
is: vary it, and make it depend on the step. A uniform delay is its own tell. A
`sleep(1.0)` between every action just moves the cluster from "instant" to "exactly
one second", and a tight cluster at one second is as machine-regular as a tight
cluster at zero. Long pauses before decisions, short ones inside a form, no number
twice:

```python
import random, time

def dwell(low=0.6, high=2.4):
    """A varied pause, the kind reading and deciding actually produces."""
    time.sleep(random.uniform(low, high))
```

## Seeing your own rhythm before a site does

You can read this signal off your own sessions the way a site would. invisible_playwright_mcp's
interface narrates every step as it takes it, so the cadence is on screen while the
task runs; for anything scripted, log a timestamp at each action and look at the
spread of the gaps. If the minimum and maximum are close together, or the mean sits
right on top of your model's typical response time, the loop is emitting the
clustered distribution described above. A human trace has a wide spread and a long
tail. Measure the stream; do not assume the shape.

## Conclusion

The fingerprint and the rhythm are two different signals, read by two different parts
of a detection system, and the engine under invisible_playwright_mcp addresses the first. It makes the
browser real, gives each click a human-shaped path, and puts real key presses behind
typed text. The cadence between actions is produced above the browser - by the model
and by how you run it - so it is yours: fewer and larger tasks, no fixed schedules,
varied pacing where you control the code, and a look at your own gap distribution
before a site looks at it for you.

## Short answers to the questions that lead here

**Does a stealth browser hide that I am running an AI agent?** It hides that the
browser is automated. It does not hide the rhythm of the loop driving it, which is a
separate signal produced above the browser.

**What is the timing signal, exactly?** The gaps between actions cluster around the
model's latency instead of spreading like human pauses, the pointer is still during
the pause, and actions land dead centre with no reading time in front of them.

**Why do I get blocked after a few actions rather than at the first page?** A block
at first load points at the fingerprint or the address. A block after interactions
points at behaviour, and the agent rhythm is the usual behaviour verdict.

**Can invisible_playwright_mcp add the pacing for me?** The engine humanizes each click's pointer path
and presses real keys, and the agent reads before acting. The step-to-step cadence
is decided by the model's loop, so what you control is how many tasks you run,
against what, on what schedule.

**Do I just add a fixed sleep between actions?** No. A tight cluster at one second is
as regular as a tight cluster at zero. Vary the pauses and make them depend on the
step.

**Will fixing the timing get me past everything?** No. A clean rhythm on a bad exit,
over quota, or against a rate limit still fails.
[Why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md) sorts the
layers.

## Sources

- invisible_playwright_mcp's own source: the system prompt in `src/invisible_playwright_mcp/agent.py` instructs the model
  to inspect pages before acting and to prefer one clear action at a time, and the
  [README](https://github.com/feder-cr/invisible_playwright_mcp#readme) documents the input behaviour
  (pointer moves, keys pressed, JavaScript form-fill refused). Both read 2026-09-03.
- The engine wiki's
  [testing method](https://github.com/feder-cr/invisible_playwright/wiki/how-to-test-bot-detection),
  which lists behaviour and the model-latency-shaped pause among the things no
  in-page suite covers, and its
  [detected-on-one-site checklist](https://github.com/feder-cr/invisible_playwright/wiki/playwright-detected-as-bot),
  which reaches pointer motion and cadence only after the browser itself is clean.

**See also:** [why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md)
for the full layer-by-layer sort, [agent retry loops and rate limits](agent-retry-loops-rate-limits.md)
for the volume half of the same problem, and
[Claude computer use detected as a bot](claude-computer-use-detected-as-bot.md) for
the rhythm of a screenshot-driven agent specifically.

---

*Written while maintaining [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), an AI agent
on a Firefox patched at the C++ level. The engine makes the browser real; the rhythm
comes from the loop, and this page is what I check first when a session of my own
gets challenged after the third click.*
