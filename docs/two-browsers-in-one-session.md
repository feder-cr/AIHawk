---
title: "Two browsers in one session: main and support"
description: "The session holds two browsers with two separate identities and one exit. What that is for, the focus rule that will catch you, and what it does not separate."
parent: "Using the Agent"
nav_order: 55
---

# Two browsers in one session: main and support

A session here is not one browser. It is two, named `main` and `support`, and
every tool takes a `browser` argument to say which one it means. Most tasks never
need the second. The ones that do need it badly, and the behaviour has one trap
worth knowing before you meet it.

## What actually happens when you open both

Measured on 2026-09-17, opening each in turn and asking the session what it had:

```
browser_open                      -> main opens.    identity: seed 982240811
browser_open  browser: support    -> support opens. identity: seed 1206782028
```

```json
{"focus": "support",
 "browsers": [{"id": "main", "url": "", "urls": []},
              {"id": "support", "url": "", "urls": []}],
 "note": "2 of 2 browsers. Commands that name none go to main."}
```

Three facts fall out of that, and the third is the trap.

**The identities are different.** Two seeds, two fingerprints. The second browser
is a different person, not a second window belonging to the first. That is the
whole reason the feature exists.

**The exit is the same.** Both go out from the same address unless you say
otherwise. The support browser's own opening line says so: same exit as main.
Different identity, same address, which is a combination worth understanding
before you rely on it.

**Focus and default are not the same thing.** After opening the second browser
the focus is `support`, and yet the note says commands that name none go to
`main`. Both are true and they point in opposite directions. **If you open a
support browser and then issue a command without naming a browser, it goes to
main**, not to the one you just opened and are presumably looking at.

That asymmetry is deliberate rather than a bug: an unnamed command having a fixed
destination is more predictable than one that follows whatever you touched last.
It is still the thing that will produce one confusing run before you internalise
it. **Name the browser on every call once you have two.**

## What the second browser is for

**Keeping a reference open.** Read a specification, a spreadsheet view or a list
in support while filling a form in main, without navigating away from a page that
holds state. Losing a half-filled wizard by navigating away to check something is
a real and annoying failure, and this is the answer to it.

**Two accounts at once.** Two sessions on the same service, side by side,
comparing what each one sees. With separate profiles, two logins that do not
interfere.

**A clean second opinion.** A page behaves oddly in main, which has been clicking
around for twenty steps and has accumulated cookies and state. Open it fresh in
support and see whether it still does. This is the browser-side version of the
bisection in
[browser problem or model problem](browser-problem-or-model-problem.md).

**Comparing two versions of a page.** Two markets, two variants, two currencies,
read at the same moment rather than two minutes apart. Give each browser its own
exit and it becomes the honest way to run the comparison in
[seeing a page as it appears in another country](see-a-page-from-another-country.md).

## What it does not separate

Worth being precise, because "a second browser" sounds like more isolation than
it is.

**Not the process.** Both browsers live in one server process. If that dies, both
go.

**Not the exit, unless you ask.** They share an address by default. Pass a
different `proxy` to `browser_open` for the one that needs a different one.

**Not your machine.** Two identities from one address, browsing at the same time,
is a pattern rather than two unrelated visitors. Whether that matters depends
entirely on what you are doing, and pretending otherwise would be the kind of
absolute claim this wiki avoids.

**Not the model's attention.** The agent has one context. Two browsers means two
sets of page state for it to keep straight, and the most common failure is not
technical: it reads support and acts on main.

## Making the agent keep them straight

The tools give you the state; the task has to make the agent check it.

- **Say which browser each step is for**, in the task, by name.
- **Have it call `browser_list` before acting on a browser it has not touched for
  a while.** That returns the focus, both ids and the current URL of each, which
  is enough to catch a mix-up before it becomes a click.
- **Expect a clear error rather than a silent wrong action** when a browser has no
  page: a tool call against an empty browser answers "this browser has no page
  open; browser_navigate opens one". That is a good failure, and it is what makes
  the mix-up cheap when it happens.

## Two browsers or two sessions

If the two jobs genuinely have nothing to do with each other, two sessions is
cleaner: separate processes, separate failures, no chance of confusing them.

Use two browsers in one session when the work is one task that needs two views at
once, and the agent has to reason about both. That is the case the feature is
built for, and it is narrower than it first looks.

## Short answers to the questions that lead here

**How do I open a second browser?** Pass `browser: support` to `browser_open`.
Every other tool takes the same argument to say which one it acts on.

**Do the two browsers have different fingerprints?** Yes. Measured: two different
seeds, drawn independently. They are two identities, not two windows.

**Do they go out from different addresses?** Not by default. They share one exit
unless you give the second a proxy of its own when you open it.

**Why did my command go to the wrong browser?** Because an unnamed command always
goes to main, even when the focus is support. Name the browser on every call once
you have two.

**Should I use two browsers or two sessions?** Two sessions when the jobs are
unrelated. Two browsers when one task needs two views at the same time.

**See also:**
[the MCP server](mcp-server.md) for the full tool list and the settings each
browser inherits, and
[how the tools are shaped, and why](mcp-tool-design.md) for why the browser is an
argument on every tool rather than a mode you switch.

## Sources

- Measured 2026-09-17 against this project's MCP server over stdio: `browser_open` with no arguments and then with `browser: support`, followed by `browser_list` and `browser_status` on each. Seeds 982240811 and 1206782028 are from that run and are the session's own, not values to expect yourself. The listing note and the no-page error message are quoted verbatim from the responses.

---

*The focus-versus-default line is the one to remember. Everything else here is
what you would guess; that one is the opposite of what you would guess.*
