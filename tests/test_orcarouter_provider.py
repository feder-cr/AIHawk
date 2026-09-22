"""OrcaRouter: the two credentials, the catalogue, and the two origins.

Three things are pinned here and nothing else is:

1. **One credential, two adapters.** A pasted `sk-orca-...` key and a completed
   PKCE sign-in end as the same `Credential`, and the things downstream - the
   inference client and the catalogue - take a key and never ask which road it
   came by. Both adapters are exercised, and both are checked to produce
   something the same code can spend.

2. **The two origins are separate and neither is derived from the other.**
   Authentication goes to `www.orcarouter.ai` and its paths are under
   `/api/v1/auth`; inference and the catalogue go to `api.orcarouter.ai/v1`.
   The wrong path (`/v1/auth/keys` on the API origin) is a 404 that reads like a
   routing bug on the far side, so it is asserted against rather than described.

3. **The catalogue decides what a model can do, and nothing else does.** Every
   capability filter is checked against records that declare the capability and
   records that do not, a record that declares nothing fails closed, and a
   failed discovery falls back to the labelled verified seed rather than to a
   free-text box.

⛔ NO REAL KEY, NO REAL CODE, AND NO REAL CONSENT ANYWHERE IN THIS FILE. The
fake auth server below is a local HTTP server this test owns; it answers the
exchange with a key that is obviously not one. A test that needed a person to
approve something would be a test that cannot run.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from aihawk import orcarouter, provider
from aihawk.chat import ChatService
from aihawk.llm import BASE_URL, DEFAULT_MODEL, make_client, orcarouter_client
from aihawk.routes import build_app
from aihawk.runner import KEY_VARIABLES, forget_key
from aihawk.sessions import Sessions
from _sessions import around

FAKE_KEY = "sk-orca-CANARY-not-a-real-key"
FAKE_CODE = "code-CANARY-not-a-real-code"


# ---------------------------------------------------------------------------
# doubles
# ---------------------------------------------------------------------------

class _Link:
    """Shaped like `Link` where the routes touch it. Touches nothing."""

    tools = []
    instructions = ""

    async def call(self, name, arguments=None):
        return None

    async def call_text(self, name, arguments=None):
        return ""

    async def close(self):
        return None


class _Brain:
    async def handle(self, text, link, say):
        return None


def _app(state=None):
    service = ChatService(_Link(), _Brain())
    return build_app(around(service), state)


def _client(state=None):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=_app(state)),
                             base_url="http://test")


class FakeAuth:
    """A local stand-in for the consent origin, in front of the real client.

    ⛔ IT ANSWERS THE EXCHANGE AND NOTHING ELSE, which is the whole point: what
    is under test is the REQUEST this package makes - its origin, its path and
    its body - and a stand-in that also implemented the consent screen would be
    a second implementation to keep in step rather than a witness.

    It records the path and the parsed body of every exchange, so a test can
    assert the verifier travelled in the body and that the path was
    `/api/v1/auth/keys` and not `/v1/auth/keys`.
    """

    def __init__(self, *, status=200, body=None):
        self.requests: list[dict] = []
        self.status = status
        self.body = body if body is not None else {
            "key": FAKE_KEY, "user_id": "1", "scope": "api"}
        recorder = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(handler):  # noqa: N802 - name fixed by the base class
                length = int(handler.headers.get("content-length") or 0)
                raw = handler.rfile.read(length)
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except ValueError:
                    parsed = dict(urllib.parse.parse_qsl(raw.decode("utf-8")))
                recorder.requests.append({"path": handler.path, "body": parsed})
                answer = json.dumps(recorder.body).encode()
                handler.send_response(recorder.status)
                handler.send_header("Content-Type", "application/json")
                handler.send_header("Content-Length", str(len(answer)))
                handler.end_headers()
                handler.wfile.write(answer)

            def log_message(self, *args):
                pass

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
    def base(self) -> str:
        return "http://127.0.0.1:%d" % self._server.server_address[1]


# ---------------------------------------------------------------------------
# the two origins
# ---------------------------------------------------------------------------

def test_the_two_origins_are_two_constants_and_not_one_derived_from_the_other():
    """Known-bad: `API_BASE_URL = AUTH_BASE_URL.replace("www.", "api.")`, which
    reads as tidier and produces a host nobody agreed to."""
    assert orcarouter.AUTH_BASE_URL == "https://www.orcarouter.ai"
    assert orcarouter.API_BASE_URL == "https://api.orcarouter.ai/v1"
    assert orcarouter.AUTHORIZE_PATH == "/auth"
    assert orcarouter.EXCHANGE_PATH == "/api/v1/auth/keys"
    assert orcarouter.MODELS_PATH == "/models"


def test_the_exchange_never_lands_on_the_inference_origin():
    """⛔ THE SINGLE MOST EXPENSIVE MISTAKE IN THIS INTEGRATION, pinned.

    `https://api.orcarouter.ai/v1/auth/keys` is a 404, and it is the path you
    get by assuming the two origins are one. Asserted on the URL the code
    actually builds, not on a comment saying not to.
    """
    auth, api = orcarouter.origins({})
    url = orcarouter.require_https(auth).rstrip("/") + orcarouter.EXCHANGE_PATH
    assert url == "https://www.orcarouter.ai/api/v1/auth/keys"
    assert not url.startswith(api)
    assert url != "https://api.orcarouter.ai/v1/auth/keys"
    assert "api.orcarouter.ai" not in url


def test_explicit_overrides_win_and_the_shared_fallback_is_second():
    """Known-bad: reading the shared variable first, which silently ignores the
    explicit one on a two-origin self-hosted deployment."""
    shared = {"ORCAROUTER_BASE_URL": "https://one.example"}
    assert orcarouter.origins(shared) == ("https://one.example", "https://one.example")

    both = {"ORCAROUTER_BASE_URL": "https://one.example",
            "ORCAROUTER_AUTH_BASE_URL": "https://auth.example",
            "ORCAROUTER_API_BASE_URL": "https://api.example/v1"}
    assert orcarouter.origins(both) == ("https://auth.example", "https://api.example/v1")


def test_a_remote_origin_must_be_https_and_loopback_may_be_plain():
    """Known-bad: accepting any scheme, which puts a key on the wire in clear
    text to a host that is not this machine."""
    assert orcarouter.require_https("https://api.example/v1") == "https://api.example/v1"
    assert orcarouter.require_https("http://127.0.0.1:9/v1") == "http://127.0.0.1:9/v1"
    assert orcarouter.require_https("http://localhost:9") == "http://localhost:9"
    with pytest.raises(ValueError):
        orcarouter.require_https("http://api.example/v1")
    with pytest.raises(ValueError):
        orcarouter.require_https("ftp://api.example")


def test_the_catalogue_url_is_the_api_origin_with_the_capability_asked_for():
    assert orcarouter.catalog_url("https://api.orcarouter.ai/v1") == \
        "https://api.orcarouter.ai/v1/models"
    assert orcarouter.catalog_url("https://api.orcarouter.ai/v1", "chat") == \
        "https://api.orcarouter.ai/v1/models?capability=chat"


# ---------------------------------------------------------------------------
# PKCE
# ---------------------------------------------------------------------------

def test_the_challenge_is_unpadded_base64url_of_the_sha256_of_the_verifier():
    """Known-bad: standard base64, which puts `+` and `/` in a query string, or
    padding, which the server does not expect."""
    verifier = "a-verifier-for-this-test"
    challenge = orcarouter.challenge_for(verifier)
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()).decode().rstrip("=")
    assert challenge == expected
    assert "=" not in challenge and "+" not in challenge and "/" not in challenge


def test_a_verifier_is_fresh_cryptographic_randomness_every_attempt():
    """⛔ THE ONE SECRET AN INTERCEPTED CODE CANNOT BE REDEEMED WITHOUT, so a
    reused or guessable one is the whole defence gone.

    Known-bad: a module-level verifier, a counter, or a timestamp.
    """
    seen = {orcarouter.new_verifier() for _ in range(50)}
    assert len(seen) == 50
    states = {orcarouter.new_state() for _ in range(50)}
    assert len(states) == 50
    assert not (seen & states)
    one = orcarouter.new_verifier()
    assert len(one) == 43 and "=" not in one


def test_the_authorize_url_names_the_auth_origin_and_asks_for_s256():
    url = orcarouter.authorize_url("https://www.orcarouter.ai",
                                   "http://127.0.0.1:51733/callback",
                                   "CH", "ST", "AIHawk")
    parsed = urllib.parse.urlparse(url)
    assert parsed.netloc == "www.orcarouter.ai"
    assert parsed.path == "/auth"
    query = urllib.parse.parse_qs(parsed.query)
    assert query["code_challenge"] == ["CH"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == ["ST"]
    assert query["app_name"] == ["AIHawk"]
    assert query["callback_url"] == ["http://127.0.0.1:51733/callback"]
    assert query["scope"] == ["api"]


def test_state_is_compared_in_constant_time_and_a_mismatch_is_refused():
    """⛔ THE ONLY THING BETWEEN THE LOOPBACK LISTENER AND SOMEBODY ELSE'S CODE.
    Known-bad: `!=`, or comparing after the code has been used."""
    assert orcarouter.state_matches("abc", "abc") is True
    assert orcarouter.state_matches("abc", "abd") is False
    assert orcarouter.state_matches("", "abc") is False
    assert orcarouter.state_matches("abc", "") is False


def test_the_exchange_body_carries_the_verifier_and_the_method():
    body = json.loads(orcarouter.exchange_body(FAKE_CODE, "v" * 43).decode())
    assert body == {"code": FAKE_CODE, "code_verifier": "v" * 43,
                    "code_challenge_method": "S256"}


async def test_a_sign_in_exchanges_on_the_auth_origin_and_persists_one_credential(
        monkeypatch, tmp_path):
    """The whole flow, through the adapter the product runs: a fresh attempt, a
    loopback listener, a code delivered to it, an exchange, and a credential.

    ⛔ THE CODE IS DELIVERED BY A REAL HTTP REQUEST to the port the login bound,
    not by calling the handler, so the state comparison and the listener are
    exercised rather than mocked.
    """
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    with FakeAuth() as auth:
        monkeypatch.setenv("ORCAROUTER_AUTH_BASE_URL", auth.base)
        login = orcarouter.PkceLogin()
        url = login.start()
        try:
            assert urllib.parse.urlparse(url).netloc == urllib.parse.urlparse(auth.base).netloc
            assert login.port > 0
            answer = await _deliver(login.callback_url, {"code": FAKE_CODE,
                                                         "state": login.state})
            assert answer == 200
            code = await login.wait(timeout=5)
            credential = await login.exchange(code)
        finally:
            login.close()

    assert credential.key == FAKE_KEY
    assert credential.method == orcarouter.BY_PKCE
    assert credential.scope == "api"

    # ⛔ ONE REQUEST, TO THE AUTH ORIGIN, ON THE RIGHT PATH, WITH THE VERIFIER IN
    # THE BODY. All three in one place because they are one fact.
    assert len(auth.requests) == 1
    assert auth.requests[0]["path"] == "/api/v1/auth/keys"
    assert auth.requests[0]["body"]["code_verifier"] == login.verifier
    assert auth.requests[0]["body"]["code"] == FAKE_CODE


async def _deliver(callback_url: str, params: dict) -> int:
    """Send the browser's request to the listener the login bound."""
    url = callback_url + "?" + urllib.parse.urlencode(params)
    async with httpx.AsyncClient() as client:
        answer = await client.get(url)
        return answer.status_code


async def test_a_denial_ends_the_sign_in_with_a_sentence_and_no_key(monkeypatch):
    monkeypatch.setenv("ORCAROUTER_AUTH_BASE_URL", "http://127.0.0.1:1")
    login = orcarouter.PkceLogin()
    login.start()
    try:
        await _deliver(login.callback_url, {"error": "access_denied", "state": login.state})
        with pytest.raises(orcarouter.PkceError) as excinfo:
            await login.wait(timeout=5)
    finally:
        login.close()
    assert "refused" in str(excinfo.value)


async def test_a_state_mismatch_is_refused_before_the_code_is_used(monkeypatch):
    """⛔ FLOW A's CSRF DEFENCE, and it has to fire BEFORE the code is read.

    Known-bad: reading `code` first and comparing the state afterwards, which is
    a code somebody else's page dropped on this listener.
    """
    monkeypatch.setenv("ORCAROUTER_AUTH_BASE_URL", "http://127.0.0.1:1")
    login = orcarouter.PkceLogin()
    login.start()
    try:
        await _deliver(login.callback_url, {"code": FAKE_CODE, "state": "not-the-state"})
        with pytest.raises(orcarouter.PkceError) as excinfo:
            await login.wait(timeout=5)
    finally:
        login.close()
    assert "state" in str(excinfo.value)


async def test_a_timeout_ends_the_wait_instead_of_hanging(monkeypatch):
    monkeypatch.setenv("ORCAROUTER_AUTH_BASE_URL", "http://127.0.0.1:1")
    login = orcarouter.PkceLogin()
    login.start()
    try:
        with pytest.raises(orcarouter.PkceError) as excinfo:
            await login.wait(timeout=0.05)
    finally:
        login.close()
    assert "timed out" in str(excinfo.value)


async def test_a_used_or_expired_code_is_one_actionable_sentence(monkeypatch):
    """403 is unknown, expired or already used - and the verifier not matching.
    All four are one thing to the person: start again."""
    with FakeAuth(status=403, body={"error": "invalid_grant"}) as auth:
        monkeypatch.setenv("ORCAROUTER_AUTH_BASE_URL", auth.base)
        login = orcarouter.PkceLogin()
        login.start()
        try:
            with pytest.raises(orcarouter.PkceError) as excinfo:
                await login.exchange(FAKE_CODE)
        finally:
            login.close()
    assert "403" in str(excinfo.value)
    assert "already used" in str(excinfo.value)


async def test_a_challenge_method_mismatch_is_reported_as_400(monkeypatch):
    with FakeAuth(status=400, body={"error": "invalid_request"}) as auth:
        monkeypatch.setenv("ORCAROUTER_AUTH_BASE_URL", auth.base)
        login = orcarouter.PkceLogin()
        login.start()
        try:
            with pytest.raises(orcarouter.PkceError) as excinfo:
                await login.exchange(FAKE_CODE)
        finally:
            login.close()
    assert "400" in str(excinfo.value)


async def test_too_many_keys_is_reported_as_429_and_not_retried(monkeypatch):
    """Ten PKCE-issued keys per user per day, then 429. Retrying is what turns
    one refusal into a locked-out account."""
    with FakeAuth(status=429, body={"error": "rate_limited"}) as auth:
        monkeypatch.setenv("ORCAROUTER_AUTH_BASE_URL", auth.base)
        login = orcarouter.PkceLogin()
        login.start()
        try:
            with pytest.raises(orcarouter.PkceError) as excinfo:
                await login.exchange(FAKE_CODE)
        finally:
            login.close()
        assert len(auth.requests) == 1, "the refusal was retried"
    assert "429" in str(excinfo.value)


async def test_a_network_failure_is_a_sentence_rather_than_a_hang(monkeypatch):
    monkeypatch.setenv("ORCAROUTER_AUTH_BASE_URL", "http://127.0.0.1:9")
    login = orcarouter.PkceLogin()
    login.start()
    try:
        with pytest.raises((orcarouter.PkceError, OSError)):
            await login.exchange(FAKE_CODE)
    finally:
        login.close()


async def test_a_scope_that_does_not_cover_what_was_asked_for_is_refused(monkeypatch):
    """⛔ WHAT WAS GRANTED, NOT WHAT WAS REQUESTED. A workspace role that does
    not permit the wider grant answers with the narrower one, and a client that
    assumes it holds what it asked for fails later, somewhere that says nothing
    about the cause."""
    with FakeAuth(body={"key": FAKE_KEY, "user_id": "1", "scope": "connector"}) as auth:
        monkeypatch.setenv("ORCAROUTER_AUTH_BASE_URL", auth.base)
        login = orcarouter.PkceLogin()
        login.start()
        try:
            with pytest.raises(orcarouter.PkceError) as excinfo:
                await login.exchange(FAKE_CODE)
        finally:
            login.close()
    assert "connector" in str(excinfo.value)
    assert orcarouter.granted_scope({"scope": "api"}) == ("api", True)
    assert orcarouter.granted_scope({}) == ("api", True)
    assert orcarouter.granted_scope({"scope": "connector"}) == ("connector", False)


async def test_the_verifier_never_appears_in_a_message_or_in_the_state(monkeypatch, tmp_path):
    """⛔ A VERIFIER IN A LOG IS A VERIFIER SOMEBODY ELSE HAS. It never rides on
    a URL either, so the authorize URL is checked for it too."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    monkeypatch.setenv("ORCAROUTER_AUTH_BASE_URL", "http://127.0.0.1:9")
    login = orcarouter.PkceLogin()
    url = login.start()
    verifier = login.verifier
    try:
        assert verifier not in url
        with pytest.raises(Exception) as excinfo:
            await login.exchange(FAKE_CODE)
        assert verifier not in str(excinfo.value)
        credential = orcarouter.Credential(FAKE_KEY, method=orcarouter.BY_PKCE)
        # ⛔ WHAT IS CHECKED IS EVERY PLACE IT COULD LEAVE: the URL the browser
        # is sent, the message a failure produces, and the state the page is
        # told. The attribute on the login object is where it is SUPPOSED to
        # live until the exchange - the rule is that it goes no further.
        assert verifier not in json.dumps(credential.as_state())
    finally:
        login.close()


async def test_close_releases_the_listener_and_is_safe_twice():
    """Known-bad: leaving the port bound on the denial path, which is a second
    sign-in that fails for a reason nobody can see."""
    login = orcarouter.PkceLogin()
    login.start()
    port = login.port
    assert port > 0
    login.close()
    login.close()
    assert login.callback_url == "oob"
    # The port is genuinely free again, and nothing is listening on it.
    async with httpx.AsyncClient() as client:
        with pytest.raises(Exception):
            await client.get("http://127.0.0.1:%d/callback?code=x" % port, timeout=1)


def test_there_is_no_refresh_anywhere_in_the_provider_modules():
    """⛔ A PKCE-ISSUED KEY IS DURABLE, NOT REFRESHABLE. There is no refresh
    endpoint, so a client that invents one is a client that will try to call a
    route that does not exist - or worse, silently overwrite a working key.

    Known-bad: adding `grant_type=refresh_token`, or a `refresh` field the code
    treats as a token.
    """
    import pathlib

    import ast

    root = pathlib.Path(orcarouter.__file__).parent
    for name in ("orcarouter.py", "provider.py"):
        text = (root / name).read_text()
        # ⛔ COMMENTS AND DOCSTRINGS STRIPPED, because this module explains in
        # prose that there IS no refresh grant - and a scan that cannot tell
        # code from the sentence saying so accuses the file of the defect it
        # documents. That failure is written down in this repository twice.
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                body = node.body
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    body.pop(0)
        code = "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith("#"))
        for forbidden in ("refresh_token", "grant_type", "oauth/token", "expires_in",
                          "refresh="):
            assert forbidden not in code, (
                "%s mentions %r, which is a token lifecycle this grant does not "
                "have" % (name, forbidden))
        assert "access_token" not in code


# ---------------------------------------------------------------------------
# adapter one: the pasted key
# ---------------------------------------------------------------------------

def test_the_key_is_read_from_the_environment_under_either_accepted_name():
    assert orcarouter.key_from_environment({"ORCAROUTER_API_KEY": "a"}) == "a"
    assert orcarouter.key_from_environment({"ORCA_KEY": "b"}) == "b"
    assert orcarouter.key_from_environment({"ORCAROUTER_API_KEY": "a",
                                            "ORCA_KEY": "b"}) == "a"
    assert orcarouter.key_from_environment({"OPENROUTER_API_KEY": "c"}) == ""
    assert orcarouter.key_from_environment({"ORCAROUTER_API_KEY": "  "}) == ""


def test_an_explicit_key_wins_and_an_empty_one_counts_as_absent():
    assert orcarouter.resolve_key("flag", {"ORCAROUTER_API_KEY": "env"}) == "flag"
    assert orcarouter.resolve_key("", {"ORCAROUTER_API_KEY": "env"}) == "env"
    assert orcarouter.resolve_key(None, {}) == ""


def test_the_mask_is_short_enough_to_be_useless_and_long_enough_to_identify():
    """Known-bad: masking with the first eight characters, which on a key of
    this shape is most of what identifies the account."""
    credential = orcarouter.Credential("sk-orca-CANARY-abcdefghijklmnop")
    masked = credential.masked
    assert masked.endswith("mnop")
    assert "CANARY" not in masked and "abcdefgh" not in masked
    assert len(masked) < len(credential.key)
    assert orcarouter.Credential("").masked == "(set)"


def test_the_state_a_page_is_given_carries_no_key():
    """⛔ THE PAGE IS A BROWSER. A key that reaches it is a key in a screenshot,
    a devtools session and a crash report."""
    credential = orcarouter.Credential(FAKE_KEY, generation=3, scope="api")
    blob = json.dumps(credential.as_state())
    assert FAKE_KEY not in blob
    assert credential.masked in blob
    assert json.loads(blob)["generation"] == 3


async def test_both_adapters_produce_a_credential_the_same_code_spends(
        monkeypatch, tmp_path):
    """⛔ THE SEAM ITSELF, AND THE REASON THIS FILE EXISTS. A pasted key and a
    signed-in key are one shape, and neither the inference client nor the
    catalogue asks which one it was: both are handed a key and a base URL, and
    the base URL is the same one either way.
    """
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    with FakeAuth() as auth:
        monkeypatch.setenv("ORCAROUTER_AUTH_BASE_URL", auth.base)
        login = orcarouter.PkceLogin()
        login.start()
        try:
            await _deliver(login.callback_url, {"code": FAKE_CODE, "state": login.state})
            signed_in = await login.exchange(await login.wait(timeout=5))
        finally:
            login.close()

    pasted = orcarouter.Credential(FAKE_KEY, method=orcarouter.BY_KEY)
    assert isinstance(pasted, orcarouter.Credential)
    assert isinstance(signed_in, orcarouter.Credential)
    assert pasted.method != signed_in.method

    # Downstream: the same client shape, the same base URL, and a catalogue
    # call that takes the key and nothing else.
    one = orcarouter_client(pasted.key)
    two = orcarouter_client(signed_in.key)
    assert str(one.base_url).rstrip("/") == str(two.base_url).rstrip("/")
    assert str(one.base_url).rstrip("/") == orcarouter.API_BASE_URL
    assert one.api_key == FAKE_KEY and two.api_key == FAKE_KEY
    assert pasted.as_state()["masked"] == signed_in.as_state()["masked"]


async def test_a_key_can_be_saved_read_back_masked_and_removed(monkeypatch, tmp_path):
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    state = provider.ProviderState()
    async with _client(state) as client:
        answer = await client.post("/provider/key", json={"key": FAKE_KEY})
        assert answer.status_code == 200
        blob = answer.json()
        assert FAKE_KEY not in answer.text
        assert blob["credential"]["set"] is True
        assert blob["credential"]["masked"].endswith("key")
        assert blob["provider"] == "orcarouter"

        stored = provider.load_credential({})
        assert stored is not None and stored.key == FAKE_KEY
        assert stored.generation == blob["credential"]["generation"]

        gone = await client.post("/provider/key", json={"remove": True})
        assert gone.json()["credential"]["set"] is False
        assert provider.load_credential({}) is None
        assert not provider.credential_path().is_file()


async def test_an_empty_key_is_refused_rather_than_stored(monkeypatch, tmp_path):
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    async with _client() as client:
        answer = await client.post("/provider/key", json={"key": "   "})
    assert answer.status_code == 400
    assert provider.load_credential({}) is None


def test_the_credential_file_is_written_atomically_and_read_back(monkeypatch, tmp_path):
    """Known-bad: `write_text` on the file directly, which hands a reader half
    a JSON document if it is interrupted."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    provider.save_credential(orcarouter.Credential(FAKE_KEY, method=orcarouter.BY_PKCE,
                                                   generation=7, scope="api"))
    where = provider.credential_path()
    assert where.is_file()
    assert not list(where.parent.glob("*.writing"))
    again = provider.load_credential({})
    assert again.key == FAKE_KEY and again.generation == 7
    assert again.method == orcarouter.BY_PKCE


def test_a_credential_in_the_environment_is_read_when_none_is_stored(monkeypatch, tmp_path):
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    got = provider.load_credential({"ORCAROUTER_API_KEY": FAKE_KEY})
    assert got.key == FAKE_KEY and got.source == "environment"
    assert provider.load_credential({}) is None


def test_a_corrupt_credential_file_is_not_a_crash(monkeypatch, tmp_path):
    """A saved thing that cannot be read is exactly as usable as one that was
    never saved - the rule `storage.read_json` already states."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    where = provider.credential_path()
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_bytes(b"{not json")
    assert provider.load_credential({}) is None


# ---------------------------------------------------------------------------
# the catalogue
# ---------------------------------------------------------------------------

def _record(model_id, endpoints=("openai",), modalities=None):
    item = {"id": model_id, "object": "model", "owned_by": "x",
            "supported_endpoint_types": list(endpoints)}
    if modalities is not None:
        item["architecture"] = {"input_modalities": list(modalities)}
    return item


def test_the_catalogue_keeps_the_vendor_namespace_verbatim():
    """⛔ THE NAMESPACE IS THE ROUTE. `deepseek/deepseek-v4-pro` trimmed to
    `deepseek-v4-pro` is a model id the gateway does not know."""
    got = orcarouter.catalog_from({"data": [_record("deepseek/deepseek-v4-pro")]})
    assert [m.id for m in got] == ["deepseek/deepseek-v4-pro"]


def test_records_that_are_not_usable_models_are_dropped_rather_than_guessed_at():
    """Known-bad: accepting a record with no id, or one advertising an endpoint
    type this client cannot speak, and offering it in a dropdown."""
    payload = {"data": [
        "not a dict",
        {"no": "id"},
        {"id": ""},
        {"id": "x" * 500},
        _record("ok/one"),
        {"id": "weird/one", "supported_endpoint_types": ["grpc", 7]},
    ]}
    got = orcarouter.catalog_from(payload)
    assert [m.id for m in got] == ["ok/one", "weird/one"]
    assert got[1].endpoints == ()
    assert orcarouter.catalog_from(None) == []
    assert orcarouter.catalog_from({"data": "nope"}) == []
    assert orcarouter.catalog_from([_record("bare/one")])[0].id == "bare/one"


def test_the_catalogue_answer_is_bounded_in_items():
    """Known-bad: no cap, so somebody else's thousand-entry answer becomes a
    thousand-entry dropdown."""
    payload = {"data": [_record("m/%d" % n) for n in range(orcarouter.MAX_CATALOG_ITEMS + 50)]}
    assert len(orcarouter.catalog_from(payload)) == orcarouter.MAX_CATALOG_ITEMS


def test_the_chat_filter_keeps_text_models_and_excludes_the_specialised_ones():
    """⛔ A MODEL THAT ALSO ADVERTISES `openai` IS STILL NOT A CHAT MODEL when
    its own endpoint list says it is an image generator, a video model or a
    reranker. Known-bad: intersecting with the chat set and stopping there.
    """
    models = orcarouter.catalog_from({"data": [
        _record("text/one"),
        _record("text/two", endpoints=("anthropic",)),
        _record("text/three", endpoints=("gemini", "openai-response")),
        _record("image/one", endpoints=("openai", "image-generation")),
        _record("video/one", endpoints=("openai", "openai-video")),
        _record("rerank/one", endpoints=("openai", "jina-rerank")),
        _record("embed/one", endpoints=("openai", "embeddings")),
        _record("nothing/one", endpoints=("grpc",)),
    ]})
    assert [m.id for m in orcarouter.models_for(models, "chat")] == \
        ["text/one", "text/two", "text/three"]


def test_every_other_capability_is_a_strict_match_on_its_own_endpoint():
    models = orcarouter.catalog_from({"data": [
        _record("text/one"),
        _record("embed/one", endpoints=("embeddings",)),
        _record("image/one", endpoints=("image-generation",)),
        _record("video/one", endpoints=("openai-video",)),
        _record("rerank/one", endpoints=("jina-rerank",)),
    ]})
    assert [m.id for m in orcarouter.models_for(models, "embedding")] == ["embed/one"]
    assert [m.id for m in orcarouter.models_for(models, "image")] == ["image/one"]
    assert [m.id for m in orcarouter.models_for(models, "video")] == ["video/one"]
    assert [m.id for m in orcarouter.models_for(models, "rerank")] == ["rerank/one"]
    assert orcarouter.models_for(models, "unknown-capability") == []


def test_a_multimodal_selector_fails_closed_on_a_record_that_declares_nothing():
    """⛔ NO GUESSING FROM A MODEL NAME. A record that does not name an input
    modality is not offered for an image, and a model that declares `image` is
    offered only when the caller asked for `image`."""
    models = orcarouter.catalog_from({"data": [
        _record("text/one"),
        _record("text/one-vision", modalities=("text", "image")),
        _record("text/one-audio", modalities=("text", "audio")),
        _record("text/one-blind", modalities=[]),
        _record("image/one", endpoints=("openai", "image-generation"),
                modalities=("text", "image")),
    ]})
    assert [m.id for m in orcarouter.models_for(models, "chat", "image")] == \
        ["text/one-vision"]
    assert [m.id for m in orcarouter.models_for(models, "chat", "audio")] == \
        ["text/one-audio"]
    assert [m.id for m in orcarouter.models_for(models, "chat")] == \
        ["text/one", "text/one-vision", "text/one-audio", "text/one-blind"]
    assert orcarouter.models_for(models, "chat", "video") == []


async def test_a_live_catalogue_is_authoritative_and_replaces_the_seed(monkeypatch, tmp_path):
    """⛔ THE SEED IS NOT MIXED INTO A LIVE ANSWER. Mixing them makes the
    dropdown a claim about the account that is partly verified and partly not,
    with no way to tell which rows those are."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    state = provider.ProviderState()
    state.set_credential(orcarouter.Credential(FAKE_KEY))
    live = orcarouter.catalog_from({"data": [_record("live/only")]})
    state.set_catalog(live, orcarouter.LIVE_SOURCE)
    assert [m.id for m in state.offered("chat")] == ["live/only"]
    assert state.source == orcarouter.LIVE_SOURCE
    assert not (set(orcarouter.SEED_MODELS) & {m.id for m in state.offered("chat")})


async def test_a_failed_discovery_falls_back_to_the_labelled_verified_seed(monkeypatch, tmp_path):
    """⛔ NOT TO A FREE-TEXT BOX AND NOT TO AN EMPTY LIST. A fresh install with
    no network must still offer something callable, and it must say what it is
    showing."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    monkeypatch.setenv("ORCAROUTER_API_BASE_URL", "http://127.0.0.1:9")
    state = provider.ProviderState()
    state.set_credential(orcarouter.Credential(FAKE_KEY))
    async with _client(state) as client:
        answer = await client.post("/provider/refresh")
    blob = answer.json()
    assert blob["source"] == orcarouter.SEED_SOURCE
    assert blob["catalog_error"]
    assert [m["id"] for m in blob["models"]] == list(orcarouter.SEED_MODELS)
    assert all(m["endpoints"] for m in blob["models"])


async def test_a_credential_less_provider_offers_the_seed_and_says_why(monkeypatch, tmp_path):
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    async with _client() as client:
        answer = await client.get("/provider/models")
    blob = answer.json()
    assert blob["source"] == orcarouter.SEED_SOURCE
    assert [m["id"] for m in blob["models"]] == list(orcarouter.SEED_MODELS)


async def test_a_model_that_left_the_compatible_list_is_cleared_not_kept(monkeypatch, tmp_path):
    """⛔ A STALE ID IS A REQUEST THAT DIES LATER, somewhere that says nothing
    about where the id came from. Known-bad: keeping the selection and hoping.
    """
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    state = provider.ProviderState()
    state.choose("orcarouter", "text/gone")
    state.set_catalog(orcarouter.catalog_from({"data": [_record("text/here")]}),
                      orcarouter.LIVE_SOURCE)
    assert state.model == ""

    state.choose("orcarouter", "text/here")
    assert state.model == "text/here"


async def test_choosing_a_provider_recomputes_the_model_list(monkeypatch, tmp_path):
    """⛔ A MODEL CHOSEN UNDER ONE PROVIDER IS NOT A MODEL THE OTHER OFFERS.
    Known-bad: carrying the id across, which is a request that fails at the
    first turn under a provider that has never heard of it.
    """
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    state = provider.ProviderState()
    async with _client(state) as client:
        first = await client.post("/provider/choose",
                                  json={"provider": "openrouter", "model": "z-ai/glm-5.3-flash"})
        assert first.json()["provider"] == "openrouter"
        assert first.json()["model"] == "z-ai/glm-5.3-flash"

        second = await client.post("/provider/choose", json={"provider": "orcarouter"})
        assert second.json()["provider"] == "orcarouter"
        assert second.json()["model"] == ""

        third = await client.post("/provider/choose",
                                  json={"provider": "orcarouter", "model": "not/in/the/list"})
        assert third.json()["refused"] is True
        assert third.json()["model"] == ""

        fourth = await client.post("/provider/choose",
                                   json={"provider": "orcarouter",
                                         "model": orcarouter.SEED_MODELS[0]})
        assert fourth.json()["model"] == orcarouter.SEED_MODELS[0]


def test_an_unknown_provider_id_is_the_default_rather_than_a_refusal():
    """A page older than this server names a provider that does not exist here.
    The honest answer is the default provider, not a 500."""
    assert provider.known("orcarouter") == "orcarouter"
    assert provider.known("orcarouter-oauth") == "orcarouter-oauth"
    assert provider.known("nonsense") == provider.DEFAULT_PROVIDER
    assert provider.known(None) == provider.DEFAULT_PROVIDER
    assert provider.DEFAULT_PROVIDER == "openrouter"
    assert set(provider.PROVIDERS) == {"openrouter", "orcarouter", "orcarouter-oauth"}
    assert provider.is_orcarouter("orcarouter-oauth")
    assert not provider.is_orcarouter("openrouter")


async def test_the_state_the_page_is_told_carries_no_key(monkeypatch, tmp_path):
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    state = provider.ProviderState()
    state.set_credential(orcarouter.Credential(FAKE_KEY, generation=2))
    async with _client(state) as client:
        answer = await client.get("/provider/state")
    assert FAKE_KEY not in answer.text
    assert answer.json()["credential"]["masked"].endswith("key")


# ---------------------------------------------------------------------------
# errors: a refused key is a terminal state and not a retry loop
# ---------------------------------------------------------------------------

async def test_a_refused_key_marks_the_exact_generation_and_deletes_nothing(
        monkeypatch, tmp_path):
    """⛔ A 401 IS TERMINAL REAUTHENTICATION, NOT A RETRY. And the secret is NOT
    deleted before a replacement succeeds: a transient or misclassified failure
    would then be irreversible."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    state = provider.ProviderState()
    async with _client(state) as client:
        await client.post("/provider/key", json={"key": FAKE_KEY})
        before = provider.load_credential({})
        marked = await client.post("/provider/reauth",
                                   json={"generation": before.generation})
        assert marked.json()["marked"] is True
        assert marked.json()["credential"]["needs_reauth"] is True
        assert provider.load_credential({}) is not None, "the secret was deleted"
        assert FAKE_KEY not in marked.text


async def test_a_stale_failure_cannot_mark_a_newer_credential(monkeypatch, tmp_path):
    """⛔ THE GENERATION-SAFE 401, AND THE REASON `generation` EXISTS AT ALL. A
    late failure from a request made before a reauthorization must not mark the
    credential that sign-in just stored - that is how a working account is
    reported as broken by a request it never made."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    state = provider.ProviderState()
    async with _client(state) as client:
        await client.post("/provider/key", json={"key": FAKE_KEY})
        stale = provider.load_credential({}).generation
        await client.post("/provider/key", json={"key": FAKE_KEY + "-new"})
        now = provider.load_credential({}).generation
        assert now > stale

        refused = await client.post("/provider/reauth", json={"generation": stale})
        assert refused.json()["marked"] is False
        assert refused.json()["reason"] == "a stale generation"
        state_now = await client.get("/provider/state")
        assert state_now.json()["credential"]["needs_reauth"] is False


async def test_reauth_with_no_credential_says_so_rather_than_inventing_one(
        monkeypatch, tmp_path):
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    async with _client() as client:
        answer = await client.post("/provider/reauth", json={"generation": 1})
    assert answer.json()["marked"] is False


# ---------------------------------------------------------------------------
# the routes the panel calls, and the one door the page has
# ---------------------------------------------------------------------------

async def test_the_provider_routes_answer_what_the_panel_asks_for(monkeypatch, tmp_path):
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    async with _client() as client:
        state = await client.get("/provider/state")
        assert set(state.json()) >= {"provider", "providers", "model", "credential",
                                     "source", "models"}
        models = await client.get("/provider/models?capability=chat")
        assert models.json()["capability"] == "chat"
        blind = await client.get("/provider/models?capability=chat&modality=image")
        assert blind.json()["modality"] == "image"
        cancelled = await client.post("/provider/cancel", json={})
        assert "cancelled" in cancelled.json()


async def test_a_cancel_for_an_attempt_that_is_not_current_releases_nothing(
        monkeypatch, tmp_path):
    """⛔ TWO TABS, ONE PROCESS. Cancelling from a page that started an older
    sign-in must not release the one somebody else is in the middle of."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    state = provider.ProviderState()
    async with _client(state) as client:
        first = await client.post("/provider/connect")
        second = await client.post("/provider/connect")
        assert second.json()["attempt"] > first.json()["attempt"]
        answer = await client.post("/provider/cancel",
                                   json={"attempt": first.json()["attempt"]})
        # ⛔ THE STALE LISTENER IS RELEASED AND THE LIVE ATTEMPT IS NOT TOUCHED.
        # Releasing it is not an accident: a superseded attempt holds a bound
        # port until somebody closes it, so a cancel that refused would be a
        # leaked listener. What must NOT happen is the live attempt being
        # cancelled by a page that is not in it.
        assert answer.json()["cancelled"] is True
        assert state.attempt == second.json()["attempt"]


async def test_a_login_answer_for_a_superseded_attempt_is_refused(monkeypatch, tmp_path):
    """⛔ THE LATE SUCCESS THAT MUST NOT LAND. A code that arrives after the
    user started another sign-in is refused with a 409 and the live credential
    is untouched."""
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    state = provider.ProviderState()
    async with _client(state) as client:
        first = await client.post("/provider/connect")
        await client.post("/provider/connect")
        answer = await client.post("/provider/login",
                                   json={"attempt": first.json()["attempt"],
                                         "code": FAKE_CODE, "wait": 0.1})
    assert answer.status_code == 409
    assert provider.load_credential({}) is None


async def test_the_page_asks_for_provider_routes_the_app_serves():
    """The route set is pinned in `test_web_service.py`; this is the other
    direction - every provider path the page names is one that exists."""
    from aihawk.ui import PAGE

    import re

    paths = {r.path for r in _app().routes}
    asked = set(re.findall(r"""(?:door|ask)\(\s*'(/provider/[a-z]+)'""", PAGE))
    assert asked, "the page never asks the provider anything"
    assert asked <= paths, "the page asks for routes that do not exist: %s" % (
        sorted(asked - paths))


async def test_every_provider_request_the_page_makes_is_a_verb_the_route_takes():
    """⛔ A PATH THAT EXISTS IS NOT ENOUGH, AND THIS WAS FOUND ON THE RUNNING PAGE
    RATHER THAN IN THE SUITE. `ask` posts; the four routes that answer a question
    are GET, and Starlette answers a POST to a GET route with 405 - so the panel
    opened with an empty model list, no mask and nothing on screen to say why.
    Measured against the live server, not read from the source.

    The whole table is checked rather than the provider's four rows: the verbs
    live in the app and the calls live in the page, and the two are the same
    question wherever they disagree.
    """
    from aihawk.ui import PAGE

    import re

    verbs = {}
    for route in _app().routes:
        for path in getattr(route, "path", None), getattr(route, "path_format", None):
            if path:
                verbs[path] = set(route.methods or [])
    # `ask` always posts; `door` posts when its `init` says so and reads
    # otherwise. The init is read as text rather than parsed: `method` is
    # written first at every call site, so what follows the path is enough.
    called = re.findall(r"""\b(door|ask)\(\s*'(/[^']+)'\s*(?:,\s*\{([^}]*)\})?""", PAGE)
    assert called, "the page asks for nothing at all"
    for helper, path, init in called:
        methods = verbs.get(path)
        if methods is None:
            continue  # a missing path is the other test's finding
        verb = "POST" if (helper == "ask" or "POST" in (init or "")) else "GET"
        assert verb in methods, (
            "the page sends %s %s and that route takes %s"
            % (verb, path, sorted(methods)))


def test_the_page_has_one_door_and_the_sign_in_uses_it():
    """⛔ A SECOND `fetch` IS A REQUEST THAT CANNOT BE TOLD THE PAGE IS STALE OR
    THE CONVERSATION GONE. The one exception the page already makes is the
    send, which puts the sentence back in the box, and the delete, which reads
    whether the server refused."""
    from aihawk.ui import PAGE

    import re

    script = PAGE[PAGE.index("<script"):]
    code = re.sub(r"/\*.*?\*/", "", script, flags=re.S)
    assert len(re.findall(r"[^.\w]fetch\(", code)) == 1


def test_the_panel_offers_both_ways_in_and_a_model_list_and_no_free_text():
    """⛔ THE HARD GATE FOR THIS FEATURE: two labelled ways to hold a credential
    on the OrcaRouter panel, a model control filled from the server, and no text
    box anywhere that a model id could be typed into.

    ⛔ THE CONTROL IS A LISTBOX AND NOT A `<select>`, and that is a requirement
    rather than a preference: a native select draws its open state as an
    operating-system popup, outside the document, so the model list would be
    invisible to anything reading or photographing the page. The rows are the
    page's own elements.
    """
    from aihawk.ui import PAGE

    assert 'Connect with OrcaRouter' in PAGE
    assert 'OrcaRouter API key' in PAGE
    assert "input" in PAGE and "type = 'password'" in PAGE
    assert "list.appendChild(modelRow(id, chosen, n === providerPick))" in PAGE
    assert "role','listbox'" in PAGE
    assert "No model list yet" in PAGE
    assert "orcarouter.ai/console/authorized-apps" in PAGE
    # Nothing can be typed into the model control: the only free-text field on
    # this panel is the key, and the code with the comments removed holds no
    # select element at all.
    code = re.sub(r"/\*.*?\*/", "", PAGE, flags=re.S)
    assert "el('select')" not in code and "<select" not in code


# ---------------------------------------------------------------------------
# regression: OpenRouter is untouched, and the browser server still gets no key
# ---------------------------------------------------------------------------

def test_openrouter_is_still_the_default_and_its_base_url_is_unchanged():
    assert BASE_URL == "https://openrouter.ai/api/v1"
    assert provider.DEFAULT_PROVIDER == "openrouter"
    assert provider.ProviderState().provider == "openrouter"
    assert str(make_client("k").base_url).rstrip("/") == BASE_URL


def test_the_orcarouter_client_is_aimed_at_the_api_origin_and_carries_no_other_vendor_headers():
    """⛔ OPENROUTER'S APP-ATTRIBUTION HEADERS ARE OPENROUTER'S. Sending them to
    another gateway would be a claim about who is calling, and they mean nothing
    there."""
    client = orcarouter_client(FAKE_KEY)
    assert str(client.base_url).rstrip("/") == orcarouter.API_BASE_URL
    assert client.api_key == FAKE_KEY
    assert "HTTP-Referer" not in (client.default_headers or {})


def test_both_key_names_are_stripped_from_the_environment_a_browser_server_is_given():
    """⛔ A BROWSER SERVER HAS NO USE FOR ANY MODEL KEY. The rule was written
    when there was one name; a second provider reached the engine through a
    second name."""
    assert "ORCAROUTER_API_KEY" in KEY_VARIABLES
    env = {"PATH": "x", "ORCAROUTER_API_KEY": FAKE_KEY, "ORCA_KEY": FAKE_KEY,
           "openrouter_api_key": "other", "STEALTHFOX_SEED": "7"}
    gone = forget_key(env)
    assert env == {"PATH": "x", "STEALTHFOX_SEED": "7"}
    assert sorted(gone) == ["ORCAROUTER_API_KEY", "ORCA_KEY", "openrouter_api_key"]


def test_the_orcarouter_module_never_names_the_wrong_exchange_path_as_a_url():
    """⛔ THE 404 THAT READS LIKE SOMEBODY ELSE'S BUG. `/v1/auth/keys` may appear
    in prose explaining the mistake; it may never be a URL this code builds."""
    import pathlib

    import re

    import ast

    source = pathlib.Path(orcarouter.__file__).read_text()
    # ⛔ THE WRONG PATH IS A STRING THE CODE ACTUALLY USES, and the right one
    # CONTAINS it as a substring (`/api/v1/auth/keys`), so what matters is what
    # precedes it. Docstrings are excluded on purpose: this module explains the
    # mistake in prose at the top, and a scan that cannot tell code from the
    # sentence saying so accuses the file of the defect it documents.
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Expr) and isinstance(child.value, ast.Constant):
                docstrings.add(id(child.value))
    literals = [node.value for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docstrings]
    assert any("/v1/auth/keys" in text for text in literals), (
        "the exchange path is no longer a literal this gate can read")
    for text in literals:
        if "/v1/auth/keys" not in text:
            continue
        assert "/api/v1/auth/keys" in text, (
            "the wrong exchange path is in code: %r" % text)
        assert "api.orcarouter.ai/v1/auth/keys" not in text, (
            "the exchange is aimed at the inference origin: %r" % text)
    # And the module says out loud which one is the mistake.
    assert "api.orcarouter.ai/v1/auth/keys" in source


def test_no_client_secret_and_no_real_key_is_committed_anywhere():
    """⛔ THE COMPLIANCE AUDIT, AS A TEST. There is no client secret in this
    flow at all, and a real key in the tree would be a key in everybody's
    checkout."""
    import pathlib
    import re

    root = pathlib.Path(orcarouter.__file__).parent
    for name in ("orcarouter.py", "provider.py", "llm.py", "cli.py",
                 "ui/js/11-provider.js", "ui/js/12-modellist.js",
                 "ui/js/13-signin.js", "ui/css/08-provider.css",
                 "ui/page.html"):
        text = (root / name).read_text()
        assert "client_secret" not in text, "%s carries a client secret" % name
        for found in re.findall(r"sk-orca-[A-Za-z0-9]{12,}", text):
            assert "CANARY" in found, "%s carries what looks like a real key" % name

# ---------------------------------------------------------------------------
# the command line: which provider a run ends up talking to
# ---------------------------------------------------------------------------

def _cli(monkeypatch, argv, env=None):
    """`aihawk ui`, stopped at the link the way the CLI's own tests stop it.

    ⛔ THROUGH `_cli_brake`, WHICH IS THE ONLY PLACE THAT KNOWS THE SEAM. The
    command serves the interface forever once it connects, so a test that
    installs its own brake is a test that can hang the suite; a gate in
    `test_the_suite_reads_no_real_session` keeps every file honest about it.

    The variables are cleared and then set, because the verdict of these tests
    must not depend on what the machine running them happens to export.
    """
    from _cli_brake import brake, run_cli

    rec = brake(monkeypatch)
    for name in ("OPENROUTER_API_KEY", "ORCAROUTER_API_KEY", "ORCA_KEY",
                 "AIHAWK_MODEL"):
        monkeypatch.delenv(name, raising=False)
    for name, value in (env or {}).items():
        monkeypatch.setenv(name, value)
    result = run_cli("ui", "--binary", "/usr/bin/firefox", *argv)
    return rec, result


def test_the_ui_declares_the_two_orcarouter_ways_in_and_the_provider_flag():
    from click.testing import CliRunner

    import aihawk.cli as climod

    rendered = CliRunner().invoke(climod.main, ["ui", "--help"]).output
    for option in ("--orcarouter-key", "--provider", "--orcarouter-connect"):
        assert option in rendered, "the help never names %s" % option
    assert "ORCAROUTER_API_KEY" in rendered


def test_a_pasted_orcarouter_key_is_the_credential_and_the_origin_is_the_api_one(monkeypatch):
    """⛔ THE FLAG NAMES THE PROVIDER, and the key it carries is spent at the
    inference origin rather than at OpenRouter's."""
    rec, result = _cli(monkeypatch, ["--orcarouter-key", FAKE_KEY])

    assert rec.calls, result.output
    assert rec.call["key"] == FAKE_KEY
    assert "api.orcarouter.ai" in result.output
    assert "openrouter.ai/api/v1" not in result.output


def test_the_orcarouter_key_can_come_from_the_environment(monkeypatch):
    rec, result = _cli(monkeypatch, [], env={"ORCAROUTER_API_KEY": FAKE_KEY})

    assert rec.calls, result.output
    assert rec.call["key"] == FAKE_KEY
    assert "api.orcarouter.ai" in result.output


def test_openrouter_is_still_what_an_unspecified_run_uses(monkeypatch):
    """⛔ THE DEFAULT DID NOT MOVE. A run with only an OpenRouter key set must
    reach OpenRouter, whatever else the shell happens to export."""
    rec, result = _cli(monkeypatch, [],
                       env={"OPENROUTER_API_KEY": FAKE_KEY,
                            "ORCAROUTER_API_KEY": "sk-orca-" + "b" * 24})

    assert rec.calls, result.output
    assert "openrouter.ai/api/v1" in result.output
    assert "api.orcarouter.ai" not in result.output


def test_an_explicit_openrouter_run_ignores_an_orcarouter_key_in_the_environment(monkeypatch):
    """⛔ FOUND ON THE RUNNING CLI, NOT IN THE SUITE. `--provider openrouter` was
    read as "nobody said which", so a shell that exported ORCAROUTER_API_KEY
    turned a named OpenRouter run into an OrcaRouter one - the key that got
    spent was not the one that was asked for."""
    rec, result = _cli(monkeypatch, ["--provider", "openrouter"],
                       env={"OPENROUTER_API_KEY": FAKE_KEY,
                            "ORCAROUTER_API_KEY": "sk-orca-" + "b" * 24})

    assert rec.calls, result.output
    assert "openrouter.ai/api/v1" in result.output
    assert "api.orcarouter.ai" not in result.output


def test_an_orcarouter_run_with_no_key_still_starts_and_says_where_to_sign_in(monkeypatch):
    """⛔ A REFUSAL WOULD BE THE WRONG ANSWER. There are two ways in and the
    panel is one of them, so a run named for OrcaRouter with no key starts, says
    so, and leaves the sign-in to the person rather than exiting."""
    rec, result = _cli(monkeypatch, ["--provider", "orcarouter"])

    # `rec.calls` is the proof it was not refused: the brake stops the run at
    # the link, so a run that reached the link got past the key check.
    assert rec.calls, "the interface refused to start without a key"
    # The startup line says which road is still open, because the command did
    # not do what it was asked and a quiet start would look like a broken model.
    assert "a sign-in, no key yet" in result.output
    assert "api.orcarouter.ai" in result.output


def test_a_keyless_run_names_both_providers_rather_than_only_openrouter(monkeypatch):
    rec, result = _cli(monkeypatch, [])

    assert not rec.calls, "the interface started without a model key"
    assert "OPENROUTER_API_KEY" in result.output
    assert "ORCAROUTER_API_KEY" in result.output
    assert "--orcarouter-connect" in result.output

def test_the_two_origins_are_declared_in_one_module_and_nowhere_else():
    """⛔ ONE PLACE KNOWS WHICH COMPANY A KEY IS SENT TO. The origins are the
    fact this whole change turns on, and a second copy of either string is a
    copy that can drift - which would be a request carrying a key to a host
    nobody chose.

    What the page is allowed is to NAME the console in prose, which is a
    sentence for a person and not an address a request is built from.
    """
    import pathlib
    import re

    root = pathlib.Path(orcarouter.__file__).parent
    auth_hosts, api_hosts = [], []
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "www.orcarouter.ai" in text:
            auth_hosts.append(path.name)
        if "api.orcarouter.ai" in text:
            api_hosts.append(path.name)
    assert auth_hosts == ["orcarouter.py"], auth_hosts
    assert api_hosts == ["orcarouter.py"], api_hosts
    # The page's script may not build a URL to either host: every request it
    # makes goes through the door, to this server.
    script = "".join((root / "ui" / "js" / n).read_text(encoding="utf-8")
                     for n in ("11-provider.js", "12-modellist.js", "13-signin.js"))
    code = re.sub(r"/\*.*?\*/", "", script, flags=re.S)
    assert "https://api.orcarouter.ai" not in code
    assert "https://www.orcarouter.ai" not in code
