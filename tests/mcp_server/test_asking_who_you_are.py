"""Being able to ASK who is browsing, which for a long time was impossible.

⛔ THE IDENTITY WAS REPORTED EXACTLY ONCE, in the return value of `session_start`
- a call the tool descriptions explicitly say you do not have to make. So on the
path the surface itself recommends, a model had no way at all to learn its own
seed, its exit or its profile, and `identity.py` promised in capitals that a
drawn seed is ALWAYS reported while being unreachable from that path.

Three things have to hold, and the third is the one that is easy to get wrong:

  1. with a session running it reports the identity, the exit and the profile;
  2. with nothing running it says so, rather than inventing an answer;
  3. it STARTS NOTHING. A tool that launches a browser to answer "who am I"
     changes the thing it was asked about, and would draw and persist an
     identity as a side effect of a question.
"""
from __future__ import annotations

import pytest

from aihawk.mcp import server
from aihawk.mcp.registry import BrowserRegistry


class _Recording:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._browser = None
        self._context = object()

    async def start(self):
        pass

    async def close(self):
        pass

    async def describe_pages(self):
        return [{"id": "tab-1", "active": True, "url": "https://example.invalid/x",
                 "title": "X"}]


@pytest.fixture
def registry(monkeypatch):
    """A registry whose default would be loud if it were ever consulted."""
    def _explode():
        raise AssertionError("session_status resolved a plan, so it is not read only")

    reg = BrowserRegistry(factory=_Recording, defaults=_explode)
    monkeypatch.setattr(server, "registry", reg)
    return reg


#: Where a caller that names no browser is filed. The tests below put a session
#: there BY HAND, so they have to spell the key the way the tools do or they set
#: up one browser and then ask about another. Two of them went red the day the
#: key was composed, which was the honest outcome; the third asserted that a
#: password does not appear in the answer and went on passing, over an answer
#: that had become "no browser is running yet". A test that stops reaching its
#: subject does not report anything.
HERE = server.addressed()


async def test_with_nothing_running_it_says_so(registry):
    answer = await server.browser_status()

    assert "no browser is running" in answer
    assert "browser_open" in answer, "it does not say how to choose who to be"


async def test_asking_starts_nothing(registry):
    """⛔ The load-bearing one. The fixture's default factory raises, so a
    browser_status that resolved a plan fails here rather than quietly launching
    a browser - and, with a profile configured, quietly writing an identity into
    it as the side effect of a question."""
    await server.browser_status()

    # Every key, not just the one it would have used: a browser started under
    # any address at all is a browser this tool was not supposed to start.
    assert registry.ids() == [], "asking who we are started a browser"


async def test_it_reports_the_running_identity(registry):
    await registry.restart(HERE, seed=4242, headless=True,
                           proxy={"server": "socks5://exit-a.invalid:1080"},
                           profile_dir="C:/tmp/acct-a")

    answer = await server.browser_status()

    assert "4242" in answer
    assert "socks5://exit-a.invalid:1080" in answer
    assert "C:/tmp/acct-a" in answer
    assert "example.invalid" in answer, "it does not say where the browser is"
    # ⛔ THE PAGE ID IS DELIBERATELY ABSENT SINCE 2026-09-11. It used to report
    # `tab-1 https://...`, which was a vocabulary a caller could act on while
    # the tab tools existed. They are gone: there is no tool that takes a page
    # id, so printing one offers a handle to something nothing accepts, and a
    # model that reads it will spend a turn looking for the tool that uses it.
    assert "tab-1" not in answer, (
        "the status hands back a page id no tool takes any more: %r" % answer)


async def test_it_reports_the_identity_of_a_browser_that_died(registry):
    """The case that made this tool necessary. After a crash the config is still
    known, so the answer is who the next tool will come back as - not silence."""
    await registry.restart(HERE, seed=4242, headless=True)
    await registry.drop(HERE)

    answer = await server.browser_status()

    assert "4242" in answer, "a dead browser lost the identity it will come back as"
    assert "not up" in answer


async def test_it_never_prints_a_proxy_password(registry):
    """A status line is the most quoted string in this surface: it goes into
    transcripts, bug reports and pasted logs."""
    await registry.restart(HERE, seed=1, headless=True,
                           proxy={"server": "socks5://exit-a.invalid:1080",
                                  "username": "u", "password": "hunter2"})

    answer = await server.browser_status()
    # The subject is checked before the absence: "hunter2 is not in this string"
    # is true of every string that is not about a proxied session, so without
    # this line the test passes hardest when it has stopped testing anything.
    assert "exit-a.invalid" in answer, (
        "the answer is not about the proxied session, so finding no password "
        "in it means nothing: %r" % answer)
    assert "hunter2" not in answer
