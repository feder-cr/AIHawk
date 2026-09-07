"""The package must accept an OpenRouter key and nothing else.

These tests pin the "OpenRouter only" requirement at three levels:

1. the pure resolvers in ``aihawk.llm`` (key, model) - which environment
   variables they read and which they must never read;
2. the constructed client object (base URL, api_key) under an environment
   deliberately loaded with OpenAI variables;
3. the bytes that actually leave the process - a real
   ``chat.completions.create`` against a local stub server, so the assertion is
   on the outgoing ``Authorization`` header rather than on an attribute that
   merely looks right.

Level 3 exists because level 2 is not sufficient: ``client.api_key`` can hold
the caller's key while the request carries a different one. That is exactly
what happens today, and the section "KNOWN DEFECTS" at the bottom of this file
records it with ``xfail(strict=True)`` so the suite reports the hole instead of
hiding it, and turns red the moment somebody fixes it.

No browser and no MCP server is started here; every test in this file is safe
to run at any time.
"""
from __future__ import annotations

import json
import os
import re
import socketserver
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest

from aihawk import llm
from aihawk.llm import (
    APP_TITLE,
    APP_URL,
    BASE_URL,
    DEFAULT_MODEL,
    make_client,
    resolve_key,
    resolve_model,
)

# Environment variables that must never influence this package. OPENAI_* are
# read by the openai SDK itself; the rest stand in for other vendors.
FOREIGN_ENV = {
    "OPENAI_API_KEY": "sk-openai-from-env",
    "OPENAI_BASE_URL": "https://api.openai.com/v1",
    "OPENAI_ORG_ID": "org-from-env",
    "OPENAI_PROJECT_ID": "proj-from-env",
    "OPENAI_ADMIN_KEY": "sk-admin-from-env",
    "ANTHROPIC_API_KEY": "sk-ant-from-env",
    "OPENROUTER_KEY": "near-miss-name",
    "OR_API_KEY": "near-miss-name",
    "AIHAWK_KEY": "near-miss-name",
}


@pytest.fixture
def clean_env(monkeypatch):
    """Every variable this package or the SDK could read is removed.

    Without this, a machine that happens to export OPENAI_API_KEY would give a
    control test a passing result for the wrong reason.
    """
    for name in list(os.environ):
        if name.startswith(("OPENAI_", "OPENROUTER", "AIHAWK_", "ANTHROPIC_")):
            monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def foreign_env(clean_env):
    """A clean environment, then loaded with every foreign vendor variable."""
    for name, value in FOREIGN_ENV.items():
        clean_env.setenv(name, value)
    return clean_env


class _StubOpenRouter:
    """A local HTTP server that answers one chat completion and records headers.

    It exists so a test can assert what the client actually SENDS. Asserting
    ``client.api_key`` alone would pass even if the request went out with a
    different credential, which is a failure mode this package really has.
    """

    def __init__(self):
        self.headers: dict[str, str] = {}
        recorder = self

        class _Handler(BaseHTTPRequestHandler):
            # HTTP/1.0 (the default) so the connection is closed after the
            # single response; a kept-alive connection blocks server shutdown.

            def do_POST(self):  # noqa: N802 - name fixed by BaseHTTPRequestHandler
                recorder.headers = {k.lower(): v for k, v in self.headers.items()}
                length = int(self.headers.get("content-length") or 0)
                self.rfile.read(length)
                body = json.dumps({
                    "id": "stub", "object": "chat.completion", "created": 0,
                    "model": "stub-model",
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }],
                }).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(body)))
                self.send_header("connection", "close")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):  # keep pytest output clean
                pass

        socketserver.TCPServer.allow_reuse_address = True
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        return False

    @property
    def url(self) -> str:
        return "http://127.0.0.1:%d/v1" % self._server.server_address[1]


def _send_one_completion(key: str, stub: _StubOpenRouter) -> None:
    """Build a client exactly as the package does, then aim a copy at the stub.

    ``copy`` keeps the api_key and the headers the constructor computed, so the
    request the stub receives is the request OpenRouter would have received.
    The real base URL is asserted separately, on the un-copied client.
    """
    client = make_client(key).copy(base_url=stub.url)
    client.chat.completions.create(
        model="stub-model", messages=[{"role": "user", "content": "hi"}]
    )


# --------------------------------------------------------------------------
# resolve_key
# --------------------------------------------------------------------------

def test_explicit_key_wins_over_the_environment():
    """Known-bad: swapping the operands to ``env.get(...) or explicit``."""
    assert resolve_key("from-arg", {"OPENROUTER_API_KEY": "from-env"}) == "from-arg"


def test_environment_key_is_used_when_no_argument_is_given():
    """Known-bad: dropping the env lookup, leaving only the argument."""
    assert resolve_key(None, {"OPENROUTER_API_KEY": "from-env"}) == "from-env"


def test_missing_key_raises_and_names_both_ways_to_supply_one():
    """The message is the whole user interface for this failure.

    Known-bad: a message reworded to name only the flag, or only the variable,
    which sends a user looking in the wrong place.
    """
    with pytest.raises(RuntimeError) as excinfo:
        resolve_key(None, {})
    message = str(excinfo.value)
    assert "--openrouter-key" in message
    assert "OPENROUTER_API_KEY" in message


def test_no_other_vendor_variable_is_accepted_as_a_key():
    """OpenRouter only: an environment full of other keys is still no key.

    Known-bad: ``env.get("OPENROUTER_API_KEY") or env.get("OPENAI_API_KEY")``,
    a one-word edit that would silently make the package accept an OpenAI key.
    """
    with pytest.raises(RuntimeError):
        resolve_key(None, dict(FOREIGN_ENV))


def test_empty_string_is_not_a_key():
    """An empty value must never be resolved into a key.

    Known-bad: ``if explicit is not None`` instead of a truthiness test, which
    would return "" and produce an unauthenticated request against OpenRouter
    that fails far from its cause.
    """
    with pytest.raises(RuntimeError):
        resolve_key("", {})
    with pytest.raises(RuntimeError):
        resolve_key(None, {"OPENROUTER_API_KEY": ""})
    with pytest.raises(RuntimeError):
        resolve_key("", {"OPENROUTER_API_KEY": ""})


def test_empty_explicit_key_falls_back_to_the_environment():
    """Documented consequence of the truthiness test above, pinned on purpose.

    An empty ``--openrouter-key`` is treated as "not supplied", so a key in the
    environment is used. This is deliberate and benign (the run proceeds with a
    valid key), but it is a real branch and it should not change unnoticed.
    """
    assert resolve_key("", {"OPENROUTER_API_KEY": "from-env"}) == "from-env"


def test_llm_reads_exactly_two_environment_variables():
    """Structural pin on the module source: no third source of configuration.

    Known-bad: adding ``env.get("OPENAI_API_KEY")`` or an ``os.environ`` read
    anywhere in llm.py. A behavioural test can only catch the names it thought
    to try; this catches any new name at all.
    """
    source = Path(llm.__file__).read_text(encoding="utf-8")
    names = set(re.findall(r"""env\.get\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']""", source))
    assert names == {"OPENROUTER_API_KEY", "AIHAWK_MODEL"}
    assert "os.environ" not in source
    assert "getenv" not in source


# --------------------------------------------------------------------------
# make_client: base URL and key
# --------------------------------------------------------------------------

def test_base_url_constant_points_at_openrouter_over_https():
    """Known-bad: BASE_URL edited to api.openai.com, or to plain http."""
    parsed = urlparse(BASE_URL)
    assert parsed.scheme == "https"
    assert parsed.netloc == "openrouter.ai"


def test_no_other_provider_host_appears_in_the_module():
    """Known-bad: a second, conditional base URL sneaking in beside the first."""
    source = Path(llm.__file__).read_text(encoding="utf-8")
    for host in ("api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com"):
        assert host not in source


def test_client_base_url_is_openrouter_even_with_openai_base_url_set(foreign_env):
    """OPENAI_BASE_URL must not redirect our traffic.

    The openai SDK reads OPENAI_BASE_URL only when base_url is not passed, and
    make_client always passes it. Known-bad: dropping the ``base_url=`` keyword
    from the OpenAI(...) call, which would send every request to whatever host
    the environment names. Asserted against the BASE_URL constant, not a copy
    of its value.
    """
    client = make_client("or-test-key")
    assert str(client.base_url).rstrip("/") == BASE_URL.rstrip("/")
    assert urlparse(str(client.base_url)).netloc == "openrouter.ai"


def test_client_api_key_is_the_given_one_with_openai_api_key_set(foreign_env):
    """OPENAI_API_KEY must not be picked up.

    Known-bad: dropping the ``api_key=`` keyword, after which the SDK falls
    back to OPENAI_API_KEY and the package would happily authenticate with a
    foreign vendor's credential.
    """
    client = make_client("or-test-key")
    assert client.api_key == "or-test-key"
    assert client.api_key != FOREIGN_ENV["OPENAI_API_KEY"]
    assert client.auth_headers == {"Authorization": "Bearer or-test-key"}


def test_a_real_request_carries_the_given_key(clean_env):
    """The control for the header assertions: on a clean environment the key
    the caller passed is the key that goes on the wire.

    This test is also what makes the xfail below meaningful: it proves the stub
    can observe the Authorization header and that a wrong key would be visible.
    """
    with _StubOpenRouter() as stub:
        _send_one_completion("or-control-key", stub)
        assert stub.headers.get("authorization") == "Bearer or-control-key"


# --------------------------------------------------------------------------
# make_client: app attribution
# --------------------------------------------------------------------------

def test_a_real_request_carries_the_app_attribution_headers(clean_env):
    """OpenRouter groups the /apps rankings by these two headers and nothing else.

    Asserted on the wire rather than on ``client.default_headers``, for the same
    reason the key is: an attribute can hold a value the request never sends.

    Known-bad: dropping ``default_headers`` from the OpenAI(...) call. Nothing
    fails when it goes - no error, no changed answer - the traffic simply
    becomes anonymous and the app leaves the rankings, which is why it needs a
    test rather than an occasional look at the site.
    """
    with _StubOpenRouter() as stub:
        _send_one_completion("or-control-key", stub)
        assert stub.headers.get("http-referer") == APP_URL
        assert stub.headers.get("x-title") == APP_TITLE


def test_app_attribution_survives_a_foreign_environment(foreign_env):
    """Another vendor's variables must not displace our own identification.

    Known-bad: passing the two headers per-request at one call site instead of
    on the client, which leaves every other call site anonymous.
    """
    with _StubOpenRouter() as stub:
        _send_one_completion("or-real-key", stub)
        assert stub.headers.get("http-referer") == APP_URL
        assert stub.headers.get("x-title") == APP_TITLE


def test_app_attribution_constants_are_a_url_and_a_name():
    """Known-bad: an empty title, or a referer that is not a URL. OpenRouter
    accepts both without complaint and produces an unusable rankings entry."""
    parsed = urlparse(APP_URL)
    assert parsed.scheme == "https"
    assert parsed.netloc == "github.com"
    assert APP_TITLE.strip() == APP_TITLE
    assert APP_TITLE != ""


# --------------------------------------------------------------------------
# resolve_model
# --------------------------------------------------------------------------

def test_model_explicit_wins_over_the_environment():
    """Known-bad: swapping the operands so the environment wins."""
    assert resolve_model("m-arg", {"AIHAWK_MODEL": "m-env"}) == "m-arg"


def test_model_environment_used_when_no_argument():
    """Known-bad: dropping the AIHAWK_MODEL lookup."""
    assert resolve_model(None, {"AIHAWK_MODEL": "m-env"}) == "m-env"


def test_model_falls_back_to_the_default_constant():
    """Asserted against DEFAULT_MODEL itself, never a hardcoded copy.

    Known-bad: a literal default inlined in resolve_model that drifts from the
    exported constant, so callers importing DEFAULT_MODEL disagree with what
    the package actually asks for.
    """
    assert resolve_model(None, {}) == DEFAULT_MODEL
    assert isinstance(DEFAULT_MODEL, str) and DEFAULT_MODEL.strip() == DEFAULT_MODEL
    assert DEFAULT_MODEL != ""


def test_model_ignores_other_environment_names():
    """Known-bad: an added ``or env.get("OPENAI_MODEL")`` fallback."""
    noisy = dict(FOREIGN_ENV)
    noisy.update({"OPENAI_MODEL": "gpt-from-env", "MODEL": "m-from-env"})
    assert resolve_model(None, noisy) == DEFAULT_MODEL


def test_empty_model_falls_through_to_the_default():
    """Known-bad: ``if explicit is not None``, which would ask OpenRouter for
    the model named "" and get a confusing 404 instead of the default."""
    assert resolve_model("", {}) == DEFAULT_MODEL
    assert resolve_model(None, {"AIHAWK_MODEL": ""}) == DEFAULT_MODEL


# --------------------------------------------------------------------------
# KNOWN DEFECTS
#
# Each test below asserts the guarantee the owner asked for and fails today.
# They are xfail(strict=True) so the suite stays honest: they are reported as
# xfailed, never as passed, and the day the defect is fixed they XPASS, which
# strict mode turns into a failure so somebody removes the marker.
# --------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason="DEFECT: OPENAI_CUSTOM_HEADERS in the environment replaces the "
           "outgoing Authorization header, so the request leaves with a "
           "credential the caller never passed. Fix: make_client should pass "
           "default_headers={'Authorization': f'Bearer {key}'}, which makes "
           "the SDK drop an env-supplied Authorization.",
)
def test_environment_cannot_replace_the_outgoing_authorization_header(clean_env):
    """The key on the wire must be the key the caller gave, whatever the env.

    The openai SDK correctly ignores OPENAI_API_KEY and OPENAI_BASE_URL when
    both are passed explicitly, but it merges OPENAI_CUSTOM_HEADERS into
    default_headers, and default_headers is applied AFTER the api_key derived
    Authorization. Measured with this same stub: the request goes out as
    "Bearer sk-hijacked" while client.api_key still reads "or-real-key", so any
    test that only inspects the attribute reports a false green.
    """
    clean_env.setenv("OPENAI_CUSTOM_HEADERS", "Authorization: Bearer sk-hijacked")
    with _StubOpenRouter() as stub:
        _send_one_completion("or-real-key", stub)
        assert stub.headers.get("authorization") == "Bearer or-real-key"


@pytest.mark.xfail(
    strict=True,
    reason="DEFECT (minor): OPENAI_ORG_ID and OPENAI_PROJECT_ID from the "
           "environment are sent as OpenAI-Organization / OpenAI-Project "
           "headers to openrouter.ai. Fix: pass those headers as Omit() in "
           "default_headers, or pass organization/project explicitly.",
)
def test_no_openai_account_identifiers_are_sent_to_openrouter(clean_env):
    """An unrelated OpenAI account id must not leak to a third party.

    Known-bad is the current behaviour itself: with OPENAI_ORG_ID set, the
    request to OpenRouter carries it verbatim.
    """
    clean_env.setenv("OPENAI_ORG_ID", "org-from-env")
    clean_env.setenv("OPENAI_PROJECT_ID", "proj-from-env")
    with _StubOpenRouter() as stub:
        _send_one_completion("or-real-key", stub)
        assert "openai-organization" not in stub.headers
        assert "openai-project" not in stub.headers


@pytest.mark.xfail(
    strict=True,
    reason="DEFECT (minor): a key with surrounding whitespace is returned "
           "verbatim; a trailing newline (the usual result of a copy-paste or "
           "of $(cat keyfile)) then fails as APIConnectionError 'Connection "
           "error.', which names neither the key nor the whitespace. Fix: "
           "strip the resolved key, or refuse it with the usual message.",
)
def test_a_key_with_surrounding_whitespace_does_not_reach_the_transport():
    """Either fix is accepted: strip it, or reject it with a clear error.

    Rejecting raises RuntimeError, which this test treats as a pass; anything
    returned must be free of the whitespace that breaks header construction.
    """
    try:
        key = resolve_key(" or-real-key\n", {})
    except RuntimeError:
        return
    assert key == key.strip()
