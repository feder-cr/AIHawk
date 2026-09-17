---
title: "Seeing a page as it appears in another country"
description: "Price, stock and availability change by country, and checking from your desk shows you your own version. What actually decides which page you get, and the four things that have to agree."
parent: "Using the Agent"
nav_order: 53
---

# Seeing a page as it appears in another country

Plenty of pages are not one page. Prices, availability, delivery options, tax
display, the legal text and sometimes the whole layout depend on where the
request appears to come from. If you check from your desk you see your own
version, and if you are comparing markets that is the one version that is useless
to you.

Getting the other version is not a trick. It is making four things agree.

## The four things a site looks at

**The exit IP.** The big one, and the one that resolves first. Geolocation
databases map the address to a country, and most sites branch on that before
anything else has loaded.

**The `Accept-Language` header.** Sent on every request. A German IP with an
`en-US` header is a combination that exists, so it will not break anything, but
some sites branch on the header rather than the IP and you get a different
answer than you expected.

**The browser's own locale and time zone.** Read from JavaScript, used by the
page's own formatting and often reported back to the site. A page can compare
what the browser says with what the IP implies.

**Whatever you already told it.** A country cookie, a `?country=` parameter, an
account preference, a redirect it did for you last week and remembered. This one
beats all three above and is the usual reason a careful setup still shows the
wrong version.

## Making them agree

With this browser the first three come from one place. Point the session at an
exit in the country you want, and **the time zone, the locale and the egress are
derived from it together**, rather than being three settings you have to keep in
sync by hand:

```
STEALTHFOX_PROXY=http://user:pass@your-proxy-host:8080
```

Bring your own exit: the variable takes a URL and the project does not supply
one. Per browser rather than per process, `browser_open` takes a `proxy`
argument, so a single session can hold one browser on one country and a second
on another, which is what a comparison actually wants.
[The MCP server page](mcp-server.md) has the full list of settings and what each
one overrides.

The fourth thing is yours to deal with, and it is the one that bites.

## The cookie is why your careful setup shows the wrong page

You set an exit in France, you load the site, and it shows you the same prices as
before. Almost always the profile is carrying a country choice from an earlier
visit, and that choice outranks geography by design: a site that lets you pick a
market will not second-guess you.

Two reliable ways out. Use a **fresh profile per country**, which is the cleanest
and costs you any logins. Or check the site's own market selector and set it
explicitly, then confirm on the page rather than assuming.

A persistent profile is what you want for logins and exactly what you do not want
for this. If you are doing both in one run, keep them in different profiles.

## Confirm before you believe

The step people skip. Before reading the number you came for, have the agent
confirm the page is the one you think it is: the currency symbol, the domain it
redirected to, the country in the footer, the market selector's current value.

It is one free read, in the sense established in
[how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md),
and it turns a silently wrong comparison into an early stop. A table of prices
where three rows are secretly your own market is worse than no table, because
nothing about it looks wrong.

## A task that works

> Open a browser for each of these three exits: France, Germany, Spain. On each
> one, go to the product page below, and before reading anything confirm the
> currency and the country shown in the footer. Then record the displayed price,
> the currency, whether tax is stated as included, and the earliest delivery date
> offered. Write one row per country to markets.csv, including the confirmation
> values you read. If the footer country does not match the exit you were given,
> write "mismatch" in the price column and stop for that country.

The last sentence is the whole discipline: it makes the check load-bearing rather
than decorative.

## What this does not fix

An exit in a country is not a customer in that country. Sites also branch on the
account, on the payment method, on a loyalty tier, and on a currency you selected
once. A price behind a login is the account's price, wherever the request came
from.

And a datacentre address in the right country is still a datacentre address,
which some sites treat differently from a residential one for reasons that have
nothing to do with geography. That is a separate subject with its own page on the
engine side:
[ASN and IP reputation](https://github.com/feder-cr/invisible_playwright/wiki/asn-and-ip-reputation-in-bot-detection).

## Short answers to the questions that lead here

**How do I see a website as another country sees it?** Point the session at an
exit in that country, so the IP, time zone and locale agree, and clear or avoid
any stored country preference, which outranks all three.

**Why does the site still show my own country?** A cookie, an account setting or
a remembered redirect. Use a fresh profile, or set the market selector
explicitly.

**Is changing the language header enough?** No. Most sites decide on the IP and
only some read the header. Changing one of the four in isolation produces a
combination you did not intend.

**Can I check several countries at once?** Yes. `browser_open` takes a proxy per
browser, so one session can hold one browser per market, which is also the only
honest way to compare them at the same moment.

**Do I need a proxy for this?** For a different country, yes, and you bring your
own. Without one the session goes out from your own address and you get your own
version of the page.

**See also:**
[running one AI agent task across a list of sites](run-one-task-across-a-list-of-sites.md),
because a market comparison is a list task with an extra dimension, and
[tracking prices across sites with an AI agent](ai-agent-price-tracking.md), where
the same page changing by country is a source of false movement.

## Sources

- The settings named here are this project's own, read from [the MCP server page](mcp-server.md) and confirmed against the running server's tool list on 2026-09-17: `browser_open` accepts `browser`, `seed`, `proxy` and `profile`.
- No proxy provider is named anywhere on this page, deliberately. The variable takes any URL and the choice is yours.

---

*The four-things framing is the part to keep. Most guides cover the exit address
and stop, and the stored country preference beats the exit address every time.*
