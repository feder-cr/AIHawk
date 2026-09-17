---
title: "Secrets in an agent task: where they end up"
description: "A password typed into a task is in the transcript, and the transcript goes to the model, to the log and possibly to disk. Four places to check, and the two designs that avoid the question."
parent: "Using the Agent"
nav_order: 78
---

# Secrets in an agent task: where they end up

If you write a password into a task, you have not handed it to a browser. You
have handed it to a conversation, and a conversation has more addresses than
people expect.

## The four places it goes

**The model.** Whatever is in the task is in the prompt, sent to whoever serves
your model, and subject to their retention policy rather than yours. If you are
driving from an assistant, that is the assistant's provider.

**The transcript.** Client-side history, often on disk, often unencrypted,
frequently synced. A value typed once lives in every later turn of that
conversation, because each turn resends what came before.

**The tool call arguments.** `browser_type` takes the text as a parameter, so the
value appears in the call, in whatever the client logs about calls, and in any
debug output.

**The page.** Where you wanted it, and the only one of the four you intended.

Three out of four are accidental, and none of them is a flaw in any particular
tool: it is what "tell the agent your password" means.

## The two designs that avoid it

**A persistent profile.** Log in once, by hand, in a headed browser, and keep the
profile. The session cookie lives on disk under your control and no credential
ever enters a conversation:

```
STEALTHFOX_PROFILE_DIR=C:/path/to/a/profile-you-keep
```

This is the right answer for almost every real case, and it is the one
[getting an AI agent to log into a website](ai-agent-login-to-a-website.md)
already recommends. The task then says "you are already signed in" and never sees
a password.

**A human step in a headed browser.** For anything the profile cannot carry: a
code from an app, a hardware key, a login that re-challenges. The agent drives to
the login page and stops; you type; it continues. Slower, and correct.

## If a secret has to be in the run

Sometimes there is no profile to lean on, an API key for instance, and then the
question is how to limit the damage rather than avoid it.

- **Scope it down.** A credential that can only read cannot do the thing you are
  worried about. The account-level argument is in
  [keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md).
- **Make it short-lived**, and revoke it at the end of the run rather than at the
  end of the quarter.
- **Never reuse a personal one.** A dedicated credential for automated work means
  a leak is a revocation rather than an incident.
- **Assume the transcript is readable.** By you later, by anyone with the
  machine, by a support process if you ever paste it into one. Write the task as
  though it will be.

## The one that catches people: the page shows it back

A logged-in page displays your name, your email, sometimes the last four digits
of something. Every read the agent takes contains that, and every screenshot
paints it.

So even a run with no secret in the task accumulates personal data in the
transcript simply by looking at pages. Two consequences worth acting on: scope
reads to the region you need rather than taking the whole page, and open any
image before it leaves your machine, which is the standing rule in
[dated screenshots of a page as evidence](dated-screenshots-as-evidence.md).

## What not to bother with

**Obfuscating the secret in the prompt.** Base64 or a substitution does not help:
the model decodes it, and the decoded value is in the same transcript.

**Asking the model not to repeat it.** It will mostly comply and it is not a
control. The value was already transmitted when you sent it.

**Putting it in an environment variable and then reading it into the task.** If
it ends up in the task, it ends up in all four places. The environment variable
only helps if the thing that consumes it is the process, not the conversation:
the profile directory above is the example that works.

## Short answers to the questions that lead here

**Is it safe to give an AI agent my password?** It goes to the model, the
transcript, the tool call and the page. Use a persistent profile and log in by
hand instead.

**How do I let an agent use a logged-in site without a password?** Log in once
yourself in a headed browser with a profile directory set, and keep that profile.
The session survives and no credential enters the conversation.

**What if I need an API key in the run?** Scope it to read-only where possible,
make it short-lived, use a dedicated one, and revoke it after.

**Does hiding or encoding the secret help?** No. The model decodes it and the
result is in the same transcript.

**Is a run without secrets clean?** Not automatically. Logged-in pages show
personal data, and every read and screenshot captures it.

**See also:**
[should you log your AI agent into your accounts](should-you-log-your-ai-agent-into-accounts.md),
which is the prior question, and
[what a run should log](what-a-run-should-log.md), where the same data ends up if
you are not deliberate about it.

## Sources

- The four destinations follow from how a tool-using conversation works rather than from a measurement, and the page says so. The profile directory setting is this project's own, documented on [the MCP server page](mcp-server.md).

---

*The whole page is one observation: a task is a message, not a configuration
file. Everything else is what follows from that.*
