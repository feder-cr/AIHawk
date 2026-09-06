# How the tools are shaped, and why

Reference for anyone building on this server rather than just using it. The
README says what the tools are; this says why they return what they return, and
carries the measurements behind each decision.

Moved out of the README on 2026-09-03: it was 82 of 227 lines, sitting between
the tool list and everything else, on a page whose job is to get somebody
browsing in two commands.

`browser_click_at` takes viewport coordinates instead of a selector, moves the
pointer there rather than teleporting, optionally holds before releasing, and
returns a screenshot of what happened - for a slider, a canvas-drawn challenge,
or a press-and-hold.

`browser_snapshot` returns the title, the url and the visible interactive
elements rather than the accessibility tree: one country `<select>` on a real
sign-up page contributes about two hundred `<option>` nodes, which fill the
character budget before the form does.

Each element comes with a `selector` when one can reach it, and that string goes
to `browser_click` or `browser_type` verbatim. It is built to match exactly one
element, which the obvious selector often does not: measured across 958 elements
on real pages, 88% could be addressed but only 48% unambiguously, and Playwright
acts on the first match without complaining, so aiming at the third of five
identical links quietly hit the first. Elements no selector can reach carry `at`
instead, the centre coordinates, for `browser_click_at`.

When a click does not land, the error says what stopped it rather than only that
it timed out: an element covering the target is named, with its id, its class and
its text, because the next move is to deal with that thing and not to retry. If
the page has replaced `getBoundingClientRect` so that nothing can be measured,
the snapshot reports `unmeasurable` with a count instead of an empty list, so a
tampered page cannot be mistaken for a page with no controls.

When an element has none of those, the selector falls back to `data-testid` and
then to a unique `aria-label`, which together took coverage from 90.5% of
elements to 97.9%. It stops there: a text-based selector is not stable, and a
handle that sometimes points elsewhere is the thing this exists to remove. What
is left carries `at` and nothing else.

A link addressed by its href has no separate `href` field, because the selector
already holds it: `a[href='/cart']` says where the link goes as plainly as the
field did, and not repeating it is what kept this affordable (+47% of the
payload with the repetition, +15% without). A link addressed by its id keeps its
href, having nothing duplicated.

`browser_read_html` returns the page's markup instead of a flat list, for when
the structure is what matters: a form and its labels, a table, what a control is
wired to. The browser decides what is actually painted, on a clone of the
document so the live page is never written to, and the markup is then reduced to
what is worth reading. Measured on real pages, 9.6 MB of markup became 293 KB
with every one of the 1,453 interactive elements still present. `mode`
is `form` (the interactive surface and the text explaining it), `text` (the prose
alone) or `full` (the structure, with the noise and the attribute soup gone).

Tool names mirror the Microsoft Playwright MCP, so prompts written for it work here too.

## The ladder, and what the refusal is worth

The README states the four rungs. This is what they cost and what they bought.

This is a pattern check on the obvious road, not a sandbox. That sentence used
to end "and it is not described as one", which was false of the only text a
model actually reads: the instructions block said `browser_evaluate will not act
on the page` and the tool docstring said `It will not act`. Measured 2026-09-04,
thirteen of fifteen ordinary acting expressions passed the guard, `requestSubmit`
among them - the modern spelling of the one call that was refused. Both texts now
say what the code does and add the sentence that matters, which is that a script
slipping past the check is a bug to report rather than a licence to use it. A
model told the door is locked has no reason to avoid the handle.

What makes the refusal reasonable is the rest of the ladder:
measured on the same task, the same model went from 14 steps with two
`browser_evaluate` calls - one of them setting a `<select>` from script - to 8
steps with none, three runs out of three.

The snapshot carries the state as well as the shape: `checked` for a checkbox or
radio, `value` for a select, alongside the text. That half matters as much as
the tools. The run above reached for script to READ the form back before it ever
reached for script to write it, and a gap in what a caller can see is answered
with `evaluate` just as surely as a gap in what it can do.

