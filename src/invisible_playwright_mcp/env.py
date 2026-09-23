"""What this package reads from the environment, and what it still answers to.

⛔ THE NAMES LIVE HERE AND NOWHERE ELSE, BECAUSE FROM 2026-09-23 EACH OF THEM IS
TWO STRINGS: the name it has, and the name it had. Before that they were one
string each and a literal at the single place that read it was the right shape.
Two strings each is not: three modules read one of these and a fourth writes
one, so the pair would be six literals, and a rename that reaches five of them
is the silent kind. One house, and every caller asks it.

The old prefix was the product's previous brand. It was kept through the package
rename on the reasoning that somebody who had set it would otherwise find it
IGNORED, which is the worst way to break a configuration; the owner then asked
for the name to be abandoned outright. Both things are true at once, and this
module is how: the new name is the only one the product emits, documents or
teaches, and the old one still ANSWERS, out loud.

Precedence, when both are set: the new name wins. It is the more recent
decision, the same reasoning that makes the shell beat `.env` in `cli.py`.

`read` says so through the logger rather than a print, on purpose. stdout is the
MCP protocol channel and a print there corrupts the stream; the logger's default
destination is stderr, which a client discards and a person at a terminal sees.
Once per name per process, because a warning repeated on every lookup is a
warning people filter out.
"""
from __future__ import annotations

import logging
import os
from typing import Mapping, Optional

log = logging.getLogger("invisible_playwright_mcp")

#: Where sessions are kept, when the default place is not wanted.
HOME = "INVISIBLE_MCP_HOME"
#: The OpenRouter model id the interface and the agent use.
MODEL = "INVISIBLE_MCP_MODEL"
#: Which saved session this process serves. Set by `runner.child_env` for a
#: server it spawns, and read once at import by `mcp.server`.
SESSION_ID = "INVISIBLE_MCP_SESSION_ID"

#: new name -> the name it replaced on 2026-09-23. A name is in this map for
#: exactly as long as somebody might still have it set; removing an entry is a
#: deliberate act, and the entry is what makes that act visible.
RETIRED = {
    HOME: "AIHAWK_HOME",
    MODEL: "AIHAWK_MODEL",
    SESSION_ID: "AIHAWK_SESSION_ID",
}

#: Names already warned about, so the notice is one per process and not one per
#: lookup. Module state on purpose: the point is that it outlives the call.
#:
#: ⛔ IT HAD A `forget_what_was_said()` BESIDE IT FOR ONE RUN, so a test could
#: reset it without touching a private name. The surface gate refused it, and
#: the gate was right: a function in the product that nothing in the product
#: calls is surface somebody will later mistake for a feature. The test that
#: asserts on the deduplication clears this directly, which is fair - the
#: deduplication is its whole subject.
_SAID: set = set()


def read(name: str, env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """The value set under `name`, or under the name it replaced, or None.

    `env` is a mapping so a test can hand one in; it defaults to the process's.
    """
    where = os.environ if env is None else env
    value = where.get(name)
    if value:
        return value

    was = RETIRED.get(name)
    if not was:
        return None
    old = where.get(was)
    if not old:
        return None

    if was not in _SAID:
        _SAID.add(was)
        log.warning(
            "%s is the retired name for %s and is what answered. It still works; "
            "the new name is what this package reads first, documents and will "
            "keep. Rename it in your shell or your .env when convenient.",
            was, name)
    return old

