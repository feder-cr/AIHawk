---
title: "browser-use on GitHub: what the repo actually gives you"
description: "The repo is github.com/browser-use/browser-use, MIT, 114k stars. What you get when you clone it, the three ways it ships, and what its config does not reach."
parent: "Alternatives and Comparisons"
nav_order: 31
---

# browser-use on GitHub: what the repo actually gives you

If you came here looking for the repository, it is
**[github.com/browser-use/browser-use](https://github.com/browser-use/browser-use)** -
MIT licensed, Python, 114,000 stars when read on 2026-09-10, described by its
own authors as "Agents that use the browser." Go there; that is the primary
source and this page does not try to replace it.

What this page adds is the part a repository landing page does not tell you:
what you are agreeing to when you clone it, which of its three shipping paths
you are actually choosing, and which problems its configuration surface can and
cannot reach. Written by people who maintain a competing project, which is
disclosed here rather than at the bottom.

## What you get, concretely

**Requirements**, from the README: Python 3.11 or newer with 3.12 recommended,
and an LLM API key. The default setup expects an OpenAI key; the project also
supports Anthropic and Google models. Installation is one line, `uv add
browser-use`, which tells you something useful on its own: the project has
standardised on `uv` rather than bare pip, so a tutorial that starts with `pip
install` is working from an older version of the instructions.

**Three shipping paths, and they are not equivalent.** The README presents the
project as a hosted cloud service, a CLI, and a Python library. The library is
the MIT-licensed thing in the repository; Browser Use Cloud is a commercial
product at `cloud.browser-use.com` with its own API key. Which one you are
reading about matters, because most tutorials blur them, and the
[free-tier question](what-is-free-in-the-agent-stack.md) is a different answer
for each.

**Topics the project claims for itself**: ai-agents, ai-tools,
browser-automation, browser-use, llm, playwright, python. That `playwright`
entry is the load-bearing one for anything to do with detection, and the next
section is about it.

## The growth, which is a real input to "should I depend on this"

One number this wiki can offer that the repository page cannot, because it
requires having looked twice: **this project recorded 112,000 stars on
2026-09-03 and 114,000 on 2026-09-10** - roughly two thousand in a week, from
our own dated readings a week apart. For a dependency decision that is the
useful shape of the signal rather than the absolute: this is not a project
that is quietly stalling, and the ecosystem risk is the opposite one, which is
a fast-moving surface you will be upgrading against.

## What the configuration reaches, and what it does not

The README is candid in a way worth quoting, because a lot of derivative
content is not: it states that **no browser configuration guarantees that every
captcha can be avoided or solved**, and that profile sync transfers cookies but
not local storage or extensions.

That first sentence is the honest version of the thing people arrive at this
repo hoping for, and it matches what we found reading the project's own
configuration code rather than its documentation. The detailed reading is on
its own page here -
[what browser-use configuration can and cannot change](browser-use-getting-blocked.md) -
and the short version is that the levers it exposes are real (a real Chrome
binary instead of the bundled build, a user data directory with actual
history) while the layer underneath is a Chromium-family browser driven over
CDP, which no setting in the repository reaches.

That is not a criticism of the project. It is a scope statement, and it is the
same scope statement that applies to every agent framework in this category:
the agent is the part they built, the browser is a dependency they inherited.
[Why an agent gets blocked](why-does-my-ai-agent-get-blocked.md) separates
those two layers properly, and it usually turns out the address and the pacing
matter more than either.

## Where to go from here

- **You want the repo.** The link is in the first paragraph. Nothing below it
  is a substitute.
- **You want to know if it fits your problem.**
  [Choosing an AI browser agent](best-ai-browser-agent.md) is the decision
  framework across the field.
- **You are on it and something is being blocked.**
  [browser-use getting blocked](browser-use-getting-blocked.md), which reads
  the configuration surface rather than guessing at it.
- **You want to know what else exists.**
  [browser-use alternatives](browser-use-alternatives.md), which opens by
  saying browser-use is good and means it.
- **You want the whole open-source layer, not just this project.**
  [Open-source agentic browsers](agentic-browser-open-source.md).

## Short answers to the questions that lead here

**Where is the browser-use GitHub repo?**
[github.com/browser-use/browser-use](https://github.com/browser-use/browser-use).

**Is browser-use free?** The MIT-licensed library in the repository is. Browser
Use Cloud is a separate commercial product, and your model tokens are billed by
whichever provider you point it at either way.

**What Python version does browser-use need?** 3.11 or newer, with 3.12
recommended by the README.

**Does browser-use need an API key?** For a model, yes. The default path
expects an OpenAI key; Anthropic and Google are supported. A separate Browser
Use API key is only for the cloud product.

**Does browser-use solve captchas?** Its own README says no browser
configuration guarantees that every captcha can be avoided or solved, which is
the accurate answer and more honest than most pages written about it.
[Can an AI agent solve a captcha](can-an-ai-agent-solve-a-captcha.md) is the
category-level version.

**Is browser-use maintained?** Actively, on the evidence of roughly two
thousand stars added in the week between our two readings, plus its release
tempo.

## Sources

- [github.com/browser-use/browser-use](https://github.com/browser-use/browser-use), retrieved 2026-09-10: licence, star count, description, topics, requirements, install command, the three shipping paths, and the captcha and profile-sync caveats quoted above.
- This wiki's own reading of the project's configuration code, written up in [browser-use getting blocked](browser-use-getting-blocked.md).
- Our own dated star readings, 2026-09-03 and 2026-09-10, recorded a week apart in this wiki.

---

*Written while maintaining [AIHawk](https://github.com/feder-cr/AIHawk), which
competes with the project this page is about. That is why the repository's own
link is the first thing on the page and why the section on what its
configuration cannot reach ends by saying the same limit applies to every
framework in the category, ours included.*
