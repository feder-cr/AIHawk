---
title: "Checking order and delivery status with an AI agent"
description: "Orders sit in a dozen accounts and three carrier sites. What an agent is genuinely good at here, why the carrier page is the easy half, and the one thing to check before automating any of it."
parent: "Using the Agent"
nav_order: 60
---

# Checking order and delivery status with an AI agent

The problem is not hard, it is scattered. Five orders live in five accounts, each
hands off to a carrier, each carrier has its own page, and none of them tells you
anything until you go and look. An agent that opens all of them and writes one
list is a good use of an afternoon's setup.

Before building it, one question decides the whole design.

## Ask whether there is a feed first

Many retailers and most carriers send email on every state change, and a growing
number expose a tracking page that needs no login. If the information reaches you
already, an agent that logs in and reads a page is the harder route to the same
place.

Use the browser for the parts that genuinely require it: an account that emails
nothing, a portal with a status not in any notification, a supplier whose tracking
lives behind a login. That is a real list and it is shorter than the one people
start with.

## The two halves are not equally hard

**The carrier page is the easy half.** Usually a tracking number in a URL, no
login, one page, a status and a date. An agent reads it in one navigation and one
text read, which together are hundredths of a second plus the page load. If all
you have is tracking numbers, this is nearly trivial and barely needs an agent at
all.

**The account page is the hard half**, and it is where the value is. It has the
order, the items, the amount, the seller, and the status before a carrier is
involved at all: preparing, backordered, partially shipped, cancelled. That
information exists nowhere else, and reaching it means a session per retailer.

Design for the second and get the first for free.

## Sessions are the real work

One persistent profile per account, kept between runs, so a slow login is paid
once:

```
STEALTHFOX_PROFILE_DIR=C:/profiles/retailer-a
```

Expect to log in again periodically anyway: shopping accounts expire sessions
aggressively and some of them will want a code by email or phone. Plan for a
human step rather than trying to engineer it away, which is the position taken in
[getting an AI agent to log into a website](ai-agent-login-to-a-website.md).

**The check that matters most here**: after navigating to the orders page, confirm
you are logged in before reading anything. An expired session serves a login form
where the order list was, and an agent that does not check will cheerfully report
that you have no orders. That silent-wrong-page failure is the one described in
[when the page changes under the AI agent](when-the-page-changes-under-the-agent.md),
and on this task it produces an answer that looks fine and is empty.

## Statuses do not mean the same thing

Every retailer invents its own vocabulary, and normalising it is where this task
either becomes useful or becomes a second thing to read.

Keep two columns: the **raw status string** exactly as the page said it, and a
**normalised state** from a small set you define, say ordered, preparing,
shipped, out for delivery, delivered, delayed, cancelled, unknown.

Two columns rather than one, for the same reason as everywhere else in this
corpus: the normalisation is a judgement and the raw string is a fact, and when
the mapping turns out to be wrong you want the fact still there. `unknown` must be
in the set, or the agent will map an unfamiliar status onto the nearest familiar
one, which is how a delayed order gets recorded as shipped.

## The delivery date is the field that lies

Carriers show an estimate, and the estimate changes. Capture it with the date you
read it, because "arriving Thursday" recorded on Monday and "arriving Thursday"
recorded on Wednesday are different facts and the column will not distinguish
them.

If you are running this on a schedule, keep the history rather than overwriting:
the useful signal is not today's estimate, it is that today's estimate moved.

## A task that works

> For each row in orders.csv with a status that is not "delivered" or
> "cancelled":
>
> Open the retailer's order page using the profile named in the row. Before
> reading anything, confirm the page shows my account and not a login form; if it
> shows a login form, write "login needed" in the status column and move to the
> next row.
>
> Record the raw status string exactly as shown, a normalised state from
> [ordered, preparing, shipped, out for delivery, delivered, delayed, cancelled,
> unknown], the tracking number if present, and the delivery estimate with
> today's date.
>
> If there is a tracking number and the carrier page needs no login, open it and
> record the carrier's own status and estimate in separate columns. Do not log in
> to any carrier.
>
> Append to orders-history.csv rather than overwriting, so estimates can be
> compared between runs.

## What not to do

**Do not check every few minutes.** Nothing about a parcel changes that fast, and
a logged-in account polling a retailer at that rate is the volume pattern in
[agent retry loops trip rate limits, not fingerprints](agent-retry-loops-rate-limits.md)
against an account with your name on it. Once or twice a day answers every real
question.

**Do not act on what you find.** Reading a status is safe. Cancelling, returning,
reordering or contacting support are irreversible in the way that
[keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md)
describes, and they belong behind a person.

## Short answers to the questions that lead here

**Can an AI agent track my orders?** Yes, and the value is in the retailer's
account pages, not the carrier pages. Carrier tracking usually needs no login and
barely needs an agent.

**How often should it check?** Once or twice a day. Higher frequency tells you
nothing new and puts an unusual access pattern on an account in your name.

**Why does it say I have no orders?** Almost certainly an expired session
returning a login page. Have the task confirm it is logged in before it reads
anything.

**How do I compare statuses across shops?** Keep the raw string and a normalised
state in separate columns, and make sure "unknown" is one of the allowed
normalised values.

**Should the agent contact support or cancel things?** No. Reading is safe;
anything that changes the order should be proposed to you and done by you.

**See also:**
[tracking prices across sites with an AI agent](ai-agent-price-tracking.md), which
is the same polling shape on public pages, and
[running an AI browser agent on a schedule](run-ai-agent-on-a-schedule.md) for
making this unattended without making it frequent.

## Sources

- No external figures are cited: the claims here are about how retail and carrier pages are structured and about task design. The per-action costs referred to in passing are measured on [how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md).
- No retailer, marketplace or carrier is named anywhere on this page.

---

*The account page is the half worth automating and the half everybody skips,
because the carrier page is the one that looks like the problem.*
