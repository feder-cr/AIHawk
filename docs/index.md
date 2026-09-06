---
title: "Home"
nav_order: 1
---

# AIHawk Wiki

AIHawk is an open-source AI browser agent: a web browsing agent with a real browser. You say what you want in plain language, and it browses, clicks, types and reads the actual web to get it done. This wiki is the reading room
around it - what an AI web agent is, how the tools in this space compare,
what to do when an agent gets blocked, and how to put an agent to work.

The [README](https://github.com/feder-cr/AIHawk#readme) is the fastest way to
run AIHawk. The pages here are for the questions that come before and after:
which tool fits, why something failed, and what is actually happening
underneath. Every page on this wiki is one link away from this one.

## [Alternatives and Comparisons](guides-alternatives-and-comparisons.md)

The AI browser-agent landscape: OpenAI Operator and what replaced it,
browser-use, computer-use agents, and how the open-source options differ.

- [What is an AI web agent?](ai-web-agent-explained.md)
- [Choosing an AI browser agent](best-ai-browser-agent.md)
- [Open-source AI browser agents](ai-browser-agent-open-source.md)
- [Open-source computer-use agents](computer-use-agent-open-source.md)
- [AI browser vs AI browser agent: which one do you want?](ai-browser-vs-ai-browser-agent.md)
- [AI browser agents vs traditional scraping](ai-browser-agents-vs-traditional-scraping.md)
- [Is OpenAI Operator still available?](is-openai-operator-still-available.md)
- [OpenAI Operator alternatives](openai-operator-alternatives.md)
- [Open-source Operator-style agents](openai-operator-open-source.md)
- [OpenAI Operator vs Claude computer use](openai-operator-vs-claude-computer-use.md)
- [Gemini computer use vs Claude computer use](gemini-computer-use-vs-claude-computer-use.md)
- [Project Mariner is gone: what replaced it](project-mariner-is-gone.md)
- [browser-use alternatives](browser-use-alternatives.md)
- [Stagehand vs browser-use](stagehand-vs-browser-use.md)
- [Skyvern alternatives](skyvern-alternatives.md)
- [Manus alternatives](manus-alternatives.md)
- [Firecrawl vs an AI browser agent](firecrawl-vs-ai-browser-agents.md)
- [Browserbase alternatives](browserbase-alternatives.md)
- [Cloud browser infrastructure for AI agents, explained](cloud-browser-infrastructure-for-ai-agents.md)
- [AI browser agent vs RPA: which one fits the job](ai-browser-agent-vs-rpa.md)
- [AI browser agent vs n8n, Zapier and Make](ai-browser-agent-vs-no-code-automation.md)
- [Vercel agent-browser alternatives, compared honestly](agent-browser-alternatives.md)
- [AIHawk, reviewed honestly by its own wiki](aihawk-review.md)

## [When the Agent Gets Blocked](guides-when-the-agent-gets-blocked.md)

Challenge pages, rate limits, timing tells, and which of those the browser
can fix versus which are yours.

- [Why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md)
- [The timing signal AI agents give off](ai-agent-timing-signal.md)
- [Agent retry loops trip rate limits, not fingerprints](agent-retry-loops-rate-limits.md)
- [Claude computer use detected as a bot](claude-computer-use-detected-as-bot.md)
- [browser-use getting blocked: what you can and cannot change](browser-use-getting-blocked.md)

## [Using the Agent](guides-using-the-agent.md)

Task-shaped guides for putting an AI agent to work on real websites.

- [Getting an AI agent to fill out forms](ai-agent-fill-out-forms.md)
- [Extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md)
- [Getting website data into Google Sheets with an AI agent](website-data-to-google-sheets-ai-agent.md)
- [Monitoring a page for changes with an AI agent](how-to-monitor-a-page-with-an-ai-agent.md)
- [AI agents for web research](ai-agent-web-research.md)
- [Using an AI agent to download invoices from portals](ai-agent-download-invoices.md)
- [Using an AI agent to hunt for apartments](ai-apartment-hunting.md)
- [Using an AI agent to test your own website](ai-agent-to-test-website.md)
- [Posting to social media with an AI agent](posting-to-social-media-with-an-ai-agent.md)
- [Posting to X with an AI agent](ai-agent-post-to-x.md)
- [Posting to Facebook with an AI agent](post-to-facebook-with-an-ai-agent.md)
- [Posting to Instagram with an AI agent](post-to-instagram-with-an-ai-agent.md)
- [Automating LinkedIn posts: read this first](automating-linkedin-posts-read-this-first.md)
- [Appointment bots: what they are and what an agent can legitimately do](appointment-bots-explained.md)
- [How to write a task an AI browser agent can follow](writing-tasks-for-an-ai-browser-agent.md)
- [Track prices across sites with an AI agent](ai-agent-price-tracking.md)
- [Build a lead list with an AI browser agent](ai-agent-lead-list.md)
- [Move data between two web apps with an AI agent](move-data-between-web-apps-with-an-ai-agent.md)
- [Run an AI browser agent on a schedule](run-ai-agent-on-a-schedule.md)
- [AI browser agent with a local LLM: what changes](ai-browser-agent-local-llm.md)
- [Should you log your AI agent into your accounts?](should-you-log-your-ai-agent-into-accounts.md)
- [Which model to use with AIHawk](which-model-to-use-with-aihawk.md)
- [Browser problem or model problem?](browser-problem-or-model-problem.md)
- [Running AIHawk's browser from Claude Code](running-aihawk-with-claude-code.md)
- [Running AIHawk's browser from Claude Desktop](running-aihawk-with-claude-desktop.md)
- [Running AIHawk's browser from Cursor](running-aihawk-with-cursor.md)
- [Running AIHawk's browser from Cline](running-aihawk-with-cline.md)
- [The MCP server: config blocks, settings, tools](mcp-server.md)
- [How the tools are shaped, and why](mcp-tool-design.md)

## The layer underneath

AIHawk drives a Firefox patched at the C++ level so the browser itself looks
and behaves like a normal desktop browser. That engine has its own
documentation, maintained with the same care as this wiki: the
[invisible_playwright wiki](https://github.com/feder-cr/invisible_playwright/wiki)
covers browser fingerprinting, bot-detection vendors, network and proxy
mechanics, and the automation layer in depth. Pages here link into it wherever
the mechanism matters.
