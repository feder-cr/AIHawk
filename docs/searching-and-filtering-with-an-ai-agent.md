---
title: "Driving a site's own search and filters"
description: "Filters are the cheapest way to cut a walk from four hundred pages to four, and the most common way to get a result that is quietly the wrong set. Use the URL when you can."
parent: "Using the Agent"
nav_order: 84
---

# Driving a site's own search and filters

Every listing has a search box and a set of filters, and using them is almost
always better than walking the whole thing. Four hundred pages filtered down to
four is four hundredths of the cost, and the numbers are all in the page loads
rather than in the browser actions, per
[how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md).

The catch is that a filter can be applied, appear applied, and not be applied,
and nothing about the resulting page says so.

## Prefer the URL, when the site puts state in it

Most listings encode their filters in the query string. If the site does, the
whole interaction collapses to one navigation:

```
/search?q=widget&category=tools&sort=price_asc&page=2
```

That is better than clicking in four ways: it is one call instead of six, it is
reproducible exactly, it can be logged as a single field, and it removes every
question about whether a control registered.

**The way to find the pattern is to do it once by hand.** Apply the filters in
your own browser, look at the address bar, and hand the agent the URL shape. Two
minutes of yours saves the agent a dozen calls per run, and the URL becomes the
thing you record, as in
[what an agent run should log](what-a-run-should-log.md).

Not every site does this. Single-page applications often keep filter state in
memory, and then the controls are the only route.

## When you have to click the controls

Three things go wrong, in rough order of frequency.

**The filter needs an apply step.** Some panels filter as you click, some collect
your choices and wait for a button. An agent that ticks three boxes and reads the
list on a site of the second kind reads the unfiltered list, which looks entirely
normal.

**Filters combine in ways you did not intend.** A previous run's choices persist
in the session, so today's filter is on top of last week's. Clearing first is
more reliable than assuming a clean start, and a fresh profile is the sure
version.

**The list updates asynchronously.** You click, the old results stay on screen
for a moment, the agent reads, and it has the pre-filter set. Wait for a state
rather than a duration, per
[when the page changes under the AI agent](when-the-page-changes-under-the-agent.md):
wait until the result count changes, not two seconds.

## Confirm the filter, not the click

The instruction that prevents all three: **read back what the page says is
applied before reading any results.**

Most listings display it, as chips, as a summary line, as "42 results for widget
in Tools". Have the agent record that string next to the data. Then a filtered
set that is secretly unfiltered is visible in the output rather than discovered
three steps later, and the recorded string is also what makes the run
reproducible.

The result count is the most useful single thing to capture, because it doubles
as the validation check in
[validating an AI agent's output](validating-an-agents-output.md): if the page
says 42 and you wrote 400 rows, the filter never applied.

## Search boxes have their own two problems

**Autocomplete steals the Enter.** Typing into a search field often opens a
suggestion list, and the first Enter selects a suggestion rather than submitting
the query, so you search for something adjacent to what you asked. Press Escape
to dismiss the list, then Enter. The keyboard routes are in
[using the keyboard instead of the mouse](keyboard-instead-of-the-mouse.md).

**The query is interpreted.** Sites stem, correct spelling, drop operators and
match loosely, so the results are for a query that is not the one you typed. If
the page shows what it searched for, and many do, record that too: "showing
results for X" next to "searched for Y" is a difference you want in the file.

## Filters that are not filters

Two look like filters and behave differently:

- **A sort.** Changes the order and not the set. An agent that treats it as a
  filter walks the same four hundred items in a new sequence.
- **A view switch.** Grid against list. Same items, different markup, and
  selectors planned against one do not resolve against the other.

Neither is a problem once named. Both produce a confusing run when they are not.

## Short answers to the questions that lead here

**How do I make an agent use a site's filters?** Use the URL when the site puts
filter state in the query string: one navigation instead of six clicks, and it is
reproducible. Otherwise click, then confirm what the page says is applied.

**Why did the filter not apply?** Either the panel needed an apply button, or the
list updated after the agent read it, or a previous selection is still active.

**How do I know the results are actually filtered?** Have the agent read back the
applied filters and the result count before recording anything, and compare that
count against the rows you got.

**Why did the search return the wrong thing?** Autocomplete took the Enter, or
the site rewrote your query. Escape the suggestion list first, and record what
the page says it searched for.

**Is sorting a filter?** No, and treating it as one is a common way to walk the
whole list by accident.

**See also:**
[running one AI agent task across a list of sites](run-one-task-across-a-list-of-sites.md),
where every site's filters are different and the confirmation step is what keeps
the results comparable, and
[reading a table with an AI agent](reading-a-table-with-an-ai-agent.md) for what
to do with the filtered set once you have it.

## Sources

- No external figures are cited: this is about how listing interfaces behave and how to write the task around them. The per-action costs referred to in passing are measured on [how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md). No site is named.

---

*Do it once by hand and read the address bar. If the filters are in the URL, most
of this page stops applying to you, which is the best outcome it offers.*
