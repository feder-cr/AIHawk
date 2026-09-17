---
title: "Finding the dead links on a site with an AI agent"
description: "A link checker is a solved problem, so the honest answer is mostly do not use an agent. The three cases where a crawler cannot see it and a browser can, and how to tell which you have."
parent: "Using the Agent"
nav_order: 56
---

# Finding the dead links on a site with an AI agent

Start with the answer that saves you an afternoon: **for a public site made of
ordinary links, do not use an agent.** A link checker fetches thousands of URLs
in the time a browser takes to open, costs nothing, and produces a better report.
An agent here is slower, more expensive and less complete.

This page is about the cases where that is not true, because they exist and they
are exactly the ones a crawler reports as fine.

## The three cases a crawler gets wrong

**1. The link exists only after JavaScript runs.** A navigation built by a
framework, a menu populated after a fetch, a card whose href is attached on
render. A crawler reading the served HTML does not see the link at all, so it
cannot report it as broken. It reports nothing, which reads as a pass.

**2. The target is behind the session.** Internal links in an authenticated area
return a login page to an anonymous crawler. Depending on the site that is a 200
or a 302, and either way the checker records success for a page the user would
never reach. This is the single most common false pass in an internal tool.

**3. The status code lies.** A soft 404: the server returns 200 and the page says
"this article no longer exists". No status-based checker can see it, because
there is nothing wrong at the protocol level. Only something that reads the
rendered page can tell.

If none of those three describes your site, close this page and run a checker.

## How the agent should do it, when it should

The shape that works is two-phase, and the phases use different tools.

**Phase one, collect.** Walk the pages you care about and read the links out of
the rendered markup rather than the source. This is the step that catches case 1,
and it is the only step where the browser is essential.

**Phase two, check.** Visit each target and decide whether the page is real. Cheap
per link: a navigation and a text read are hundredths of a second, as
[measured](how-long-an-ai-agent-takes-per-step.md), so the cost is page load and
nothing else.

Deciding "is this page real" is the part that needs a model, and it is worth
being specific about the criteria rather than leaving it to judgement:

- the page contains the words of a not-found message;
- the page is the login form rather than the content;
- the page is the site's generic landing page rather than the thing linked;
- the main content region is empty.

The third one is the sneaky one. A redirect from a dead article to the homepage
is a 200 to any checker and a dead link to a reader.

## Collect once, check once

Sites link the same pages from everywhere. A naive walk of fifty pages produces
two thousand links pointing at four hundred distinct targets, and checking them
as they come means checking each target five times.

Deduplicate the target list before phase two, and record which pages linked to
each one. The report you want is per target, with a list of the pages that point
at it, because that is the list you have to edit.

## What to report, and why the status code is not enough

One row per distinct target, with:

- the URL,
- the verdict: alive, dead, soft-dead, login-required, unreachable,
- the evidence: the phrase that made it a soft 404, or the title of the page that
  came back,
- every page that links to it.

**Five verdicts rather than two**, because the actions differ. A dead link gets
removed or fixed. A soft-dead one gets the same treatment and would not have been
found otherwise. A login-required one may be entirely correct. An unreachable one
means the check failed, not the link, and re-running is the right response, which
is the distinction between "no result" and "a negative result" that
[when the page changes under the AI agent](when-the-page-changes-under-the-agent.md)
makes in a different context.

## Be careful about the volume

A link check is, by construction, a lot of requests to one host in a short time.
On your own site that is fine and you should still pace it. On somebody else's it
is the volume pattern described in
[agent retry loops trip rate limits, not fingerprints](agent-retry-loops-rate-limits.md),
and it is discourteous regardless of what any policy says.

Check external links at a slower rate than internal ones, and treat a wave of
errors as "stop and tell me" rather than as a finding. A hundred links that all
went dead in the same minute is a throttle, not a broken site.

## Short answers to the questions that lead here

**Should I use an AI agent to check for broken links?** Usually no. Use a link
checker. Use an agent when links are built by JavaScript, targets are behind a
login, or the site answers 200 with a not-found page.

**What is a soft 404?** A page that returns a success status and tells the reader
the content is gone. Status-based checkers cannot detect it; something that reads
the rendered page can.

**Why does my checker say the internal links are fine?** It is probably getting a
login page with a success status for every one of them. Check what it actually
received, not the code.

**How many links can I check?** As many as you like on your own site, paced. On
somebody else's, slowly, and stop on a wave of errors rather than recording them
as dead.

**What should the report contain?** One row per distinct target, a verdict with
more than two values, the evidence for the verdict, and every page that links to
it.

**See also:**
[using an AI agent to test your own website](ai-agent-to-test-website.md), which is
the broader version of this job, and
[running one AI agent task across a list of sites](run-one-task-across-a-list-of-sites.md)
for the partial-results discipline that a long check needs.

## Sources

- The per-action timings used to argue that phase two is cheap are measured and sourced on [how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md).
- The three crawler blind spots are stated from experience with this browser rather than from a study, and the page opens by recommending against itself for the common case, which is the honest shape of the answer.

---

*A page that starts by telling you not to use the tool it is documenting. The
three exceptions are real, and they are also the only reason this page exists.*
