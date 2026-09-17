---
title: "When the page changes under the AI agent"
description: "The gap between looking and acting is where browser agents break. What moves in that gap, why a selector fails better than a coordinate, and the one instruction that fixes most of it."
parent: "Using the Agent"
nav_order: 51
---

# When the page changes under the AI agent

Every browser agent runs the same loop: look, decide, act. The decide step is the
slow one, because a model is thinking, and a web page does not wait. Everything
awkward about driving a browser with a model lives in that gap.

It is worth being precise about how long the gap is. The looking and the acting
are fast: a snapshot comes back in about a hundredth of a second and a click
takes about a second, both
[measured](how-long-an-ai-agent-takes-per-step.md). The thinking in between is
seconds. So the page has, routinely, **several seconds in which to become a
different page** while the agent is holding a description of the old one.

## What actually moves in those seconds

- **A consent or cookie wall appears**, and now everything the snapshot described
  is behind it.
- **Images finish loading** and push the layout down. Nothing changed logically;
  every coordinate moved.
- **A lazy list renders** and the element that was third is now ninth.
- **A single-page app swaps a view**, and the elements the snapshot listed no
  longer exist.
- **A toast or a modal opens** over the thing the agent was about to click.
- **A session expires**, and the page is now a login form that looks nothing like
  the snapshot.

None of these is a bug in the page, and none of them is the model being careless.
They are the normal behaviour of the modern web meeting a client that thinks for
three seconds.

## Why a selector fails better than a coordinate

This is the practical asymmetry, and it decides how you should drive.

A **selector** resolved after the page moved either finds the right element or
finds nothing. Finding nothing is an error the agent can see and react to.

A **coordinate** resolved after the page moved always finds *something*: whatever
is now at that x and y. The action succeeds, the wrong thing happens, and nothing
in the run reports a problem.

That is why the sensible order is a named tool with a selector first, coordinates
only when no selector describes the target, and a picture only when the snapshot
does not list the thing at all. It is not about precision; it is about which kind
of failure you get.
[Why did the AI agent click the wrong thing](why-did-the-agent-click-the-wrong-thing.md)
is the same asymmetry seen from the symptom.

## The one instruction that fixes most of it

Re-read immediately before acting, and act on the fresh read.

It sounds obvious and it is routinely skipped, because a snapshot feels like it
costs something. It costs a hundredth of a second. The right habit is:

```
snapshot  ->  decide  ->  snapshot again  ->  act on the second one
```

The second read closes the gap to roughly the duration of one tool call instead
of the duration of one model turn, which is one to two orders of magnitude
smaller. It does not close the gap to zero, and nothing can.

## Waiting is not the same as re-reading

A common half-fix is to insert a wait: pause two seconds after navigating, then
carry on. That helps with the slowest case and leaves the others alone, because
the thing you are waiting for is not time, it is a state.

The better instruction names the state: wait until the result list has rows, wait
until the spinner is gone, wait until the button is enabled. The agent can check
those by reading, which is free. A fixed wait is a guess that is too long when the
page is fast and too short when it is slow.

## What to do when it has already happened

Three situations, three different responses.

**The action failed cleanly.** The best case. Re-read and retry once, on the
fresh description. If the second attempt also fails, stop: something structural
changed and retrying is now the loop described in
[giving an AI browser agent a stopping condition](giving-an-ai-agent-a-stopping-condition.md).

**The action succeeded but the result is wrong.** Re-read and compare against what
you expected the page to say. This is the case that needs a stated expectation in
the task, because without one there is nothing to compare against.

**The action was irreversible.** There is no recovery here, which is why this
class of action needs a confirmation step in front of it rather than a retry
behind it. That argument is in
[keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md).

## The case you cannot engineer around

A session that expires mid-run turns the page into a login form, and every
subsequent step operates on the wrong page while looking superficially normal.
The agent fills fields, the fields exist, nothing errors.

The defence is a cheap assertion rather than cleverness: have the task state one
thing that must be true of the page it is on, and check it after each navigation.
"The header shows my account name." It costs one free read and it turns a silent
wrong run into an early stop.

## Short answers to the questions that lead here

**Why does my agent act on stale information?** Because it looked, then thought
for a few seconds, then acted. The page had those seconds. Re-read immediately
before acting and the window shrinks to a single tool call.

**Should I add a wait after navigating?** Prefer waiting for a state over waiting
for a duration. A fixed wait is too long on a fast page and too short on a slow
one.

**Why did the click succeed and do the wrong thing?** You clicked a coordinate,
and the layout shifted. Coordinates always hit something; selectors fail cleanly.

**How do I detect that the session expired mid-run?** Give the task one sentence
that must be true of a logged-in page and check it after every navigation.

**Does a faster model fix this?** It narrows the gap, which helps, and it does not
close it. The structural fix is the second read, not the faster turn.

**See also:**
[how to write a task an AI browser agent can follow](writing-tasks-for-an-ai-browser-agent.md),
where the "what must be true afterwards" sentence comes from, and
[running one task across a list of sites](run-one-task-across-a-list-of-sites.md),
where one flaky page in a list of fifty is the thing that decides whether the run
is usable.

## Sources

- The two timings this page leans on, a read at about 0.01 s and a click at about 1 s, are measured and sourced on [how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md). The list of things that move during the gap is from running this browser rather than from a study, and is offered as such.

---

*The whole page reduces to one line: the gap between looking and acting is a
model turn long, and you can make it a tool call long instead. Everything else
here is a consequence.*
