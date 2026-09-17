---
title: "Filling a CRM record from a company's website"
description: "Enrichment done by reading the site rather than buying a database. What is reliably on a company site, what is not, and the field that is wrong often enough to poison the rest."
parent: "Using the Agent"
nav_order: 57
---

# Filling a CRM record from a company's website

Enrichment vendors sell this as a lookup. Doing it with an agent reading the
actual site is slower per record and better in one specific way: you get the
company's own current words rather than a snapshot of somebody's database, and
you get a URL for every claim.

It is also worse in ways worth stating before you build it, which is most of this
page.

## What is reliably on a company site

These are worth asking for, in rough order of how often they are actually there:

- **What the company says it does**, in its own words, from the homepage or the
  about page. The single most useful field and the one no database has in a form
  you would want to read.
- **The legal entity name and registered address**, usually in the footer, the
  imprint, the terms or the privacy policy. Often more accurate than the trading
  name you started from.
- **Segment and positioning signals**: whether pricing is public, whether there is
  a free tier, whether the customer logos are enterprises or small businesses,
  whether there is a careers page at all.
- **The technology and integration surface**: an integrations page, a developer
  section, a status page. Strong signal for a technical sale and rarely in a
  bought dataset.
- **Contact routes the company publishes**: a general address, a support form, a
  phone number.

## What is not reliably there, and pretending otherwise is the main failure

**Headcount.** A site almost never states it. Anything an agent returns for this
field is an inference from the team page or a guess, and it will be confidently
wrong.

**Revenue.** Same, more so.

**Named individuals and their contact details.** Sometimes present, and this is
where you stop and think about what you are doing rather than about whether you
can. Personal data has rules that do not care that the page was public, and a
task that scoops up names and emails because they were visible is the shape most
likely to be a problem later. Collect roles and public company channels; leave
individuals alone unless you have a reason that survives being written down.

**Anything a site has an interest in overstating.** Customer counts, "trusted by",
awards. Record them as claims with the URL, never as facts.

## The design that makes it usable: two fields per fact

One field holds the value. The second holds where it came from.

Every row you write gets the URL the value was read from, and ideally the phrase.
This costs nothing at write time and it is the difference between a CRM you can
act on and one nobody trusts after the first wrong entry. When a salesperson
finds a record that says the wrong thing, the question is always "where did this
come from", and either you can answer it in one click or the whole dataset loses
credibility.

Add a third, blunt field: **confidence, with only two values.** Read it, or
inferred it. The agent knows which, and forcing the distinction stops inference
from being laundered into fact somewhere between the page and the spreadsheet.

## Say what "not found" looks like

The most common way this task degrades is an agent that will not return empty. It
was asked for an industry, the site does not say, so it produces a plausible one.
Nothing in the output marks it, and it is indistinguishable from the ones that
were read.

The instruction that prevents it is one sentence: **write "not stated" and move
on, and never infer a value into a field marked as read.** It is the same escape
hatch as in
[giving an AI browser agent a stopping condition](giving-an-ai-agent-a-stopping-condition.md),
applied per field rather than per run.

## A task that works

> For each domain in companies.csv, open the site and fill these columns:
> one-sentence description in the company's own words, legal entity name,
> registered address, whether pricing is public (yes/no/partial), whether there is
> a free tier, and up to three integrations named on the site.
>
> For every column also write the URL you read it from and whether you read it or
> inferred it. If the site does not state something, write "not stated" and leave
> the source blank: do not infer a value into a column marked "read".
>
> Do not collect names or contact details of individuals. Stop after eight pages
> on any one company and write what you have.

## Where the time goes, and what that means for the list

Reading is free and pages are slow, so per company the cost is roughly the number
of pages you open. Six pages is a comfortable budget for the fields above: home,
about, pricing, integrations, footer legal, and one spare.

That makes this a list task, with everything that implies about writing rows as
you go and giving failures a value. The discipline is in
[running one AI agent task across a list of sites](run-one-task-across-a-list-of-sites.md),
and at this scale it is what decides whether you get two hundred rows or a
mystery.

## Short answers to the questions that lead here

**Can an AI agent enrich CRM records?** For what a company publishes about
itself, well, and with a source for every field. For headcount, revenue and
people, no: the site does not say, so the agent infers.

**How do I stop it inventing values?** Require a source URL per field and a flag
saying read or inferred, and instruct it explicitly to write "not stated" rather
than fill a gap.

**Is this better than an enrichment vendor?** Different. You get current wording
in the company's own voice with a citation; they get you structured firmographics
you cannot verify. Several teams use both and reconcile.

**Should the agent collect email addresses from the site?** Company channels, if
you need them. Individuals, only with a reason you are prepared to write down:
public does not mean unrestricted.

**How many pages per company?** Around six covers the fields worth having. Set it
as a ceiling so one sprawling site does not consume the list's budget.

**See also:**
[building a lead list with an AI browser agent](ai-agent-lead-list.md), which is
the discovery step that produces the domains this page reads, and
[moving data between two web apps with an AI agent](move-data-between-web-apps-with-an-ai-agent.md)
for getting the finished rows into the CRM itself.

## Sources

- No external statistics are cited on this page, because the claims are about how company websites are structured and about task design, and inventing a number for either would be worse than having none.
- The per-field discipline (source URL, read-or-inferred, explicit "not stated") is the same pattern this project applies to its own measurements, for the same reason.

---

*The two-field rule is the part worth stealing even if you never use an agent for
this. A value without a source is a value nobody will act on twice.*
