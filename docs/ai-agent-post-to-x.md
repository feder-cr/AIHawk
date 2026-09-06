---
title: "Posting to X with an AI agent"
description: "X has a real write API at pay-per-usage prices and a dedicated automation policy; this page does the arithmetic honestly and locates the narrow case where a browser agent still makes sense."
parent: "Using the Agent"
nav_order: 19
---


# Posting to X with an AI agent

X is the platform where the API-versus-agent question is genuinely close,
so this page does the arithmetic instead of picking a side first. X has a
real, working write API; it costs money per request; and X publishes a
dedicated automation policy that governs whichever route you take. All
three facts were checked on 2026-09-03, and the honest conclusion is at the
end rather than assumed at the start.

Scope, as on every page in this set: your own posts, your own account, one
at a time, with you in the loop. Not engagement automation - no automated
likes, reposts, replies or follows - not mass posting, not multiple
accounts. X's spam enforcement is aimed at exactly that cluster, and its
automation policy addresses it directly.

## The write API, and what it costs now

Creating a post through the X API v2 is one endpoint:

```
POST /2/tweets
```

authenticated with an OAuth 2.0 user token carrying the `tweet.write`
scope. The documented rate limits are far above human posting: 100 requests
per 15 minutes per user, 10,000 per 24 hours per app.

The part that changed and that older articles get wrong: X API pricing is
now pay-per-usage, no subscription tiers. Per X's own pricing page, a
standard post costs $0.015 per request, and a post containing a URL costs
$0.200 per request. There is no free allowance; every call is charged.

Do the math for the register this page assumes. A person posting three
times a day, every day, spends about $1.35 a month at the standard rate,
or around $18 a month if every post carries a link. That is not free the
way Mastodon's or Bluesky's APIs are free, but for text posts it is coffee
money, and it buys the supported channel: documented behavior, no
interface drift, no session to keep alive. If you can hold your nose
through the developer-portal setup, the API is the robust answer for
anything programmatic, and this wiki says so even though it maintains a
browser agent.

The URL price is the one honest wrinkle. At $0.200 per link post, a
link-heavy posting habit costs real money through the API - more than
thirteen times the standard rate - and that asymmetry is presumably not an
accident. It
is also the one place where the economics stop being negligible and the
browser route earns a look.

## The automation policy you are bound by either way

X maintains a dedicated automation rules page:
[help.x.com/en/rules-and-policies/x-automation](https://help.x.com/en/rules-and-policies/x-automation).
That page returns a 403 to plain fetchers - it did to this wiki's checks
this session - so nothing from it is quoted here, because quoting a page
you could not read is how documentation rots. It exists, it is X's
governing document on automated behavior, and you should read it in a
browser before automating anything on X, through the API or otherwise.

The risk statement, plainly: X suspends and restricts accounts for
automated behavior it classifies as spam or platform manipulation, and an
account driven through the web interface by an agent is automated behavior
in the ordinary sense of the words, whatever the volume. Single posts of
your own content with human review is the defensible end of the spectrum;
it is not a guarantee. The account is yours and so is the risk. If the
account matters commercially, the API route also has the advantage of
being the channel X itself sells for this purpose.

## Where the browser agent honestly fits

Given a working API at these prices, the agent's slot on X is narrow, and
it is not "saving money" for most people. It is three specific situations:

- **No developer setup, ever.** The API route means a developer account, an
  app, OAuth tokens and a credit card on file at the portal. For someone
  who posts occasionally and will not do that setup, an agent driving
  their existing logged-in session is the only automation they will
  actually use.
- **Mixed sessions.** An agent can read your timeline context, draft a
  reply-shaped post about something it just looked up on the web, show
  you, and post after your approval - one conversational loop in one
  browser. The API splits that across tools; the agent keeps it in one
  place with you watching. The drafting half of that loop is
  [web research](ai-agent-web-research.md), which the agent does anyway.
- **Link-heavy, low-volume posting**, where the $0.200 per-request price
  makes the API cost visible and the browser costs what your model tokens
  cost.

The mechanics mirror the other platforms. Keep the session with
`--profile-dir` and log in yourself once; ask for the post to be typed and
for the agent to stop before the Post button; read it; click it yourself.
AIHawk types through real input events rather than script injection, the
composer is an ordinary rich-text widget by
[the forms page's](ai-agent-fill-out-forms.md) standards, and the
human-review rule is the README's own: nothing submits that a person has
not read. Media carries the same boundary as everywhere: the toolset has no
file-upload action, so an image post needs your hands for the attachment
in a headed session; text and link posts are fully within reach.

```bash
aihawk ui --profile-dir ~/.aihawk-x
```

> Go to x.com. Open the composer, type exactly this post, and stop without
> clicking Post. Tell me when it is ready for review: "New write-up on the
> wiki: how the three posting routes actually compare."

## The honest conclusion

For programmatic posting on X, use the API: it works, its per-post price
is small for text, and it is the channel built for the purpose. The browser
agent is for the person who will never open the developer portal, for
sessions where reading and posting mix, and for the occasional link post
priced oddly by the API - always at human frequency, always with the final
click human. If your plan involves volume on either route, X's automation
policy is the document standing in your way, and no tool changes that.

## Short answers to the questions that lead here

**Can an AI agent post to X (Twitter) for me?** Yes - it drives your own
logged-in session, types the post and leaves the final click to you. But
check the API first: `POST /2/tweets` at $0.015 per standard post is the
supported route, and for anything programmatic it is the better one.

**How much does the X API cost for posting?** Pay-per-usage, per X's
pricing page fetched 2026-09-03: $0.015 per standard post, $0.200 per post
containing a URL, no subscriptions and no free allowance. Per-user rate
limit on the endpoint: 100 requests per 15 minutes.

**Is automating posts against X's rules?** X publishes dedicated
automation rules at help.x.com (linked above; it blocks plain fetchers, so
read it in a browser). Automated engagement and spam are the enforced
core; posting your own content at human frequency with review is the
defensible end. Account risk exists on every route and it is yours.

**Can the agent post with an image?** Not unattended - the toolset has no
file-upload action. Text and link posts work; attach media yourself in a
headed session, or use the API, which has proper media upload endpoints.

**Should I use the agent to save on API costs?** Mostly no. At $0.015 a
post, three posts a day costs under two dollars a month through the API,
less than the model tokens the agent would spend. The exception worth
naming is link-heavy low-volume posting at the $0.200 URL price.

## Sources

All retrieved 2026-09-03.

- [X API: creation of a post](https://docs.x.com/x-api/posts/creation-of-a-post),
  for `POST /2/tweets`, the `tweet.write` scope and media constraints.
- [X API: rate limits](https://docs.x.com/x-api/fundamentals/rate-limits),
  for the 100 per 15 minutes per user and 10,000 per 24 hours per app
  figures.
- [X API: pricing](https://docs.x.com/x-api/getting-started/pricing), for
  the pay-per-usage model and the per-request prices quoted above.
- [X automation rules](https://help.x.com/en/rules-and-policies/x-automation),
  cited by reference; it returned 403 to plain fetches this session, so no
  text from it is quoted.
- [feder-cr/AIHawk](https://github.com/feder-cr/AIHawk), plus its README
  and source in this repository, for `--profile-dir`, real input events,
  the absence of a file-upload tool, and the human-review rule.

**See also:** [the social posting decision page](posting-to-social-media-with-an-ai-agent.md),
[posting to Facebook](post-to-facebook-with-an-ai-agent.md),
[posting to Instagram](post-to-instagram-with-an-ai-agent.md),
[AI agents for web research](ai-agent-web-research.md), and the rest of
[Using the Agent](guides-using-the-agent.md).

---

*From the [AIHawk](https://github.com/feder-cr/AIHawk) wiki. The page that
tells you to pay X fifteen cents a day instead of running our agent is the
page you can trust about the cases where the agent is the right call.*
