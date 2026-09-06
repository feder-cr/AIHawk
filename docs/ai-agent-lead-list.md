---
title: "Build a lead list with an AI browser agent"
description: "What to collect for a lead list, what never to collect, the GDPR/CAN-SPAM caveat in plain terms, and how to verify rows before trusting them."
parent: "Using the Agent"
nav_order: 23
---


# Build a lead list with an AI browser agent

A lead list is rows of public information about organizations worth
contacting: company name, sector, a public contact page, and one fact worth
citing in an outreach email. A browser agent reads company pages, directories
and exhibitor lists the way a person would and writes those rows down, if you
tell it exactly what counts as a lead and what to skip.

## What "a lead list" means here

A "lead" here is an organization, not a person: a company, a nonprofit, an
exhibitor, a vendor in a directory. The list is a small number of facts about
each one, gathered from pages the organization itself published to be read:
an about page, a directory listing, a press page. The point is arriving at a
conversation with something specific to say, not harvesting an inbox at
scale.

If the task is closer to open-ended research, comparing sources or
summarizing a debate, that is covered on
[AI agents for web research](ai-agent-web-research.md); a lead list is
narrower: the same handful of fields, repeated across many organizations.

## What to collect, row by row

Four fields carry the whole list, and each earns its place:

- **Company name and sector.** The two facts that let you sort the list,
  sector read from the directory or exhibitor category, not your own guess.
- **A public contact page URL, not a person's inbox.** The company's own
  about or contact page, the address it published for this purpose, not an
  individual's email pulled from a page never built as a directory.
- **One fact worth citing.** A specific detail on the page: a product line, a
  stated focus, a location. It turns a template into something that reads
  like it was written for that one company, and it is the one field a
  template cannot fake.
- **The source URL and the date read.** Company pages change; a row without
  its source cannot be re-checked when something looks wrong, and a stale
  row is worse than none.

## What not to collect

Three lines, and each is a different kind of risk:

- **Personal data harvested at scale is a different job, and a legal one.**
  An individual's name, personal email or phone number, collected in bulk, is
  personal data under rules like the EU's GDPR, and unsolicited commercial
  email is regulated too, under rules like the US's CAN-SPAM Act. Neither is
  explained here, and this is not legal advice: check what applies to your
  case before building a list of *people* rather than *organizations*.
- **Anything behind a login you were not given stays off limits**, same as
  any automated access: an agent typing credentials it was not handed is not
  something this page instructs.
- **Anything a site's terms forbid stays forbidden regardless of the tool.**
  Directories often publish their own rules on bulk collection; read them
  before pointing an agent at the page.

## Where the rows come from

Rows come from pages an organization already published to be read: a
company's own about or contact page, a business directory, a conference's
exhibitor list. Typed into `aihawk ui`, or handed to your assistant with
AIHawk's browser attached:

> Go to `<the exhibitor list page>`. For each exhibitor, open its entry and
> its own site if linked. Collect: company name, sector as the directory
> states it, a public contact or about page URL, and one specific fact worth
> mentioning in an email. Skip any exhibitor with no public site. Do not
> collect names or emails of individual people. Output one CSV row per
> company: name, sector, contact_url, fact, source_url, date_checked.

Bound a run the same way: a few dozen exhibitors in one session reads
reliably; a directory of thousands is a slower, different task. The
mechanics of clean CSV output belong to
[extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md).

## Verifying rows before you trust them

A model can misread a directory's category, invent a "fact" that sounds
plausible but is not on the page, or grab the wrong company's site when two
names are similar. Spot-check a sample of rows against the live page before
using the list for anything.

A paraphrased fact that turns out wrong in an actual email is worse than no
fact at all. Re-open each contact URL once more before you send anything,
since a page can change between the run and the message.

## From rows to a spreadsheet

Once the list exists as CSV, landing it in a spreadsheet is a separate,
smaller task: paste the rows in, or import the file directly. The mechanics,
and where a spreadsheet's own import functions beat asking an agent to do the
pasting, are covered in
[getting website data into Google Sheets with an AI agent](website-data-to-google-sheets-ai-agent.md).

## Pacing a list-building run

Treat a directory or exhibitor page the same as any repeated traffic: a few
dozen rows in one sitting reads like a person working through a list, and a
script that revisits the same directory every few minutes reads like
something else.

Bound the run by count, not by time, run it once rather than on a loop, and
stop at the first sign the site is pushing back rather than retrying
immediately. A one-off build for an upcoming event rarely needs repeating at
all.

## Short answers to the questions that lead here

**Can an AI agent build a lead list for me?** Yes, for organizations rather
than individuals: it can read company pages, directories and exhibitor lists
and write out a name, sector, a contact page and one usable fact per row, if
you tell it exactly which fields count.

**Is it legal to scrape company data for lead generation?** It depends what
you collect and where you operate. Company-level facts carry lower risk than
personal data about named individuals, and rules like the EU's GDPR and the
US's CAN-SPAM Act exist around exactly that; this is not legal advice, so
check what applies to your case.

**Should the agent collect names and emails of individual people?** Treat
that as a separate, higher-risk task this page does not cover. A
company-level list carries a different, lower risk profile than harvesting
named individuals' personal emails at scale.

**How do I check the list is accurate before using it?** Spot-check a sample
of rows against the live page, the way you would proof any generated
dataset. The "one fact worth citing" field is most likely to be paraphrased
wrong, and the one your reader notices first.

**How many companies can I collect in one run?** Bound it like any agent
extraction: a few dozen rows in one session reads reliably, hundreds is a
slower run with more chances of a dropped or duplicated row, covered
generally on
[the CSV extraction page](how-to-extract-data-to-csv-with-an-ai-agent.md).

**See also:** [AI agents for web research](ai-agent-web-research.md), [extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md), and [getting website data into Google Sheets with an AI agent](website-data-to-google-sheets-ai-agent.md).

## Sources

Retrieved 2026-09-05.

- [AIHawk README](https://github.com/feder-cr/AIHawk#readme), for the
  `aihawk ui` interface and the MCP path for assistants that can already
  run tools.

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The agent reads
the public page; deciding who to email, and what to promise them, is still
yours.*
