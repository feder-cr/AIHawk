---
title: "The task works headed and fails headless"
description: "Six causes, and the first thing to know is that it is rarely the site detecting headless. Usually it is the viewport, the timing, or a native dialog nobody is there to dismiss."
parent: "Using the Agent"
nav_order: 85
---

# The task works headed and fails headless

You watch it run, it works. You run it unattended, it fails. The conclusion
everybody reaches first is that the site can tell it is headless, and that is the
least likely of the six explanations below.

Work through them in this order, because the first three are free to check and
account for most of it.

## 1. The window is a different size

The commonest cause by a distance, and it has nothing to do with detection. A
headed window is whatever size your screen made it; a headless one is whatever
the default is. Different width means a different layout, and on a responsive
site a different layout means different elements.

A navigation that is a row of links at 1600 pixels is a hamburger menu at 900.
The selector the agent used when you watched does not exist in the other layout,
and the failure reads as "element not found".

Check it by looking at what the run actually saw. The live view shows the whole
window, per
[watching the agent work](watching-the-agent-work.md), and it works headless
precisely because there is still a window being composited.

## 2. Everything happens faster

When you watch, you are slow. You read the page, you move the mouse, seconds
pass, and the page finishes loading during them. Unattended, the calls arrive as
fast as they can be issued and the race that you always won is now a coin flip.

This is the single biggest reason "it worked when I watched it" is not evidence
that the task is correct. The mechanism, and the fix of waiting for a state
rather than a duration, is in
[when the page changes under the AI agent](when-the-page-changes-under-the-agent.md).

## 3. Something needed a person

A login that re-challenged, a code, a confirmation, a file to attach that
[the agent cannot attach](uploading-a-file-with-an-ai-agent.md). Watching, you
supplied it without thinking of it as a step. Unattended, there is nobody.

This one is easy to miss precisely because it did not feel like part of the task.
The check is to run headed and pay attention to everything you do with your own
hands.

## 4. A native dialog is waiting

A print dialog, a file picker, a permission prompt, a basic-auth box. These are
operating-system windows rather than parts of the page, so nothing that drives a
page can dismiss them, and the run stalls until a timeout.

Headed, you close it in a second and forget it happened.

## 5. The session was not the same session

You watched with a profile that had cookies, consent choices and a login in it.
The unattended run used a fresh one, so it got a consent wall, a locale picker,
or a sign-in page where you got the content.

The tell is that the failure happens at the very first read rather than deep in
the task. A persistent profile directory is what makes the two runs comparable,
and it is set out on
[the MCP server page](mcp-server.md).

## 6. The site really is treating the run differently

Last, not first, and when it happens it is usually not about headless as such: it
is the rhythm of an unattended run, the absence of the pauses a person makes, or
the volume of a loop. That family has its own pages:
[the timing signal AI agents give off](ai-agent-timing-signal.md) and
[agent retry loops trip rate limits, not fingerprints](agent-retry-loops-rate-limits.md).

Before concluding this, rule out the five above. They are cheaper to check and
they are more often the answer.

## The one-command bisection

Run the same task headed and headless, and compare the first read of each.

If the two reads differ, the cause is in 1, 5 or 6 and you can usually tell
which by looking: a different layout is 1, a consent wall or a login is 5, a
challenge page is 6. If the two reads match and the failure comes later, the
cause is 2, 3 or 4, and the question becomes which step.

That is the same instrument as
[browser problem or model problem](browser-problem-or-model-problem.md) applied
to a narrower question, and it is two runs.

## A note on how the mode is decided

Headless is the default and each launch decides for itself. A saved session does
not record the mode, so a browser reopened by a headless server stays hidden even
if it was headed last time you used it.

Worth knowing because it removes one possible explanation: a run is not
accidentally inheriting a headed mode from yesterday. Whatever it is, it is one
of the six.

## Short answers to the questions that lead here

**Why does my agent work headed and fail headless?** Most often a different
window size producing a different layout, or a timing race that watching used to
win. Site detection is the last thing to suspect, not the first.

**Does headless change the page?** Indirectly, through the viewport. A responsive
site at a different width is a different document, with different elements.

**Why does it work when I watch it?** Because you are slow. Your reading time was
the wait the task never declared.

**Can the agent dismiss a print or file dialog?** No. Those are operating-system
windows, not parts of the page.

**How do I tell which of the six it is?** Run both modes and compare the very
first read. Differing there points at the layout, the session or the site;
matching there points at timing, a human step, or a dialog.

**See also:**
[watching the agent work](watching-the-agent-work.md), which shows the window the
headless run actually has, and
[when the page changes under the AI agent](when-the-page-changes-under-the-agent.md)
for the timing half.

## Sources

- The behaviour that a saved session does not record headless, so a browser reopened by a headless server stays hidden, is this project's own documented behaviour on [the MCP server page](mcp-server.md).
- The ordering of the six causes is from experience with this browser rather than from a study, and the page is explicit that the popular explanation is the least likely one rather than claiming a measured frequency.

---

*The order is the content. Everybody starts at six and the answer is almost
always one or two.*
