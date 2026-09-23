---
title: "invisible_playwright_mcp, reviewed honestly by its own wiki"
description: "What invisible_playwright_mcp does well, what it does not do at all, the real risks of running it, and its AGPL-to-MIT license history - written by the people who maintain it, with the conflict stated in the first line."
parent: "Alternatives and Comparisons"
nav_order: 19
---

# invisible_playwright_mcp, reviewed honestly by its own wiki

This page is the project reviewing itself: it lives on invisible_playwright_mcp's wiki and is
written by invisible_playwright_mcp's maintainers, so it is the most conflicted review of
invisible_playwright_mcp you will find. It exists anyway because most of what ranks for
"invisible_playwright_mcp review" is written by nobody in particular about a repository they
have not read, and because a first-party review can do one thing a
third-party one cannot: state plainly what the project does not do, and be
accountable for it. Every factual claim below is checkable against the
[repository](https://github.com/feder-cr/invisible_playwright_mcp) and the published package,
both read on 2026-09-03 with the default model re-read on 2026-09-08, and the
honest move for a reader is to treat the praise with suspicion and the
self-criticism as reliable.

## What invisible_playwright_mcp is

invisible_playwright_mcp is an open-source AI web agent: you describe a task in plain
language and it drives a real browser until the task is done. The
repository sits at about 30,300 stars and 4,600 forks, has existed since
August 2024, and is MIT licensed. The Python package `invisible-playwright-mcp` is on PyPI
and needs Python 3.11 or newer. This review was written against what the
index and the repository carried on 3 September 2026: 0.3.0 published,
0.4.0 on the main branch. The package has shipped many times since, so
[the PyPI page](https://pypi.org/project/invisible-playwright-mcp/) is the current answer
and this paragraph is not; the statements below that name a version say
which one they describe.

One factual line on where it came from, because the repository description
still says it: the project was born as an AI web agent that applied to
jobs in bulk, drew mainstream press coverage in 2024 that was in part
critical, and has since been rebuilt as the general-purpose agent this
wiki documents; that earlier use is not covered here.

There are two ways to run it, and they share one browser:

- **Inside an assistant you already use.** A plugin for Claude Code
  (`claude plugin install invisible-playwright-mcp@feder-cr`, once the repository is added as a
  marketplace), an extension for Gemini CLI, or a config entry in Claude
  Desktop or Cursor, and your assistant's model does the thinking.
- **Standalone.** `uvx invisible-playwright-mcp ui` serves a local page with chat on the
  left and the live browser on the right. It takes an
  [OpenRouter](https://openrouter.ai) key, defaults to `z-ai/glm-5.3-flash`,
  and accepts `--model` for anything OpenRouter serves. Since 0.3.0 this
  is the only invisible_playwright_mcp entrypoint; headless one-shots run through the
  assistant path above.

The differentiating bet is the browser itself. Instead of driving a stock
automation build over an automation protocol, invisible_playwright_mcp drives a Firefox
patched at the source level so that what a page inspects - the things
JavaScript can read, the way input arrives - presents as a normal desktop
machine. The agent also refuses to set form fields from JavaScript even
when that would be quicker, because a page can tell the difference between
script writes and typed input.

## What it does well

**The browser story is real engineering, not a flag.** The fingerprint
work lives in patched C++, is seed-deterministic (`--seed` gives you the
same browser identity on every run), and is maintained as its own
published engine. This is the part of the project we would defend in any
room.

**It is honest about inputs.** Keys are handled carefully: the OpenRouter
key is stripped from the environment the browser process starts with, by
name and by value, and
[a test in the repository](https://github.com/feder-cr/invisible_playwright_mcp/blob/main/tests/test_key_isolation.py)
fails if that stops being true.

**Operational features match real use.** `--proxy` takes HTTP or SOCKS5
and the browser's timezone, locale and egress follow it; `--profile-dir`
persists logins between runs; `--headed` shows the window; on the
assistant path the same knobs ride the MCP registration as
`STEALTHFOX_*` variables; and for scheduled work the engine itself is a
Python library with Playwright's API. The pieces you need to run it
repeatedly are there, not left as exercises.

**It is genuinely open.** MIT license, the engine and its wrapper
published as installable packages, and the agent code in this repository
short enough to actually read before you trust it with a browser.

## What it does not do

This list is the reason the page exists. None of it is roadmap coyness;
it is what the product is.

- **It does not solve captchas.** Nothing in the codebase attempts it.
  When a challenge appears, the agent's options are the same as any
  script's: stop, or hand the session to you.
- **It does not promise you will not be detected.** A patched browser
  changes what a page can read from the browser; it does nothing about
  your IP's reputation, your pacing, or per-account limits, and this
  wiki maintains [a whole section](guides-when-the-agent-gets-blocked.md)
  on exactly those failure modes. Distrust any tool in this category
  that promises otherwise.
- **No macOS.** Windows x86_64 and Linux x86_64/arm64 only; the last
  macOS engine build was `firefox-20`, and support ended. A Mac user
  cannot run the standalone product today.
- **There is no free mode.** Since 0.4.0 `uvx invisible-playwright-mcp ui` refuses to start
  without an OpenRouter key: an agent is a model with a browser, and tokens
  cost money. Driving the browser by hand without a model is the
  invisible_playwright library's job, not this product's.
- **The browser is a quarter-gigabyte separate download** that the server
  fetches on its own when it starts, unless you pre-fetch it
  (`uvx invisible-playwright fetch`); on a slow connection the first task is
  answered with the download's progress rather than a page.
- **The model is not included, and results track the model.** A weak
  model drives the good browser badly;
  [browser problem or model problem](browser-problem-or-model-problem.md)
  is our own documentation of that boundary.

## The real risks of running it

**Sites can restrict accounts.** Many platforms prohibit automated access
in their terms. If you log the agent into an account on a platform that
does, that account can be challenged, limited or closed, and no browser
engineering changes the contract you accepted. Read the terms of the
sites you point it at; the README says the same thing in its
"Using it responsibly" section, and we mean it.

**An agent with your session is an agent with your session.** Anything
the logged-in browser can do, a misread page or a badly phrased task can
do too. Use `--profile-dir` deliberately, keep high-value accounts out of
it, and do not submit anything a human has not read.

**Prompt injection is a live category.** A hostile page can try to talk
the model into actions you did not ask for. Big-vendor agents carry
classifiers for this; invisible_playwright_mcp's standalone loop places that trust in the
model you chose, and caution in the tasks you give it.

**The UI binds to localhost for a reason.** `--host` beyond `127.0.0.1`
exposes an interface with no authentication; the README warns about
this, and so does this review.

## Is it legit, and which one is the real one

For the searcher asking "is invisible_playwright_mcp safe" in the download-sense: the
canonical repository is
[github.com/feder-cr/invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) and the
canonical package is
[`invisible_playwright_mcp` on PyPI](https://pypi.org/project/invisible-playwright-mcp/). A project with this
history has accumulated forks and mirrors on other sites, some carrying
old code under the old license and the old purpose; none of them are
maintained here, and anything this wiki says applies only to the
canonical pair above. The code you run is auditable before you run it,
which is the strongest safety statement an open project can truthfully
make - not "trust us", but "check".

## The license history, plainly

invisible_playwright_mcp is MIT licensed today. The relicense landed on 2 September 2026,
and the README states the boundary precisely: everything distributed
before 2 September 2026 was released under AGPL-3.0 and stays under it.
In practice: the current code can be used, modified and embedded under
MIT's permissive terms; old snapshots and forks made from them remain
AGPL, with its copyleft obligations. If you vendored invisible_playwright_mcp code before
that date, your obligations follow the license it shipped under, not the
current one.

## Verdict

Use invisible_playwright_mcp if the browser is your bottleneck: your tasks are real
browsing on sites that inspect their visitors, you want open code on your
own machine, and you accept the token bill and the no-macOS line. Its
engine is the most serious open-source attempt we know of at making the
browser itself unremarkable, and we say that as the people who would.

Look elsewhere if you need macOS, captcha handling, a hosted
zero-setup product, or the largest possible community -
[browser-use](browser-use-alternatives.md) has an order of magnitude more
adopters, and the [alternatives hub](guides-alternatives-and-comparisons.md)
compares the field with the same disclosure this page opens with. And
whatever this page just told you, it was the project grading its own
exam: run `uvx invisible-playwright-mcp ui` against a real task of yours, which costs an
afternoon and answers the only question that matters.

## Short answers to the questions that lead here

**Is invisible_playwright_mcp legit?** The canonical repo is `feder-cr/invisible_playwright_mcp` (about 30k
stars, MIT) and the package is `invisible-playwright-mcp` on PyPI. It is real, maintained,
and auditable; mirrors elsewhere are not ours.

**Is invisible_playwright_mcp safe?** The code is open for inspection before you run it,
and the API key is provably isolated from the browser process. The
operational risks - account restrictions, prompt injection, what you
log it into - are yours to manage and are listed above.

**Is invisible_playwright_mcp free?** The software is MIT-licensed free software. Model
tokens are the running cost, via your OpenRouter key or your assistant's
subscription.

**Does invisible_playwright_mcp work on macOS?** No. Windows and Linux only; macOS engine
builds ended at `firefox-20`.

**Does invisible_playwright_mcp solve captchas?** No, and it does not claim to. A
challenge stops the run or goes to a human.

**Who maintains invisible_playwright_mcp?** The developer behind the `feder-cr` account,
who also maintains the patched-Firefox engine and this wiki - which is
exactly the conflict declared in the first line.

**See also:** [Which model to use with invisible_playwright_mcp](which-model-to-use-with-invisible-playwright-mcp.md)
for the token-cost side of the decision, and
[Running invisible_playwright_mcp with Claude Code](running-invisible-playwright-mcp-with-claude-code.md) for
the MCP route.

## Sources

- The [invisible_playwright_mcp repository](https://github.com/feder-cr/invisible_playwright_mcp): README, LICENSE, `pyproject.toml` and `tests/test_key_isolation.py` read in the working tree on 2026-09-03; stars, forks, license and creation date read via the GitHub API the same day; `src/invisible_playwright_mcp/llm.py`, for the default model id, re-read 2026-09-08.
- [`invisible_playwright_mcp` on PyPI](https://pypi.org/project/invisible-playwright-mcp/), version 0.3.0 metadata checked against the index 2026-09-04.
- The relicense commit ("Relicense under MIT", dated 2026-09-02) in the repository history, and the README's license section stating the AGPL-3.0 boundary for earlier distributions, both read 2026-09-03.
- For comparative claims about other tools, the pages linked above carry their own dated sources; none are repeated here.

---

*This is [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp)'s wiki reviewing
invisible_playwright_mcp. You have every reason to discount the compliments, so we put the
limitations in their own section and made every claim point at something
you can check without trusting us.*
