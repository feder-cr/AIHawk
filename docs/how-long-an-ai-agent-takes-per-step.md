---
title: "How long an AI browser agent takes per step, measured"
description: "Eight actions timed against a real MCP browser. Two of them dominate the clock, one of them is slow on purpose, and typing costs about a second plus 270 ms a character."
parent: "Using the Agent"
nav_order: 46
---

# How long an AI browser agent takes per step, measured

People budget agent runs by counting model turns. On a browsing task the model
is often not the slow part. Here is the other half, timed on 2026-09-17 against
a real MCP browser driving a page served from `127.0.0.1`, so that none of these
numbers contains somebody else's server:

| action | median | range |
|---|---|---|
| protocol handshake | 1.09 s | 1.09 to 2.14 |
| `browser_open` | 4.82 s | 4.82 to 7.69 |
| `browser_navigate` | 0.08 s | 0.07 to 0.12 |
| `browser_read_text` | 0.01 s | 0.01 to 0.02 |
| `browser_read_html` | 0.02 s | 0.01 to 0.02 |
| `browser_snapshot` | 0.02 s | 0.01 to 0.02 |
| `browser_take_screenshot` | 0.11 s | 0.08 to 0.12 |
| `browser_click` | 0.99 s | 0.68 to 1.38 |
| **`browser_type`** | **3.98 s** | 3.70 to 8.79 |
| `browser_evaluate` | 0.01 s | 0.01 to 0.01 |

Two rows carry the whole clock, and they are the two at the top and the bottom:
opening the browser, once, and typing, every time.

## Why typing is the expensive one

`browser_type` above was entering twelve characters. Timed at three lengths, the
shape is linear with a fixed cost on top:

| characters | median | per character |
|---|---|---|
| 3 | 1.87 s | 622 ms |
| 12 | 3.93 s | 327 ms |
| 43 | 12.63 s | 294 ms |

Fit a line through those and you get **about one second of fixed cost plus about
270 ms per character**. A forty-character email address is twelve seconds. A form
with five such fields is a minute of wall clock before the model has done
anything at all.

![Three measured points plotted against the number of characters typed into one field: 1.87 seconds for three characters, 3.93 for twelve, 12.63 for forty-three. A dashed line through them shows the model, about 1.06 seconds of fixed cost plus 269 milliseconds per character, and the line does not pass through the origin.](https://raw.githubusercontent.com/feder-cr/invisible_playwright_mcp/main/docs/img/how-long-an-ai-agent-takes-per-step.png)

The line not passing through the origin is the part worth seeing: there is a
per-field cost that exists before the first keystroke, which is why a form of
many short fields is not cheap just because the values are short.

**This is not slowness to be tuned away. It is the point.** Keystrokes arrive
through the real keyboard at a human cadence because a field that fills
instantly, character-perfect, with no inter-key variation, is one of the cheapest
things for a page to notice. The related tells and which ones an agent can
actually control are in
[the timing signal AI agents give off](ai-agent-timing-signal.md).

What follows from it is a planning rule rather than a fix: **count the characters
your task types, not the fields**. A task that types two short codes is fast. A
task that fills a long address is not, and no model choice changes that.

## The cheap actions are cheaper than you will believe

Reading is effectively free: text, HTML and the accessibility snapshot all came
back in one or two hundredths of a second, and `browser_evaluate` in one
hundredth. That has a consequence for how you write a task.

Agents are often told to be economical about looking, on the theory that each
look costs something. On the browser side it costs nothing measurable. The cost
of looking is entirely in what the result does to the model's context, which is a
completely different budget with completely different numbers, and it is the
subject of
[text, HTML, snapshot or screenshot](what-should-the-agent-read.md).

So: **look often, and choose carefully what you look with.** The first half is
free, the second half is where the bill is.

## Where the first five seconds go

`browser_open` is the outlier among the per-action numbers, and it is a one-off.
It is a browser starting: process launch, profile, the first window. Five seconds
once per session, amortised across however many actions the session performs.

The mistake it invites is opening a browser per task in a loop. Ten small tasks
run as ten sessions pay fifty seconds of startup; run as one session they pay
five. If your client lets you keep a session across a conversation, that is the
single largest saving available in this table, and it is free.

## A worked budget

A realistic small task, using the medians above, with model time excluded:

```
handshake + browser_open        5.9 s
navigate                        0.1 s
snapshot (find the fields)      0.0 s
type a 20-character name        6.4 s
type a 30-character email       9.1 s
click submit                    1.0 s
read the confirmation           0.0 s
                              -------
                               22.5 s
```

Roughly **seventy per cent of that is typing**, and a quarter is the one-time
browser start. Nothing in the middle is worth optimising.

Against a real site rather than `127.0.0.1` you add page load time to
`browser_navigate`, which is the site's number and not the agent's, and you add
the model's thinking between each step. The point of the table is that you now
know which part is which.

## Short answers to the questions that lead here

**Why is my AI browser agent so slow?** Most likely typing. At roughly 270 ms per
character a long field is ten seconds, and a form of several long fields is most
of a minute. Second most likely, a new browser per task instead of one session.

**How long does an AI agent take to fill a form?** Count characters, multiply by
270 ms, add a second per field and one second per click. A five-field form with
100 characters total is about 35 seconds of browser time, plus model turns.

**Can I make the typing faster?** You can set values from script, and this
browser refuses to, for the reason in
[keeping an AI agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md):
the event that arrives is untrusted and that is the clearest signal there is.
Speed here is bought with the thing you came for.

**Does the model or the browser dominate the time?** On a typing-heavy task, the
browser. On a reading and reasoning task, the model, because every read above is
hundredths of a second.

**See also:**
[how to write a task an AI browser agent can follow](writing-tasks-for-an-ai-browser-agent.md),
which is where a task gets shorter before it gets faster, and
[giving an AI agent a stopping condition](giving-an-ai-agent-a-stopping-condition.md)
for the runs that are slow because they never decide they are done.

## Sources

- All timings taken 2026-09-17 on one Windows 11 machine, through the MCP server over stdio exactly as a client drives it, against a page served from `127.0.0.1`. Medians over three runs per action, three runs per typing length. Model time excluded by construction: no model was attached.

---

*The numbers are one machine and one page, so treat the ratios as the finding and
re-time the absolutes on yours. The measurement is ten minutes and the method is
in the note above.*
