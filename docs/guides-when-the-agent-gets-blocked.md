---
title: "When the Agent Gets Blocked"
has_children: true
nav_order: 3
---

# When the Agent Gets Blocked

An AI agent that browses the web inherits every way a browser can be detected,
plus a few tells of its own: the rhythm of a think-act loop, the volume of a
retry storm, the fingerprint of the machine it runs on. These pages sort out
which is which, because the fix is different for each - and some of them are
not fixable from the agent at all.

The mechanism layer lives on the
[invisible_playwright wiki](https://github.com/feder-cr/invisible_playwright/wiki),
which documents the fingerprinting surfaces and the detection vendors in
depth. The pages here stay at the level of the agent: what happened, what to
check, in what order.

- [Why does my AI agent get blocked?](why-does-my-ai-agent-get-blocked.md)
- [The timing signal AI agents give off](ai-agent-timing-signal.md)
- [Agent retry loops trip rate limits, not fingerprints](agent-retry-loops-rate-limits.md)
- [Claude computer use detected as a bot](claude-computer-use-detected-as-bot.md)
- [browser-use getting blocked: what you can and cannot change](browser-use-getting-blocked.md)
- [Playwright MCP session getting blocked](playwright-mcp-blocked.md)
- [Playwright MCP and captchas](playwright-mcp-and-captchas.md)
- [Cloudflare and a browser MCP server](cloudflare-and-playwright-mcp.md)
- [Can an AI agent solve a captcha?](can-an-ai-agent-solve-a-captcha.md)
