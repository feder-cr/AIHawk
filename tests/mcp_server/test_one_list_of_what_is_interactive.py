"""What a caller can act on is declared once and read by both readers.

⛔ IT WAS DECLARED TWICE, IN TWO LANGUAGES, AND THEY DISAGREED. `clean.py` held
nineteen roles for the sieve; the snapshot's selector held seven, typed out by
hand inside a JavaScript string in another module. Nothing could compare them,
so nothing did.

Measured 2026-09-15 by driving a page of ARIA controls through the real server:
a `role=combobox` and a `role=slider` with no `tabindex` came back from
`browser_read_html` and were absent from `browser_snapshot` - which is the tool
the instructions name as the way to find something to click. Seven controls in
all, invisible to the rung the ladder starts on, while the sieve saw every one.

The two need the same list with ONE difference, and the difference is now
NAMED rather than left to a second list to imply: roles whose members come in
hundreds are kept by the sieve and left out of the inventory.
"""
from __future__ import annotations

import re

from invisible_playwright_mcp.mcp import actions, clean


def selector_in_the_page() -> str:
    """The selector string as it reaches the browser, read back out of the
    JavaScript the snapshot actually evaluates.

    Read from the emitted script rather than from the constant it was built
    from: the point of this file is that ONE declaration reaches the page, and
    comparing the constant to itself would prove nothing.
    """
    found = re.search(r"const SEL = \"(.*?)\";", actions.SNAPSHOT_JS)
    assert found, "the snapshot no longer carries a SEL it built from Python"
    return found.group(1)


def roles_in(selector: str) -> set:
    return set(re.findall(r"\[role='([a-z]+)'\]", selector))


def test_the_snapshot_asks_the_page_for_every_role_the_sieve_knows():
    """Known-bad: type a role list into the JavaScript again, or drop one role
    from `CONTROL_ROLES` - the two stop agreeing and this says which."""
    asked = roles_in(selector_in_the_page())
    assert asked == set(clean.CONTROL_ROLES), (
        "the snapshot asks for a different set of roles than the one declared: "
        "missing %s, extra %s"
        % (sorted(set(clean.CONTROL_ROLES) - asked), sorted(asked - set(clean.CONTROL_ROLES))))


def test_the_controls_that_were_invisible_are_asked_for_now():
    """The seven measured on 2026-09-15, named one by one.

    A set comparison alone would go green if somebody shrank both sides, and
    these are the elements the defect was actually about.

    Known-bad: remove any of these from `CONTROL_ROLES`.
    """
    asked = roles_in(selector_in_the_page())
    for role in ("combobox", "slider", "textbox", "searchbox", "spinbutton",
                 "menuitemcheckbox", "menuitemradio", "treeitem", "columnheader",
                 "listbox"):
        assert role in asked, (
            "role=%s is a control a caller acts on, and the snapshot does not "
            "ask the page for it" % role)


def test_the_roles_left_out_are_the_ones_that_come_in_hundreds():
    """The snapshot leaves `option` and `gridcell` out ON PURPOSE, for the
    reason its own docstring measured: one country select contributes about
    two hundred option nodes and fills the answer.

    ⛔ AND THE SIEVE STILL KEEPS THEM. Leaving them out of the inventory must
    not turn into deleting them from the page, which would break the invariant
    at the top of `clean.py`.

    ⛔ THE TWO NAMES ARE WRITTEN OUT, and the first version of this did not
    write them: it asked whether anything in `MANY_PER_WIDGET_ROLES` was in the
    selector, which a mutation satisfies by MOVING the role into the other set.
    Measured on the known-bad bench, that one survived. A gate held against a
    set the change can edit is held against nothing.

    Known-bad, three: put either name in the selector, and the inventory
    floods; take either out of `INTERACTIVE_ROLES`, and the sieve deletes real
    controls.
    """
    asked = roles_in(selector_in_the_page())
    for role in ("option", "gridcell"):
        assert role not in asked, (
            "role=%s is inventoried now, and one widget of them fills the "
            "answer before the form somebody was looking for appears" % role)
        assert role in clean.INTERACTIVE_ROLES, (
            "%s is left out of the inventory AND out of the sieve, so the "
            "page loses it" % role)
        assert role in clean.MANY_PER_WIDGET_ROLES, (
            "%s stopped being declared as a collection member, so the reason "
            "it is not inventoried is no longer written anywhere" % role)


def test_no_second_list_of_roles_is_written_anywhere():
    """The class, not the instance: a role name spelled inside the snapshot's
    JavaScript is a second list starting.

    Known-bad: add `'[role="button"]'` back into the script.
    """
    body = actions.SNAPSHOT_JS
    sel = selector_in_the_page()
    rest = body.replace(sel, "")
    strays = sorted(set(re.findall(r"role=[\"']([a-z]+)[\"']", rest)))
    assert not strays, (
        "roles are named inside the snapshot script again, beside the list it "
        "is handed: %s" % strays)


def test_the_tags_and_the_fallbacks_survived_the_move():
    """The selector is not only roles. A move that quietly dropped `a[href]`
    or the tabindex fallback would pass every assertion above.

    Known-bad: drop any of these from `SNAPSHOT_CSS`.
    """
    sel = selector_in_the_page()
    for piece in ("input", "select", "textarea", "button", "a[href]",
                  "[onclick]", "[tabindex]:not([tabindex='-1'])",
                  "[contenteditable='true']"):
        assert piece in sel, "the snapshot stopped asking for %r" % piece
