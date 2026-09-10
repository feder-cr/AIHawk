---
title: "Playwright MCP with a proxy, and the three leaks it leaves"
description: "The config is one line. DNS, WebRTC and a timezone that disagrees with the exit are the three things that routing HTTP through a proxy does not close."
parent: "Using the Agent"
nav_order: 34
---

# Playwright MCP with a proxy

Microsoft's server takes `--proxy-server`, the same shape Chromium has always
used, plus `--proxy-bypass` for hosts that should go direct. That is the
configuration part and it is one line. The rest of this page is the part that
decides whether it helps.

## Why the proxy is often the real fix

When an agent starts failing on a site that worked from your laptop, the change
is usually not the browser. It is where the request came from. A laptop on a
domestic connection and a container on a cloud host present two very different
network identities, and the second one is pre-judged before a single byte of
your page interaction happens.

That is worth knowing before you spend a day switching servers.
[Why an agent gets blocked](why-does-my-ai-agent-get-blocked.md) works through
attributing the failure properly, and the network is the first place to look,
not the last.

## The three leaks a proxy does not close by itself

Routing HTTP through a proxy is not the same as being at the other end of it.
Three specific things stay behind unless you handle them.

**DNS.** If names are resolved locally and only the connection is proxied, the
resolution path still points home. It is invisible in a browser and obvious to
anything watching resolvers. Whether it leaks depends on the proxy scheme: a
SOCKS5 proxy can be told to resolve remotely, an HTTP proxy resolves for you by
design, and a local resolver in front of either undoes both.

**WebRTC.** The classic one. A page can ask the browser to enumerate candidate
addresses, and unless the browser is configured otherwise it will happily report
the machine's real ones. The engine wiki has the mechanism and the test:
[WebRTC leaks with a proxy](https://github.com/feder-cr/invisible_playwright/wiki/webrtc-leak-proxy).

**Timezone and locale.** The one people forget, and the one that is trivially
checkable from JavaScript. If the exit says Frankfurt and
`Intl.DateTimeFormat().resolvedOptions().timeZone` says your own city, that is a
contradiction no amount of proxying fixes. Set it to match the exit, or accept
that you are self-reporting a mismatch.

None of these is exotic. All three are readable in a few lines from a page, and
the engine wiki documents
[how to check whether a proxy leaks your real IP](https://github.com/feder-cr/invisible_playwright/wiki/how-to-check-proxy-ip-leak)
so you can test rather than assume.

## Choosing what to route through

**Do not proxy everything reflexively.** A proxied session is slower, and if the
proxy is shared its reputation is not yours to control: you can move from a
neutral address to one that a hundred other people have already spent. For
sites that were never a problem, the direct path is fine, which is what
`--proxy-bypass` exists for.

**Residential and datacenter are different products.** A datacenter address is
fast, stable and identifiable as a datacenter. A residential one is neither fast
nor stable and is not pre-judged the same way. Which you want depends on whether
the site is judging the address at all, and that is testable.

**Rotation is not free.** An address that changes mid-session is a session that
looks like it moved city between two clicks. If you rotate, rotate between
sessions, not inside one.

## In this project

[AIHawk](https://github.com/feder-cr/AIHawk)'s server takes the proxy per
session rather than per process, so two sessions in one server can sit behind
two different exits. It is set at `session_start`, alongside the seed. The
timezone can follow the exit rather than the host, which closes the third leak
above by construction instead of by remembering.

That is a convenience, not an advantage over anything: the same result is
reachable with any server plus care. [The MCP server](mcp-server.md) has the
settings.

## Short answers to the questions that lead here

**How do I set a proxy in Playwright MCP?** `--proxy-server` on the server
command line, with `--proxy-bypass` for hosts that should go direct.

**Can I use a different proxy per session?** Not with a single process and a
command-line flag. Either run one server per proxy, or use a server that takes
the proxy per session.

**Does a proxy hide that I am automating?** No. It changes where the request
comes from. Everything a page can read about the browser is unchanged, and so is
your pacing.

**Will a proxy fix a challenge page?** Sometimes, when the address was the
reason. Often not.
[Cloudflare and Playwright MCP](cloudflare-and-playwright-mcp.md) covers what a
challenge is actually reading.

**Do I need a residential proxy?** Only if the site is judging the address type.
Test with the cheap option first; a lot of failures attributed to the address
are pacing.

**See also:** [Playwright MCP best practices](playwright-mcp-best-practices.md),
[when the agent gets blocked](guides-when-the-agent-gets-blocked.md), and
[the MCP server](mcp-server.md).

## Sources

- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp), retrieved 2026-09-10, for `--proxy-server` and `--proxy-bypass`.
- The engine wiki's own measurements on [WebRTC leaks](https://github.com/feder-cr/invisible_playwright/wiki/webrtc-leak-proxy) and [checking for IP leaks](https://github.com/feder-cr/invisible_playwright/wiki/how-to-check-proxy-ip-leak).

---

*Written while maintaining a server that takes the proxy per session. The page
says that is a convenience rather than an advantage, because the same result is
reachable with the tool most readers already have.*
