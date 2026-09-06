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

from invisible_playwright_mcp import server
from invisible_playwright_mcp.registry import SessionRegistry


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

    reg = SessionRegistry(factory=_Recording, defaults=_explode)
    monkeypatch.setattr(server, "registry", reg)
    return reg


async def test_with_nothing_running_it_says_so(registry):
    answer = await server.session_status()

    assert "no browser is running" in answer
    assert "session_start" in answer, "it does not say how to choose who to be"


async def test_asking_starts_nothing(registry):
    """⛔ The load-bearing one. The fixture's default factory raises, so a
    session_status that resolved a plan fails here rather than quietly launching
    a browser - and, with a profile configured, quietly writing an identity into
    it as the side effect of a question."""
    await server.session_status()

    assert registry.peek() is None, "asking who we are started a browser"


async def test_it_reports_the_running_identity(registry):
    await registry.restart(seed=4242, headless=True,
                           proxy={"server": "socks5://exit-a.invalid:1080"},
                           profile_dir="C:/tmp/acct-a")

    answer = await server.session_status()

    assert "4242" in answer
    assert "socks5://exit-a.invalid:1080" in answer
    assert "C:/tmp/acct-a" in answer
    assert "tab-1" in answer and "example.invalid" in answer


async def test_it_reports_the_identity_of_a_browser_that_died(registry):
    """The case that made this tool necessary. After a crash the config is still
    known, so the answer is who the next tool will come back as - not silence."""
    await registry.restart(seed=4242, headless=True)
    await registry.drop()

    answer = await server.session_status()

    assert "4242" in answer, "a dead browser lost the identity it will come back as"
    assert "not up" in answer


async def test_it_never_prints_a_proxy_password(registry):
    """A status line is the most quoted string in this surface: it goes into
    transcripts, bug reports and pasted logs."""
    await registry.restart(seed=1, headless=True,
                           proxy={"server": "socks5://exit-a.invalid:1080",
                                  "username": "u", "password": "hunter2"})

    assert "hunter2" not in await server.session_status()
