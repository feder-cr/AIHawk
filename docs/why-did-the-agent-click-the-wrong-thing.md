---
title: "Why did the AI agent click the wrong thing"
description: "Six causes, in the order worth checking. Most misclicks are not the model being stupid: they are the agent acting on a description of the page that stopped being true."
parent: "Using the Agent"
nav_order: 50
---

# Why did the AI agent click the wrong thing

A misclick almost never means the model picked a bad element out of a correct
list. It usually means the list was correct when it was taken and wrong when it
was used, or that the thing the model wanted was never in the list at all.

Check these in order. They are ordered by how often each one turns out to be the
answer, not by how interesting it is.

## 1. The page moved between looking and clicking

The commonest cause by a distance. The agent takes a snapshot, the model
chooses, the click goes out. In between, a banner loaded, an image finished and
pushed the layout down, a lazy list rendered, or a modal appeared.

If the click was made from **coordinates**, it lands wherever those coordinates
now are, which may be a different element entirely. If it was made from a
**selector**, it usually fails cleanly instead, which is why a selector is the
first rung and coordinates the second.

The tell: it works when you watch it and fails when you do not, or it fails on
the first run after a cold start and works on the second. That is loading, and
[when the page changes under the agent](when-the-page-changes-under-the-agent.md)
is the longer treatment.

## 2. Two elements say the same thing

"Continue", "Next", "Download", "Delete" appear more than once on a lot of real
pages: once in the visible flow, once in a hidden menu, once in a footer, once in
an aria-label the eye never sees. The model asked for "the Continue button" and
got a Continue button.

The fix is to describe the element by where it is rather than by what it says:
the one inside the form, the one after the total, the one in the dialog. A
snapshot gives the structure that makes those phrasings resolvable.

## 3. The element was never in the list

An agent can only click what it can identify. Things that routinely do not appear
as elements: a control drawn on a canvas, a slider built from unlabelled divs, a
custom widget in a shadow tree, a map pin, anything rendered as an image.

Here the agent is not wrong so much as blind, and the answer is the next rung of
the ladder: coordinates from the snapshot, or the picture when the snapshot does
not list the thing at all.
[Text, HTML, snapshot or screenshot](what-should-the-agent-read.md) has when each
one is the right ask, and
[clicking by selector or by coordinates](clicking-by-selector-or-by-coordinates.md)
has the trade between the first two rungs with the timings.

Two of the cases on that list have been measured since, and both are worth
recognising by sight. An element inside an **iframe** is absent from every read
and the selector spends a full fifteen seconds failing:
[an agent and an iframe](an-agent-and-an-iframe.md). An element inside a **shadow
root** is equally absent from the reads, and yet a click by selector reaches it,
even a closed one:
[shadow DOM and an AI agent](shadow-dom-and-an-ai-agent.md). Same symptom, opposite
remedy, which is why they are worth telling apart.

## 4. It clicked the right element and the page did nothing

This one masquerades as a misclick and is not one. Some controls only respond to
a full interaction sequence: a focus, a pointer down and up in the same place, a
change event. Others are covered by a transparent overlay that swallows the
click, so the pointer lands on the overlay and the button underneath never hears
about it.

The distinguishing question: did the page change at all? If a cookie wall or a
modal is up, everything under it is unclickable and every click looks like a
misclick until the wall is gone.

## 5. The agent read the page before the page was the page

Related to the first, but a different moment: the agent read at
`domcontentloaded` rather than after the content arrived, so the snapshot
describes the skeleton. Single-page applications are the usual venue, because the
first HTML is a shell and the real page arrives later.

This is also why "it worked yesterday" is not evidence of anything: the site got
slower, or your connection did, and the race tipped the other way.

## 6. The model genuinely chose badly

It happens, and it is last on the list because it is the least frequent and
because the first five look identical from the outside. The signature is a
consistent wrong choice: the same wrong element every run, on a page that is
stable. The first five causes are intermittent; this one is not.

When it is this, the fix is in the task rather than the browser. Name the target
the way a person would point at it, and say what the page should look like
afterwards so the agent can tell it went wrong.
[How to write a task an AI browser agent can follow](writing-tasks-for-an-ai-browser-agent.md)
is the whole of that argument.

## The diagnostic that settles it in one run

Ask for a snapshot immediately before and immediately after the failing action,
and compare. Both reads are effectively free, at a hundredth of a second each,
which is measured in
[how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md),
so there is no reason to be economical here.

- **Different before and after, and the target moved**: cause 1.
- **The target appears twice in the before**: cause 2.
- **The target is absent from the before**: cause 3.
- **Identical before and after**: cause 4, the click did nothing.
- **The before is nearly empty**: cause 5.
- **Everything looks right and the model still picked the other one**: cause 6.

## Short answers to the questions that lead here

**Why does my AI agent click the wrong button?** Most often because the page
moved between the look and the click. Second most often because two elements have
the same label.

**Why does it work when I watch it and fail when I do not?** That is a timing
race, and watching slows everything down enough to win it. Treat it as cause 1
rather than as a fluke.

**Should the agent click by selector or by coordinates?** Selector first, because
a stale selector fails cleanly while stale coordinates hit something else.
Coordinates are for elements a selector cannot describe.

**The agent clicked correctly but nothing happened. Is that a misclick?** No, and
the difference matters. Check for an overlay or a consent wall first: everything
underneath one is unclickable.

**How do I know it is the model and not the page?** Consistency. Page problems
are intermittent; a model choosing badly does it the same way every run.

**See also:**
[when the page changes under the agent](when-the-page-changes-under-the-agent.md)
for the first cause in detail, and
[keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md)
for what to do about the misclicks that cannot be undone.

## Sources

- The ordering of causes here is from running this project's own browser rather than from a published study, and it is presented as experience rather than as a measurement. The one number quoted, that a read costs a hundredth of a second, is measured and cited on the page it comes from.

---

*No statistics in this one on purpose. Anybody can produce a ranked list of
causes; the part worth having is the before-and-after snapshot at the end, which
tells you which of the six you have in about a minute.*
