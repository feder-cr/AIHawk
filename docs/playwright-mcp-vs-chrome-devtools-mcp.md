---
title: "Playwright MCP vs Chrome DevTools MCP: different jobs"
description: "Both are browser MCP servers from major vendors and they answer different questions. One drives a page, one inspects a running Chrome. Which fits when."
parent: "Alternatives and Comparisons"
nav_order: 32
---

# Playwright MCP vs Chrome DevTools MCP: different jobs

Short answer: **Chrome DevTools MCP is for finding out why a page behaves the
way it does; Playwright MCP is for making a page do something.** They overlap
enough to be confused for competitors and were built for different questions,
and picking by star count gets you the wrong one.

| | Chrome DevTools MCP | Playwright MCP |
|---|---|---|
| Maintainer | ChromeDevTools | Microsoft |
| Stars, read 2026-09-10 | 51,500 | 36,900 |
| Licence | Apache-2.0 | Apache-2.0 |
| Browsers | Chrome and Chrome for Testing only | chrome, firefox, webkit, msedge |
| The model sees | DevTools: traces, network, console | the accessibility tree |
| Built for | inspecting and profiling | driving and asserting |

## What each one is actually good at

**Chrome DevTools MCP gives an assistant the DevTools panel.** Performance
traces with insights extracted, network request analysis, console messages,
screenshots, and source-mapped stack traces. The last one is the giveaway:
source maps only matter if you are debugging code you wrote. This is a tool for
your own application, and it is very good at the question "why is this slow, and
what fired when".

**Playwright MCP gives an assistant a browser to operate.** It exposes the page
as an accessibility tree with stable references and a small action vocabulary,
so a model can navigate, click and type its way through a flow.
[What it is and how it differs from the Playwright CLI](playwright-mcp-vs-cli.md)
covers that side in full.

The practical split, in one line each: if you would have opened DevTools, you
want the first. If you would have written a script, you want the second.

## Where the choice is not obvious

**"I want the agent to test my site."** Both, at different moments. Playwright
MCP to walk the flow, Chrome DevTools MCP to find out why the step that failed
was slow or threw. Neither replaces knowing which of the two questions you are
asking at that moment.

**"I want to scrape."** Neither is built for it and Chrome DevTools MCP
especially is not. See
[using a browser MCP server for web scraping](mcp-for-web-scraping.md) for the
pattern that actually works, which uses a model to work out the shape and plain
code to do the repetition.

**"The site keeps blocking my agent."** Neither addresses that, because both
drive a stock automation build. That is a third question about the engine
underneath, and
[why an agent gets blocked](why-does-my-ai-agent-get-blocked.md) sorts the
causes by how often they are the real one.

## Three caveats in Chrome DevTools MCP's own documentation

Worth reading before you register it, and stated by the project rather than
inferred by us:

- **It exposes all browser content to the MCP client without sandboxing.** If
  the Chrome it attaches to is the one you are logged into, the assistant can
  see what you can see.
- **Performance tooling may send trace data to Google's CrUX API**, with an
  opt-out available.
- **It collects usage statistics by default**, disabled with a flag.

None of these is unusual for a debugging tool, and all three are the kind of
thing that matters more once an assistant rather than a person is on the other
end of it.

## What a browser MCP server costs you either way

Whichever you register, the tool descriptions ride in the model's context on
every turn. For calibration, measured on our own server by reading its source
on 2026-09-10: **24 tools, 14,064 characters of description, about 3,500 tokens
per turn.** Register two browser servers side by side and you are paying that
twice, on every turn, plus giving the model overlapping verbs to choose between.

That is the argument against "install both and see": pick the one that matches
the question you have this week, and keep the other unregistered until it is
the question.

## Short answers to the questions that lead here

**Is Chrome DevTools MCP better than Playwright MCP?** Different jobs. DevTools
MCP inspects a running Chrome; Playwright MCP drives a page across four engines.

**Does Chrome DevTools MCP work with Firefox?** No. Chrome and Chrome for
Testing only; other Chromium browsers may work and are not guaranteed.

**Can I use both?** Yes, and it costs context twice and makes the model's choice
harder. Prefer one per task.

**Which one for performance debugging?** Chrome DevTools MCP, without
competition - traces and insights are the thing it was built for.

**Which one for automating a flow?** Playwright MCP, and if the flow is stable
and repeated, neither: write it as a script.

**Do either of them avoid bot detection?** No. Both drive a stock automation
build, and that is a separate layer from the MCP surface.

**See also:** [Playwright MCP vs the Playwright CLI](playwright-mcp-vs-cli.md),
[choosing an MCP server for browser automation](best-mcp-server-for-browser-automation.md),
and [the MCP server](mcp-server.md) for this project's own configuration.

## Sources

- [ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp), retrieved 2026-09-10: stars, licence, browser support, capabilities, and the three caveats quoted above.
- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10: stars, licence, browser options and the accessibility-tree design.
- This project's own MCP server source, read 2026-09-10, for the tool-count and description-size figures.

---

*Written while maintaining a third browser MCP server. It is not the
recommendation for either job on this page: for debugging your own site
DevTools MCP wins outright, and for driving a flow across engines Playwright
MCP is the default.*
