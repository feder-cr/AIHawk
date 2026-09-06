# Contributing to AIHawk

Thanks for being here. This page says what this repository is, so you can tell in
one minute whether your change belongs here or in one of the packages below.

## What lives here

The `aihawk` package: the two-pane interface, the loop that turns a sentence into
browser actions, the command line around both, and, under `aihawk.mcp`, the MCP server the interface drives. If you are changing what a
person sees, or how the model decides what to do next, it is here.

What is NOT here is the browser engine. AIHawk does not drive Firefox directly - it
talks to an MCP server over MCP, using the same tools any other client
gets. That is deliberate and it is the thing to understand before changing
anything: this interface has no privileged path to the page, so a browser
capability it needs is a capability every client gets, or it does not exist.

This page said the opposite earlier on 2 September 2026, when the repository held
only documentation. The package moved in the same day.

## Where the code is

| Repository | What it holds |
|---|---|
| **this one** | the interface, the agent loop, the CLI, and the MCP server (`src/aihawk/mcp`: the tools, and nothing with a face) |
| [invisible_playwright](https://github.com/feder-cr/invisible_playwright) | the Python wrapper, the launcher, and the patched browser it pins |
| [invisible_core](https://github.com/feder-cr/invisible_core) | seed to fingerprint to preferences, proxy and geolocation |

Where things go:

- the page, the conversation, the step list, the model's behaviour: **here**
- a tool that returns the wrong thing, or a click that does not land: **the MCP server, `src/aihawk/mcp` here**
- the browser failing to start, a proxy not used, a timezone that does not match
  the exit country: **the wrapper or the core**
- a detector spotting the browser: almost always the engine, not this repository

If you are not sure, open the issue here and it will be moved.

## Development setup

```bash
git clone https://github.com/feder-cr/AIHawk.git
cd AIHawk
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[test]"
```

Python 3.11 or newer, Windows or Linux. No key is needed to work on it: `aihawk
ui` without one runs the literal-command placeholder, which drives the real
browser through the real server and is how most of this was tested.

## Running the tests

```bash
pytest                 # the default selection, no browser, seconds
pytest -m ui           # drives a REAL browser through a REAL server
pytest -m e2e tests/mcp_server   # the server's own browser tests, engine fetched on first use
```

The server's browser tests carry the `e2e` marker and run with `pytest -m e2e tests/mcp_server`, against an engine that is downloaded on first use. The `ui` tests are deselected by default because they are slow and they must run
serially: they launch a browser, and two browser benches on one machine produce
results that are noise with numbers on them. Run them one at a time, on a machine
that is not doing anything else.

They assert what happened INSIDE the page, never what a tool said about itself. A
tool that answers "clicked #go" while nothing moved is the failure they exist to
catch, so the tool's own success string is never the assertion.

## Pull requests

Fork, branch, open the pull request against `main`. There is one branch and no
release train.

Keep a pull request to one change, and say in the description what a reader would
be able to do afterwards that they could not do before. If you change what the
interface shows, include a screenshot: this project has already had the case
where five green tests passed while the pane showed a black rectangle, and the
picture was the only thing that noticed.

## Opening an issue

Use one of the [templates](https://github.com/feder-cr/AIHawk/issues/new/choose).
Before you do, search the open and closed issues.

For a bug, the two things that decide how fast it can be answered are the exact
commands you ran and what happened instead of what you expected. Include your OS
and Python version, and whether you were running `ui` or `do`.

Please do not report a security problem in a public issue. In particular, never
paste an OpenRouter key into one: if you have, rotate it before anything else.

## Tone

Questions are welcome and beginners are welcome. If something in the README was
not clear enough for you, that is worth an issue on its own, because it was
probably not clear to somebody else either.

## Licence

By contributing you agree that your contribution is licensed under the MIT
licence, which is the licence in [LICENSE](../LICENSE). Everything received
before 2 September 2026 was contributed under AGPL-3.0 and stays under it: a
licence already granted is not withdrawn by changing that file.

Participation is covered by the [Code of Conduct](CODE_OF_CONDUCT.md).
