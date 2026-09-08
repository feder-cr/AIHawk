---
title: "The MCP server"
description: "The stealth Firefox as an MCP server, shipped inside aihawk: the config block for every client that takes a file, the STEALTHFOX_* settings, and the tools with what each one returns."
parent: "Using the Agent"
nav_order: 29
---
# The MCP server

A stealth Firefox as an [MCP](https://modelcontextprotocol.io) server. Add it to
Claude Code, Claude Desktop, Codex, Cursor or any other MCP client, and your
assistant gets a real browser: tabs, navigation, reading, clicking, typing,
dropdowns, keys, screenshots, a live view of the window, and a JavaScript
reader, on a Firefox whose fingerprint is set inside the engine rather than
bolted onto the page.

The engine is [`invisible-playwright`](https://github.com/feder-cr/invisible_playwright),
a Firefox patched at the C++ source. The server ships inside the `aihawk`
package and is what `aihawk` runs with no subcommand: `uvx aihawk` is what a
client registers, `python -m aihawk` is what the interface spawns. Every tool
below is a thin wrapper over the engine, and the interface (`aihawk ui`) is a
client of it like any other.

**How to install this, and the two ways to use it, are in
[AIHawk's README](https://github.com/feder-cr/AIHawk#readme).** This page keeps
what the server itself owns: the config block for clients that take a file, the
settings, and the tools.

## Adding it to your client

Claude Code, Codex and Gemini CLI have a command for it, and the command is in
AIHawk's README. The rest take a config file, and the file is not the same
everywhere: **three different top-level keys, and one of them is not even
JSON.** Find yours below. The block only tells the client how to start the
server; installing `uv` and fetching the engine come first, as AIHawk's README
shows.

### If your client takes a config file

**Most use a top-level `mcpServers`** - Claude Desktop, Cursor, Windsurf, Cline:

```json
{
  "mcpServers": {
    "stealth": {
      "command": "uvx",
      "args": ["aihawk"]
    }
  }
}
```

| Client | File |
|---|---|
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |
| Cursor | `.cursor/mcp.json` in the project, or `~/.cursor/mcp.json` for every project |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| Cline | `~/.cline/data/settings/cline_mcp_settings.json`, or the **Configure MCP Servers** button in its MCP panel, which opens whichever file your version uses |

**Zed calls the key `context_servers`**, not `mcpServers`, in
`~/.config/zed/settings.json` (`%APPDATA%\Zed\settings.json` on Windows):

```json
{
  "context_servers": {
    "stealth": {
      "command": "uvx",
      "args": ["aihawk"]
    }
  }
}
```

**VS Code calls it `servers`**, in `.vscode/mcp.json` for a workspace:

```json
{
  "servers": {
    "stealth": {
      "type": "stdio",
      "command": "uvx",
      "args": ["aihawk"]
    }
  }
}
```

**Codex uses TOML**, in `~/.codex/config.toml`:

```toml
[mcp_servers.stealth]
command = "uvx"
args = ["aihawk"]
```

**Continue** uses YAML with its own block format, which changed recently enough
that we would rather point you at
[their documentation](https://docs.continue.dev/customize/deep-dives/mcp) than
print a block here that may already be stale.

### Where a proxy and the other settings go

Everything in **Settings** below goes under `env` on the server entry, in
whatever shape your client uses:

```json
{
  "mcpServers": {
    "stealth": {
      "command": "uvx",
      "args": ["aihawk"],
      "env": {
        "STEALTHFOX_PROXY": "http://user:pass@proxy.example.com:8080",
        "STEALTHFOX_SEED": "4242"
      }
    }
  }
}
```

In Codex's TOML that is a `[mcp_servers.stealth.env]` table; on the command line,
Claude Code and Codex take `-e KEY=value` and `--env KEY=value`.

⛔ **"Added" is not "connected".** Every one of these writes a config entry
without running anything, so a typo, a missing `uv`, or the first-run browser
download all surface later as a server that will not start. Check before you
trust it: `claude mcp list`, `codex mcp list`, or your client's MCP panel.

## Settings

Environment variables, all optional. A proxy is the one worth adding: without it
the exit IP, timezone and locale are your own machine's, which is a real gap
between what the browser says it is and where it appears to be.

| Variable | Meaning |
|---|---|
| `STEALTHFOX_PROXY` | Proxy URL, e.g. `http://user:pass@proxy.example.com:8080` or `socks5://proxy.example.com:1080`. Host and port are both required. Bring your own. With it set, the session's timezone, locale and egress are derived from the proxy. |
| `STEALTHFOX_NO_PROXY` | `1` to go out from this machine's own address even when `STEALTHFOX_PROXY` is set. |
| `STEALTHFOX_SEED` | Integer seed for a deterministic fingerprint (same seed, same identity). A profile's own seed wins over this one. |
| `STEALTHFOX_PROFILE_DIR` | A directory for a persistent profile, so logins survive across runs. |
| `STEALTHFOX_BINARY` | Path to an engine binary you already have. It must be the build the packaged seal pins, or startup refuses. |
| `STEALTHFOX_HEADLESS` | `0` to run headed; headless by default. |
| `STEALTHFOX_MCP_TRANSPORT` | `http` to serve over streamable HTTP instead of stdio. Default is stdio, which is what MCP clients expect. |
| `STEALTHFOX_MCP_HOST` | Bind address for the HTTP transport. Default `127.0.0.1`. |
| `STEALTHFOX_MCP_PORT` | Port for the HTTP transport. Default `8765`, which is also the AIHawk interface's default: change one of the two if you run both. |
| `AIHAWK_HOME` | Where saved sessions are kept. Defaults to `%APPDATA%/aihawk` on Windows, `~/Library/Application Support/aihawk` on macOS and `$XDG_DATA_HOME/aihawk` on Linux. Set it to put them on another disk. |

Anything a tool call says wins over these. `session_start` can pick another
seed, another exit or another profile for one session; the variables are what a
session gets when nobody says anything.

## Tools

`session_list`, `session_forget`, `session_status`, `session_start`,
`session_new_page`, `session_list_pages`,
`session_select_page`, `session_close_page`, `browser_open`, `browser_close`,
`browser_list`, `browser_focus`, `browser_navigate`,
`browser_read_text`, `browser_snapshot`, `browser_read_html`,
`browser_take_screenshot`, `browser_watch`, `browser_click`, `browser_click_at`,
`browser_type`, `browser_select_option`, `browser_press_key`, `browser_evaluate`.

Tool names mirror the Microsoft Playwright MCP, so prompts written for it work
here too. Three groups: who is browsing and which tab, reading the page, and
acting on it.

**Every tool below also takes `session_id` and `browser_id`, both optional, and
neither appears in the tables because the answer is the same for all of them.**
Send neither and you get the default browser of the default session, which is
what a client that never mentions either has always got and always will. Name
them when a session holds more than one browser and the command has to reach a
particular one.

The two are not the same thing. A **session** is the piece of work: it owns a
conversation and the browsers that belong to it. A **browser** is one running
engine inside that session, with its own tabs, its own cookies and its own
identity, and it does not share any of that with its neighbours. Tabs live
inside a browser, which is why the tab tools take a page id and not a third
address.

### Session and tabs

| Tool | Arguments | What it does |
|---|---|---|
| `browser_open` | `browser_id`, `seed`, `proxy`, `profile`, all optional | Opens another browser in this session and makes it the one unaddressed commands go to. Each browser has its own tabs, cookies and identity and shares none of them. Refuses past eight, saying what eight cost when it was measured. |
| `browser_close` | `browser_id` optional | Closes one browser and frees what it held. Its tabs go with it; the other browsers and the conversation do not. Forgets who it was, so the same name later is a new stranger rather than that person resumed. |
| `browser_list` | `session_id` optional | Which browsers this session holds, where each one is, and which one commands go to. Starts nothing, so asking is free. |
| `browser_focus` | `browser_id` | Chooses which browser the commands that name none land on. Naming a browser still reaches it whatever the focus is. |
| `session_list` | none | Every saved session and what each one holds. Sessions survive the server, so this is how you find the one you were in. Starts nothing. |
| `session_forget` | `session_id` | Delete a saved session: its browsers are closed and it stops being listed. Not the same as closing browsers, which frees the engines and keeps the session. |
| `session_status` | none | Who is browsing right now: the seed, the exit, the profile and the open tabs. Starts nothing; if no browser is up it says so. |
| `session_start` | `seed`, `proxy`, `profile`, all optional | Close whatever is open and start a browser as a particular person. Returns a sentence describing the session it actually started. |
| `session_new_page` | none | Open a tab, make it the active one, return its id. |
| `session_list_pages` | none | Every open tab: id, title, url, and which one is active. |
| `session_select_page` | `page_id` | Make a tab the active one. Every `browser_*` tool acts on the active tab. |
| `session_close_page` | `page_id`, optional | Close a tab, or the active one when the id is left out. |

You can ignore `session_start` entirely: the first tool that needs a page starts
a session on its own, as a different stranger every time, which is the right
default. A session holds up to eight browsers, so two accounts CAN be live at
the same time: open a second browser with `browser_open` and address commands to
whichever one you mean. `session_start` still replaces the browser you are in
rather than adding one, which is the difference between the two.

**The interface's session column lists these same sessions.** A conversation
in `aihawk ui` and a session here are one thing with one id: the chat named
`lavoro` drives the browsers of session `lavoro` and no others, and deleting it
there closes them. A client that names no session and a page that names none
both land on `default`, which is why they share a browser.

Sessions are written down as soon as one holds a browser, and what is written is
the DECLARATION - which browsers a session has, who each one is, and where its
tabs were pointing - not eight running engines. Reopening one gives the
identities back immediately; each engine starts when a command is aimed at it,
as the right person. Cookies and logins come back only where a browser had a
`profile`, which is the mechanism that already exists for that.

- **`seed`** is the identity. Same seed, same fingerprint, every time. Leave it
  out and one is drawn; the answer says which, so a session worth repeating can
  be repeated.
- **`profile`** is a directory that keeps cookies and logins between sessions.
  **A profile also owns its seed**: the first session on a new one stores the
  identity inside it and every later session reuses it, so a login never comes
  back wearing different hardware. Ask for a seed that contradicts the one a
  profile carries and you get a refusal naming both numbers, never a silent
  choice. A relative path is resolved against the server's own directory, and
  the answer reports the full path it used.
- **`proxy`** is where the traffic leaves, `http://user:pass@host:port` or
  `socks5://host:port`. Timezone, locale and geography follow it.
- Pass `""` for `profile` or `proxy` to insist on **none**, even when the
  environment sets a default. That is how you get sessions a site cannot link
  to each other.

**A profile does not own its exit the way it owns its seed.** The same login
arriving from another country is as visible as one arriving on different
hardware. You are warned when a profile's exit changes, but only when *you*
change it: a provider rotating its own addresses behind one host and port is
indistinguishable from here.

A `session_start` that fails, usually because the proxy is down, leaves nothing
running, and every later tool repeats the refusal until a `session_start` works.
It does not quietly start a browser without the exit that was asked for.

### Reading the page

| Tool | Arguments | What it returns |
|---|---|---|
| `browser_navigate` | `url`, `wait_until` | Goes to the url in the active tab, opening one if none exists. Answers with the HTTP status and the url it landed on, so a 404 or a redirect to a login wall is visible instead of reading like a normal arrival. `wait_until` is `domcontentloaded` by default, which returns as soon as the markup is parsed; `load` waits for images and stylesheets, `networkidle` for a single-page app that fetches its content after load. |
| `browser_read_text` | `selector` (default `body`), `max_chars` (default 6000) | The visible text of an element, markup gone. The cheapest way to read a page. Long text is cut at `max_chars` and the cut is marked, so text without the marker is the whole thing. |
| `browser_snapshot` | `max_chars` | Title, url, and the interactive elements that are actually visible, each with a `selector` when one can reach it and `at: [x, y]`, its centre in viewport pixels. Not the accessibility tree: a single country `<select>` would contribute about two hundred `<option>` nodes and fill the cap before the form appears. |
| `browser_read_html` | `mode`: `form` (default), `text`, `full` | The page's HTML reduced to what is worth reading: `form` keeps the interactive surface and the text explaining it, `text` the prose alone, `full` the structure with the noise removed. Not capped, on purpose: cutting markup in the middle leaves tags that mean nothing, so on a large page the answer is long. |
| `browser_take_screenshot` | none | A screenshot of the active tab, as an image. |
| `browser_watch` | none | The whole browser window as a person at the machine sees it: tab strip, address bar, page and the pointer, from a live capture the session keeps running on the active tab. |

The selectors a snapshot hands out are built to match exactly one element, and
that is the reason to pass them verbatim rather than writing your own: measured
across 958 elements on real pages, 88% could be addressed by a selector but only
48% unambiguously, and Playwright acts on the first match, so a caller aiming at
the third of five identical links would silently hit the first.

`browser_watch` is for the person watching, not for the model acting. The
pointer is drawn in the browser chrome on purpose, so that no page can see it,
which is also why no page screenshot can ever contain it. The picture is window
pixels: feed `browser_take_screenshot` to `browser_click_at`, not this. It needs
an engine from `firefox-28` on; an older engine answers with a sentence saying
so.

### Acting on the page

| Tool | Arguments | What it does |
|---|---|---|
| `browser_click` | `selector` | Clicks the first element matching a CSS selector, scrolling it into view and waiting for it to be clickable. The pointer approaches, hovers, presses and releases, the way a hand does. |
| `browser_click_at` | `x`, `y`, `hold_seconds` (default 0) | Clicks a viewport coordinate instead of a selector: moves the pointer there, presses, holds if asked, releases, and returns a screenshot taken right after. For a slider track, a canvas-drawn challenge, a precise point inside a wider element. |
| `browser_type` | `selector`, `text` | Fills a field, replacing whatever it holds. It sets the value rather than typing key by key, so per-keystroke handlers such as an autocomplete do not fire; for those, click the field and use `browser_press_key`. |
| `browser_select_option` | `selector`, `value` | Chooses an option in a `<select>`, by its visible label or by its value. |
| `browser_press_key` | `key` | Presses a key on whatever has focus: `Enter`, `Tab`, `Escape`, `ArrowDown`, `Control+a`, or a single character. |
| `browser_evaluate` | `expression` | Runs JavaScript to **read** from the page and returns the result as JSON: a computed style, a value held in a framework's state, the length of a list. |

`browser_click_at` takes coordinates relative to the **viewport**, not to the
page, so the ones in a snapshot go stale the moment anything scrolls: a click, a
keypress, a lazy image loading above the fold. Nothing raises when that happens;
the click lands on whatever is at that spot now. Take a fresh snapshot after
anything that could have moved the page, and prefer `browser_click` with an
element's `selector` whenever it has one.

`browser_evaluate` reads; it will not act. Assigning to `value`, `checked` or
`selected`, or calling `click()`, `dispatchEvent()`, `submit()` or
`requestSubmit()`, is refused, and the refusal names the tool to use instead.
Script reaches the page with no keystroke and no pointer, so the event carries
`isTrusted` false, which is the clearest signal a page can collect that nobody
is really there. Reading those properties is fine. The refusal catches the
obvious spellings, not every possible one; a script that slips past it is still
the wrong way to do the thing.

### The order to try them in

The server hands every client this ladder, because a model that cannot find a
way down it invents one:

1. **A named tool with a selector**: `browser_click`, `browser_type`,
   `browser_select_option`, `browser_press_key`. `browser_snapshot` supplies the
   selector.
2. **Coordinates**: the snapshot reports `at: [x, y]` for every element, and
   `browser_click_at` moves the pointer there. For a canvas, a slider, a map, a
   widget built out of divs.
3. **A screenshot**: `browser_take_screenshot`, then `browser_click_at` on what
   you can see. For what the snapshot does not list at all.
4. **`browser_evaluate`**, to read what none of the above can see.

Getting to the bottom of the ladder without a way to do the thing is a result
too: a task reported as impossible is worth more than one completed in a way
that gets the session blocked.

**Why each tool returns what it does**, with the measurements behind it:
[the tool design page](mcp-tool-design.md).

## More than one client on the same browser

Over stdio the browser belongs to the client that opened it. Set
`STEALTHFOX_MCP_TRANSPORT=http` and it does not: the session is owned by the
server, so a second client can attach to the browser the first one left open,
and closing a client no longer kills the browser.

```bash
STEALTHFOX_MCP_TRANSPORT=http uvx aihawk        # Linux
```
```powershell
$env:STEALTHFOX_MCP_TRANSPORT = "http"; uvx aihawk   # Windows
```

To SEE the browser rather than share it, [AIHawk](https://github.com/feder-cr/AIHawk)
shows the live page beside the conversation.

## Notes

- This is a browser, not a captcha solver. It does not solve or bypass
  challenges for you; it makes an ordinary Firefox session look like a real one.
- One browser per server process. Tabs are the way to keep several pages open;
  two identities at once need two servers.

## License

[MIT](https://github.com/feder-cr/AIHawk/blob/main/LICENSE),
the same as the engine it wraps.
