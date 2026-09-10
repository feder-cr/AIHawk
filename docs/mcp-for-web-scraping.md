---
title: "Using a browser MCP server for web scraping: the pattern"
description: "A model is the right tool for working out how to scrape a site and the wrong one for doing it. The three-phase split, and the two jobs it stays inside."
parent: "Using the Agent"
nav_order: 36
---

# Using a browser MCP server for web scraping

The honest version, first: **a browser MCP server is excellent at finding out
how to scrape a site and bad at doing the scraping.** Every step is a round trip
through a model. That is a few seconds and a few thousand tokens per page. A
plain script does the same page in a fraction of a second for nothing.

The floor under that estimate is measurable and it is ours: our server's tool
descriptions alone are **14,064 characters, about 3,500 tokens, resent on every
turn** (24 tools, read from `src/aihawk/mcp/server.py` on 2026-09-10). Page
content and the model's own reasoning stack on top of that floor. Multiply by
turns, then by pages, and phase 2 below stops being a style preference.

Which does not make MCP useless here. It makes it useful in a specific place,
and the pattern below is what people converge on after they have paid for the
naive version once.

## The pattern that works

**Phase 1, with the model.** Open the site. Ask the agent to find the listing,
the pagination control, the fields you want and the shape of the detail page.
Have it report the selectors it used, not just the values it found. This is one
session, maybe twenty turns, and it replaces the half hour you would have spent
in devtools.

**Phase 2, without the model.** Write those selectors into ordinary code and let
it run over ten thousand pages. Deterministic, fast, free, and testable.

**Phase 3, back to the model, on failure only.** When the script starts
returning empty fields, that is the signal that the page changed. Reopen the MCP
session, ask what the page looks like now, update the selectors. The model is
handling the exception, which is the thing it is good at, rather than the
routine, which it is not.

The trap this avoids is real and expensive: a model rediscovering the same
layout on every one of ten thousand pages, slowly, and with the possibility of
deciding differently on page 4,000 than on page 3,999. A scrape that is not
reproducible is not a dataset.

## The two jobs where the model stays in

**When every page is shaped differently.** A hundred suppliers' sites with the
same information in a hundred layouts is precisely the job a selector cannot
express and a model can. The cost per page is high and there is no alternative
that is lower, because the alternative is a hundred scripts.

**When getting to the data is a flow.** Search, filter, expand, accept, then
read. If the sequence varies by page and cannot be replayed blindly, keeping the
model in the loop is cheaper than encoding every branch.

Both are the same underlying rule: **the model is worth its cost exactly where
the next step is not knowable in advance.** Everywhere else it is an expensive
way to run code you could have written.

## What the server should give you for this

Three properties matter for extraction specifically, and tool count does not.

**Reading without scripting.** A text read and a structured snapshot, so the
model can look at the page without you writing an evaluation for it. Microsoft's
server returns an accessibility tree with stable references, which is the right
shape for this.

**A path to what selectors cannot reach.** Coordinates, for a canvas or a
custom widget. Otherwise phase 1 stalls on exactly the pages you needed help
with.

**A JavaScript reader.** For the remainder: a value in a data attribute, a JSON
blob in a script tag, the thing that never made it into the DOM as text.

[How the tools are shaped, and why](mcp-tool-design.md) argues that in general;
[choosing an MCP server](best-mcp-server-for-browser-automation.md) applies it
to the field.

## The part that is not about MCP at all

Volume scraping fails for reasons that have nothing to do with which server you
picked. Rate limits, an address with a datacenter reputation, and pacing that no
person could produce. A model in the loop actually makes the pacing question
worse in one direction and better in another: slower per page, but with an
irregularity that is accidental rather than designed.

Before concluding your server is the problem, read
[why an agent gets blocked](why-does-my-ai-agent-get-blocked.md), and if you are
choosing between an agent and a scraper at all,
[AI browser agents vs traditional scraping](ai-browser-agents-vs-traditional-scraping.md)
is the wider comparison.

And the boundary this project keeps: nothing here defeats a site's protections,
and a page that is served only behind a challenge stays behind it.
[Can an AI agent solve a captcha](can-an-ai-agent-solve-a-captcha.md) is the
direct answer.

## Short answers to the questions that lead here

**Can I scrape with Playwright MCP?** Yes, and you should use it to work out how
to scrape rather than to do the scraping.

**Is an MCP server better than BeautifulSoup?** Different jobs. If the data is
in the HTML the server sent, you never needed a browser at all.

**How much does it cost per page?** Dominated by model tokens: a snapshot plus a
few actions per page, every page. That is the number that makes phase 2 obvious.

**Can the model extract to CSV?** It can produce the rows. Have it produce the
selectors too, so the next ten thousand rows do not cost the same.

**Does an MCP server get past anti-bot protection?** No, and the servers that
say so are making a claim rather than a statement.

**See also:** [Playwright MCP best practices](playwright-mcp-best-practices.md),
[getting data into a spreadsheet with an agent](how-to-extract-data-to-csv-with-an-ai-agent.md),
and [Playwright MCP vs the CLI](playwright-mcp-vs-cli.md).

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10, for the accessibility-tree snapshot and the vision capability.

---

*Written while maintaining an MCP browser server. The advice that costs us the
most is phase 2, and it is the middle of the page rather than a footnote because
it is the part that saves the reader real money.*
