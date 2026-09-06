---
title: "Posting to Instagram with an AI agent"
description: "The official publishing API covers professional accounts and is the right tool there; for everyone else this page says the uncomfortable part out loud: an Instagram post needs media, and the agent cannot upload a file."
parent: "Using the Agent"
nav_order: 18
---


# Posting to Instagram with an AI agent

Instagram is the platform where this wiki's honesty costs it the most, so
here is the summary up front. If you have a professional account, an official
publishing API exists and is the right tool. If you have a personal account,
no API exists - and the browser route has a hard limit that most pages on
this subject quietly skip: an Instagram post requires media, attaching media
in a browser means a file picker, and AIHawk's agent has no file-upload tool.
Verified against the source, not the marketing, on 2026-09-03. What remains
is a narrower, honest slot, described below without inflation.

The register first, and on Instagram it matters more than anywhere: this
page is about publishing your own posts to your own account, with you
reviewing each one. It is not about growth - no automated likes, follows or
comments, no volume, no multiple accounts. Instagram's enforcement history
against engagement automation is long and public, and nothing here is a tool
for it.

## The official API: professional accounts, two calls, real limits

Meta documents content publishing for Instagram professional accounts
(business and creator), and it works in two steps: create a media container,
then publish it.

```
POST /<IG_ID>/media           (the container: image URL, caption)
POST /<IG_ID>/media_publish   (publishes the container)
```

The limits are stated plainly in the documentation and worth quoting,
because they define what "supported automation" means here: "Instagram
accounts are limited to 100 API-published posts within a 24-hour moving
period. Carousels count as a single post." Images must be JPEG, the media
must sit at a publicly accessible URL at publish time, and an unpublished
container expires after 24 hours.

If you have a professional account, or your use of Instagram would justify
switching to one, this is the answer. One hundred posts a day
is two orders of magnitude beyond any human posting schedule, the calls are
documented and stable, and every scheduler product supports Instagram
through exactly this door. There is no honest reason to point a browser
agent at instagram.com when this API covers you.

## Personal accounts, and the limit this page exists to state

A personal Instagram account is outside the publishing API. That leaves the
web interface, and the web interface is where the claim you came to verify
falls apart, so here it is with its evidence.

Posting on instagram.com starts with a file: the create flow's first real
step is "select from computer", an OS file picker. AIHawk's agent operates
the browser through a fixed set of tools - navigate, read, click, type,
screenshot, and their session-management siblings - and that set contains no
file-upload action. This is checked against the tool server's source, not
inferred from a failed attempt. The agent can log in with your saved
session, open the create dialog and write a caption, but it cannot hand a
file to the picker. Since a feed post cannot exist without media, **AIHawk
cannot post to Instagram end to end, and this page will not pretend
otherwise.**

What works instead is a division of labor that is honest about who does
what. Run headed, so the browser is a normal window on your desktop:

```bash
aihawk ui --profile-dir ~/.aihawk-instagram --headed
```

Log in yourself once; the profile directory keeps the session for later
runs. When you want to post, you click through the media selection - the
one step that needs hands - and the agent is useful on either side of it:
navigating to the right place, typing a caption you dictated, reading back
what the review screen shows before you press Share. Whether that division
is worth a running agent for your posting volume is a fair question, and
for many people the answer is "post it by hand, it is faster". A tool page
that cannot say that sentence is selling something.

The final click stays yours either way. AIHawk's stated rule for every
surface applies verbatim here: do not submit anything a human has not read.

## The terms, and the account you are risking

Instagram is a Meta product, and Meta's Terms of Service, section 3.2,
fetched 2026-09-03, reads:

> "You may not access or collect data from our Products using automated means
> (without our prior permission) or attempt to access data you do not have
> permission to access, regardless of whether such automated access or
> collection is undertaken while logged-in to a Facebook account."

Instagram additionally maintains its own
[Terms of Use](https://help.instagram.com/581066165581870); that page is
rendered by script and could not be read by a plain fetch this session, so
it is cited here by name rather than quoted - read it in a browser before
deciding, because it binds you either way.

The risk statement, plainly: automated behavior on an Instagram account can
trigger action against the account - challenges, feature blocks,
restriction, or loss of the account - and Instagram has enforced against
automation more visibly than almost any platform. A personal account driven
by an agent, even gently, carries that risk, and the account is yours, not
the tool's. The lowest-risk shape is the one this page describes: your
session, your media click, your review, single posts at human frequency.

## Short answers to the questions that lead here

**Can an AI agent post to Instagram for me?** With a professional account,
use the official API instead: two documented calls, 100 API-published posts
per 24 hours, JPEG media at a public URL. With a personal account there is
no API, and AIHawk specifically cannot complete a browser post alone,
because posting requires media and its toolset has no file-upload action.

**Can AIHawk upload an image to Instagram?** No. The agent's tool
vocabulary has no file-upload action, so it cannot operate the file picker
that Instagram's create flow starts with. It can handle navigation and the
caption around a media selection you make yourself in a headed session.

**Is there an Instagram posting API for personal accounts?** No. The
content-publishing API covers Instagram professional accounts - business
and creator. Switching to a creator account is the supported path if you
want API publishing.

**Is automating Instagram against the terms?** Meta's terms restrict
automated access without prior permission - section 3.2 is quoted above -
and Instagram's own Terms of Use apply on top. Engagement automation is the
clearly-enforced end; your own single posts with human review is the
defensible end; the account risk in between is real and yours.

**What about scheduling posts?** Schedulers support Instagram through the
professional-account API, which is why they all ask you to connect a
professional account. Scheduling for a personal account does not exist
through any supported channel, whatever a landing page implies.

## Sources

All retrieved 2026-09-03.

- [Instagram platform: content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing),
  for the endpoints, the professional-account requirement, and the
  100-posts-per-24-hours quote.
- [Meta Terms of Service](https://www.facebook.com/legal/terms), section
  3.2, quoted verbatim above.
- [Instagram Terms of Use](https://help.instagram.com/581066165581870),
  cited by reference; not readable by plain fetch this session, as noted.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its source and
  the tool server's source in this repository's family, for the exact tool
  vocabulary and the absence of a file-upload action.

**See also:** [the social posting decision page](posting-to-social-media-with-an-ai-agent.md),
[posting to Facebook](post-to-facebook-with-an-ai-agent.md),
[posting to X](ai-agent-post-to-x.md),
[getting an AI agent to fill out forms](ai-agent-fill-out-forms.md), and the
rest of [Using the Agent](guides-using-the-agent.md).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The paragraph
admitting the agent cannot finish this task is the most useful one on the
page, which is exactly why it is here.*
