"""Every tool the agent can call has a word a person recognises.

The step list is the whole interface: it is what a person watches while the
agent works, and it is the only place they can see something going wrong before
it finishes. A step that reads `Called selector=#sala, value=beta` is not
broken, it is just written in the machine's word order - which is the same
thing to whoever is reading it.

⛔ AND IT DEGRADES SILENTLY, which is why this is a test and not a habit.
`browser_select_option` was added to the server and the step list rendered it
through the fallback the very first time a model used it, with nothing red
anywhere. The verb table is in the page's JavaScript and the tool list is in
another package; the two can only disagree, never complain.

Reads the table out of the served page rather than importing a Python
constant, because the table a reader sees is the one in the page.
"""
from __future__ import annotations

import re



def _verbs_in_the_page() -> dict:
    from aihawk import web

    match = re.search(r"const VERB = \{(.*?)\};", web.PAGE, re.S)
    assert match, "the VERB table is gone from the page, or has been renamed"
    return dict(re.findall(r"(\w+)\s*:\s*\[\s*'([^']*)'", match.group(1)))


def test_the_table_is_read_correctly_before_anything_is_concluded_from_it():
    """A parser that finds nothing would make the next test pass for free.

    Same family as a gate whose mutation never reaches the code: the assertion
    below is only worth something if this one holds.
    """
    verbs = _verbs_in_the_page()
    assert len(verbs) >= 10, "only parsed %d entries, so the regex is wrong" % len(verbs)
    assert verbs.get("browser_navigate") == "Navigating", verbs.get("browser_navigate")


def test_every_tool_the_server_offers_has_a_verb():
    """Against the LIVE tool list, so a tool added upstream shows up here.

    The alternative - a hand-written list of names in this repo - drifts the
    same way the table does, and would have been just as quiet.
    """
    import asyncio

    from aihawk.mcp import server

    offered = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert offered, "the server registered no tools at all"

    verbs = _verbs_in_the_page()
    missing = sorted(offered - set(verbs))
    assert not missing, (
        "these tools would render as 'Called <raw arguments>' in the step "
        "list: %s" % missing)


def test_the_table_names_no_tool_that_does_not_exist():
    """The other direction. A verb for a tool nobody offers is a tool that was
    removed upstream without anyone here noticing, and the next reader trusts
    the table as an inventory.
    """
    import asyncio

    from aihawk.mcp import server

    offered = {t.name for t in asyncio.run(server.mcp.list_tools())}
    stale = sorted(set(_verbs_in_the_page()) - offered)
    assert not stale, "verbs for tools the server no longer offers: %s" % stale
