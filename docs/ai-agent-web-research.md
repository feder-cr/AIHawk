---
title: "AI agents for web research"
description: "Two architectures answer to 'research agent': search-API pipelines like gpt-researcher and real-browser agents. Where each wins, honestly, and how to run browser-grade research."
parent: "Using the Agent"
nav_order: 13
---


# AI agents for web research

"AI agent for web research" names two different machines, and buying the wrong
one wastes either money or an afternoon. The first is a search-API pipeline:
it queries search engines, fetches the result pages, and synthesizes a report.
The second is a browser agent: it opens pages in a real browser and works them
the way a reader would. This page lays out both honestly, because the
uncomfortable truth for a browser-agent wiki is that for a large share of
research questions, the pipeline is the better buy.

## The search-API pipeline, and where it simply wins

The reference open-source project is
[gpt-researcher](https://github.com/assafelovic/gpt-researcher), at about
29,300 stars as of this writing. Its architecture is a planner agent that
turns your question into a set of research questions, execution agents that
gather sources for each - through search APIs, Tavily by default, plus page
scraping - and a publisher that aggregates the findings into a cited report.
Its README advertises aggregating "over 20 sources" per report, and for its
deep-research mode states about five minutes and roughly forty cents per run.

Take those numbers at face value and notice what they buy: twenty-plus
sources read in parallel for less than a coffee. A browser agent cannot touch
that economics, because a browser agent reads pages one at a time, in
sequence, each observation a model turn carrying the whole transcript - the
cost curve [the CSV page](how-to-extract-data-to-csv-with-an-ai-agent.md)
describes applies to research runs unchanged. For breadth-first questions
over the open web - survey a topic, compare published opinions, summarize
the state of a debate - the pipeline wins on speed, cost and coverage, and
it is not close. If that is your research shape, use one of those tools; this
wiki will still be here.

## Where a real browser earns its cost

The pipeline's strength is its weakness: it consumes the web as fetched
documents. Three research shapes do not survive that flattening, and they are
where a browser agent stops being the expensive option and becomes the only
option.

- **Pages that only exist after interaction.** Content rendered by
  JavaScript, loaded on scroll, revealed by a tab or a version switcher, or
  assembled after a form is submitted. A fetcher gets the shell; the answer
  you need was never in the served HTML. A browser agent renders the page,
  clicks the switcher, scrolls the list, and reads what a reader would have
  read. If you are unsure whether your target is like this, the diagnosis is
  cheap: view the page source and search for a phrase you can see on screen.
  Missing means fetchers cannot help you.
- **Sources behind a login.** Member forums, subscribed publications,
  dashboards, your own organization's internal tools. Search APIs have no
  session; a browser agent with a persistent profile (`--profile-dir`, login
  performed once by hand) reads them as you. The mechanics are the same
  profile pattern [the invoices page](ai-agent-download-invoices.md) uses for
  portals, and the same honesty applies: your credentials, your terms-of-use
  reading, your call.
- **Paginated archives walked in order.** A changelog forty pages deep, a
  forum thread across years, an archive whose search is worse than its
  next-page button. Pipelines sample what search surfaces; an agent walks the
  actual sequence, page by page, and can carry a running question through the
  walk - "note every entry that mentions the pricing change." Bound the walk
  the way the CSV page bounds extractions, because turns are money.

The test that sorts every case: could a person answer this with search
results alone, without ever touching a page's controls? If yes, pipeline. If
they would need to click, log in, or turn pages, browser.

## Running browser-grade research on AIHawk

Two ways in, matching the two ways into everything here. Through an MCP
client - [Claude Code](running-aihawk-with-claude-code.md),
[Claude Desktop](running-aihawk-with-claude-desktop.md),
[Cursor](running-aihawk-with-cursor.md) or
[Cline](running-aihawk-with-cline.md) - your assistant does the reading and
synthesis while the browser does the driving, which suits research well: the
conversation holds the accumulating picture, and you can steer mid-walk. Or
scripted, one question per run:

> Go to https://books.toscrape.com/. Walk the first three pages
> of the catalog and report: how many books are priced above forty pounds, and
> the three most common price bands you observe. Ground every number in what
> the pages show; do not estimate.

(Typed into `aihawk ui`, or handed to your assistant with AIHawk's
browser attached - research is judgment work, and since aihawk 0.3.0 the
judgment paths are those two.)

Prompt habits that separate usable research from confident noise:

- **Demand grounding.** "Quote the exact sentence and say which page it was
  on" turns a summarizer into a witness. The agent's system prompt already
  pushes it to report only what pages show; your instruction should pull the
  same direction.
- **Bound the walk.** "The first three pages", "stop after five sources".
  Unbounded research runs are where
  [turn budgets](how-to-extract-data-to-csv-with-an-ai-agent.md) expire
  mid-thought.
- **Separate gathering from judging.** Two passes - collect the claims, then
  evaluate them - beat one pass doing both, for the same reason it works with
  human researchers: the gatherer stops shading the evidence toward a thesis.

And verify. A model is a stochastic reader; the transcript shows what it saw,
and claims that matter get spot-checked against the live page. That is not a
browser-agent weakness, it is an LLM property - the pipeline tools carry the
same caveat in their own documentation, which is part of why gpt-researcher
leans on aggregating many sources to average out misreadings. On a
single-source read, you are the aggregation.

## The hybrid that practitioners land on

Nothing forces a choice per project; choose per source instead. Let a
search-first tool (or your assistant's own web search) do discovery - what
exists, what is worth reading - then send the browser agent into the
minority of sources that need driving: the JS-heavy dashboard, the archive,
the logged-in forum. Research spends most of its sources on breadth and its
conclusions on a few deep reads; matching the tool to each half keeps the
bill shaped like the value. When the deep read stops being research and
becomes recurring extraction, that is
[the monitoring page's](how-to-monitor-a-page-with-an-ai-agent.md) territory,
and when a source pushes back on being read at all,
[the blocked checklist](why-does-my-ai-agent-get-blocked.md) is the map.

## Short answers to the questions that lead here

**What is the best AI agent for web research?** Wrong first question; the
right one is which architecture your sources need. Open-web breadth:
search-API pipelines like gpt-researcher, cheaper and faster at scale.
Sources needing interaction, logins, or page-walking: a real-browser agent.
Most serious research uses both.

**Is gpt-researcher better than a browser agent?** For aggregating many
public sources into a cited report, yes - its own numbers, about five
minutes and forty cents for twenty-plus sources, are an economics a
sequential browser cannot match. It cannot log in as you, render
interaction-gated content, or walk an archive in order. Different machine.

**Can AIHawk do deep research?** It does the browser half well: driven
reading of hard sources, in its own interface or through an MCP client where
your assistant synthesizes. It does not fan out
across twenty sources in parallel, and this page does not pretend otherwise.

**How do I stop a research agent from making things up?** Demand quotes tied
to pages, bound the scope, and spot-check what matters against the live
source. Grounding instructions shrink the problem; verification catches the
remainder. Nothing eliminates it, on any architecture.

**Why is my browser-based research so slow and expensive?** Because every
page is a sequence of model turns carrying the whole transcript. That is the
price of driving; pay it only for sources that need driving, and hand the
rest to a fetch-based tool.

**Can it research sources behind my logins?** Yes - a persistent profile
with a login you performed by hand makes the agent read as you. Whether you
should is between you and each source's terms; the capability is stated, not
the permission.

## Sources

All retrieved 2026-09-03.

- [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher),
  for the star count, the planner-executor-publisher architecture, the
  search-API approach, and the per-run time and cost figures quoted from its
  README.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its README and
  source in this repository, for the agent loop, the grounding line in its
  system prompt this page's cost notes describe.

A complete run of this page's worked example, with the agent's counts checked
against a model-free script on the same pages (they matched, 24 to 24), is in
the repository:
[web research, audited](https://github.com/feder-cr/AIHawk/tree/main/articles/web-research-audited).

**See also:** [what is an AI web agent?](ai-web-agent-explained.md),
[AI browser agents vs traditional scraping](ai-browser-agents-vs-traditional-scraping.md),
[extracting data to a CSV](how-to-extract-data-to-csv-with-an-ai-agent.md),
and [which model to use with AIHawk](which-model-to-use-with-aihawk.md) for
the cost half of the equation.

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki, which just spent
its second section telling you when not to use its own product. That is the
register the rest of the page earns its claims in.*
