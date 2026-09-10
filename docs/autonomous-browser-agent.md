---
title: "Autonomous browser agents: the four rungs of autonomy"
description: "Autonomy is a spectrum, not a feature. The four rungs, what breaks above rung two, and the three-question test for whether your task belongs on the top."
parent: "Alternatives and Comparisons"
nav_order: 29
---

# What an autonomous browser agent can and cannot do

"Autonomous" is used as a yes-or-no property and it is not one. There are four
rungs, every product sits on one of them for your specific task, and the gap
between rung three and rung four is where most disappointment lives.

## The four rungs

**Rung 1: suggested.** The agent proposes, you approve each step. Slow, and the
only setting in which a mistake cannot cost you anything.

**Rung 2: supervised.** It runs, you watch, you can stop it. This is where most
useful work actually happens and where most people should start.

**Rung 3: unattended, bounded.** It runs without you, on a task with a defined
end state, with a budget and a timeout. Nobody is watching, but it cannot go far.

**Rung 4: unattended, open-ended.** "Monitor these sites and tell me when
something interesting happens." No defined end. This is what the word autonomous
suggests, and it is the rung where the failure modes below are not
hypothetical.

The useful question is never "is this tool autonomous". It is **which rung does
my task belong on**, and the honest answer for most tasks is two or three.

## What breaks above rung two

**Nothing knows when to stop.** A task with no end state does not end. Left
alone, an agent will keep browsing, and it will keep billing. A turn budget and
a wall-clock timeout are not optional at rung three; they are what makes rung
three different from an accident.

**Errors compound silently.** At rung two you see the wrong click and stop it.
Unattended, the wrong click becomes the state the next decision is made from, and
by step twenty the agent is somewhere unrelated, confidently. The mitigation is
a check between steps that the page is still the kind of page expected, and a
stop when it is not.

**Authority becomes the risk.** An unattended agent with a logged-in session can
act with your credentials, and a page can address instructions to it in the same
channel your instruction arrived. That is prompt injection, and unattended plus
logged-in is exactly the combination that turns it from a wrong answer into an
action. [Getting an agent to log into a website](ai-agent-login-to-a-website.md)
and [should you log your agent into accounts](should-you-log-your-ai-agent-into-accounts.md)
are the pages for that.

## The test for whether your task belongs on rung four

Three questions. If any answer is no, it belongs lower.

**Can you write the stopping condition in one sentence?** If not, the agent
cannot either, and it will not stop.

**If it does the wrong thing forty times, what does it cost?** Money, an account
suspension, or a row of real actions taken on a real site. If the answer is
worse than "wasted tokens", stay at rung two or take the account away.

**Would a script do it?** If the steps are the same every time, a script is
faster, cheaper, deterministic and cannot wander.
[Playwright MCP vs the CLI](playwright-mcp-vs-cli.md) has that split, and
[using a browser MCP server for web scraping](mcp-for-web-scraping.md) applies
it to the volume case, where the answer is nearly always the script.

The tasks that genuinely want rung four are the ones where the next step is not
knowable in advance **and** the wrong step is cheap. That is a narrower set than
the marketing implies, and recognising which side of the line you are on is
worth more than any tool choice.

## What tools actually give you

Most agent libraries and MCP servers are rung two by default and let you build
rung three: browser-use, Skyvern, Stagehand, the MCP servers including this one.
Rung three is where you add the budget, the timeout and the state checks, and
that work is yours in every one of them.

The consumer agentic browsers sit closer to rung two by design, because they
run in front of you.
[What is an agentic browser](what-is-an-agentic-browser.md) covers that split.

Nothing on this list makes rung four safe. They make it possible, which is not
the same claim.

## Short answers to the questions that lead here

**What is an autonomous browser agent?** A program that decides its own next
browser action toward a goal. How much of that decision it makes without you is
the spectrum above.

**Can I leave one running overnight?** With a budget, a timeout, a defined end
state and no credentials it can spend. Otherwise you are gambling.

**Are autonomous agents reliable?** At rung two, useful. At rung four, the
compounding failure is real and unavoidable, because there is nobody to catch
step three.

**Is an autonomous agent the same as an AI browser?** No.
[AI browser vs AI browser agent](ai-browser-vs-ai-browser-agent.md) separates
them.

**Will it get blocked if it runs unattended?** More likely, because unattended
usually means faster and more regular, and rate and rhythm are what get judged.
[Why an agent gets blocked](why-does-my-ai-agent-get-blocked.md).

**See also:** [running an agent on a schedule](run-ai-agent-on-a-schedule.md),
[writing tasks for a browser agent](writing-tasks-for-an-ai-browser-agent.md),
and [choosing an AI browser agent](best-ai-browser-agent.md).

## Sources

- [Same-Origin Policy for Agentic Browsers](https://arxiv.org/pdf/2606.14027), retrieved 2026-09-10, for the authority problem at the unattended end.
- The [browser-use](https://github.com/browser-use/browser-use) and [Skyvern](https://github.com/Skyvern-AI/skyvern) repositories for what each provides out of the box.

---

*Written by a project in this category. The page argues that most tasks belong
two rungs below what the category advertises, which is the opposite of a sales
pitch and the reason it is worth reading.*
