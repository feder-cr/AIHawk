---
title: "Using an AI agent to hunt for apartments"
description: "What an agent genuinely does for an apartment search - read listings at volume, compare them against your criteria, watch for new ones - the concrete workflow, and the boundaries that keep the search from becoming scraping."
parent: "Using the Agent"
nav_order: 10
---


# Using an AI agent to hunt for apartments

Apartment hunting is a reading problem wearing a browsing costume. The work
is not clicking through listings; it is holding forty of them in your head
against a dozen criteria - budget, commute, floor, pets, lease length,
which "cozy" means small and which "needs love" means broken - and doing it
again tomorrow when thirty new ones appear. That is judgment applied to
prose at volume, which is precisely the shape of task an AI agent with a
real browser is good at, and precisely the shape a scripted scraper is bad
at, because the facts live in free text and photos, not in stable fields.

This page covers what the agent genuinely does for a search like this, a
concrete workflow with the `aihawk` CLI, and the boundaries stated up
front rather than in the fine print - because listing portals have terms
too, and an agent does not exempt you from them.

## The boundaries, first

**Listing sites have terms of use, and many restrict automation.** The big
portals - Zillow, Apartments.com, Idealista, Rightmove, ImmobilienScout24,
whichever ones serve your market - publish terms, and prohibitions on
scraping and automated access are common; Rightmove's site states flatly
that it "prohibits the scraping of its content." Read the terms of the
portal you actually use before pointing an agent at it. An agent reads a
page the way a person does, one listing at a time under your instruction -
but the terms are the site's call, not this wiki's.

**Volume is still volume.** A person checking twenty listings a day is a
reader; a scheduled sweep pulling five hundred listings an hour is a
scraper, whatever software does the pulling. The signals that get agents
blocked anywhere - rate, rhythm, fingerprint - apply on listing sites too,
and the map for them is
[why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md).
Keep the ask human-sized and most of that page never becomes relevant to
you.

**The agent reads; you contact.** Inquiries to landlords and agents are
messages sent in your name about a place you might live. The agent can
draft one from a listing's details; a human sends it. Auto-sending
inquiries at volume is the rental-market version of the spray pattern, and
it burns the same thing every volume play burns: your credibility with the
people you need to say yes.

## What the agent actually does

**Reads listings against your criteria, not just filters.** Portal filters
stop at structured fields. Your real criteria do not: "ground floor only
if there is a garden," "top floor only with an elevator," "no
north-facing," "landlord-managed preferred." An agent holds the full
criteria list and reads each listing's prose and captions against it,
returning fits, near-misses with the reason, and the disqualified with the
disqualifier named - so you can audit its judgment instead of trusting it.

**Compares across sites that do not compare themselves.** Markets are
fragmented across portals with different layouts and vocabularies. The
agent does not care; a listing page is a listing page. Ask it to check the
same neighborhood on two portals and reconcile duplicates - the same flat
posted twice at different rents is a genuinely useful find.

**Extracts to something you can track.** A search generates state: what you
saw, where, at what price, its status. Have the agent emit each session's
findings as CSV rows and you have a running spreadsheet of the market -
the mechanics and the honest failure modes of that pattern are covered in
[extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md).

**Watches for new listings - with judgment, on a sane schedule.** The
recurring question in a hot market is "anything new today that fits?" That
is a monitoring task where the condition needs reading, which is exactly
when an agent earns its per-run cost over a plain diff tool - the boundary
[the monitoring page](how-to-monitor-a-page-with-an-ai-agent.md) draws in
detail, including when the plain tool wins. Daily is a search; every five
minutes is a bill and a signature.

## The workflow, concretely

Reading listings against criteria is judgment work, so it runs where the
model is: `aihawk ui`, or your assistant with AIHawk's browser attached.
A worked instruction to paste, with the portal URL being whatever
search-results page you have already set up by hand:

> Go to `<your saved search URL>`. Read the first 15 listings.
> My criteria: max 1600/month, 2 rooms, pets allowed, available within 60
> days, no ground floor without outdoor space. For each listing output one
> line: title, price, rooms, floor, verdict FIT/NEAR/NO with the deciding
> reason. Read the listing text, do not trust the summary card. If a fact is
> not stated, write UNKNOWN, do not guess.

The prompt carries the craft, and three parts of it matter more than the
rest. The criteria are explicit and closed - the agent judges against your
list, not its taste. The output is one line per listing with the reason
attached - auditable at a glance. And "UNKNOWN, do not guess" is
load-bearing: listings omit exactly the facts that matter, and an agent
that fills gaps optimistically is worse than none, because a wrong "pets
allowed" costs you a viewing trip.

For the recurring half - "anything new today?" - split the work the way
[the monitoring page](how-to-monitor-a-page-with-an-ai-agent.md) does: a
scheduled script on the same engine captures the listing count or the newest
title each morning, and when that signal moves you bring the judgment prompt
above to the agent. Once a day, or twice in a genuinely fast market. For
interactive sessions - "open the third FIT and tell me what
the photos show about the kitchen" - `aihawk ui` gives you the same
agent beside a live browser view, and if you already use Claude Code or
Claude Desktop, the same browser attaches to your assistant instead
([the setup page](running-aihawk-with-claude-code.md) has the one-liner).

Two practical notes from the field. First, listing portals are heavy,
banner-laden pages; a stronger model earns its cost here more than on
simple pages, and
[which model to use with AIHawk](which-model-to-use-with-aihawk.md) covers
that trade. Second, keep the geography honest: if you run through a proxy
for other work, a search "from" the wrong country gets you the wrong
inventory and prices - plain home connection is the right default for a
local search.

## What stays yours

The agent compresses the reading. It does not - and should not - replace
the parts where the stakes live: viewing the place, judging the
neighborhood at 10pm rather than in the photos, reading the lease, smelling
the damp the wide-angle lens cropped out. Treat its output as a briefing,
verify anything that costs money to believe (a "FIT" is a claim, not a
fact - the listing may have lied, or the agent misread), and never send
money or documents based on a listing nobody has visited. Rental fraud
predates AI and an agent does not detect it for you; a deal that reads too
good in the agent's summary reads that way because it is.

## Short answers to the questions that lead here

**Can an AI agent find me an apartment?** It can read the market for you:
screen listings against real criteria, compare across portals, track what
is new, and draft inquiries. Choosing, viewing, and signing stay human -
as does hitting send on the first message.

**Is it allowed to use an agent on listing sites?** The portal's terms
decide, and several restrict automated access - Rightmove states it
prohibits scraping outright. Read the terms of the site you use; a
human-paced, human-supervised session is a different thing from a scraping
operation, but the line is drawn by the site, not by your tooling.

**How is this different from setting up portal alerts?** Alerts fire on
structured filters; the agent judges prose criteria the filters cannot
express, reconciles across portals, and explains each verdict. Use both:
alerts for speed, the agent for judgment.

**What does it cost per run?** A browser session plus a handful of model
calls - cents per check on the default model, roughly a minute of wall
clock. Fine daily; wasteful as a rapid poller, and a plain diff monitor is
the better rapid poller anyway.

**Will the agent get blocked by listing sites?** At human pace with the
project's browser, usually not - and if it does, work the layers in order
on [the blocking page](why-does-my-ai-agent-get-blocked.md) before blaming
any one of them. A sweep at scraper volume deserves the block, and this
page is not the recipe for one.

**Can it fill out rental application forms too?** Yes, with the same
discipline as any form: draft from your real information, stop at anything
binding, human reviews and submits. See
[getting an AI agent to fill out forms](ai-agent-fill-out-forms.md).

## Sources

All retrieved 2026-09-03.

- The [AIHawk README](https://github.com/feder-cr/AIHawk#readme), for the
  `aihawk ui` command, the MCP path for assistants, and the profile and
  proxy behavior (updated for aihawk 0.3.0, which removed the `do`
  subcommand).
- [Rightmove's terms-of-use page](https://www.rightmove.co.uk/this-site/terms-of-use.html),
  for its stated prohibition on scraping its content, cited as the
  concrete example that listing portals restrict automated access.
- Portal names (Zillow, Apartments.com, Idealista, ImmobilienScout24) are
  used as examples of the category only; no claim is made here about any
  individual site's terms beyond the one quoted above.

**See also:** [monitoring a page for changes with an AI
agent](how-to-monitor-a-page-with-an-ai-agent.md) for the recurring-check
mechanics this page leans on, [extracting data to a CSV with an AI
agent](how-to-extract-data-to-csv-with-an-ai-agent.md) for turning
sessions into a tracked spreadsheet, [which model to use with
AIHawk](which-model-to-use-with-aihawk.md) for the model trade-off on
heavy pages, and [why does my AI agent get
blocked?](why-does-my-ai-agent-get-blocked.md) for when a portal pushes
back.

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The agent
reads the listings; you still take the viewing - and the flat with the
suspiciously wide-angle photos is still small.*
