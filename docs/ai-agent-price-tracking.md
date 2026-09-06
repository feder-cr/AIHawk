---
title: "Track prices across sites with an AI agent"
description: "How to tell an agent which price to read, check several retailers in one run, ask for a table or CSV, pace re-runs safely, and when a scraper wins."
parent: "Using the Agent"
nav_order: 22
---


# Track prices across sites with an AI agent

Prices hide behind things a plain HTTP request never renders: a widget that
swaps in a discount after a script runs, a country redirect that changes the
currency, a login wall around a member price. A browser agent opens the page
the way a shopper does and reads what is actually on screen, which a static
scraper cannot.

## Why a plain fetch misses the price

A price on a modern retail or travel page rarely sits static in the page a
server first sends. It is assembled after load: a script checks your session
and location, a currency switcher rewrites the number from a cookie or an
inferred country, and a widget crosses out a list price to print a lower one,
itself a small decision, not a value baked into the HTML.

A plain fetch gets whatever was there before any of that ran, often the wrong
number. A browser agent waits for the page to settle, then reads what
actually rendered.

## Writing the task so it reads the one number you mean

The hard part is rarely finding a number on the page. It is making sure the
agent reads the one a shopper would call "the price." Most product pages show
three or four candidates: a crossed-out list price, a flash-sale price, a
coupon-only price, a subscription price beside the one-time price. A vague
"read the price" leaves the model guessing, and it guesses differently
between runs.

Naming the one you want, and what to ignore, fixes that. Typed into
`aihawk ui`, or handed to your assistant with AIHawk's browser attached:

> Go to `<the product page URL>`. Find the price a first-time buyer pays
> today: no subscription, no coupon. Ignore any crossed-out or "was" price. If
> a subscription price sits beside a one-time price, report the one-time
> price. If price differs by size or color, name the default option. Reply
> with one line: price, currency, option if any.

## Checking several retailers in one run

A single run can visit several sellers of the same item and return one line
per seller, the whole point of using an agent instead of five tabs by hand.
List the pages and repeat the same reading rule for each, or the comparison
collapses the moment one seller's number is a sale price and another's a
subscription price:

> Check the current one-time price for `<the item>` on `<url 1>`, `<url 2>`,
> `<url 3>`, in order. Ignore subscription and crossed-out prices everywhere,
> note any assumed size or color, write UNKNOWN if out of stock. Output one
> table: seller, price, currency, in stock, notes.

Bound the list the way you would any extraction: three or four sellers read
reliably in one session, twenty is a longer, costlier run whose clean-output
mechanics belong to
[extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md).

## What to ask for as output

A one-off comparison is fine as a small table in the reply, exactly what the
prompt above asked for. For a comparison you will run again, or paste into a
spreadsheet, ask for CSV instead: a named header row, one line per seller, no
commentary before or after. A model asked for "a table" with nothing more
sometimes hands back markdown nothing else can read; CSV forces a format any
spreadsheet opens without cleanup.

## How often to re-run without hammering a site

A price rarely moves minute to minute outside an active sale, so once a day
covers nearly everything worth tracking. A fixed schedule that never varies is
itself something a site can read, the signal
[the monitoring page](how-to-monitor-a-page-with-an-ai-agent.md) covers in
full, scheduling mechanics included. Jitter the run time instead of the same
clock minute daily, and do not retry inside the same run if a check fails; let
the next scheduled run be the retry.

Each run is a full browser session plus several model turns, real cost, so a
five-minute cadence adds up for something that changes once a day at most. If
a check that used to work starts failing, read
[why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md)
before blaming the price logic.

## When the price sits behind a login or a region redirect

Two obstacles, two fixes. Some prices only appear after signing in, and
`--profile-dir` keeps that session on disk so the agent does not sign in
again next run.

A region redirect is different: the price is locale-specific, and AIHawk's
`--proxy` option sets an egress point the timezone and locale follow, so a
check from the wrong country returns the wrong currency or inventory. Run
through a proxy in the country you need, or accept that a home connection
gives you the price your own market sees; some region prices only surface at
checkout once a local billing address is entered, and no instruction gets
around that.

## Agent or scraper: which wins here

A handful of retailers checked once a day sits in the low-volume,
high-judgment territory where an agent earns its cost, the general trade
[the scraping comparison page](ai-browser-agents-vs-traditional-scraping.md)
works out. Each run is a browser session plus several model turns: real
minutes, real cents, never free.

Once you are watching the same known URLs for the same fields daily, a script
that requests them directly costs a fraction of that per check and never
waits on a model. An agent earns its cost on the one thing a script cannot do
cheaply: deciding which of four visible numbers is "the price" on a page
whose layout you do not control.

## Short answers to the questions that lead here

**Can an AI agent track prices for me?** Yes: it opens each seller's page,
reads the price after scripts and region logic run, and reports the number
you defined as "the price."

**How do I stop it reading the wrong price?** Name the exact price you want
and name what to ignore: crossed-out, subscription, coupon-only prices. A
vague "read the price" reports whichever one the model sees first.

**Can it check several sites at once?** In one session, sequentially: list
the pages, apply the same reading rule to each, and ask for one table or CSV
row per seller.

**Will daily checks get an agent blocked?** A light load at that frequency;
risk grows with volume and a fixed schedule. Jitter the timing, and read
[why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md) if a
working check starts failing.

**Is this better than a scraper?** For a handful of retailers checked daily,
an agent reads a rendered price a raw fetch can miss. Past a few hundred
pages a day, a script is cheaper, faster, and the better tool.

**See also:** [monitoring a page for changes with an AI agent](how-to-monitor-a-page-with-an-ai-agent.md), [extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md), [why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md), and [AI browser agents vs traditional scraping](ai-browser-agents-vs-traditional-scraping.md).

## Sources

Retrieved 2026-09-05.

- [AIHawk README](https://github.com/feder-cr/AIHawk#readme), for the
  `aihawk ui` interface, the `--proxy` option and its effect on timezone,
  locale and egress, and the `--profile-dir` option for keeping a session
  between runs.

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The agent reads
the number that is actually on the screen; catching a mispriced sale banner
before checkout is still the reader's job.*
