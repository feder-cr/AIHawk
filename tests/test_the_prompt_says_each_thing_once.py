"""The model is told each thing once, and by whoever owns it.

⛔ THE SYSTEM MESSAGE IS TWO TEXTS GLUED TOGETHER, so a sentence in both is a
sentence the model reads twice in one message - and two copies of a rule are
two things to keep in agreement. The prompt used to open with "open the browser
with browser_open before anything else; if a tool answers that the browser is
not open or is gone, call browser_open and carry on", which is the server's
first paragraph said again a few lines above it.

⛔ AND THE SAME SENTENCE ABOUT `browser` CLOSED THIRTEEN TOOL DESCRIPTIONS,
word for word. That is thirteen places to change it, and it was spent out of
the wrong budget: a description is cut at 1024 characters before the model
reads it, and `browser_open` sat at 1021 - three characters from losing the
sentence that says who closes `support`, which is the defect its own gate was
written for. On the parameter it is said once and shown beside the argument it
describes, on every tool.

The rule about opening belongs to the SERVER: it is a fact about the tools, and
a standalone client that never sees the loop's prompt still has to be told it.
"""
from __future__ import annotations

import asyncio

from invisible_playwright_mcp.agent import SYSTEM_PROMPT, system_message
from invisible_playwright_mcp.mcp import server


def descriptions() -> dict:
    tools = asyncio.run(server.mcp.list_tools())
    return {t.name: (t.description or "") for t in tools}


def schemas() -> dict:
    tools = asyncio.run(server.mcp.list_tools())
    return {t.name: t.inputSchema for t in tools}


def test_the_rule_the_prompt_stopped_saying_is_said_by_the_server():
    """⛔ THE HALF THAT MATTERS WHEN A SENTENCE MOVES. Taking it out of the
    prompt is only safe while the place it moved to still has it, and that is
    a thing to hold rather than to trust.

    Known-bad: take the first paragraph out of INSTRUCTIONS - the rule is then
    in neither text and nothing else fails.
    """
    text = server.INSTRUCTIONS
    assert "browser_open" in text
    assert "BEFORE ANYTHING ELSE" in text, (
        "the server no longer tells a caller to open a browser first, and the "
        "loop's prompt stopped saying it on the strength of this")
    assert "no other tool opens a browser" in text


def test_the_prompt_and_the_server_do_not_say_the_same_thing_twice():
    """Known-bad: put the sentence back at the top of SYSTEM_PROMPT.

    Held on the SHARED sentences rather than on a word: `browser_open` is named
    by both texts for different reasons and that is fine. What must not happen
    is the same instruction arriving twice.
    """
    both = system_message(server.INSTRUCTIONS)["content"]
    for repeated in ("before anything else",
                     "call browser_open and carry on"):
        assert both.lower().count(repeated.lower()) <= 1, (
            "the model reads %r twice in one system message" % repeated)


def test_the_prompt_keeps_what_only_the_loop_owns():
    """The cut must not take the half that has no other home: how the agent
    writes is this loop's business and appears nowhere in the server.

    Known-bad: move a writing rule into INSTRUCTIONS, or delete it.
    """
    for owned in ("Never use emoji", "plain hyphen", "answer first"):
        assert owned.lower() in SYSTEM_PROMPT.lower(), (
            "the loop's own prompt lost %r, which the server never says" % owned)
    assert "emoji" not in server.INSTRUCTIONS.lower(), (
        "a writing rule moved into the server, which is the wrong owner")


def test_the_browser_parameter_explains_itself_once():
    """Known-bad: put the sentence back at the end of a tool docstring.

    The schema carries it for every tool that takes the argument, so a client
    shows it beside the argument whether or not the description reached its
    end.
    """
    carried = 0
    for name, schema in schemas().items():
        field = (schema.get("properties") or {}).get("browser")
        if field is None:
            continue
        carried += 1
        assert "main" in (field.get("description") or ""), (
            "%s takes a browser and the parameter does not say what it means"
            % name)
    assert carried >= 13, "only %d tools carry the argument" % carried

    repeats = [n for n, d in descriptions().items()
               if "is `main` unless you say" in d]
    assert not repeats, (
        "the sentence is back in the descriptions, spending the budget the "
        "rules can only be stated in: %s" % repeats)


def test_moving_a_sentence_did_not_move_the_cost():
    """⛔ THE MEASUREMENT THAT CAUGHT THIS CHANGE BEING A LOSS. A tool's schema
    is resent every turn exactly as its description is, so a sentence moved from
    thirteen descriptions into thirteen schemas is the same duplication wearing
    a different coat - and the first version of the move, four sentences long,
    cost 16% MORE per turn than the thirteen copies it replaced.

    Held on the COMPLETE definition, which is what travels, and not on the
    description alone, which is what looked good.

    ⛔ HELD ON THE CAUSE, NOT ON THE TOTAL. A first draft asserted a ceiling on
    the whole definition and had to be thrown away: in CHARACTERS the change is
    +77 while in TOKENS it is -13, so the aggregate answers differently
    depending on which unit you ask it in, and neither answer is about the
    thing that went wrong. What went wrong is a paragraph on a parameter that
    thirteen tools carry, and that is one number with one meaning.

    Known-bad: put the four-sentence version back on the `browser` parameter -
    the descriptions still shrink, and this is what goes red.
    """
    #: One line. Thirteen tools carry it, so every character here is spent
    #: thirteen times on every turn, while the paragraph it replaced is said
    #: once per conversation in the server's instructions.
    LIMIT = 80
    for name, schema in schemas().items():
        field = (schema.get("properties") or {}).get("browser")
        if field is None:
            continue
        text = field.get("description") or ""
        assert len(text) <= LIMIT, (
            "the `browser` parameter carries %d characters on %s, and on "
            "twelve other tools beside it: what a browser IS belongs to the "
            "instructions, which are sent once. %r" % (len(text), name, text))


def test_no_description_is_near_the_cut_any_more():
    """⛔ NOT A DUPLICATE OF THE EXISTING CEILING GATE. That one holds every
    description UNDER 1024. This holds that the one which has to carry the
    most is not sitting against it, because at three characters of headroom
    the next true sentence anybody adds is the one that disappears.

    Known-bad: pad browser_open back up towards the limit.
    """
    longest = max(descriptions().items(), key=lambda kv: len(kv[1]))
    assert len(longest[1]) <= 1024 - 16, (
        "%s is %d of 1024, so there is no room to say anything else"
        % (longest[0], len(longest[1])))
