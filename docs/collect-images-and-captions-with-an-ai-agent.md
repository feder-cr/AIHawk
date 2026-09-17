---
title: "Collecting every image on a page with its caption"
description: "The caption is rarely in the alt text and almost never next to the file. Where the description actually lives in modern markup, and why the biggest image is the one you want."
parent: "Using the Agent"
nav_order: 63
---

# Collecting every image on a page with its caption

Pulling the pictures off a page is easy. Pulling them with the words that belong
to each one is the actual job, and it is harder than it looks because there is no
single place a caption lives.

## Where the description actually is

For any one image, the text that describes it may be in any of these, and often
in more than one with different content:

- **`alt`**, which is meant to be the description and is frequently empty, or a
  filename, or the word "image".
- **`title`**, shown on hover, sometimes the real caption.
- **A `<figcaption>`** in the same `<figure>`. When this exists it is usually the
  best answer.
- **A sibling element**, a `<p>` or a `<span>` right after the image, styled as a
  caption without any markup saying so.
- **`aria-label`** or a referenced `aria-describedby` element.
- **The link text**, when the image is inside a link to a larger version or a
  detail page.
- **The surrounding paragraph**, which is the only source when the page uses none
  of the above.

An agent asked for "the images and their captions" will pick one of these per
image, inconsistently. **Say which ones to try and in what order**, and have it
record which one it used. Then a caption that turns out to be a filename is
traceable to the field it came from rather than being a mystery.

## The `src` is not the image

The second thing that surprises people. A modern page serves several versions of
the same picture and lets the browser choose:

- `srcset` with widths, so the page carries a 400-wide and a 1600-wide URL and
  `src` holds whichever the author set as the fallback.
- A `<picture>` with `<source>` elements for different formats, where the `<img>`
  is the fallback for browsers that do not support the newer one.
- A lazy-loading placeholder in `src`, with the real URL in `data-src` and the
  displayed pixel being a grey rectangle until it loads.

If you take `src` you will sometimes get a thumbnail, sometimes a tracking pixel,
and sometimes a base64 blur. **Read the markup rather than the text**, take the
largest candidate from `srcset` when there is one, and prefer `data-src` over a
placeholder `src`.

Reading HTML rather than text costs 1.3 times as much and is the only
representation that carries attributes at all, which is
[measured on its own page](what-should-the-agent-read.md).

## Lazy loading means the list is incomplete

A gallery renders the images near the viewport and leaves the rest as
placeholders. Read once at the top and you get the first handful, with the others
either absent or pointing at a placeholder.

Same walk as everywhere: scroll, wait for the count to change, read, append,
repeat until the count stops growing, deduplicate on the URL rather than on
position. The identical pattern applies to a PDF viewer, where it is
[measured precisely](read-a-pdf-in-the-browser-with-an-ai-agent.md): two pages of
twelve present at first, and never the middle ones.

**Deduplicate on the resolved URL, not on the alt text**, because a page will
happily use the same caption for six images and different URLs for the same
picture.

## Background images will not be in your list

A picture set with CSS rather than an `<img>` element is invisible to any
approach that enumerates images, and it is common for hero banners and decorative
panels. If the thing you want is missing and looks like a background, it is one.

Whether that matters depends on the job: for a content inventory, those are
usually decoration you did not want. For "capture everything on this page", they
are a gap you should know about rather than discover later.

## What to write down

One row per distinct image, with:

- the resolved URL, at the largest size offered;
- the caption;
- **which field the caption came from**, from the list at the top;
- the width and height as the page declares them, when it does, because that is
  how you separate content images from icons afterwards;
- the page URL it was found on.

That third column is the one people leave out and the one that makes the dataset
trustworthy. Sorting by it tells you immediately that forty images have
"alt=image" and need a different treatment.

## Before downloading any of them

Enumerating what a page shows is one thing. Copying the files is another, and
whether you may depends on the licence and the terms of the site, not on whether
the agent can. A page being public says nothing about reuse rights, and images
are the category where that distinction is enforced most often.

Collect the list first. Decide about the files second, deliberately, and per site.

## Short answers to the questions that lead here

**Why are the captions empty?** Because `alt` is empty on a lot of real pages. Try
`figcaption`, `title`, an adjacent element and `aria-label` before giving up, and
record which one you used.

**Why did I get thumbnails instead of the full images?** You took `src`. The full
version is usually the largest entry in `srcset`, or in a `<picture>` source, or
in `data-src` behind a lazy placeholder.

**Why does my list stop at twelve images?** Lazy loading. Scroll and accumulate
until the count stops growing, and deduplicate on the URL.

**Some images on the page are not in the list at all.** They are probably CSS
background images, which are not `<img>` elements and will not be enumerated.

**Should I read the HTML or the text?** HTML, and it is the only choice: the
attributes that hold both the real URL and the caption do not exist in the text.

**See also:**
[extracting data to a CSV with an AI agent](how-to-extract-data-to-csv-with-an-ai-agent.md)
for the output side, and
[text, HTML, snapshot or screenshot](what-should-the-agent-read.md) for why the
markup is the cheap representation and the picture is not.

## Sources

- The relative cost of reading HTML against plain text, 1.3 to 1, and of a screenshot, 89 to 1, is measured and sourced on [text, HTML, snapshot or screenshot](what-should-the-agent-read.md).
- The lazy-rendering pattern, and the fact that scrolling reveals a moving window rather than accumulating the whole document, is measured on [reading a PDF that opens inside the browser](read-a-pdf-in-the-browser-with-an-ai-agent.md).
- The list of places a caption can live is from the markup patterns in current use and is offered as a checklist, not as a measurement.

---

*The column that says where the caption came from is the whole trick. Without it
you have a list of captions of unknown quality; with it you have a list you can
sort by quality in one click.*
