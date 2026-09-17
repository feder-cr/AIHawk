---
title: "Keeping an AI browser agent out of destructive actions"
description: "The guardrails that work are the ones outside the prompt. What a browser can refuse at the tool boundary, what only the account can stop, and the refusal message this one gives, verbatim."
parent: "Using the Agent"
nav_order: 49
---

# Keeping an AI browser agent out of destructive actions

An agent driving a logged-in browser can do anything you can do in that browser,
including the things with no undo. The instinct is to write "do not delete
anything" in the task. That is the weakest of the available defences, because it
lives in the same text the page can argue with.

Defences sort into three layers by where they are enforced, and only the outer
two hold.

## Layer 1: the prompt, which is advice

"Never click Delete" is a sentence in a context window that also contains the
page. If the page contains text that reads like an instruction, the two are in
the same medium and the model weighs them. That is the whole mechanism behind
prompt injection, and it is why an instruction is a preference rather than a
control.

Keep writing it. It shifts behaviour. Just do not count it as the thing that
stops a mistake.

## Layer 2: the tool boundary, which is a wall

This is the layer worth understanding, because it is enforced by code that the
model does not get a vote on.

A browser server that exposes "run this JavaScript" has effectively no boundary:
every restriction above it is advice, because script can do anything the page can
do. A server that exposes *named actions* has a real one, because a tool that does
not exist cannot be called.

This project's server refuses the obvious script routes, and says why in the
error rather than failing silently. Verbatim:

> refused: this changes the page from script, which produces an untrusted event
> and is exactly what this browser exists to avoid. Use browser_click, or
> browser_click_at when no selector describes the target. Reading is fine - it is
> assigning and calling that is refused. If no tool fits, say so in your answer
> rather than working around it.

That is the message for a scripted `click()`. Assigning to a field's `value`
returns the same sentence with a different middle: "Use browser_type for a text
field, browser_select_option for a dropdown, browser_click for a checkbox or a
radio."

Three things about that message are the design and not the wording. It **names
the tool to use instead**, and names the right one per case, so the refusal is a
redirect rather than a dead end.
It draws the line at **assigning and calling, not at reading**, so inspection
stays free. And the last sentence tells the model what to do when nothing fits,
which is the sentence that prevents a creative workaround.

⛔ **And the honest limit, which this project states about its own guardrail:**
that refusal catches the obvious roads, not every road. JavaScript has unlimited
ways to say the same thing. It is a guardrail on the paths worth catching, and a
silent pass is not a permission.

## Layer 3: the account, which is the only real one

Everything above is inside your browser. The only defence that survives an agent
doing exactly what it was asked, to the wrong object, is outside it.

- **A separate account with the permissions the task needs and no more.** A
  read-only API user cannot delete, no matter what it is told.
- **A separate browser profile** that is logged into that account and nothing
  else, so the blast radius is one service rather than every tab you own.
- **Whatever the service offers**: a trash that holds for thirty days, a
  confirmation step, an audit log, a sandbox tenant.

[Should you log your AI agent into your accounts](should-you-log-your-ai-agent-into-accounts.md)
takes the question of whether to give it a session at all, including the cases
where the answer is no. This page assumes you already did.

## The practical shape

For anything irreversible, the pattern that works is **propose, then confirm**:
the agent finds the thing and reports what it would do; a person, or a second
process, does the last click. It costs one round trip and it converts an
unrecoverable mistake into a message you ignore.

Where a human is not available, the substitute is a dry run against a copy: the
same task against a staging tenant or a test account, with the output diffed
before it is repeated for real.

And the cheap one, which is not really a guardrail but prevents a good share of
the damage: **give the agent a stopping condition**. A run bounded by an artifact
and a page budget does not wander far enough to find the dangerous button. That is
[its own page](giving-an-ai-agent-a-stopping-condition.md).

## What "destructive" includes that people forget

Deleting is the obvious one. The list that actually bites is longer, and every
item on it has been reachable by a misread page:

- **Sending.** A message, an email, a form that notifies somebody. No undo, and
  the damage is to a relationship rather than to data.
- **Buying.** A stored card and a one-click checkout is one misclick.
- **Publishing.** A draft posted, a visibility toggle flipped.
- **Overwriting.** A form saved with the fields the agent could read and blanks
  where it could not, which silently erases what was there.

That last one is the quiet one. It does not look like a destructive action at any
point, and it is the most likely of the four.

## Short answers to the questions that lead here

**How do I stop an AI agent from deleting things?** Not with the prompt. Use an
account that lacks the permission, or a tool surface with no delete in it, and
keep a confirmation step for anything irreversible.

**Is a system prompt enough to keep an agent safe?** No. The prompt and the page
are the same medium, so a page can argue with your instruction. Prompts shift
behaviour; they do not enforce.

**What is the safest way to let an agent act on my accounts?** A dedicated
account with least privilege, in a dedicated profile, with a propose-then-confirm
step in front of anything with no undo.

**Does refusing JavaScript make the agent safe?** It removes the easiest way
around the named tools, and this server says so plainly in its own refusal. It is
a guardrail on the obvious road, not a wall around the field.

**What is the most common irreversible mistake?** Saving a form with blanks where
the agent could not read the existing value. It never looks like a destructive
action while it is happening.

**See also:**
[why did the agent click the wrong thing](why-did-the-agent-click-the-wrong-thing.md),
which is the mechanism behind most of the accidents this page is guarding
against, and
[how the tools are shaped, and why](mcp-tool-design.md), on why a small named
surface is a safety property and not only an ergonomic one.

## Sources

- The refusal message is quoted from this project's own MCP server, read from its source on 2026-09-17 and reproduced in full. It was also triggered live on three expressions during the same session: a `click()` call, a `value` assignment and a `submit()` call, each of which returned it.

---

*The three layers are ordered by how much they cost to set up and inversely by
how much they help, which is why most people have only the first one.*
