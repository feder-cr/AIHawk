---
title: "Open-source computer-use agents"
description: "The open-source agents that see pixels and click coordinates - UI-TARS, Cua, Agent S, self-operating computer - and how the category differs from browser agents."
parent: "Alternatives and Comparisons"
nav_order: 8
---


# Open-source computer-use agents

A computer-use agent looks at a screenshot and clicks coordinates. That single design
choice separates it from the browser agents on
[the sibling page](ai-browser-agent-open-source.md): a browser agent reads page
structure and acts on named elements, a computer-use agent sees exactly what a person
sees, pixels, and acts exactly where a person acts, at a point on the screen. This
page maps the open-source projects in the screenshot-and-click category, verified
against their own repositories on 2026-09-03, and is honest about when the category
is the right one, which is less often than the demos suggest.

Disclosure, as on every comparison page here: this is invisible_playwright_mcp's wiki, and invisible_playwright_mcp is a
browser agent, not a computer-use agent. The category difference below is real and
cuts both ways.

## The category difference, honestly

A browser agent gets a privileged view: the DOM, the accessibility tree, element
roles and labels. When it clicks "Submit", it clicks the element called Submit, at
whatever pixel that element happens to occupy. A computer-use agent gets an image.
It must find the button in the image, decide the button's coordinates, and issue a
click at those coordinates, a step the field calls grounding, and grounding is where
these agents fail: the model knows it wants the search box and clicks forty pixels
left of it.

What the pixel view buys is generality. A computer-use agent can drive a desktop
application, a settings dialog, a virtual machine console, a canvas-rendered app
with no DOM to read, or three applications in one task. A browser agent can drive
none of those. What the pixel view costs:

- **Tokens.** Screenshots are large model inputs, and every loop step sends a new
  one. The same task costs more, per step and in step count.
- **Precision.** Grounding errors have no equivalent in a browser agent; a DOM click
  either finds the element or fails loudly. A coordinate click on the wrong pixel
  succeeds silently on the wrong thing.
- **Blast radius.** An agent with mouse and keyboard on your actual desktop can act
  outside the task. Most serious projects in the category run in a sandbox or a VM
  for exactly this reason.

If the task lives entirely inside web pages, the structural view usually wins. If it
touches anything outside a browser, only this category can do it at all.

## The projects

### UI-TARS Desktop / Agent TARS (ByteDance)

38.8k stars, TypeScript, Apache-2.0. Two things in one repository: UI-TARS Desktop,
a native GUI-agent application for your own computer, and Agent TARS, a multimodal
agent stack with a CLI and web UI. The distinctive part is the model: the stack is
driven by ByteDance's own UI-TARS vision-language models, built for GUI grounding,
with the research paper published (arXiv:2501.12326). Agent TARS also documents a
hybrid browser mode that mixes the GUI (pixel) approach with DOM reading, which is
the clearest sign in the whole category that pure pixels are not always enough.

### Cua (trycua)

22.1k stars, Python, MIT. Cua is the infrastructure answer: sandboxed computer-use
environments across macOS, Windows, Linux and Android, built on VMs rather than
containers, with agents perceiving through screenshots and acting through mouse,
keyboard and touch at pixel coordinates. It aims at running fleets of sandboxes for
training, evaluation and data generation as much as at single-agent use. Pick it
when the question is "where do I safely run a computer-use agent" rather than
"which agent".

### Agent S (Simular)

12.2k stars, Python, Apache-2.0. A research-driven framework that takes screenshots
and acts through pyautogui on Linux, macOS and Windows, using grounding models
(UI-TARS among them) for locating elements. Its README reports Agent S3 at 72.6% on
the OSWorld benchmark, which it states surpasses the roughly 72% human level, plus
56.6% on WindowsAgentArena and 71.6% on AndroidWorld. Benchmark numbers from a
project's own README deserve the usual discount, but OSWorld is a real benchmark
and the trajectory of these numbers over two years is the honest signal: the
category has moved from demo to competent on scoped desktop tasks.

### self-operating-computer (OthersideAI)

10.3k stars, Python, MIT. The early, minimal take on the idea and still a good way
to understand it: screenshot in, mouse and keyboard out, with the same interface a
person has. It supports multiple vision models including local ones through Ollama,
and adds OCR and Set-of-Mark prompting modes to help the grounding problem. Simpler
and less capable than the entries above, and the code is small enough to read in a
sitting, which is worth something.

### OpenHands, and why it is only adjacent

86.1k stars, MIT, the largest project anywhere near this page, listed here because
people search for it in this category. Its repository positions it as a self-hosted
control center for coding agents and automations, running agents like its own,
Claude Code or Codex against development tasks. Its agents work in sandboxed
environments, but the product is code-and-terminal shaped, not
screenshot-and-click shaped. If your task is "operate this GUI", it is the wrong
shelf; if your task is "build and fix software", it is a strong one.

## The table

| Project | Stars (2026-09-03) | Language | License | Sees | Acts |
|---|---|---|---|---|---|
| UI-TARS Desktop / Agent TARS | 38.8k | TypeScript | Apache-2.0 | screenshots (hybrid DOM mode in Agent TARS) | mouse and keyboard, own VLM |
| Cua | 22.1k | Python | MIT | screenshots in sandboxed VMs | pixel-coordinate input, cross-OS |
| Agent S | 12.2k | Python | Apache-2.0 | screenshots plus grounding models | pyautogui |
| self-operating-computer | 10.3k | Python | MIT | screenshots, optional OCR / Set-of-Mark | mouse and keyboard |
| OpenHands (adjacent) | 86.1k | TypeScript, Python | MIT | code, terminals, sandboxes | developer tooling, not GUI clicks |

## Choosing between the two categories

The decision is about the task surface, not the project quality.

- **Everything happens in web pages:** use a browser agent. The structured view is
  more precise, cheaper per step, and its failures are diagnosable. The options are
  on [the browser-agent page](ai-browser-agent-open-source.md); invisible_playwright_mcp is one of
  them, and that sentence carries this wiki's standing disclosure.
- **The task touches desktop applications, or a UI with no readable structure:**
  computer-use is the only category that reaches it. Take the sandbox seriously.
- **Mixed:** the field's own direction is instructive. Agent TARS ships a hybrid
  GUI-plus-DOM browser mode, and browser agents like browser-use attach screenshots
  next to the DOM. Both categories are converging on "structure where it exists,
  pixels where it does not".

One thing the pixel view does not buy, because the question comes up: it does not
make an agent look human to a website. Detection systems read the browser
fingerprint, the network, the volume and the pacing, and a computer-use agent
driving a stock browser through a VM usually looks less normal on the first two, not
more. That reasoning is laid out in
[why agents get blocked](why-does-my-ai-agent-get-blocked.md) and, for the specific
case people search for, in
[Claude computer use detected as a bot](claude-computer-use-detected-as-bot.md).

## Short answers to the questions that lead here

**What is a computer-use agent?** An agent that perceives the screen as an image and
acts by moving the mouse and typing at coordinates, the way a person does, rather
than reading page structure the way a browser agent does.

**Which open-source computer-use agent is the most capable right now?** By its own
published benchmarks, Agent S3 leads on OSWorld at 72.6%; ByteDance's UI-TARS stack
is the largest by stars and ships its own grounding models. Both readings are from
the projects' repositories on 2026-09-03, not independent evaluation.

**Can a computer-use agent browse the web?** Yes, by driving a browser as pixels,
and for web-only tasks that is usually the worse tool: more tokens, weaker
targeting, silent misclicks. Use it for the web only when the page offers no usable
structure.

**Do these run locally?** Agent S, self-operating-computer and the TARS desktop app
run on your machine; Cua exists precisely to give the agent a VM instead of your
machine. Local model support varies; self-operating-computer documents Ollama.

**Is OpenAI Operator part of this category?** Operator-style products are hosted
computer-use agents. This page covers open-source ones; for the hosted comparison
see [OpenAI Operator vs Claude computer use](openai-operator-vs-claude-computer-use.md)
and [open-source Operator-style agents](openai-operator-open-source.md).

**Is invisible_playwright_mcp a computer-use agent?** No. It is a browser agent: it reads page
structure through MCP tools and drives a patched Firefox. If your task leaves the
browser, use one of the projects on this page instead.

## Sources

All retrieved 2026-09-03, from each project's own repository.

- [bytedance/UI-TARS-desktop](https://github.com/bytedance/UI-TARS-desktop)
- [trycua/cua](https://github.com/trycua/cua)
- [simular-ai/Agent-S](https://github.com/simular-ai/Agent-S), including its
  self-reported OSWorld, WindowsAgentArena and AndroidWorld figures.
- [OthersideAI/self-operating-computer](https://github.com/OthersideAI/self-operating-computer)
- [All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands)

**See also:** [open-source AI browser agents](ai-browser-agent-open-source.md),
[what is an AI web agent?](ai-web-agent-explained.md), and
[OpenAI Operator vs Claude computer use](openai-operator-vs-claude-computer-use.md).

---

*From the [invisible_playwright_mcp](https://github.com/feder-cr/invisible_playwright_mcp) wiki. invisible_playwright_mcp sits in the
other category, the browser agents, which is exactly why this page spends its words
on when pixels beat structure and not the reverse.*
