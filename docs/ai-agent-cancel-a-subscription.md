---
title: "Cancelling a subscription with an AI agent"
description: "The one task where the agent should probably not press the button. Where cancellation flows genuinely obstruct, what an agent is good for here, and the confirmation that has to stay human."
parent: "Using the Agent"
nav_order: 65
---

# Cancelling a subscription with an AI agent

This is the task people most want to hand over and the one where handing over the
final click is the worst idea on this wiki. Worth separating what an agent is
genuinely good at here from the part that should stay with you.

## Why the last click stays human

A cancellation is irreversible in a way that matters and asymmetric in a way that
bites:

- **Cancel the wrong subscription** and you may not get the same price back. Grandfathered
  rates, legacy plans and promotional terms usually do not survive.
- **Cancel at the wrong moment** and you lose the remainder of a period you have
  already paid for, or you trigger a fee.
- **Choose the wrong option** in a flow that offers pause, downgrade, cancel at
  period end and cancel immediately, and three of those four are not what you
  asked for.
- **Fail to confirm the last step** and you believe it is cancelled when it is
  not, which is the expensive failure because you find out a month later.

That last one is the argument against automating the click even when you trust
the agent. The failure is silent, delayed, and indistinguishable from success
from inside the run.

So the shape is **propose, then confirm**, as in
[keeping an AI browser agent out of destructive actions](keeping-an-ai-agent-out-of-destructive-actions.md).
The agent does the tedious ninety per cent and stops with its hand over the
button.

## What the agent is genuinely good at here

**Finding the flow.** Cancellation is frequently four or five levels deep, under
a name that is not "cancel": Manage plan, Subscription settings, Membership,
Billing, sometimes only in a help article. An agent that reads and navigates
finds it faster than you will, and does it without getting annoyed.

**Reading the terms before you commit.** What happens to the remaining period, the
notice period, whether there is a fee, whether you keep access until the end.
These are usually stated somewhere in the flow, in small text, and they are
exactly what you want extracted and put in front of you.

**Doing it across several services.** The value of this task is almost never one
subscription. It is the six you are not sure you still have, which makes it a
list task with
[everything that implies](run-one-task-across-a-list-of-sites.md).

**Auditing rather than cancelling.** Honestly the highest-value version: open each
account, record what the plan is, what it costs, when it renews, and where the
cancel control lives. That list is the thing you actually needed, and it involves
pressing nothing.

## The flows are obstructive on purpose, and that is the interesting part

Retention flows are designed to add friction: extra confirmation screens, an
offer, a survey, a chat widget, a button labelled "keep my benefits" placed where
the continue button was on the previous screen.

Two consequences for the agent:

**Layout traps hit coordinate clicks hardest.** A flow that moves the primary
button between steps is precisely the case where clicking by position goes wrong,
and by selector fails cleanly instead. That asymmetry is the subject of
[why did the AI agent click the wrong thing](why-did-the-agent-click-the-wrong-thing.md).

**"Are you sure" screens are not all the same screen.** Some confirm the
cancellation, some confirm accepting an offer instead. An agent walking a flow by
pressing whichever button continues will accept a discount and report that it
cancelled.

The instruction that prevents it: **read each screen back and say what it is
offering before doing anything**, and stop at anything that is not plainly the
cancellation step.

## Some of it you will not be able to do at all

A meaningful share of services require a phone call, a form that generates a
support ticket, an email to a specific address, or a chat with a human. That is
not an agent limitation and no amount of driving fixes it.

Where the route is a support conversation, the useful output is a drafted message
with the account details filled in, for you to send. Have the agent recognise this
branch and produce that rather than attempting a conversation on your behalf: a
chat window is a person on the other end, and an agent negotiating with them
without saying it is an agent is a different thing from filling a form.

## A task that works

> For each service in subscriptions.csv, log in with the profile named in the
> row and find the subscription settings.
>
> Record: the plan name, the amount and currency, the billing period, the next
> renewal date, whether cancelling takes effect immediately or at period end, any
> notice period or fee stated, and the exact path you took to reach the
> cancellation page.
>
> Go as far as the screen that would perform the cancellation. Do not press it.
> Screenshot that screen, say what the button is labelled and what the page says
> will happen, and stop.
>
> If the service requires a phone call, an email or a chat, write that in the
> notes column and move on without starting any of them.

You then do six clicks having read six accurate summaries, which is the right
division of labour.

## Short answers to the questions that lead here

**Can an AI agent cancel my subscriptions?** It can navigate the whole flow and
should stop before the final button. The failure mode of automating that click is
silent: you believe it is cancelled and it is not.

**What is the safest way to use an agent here?** As an audit. Have it list every
subscription, cost, renewal date and where the cancel control is. Then press the
buttons yourself.

**Why did the agent accept a discount instead of cancelling?** Retention screens
reuse the layout of the confirmation screens. Require it to read back what each
screen offers before acting, and to stop on anything that is not plainly the
cancellation.

**What if cancelling needs a phone call or an email?** Have the agent detect that
branch and draft the message with your details in it. Do not have it hold a
conversation on your behalf.

**Should it click by position or by selector?** Selector. These flows move the
primary button between steps, which is the exact case where a positional click
lands on the wrong thing and reports success.

**See also:**
[should you log your AI agent into your accounts](should-you-log-your-ai-agent-into-accounts.md),
which is the prior question this task assumes you have answered, and
[giving an AI browser agent a stopping condition](giving-an-ai-agent-a-stopping-condition.md),
since "stop at the confirmation screen" is exactly one.

## Sources

- No external figures are cited. The claims here are about how cancellation flows are built and about where to put the human step, and a number invented for either would be worse than none.
- No service, retailer or subscription product is named anywhere on this page.

---

*The audit version is the one to build. It produces the thing you actually
wanted, which is the list, and it cannot cancel the wrong plan.*
