---
title: "Uploading a file with an AI agent, and why this one cannot"
description: "The snapshot lists the file input, complete with a selector. Nothing can put a file into it. The measured refusal, why the listing makes it worse, and the three routes that do work."
parent: "Using the Agent"
nav_order: 73
---

# Uploading a file with an AI agent, and why this one cannot

Short answer first, because it saves an afternoon: **this browser cannot upload a
file.** There is no tool for it, and the tools that look like they might are
refused.

Measured on 2026-09-17 on a page with a single `<input type="file">`, served from
`127.0.0.1`:

```
browser_snapshot   -> {"tag": "input", "type": "file", "id": "file",
                       "selector": "#file", "at": [123, 92]}
browser_type       -> Error: Page.fill: Input of type "file" cannot be filled
browser_evaluate   -> document.getElementById("file").files.length  ->  0
page state         -> out: none
```

The input is there, the agent can see it, it has a selector and a position, and
nothing in the tool surface can put a file into it.

## The listing is the problem, not the absence

An agent handed this page will find the input in the snapshot, conclude it can be
used, try to type into it, get a refusal, and then start improvising: clicking
the input to open the file dialog, which is a native window it also cannot touch,
or setting `value` from script, which is refused for a different reason and would
not work anyway because browsers do not let script set a file input's value.

So the run does not fail cleanly at the top. It fails several steps in, having
tried three things, and the transcript reads like a page problem.

**Say it in the task.** One sentence, "you cannot upload files, stop and tell me
if a step needs one", turns a confusing five-call failure into an immediate,
accurate report. This is the same shape as every other useful instruction about
what to do when a step is impossible, covered in
[giving an AI browser agent a stopping condition](giving-an-ai-agent-a-stopping-condition.md).

## Why the file dialog is not a way round it

Clicking a file input opens the operating system's file picker. That window
belongs to the OS, not to the page, so nothing that drives a page can see or
operate it. It is not a matter of a missing selector: there is no document there.

The same is true of a drag-and-drop zone that ultimately expects a real file from
the desktop. The zone is in the page, the file is not.

## The three routes that do work

**A person does it, with the agent doing everything else.** Run the browser
headed, let the agent navigate, log in and fill the twelve other fields, and stop
at the upload with the form ready. You attach the file and submit. This is the
division of labour that
[downloading invoices from portals](ai-agent-download-invoices.md) describes for
the mirror-image problem, and it is the honest answer for most one-off work.

**A script, not an agent.** The underlying automation library can set a file
input directly. If this is a recurring job rather than an exploration, the thing
you want is twenty lines of code against the same engine, with the agent used
once to work out where the form is and what it wants. That hybrid is described in
[extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md)
for extraction, and the reasoning carries over.

**The API, if there is one.** Any system with an upload form worth automating
usually has an endpoint behind it. A browser is the route of last resort for
getting a file into somewhere, not the first.

## What the agent can still do around an upload

Most of the task, usually. Find the right form, fill the metadata, choose the
category, read the constraints the page states (accepted types, size limits,
required naming), check the result afterwards, and record the confirmation.

If the upload is one field in a twenty-field submission, the agent is still worth
using for the nineteen. Write the task so it stops at the boundary and reports
the state, rather than treating the whole thing as impossible.

## Short answers to the questions that lead here

**Can an AI agent upload a file?** Not with this tool surface. There is no
file-setting tool, and typing into a file input is refused with `Input of type
"file" cannot be filled`.

**Why does the agent see the input then?** The snapshot lists interactive
elements, and a file input is one. Being listed is not the same as being usable,
and this is the clearest case of that gap.

**Can it click the input and use the file dialog?** No. The dialog is an
operating-system window, not part of the page, so nothing that drives a page can
reach it.

**What about drag and drop?** Same problem: the drop zone is in the page, the
file is on your desktop, and the agent has no way to produce the file.

**What should I do instead?** Have the agent do everything except the attachment
and stop there for you, or write a short script against the same engine if the
job is recurring, or use the API if one exists.

**See also:**
[what a page snapshot costs, per control](what-a-page-snapshot-costs.md), for what
the snapshot does and does not mean, and
[using an AI agent to download invoices from portals](ai-agent-download-invoices.md),
which sets out the same escort-not-courier division for files coming the other
way.

## Sources

- Measured 2026-09-17 through this project's MCP server over stdio, on a page with one `<input type="file">` served from `127.0.0.1`. The snapshot entry and the refusal message are quoted verbatim from the run; `files.length` read back as 0 and the page's own change handler never fired.

---

*The page exists because the snapshot lists the input. If it did not, nobody
would try, and the failure would not take five calls to arrive at.*
