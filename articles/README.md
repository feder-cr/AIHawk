# Articles

Guides on using invisible_playwright_mcp, with worked examples.

- [Extracting a category to CSV](extracting-a-category-to-csv/) - a 32-book
  category over two pages, driven over MCP, with the wrong turn left in.
- [Web research, audited](web-research-audited/) - the agent counts 60 prices,
  a model-free script counts the same pages, and the two answers are printed
  side by side.

One article per folder, so the piece and the things it references travel
together:

```
articles/
  extracting-a-category-to-csv/
    README.md
    mystery-books.csv
    screenshots/
```

## What makes one worth publishing

**A prompt somebody can paste, and the result it actually produced.** Not a
paraphrase of what it would do. If the run took four tries to get right, the
article is more useful with the four tries in it than with a clean one that
never happened.

**The run's own visual record, not a diagram of it.** The thing worth showing
is the browser doing the work while the transcript narrates. For a headed run
that means a recording; for a headless MCP run, where there is no window to
point a recorder at, it means the screenshots the browser itself returned
during the run - actual captures from the session, never staged afterwards.

**The version it was recorded against.** These pieces go stale: the tool names
and the shape of the responses change between releases, and a reader who cannot
tell which version they are looking at cannot tell whether the difference is
theirs or ours.

## Two rules that are not style

**Site names are for subjects, not examples.** A mainstream platform may be
the declared subject of a guide - a piece about automating a specific site,
written in the open, honest about what that site's terms say and what the
reader risks. What stays out is the other thing: naming sites incidentally as
the targets your demo happens to run against, which turns a guide into a
target list. For demos and recordings, `books.toscrape.com` exists for exactly
this and is fair game; otherwise use a page you serve yourself. A guide about
a named site never includes instructions aimed at defeating that specific
site's protections.

**No proxy providers, and no credentials.** Not in a config block, not in a URL
in a screenshot, not in a terminal recording. A recording is the easiest place
to leak one, because nobody re-reads a video before publishing.

And read a screenshot before it ships. A grep cannot clear a PNG, and a
fingerprint or detector page paints the real IP, timezone and locale straight
into the pixels.
