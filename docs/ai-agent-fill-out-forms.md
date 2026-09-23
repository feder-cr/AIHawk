---
title: "Getting an AI agent to fill out forms"
description: "What actually happens when an agent fills a form - field reading, selects and date pickers, validation errors, multi-step wizards - and what to check when it fails."
parent: "Using the Agent"
nav_order: 1
---


# Getting an AI agent to fill out forms

Filling a form is the task people reach for first with a web agent, and it is both
easier and harder than it looks: easier because a well-built form is the most
structured thing on the web, harder because forms are where sites concentrate their
defenses, their validation and their worst widgets. This page walks what actually
happens between "fill this out" and a submitted form, using a generic
registration-style form as the running example: a few text fields, a country
dropdown, a date of birth, some checkboxes, and a second page after "Continue". No
hype and no horror stories, just the mechanics and the failure modes in the order
you will meet them.

If the agent loop itself is new to you,
[the explainer](ai-web-agent-explained.md) covers it; this page assumes you know
the agent observes the page, decides one action, and repeats.

## Step one: the agent has to read the form, and forms lie

Before anything is typed, the agent maps fields to meanings. On a well-built form
this is straightforward, because structure carries the answer: labels are attached
to inputs, field names say what they are, required fields are marked. This is what
a structure-reading agent consumes, and it is the reason
[browser agents](ai-browser-agent-open-source.md) handle forms better than
screenshot-driven ones, which must infer the same mapping from pixels.

Real forms drift from the ideal in ways that produce specific errors:

- **Placeholder-only fields.** A field whose only description is the grey text
  inside it, which disappears on focus. Agents usually cope; they occasionally
  put the phone number in the fax field on forms where four boxes look alike.
- **Detached labels.** Text near an input but not linked to it. The agent, like a
  screen reader, is left guessing by proximity, and proximity misleads on
  multi-column layouts.
- **Fields that appear on interaction.** "Add another address" rows, sections
  that expand when a checkbox is ticked. The agent cannot fill what has not been
  rendered yet, so ordering matters: tick first, observe again, then fill.

Expectation to carry in: on a clean form, field mapping just works. On a messy
one, the first failure is usually here, and it looks like the right value in the
wrong box.

## Text is easy; everything else is the actual work

Typing into a text input is the reliable case. The hierarchy of difficulty above
it, from experience:

- **Native selects and checkboxes** are structured controls with enumerable
  options; agents handle them well, with one recurring trip: the option text the
  agent wants ("United States") versus what the list actually holds ("USA"), an
  exact-match failure a person would never notice making.
- **Custom dropdowns**, the styled div-based kind, are harder: the options do not
  exist in the page until the control is opened, so the agent must click, observe
  the appeared list, then click an option, three loop turns where a native select
  takes one. Searchable comboboxes add a type-then-wait-then-pick dance.
- **Date pickers** are the classic. Some accept typed dates; many demand clicks
  through a calendar widget, and month navigation is where agents wander. If a
  date field accepts typing, expect success; if it is click-only, expect more
  steps and more chances to end up in the wrong month. invisible_playwright_mcp's own README uses
  exactly this case in its example prompt, with the instruction to click the days
  rather than type, because saying so raises the success rate.
- **File uploads** need the file to exist on the machine the browser runs on, and
  a hosted agent may not have your file at all. Know where your agent's browser
  actually runs before promising it an attachment.

One mechanical note that matters for how the filling happens: a page can
distinguish a value typed through real input events from a value injected into
the field by script. invisible_playwright_mcp fills forms through actual key presses and clicks and
refuses the script shortcut even where it would be faster; whatever agent you
use, that behavior is worth confirming, both because injected values can skip the
page's own event handlers (breaking forms that compute things as you type) and
because it is a detectable difference.

## Validation errors: where decent runs go to die

Submit rarely means done. Browsers enforce built-in constraints, required fields,
patterns, minimum lengths, before the form even leaves the page, and MDN's
form-validation guide documents how deliberately these block submission: the form
does not submit, and a message appears near the offending field. Sites then add
their own layer, inline checks and server-side rejections with messages rendered
anywhere on the page.

For an agent this creates a read-back loop: submit, observe what changed, find
the error text, connect it to a field, fix, resubmit. Where it goes wrong:

- **The error is not seen.** A message rendered far from the field, or only
  visible after scrolling, can be missed, and the agent resubmits the same data.
  Two identical rejections in a row in the transcript is the signature.
- **The error is seen but misread.** "Password must contain a symbol" is easy.
  "Something went wrong" is not actionable for anyone, agent or human.
- **Formats fight back.** Phone, date and postal formats are the most common
  rejection, a field wanted digits only, the agent supplied punctuation. Stating
  formats in your instruction ("phone as digits only") is cheap insurance.

A validation loop that converges in one or two rounds is normal and fine. One
that repeats deserves a stop: repeated identical submissions are also a request
pattern sites notice, which crosses this page into
[why agents get blocked](why-does-my-ai-agent-get-blocked.md).

## Multi-step wizards: the state problem

Our example form has a "Continue" to page two, and multi-step is where the small
risks compound. Each step is its own little form with its own validation, so
everything above happens per step. The specific new failures:

- **Progress loss.** A session that expires or a step that hard-fails can throw
  away earlier pages. Long wizards on slow sites fail at step four, not step one.
- **Back-button hazards.** An agent that navigates back to fix something may find
  earlier answers cleared, and must notice that rather than assume.
- **Review pages.** The final "check your answers" page is the agent's best
  checkpoint and yours: it is the one place the whole submission is visible at
  once.

The rule that keeps all of this safe, and it is invisible_playwright_mcp's own stated position on
responsible use: do not let anything be submitted that a person has not read.
Have the agent fill and stop, review the completed form or the review page
yourself, and make submission the human's click wherever the stakes are real.

## What to check when it fails

In order, because the early ones are cheaper:

1. **Read the transcript before rerunning.** Every decent agent shows what it saw
   and did per step. The failure is usually legible there, and rerunning without
   reading spends tokens re-arriving at it. Wrong value in the wrong box points
   at field mapping; identical resubmissions point at unseen validation errors.
2. **Do it once by hand.** Two minutes in your own browser reveals what the form
   really demands, the strict formats, the click-only date picker, which of the
   look-alike fields is which, and turns into one clarifying sentence in your
   next instruction.
3. **Feed facts, not vibes.** Most fill errors trace to information the agent
   never had. Give exact values and exact formats for anything that matters, and
   say which optional sections to skip.
4. **Break the task at wizard boundaries.** "Complete step one and stop" is far
   more reliable than "finish the whole wizard", and gives you checkpoints for
   free.
5. **If the form never loads or rejects instantly, stop debugging the form.**
   That is not a filling problem; work through
   [the blocked checklist](why-does-my-ai-agent-get-blocked.md) first, and if the
   failures involve the agent hammering retries, see
   [retry loops and rate limits](agent-retry-loops-rate-limits.md).

And when the job is not one form but one form per row of a spreadsheet, the
arithmetic and the recovery change enough to need their own treatment:
[one form submission per spreadsheet row](one-form-per-spreadsheet-row.md) covers
the typing bill, the column that makes a rerun safe, and why the first row runs
alone.

Three control types have their own measured pages now:
[native selects and the ones that only look like selects](native-selects-and-fake-ones.md),
where one takes a single call and the other takes two clicks;
[uploading a file with an AI agent](uploading-a-file-with-an-ai-agent.md), which
this tool surface cannot do at all although the snapshot lists the input; and
[using the keyboard instead of the mouse](keyboard-instead-of-the-mouse.md), which
is both faster per action and the only route on some controls.

## Short answers to the questions that lead here

**Can an AI agent fill out web forms reliably?** On clean forms with typed inputs
and native controls, yes, routinely. Reliability drops with custom widgets,
click-only date pickers and multi-step wizards, and the fix is usually better
instructions and smaller steps, not a different agent.

**Why does the agent put the right value in the wrong field?** Field mapping:
placeholder-only or detached labels leave the agent guessing by proximity. Name
the fields explicitly in your instruction on forms where boxes look alike.

**How does the agent handle validation errors?** By reading the page after a
rejected submit and correcting the flagged field. It converges when errors are
specific and visible; it loops when they are vague or rendered where the agent
does not look, which is when you supply the format yourself.

**Can it handle dropdowns and date pickers?** Native selects, well. Custom
dropdowns and calendar widgets, with more steps and more failure chances; if
typing a date is allowed, that path wins. Saying "click the days rather than
typing" in the instruction genuinely helps.

**Should I let the agent submit?** Not unattended where stakes are real. Let it
fill, review the result yourself, and keep the submit click human. That is also
invisible_playwright_mcp's stated position for its own users.

**Do forms detect agents?** Forms are where detection concentrates, and filling
speed and rhythm are part of what gets read. A form filled in under a second
reads as what it is; the wider picture is on
[the timing-signal page](ai-agent-timing-signal.md).

## Sources

All retrieved 2026-09-03.

- [MDN: Client-side form validation](https://developer.mozilla.org/en-US/docs/Learn_web_development/Extensions/Forms/Form_validation),
  for the built-in constraint attributes and how browsers block submission and
  surface messages.
- [feder-cr/invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), plus its README in this
  repository, for the real-input-events behavior, the calendar-widget example
  prompt, and the responsible-use position quoted above.

**See also:** [what is an AI web agent?](ai-web-agent-explained.md),
[why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md), and the
rest of [Using the Agent](guides-using-the-agent.md).

---

*From the [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) wiki, written from
transcripts of its agent doing exactly this. The advice to keep the submit click
human is not a disclaimer, it is how the maintainer runs it.*
