---
title: "Which model to use with AIHawk"
description: "The default model, what browser-agent work actually demands from an LLM, real OpenRouter prices, and why cost is turns times context rather than a price-sheet number."
parent: "Using the Agent"
nav_order: 2
---


# Which model to use with AIHawk

AIHawk brings the browser and you bring the model, from
[OpenRouter](https://openrouter.ai) and nowhere else. If you set nothing, you get
`z-ai/glm-5.3-flash`: that is the default written into the source, and it sits at
the cheap-and-fast end of the catalog rather than the flagship end. You override it
with `--model` on `aihawk ui`, or the `AIHAWK_MODEL` environment variable, and
any model id OpenRouter serves is legal. So the real question is not "which model
does AIHawk support" - all of them - but which one is worth paying for on this
kind of work, and that has a less obvious answer than the price sheet suggests.

## How AIHawk actually spends the model

Worth knowing before choosing, because the loop's shape decides the bill. The
interface runs one fixed loop: the model receives the task and
the browser tools, replies with one thought and usually one tool call, the tool
runs, the result goes into the transcript, and the model is called again. In the
current source the loop is capped at 25 turns per instruction, each reply is
capped at 8,192 tokens, temperature is pinned to 0, and each tool result is
clipped to 8,000 characters before it enters the transcript.

Two consequences follow directly:

- **Every turn resends the whole transcript.** The API is stateless, so turn
  twelve pays for the task, every earlier thought, and every earlier tool result
  again. A big page read early in a task is not paid once; it is paid on every
  turn after it. The interface's token meter shows the last turn's prompt size
  for exactly this reason: that number is the current occupancy of the context,
  and it only grows.
- **A task's cost is roughly turns times context, times the input price.**
  Output is a minor line item here; a turn's reply is a sentence and a tool
  call, not an essay. The input side, resent and growing, dominates.

## What browser-agent work demands from a model

This is not creative writing, and rankings built on prose quality mislead here.
What the loop actually exercises:

- **Tool-call discipline.** Every turn must produce a well-formed call with
  valid JSON arguments. The loop tolerates a malformed one - it tells the model
  its arguments were unreadable and lets it retry - but each such retry is a
  full-price turn that moved nothing.
- **Instruction following under a system prompt.** The agent is told to inspect
  before acting, to prefer one action at a time, and to stop calling tools when
  the task is done. A model that keeps calling tools after the answer is in hand
  burns turns; one that answers without reading the page invents results.
- **Reading long, messy context.** By mid-task the transcript is mostly
  extracted page text. The model has to find the price in the noise, and notice
  when a click changed nothing.
- **Knowing when it is done, and when it is stuck.** The worst outcome is not a
  wrong answer, it is 25 turns of confident wandering: the loop then stops with
  an error and you have paid for the whole journey with no answer at the end.

Speed matters more than in chat, too: a person watches the interface while up to
25 round trips happen in sequence, so per-turn latency multiplies.

## Real prices, and one worked comparison

Retrieved from OpenRouter on 2026-09-08. OpenRouter routes each model across
several providers, so cheap models show a price range rather than one number,
and all of these move; check the model's page before relying on them.

| Model | Input, per 1M tokens | Output, per 1M tokens |
|---|---|---|
| `z-ai/glm-5.3-flash` (the default) | $0.071 - $0.388 | $0.237 - $1.358 |
| `anthropic/claude-sonnet-4.5` | $3.00 - $3.30 | $15.00 - $16.50 |

The default's range is that wide because two dozen providers serve it and
OpenRouter picks one per request, so a task's bill depends on where it landed as
well as on how long it ran. Sonnet's lower figures are the standard tier; above
200,000 prompt tokens a higher tier applies ($6.00 / $22.50), which an agent
transcript can in principle reach, though with this loop's 25-turn cap and
clipped tool results it rarely will.

One more number from the same page, because it changes what stops a run: the
default's context window is 1,310,720 tokens, against 204,800 for `z-ai/glm-4.6`,
the default before it. With a 25-turn cap and tool results clipped at 8,000
characters, a transcript will not come near filling that window, so the ceiling
you actually meet is the turn cap or the bill, not the model's context.

Now the arithmetic, illustrative rather than measured: take a 20-turn task whose
transcript averages 15,000 tokens per turn. That is about 300,000 input tokens,
plus a few thousand output tokens.

- On the default, at the top of its range: about $0.12 of input and under a cent
  of output. Call it **$0.12**. Routed to the cheap end of the same range, the
  same task is about **$0.02**.
- On Claude Sonnet 4.5: $0.90 of input and $0.06 of output. Call it **$0.96**.

Same task: an 8x multiplier against the default's most expensive provider, and
around 40x against its cheapest. All of them are under a dollar, which is the
honest scale of a single task; the multiplier is what compounds when you run
fifty of them, or when a monitoring job runs one every hour.

## The catch: a cheaper model that retries is not cheaper

The table above assumes both models take the same 20 turns, and they do not. A
weaker model clicks the wrong element and has to notice and recover, re-reads
pages it already read, or wanders into the 25-turn ceiling - and a task that
dies at the ceiling costs more than a task that succeeds, because the transcript
was at its largest exactly when it was being resent most. Three failed cheap
runs plus one successful one can overtake a single clean run on a model five
times the price.

That caveat applies to the default as much as to anything you might downgrade
to. It is a fast, cheap model, and this wiki has no measurement of how it holds
up over twenty turns of tool calls in this particular loop. What is known is the
price, the context window, and that it is what you get if you set nothing; how
many turns it takes on your tasks is something to read off your own transcripts,
not off this page. Neither direction of this is guaranteed, which is why the only
trustworthy comparison is empirical: same task, both models, read the
transcripts. [Browser problem or model problem?](browser-problem-or-model-problem.md)
covers how to make that comparison clean, and passing the same `--seed` keeps
the browser identity constant between runs so the model is the only variable
you moved.

## How to choose in practice

1. **Start with the default.** If your tasks succeed on it, there is nothing
   to optimize; a bigger model would have done the same work for several times
   the money.
2. **When a task fails, diagnose before upgrading.** A blocked page or a
   challenge page is not a model problem, and no model spend fixes it; the
   [diagnostic page](browser-problem-or-model-problem.md) separates the two.
3. **Upgrade on model-side symptoms only**: wrong elements, loops, premature
   "done", turn-ceiling errors on tasks that ought to be short. Try a frontier
   model on the same task and compare transcripts, not vibes.
4. **Match the model to the task's stakes.** A nightly check that reads one
   number can live on the cheapest thing that works ([monitoring is exactly
   this shape](how-to-monitor-a-page-with-an-ai-agent.md)); a long multi-step
   extraction where a wrong answer costs you something deserves the stronger
   model, because the model is the cheapest part of being wrong.

One boundary stated plainly: this page cannot tell you the best model id to
paste, because that answer decays in weeks and depends on your tasks. The
criteria above do not.

## Short answers to the questions that lead here

**What model does AIHawk use by default?** `z-ai/glm-5.3-flash`, via OpenRouter. Set
`--model` or `AIHAWK_MODEL` to use anything else OpenRouter serves.

**Do I need an OpenRouter account?** For AIHawk's own interface, yes - the
model comes from OpenRouter and nowhere else in the current source, and since
0.4.0 `aihawk ui` refuses to start without a key. The spend-nothing routes are
your assistant over MCP (its subscription is the model) and the
invisible_playwright library (no model at all).

**Is a frontier model worth it for browser automation?** Only when the
transcript shows model-side failures on a cheaper one. On tasks the default
handles, a frontier model does the same work at several times the price; on
tasks the default fumbles, it can be cheaper than the retries.

**Why did a short task cost more than I expected?** Because every turn resends
the whole transcript, so cost grows with turns times context, not with the
length of your instruction. One early full-page read is paid again on every
later turn.

**Does AIHawk send my key anywhere besides OpenRouter?** It is used for the
OpenRouter API and stripped from the environment the browser engine starts
with, by name and by value; the repository carries a test that fails if that
stops being true.

**Can I cap what a task spends?** There is no money cap in the current source.
The structural caps are 25 turns per instruction and 8,192 tokens per reply,
and the interface shows running token usage while a task runs, so a runaway is
visible while it is still cheap.

## Sources

All retrieved 2026-09-08.

- [OpenRouter: Z.ai GLM 5.3 Flash](https://openrouter.ai/z-ai/glm-5.3-flash), for
  the default model's per-provider pricing range and its context length.
- [OpenRouter: Z.ai GLM 4.6](https://openrouter.ai/z-ai/glm-4.6), the previous
  default, for the context-window comparison only.
- [OpenRouter: Claude Sonnet 4.5](https://openrouter.ai/anthropic/claude-sonnet-4.5),
  for the frontier comparison pricing and the long-context tier.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), this repository's
  source: `src/aihawk/llm.py` (default model, OpenRouter-only base URL, key and
  model resolution), `src/aihawk/agent.py` (the loop, turn cap, token caps,
  transcript resending, usage meter), and `src/aihawk/runner.py` with
  `tests/test_key_isolation.py` (the key never reaching the browser process).

**See also:** [browser problem or model problem?](browser-problem-or-model-problem.md),
[agent retry loops and rate limits](agent-retry-loops-rate-limits.md), and the
rest of [Using the Agent](guides-using-the-agent.md).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The mechanics
here - the default, the caps, the resent transcript - are read from the source;
the prices from OpenRouter on the date shown. Both drift, so trust the criteria
longer than the numbers.*
