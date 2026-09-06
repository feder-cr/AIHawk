---
title: "Using an AI agent to download invoices from portals"
description: "The monthly supplier-portal chore: why scripts rot here, what 'download' honestly means with a browser agent today, keeping logins alive between runs, and a cron cadence."
parent: "Using the Agent"
nav_order: 12
---


# Using an AI agent to download invoices from portals

The chore is easy to describe and miserable to do: some number of supplier
portals, each with its own login, its own idea of where "Billing" lives, and
its own way of presenting last month's invoice. Once a month somebody walks
all of them. It is the most-cited use case for browser agents in business
automation, and this page walks through what an agent genuinely does for it,
including the one part most write-ups blur: what "download" actually means.

## Why this task defeats scripts specifically

A scripted browser automation can absolutely log into one portal and fetch
one PDF; that is a solved problem. The task rots at the multiplication.
Skyvern, the commercial agent company whose pages rank for exactly this
workflow, states the reason plainly in
[its invoice-automation guide](https://www.skyvern.com/blog/how-to-automate-downloading-invoices-september-2025/):
"each vendor portal has unique navigation patterns, different invoice formats,
and different download mechanisms." Ten portals means ten scripts, and every
portal redesign quietly breaks one of them, discovered the month the invoice
goes missing.

An agent flips the maintenance model: instead of encoding each portal's
navigation, you state the goal - find the most recent invoice on this portal -
and the agent reads whatever the page looks like this month. That is the same
trade [the scraping comparison](ai-browser-agents-vs-traditional-scraping.md)
prices out for extraction: worse per-run cost, dramatically better tolerance
for drift, and for a dozen runs a month across changing portals, drift
tolerance is the whole game.

## What "download" honestly means here

Now the part to get straight before building anything. AIHawk's browser is
driven through a fixed set of tools - navigate, read, click, type, screenshot,
and their session-management siblings, the full list in the
[server's README](https://github.com/feder-cr/invisible-playwright-mcp) - and
that list contains no download tool and no save-file tool. The agent's
deliverable is its answer, as text. Checked against the tool list as of this
writing, an instruction ending in "and download the PDF" is asking for
something the agent has no hands for.

So the honest offering splits in two, and both halves are useful:

- **The data, not the file.** For most accounting purposes what you need from
  an invoice is its fields: number, date, amount, due date, status. Those the
  agent reads off the portal and returns as text, and the
  [CSV extraction patterns](how-to-extract-data-to-csv-with-an-ai-agent.md)
  apply directly - name the columns, say "CSV only", verify the rows. A
  monthly run per portal appending to a ledger file covers reconciliation
  without any PDF changing hands.
- **The escort, not the courier.** When you need the actual PDF - audits and
  tax filings do - the agent's real value is getting you to it: logged in,
  navigated through whatever the portal renamed "Billing" to this quarter,
  sitting on the invoice page. Run headed (`--headed`, or
  `STEALTHFOX_HEADLESS=0` through MCP clients) and the browser is a real
  window on your screen; the final click on the download control is yours, in
  a session the agent drove to the right place. That split of labor is also
  the standing advice from [the forms page](ai-agent-fill-out-forms.md) about
  consequential clicks, applied in reverse.

Skyvern, for contrast, sells the full courier service and claims more besides:
its materials say it "supports multiple authentication flows including
standard username/password combinations, two-factor authentication, and
CAPTCHA solving." Those are Skyvern's claims about Skyvern's product, quoted
here because they define what the commercial end of this market promises.
AIHawk makes no such claims: if a portal raises a challenge, that is your
session to complete by hand, and the boundary is stated rather than blurred.

## The monthly workflow, concretely

What runs well today, per portal:

1. **Establish the login once, yourself.** Start the interface with a
   persistent profile and a visible window:

   ```bash
   aihawk ui --headed --profile-dir ~/.hawk-invoices
   ```

   Ask the agent to open the portal's login page, then sign in yourself in
   the real window. A headed browser is an ordinary Firefox window; typing
   your own password into it beats putting credentials in a prompt, because
   anything in the prompt travels through the model provider. The profile
   directory keeps the session.

2. **Extract on a rhythm, honestly.** Since aihawk 0.3.0 there is no headless
   aihawk command to put in cron, and this page will not pretend a scheduler
   is doing work a person starts. The monthly run is a five-minute ritual:
   open the same session (the profile still holds the login), paste the same
   instruction - "Find the most recent invoice. Reply with CSV only:
   number,date,amount,due_date, one line, no commentary." - and append the
   line to your ledger file. Same `--seed` and `--profile-dir` as step 1, so
   every visit is the same returning browser rather than a parade of new
   devices.

   If a portal of yours is stable enough that finding the newest invoice is
   the same three clicks every month, that is no longer judgment work: the
   engine behind AIHawk is on PyPI as a Python library with Playwright's API,
   and a short script with your portal's selectors plus `profile_dir` makes
   the run schedulable for real - the pattern, with an executed example, is
   on [the monitoring page](how-to-monitor-a-page-with-an-ai-agent.md). This
   page does not print a portal script because your portal's selectors are
   yours; test it against your own portal before trusting it with money.

3. **Verify like it is money, because it is.** Every number the agent returns
   is a model's reading of a page. Before a ledger line drives a payment,
   check it against the portal - which the escort pattern makes cheap, since
   the agent can land you on the exact page. A misread amount is rarer than a
   missed invoice, but both happen, and
   [the CSV page's verification habits](how-to-extract-data-to-csv-with-an-ai-agent.md)
   are the floor, not the ceiling, when the rows are financial.

Sessions expire between months; when a run comes back describing a login page
instead of an invoice, that is the signal to repeat step 1, not a bug. And if
a portal that worked stops loading at all, work through
[why agents get blocked](why-does-my-ai-agent-get-blocked.md) before blaming
the workflow.

## Bank statements: the one-paragraph caution

The neighboring idea - point the same workflow at a bank - deserves a plain
no rather than a workflow. Banking sessions are guarded harder than any
supplier portal, banks' terms commonly prohibit automated access and
credential sharing outright, and a tripped fraud model can freeze the account,
a failure mode entirely unlike a supplier portal shrugging off a bot. Banks
that want to give you programmatic statements do it through data-sharing
programs and exports built for the purpose. Fetch statements by hand, or
through the bank's own channels; spend the automation budget on the portals
where the downside is a broken run, not a frozen account.

## Short answers to the questions that lead here

**Can an AI agent download my invoices automatically?** It can log in via a
saved profile, navigate to the invoice, and extract its data as text rows;
what it cannot do today in AIHawk is save the PDF itself, because the tool
set has no download tool. Data extraction runs unattended; the PDF click is
yours, in a headed session the agent drove to the right page.

**How does the agent stay logged in month to month?** `--profile-dir` keeps a
persistent profile, so a login you perform once in a headed session survives
across runs. Expect to refresh it when portals expire sessions; a run that
reports a login page is telling you it is time.

**Can it get past two-factor prompts or captchas?** No claim of that is made
here. Vendors like Skyvern advertise handling both; on AIHawk a challenge
ends the unattended run and waits for you. Complete it by hand in a headed
session and the profile carries the result forward.

**Is this cheaper than doing it by hand?** For a few portals, roughly cents
per run against minutes of your month, so yes, quickly. The real saving is
missed-invoice risk: a scheduled run does not forget the 3rd of the month.

**Can I automate my bank statements the same way?** Read the caution above:
banking terms, hard defenses and account-freeze risk make this the wrong
target. Use the bank's own export channels.

**Where do the extracted rows go?** Wherever text goes: a ledger CSV via
redirection, then [into a spreadsheet](website-data-to-google-sheets-ai-agent.md)
through the import path that page describes.

## Sources

All retrieved 2026-09-03.

- [Skyvern's invoice-automation guide](https://www.skyvern.com/blog/how-to-automate-downloading-invoices-september-2025/),
  for the portal-heterogeneity quote and the vendor claims about
  authentication flows, quoted attributively.
- [feder-cr/invisible-playwright-mcp](https://github.com/feder-cr/invisible-playwright-mcp),
  the server's README, for the complete tool list this page's "no download
  tool" statement is checked against.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its README and
  source in this repository, for `--profile-dir`, `--seed`, `--headed` and
  the key-in-environment guidance.

**See also:** [extracting data to a CSV](how-to-extract-data-to-csv-with-an-ai-agent.md),
[getting website data into Google Sheets](website-data-to-google-sheets-ai-agent.md),
[monitoring a page for changes](how-to-monitor-a-page-with-an-ai-agent.md),
and [getting an AI agent to fill out forms](ai-agent-fill-out-forms.md).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The "no download
tool" paragraph is the page: everything else here works because that limit is
stated instead of papered over.*
