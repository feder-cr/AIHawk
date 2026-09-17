---
title: "How long the agent waits before it gives up"
description: "Forty-five seconds for a navigation, fifteen for anything that touches an element, and hundreds of retries inside that fifteen. Which failures the ceilings catch and the one they cannot."
parent: "Using the Agent"
nav_order: 71
---

# How long the agent waits before it gives up

Every tool call has a ceiling. Knowing the numbers turns a confusing pause into a
diagnosis, because **how long a call took tells you what went wrong** almost as
precisely as the error does.

| call | ceiling |
|---|---|
| `browser_navigate` | **45 s** |
| `browser_click` | **15 s** |
| `browser_type` | **15 s** |
| `browser_select_option` | **15 s** |

Those are per call. There is no ceiling on a run.

## The fifteen seconds are not a wait, they are a retry loop

This is the part worth understanding. A click does not look once and fail. It
re-resolves the element and re-checks that it is actionable, over and over, until
either it succeeds or the ceiling runs out.

Measured here on 2026-09-17, a click at a selector that was inside an iframe and
therefore unreachable: `'#fb' not actionable in 15s after 275 attempts`. This
project's own source records the same mechanism on a different case: 208 attempts
over the same fifteen seconds, on a skip-to-content link that reported as visible
and could not be clicked.

So the loop runs at roughly fifteen to twenty attempts a second, and the message
tells you how many it made. That count is information: a call that failed after
hundreds of attempts spent its whole budget looking for something that was never
going to be there, which is a different problem from a call that failed
immediately.

## Reading a failure by its duration

- **Instant failure.** The call was rejected before any page work: a wrong kind
  of element, an unsupported operation, a browser with no page open. The message
  names it. An example is
  [select_option on something that is not a select](native-selects-and-fake-ones.md).
- **A second or two.** Ordinary page work. Nothing to diagnose.
- **The full fifteen.** The element could not be resolved or could not be acted
  on for the entire budget. Candidates, in order: it is in an iframe, it is
  behind an overlay, it never rendered, the selector is wrong, or it is one of
  those elements that reports visible and is not.
- **The full forty-five on a navigation.** The site did not finish what you asked
  it to wait for. Often that is a slow page, and often it is a `wait_until` that
  is stricter than the page will ever satisfy.

## The ceiling that does not exist is the expensive one

The run has no limit. A task can make a hundred successful calls in a direction
that is wrong, and nothing in the loop will stop it: each call is fast and
succeeds, so no ceiling is ever reached.

That is why the per-call numbers above are a debugging aid rather than a safety
mechanism, and why the bound you actually need is one you write into the task.
[Giving an AI browser agent a stopping condition](giving-an-ai-agent-a-stopping-condition.md)
is that argument, and the short version is that a budget the model counts for
itself is soft and something outside the agent has to hold the hard one.

## Waiting for a state beats waiting for time

The navigation call takes a `wait_until`, and it is the one place where choosing
badly costs you the whole forty-five seconds. A page that keeps a connection open
for streaming or polling may never reach the strictest condition, no matter how
healthy it is.

For everything after the navigation, the better instrument is not a wait at all:
read the page and check for the state you need. A read costs about a hundredth of
a second, per
[how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md),
so checking ten times is free, while a fixed pause is too long on a fast page and
too short on a slow one. The general form is in
[when the page changes under the AI agent](when-the-page-changes-under-the-agent.md).

## What to do when a call hits its ceiling

Not retry it unchanged. The call already retried, hundreds of times, which is
what the ceiling was spent on. Repeating it buys another fifteen seconds of the
same.

Change something first: re-read the page and confirm the element is still
described the way you think, check for an overlay or a consent wall, check
whether it is in a frame, or drop to the coordinate rung in
[clicking by selector or by coordinates](clicking-by-selector-or-by-coordinates.md).

And if two attempts have hit the ceiling on the same element, stop the run rather
than continuing. Two full ceilings is thirty seconds spent learning the same
thing twice.

## Short answers to the questions that lead here

**How long does an agent wait for an element?** Fifteen seconds, spent on
hundreds of re-checks rather than one long pause. Navigation gets forty-five.

**What does "not actionable in 15s after 275 attempts" mean?** The element could
not be resolved or could not be clicked for the whole budget. It is usually in a
frame, behind an overlay, or never rendered.

**Can I raise the timeouts?** They are fixed per call in this surface. The lever
you have is the task: check for the state you need with a read instead of leaning
on the ceiling.

**Is there a limit on the whole run?** No. Every call can succeed while the run
goes the wrong way, which is why a stopping condition belongs in the task.

**Should I retry a call that timed out?** Not unchanged. It already retried
hundreds of times. Re-read, check for a frame or an overlay, or switch rung.

**See also:**
[what an AI agent can and cannot do inside an iframe](an-agent-and-an-iframe.md),
the case that produces the cleanest full-ceiling failure, and
[browser problem or model problem](browser-problem-or-model-problem.md) for
sorting a timeout that is really the site's.

## Sources

- The ceilings are read from this project's own MCP action layer on 2026-09-17: `goto` at 45,000 ms, `click`, `fill` and `select_option` at 15,000 ms.
- The 275-attempt failure is from a measurement the same day, clicking a selector inside an iframe. The 208-attempt figure is recorded in the same source file, from a measurement on skip-to-content links that report as visible and cannot be clicked.

---

*The count of attempts in the error is the part people skim past. It is the
difference between "your selector is wrong" and "that element is somewhere the
selector cannot go".*
