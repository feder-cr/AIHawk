---
title: "Getting website data into Google Sheets with an AI agent"
description: "Landing web data in a spreadsheet: when Sheets' own IMPORTHTML and IMPORTXML win, when an n8n workflow wins, and the honest agent route - CSV out, Sheets imports it."
parent: "Using the Agent"
nav_order: 11
---


# Getting website data into Google Sheets with an AI agent

You want numbers that live on a web page to end up in rows of a Google Sheet.
That is the whole task, and this page is about the paths to it, ordered by
cost, with the agent route described exactly as it works rather than as a
diagram with a magic arrow labeled "integration."

One disambiguation first, because two different questions collide on these
words. Google now ships AI inside Sheets: an `AI("prompt", [range])` function
that runs Gemini on data already in your spreadsheet, documented in
[Google's editors help](https://support.google.com/docs/answer/15877199). That
is AI operating on cells you have. This page is the other direction: getting
data from the web into the cells in the first place. If you searched for AI in
Google Sheets and meant formulas, that help page is your destination; everyone
else, read on.

## Try the built-in functions before any agent

Google Sheets can pull from the web by itself, has been able to for years, and
where its functions apply they beat an AI agent on every axis that matters:
free, refreshing on their own, and deterministic. Three of them do the work,
names and signatures from Google's own documentation:

- **`IMPORTHTML(url, query, index)`** imports "data from a table or list
  within an HTML page." `query` is the literal word `"table"` or `"list"`,
  `index` counts which one on the page, starting at 1. If the page renders its
  data as an actual HTML table, this one formula is the entire project.
- **`IMPORTXML(url, xpath_query, locale)`** imports from structured data
  including XML and HTML, addressed by an XPath query. More flexible, more
  brittle: you are writing a selector, and selectors break when the page
  changes.
- **`IMPORTDATA(url)`** imports a `.csv` or `.tsv` file served at a URL. Keep
  this one in mind; it becomes the last step of the agent route below.

Where they win, use them and close the tab. Where they fail is specific, and
it is the same boundary [the scraping comparison](ai-browser-agents-vs-traditional-scraping.md)
draws for code: pages that build their content with JavaScript after load
(the import functions read the served HTML, not what a browser renders), pages
behind a login (the functions fetch as Google, not as you), pages whose data is
not shaped like a table or list, and any column that requires judgment rather
than extraction - "category", "sentiment", "does this mention a deadline."

## When an n8n workflow beats both

If the task is recurring and mechanical - the same fields from the same pages,
on a schedule, appended as rows - a workflow tool is the honest recommendation,
and [n8n](https://n8n.io) is the usual open-source pick. Its Google Sheets node
writes rows directly, its trigger nodes handle the schedule, and its template
gallery already contains this exact shape, for example a
[recursive multi-page scraper with Google Sheets storage](https://n8n.io/workflows/10173-scrape-multi-page-websites-recursively-with-google-sheets-storage/).
You pay a setup afternoon once, then every run is free and identical.

The concession cuts the other way too: an n8n workflow is a pipeline you
maintain. When the page changes shape, the workflow breaks and waits for you.
The agent's one advantage over both the functions and the pipeline is that it
reads the page fresh each time and tolerates drift - which is worth paying for
sometimes and not others.

## The agent route, honestly: CSV out, Sheets imports it

Here is the fact this page exists to state plainly: AIHawk has no Google
Sheets integration. Nothing in its source talks to a Google API, there is no
credential to configure, and the agent has no file-writing tool at all. What
the agent produces is its answer as text in the interface's chat, and what
the scheduled script produces is CSV on stdout. That is not a gap waiting
for a feature; it is
the architecture: the extraction produces text, and the spreadsheet imports.

So the working pipeline has two short stages. First, extraction to CSV. For a
one-off, the agent is the right tool and
[the CSV page](how-to-extract-data-to-csv-with-an-ai-agent.md) covers the
prompt patterns, the cost curve and the failure modes. When the source is an
internal screen rather than a public listing,
[getting data out of a dashboard with no export button](dashboard-with-no-export-button.md)
has the four routes in order, including why the chart is the one place the
obvious move is the wrong one. For the RECURRING
version this page is about, the extraction is better off as a script on the
same engine, because the selectors are stable and a model re-deciding them
every morning is cost without judgment:

```python
# extract_books.py - the watched listing to CSV on stdout
from invisible_playwright import InvisiblePlaywright

with InvisiblePlaywright(seed=7) as browser:
    page = browser.new_page()
    page.goto("https://books.toscrape.com/", wait_until="domcontentloaded")
    print("title,price_gbp")
    for card in page.locator("article.product_pod").all():
        title = card.locator("h3 a").get_attribute("title").replace('"', '""')
        price = card.locator(".price_color").inner_text().lstrip("£")
        print(f'"{title}",{price}')
```

Since aihawk 0.3.0 there is no headless aihawk command, and a recurring
extraction with stable selectors does not want one: it is mechanical work, and
the same stealth engine AIHawk drives is on PyPI as a plain Python library
(`pip install invisible-playwright`) with Playwright's API. Executed on
2026-09-03, `python extract_books.py > books.csv` produced a header plus
twenty rows, starting `"A Light in the Attic",51.77`. No model and no API key
are involved anywhere in this path.

Second, the import, which is Google's half and needs no agent:

- **By hand:** File, then Import, in any Google Sheet takes the CSV upload and
  offers to replace or append. For a one-off extraction this is thirty
  seconds and done.
- **By URL:** if the CSV lands somewhere web-served - an internal static
  host, a paste service with raw URLs, your own server - one cell of
  `IMPORTDATA("https://your-host/books.csv")` makes the sheet re-read it.
  Combine that with a scheduled extraction and the sheet updates itself: cron
  runs the script and drops the file, `IMPORTDATA` picks it up. The
  scheduling half, including the settings that keep a recurring run stable, is
  on [the monitoring page](how-to-monitor-a-page-with-an-ai-agent.md); it
  transfers unchanged.

Resist the urge to have the agent drive the Google Sheets web interface and
type values into cells. It can, in the way a browser agent can do most things
slowly, but you would be paying model turns to simulate a paste, into an
interface built of exactly the custom widgets
[the forms page](ai-agent-fill-out-forms.md) warns about. The CSV path is
faster, cheaper, and leaves a file you can check before the sheet sees it.

## Notion and Excel, briefly

The same architecture covers the other two destinations people ask about,
because both ends of it are standard. Notion imports a CSV into a database
table (Import in the left sidebar, CSV as the source), after which each row is
a page and each column a property. Excel opens CSV files natively, and a
recurring drop of the same filename plus a refreshable query over it gets you
the self-updating version. In all three cases the agent's part ends at the
file; the destination's own import does the rest, which is why swapping
destinations costs nothing.

## Choosing, in one paragraph

Public page, real HTML table, no login: `IMPORTHTML`, and you are done in one
formula. Same fields on a schedule from stable pages: an n8n workflow with its
Google Sheets node. Data that needs a real browser or a judgment call - JS
rendering, a login, columns that require reading - the agent extracts to CSV
and Sheets imports it, by hand once or via `IMPORTDATA` on a schedule. And if
the extraction itself is the hard part, that is
[the CSV page's](how-to-extract-data-to-csv-with-an-ai-agent.md) territory;
this page only ever cared about the landing.

## Short answers to the questions that lead here

**Can an AI agent put website data into Google Sheets?** Yes, in two stages:
the agent extracts to CSV (its answer, redirected to a file), and Sheets
imports the CSV, by File then Import or with `IMPORTDATA` on a served URL.
There is no direct AIHawk-to-Sheets connection, and the page above argues that
is the right shape, not a missing feature.

**Does AIHawk have a Google Sheets integration?** No. Its source contains no
Google API client and the agent has no file-writing tool; the answer text is
the deliverable. Anything promising one-click web-to-Sheets is doing the same
CSV hop internally or driving the Sheets UI, which you can do cheaper.

**When is an agent overkill for this?** Whenever `IMPORTHTML(url, query,
index)` or `IMPORTXML(url, xpath_query, locale)` can see the data: public
page, served HTML, table or list shape. Free and self-refreshing beats cents
and a model every time the mechanical tool can reach.

**How do I make the sheet update on a schedule?** Schedule the extraction
(cron plus the script above, per [the monitoring page](how-to-monitor-a-page-with-an-ai-agent.md)),
write the CSV to a web-served location, and point `IMPORTDATA` at it. The
sheet re-fetches; nothing touches the sheet directly.

**What about Notion or Excel instead?** Same two stages, different second
stage: Notion's CSV import creates a database, Excel opens CSV natively. The
agent side does not change at all.

**Is this the same as the AI function inside Google Sheets?** No. `AI()` runs
Gemini over data already in your sheet, per
[Google's help](https://support.google.com/docs/answer/15877199). This page is
about getting web data into the sheet, which that function does not do.

## Sources

All retrieved 2026-09-03.

- [Google Docs editors help: IMPORTHTML](https://support.google.com/docs/answer/3093339),
  [IMPORTXML](https://support.google.com/docs/answer/3093342) and
  [IMPORTDATA](https://support.google.com/docs/answer/3093335), for the exact
  signatures and what each imports.
- [Google Docs editors help: the AI function in Sheets](https://support.google.com/docs/answer/15877199),
  for the other meaning of these search words.
- [n8n workflow gallery: recursive multi-page scraping into Google Sheets](https://n8n.io/workflows/10173-scrape-multi-page-websites-recursively-with-google-sheets-storage/),
  the template class recommended for recurring mechanical work.
- [feder-cr/aihawk_mcp_server](https://github.com/feder-cr/aihawk_mcp_server), plus its README and
  source in this repository, for the no-file-tool, answer-on-stdout
  architecture of the agent loop.

**See also:** [extracting data to a CSV](how-to-extract-data-to-csv-with-an-ai-agent.md),
[monitoring a page for changes](how-to-monitor-a-page-with-an-ai-agent.md),
[AI browser agents vs traditional scraping](ai-browser-agents-vs-traditional-scraping.md),
and the rest of [Using the Agent](guides-using-the-agent.md).

---

*From the [AIHawk](https://github.com/feder-cr/aihawk_mcp_server) wiki. The maintainer's
own sheets update through the boring path - a scheduled extraction, a served
CSV, one IMPORTDATA cell - because the boring path is the one still working
next month.*
