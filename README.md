<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/feder-cr/AIHawk/main/assets/aihawk-logo-dark.png">
  <img alt="AIHawk" src="https://raw.githubusercontent.com/feder-cr/AIHawk/main/assets/aihawk-logo-light.png" width="380">
</picture>

**AIHawk is an open-source AI browser agent: a web browsing agent with a real browser. You say what you want in plain language, and it browses, clicks, types and reads the actual web to get it done.**

<sub>FEATURED IN</sub><br>
[**Business Insider**](https://www.businessinsider.com/aihawk-applies-jobs-for-you-linkedin-risks-inaccuracies-mistakes-2024-11) ·
[**TechCrunch**](https://techcrunch.com/2024/10/10/a-reporter-used-ai-to-apply-to-2843-jobs/) ·
[**Semafor**](https://www.semafor.com/article/09/12/2024/linkedins-have-nots-and-have-bots) ·
[**Wired**](https://www.wired.it/article/aihawk-come-automatizzare-ricerca-lavoro/) ·
[**The Verge**](https://www.theverge.com/2024/10/10/24266898/ai-is-enabling-job-seekers-to-think-like-spammers) ·
[**Vanity Fair**](https://www.vanityfair.it/article/intelligenza-artificiale-candidature-di-lavoro) ·
[**404 Media**](https://www.404media.co/i-applied-to-2-843-roles-the-rise-of-ai-powered-job-application-bots/)

</div>

---

## Two ways to use this browser agent

The only question is where the model comes from. If you already use Claude
Code, Codex or Gemini CLI, take the first. If you do not, take the second.
Both need Python 3.11 or newer.

### 1. From your assistant, over MCP

```bash
pip install aihawk
invisible-playwright fetch
```

Then tell your assistant it exists.

**Claude Code:**

```bash
claude mcp add --scope user stealth -- invisible-playwright-mcp
```

**Codex:**

```bash
codex mcp add stealth -- invisible-playwright-mcp
```

**Gemini CLI:**

```bash
gemini mcp add --scope user stealth invisible-playwright-mcp
```

### 2. Standalone: the web UI

We bring the interface, you bring an [OpenRouter](https://openrouter.ai) key.
Chat on the left, the live browser on the right.

```bash
pip install aihawk
invisible-playwright fetch
aihawk ui --openrouter-key sk-or-...
```

Then open **http://127.0.0.1:8765** and type the same thing.

---

## What to ask a web browsing agent

Anything that needs real web automation: a browser rather than an API, and a
person's judgement about what is on the page.

> Go to `<paste the URL>`. One way, Milan to Lisbon, economy, one checked bag,
> one adult. Check every date from the 12th to the 16th of next month, one at a
> time, and read the cheapest fare for each day. The date field is a calendar
> widget, so click the days rather than typing them. If a date has no
> availability, say so. Do not guess a number.

It drives the page the way a person would: the pointer moves, keys are pressed,
and it refuses to set a form field from JavaScript even when that would be
quicker, because a page can tell the difference.

## Options: proxy, profile, seed

- **`--openrouter-key`** Your key, or the `OPENROUTER_API_KEY` variable.
- **`--model`** An OpenRouter model id, or `AIHAWK_MODEL`. Defaults to `z-ai/glm-4.6`.
- **`--proxy`** Optional. `http://user:pass@proxy.example.com:8080` or
  `socks5://proxy.example.com:1080`. Host and port are both required. The
  timezone, locale and egress follow it.
- **`--binary`** An engine binary you already have. It must be the build the seal
  pins, or startup refuses: this skips the download, not the version check.
- **`--seed`** An integer. Same seed, same browser identity, every run.
- **`--profile-dir`** A directory to keep the profile in, so logins and cookies
  survive restarts.
- **`--headed`** Show the browser window. The interface shows you the page anyway.
- **`--host`, `--port`** `127.0.0.1` and `8765`. Changing the host
  exposes an interface that has no authentication.

### A `.env` beside the command

Rather than retyping the key and the binary path, put them in a `.env` in the
directory you run from:

```
OPENROUTER_API_KEY=sk-or-...
STEALTHFOX_BINARY=/path/to/firefox
```

It is read at startup, and on the way in it **never overrides** something
already set, so the order is `--flag` > the environment > `.env` > the default.
Only the directory you are in is read - there is no search upwards, so running
from a subfolder cannot silently pick up a different key. The startup line names
the variables it applied and never prints their values.

Passing `--openrouter-key` puts the key in your shell history, and on Linux in
the process list. `OPENROUTER_API_KEY` in the environment or in a `.env` avoids
both.

## The wiki: AI browser-agent guides

The reading room around the agent lives in the
[wiki](https://github.com/feder-cr/AIHawk/wiki): the
[AI browser-agent landscape: browser-use, Operator-style and
computer-use agents compared](https://github.com/feder-cr/AIHawk/wiki/guides-alternatives-and-comparisons),
[what to check when an agent gets blocked](https://github.com/feder-cr/AIHawk/wiki/why-does-my-ai-agent-get-blocked),
and [what happened to OpenAI Operator](https://github.com/feder-cr/AIHawk/wiki/is-openai-operator-still-available),
among others. Worked examples, transcripts and their outputs live in
[articles/](https://github.com/feder-cr/AIHawk/tree/main/articles).

## The rest of the family: browser MCP server, engine, core

- **[invisible-playwright-mcp](https://github.com/feder-cr/invisible-playwright-mcp)**
  The MCP server from option 1. Tools only, no interface.
- **[invisible_playwright](https://github.com/feder-cr/invisible_playwright)**
  The engine, as a Python library, for writing code instead of prompts. The API
  is Playwright's.
- **[invisible_core](https://github.com/feder-cr/invisible_core)**
  Seed to fingerprint to preferences, proxy and geolocation.

## Using it responsibly

This automates a browser under your control. Read the terms of the sites you
point it at, respect their rate limits, and do not submit anything a human has
not read.

## License

[MIT](https://github.com/feder-cr/AIHawk/blob/main/LICENSE). Everything
distributed before 2 September 2026 was released under AGPL-3.0 and stays under
it.
