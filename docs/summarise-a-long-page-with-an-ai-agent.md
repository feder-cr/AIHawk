---
title: "Summarising a long page or thread with an AI agent"
description: "Why use a browser at all when the model can be handed a URL. Three cases where the fetch gets a different page than a reader does, and what to ask for so the summary is checkable."
parent: "Using the Agent"
nav_order: 62
---

# Summarising a long page or thread with an AI agent

Most of the time you do not need a browser for this. Paste the URL, let the
assistant fetch it, read the summary. That path is faster and cheaper and you
should use it.

This page is about the cases where that path quietly returns a summary of
something other than the page, and about what to ask for so you can tell.

## Three cases where the simple fetch gets a different page

**The content is assembled by JavaScript.** A plain fetch receives the shell: a
navigation bar, a loading state and an empty main region. The summary that comes
back is not wrong so much as about nothing, and it usually reads plausibly
because a model will summarise whatever it was given.

**The page is behind a session.** Internal documents, a subscription, a forum
that requires an account. The fetch gets a sign-in page. The tell is a summary
that is suspiciously generic and mentions signing up.

**The thread is paginated or collapsed.** Long discussions load the first twenty
replies and hide the rest behind "show more", sometimes several times. A fetch,
and for that matter a single browser read, sees the opening and the conclusion is
drawn from it. On a thread where the useful answer is at comment 340, the summary
confidently reports the argument nobody agreed with.

If none of those applies, close this page and paste the URL.

## What the browser changes

It renders, it carries your session, and it can expand the page before reading.
That is the whole advantage, and it is three separate things worth asking for
explicitly.

Reading itself is nearly free: the text of a page comes back in about a
hundredth of a second, as
[measured](how-long-an-ai-agent-takes-per-step.md), and as plain text rather than
markup it is the cheapest of the four representations. For summarising, text is
exactly the right ask: you do not need selectors and you certainly do not need a
picture.

## Expanding before reading is most of the work

On a long thread the sequence is: read, find the control that reveals more, click
it, wait for the text to grow, read again, repeat until it stops growing or you
hit a ceiling.

Two details make the difference between that working and looping:

- **Stop when the text stops growing**, not when a control disappears. Sites reuse
  the same button for several behaviours and some never remove it.
- **Put a ceiling on the expansions**, because a thread with ten thousand replies
  will happily consume the whole context. Ten expansions, or a total character
  budget, whichever you prefer, and say which one you hit.

The lazy-loading half of this has the same shape as the PDF viewer, where only a
window of the document exists at once and the fix is to walk it:
[reading a PDF that opens inside the browser](read-a-pdf-in-the-browser-with-an-ai-agent.md)
has that measured.

## Ask for a summary you can check

The default output of "summarise this" is a paragraph with no way to verify it.
Three additions cost nothing and change that:

**Quote before you conclude.** For each claim in the summary, the sentence from
the page it rests on. A claim with no quote beside it is the model's inference,
and that is worth knowing.

**Say what the page is, not just what it says.** A product page, a press release,
one person's opinion in a thread, a vendor's own documentation. The genre changes
what the content is worth, and a summary that omits it flattens an argument into
a fact.

**Report the coverage.** How much of the thread was actually read: "the first 120
of about 400 comments" is a usable caveat. Without it, a summary of the visible
tenth is indistinguishable from a summary of the whole.

That third one is the single most useful instruction on this page, because the
failure it prevents is invisible.

## A task that works

> Open the thread at the URL below. Expand replies until the page text stops
> growing or you have expanded ten times, whichever comes first.
>
> Then write: what kind of page this is, how many comments are present out of how
> many the page claims, the three positions being argued with a short quote for
> each, anything the participants agree on, and anything stated as fact that
> nobody sourced.
>
> If the page needed a login and you were not logged in, say so and stop.

The last line matters more than it looks. Without it the run produces a summary
of a sign-up page written as though it were a summary of the thread.

## Where this genuinely beats reading it yourself

Not comprehension. On one page a person is better. Where it wins is **the same
question asked of twenty pages**: the positions across twenty threads, the
wording of a clause across twenty policies, whether twenty release notes mention
one feature.

There the value is the consistency of the question rather than the quality of any
single answer, and it becomes a list task with everything that implies about
writing results as you go:
[running one AI agent task across a list of sites](run-one-task-across-a-list-of-sites.md).

## Short answers to the questions that lead here

**Should I use an agent to summarise a web page?** Usually not. Paste the URL.
Use the browser when the content is built by JavaScript, sits behind a login, or
is hidden behind expand controls.

**Why is the summary generic and vaguely wrong?** Most likely it summarised a
loading shell or a sign-in page. Ask the task to state what kind of page it found
and to stop if it hit a login.

**How do I know the whole thread was read?** Only by asking. Require the summary
to report how many comments were present against how many the page claims.

**How many times should it expand?** Set a ceiling and have it tell you which
limit it hit. Without one, a very long thread consumes the context and the
summary degrades as it goes.

**Should it screenshot the page?** No. Text is the right representation here, and
a picture of a long page is both expensive and worse to read from.

**See also:**
[AI agents for web research](ai-agent-web-research.md), which is this task with
more than one source and the additional problem of reconciling them, and
[text, HTML, snapshot or screenshot](what-should-the-agent-read.md) for why plain
text is the correct ask for reading.

## Sources

- The read cost of about a hundredth of a second, and the relative cost of the four page representations, are measured and sourced on [how long an AI browser agent takes per step](how-long-an-ai-agent-takes-per-step.md) and [text, HTML, snapshot or screenshot](what-should-the-agent-read.md).
- The three failure cases are stated from experience with this browser rather than from a study, and the page opens by recommending the simpler tool for the common case.

---

*The coverage line is the one to keep: a summary that does not say how much it
read is a summary you cannot use, and it is one sentence in the task.*
