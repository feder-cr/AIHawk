---
title: "What is an agentic browser? Definition and the two kinds"
description: "An agentic browser acts for you instead of just showing pages. The two products that share the name, the four problems both solve, and the security gap."
parent: "Alternatives and Comparisons"
nav_order: 24
---

# What is an agentic browser?

An agentic browser is a browser that can carry out a task for you, rather than
only display pages while you do the clicking. You give it an instruction in
words, and it navigates, reads, clicks, fills forms and reports back. The
browser is still a browser: what is new is that an AI agent sits inside it with
the ability to drive the same UI you would have driven.

That is the whole definition. Everything else on this page is the part the
definition hides, and the reason people search this term twice.

## The term covers two different products, and that is why it is confusing

Search this phrase and you get two kinds of result that barely overlap: consumer
browser reviews, and security advisories. They are not talking past each other
by accident. There really are two things.

**A browser you use, with an agent inside it.** You install it, you log in, you
browse. When you want something done, you ask. Perplexity's Comet, OpenAI's
ChatGPT Atlas, Opera Neon, Fellou, Dia, Sigma and the open-source BrowserOS all
sit here, as do the agent features being folded into Chrome and Firefox. The
agent inherits your session, your cookies and your logged-in accounts, because
it is running in your browser.

**A browser your code drives, with an agent in the loop.** No window you sit in
front of. A program starts a browser, an LLM decides what to do next, and the
browser does it. browser-use, Skyvern, Stagehand and
[AIHawk](https://github.com/feder-cr/AIHawk) - this wiki's project - are this
shape. Nobody is logged in unless you arrange it.

The words are almost the same and the risk profile is opposite. If you are
comparing tools, work out which one you meant first, because a review of Comet
tells you nothing useful about a library, and vice versa. This wiki keeps that
split on its own page:
[AI browser vs AI browser agent](ai-browser-vs-ai-browser-agent.md).

## The four things any agentic browser has to solve

Whichever shape it is, the same four problems show up, and how a product answers
them is a better comparison axis than its feature list.

**How the agent perceives the page.** Two families. Either the model reads a
structured description of the page - the accessibility tree, or the DOM reduced
to something a model can hold - or it looks at a screenshot and works in pixels.
Structured reading is cheaper and more reliable when the page is well built;
pixels are the fallback for canvas, custom widgets and anything the tree does
not describe. Most serious tools now do both and pick per step.

**How it acts.** A selector-based click is precise and brittle. A coordinate
click is general and blind. Whether the resulting event looks like a person
depends on the layer underneath, which is a separate question from the agent.

**What it is allowed to do.** This is the one that will decide the category.
An agent that inherits your logged-in session can do anything you can do,
including things you did not ask for, if it is talked into it by text on a page.

**Whether the site can tell.** An agentic browser is still automation as far as
a defended site is concerned, and the tells live in the browser build and the
network path, not in the agent's reasoning. This wiki has a whole section on
that: [when the agent gets blocked](guides-when-the-agent-gets-blocked.md).

## The security argument, stated fairly

The reason a security vendor outranks a product page for this term is that the
consumer shape has a genuinely unsolved problem: **prompt injection**. The agent
reads the page in order to act on it, so text on the page arrives in the same
channel as your instruction. A page can contain a sentence addressed to the
agent rather than to you. If the agent is browsing with your session, the worst
case is not a wrong answer, it is an action taken with your credentials.

The research literature in 2026 is actively proposing browser-level answers to
this - work on a same-origin policy for agentic browsers is one direction, the
idea being that an agent's authority should be scoped the way a script's already
is. None of it is settled. Treat any product claim of "we handle prompt
injection" as a claim, and ask what it means mechanically.

The library shape dodges most of this by default, for a boring reason: it
usually starts with no session at all. That is not virtue, it is scope. The
moment you hand a code-driven agent a logged-in profile, you have the same
problem, which is why this wiki has a page asking
[whether you should log your agent into accounts](should-you-log-your-ai-agent-into-accounts.md)
before you do it.

## Do you want one?

- **You want to save yourself clicks on sites you are logged into.** A consumer
  agentic browser. Accept that it acts with your session, and read what it does
  with your data before you enable it on your bank.
- **You want a task to run repeatedly, unattended, on a schedule.** Not a
  consumer browser. You want the library shape, where the run is a program you
  can log, replay and rate-limit.
- **You want to pull data out of sites at volume.** Probably not an agent at
  all, at least not for the whole job. See
  [AI browser agents vs traditional scraping](ai-browser-agents-vs-traditional-scraping.md):
  an agent is the right tool for the part that changes and the wrong tool for
  the part that repeats.
- **You want your existing assistant to be able to open a page.** That is the
  MCP route, and it is the cheapest of the four to try:
  [the MCP server](mcp-server.md).

## Short answers to the questions that lead here

**What does agentic mean in a browser?** That the browser can take a sequence of
actions toward a goal you stated once, instead of executing the single action
you just clicked.

**Is an agentic browser the same as an AI browser?** Not quite. An AI browser
may only summarise and answer; an agentic one acts. Products blur the line
because acting is the feature people pay for.

**Is an agentic browser safe?** The mechanism to worry about is prompt
injection, not the AI generally. The exposure scales with what the agent is
logged into, so the honest answer depends entirely on how you configure it.

**Are there open-source agentic browsers?** Yes, in both shapes.
[Open-source agentic browsers and agents](agentic-browser-open-source.md)
covers what exists and what each one actually gives you.

**Will sites block an agentic browser?** Defended sites block automation whether
or not there is an agent involved, and they judge the browser and the network
path, not the intent. Start with
[why an agent gets blocked](why-does-my-ai-agent-get-blocked.md).

**See also:** [Choosing an AI browser agent](best-ai-browser-agent.md) for the
decision framework, [What is an AI web agent?](ai-web-agent-explained.md) for
the library shape in detail, and
[the MCP server](mcp-server.md) for turning an assistant you already run into
one.

## Sources

- [Top 5 agentic browsers in 2026: capabilities and security risks](https://seraphicsecurity.com/learn/ai-browser/top-5-agentic-browsers-in-2026-capabilities-and-security-risks/), Seraphic Security, retrieved 2026-09-10, for the security framing and the product list.
- [What is an agentic browser](https://www.sigmabrowser.com/blog/what-is-an-agentic-browser-best-agentic-browsers-in-2026), Sigma, retrieved 2026-09-10, a vendor overview of the consumer shape.
- [Same-Origin Policy for Agentic Browsers](https://arxiv.org/pdf/2606.14027), arXiv preprint, retrieved 2026-09-10, for the browser-level direction on prompt injection.
- The [browser-use](https://github.com/browser-use/browser-use), [Skyvern](https://github.com/Skyvern-AI/skyvern) and [AIHawk](https://github.com/feder-cr/AIHawk) repositories for the library shape.

---

*Written while maintaining [AIHawk](https://github.com/feder-cr/AIHawk), which
is one of the tools in the second category. The page is deliberately about the
category rather than the product, and the section that tells you when you do not
want an agent is there because it is the honest answer more often than a project
in this space likes to admit.*
