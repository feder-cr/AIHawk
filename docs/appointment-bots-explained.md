---
title: "Appointment bots: what they are and what an agent can legitimately do"
description: "The bots that hammer government booking calendars, the paid-slot ecosystem around them, what embassies say about it, and the one legitimate agent task: watching availability for yourself and alerting a human."
parent: "Using the Agent"
nav_order: 21
---


# Appointment bots: what they are and what an agent can legitimately do

Searches about appointment bots almost always mean one of two systems:
embassy and consulate visa-appointment calendars, or DMV-type government
booking sites, both defined by the same shortage of open slots. Around that
shortage two very different things have grown: a narrow, legitimate use of
automation, and a paid ecosystem that embassies now publish warnings about.
This page separates them, leads with the legitimate one, and quotes the
official sources on the rest.

## The legitimate slice: watch for yourself, book by hand

There is exactly one appointment-related task this wiki considers an agent fit
for: watching availability for yourself, and telling you when it changes. That
is not a special appointment feature, it is ordinary page monitoring, and the
full treatment already exists on
[the monitoring page](how-to-monitor-a-page-with-an-ai-agent.md): checking a
page the way a patient person would, remembering what was seen last, and
raising an alert instead of taking an action. Applied here, the shape is a
check of the public availability page at a human cadence, an alert to you when
something opens, and then you, in your own session, as yourself, doing any
actual booking by hand.

Three properties separate this from everything described below, and all three
have to hold: it is your own appointment need, not a service to others; the
checking rhythm is what a person would do, not what a machine can do; and a
human makes the booking. This page does not go one step further than that.
There are no auto-booking instructions here, and the rest of the page is the
explanation of why.

Two neighbouring tasks sit inside that same boundary, because both read and
neither acts:
[checking order and delivery status with an AI agent](check-an-order-status-with-an-ai-agent.md),
where the value is in the account pages rather than the carrier's, and
[collecting event and course listings with an AI agent](collect-event-listings-with-an-ai-agent.md),
which stops at recording what is offered and never registers for any of it.

Conflict of interest, declared where it belongs: you are reading the wiki of a
browser-automation tool. An agent can be pointed at either half of this
subject, which is exactly why the boundary is written down rather than left to
the reader's imagination.

## What an appointment bot actually is

Mechanically, an appointment bot is a program that polls a booking calendar at
high frequency and reacts the moment a slot appears. The polling is the whole
trick: cancelled or newly released slots surface at unpredictable times and
disappear in minutes, so a bot checks many times a minute, around the clock,
which no person can or would do. What happens on a hit divides the category in
two: alerting bots notify a human, booking bots seize the slot themselves,
logged in with someone's credentials, at machine speed.

That polling profile is also the built-in weakness. Checking a page hundreds
of times an hour is a pure volume signature, the third of the four layers on
[why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md), and
the way automated loops amplify it has its own page,
[agent retry loops and rate limits](agent-retry-loops-rate-limits.md). No
fingerprint work and no clean address survives a request rate that announces
itself, and booking systems do not need anything sophisticated to see it:
they count.

The systems say so themselves. The FAQ of the Italian Consulate General in
London, on the Italian foreign ministry's own booking platform, explains that
an account still locked after the ordinary 24 hours "has been automatically
blocked by the system", and that this "typically occurs when anomalies are
detected, such as booking attempts that are too rapid to be performed by a
human operator (e.g., the use of bots) or multiple booking attempts across
different services." That is a government booking system stating, in its own
help text, that too fast is the tell and an automatic block is the response.

## The paid slot ecosystem, told honestly

Where slots are scarce, intermediaries run booking bots at scale, seize
appointments as they are released, and sell them. This is the half of the
subject that official sources have started addressing by name, and their
statements are worth reading in full.

The U.S. Embassy in Santo Domingo maintains a page titled "Beware of Visa
Fixers, Bots, and Offers of Earlier Visa Appointments". It advises applicants
to "stay far away from visa fixers offering earlier appointments", says the
embassy "is aware of individuals who are attempting to manipulate the visa
appointment system through bots and other unauthorized methods", and spells
out what manipulation costs the applicant: "Potential consequences include:
appointment cancellation, visa refusal, and visa cancellation." The same page
adds the sentence that frames the whole ecosystem: "Any attempt to manipulate
the appointment system is both unfair to other applicants and puts your
application at risk."

Enforcement is not hypothetical. In March 2025 the U.S. Embassy in India
publicly announced that it was canceling about 2,000 visa appointments made by
bots and suspending the scheduling privileges of the associated accounts,
stating zero tolerance for agents and fixers who violate its scheduling
policies; the announcement is cited by name in the sources below.

And the question people actually type, answered plainly: **can a visa bot
guarantee approval?** No, and approval was never the bot's to give. A bot
touches a calendar; a visa decision is made by a consular officer, on the
applicant's own case, at the interview the slot merely schedules. A paid slot buys, at
best, the same interview and the same decision; at worst, per the embassy's
own list, it costs the appointment or the visa because of how the slot was
obtained. Anyone selling a "guaranteed"
outcome is selling something that is not theirs.

## A public queue, degraded for everyone

One more thing needs saying without hedging. Government booking systems are a
public service with a fixed pool of slots. A bot does not create appointments;
it moves them, to whoever paid, away from whoever did not. And the polling
itself has a cost even before any slot is taken: a public calendar hammered
around the clock by scripts serves everyone worse, and pushes the operator
toward tighter limits and stricter defenses that ordinary applicants then
climb over. Hammering a public queue is not a clever trick around scarcity; it
is queue-jumping that also degrades the queue.

That is the fairness half of why the legitimate slice at the top of this page
is drawn where it is: watching for yourself at a human cadence takes nothing
from anyone.

## Short answers to the questions that lead here

**Can a visa bot guarantee approval?** No. Approval is decided by a consular
officer on your case, not by whoever booked the slot, and it was never the
bot's to give. Official warnings add that manipulated bookings risk
appointment cancellation, visa refusal, and visa cancellation.

**Do appointment bots work?** They can seize slots, which is exactly why
embassies act against them: bot-made appointments have been cancelled by the
thousands and the accounts behind them suspended. Whatever a bot books, the
system can unbook.

**Are appointment bots allowed?** The booking systems' own help pages describe
automatic blocks for bot-speed activity, and embassy statements attach
consequences up to visa cancellation. Between those two sources there is no
reading under which they are welcome.

**Can an AI agent watch appointment availability for me?** Watching a public
availability page for your own need and alerting you is page monitoring, and
[the monitoring page](how-to-monitor-a-page-with-an-ai-agent.md) covers doing
it at a human cadence. The booking itself stays yours, by hand.

**Why do booking-site accounts get blocked?** Because high-frequency checking
is a volume signal the systems watch for; one consulate FAQ names "booking
attempts that are too rapid to be performed by a human operator" as a trigger
for automatic blocks. The general mechanics are on
[the blocked page](why-does-my-ai-agent-get-blocked.md) and
[the retry-loops page](agent-retry-loops-rate-limits.md).

**Should I pay someone who says they have appointment slots?** The embassy
warning quoted above tells applicants to stay far away from fixers, and its
consequence list falls on the applicant, not the seller. The money buys, at
best, an interview that was never theirs to sell.

## Sources

Retrieved 2026-09-03 unless noted.

- [Beware of Visa Fixers, Bots, and Offers of Earlier Visa Appointments](https://do.usembassy.gov/beware-of-visa-fixers-bots-and-offers-of-earlier-visa-appointments/),
  U.S. Embassy in the Dominican Republic, for the warning and consequence
  quotes.
- [FAQ, booking system, Consulate General of Italy in London](https://conslondra.esteri.it/en/info-utili/f-a-q/faq-sistema-di-prenotazione/),
  for the automatic-block quote on too-rapid booking attempts.
- [U.S. Embassy India statement, March 2025](https://x.com/USAndIndia/status/1904843783201583522),
  cited by name and URL: the platform does not permit retrieval, so nothing is
  quoted from it here; the cancellation of about 2,000 bot-made appointments
  and the account suspensions it announced were corroborated across
  contemporaneous press coverage found in this session's searches.

**See also:**
[monitoring a page for changes with an AI agent](how-to-monitor-a-page-with-an-ai-agent.md),
[agent retry loops and rate limits](agent-retry-loops-rate-limits.md),
[why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md), and
the rest of [Using the Agent](guides-using-the-agent.md).

---

*From the [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) wiki. The agent is good
at watching pages patiently; the maintainer's position is that booking stays a
human act, in your own name, at the queue's own pace.*
