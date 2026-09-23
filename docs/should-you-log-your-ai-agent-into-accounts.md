---
title: "Should you log your AI agent into your accounts?"
description: "What a logged-in AI agent can actually do, the three real risks (misreads, prompt injection, and ToS violations), and the mitigations that limit the damage."
parent: "Using the Agent"
nav_order: 26
---


# Should you log your AI agent into your accounts?

Yes, if you treat the login as a capability grant, not a formality: a session
lets the agent do anything you could do while signed in, including a misread
page taking an unwanted action. The real risks are narrow and known, and a
separate profile, read-only tasks first, and human review before anything
submits handle most of them.

## What a logged-in session actually grants an agent

Nothing about login changes what the agent is: a browser driven by a model,
following whatever instruction it was given. What changes is scope, because a
saved session or a stored credential means every action after that point runs
as you.

If the account can delete a listing, cancel a subscription, send a message, or
move money, an agent signed into it can do all of that without pausing to ask
whether it should. The login is not a formality, it is a set of permissions,
and [invisible_playwright_mcp's own review](stealth-browser-mcp-review.md) names this same trade-off as a
declared limit of the project, not a footnote.

## What can go wrong: the three real risks

Three things go wrong in practice, and they are different enough to need
different fixes. None of them are exotic; all three have happened to real
automation, agentic or not.

### A misread page taking a destructive action

An agent decides its next action from what it currently sees, and it can
misread a button, a confirmation dialog, or a box the site pre-checked rather
than you. A "delete" placed where "cancel" usually sits, or a bulk-select
that grabbed one row too many, turns a routine task into an action nobody
asked for. A human notices when something looks off; an agent following
instructions literally often does not.

### Prompt injection: hostile page content talking to the model

A page an agent visits is not just data, it is also read by the same model
that is following your instructions, and it can carry text aimed at that
model rather than at you: a hidden instruction in a review, a comment, an
email body. This is prompt injection, distinct from a user jailbreaking a
model on purpose, because here the hostile instruction arrives from outside,
through content the model was sent to read.

OWASP's GenAI Security Project ranks prompt injection first in its LLM Top
10, as LLM01:2025, and defines it as a case where "user prompts alter the
LLM's behavior or output in unintended ways". The half that matters for
browsing is the indirect one, which OWASP describes as happening when "an
LLM accepts input from external sources, such as websites or files" whose
content, once interpreted, "alters the behavior of the model in unintended
or unexpected ways". A web page your agent reads is exactly that external
source.

Two of OWASP's own mitigations translate directly into how you run an
agent: enforce least privilege on what the session can reach, and require
human approval for high-risk operations. Both are decisions you make before
the run starts, not settings inside the tool.

Big-vendor agents increasingly ship classifiers to catch this before it
reaches an action; a self-hosted loop places that same trust in whichever
model you chose.

### Terms of service that prohibit automated access

Many platforms write against automated access in their terms, and a
logged-in agent is automation with your name on it. If the site prohibits
it, the account behind that login can be limited or closed, no matter how
carefully the agent was built. Restricted accounts often show the same
symptoms as [an agent getting blocked for other
reasons](why-does-my-ai-agent-get-blocked.md): fewer requests succeed,
challenges appear more often, until access stops. Read the terms before you
log in.

## How to reduce the risk without giving up the login

None of the above argues against ever logging an agent in. It argues for
doing it deliberately, the way you would hand a new employee access.

- **A separate profile directory per task.** invisible_playwright_mcp's `--profile-dir` flag
  keeps logins and cookies in one folder, so a research task and a task on a
  paid account never share a session.
- **Never the profile that holds your highest-value accounts.** Bank logins,
  a primary email, stored payment methods: keep those out of any profile an
  agent drives.
- **Read-only tasks first.** Point a new setup at something that only reads
  before you let it write, click a purchase button, or submit a form.
- **Nothing submitted that a human has not read.** [Filling out a
  form](ai-agent-fill-out-forms.md) is where this matters most: review the
  completed form yourself and keep the submit click human.
- **Revoke the session after a run.** Log out, or clear the profile
  directory, so a stale session is not sitting around for the next task.

Those are the habits. The defences that actually hold when a habit slips are the
ones enforced outside the prompt, and they sort into three layers:
[keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md)
sets them out, including the quiet one that is not deleting anything at all. For
the single task people most want to hand over and most should not,
[cancelling a subscription with an AI agent](ai-agent-cancel-a-subscription.md)
works through where the human click belongs.

And if the reason you are here is that you were about to put a password into the
task itself, the four places it ends up are in
[secrets in an agent task](secrets-in-an-agent-task.md), along with the profile
setup that makes the question go away.

## Does the agent's vendor already protect me from this?

Partly, and it depends which agent you run. Large-vendor assistants
increasingly filter for prompt injection before an instruction becomes an
action, a real defense you get by default. A self-hosted or smaller
open-source agent usually carries no such filter; it places the same trust
directly in whichever model you configured. Either way, the
profile-and-review practices above still apply.

## Short answers to the questions that lead here

**Is it safe to let an AI agent log into my accounts?** It is safe for
low-value, read-mostly accounts run with a dedicated profile and human
review before anything submits. It is not safe as a set-and-forget
arrangement on an account you would not hand a stranger for an afternoon.

**What happens if a site's terms of service ban automated agents?** The
account behind the login can be limited, challenged, or closed, regardless
of how carefully the agent was built. The contract is with the site, not
your tooling, so read the terms first.

**Can prompt injection make my agent do something I did not ask for?** Yes.
A page can carry text aimed at the model, not at you, and a model reading it
cannot always tell your instruction from the page's own content. OWASP
ranks this as a top risk for exactly that reason.

**Do AI agent platforms protect against prompt injection automatically?**
Some do, partially. Large-vendor assistants increasingly filter for it
before an instruction becomes an action; a self-hosted agent usually
carries no such layer, so the caution has to live in your task and profile
choices instead.

**See also:** [A stealth browser MCP, reviewed honestly by its own wiki](stealth-browser-mcp-review.md),
[why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md), and
[getting an AI agent to fill out forms](ai-agent-fill-out-forms.md).

## Sources

All retrieved 2026-09-05 unless noted.

- [feder-cr/invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp), this repository's
  README, for the `--profile-dir` option and the "Using it responsibly"
  section, read in the working tree 2026-09-05.
- OWASP GenAI Security Project, "LLM01:2025 Prompt Injection",
  https://genai.owasp.org/llmrisk/llm01-prompt-injection/ - the quoted
  definition, the indirect-injection passage about websites and files, and
  the mitigations on least privilege and human approval for high-risk
  operations. Read 5 September 2026.

---

*From the [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) wiki. The mitigations
above match the project's own README: read the terms, respect rate limits,
and do not submit anything a human has not read.*
