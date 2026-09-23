"""The selector the snapshot hands out, EXECUTED, with no browser.

⛔ THE MACHINE HAS A JAVASCRIPT ENGINE AND THIS GATE WAS READING STRINGS.
`SNAPSHOT_JS` is 220 lines of JavaScript inside a Python string, and the part
of it below decides the selector for every click this product makes. Its
behaviour was proven in exactly one place: `test_snapshot_handles.py`, against
a real Firefox, behind `@pytest.mark.e2e` - which the default selection
DESELECTS. So on an ordinary run, and on every pull request that does not pay
for an engine, the rule "prefer an id, then a name, then an href" was held up
by regexes over the source text, which can see that a branch exists and never
what it returns.

`node` is on this machine and on every CI runner, and three of this suite's
page gates already use it. The half of the snapshot that builds a HANDLE is
pure: element attributes in, a selector string out, with one question asked of
the document (how many nodes does this selector match). That is a fake small
enough to print. The half that decides VISIBILITY is not, and stays where it
is: it reads layout through getBoundingClientRect and getComputedStyle, and a
fake DOM for that would be fiction rather than a test.

⛔ ONE BRANCH IS DELIBERATELY NOT REACHED HERE. `cssq` prefers `CSS.escape`
when the window has it, which every real engine does and node does not, so
what runs below is the regex fallback. The escaping assertions therefore hold
the fallback to the same promise; the engine's own branch is what
`test_snapshot_handles.py` exercises against Firefox. Said plainly rather than
left for somebody to discover: a gate whose perimeter is guessed from its
green is a hope.
"""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from invisible_playwright_mcp.mcp import actions

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="needs node to EXECUTE the handle logic")

FIRST = "    function useful(h) {"
LAST = "    // No deduplication."

#: A document small enough to print: `querySelectorAll` answers from a table
#: the test writes, which is the one question `handle` asks of the page.
SHIM = """
const window = {};
let DOC = {};
const document = { querySelectorAll: (sel) => { if(!(sel in DOC)) throw new Error('unknown selector ' + sel); return DOC[sel]; } };
function node(tag, attrs){
  const el = { tagName: tag.toUpperCase(), id: attrs.id || '', name: attrs.name || '',
               getAttribute: (k) => (k in attrs ? attrs[k] : null) };
  return el;
}
"""


def handles(script: str):
    """Run `script` against the snapshot's own handle logic."""
    body = actions.SNAPSHOT_JS[actions.SNAPSHOT_JS.index(FIRST):actions.SNAPSHOT_JS.index(LAST)]
    done = subprocess.run([NODE, "-e", SHIM + body + "\n" + script],
                          capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert done.returncode == 0, "the handle logic threw:\n%s" % done.stderr
    return json.loads(done.stdout)


def test_a_handle_prefers_an_id_then_a_name_then_an_href():
    """⛔ THE ORDER IS THE WHOLE THING, and it is measured: across 958 elements
    on real pages 88.3% carried an id, a name or an href.

    Known-bad: swap any two arms of the chain. Ids are the commonest handle on
    the web, so putting `name` first is the mutation that looks harmless and
    changes the selector of a large share of every page.
    """
    got = handles("""
      const el = node('input', {id: 'go', name: 'q'});
      DOC = {'#go': [el], "input[name='q']": [el]};
      const withId = handle(el, undefined).sel;
      const noId = (el.id = '', handle(el, undefined).sel);
      const link = node('a', {});
      DOC["a[href='/x']"] = [link];
      const byHref = handle(link, '/x');
      process.stdout.write(JSON.stringify({withId, noId,
        byHref: byHref.sel, fromHref: byHref.fromHref}));
    """)
    assert got["withId"] == "#go", "an id is not the first choice: %r" % (got,)
    assert got["noId"] == "input[name='q']", (
        "an element with no id is not addressed by its name: %r" % (got,))
    assert got["byHref"] == "a[href='/x']" and got["fromHref"] is True, (
        "a link with neither id nor name is not addressed by its href: %r" % (got,))


def test_a_test_id_and_then_an_aria_label_are_the_last_resorts():
    """⛔ APPENDED TO THE ORDER, NOT WOVEN INTO IT, which is why they come
    last: 9.5% of elements had no handle at all and fell back on coordinates
    that go stale the moment the page scrolls. Of those, 58% carried a
    data-testid and a further quarter a unique aria-label.

    Known-bad: move either arm above `name`, and a form field that has both
    stops being addressed by the name the server will read.
    """
    got = handles("""
      const out = {};
      const testid = node('div', {'data-testid': 'send'});
      DOC = {"[data-testid='send']": [testid]};
      out.testid = handle(testid, undefined).sel;

      const qa = node('div', {'data-qa': 'ok'});
      DOC["[data-qa='ok']"] = [qa];
      out.qa = handle(qa, undefined).sel;

      const labelled = node('div', {'aria-label': 'Close'});
      DOC["[aria-label='Close']"] = [labelled];
      out.aria = handle(labelled, undefined).sel;

      const named = node('input', {name: 'q', 'data-testid': 'search'});
      DOC["input[name='q']"] = [named];
      out.nameWins = handle(named, undefined).sel;

      out.nothing = handle(node('div', {}), undefined);
      process.stdout.write(JSON.stringify(out));
    """)
    assert got["testid"] == "[data-testid='send']"
    assert got["qa"] == "[data-qa='ok']", (
        "the other three test-id spellings are not read: %r" % (got,))
    assert got["aria"] == "[aria-label='Close']"
    assert got["nameWins"] == "input[name='q']", (
        "a test id outranks the name, so the handle stopped being the field "
        "the server will read: %r" % (got,))
    assert got["nothing"] is None, (
        "an element with nothing to address it by got a selector anyway, which "
        "is how a click lands on the wrong node: %r" % (got,))


def test_a_selector_that_matches_several_is_numbered_from_one():
    """⛔ THE DEFECT THIS EXISTS FOR IS NOT AN ERROR, IT IS A QUIET
    SUBSTITUTION. 88.3% of elements carried a handle and only 47.6% reached
    their element ALONE; for the rest Playwright acts on the first match, so a
    model aiming at the third of five identical links clicks the first and is
    told it worked.

    Known-bad, three: drop the wrapping and answer the bare selector; count
    from zero; or look the element up in the filtered list rather than in the
    whole document.
    """
    got = handles("""
      const a = node('a', {}), b = node('a', {}), c = node('a', {});
      DOC = {"a[href='/dup']": [a, b, c]};
      const stranger = node('a', {});
      process.stdout.write(JSON.stringify({
        first: handle(a, '/dup').sel,
        third: handle(c, '/dup').sel,
        absent: handle(stranger, '/dup'),
      }));
    """)
    assert got["first"] == ":nth-match(a[href='/dup'], 1)", (
        "a selector matching three nodes was handed out bare: %r" % (got,))
    assert got["third"] == ":nth-match(a[href='/dup'], 3)", (
        "the index is not the element's own position, counted from one: %r" % (got,))
    assert got["absent"] is None, (
        "an element the document does not hold was given a number anyway, "
        "which addresses somebody else: %r" % (got,))


def test_a_quote_or_a_backslash_in_a_value_does_not_break_out_of_the_selector():
    """A name is whatever the page's author typed, and it is being pasted into
    a quoted CSS string. Single quotes are used inside the selector because the
    answer is about to be serialized as JSON, where every double quote costs
    two characters.

    Known-bad: drop either replace in `attr`. The selector then ends early and
    matches nothing, or is a syntax error, and the tool reports no element at a
    place where there plainly is one.
    """
    got = handles("""
      const quoted = node('input', {name: "e'mail"});
      const slashed = node('input', {name: 'a' + String.fromCharCode(92) + 'b'});
      DOC = {}; DOC[handleBase(quoted)] = [quoted]; DOC[handleBase(slashed)] = [slashed];
      function handleBase(el){
        return el.tagName.toLowerCase() + "[name='" + attr(el.name) + "']";
      }
      process.stdout.write(JSON.stringify({
        quoted: handle(quoted, undefined).sel,
        slashed: handle(slashed, undefined).sel,
      }));
    """)
    bs = chr(92)
    assert got["quoted"] == "input[name='e" + bs + "'mail']", (
        "a single quote in a value closes the selector early: %r" % (got,))
    assert got["slashed"] == "input[name='a" + bs + bs + "b']", (
        "a backslash in a value is not doubled, so CSS eats the next "
        "character: %r" % (got,))


def test_an_href_that_addresses_nothing_is_not_a_handle():
    """`#` and `javascript:` are what a page writes when the link is wired by
    script, so they name every such link on the page at once.

    Known-bad: return `h` unchanged. Every scripted link on a page then shares
    one selector, and the numbering above cannot save it - the elements are not
    the same set the document returns for that href.
    """
    got = handles("""
      process.stdout.write(JSON.stringify({
        real: useful('/x') || null,
        hash: useful('#') || null,
        script: useful('javascript:void(0)') || null,
        empty: useful('') || null,
      }));
    """)
    assert got["real"] == "/x"
    assert got["hash"] is None and got["script"] is None and got["empty"] is None, (
        "a placeholder href was accepted as a handle: %r" % (got,))
