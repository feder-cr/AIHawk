---
title: "Posting to Facebook with an AI agent"
description: "For a Facebook Page the Graph API is the right tool and this page proves it; for a personal profile no posting API exists, and that is the narrow slot where a browser agent honestly fits."
parent: "Using the Agent"
nav_order: 17
---


# Posting to Facebook with an AI agent

Whether an AI agent should post to Facebook for you depends on one question
with a verifiable answer: are you posting as a Page or as a personal profile?
The two surfaces have opposite answers, both checked against Meta's own
documentation on 2026-09-03, and this page takes them in that order: the API
case first because it is the right tool where it applies, then the profile
case where the agent has its one honest slot, then the walkthrough and the
terms-of-service reality you accept by doing any of it.

Scope, before anything else: this is about publishing your own posts to your
own Page or your own profile, one at a time, with you reading them before
they go out. It is not about posting into groups at volume, not about
engagement automation of any kind - likes, follows, comments at scale - not
about mass posting, and not about running more than one account. Meta's
enforcement is aimed squarely at that cluster, and no tool choice makes it a
good idea.

## Posting as a Page: the Graph API is the right tool

If you manage a Facebook Page, stop here and use the API. Publishing is one
documented call:

```
POST /page_id/feed
```

with a `message` (and optionally a `link`), authenticated by a Page access
token, requiring the `pages_manage_posts` and `pages_manage_engagement`
permissions alongside the read permissions. Scheduling is native: send
`published=false` plus a `scheduled_publish_time`, and Meta's documentation
states the publish date "must be between 10 minutes and 30 days from the time
of the API request". That is a supported, stable, terms-compliant channel
with scheduling built in, and an agent clicking through the Page composer
would be a slower, costlier, more fragile way to do the same thing.

The secondary question people arrive with - how to automate Facebook posts
from Python - has the same answer for Pages: a few lines against the Graph
API, no browser anywhere.

```python
import requests

requests.post(
    "https://graph.facebook.com/PAGE_ID/feed",
    data={"message": "Release notes are up.", "access_token": PAGE_TOKEN},
)
```

Setting up the token takes a developer account and an app; that one-time cost
is the whole price of doing this the supported way.

## The personal profile: where no API exists

Personal profiles are the opposite case, and it is not a gap in your reading:
there is no API for publishing to a personal timeline. The Graph API
reference for the User/feed edge marks the create operation as unavailable:
the edge is for reading, and no permission exists that would change that.
Every third-party tool that claims to post to profiles is driving the web
interface, whatever its landing page implies.

So the honest options for a profile are exactly two: post by hand, or have
something operate the same web interface you would - which is what a browser
agent is. That makes the profile the agent's slot by elimination, and it
also means the terms question cannot be skipped, because the web interface
is governed by Meta's Terms of Service and the automated path through it is
precisely what those terms address.

## What Meta's terms say, and the risk you carry

Quoted from Meta's Terms of Service, section 3.2 ("What you can share and do
on Meta Products"), fetched 2026-09-03:

> "You may not access or collect data from our Products using automated means
> (without our prior permission) or attempt to access data you do not have
> permission to access, regardless of whether such automated access or
> collection is undertaken while logged-in to a Facebook account."

The clause is written around data collection, and posting your own content is
not collecting data - but do not read that as a safe harbor. The terms give
Meta broad discretion over automated interaction with its products, and
Meta's enforcement systems do not adjudicate intent: an account behaving
automatically can be checkpointed, asked to verify, restricted or disabled,
and appeals for personal accounts are slow and uncertain. Plainly: if you
point an agent at your own profile, you accept a real, non-zero risk to that
account. Occasional single posts with a human reviewing each one is the
lowest-risk end of the spectrum; anything resembling volume is the highest.
This wiki's position is to state that trade honestly and leave the decision
with the account's owner, who is the only person entitled to make it.

## The walkthrough, as it actually goes

What a session looks like with AIHawk, and what to expect from each step:

**Login persists; do it yourself, once.** Start with a profile directory so
the session survives restarts - the README describes `--profile-dir` as a
directory that keeps logins and cookies across runs:

```bash
aihawk ui --profile-dir ~/.aihawk-facebook
```

Log in by hand in that first session. A login page is where a site's
defenses concentrate, and your password does not belong in a prompt anyway.
Every later session finds the cookies in place and starts logged in.

**Tell it the post, tell it to stop.** The instruction that works is
explicit about both the content and the boundary:

> Go to facebook.com. Open the composer ("What's on your mind?"), type
> exactly this post, and stop. Do not click Post. Tell me when the text is
> in place: "Shipped the new release this morning. Changelog in the
> comments."

The composer is a custom widget of the kind
[the forms page](ai-agent-fill-out-forms.md) documents: expect a click to
open it, a pause, then typing through real key events - AIHawk refuses to
inject text by script, because pages can tell the difference. Then you read
the draft in the browser and the final click is yours. That division is not
caution theater; it is the README's own rule for the whole tool: do not
submit anything a human has not read.

**Know the media boundary.** AIHawk's toolset has no file-upload action, so
the agent cannot attach a photo: text posts and link posts are within its
reach, and a photo post needs your hands for the attachment step (run with
`--headed` and the browser is a normal window you can click in). Link
previews generate on their own once the URL is typed, so link posts work
fine.

**If something fails, read before rerunning.** A composer that never opens,
or a session that lands on a checkpoint page, is not a prompt problem - see
[why agents get blocked](why-does-my-ai-agent-get-blocked.md) before
spending more tokens. And resist retry loops: repeated identical attempts
are themselves a signal, covered in
[retry loops and rate limits](agent-retry-loops-rate-limits.md).

## Short answers to the questions that lead here

**Can an AI agent post to Facebook for me?** To a Page, yes, but the Graph
API is the better tool and this page shows the call. To a personal profile,
a browser agent is the only kind of automation that can, because no posting
API exists for profiles; do it with your own session, one post at a time,
reviewing before the click, and accepting the account risk stated above.

**How do I automate Facebook posts with Python?** For a Page:
`POST /page_id/feed` via the Graph API with a Page access token and the
`pages_manage_posts` permission; scheduling is native. For a profile there
is no API to call from Python or anything else; the web interface is the
only surface.

**Is it against Facebook's terms?** Meta's terms restrict automated access -
section 3.2 is quoted above - and give Meta wide enforcement discretion.
Your own content on your own account with human review is the defensible
end; volume, groups, engagement automation and multiple accounts are the
prohibited end. The risk to the account is real in all cases and it is
yours.

**Can it post with an image?** Not unattended: the toolset has no
file-upload action. Have the agent handle the text and do the attachment
yourself in a headed session, or use the Page API, which takes media
properly.

**Can it post to groups?** This page does not cover posting to groups, and
at volume that is exactly the pattern this wiki's scope rules out. If you
have one group you genuinely participate in, post there yourself.

## Sources

All retrieved 2026-09-03.

- [Meta Terms of Service](https://www.facebook.com/legal/terms), section 3.2,
  quoted verbatim above.
- [Facebook Pages API: posts](https://developers.facebook.com/docs/pages-api/posts/),
  for the endpoint, permissions and the scheduling window.
- [Graph API reference: User/feed](https://developers.facebook.com/docs/graph-api/reference/user/feed/),
  for the create operation being unavailable on the personal-profile edge.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its README and
  source in this repository, for `--profile-dir`, the real-input-events
  behavior, the absence of a file-upload tool, and the human-review rule.

**See also:** [the social posting decision page](posting-to-social-media-with-an-ai-agent.md),
[posting to Instagram](post-to-instagram-with-an-ai-agent.md),
[posting to X](ai-agent-post-to-x.md),
[getting an AI agent to fill out forms](ai-agent-fill-out-forms.md), and the
rest of [Using the Agent](guides-using-the-agent.md).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The rule about
keeping the final click human is not legal decoration; it is how the
maintainer uses the agent on accounts that matter to him.*
