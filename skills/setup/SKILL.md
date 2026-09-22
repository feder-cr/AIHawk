---
name: setup
description: What the invisible_playwright_mcp browser server needs on this machine - the patched Firefox it drives, which the server downloads on its own the first time it runs. Use when browser_open answers that the engine is downloading or that its download failed, or right after installing the plugin.
---

The server runs with `uvx aihawk` and needs its browser engine on this machine once, about a quarter of a gigabyte. It downloads it on its own when it starts; while that is in flight, `browser_open` answers with how far the download is instead of opening a browser, and asking again a minute later is all that is needed.

To do the download ahead of time, or again after it failed, in a terminal where the user can watch it, run the block for the user's system:

Windows, in PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uvx invisible-playwright fetch
```

Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uvx invisible-playwright fetch
```

Nothing else to configure: no account, no key. Over MCP the model is the client's own.
