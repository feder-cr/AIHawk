---
title: "Monitoring a page for changes with an AI agent"
description: "When a plain diff monitor is the right tool, when an agent's judgment earns its cost, how to schedule the capture as a script on the same engine, and what to store between runs."
parent: "Using the Agent"
nav_order: 7
---


# Monitoring a page for changes with an AI agent

Start with the uncomfortable half: if the question is "tell me when this page
changes at all," an AI agent is the wrong tool. A diff-based monitor fetches the
page, compares it to the last fetch, and notifies on difference, at effectively
zero cost per check; an agent run is a browser launch plus a chain of model
calls, cents and tens of seconds per check, to answer the same yes/no. Running
an LLM on a schedule to do a byte comparison is paying for judgment and not
using it.

The agent earns its cost when the question actually needs judgment: not "did a
byte change" but "did the return policy meaningfully change," "is the price now
below the threshold I care about," "summarize what is different in terms I can
act on." A diff monitor fires on a rotated banner, a new timestamp in the
footer, a reshuffled ad slot; it cannot tell you whether the change matters.
That distinction is a reading-comprehension question, and reading comprehension
is the one thing the agent brings.

This page covers both halves: the plain tool, scheduling the agent, and the
two-stage pattern that uses each at its own price.

## When the plain tool is the right answer

For "any change, tell me fast," use a purpose-built monitor. The reference
open-source option is [changedetection.io](https://github.com/dgtlmoon/changedetection.io):
self-hostable, diffs pages on a schedule you set, and notifies over the usual
channels. It does per-check what an agent cannot: run constantly, for free,
without a model in the loop. One disclosure belongs next to that
recommendation: this project's maintainer also publishes a
[changedetection.io fetcher plugin](https://github.com/feder-cr/invisible_playwright-changedetectionio)
that puts this same browser engine behind it, so the advice to use
changedetection.io is not disinterested - it is still the right advice for
mechanical checks, which is why it leads this section.

Choose it whenever your condition is mechanical. A number appearing, a string
disappearing, a section changing at all: these are diff conditions, and paying
model tokens to evaluate them is waste. It is the same boundary
[the scraping comparison](ai-browser-agents-vs-traditional-scraping.md) draws
for extraction: deterministic conditions belong to deterministic tools.

## When the agent earns its cost

Three shapes of monitoring genuinely need the model:

- **Meaningful-change detection.** "Tell me when the terms of service change in
  a way that affects cancellation." A diff fires on every typo fix; the agent
  reads both versions and answers the question you actually asked.
- **Threshold and condition checks that need reading.** "If the top item is
  marked unavailable, or the stated delivery estimate slips past two weeks,
  flag it." The facts live in prose and layout, not in one stable element a
  selector could watch.
- **Summarized deltas.** "What changed on this page since last week, in three
  bullets, ignoring cosmetics." The output is an editorial judgment, which is
  exactly what you cannot script.

Be honest about the price even here: every judgment is a fresh agent session -
a browser opened, a handful of model turns, cents on the default model and
roughly a minute of wall clock. Daily is comfortable; every five minutes is a
bill and, as covered below, a signature. The scheduled capture itself, as the
next section shows, costs no model at all.

## Scheduling it: a script, as of aihawk 0.3.0

Since 0.3.0 AIHawk itself is interactive-only (`aihawk ui`): there is no
headless subcommand to put in cron anymore. That is less of a loss than it
sounds, because the scheduled half of monitoring is deliberately mechanical -
fetch the page, extract one signal, save it - and mechanical work belongs in
code, not in model turns. The same stealth engine AIHawk drives is on PyPI as
a Python library with Playwright's API, so the check is a short script. This
one runs as shown, against the public scraping sandbox:

```python
# check_page.py - fetch one signal from the watched page
from invisible_playwright import InvisiblePlaywright

with InvisiblePlaywright(seed=7) as browser:
    page = browser.new_page()
    page.goto("https://books.toscrape.com/", wait_until="domcontentloaded")
    first = page.locator("article.product_pod").first
    title = first.locator("h3 a").get_attribute("title")
    price = first.locator(".price_color").inner_text()
    print(f"{title} | {price}")
```

Executed on 2026-09-03 it prints exactly `A Light in the Attic | £51.77`.
`pip install invisible-playwright` is the only setup; swap the URL and the two
selectors for your page's. Three details matter for a recurring check:

- **`seed=7`** pins the browser identity. Same seed, same fingerprint, every
  run; without it each check arrives as a new device, which is not what a
  returning reader looks like.
- **`profile_dir="..."`** (a second keyword argument) keeps a persistent
  profile, so cookies and any login survive between runs. Use an absolute
  path; a relative one resolves from wherever cron happened to start.
- **No model, no key, anywhere in the scheduled path.** The script reads one
  signal; judging what it means is the model's half, and it does not belong
  in the crontab.

A real crontab line, deliberately not on the hour:

```
17 8 * * *  python $HOME/hawk-mon/check_page.py >> $HOME/hawk-mon/$(date +\%F).txt 2>&1
```

The interface (`aihawk ui`) has no scheduler; the recurring path is this
script plus whatever scheduler your system already has.

## What to store between runs

Each run prints one line and exits: nothing carries over on its own, which
means the memory of the monitor is yours to keep. Two files do it:

- **The previous signal.** "Did it change" is a comparison, and with the
  signal in a file the comparison is a diff, not a model call:

  ```bash
  python check_page.py > today.txt
  diff -q last.txt today.txt || echo "changed - go look"
  mv today.txt last.txt
  ```

  The exit code of `diff` is the sentinel: zero means quiet, non-zero means
  something moved. No model can misread a byte comparison.

- **The dated archive.** Keep every line with its timestamp. When the diff
  fires and the question becomes "does this change MATTER", that is the
  judgment half - open `aihawk ui` (or your assistant with this browser
  attached) and ask exactly that, with the two saved lines pasted in. The
  agent earns its per-session cost only on the days something actually moved,
  which is the whole economics of the hybrid this page keeps arguing for.

The strongest architecture is the two-stage hybrid: let the cheap diff monitor
watch constantly, and run the agent only when the diff fires, to judge whether
the change matters and to write the summary. The plain tool does the always-on
part; the model is paid only for judgment.

## Pacing, which is also a signal

A monitor is repeated traffic by definition, so the pacing rules are not
etiquette, they are survival:

- **A fixed clock-minute schedule is itself a signal.** A visitor who arrives
  at exactly :00 every hour, forever, has announced what it is; sites can read
  regularity the same way they read
  [action rhythm](ai-agent-timing-signal.md). Pick odd minutes, and put a
  random sleep in front of the command.
- **Check as rarely as the answer allows.** The right frequency comes from the
  question, not the scheduler's resolution: a policy page that changes yearly
  does not need an hourly reader.
- **Do not retry a failed check inside the same slot.** One check that fails
  should be one log line, not a burst of attempts; agents amplify failures
  into exactly the pattern described in
  [retry loops and rate limits](agent-retry-loops-rate-limits.md). Let the next
  scheduled run be the retry.
- **Honor the site.** Recurring automated visits are the case where reading
  the site's terms and rate expectations is least optional. If the site offers
  a feed or an API for the thing you are watching, use that and retire the
  browser check entirely.

If checks that used to work start failing, resist tuning the prompt first;
work through [why agents get blocked](why-does-my-ai-agent-get-blocked.md), and
remember that with `--seed` unset, every run was a different browser.

## Short answers to the questions that lead here

**Can an AI agent monitor a website for changes?** The watching half is a
scheduled script on the same stealth engine; the judging half is the agent,
invoked when the script's diff fires. Whether the agent belongs in the loop
at all depends on the question: byte-level "did it change" belongs to a diff
tool; "does the change matter" is the agent's case.

**Is an LLM agent overkill for change detection?** For plain change detection,
yes, by orders of magnitude on cost and latency. It stops being overkill when
the check requires reading: meaningful-change questions, prose thresholds,
summarized deltas.

**How do I schedule AIHawk to check a page every day?** Cron (or any
scheduler) plus the `check_page.py` script above on the same engine: `seed`
for a stable identity, `profile_dir` for a persistent profile, and stdout
redirected somewhere dated. There is no built-in scheduler; a script that
prints one line is the building block on purpose.

**What does each check cost?** The scheduled script costs no model tokens at
all: a browser session and a few seconds. The model bill starts only when a
diff fires and you ask the agent whether the change matters, which keeps that
bill proportional to actual changes - the whole point of the hybrid.

**How does the agent know what changed since last time?** It does not, unless
you tell it. Runs share nothing; the script stores each signal to a file, and
when you bring the question to the agent you paste the before and after in as
the baseline to compare against.

**Will a site notice a scheduled agent?** It can: a metronomic schedule is a
tell independent of the browser, and the browser's own realism does not cover
it. Jitter the schedule, keep frequency honest, and read
[the timing-signal page](ai-agent-timing-signal.md) for what regularity gives
away.

## Sources

All retrieved 2026-09-03.

- [dgtlmoon/changedetection.io](https://github.com/dgtlmoon/changedetection.io),
  the self-hosted diff-based monitor referenced as the plain-tool baseline,
  including its scheduling and notification features.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its README and
  source in this repository: the interface entrypoint and the
  open-run-close session behavior in
  [`src/aihawk/runner.py`](https://github.com/feder-cr/AIHawk/blob/main/src/aihawk/runner.py).
- [invisible_playwright](https://github.com/feder-cr/invisible_playwright),
  the engine as a Python library, whose Playwright API the scheduled script
  uses; the script above was executed against books.toscrape.com on
  2026-09-03 and printed the line quoted.

**See also:** [extracting data to a CSV](how-to-extract-data-to-csv-with-an-ai-agent.md),
[agent retry loops and rate limits](agent-retry-loops-rate-limits.md),
[the timing signal AI agents give off](ai-agent-timing-signal.md), and
[which model to use with AIHawk](which-model-to-use-with-aihawk.md) for keeping
per-check cost down.

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The maintainer runs
the two-stage version: a free diff watching always, the agent woken only to
answer "does this matter", which is the only question worth paying it for.*
