"""A registry around one conversation the test already built.

⛔ THIS WAS `Sessions.around`, A CLASSMETHOD IN THE PRODUCT WITH NO PRODUCT
CALLER. Eleven call sites, all in two test modules; zero in `src`. Its docstring
offered "and so would anything embedding this", which is a use nobody has: this
is an application, not a library, and the only importer of `invisible_playwright_mcp.sessions` is
`invisible_playwright_mcp.cli`.

The argument it was written for survives untouched and is worth restating,
because it is the reason this is a move and not a deletion: a test that drives
ONE conversation should still go through `build_app` and the routes, so the
single-conversation case is exercised by the same code the many-conversation
case uses. Two ways in would mean the routes were tested one way and used
another.

It reaches into `_brain`, which is a private of `ChatService`. That is fine
here and was not fine there: a test helper may know how the thing it helps is
built; the product should not carry a constructor whose only purpose is to be
built that way by a test.
"""
from __future__ import annotations

from invisible_playwright_mcp.sessions import Sessions


def around(service) -> Sessions:
    """A registry holding one conversation somebody else made.

    It never spawns anything: the conversation it holds already has its
    connection, and `Sessions.get` finds it in `_live` before reaching for the
    options it was built with.
    """
    got = Sessions({}, None, lambda: service._brain, service.model_label)
    got._live[service.session_id] = service
    return got
