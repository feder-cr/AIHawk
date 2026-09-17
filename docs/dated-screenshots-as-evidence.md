---
title: "Dated screenshots of a page as evidence"
description: "A screenshot proves what your browser rendered, not what the site served. What to capture alongside the image so the record is worth something, and the honest limits of the whole exercise."
parent: "Using the Agent"
nav_order: 59
---

# Dated screenshots of a page as evidence

Capturing a page because you may need to show later what it said is a real and
ordinary job: a price you were quoted, a policy before it changed, a listing that
disappeared, a competitor's claim. An agent is good at it, and the picture on its
own is close to worthless.

Understanding why is the difference between a usable record and a folder of PNGs.

## What a screenshot actually proves

It proves that a browser, on a machine, at some moment, rendered those pixels. It
does not establish which URL, when, what the server sent, or that the image has
not been edited since.

Every one of those gaps is closable, cheaply, and none of them is closed by
taking a better screenshot. **The image is the least important artifact in the
capture.**

## Capture the record, not the picture

For each capture, write all of this, in a file next to the image:

- **The final URL**, after redirects, not the one you asked for.
- **The timestamp in UTC**, from a clock you can name, plus the local time zone
  the browser was using, because the page may have rendered dates in it.
- **The page title and the full rendered text.** This is the part people skip and
  it is the most useful single item: text is searchable, diffable and quotable,
  while an image is none of the three. It also costs about a ninetieth of the
  image, which is
  [measured](what-should-the-agent-read.md).
- **The HTML as served**, so the structure and any values hidden in attributes
  survive.
- **The exit the request went out from**, at least the country, because a page
  that varies by market is a page whose capture means nothing without it. That is
  the subject of
  [seeing a page from another country](see-a-page-from-another-country.md).
- **A hash of each file**, computed at capture time and recorded in a separate
  list. This is what turns "here is an image" into "here is an image that has not
  changed since I took it", which is the only integrity claim you can honestly
  make yourself.

## Full page or viewport

A viewport screenshot shows what a person would see without scrolling, which is
sometimes exactly the claim: the price was visible above the fold, the disclaimer
was not.

A full-page capture shows everything, which is usually what you want for a record
and is occasionally misleading, because it composites a page that no viewer ever
saw at one moment. If the question is "what did it say", capture everything. If
the question is "what would a person have noticed", capture the viewport and say
which you did.

Record which one you took. A capture that does not say is a capture somebody can
argue with.

## The things that will ruin a capture

**Consent walls and cookie banners.** Half the captures people take are of a
modal. Dismiss it, and record that you dismissed it, because the page underneath
is the evidence and the overlay is not.

**Lazy content.** A page captured before the images and the lower sections
rendered is a picture of a skeleton. Wait for a state rather than a duration, per
[when the page changes under the AI agent](when-the-page-changes-under-the-agent.md),
and capture the text alongside so a thin capture is obvious.

**Personalisation.** A logged-in page shows your prices, your name, your recently
viewed. If the claim is about what the public sees, capture from a clean profile
with no session, and say so in the record.

**Your own details in the pixels.** A capture of a logged-in page contains
whatever the page shows about you. Before it goes to anybody, open it and look.
That applies to any image leaving your machine, and it is the rule this project
applies to its own screenshots without exception.

## Repeat captures are where the value is

A single capture is a snapshot. The useful artifact is a series: the same page,
same settings, on a schedule, with the text diffed between runs.

Then the record answers the question people actually ask, which is not "what did
it say" but "when did it change". Store the text per capture and compare; the
images become the illustration of a change the text found.
[Monitoring a page for changes with an AI agent](how-to-monitor-a-page-with-an-ai-agent.md)
is the monitoring half, and
[running an AI browser agent on a schedule](run-ai-agent-on-a-schedule.md) is how
it runs unattended.

## The limit, stated plainly

None of this makes a capture legally authoritative. A record you produced
yourself, on your own machine, with hashes you also produced, is a contemporaneous
business record and not an independent attestation. If the situation genuinely
needs one, the services that exist for it, and in some jurisdictions a notary,
are the answer and a browser is not.

What the discipline above gets you is a record that is internally consistent,
searchable, and hard to accidentally misrepresent. That is the right bar for
almost every real use, and it is worth knowing which bar you are clearing.

## Short answers to the questions that lead here

**How do I take a dated screenshot of a webpage?** Capture the image, and with it
the final URL, a UTC timestamp, the rendered text, the HTML, the exit country and
a hash of each file. The image alone proves very little.

**Is a screenshot proof of what a website said?** It is evidence of what your
browser rendered. Without the URL, the time and the content alongside it, it is
weak evidence and easy to dispute.

**Full page or just the visible part?** Full page for "what did it say", viewport
for "what would a person have seen". Record which.

**How do I prove the image was not edited?** You cannot, by yourself, beyond
hashing it at capture time and keeping the hash list separately. For a stronger
claim you need a third party.

**Why capture the text as well as the image?** Because text is searchable and
diffable, and because comparing two captures is how you find out when something
changed. It also costs about a ninetieth of the image.

**See also:**
[monitoring a page for changes with an AI agent](how-to-monitor-a-page-with-an-ai-agent.md),
which is what a series of these becomes, and
[text, HTML, snapshot or screenshot](what-should-the-agent-read.md) for why the
picture is the expensive artifact and the text is the cheap one.

## Sources

- The relative cost of an image against the rendered text of the same page, about 89 to 1, is measured and sourced on [text, HTML, snapshot or screenshot](what-should-the-agent-read.md).
- The claim about legal weight is deliberately non-specific: it varies by jurisdiction, and this page says only that a self-produced record is not an independent attestation, which is true everywhere.

---

*The one-line version: capture the text, hash everything, and write down what you
dismissed to get to the page. The picture is the part you will look at and the
smallest part of what makes the record worth having.*
