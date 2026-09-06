---
title: "Browser problem or model problem?"
description: "When an agent task fails, one of two very different things broke. How to tell them apart with a model-free replay on the same engine and a two-model comparison, before spending on either fix."
parent: "Using the Agent"
nav_order: 3
---


# Browser problem or model problem?

When an agent task fails, one of two very different things broke: the browser
side (the page never arrived, or arrived hostile) or the model side (the page
was fine and the model mishandled it). The fixes have nothing in common -
network and identity on one side, model choice and instructions on the other -
so misdiagnosing sends you shopping in the wrong store. People upgrade to a
frontier model to fix a blocked page, and swap proxies to fix a model that
clicks the wrong button, and both spend money to change nothing.

There is an unusually clean way to split the two, and it costs nothing in
model tokens: replay the failing step on the same engine with no model in the
loop at all. The stealth Firefox that AIHawk drives is on PyPI as a plain
Python library (`pip install invisible-playwright`, Playwright's API), so a
model-free replay is a few lines in a Python shell. Whatever happens in that
replay happened without a model, so it cannot be a model problem. That is the
instrument this page is built around.

## The instrument: the same browser with no model attached

This exact replay was executed against the public scraping sandbox while
writing this page, and it prints `Travel | 11 results`:

```python
from invisible_playwright import InvisiblePlaywright

with InvisiblePlaywright(seed=7) as browser:
    page = browser.new_page()
    page.goto("https://books.toscrape.com/", wait_until="domcontentloaded")
    page.click('a[href*="category/books/travel"]')
    page.locator('h1:text("Travel")').wait_for()
    print(page.locator("h1").inner_text(), "|",
          page.locator("form strong").first.inner_text(), "results")
```

Each call is the same engine, the same fingerprint work, the same connection
path the agent would use - minus the model. One line of hard-won detail is in
there on purpose: after a `click` that navigates, wait for something the
DESTINATION shows (`wait_for()` on its heading) before reading. The first
version of this snippet read the old page's heading and reported the wrong
page confidently - which is exactly the kind of off-by-one a model in the
loop would have papered over.

Swap in your own URL, your own selectors, and the failing step, and you can
see verbatim what the browser saw with zero model behavior mixed in.

## Symptoms that point at the browser side

These appear with any model, and with no model:

- **The page never loads.** `page.goto` times out or errors in the model-free
  replay too. Network, proxy, or the site itself. If a proxy is configured,
  suspect it first; if this is the first run ever, see the last symptom below.
- **A challenge page or block message appears instead of the content.**
  `page.locator("body").inner_text()` in the replay shows you verbatim what
  the site served. If the block is there before any automation logic has
  acted, no model change can touch it - work through
  [why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md),
  which separates fingerprint, IP reputation, volume and rhythm.
- **It works by hand in your normal browser, but not through AIHawk, on the
  same network.** That narrows it to the agent's exit or identity rather than
  the site being down. The blocked page's checklist is the map.
- **It worked for many pages, then stopped.** Volume or retries, not
  intelligence. Check the transcript for a retry burst;
  [retry loops and rate limits](agent-retry-loops-rate-limits.md) is that
  failure's own page.
- **The very first instruction ever hangs for minutes.** Probably not a
  failure at all: the browser engine, roughly a quarter of a gigabyte, downloads
  on the first request that needs a page. `invisible-playwright fetch` in a
  terminal gets it over with where you can watch it.

## Symptoms that point at the model side

These appear only with a model in the loop, on pages the model-free replay
handles fine:

- **The right page, the wrong element.** The transcript shows the page loaded
  and the model clicked or typed somewhere defensible but wrong. Often a
  field-mapping problem - [the forms page](ai-agent-fill-out-forms.md) covers
  why look-alike fields invite it.
- **Loops.** The same action, or the same failing submit, repeated with no
  change in between. A model that does not register that its last action
  changed nothing.
- **Giving up, or declaring victory early.** An answer that does not match
  what the live pane showed, or a "done" with steps visibly left.
- **Misreading the task.** It did something coherent, just not what you asked.
  Usually fixable with a more explicit instruction before it is a reason to
  change models.
- **The turn ceiling.** An error saying the task did not finish within
  `max_turns=25` means the model spent 25 turns without converging. On a
  genuinely long task, that is the task's problem; on a short one, it is the
  model wandering.
- **Unreadable tool arguments.** The transcript notes the model's arguments
  were not valid JSON and it was told to retry. Occasional is tolerable;
  frequent is a model quality signal in itself.

## The procedure

1. **Read the failed transcript first.** The interface shows each step, what
   was called, and what came back; on the assistant path the same record is
   your assistant's own conversation. Most failures are legible there, and the split is often obvious:
   a block page in a tool result is browser-side, a wrong click on a healthy
   page is model-side.
2. **Replay the failing step with no model.** In a Python shell, on the
   library: `goto` the same URL, read what came back, `click` the same
   selector (the executed snippet above is the template). If the failure
   reproduces, it is browser-side, full stop - no model was present. If your
   hand-driven steps sail through, the page is drivable and the model is the
   variable.
3. **Same task, two models.** If step 2 cleared the browser, run the identical
   instruction with `--model` set to something stronger, and pass the same
   `--seed` both times so the browser identity is constant and the model is
   the only thing you moved. One model failing where another succeeds, on the
   same page and identity, is the clean model-side verdict - and the moment to
   read [which model to use](which-model-to-use-with-aihawk.md).
4. **Change one thing at a time.** Swapping model and proxy together tells you
   nothing whichever way it goes. This is the same discipline as the blocked
   checklist, because it is the same trap.

## When it is honestly both

The two sides feed each other. A page that starts refusing mid-task makes a
competent model look lost, because every read comes back strange; and a model
that reacts to failure by hammering retries turns one soft refusal into a hard
block, which then greets the next run too. If a transcript shows both, fix the
browser side first: it is upstream, and model behavior on a hostile page is not
evidence about the model. Then rerun before judging anything else.

## Short answers to the questions that lead here

**How do I know if my agent failed because of the site or the model?** Replay
the failing step on the library with no model in the loop. Reproduces
without a model: browser side. Works by hand: model side. That single test
settles most cases.

**The page shows a challenge or block - which side is that?** Browser side,
always: it was served before any model decision mattered. Work through
[the blocked page](why-does-my-ai-agent-get-blocked.md); changing models
changes nothing there.

**The agent clicks the wrong thing - which side?** Model side, if the
transcript shows the page loaded correctly. Try a sharper instruction first,
then a stronger model on the same task and seed.

**What does the max_turns error mean?** The model used its 25-turn budget
without finishing. On a short task, that is a model-side symptom; on a long
one, split the task into smaller instructions before blaming anything.

**Can I run this diagnosis without spending anything?** The replay half, yes -
the library needs no model and no key, and the engine download is one-time.
The two-model comparison spends normal task tokens on each run.

**Is the replay still useful if I already have a key?** Precisely because it
removes the model: any failure it reproduces is guaranteed browser-side,
which is a certainty no model-driven run gives you.

## Sources

All retrieved 2026-09-03.

- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), this repository's
  source: `src/aihawk/agent.py` (the shared loop, the
  turn ceiling, the invalid-arguments retry), and the README (the
  engine download and prefetch command).
- [invisible_playwright](https://github.com/feder-cr/invisible_playwright),
  the engine as a library; the replay snippet above was executed against
  books.toscrape.com on 2026-09-03 and printed the line quoted.

**See also:** [why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md),
[which model to use with AIHawk](which-model-to-use-with-aihawk.md), and
[agent retry loops and rate limits](agent-retry-loops-rate-limits.md).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The model-free
replay is how the maintainer runs this exact split while debugging; the wrong
first version of the snippet above is left described because that is how it
went.*
