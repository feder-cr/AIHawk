---
title: "Using an AI agent to test your own website"
description: "Plain-language smoke tests on your own app: what an agent catches that scripted suites miss, what suites catch that it never will, and the flakiness honesty in between."
parent: "Using the Agent"
nav_order: 14
---


# Using an AI agent to test your own website

"Go to my app, register an account, add an item to the cart, and tell me
everything that broke or confused you." That sentence is a test plan, and an
agent with a real browser will execute it against your dev server right now,
no test framework, no selectors, no setup beyond pointing it at localhost.
This page is about what that is genuinely worth, which is a real and specific
thing, and what it is not, which is your regression suite.

The scope rule comes first because everything on this page depends on it:
your own application, on localhost or staging, with test data. Against your
own app, mistakes are free, there are no terms to honor and no rate limits to
respect, and you know the ground truth the agent's report gets checked
against. That combination exists nowhere else on the web, which is why testing
is the least complicated use of a browser agent on this whole wiki.

## The smoke test in plain language

The working pattern is one instruction, one flow, one report:

> Open http://localhost:3000. Register a new user with placeholder data, log
> in as that user, add any item to the cart, and go to checkout but do not
> place the order. At each step, tell me what you saw, anything that looked
> broken, and any error or validation message that appeared.

Run it through an editor client - [Cursor](running-aihawk-with-cursor.md) or
[Cline](running-aihawk-with-cline.md), where the same assistant also has your
code open - or from the terminal:

> Open http://localhost:3000 and try to register a new user
> with placeholder data. Report every field, every validation message, and
> whether registration succeeded.

Typed into `aihawk ui`, which runs the task with the live page beside the
chat - and for testing the watching is worth having: seeing the agent
hesitate on your form is itself a finding. Two properties of
this browser matter specifically for testing. It fills forms through real key
presses and clicks, refusing script injection, so your input handlers,
keystroke validation and change events fire the way they fire for people. And
the editor-client route closes the loop in one conversation: the agent that
just hit the bug is the assistant reading the handler that caused it, so "now
find why" is the natural next sentence.

## What it catches that your test suite does not

A scripted test asserts what you thought to assert. The agent reads the page
like a first-time user with infinite patience, and its findings cluster
exactly where scripted suites are blind:

- **The unasserted breakage.** The suite checks that registration returns
  200; the agent reports that the success page renders with the username
  missing and a raw template variable in the heading. Nobody wrote that
  assertion, because nobody predicted that break.
- **Confusion as a finding.** "The button labeled Continue took me back to
  the start" or "two fields are both labeled Name and I could not tell which
  was which." No assertion fails on confusing; an agent narrating its own
  attempt surfaces it. It is a cut-rate usability pass - genuinely cut-rate,
  and genuinely a pass.
- **Validation behavior in full.** Ask it to probe a form with wrong inputs
  on purpose - bad emails, empty requireds, a date in the past - and report
  every message. [The forms page](ai-agent-fill-out-forms.md) describes
  agents fighting validation as a failure mode; against your own form it
  inverts into coverage, and the agent's misreadings of your error messages
  are findings too. If it could not connect the message to the field, some
  users will not either.
- **The path you never test by hand.** Flows behind three clicks of setup
  decay unexercised. An agent walks them for cents while you review a diff.

## What your suite catches that the agent never will

The concession, without hedging: an agent is not a regression suite and
cannot become one. A scripted Playwright test runs in seconds, costs nothing
per run, produces the same verdict every time, and fails loudly in CI the
moment a change breaks the checkout - that determinism is the entire point of
a test suite, and a model-driven agent has none of it. Speed alone
disqualifies it from the inner loop: an agent run is tens of seconds and a
model bill; your suite is hundreds of assertions before the coffee cools.

The two are not rivals; they are a feeder pattern. The agent explores and
finds; what it finds worth protecting, you pin down as a scripted test. For
that half, AIHawk's own engine is a library with Playwright's API -
[invisible_playwright](https://github.com/feder-cr/invisible_playwright) -
and its [wiki](https://github.com/feder-cr/invisible_playwright/wiki) covers
scripted browser automation in a depth this page does not attempt. Realistic
browser behavior in scripted tests matters more than people expect, because
users do not send synthetic events.

## Flakiness, stated plainly

An agent run is a stochastic process on both ends: the model reads and
decides differently across runs, and your app under development shifts too.
Consequences to accept up front, not discover:

- **Same instruction, different walk.** Two runs may click different valid
  paths to the same goal, and one may notice what the other skipped. For
  exploration that variance is a feature; for a pass/fail gate it is
  disqualifying. Do not wire an agent verdict into CI as a blocker.
- **A reported bug is a lead, not a verdict.** Reproduce it by hand before
  filing. The transcript and screenshots tell you where it thought it was;
  [browser problem or model problem](browser-problem-or-model-problem.md) is
  the sorting guide when the report itself seems off.
- **Repetition is the instrument.** One clean run proves little; several
  runs that all pass the same flow mean more. This wiki's own testing rule
  for verdicts on nondeterministic domains is many runs, and your app under
  an agent is exactly such a domain.
- **`--seed` pins the browser identity, not the model's choices.** Useful so
  each run is not a new device to your analytics; it does not make runs
  repeat. Nothing makes runs repeat - that is what your scripted suite is
  for.

## Short answers to the questions that lead here

**Can an AI agent test my website?** Yes, as a plain-language smoke tester
and exploratory prober on your own app: give it a flow in a sentence, get a
narrated report of what broke or confused it. It complements a scripted
suite; it does not replace one, and the flakiness section above is why.

**What does it catch that Playwright tests do not?** The unasserted: renders
nobody predicted would break, confusing labels and dead-end flows, validation
messages that do not reach a reader. Scripted tests check what you
anticipated; the agent reports what it met.

**Should it run in CI?** Not as a gate. Model-driven runs are
nondeterministic, slow and metered; a red that means "the agent wandered" and
a green that means "the agent did not look" both poison a pipeline. Keep it
as an on-demand explorer, and let what it finds graduate into scripted tests.

**How do I let it test behind my app's login?** Simplest on your own app:
create a test account and put the credentials in the instruction - it is your
system, so the caution about credentials traveling through the model is
yours to weigh. A persistent `--profile-dir` with a login done once by hand
also works, same pattern as elsewhere on this wiki.

**Why does it fail on my custom datepicker?** The same reason agents fail on
everyone's custom widgets - [the forms page](ai-agent-fill-out-forms.md)
catalogs it. On your own site that failure is information: if an agent
reading the accessibility tree cannot work your widget, check what a screen
reader user meets.

**Is the browser realistic enough to matter for testing?** It is a real
patched Firefox sending real input events, so handlers fire as they do for
people. For most functional testing any browser would do; the realism starts
mattering when what you are testing is behavior that differs between real
input and synthetic events.

## Sources

All retrieved 2026-09-03.

- [feder-cr/invisible_playwright](https://github.com/feder-cr/invisible_playwright)
  and its [wiki](https://github.com/feder-cr/invisible_playwright/wiki), the
  Playwright-API engine and its scripted-automation reference, linked for the
  regression-suite half of the pattern.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its README and
  source in this repository, for the real-input-events behavior, `--headed`,
  `--seed`, `--profile-dir`, and the agent loop the flakiness section
  describes.

**See also:** [running AIHawk's browser from Cursor](running-aihawk-with-cursor.md),
[running AIHawk's browser from Cline](running-aihawk-with-cline.md),
[getting an AI agent to fill out forms](ai-agent-fill-out-forms.md), and
[browser problem or model problem?](browser-problem-or-model-problem.md).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The most useful
bug report the maintainer ever got from the agent was three words about a
form nobody had touched in months: "Continue does nothing."*
