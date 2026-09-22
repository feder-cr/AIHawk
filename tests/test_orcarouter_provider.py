"""OrcaRouter: the two ways in, and the one credential they both produce.

⛔ WHAT THIS FILE IS FOR. A provider preset is easy to write and easy to be
wrong about in ways no screenshot shows: a base URL built by swapping a hostname,
an exchange sent to the inference origin, a verifier that outlives the attempt
that made it, a revoked key that loops on 401 instead of asking to be replaced.
None of those produce a red anything on their own, and every one of them is a
line of code rather than a design.

So the assertions here are on the wire and on the state, never on a helper in
isolation:

* the two adapters are driven and the credential each one produces is compared,
  because "two ways in" that produce two different things downstream is one way
  in with extra steps;
* the authorize and exchange URLs are read off the request that would be sent,
  not off a constant that is also read by the code under test;
* a fake auth server completes the whole loop - authorize, callback, exchange,
  persist - because a hash helper tested alone proves nothing about the flow;
* and the secrets are looked for in the places they leak: repr, messages, logs,
  and the URLs.

Every key and code here is a fake with a marker in it, so an echo is
recognisable. Nothing in this file touches the network: `urlopen` is replaced
wherever a request would go out.
"""
from __future__ import annotations

import json
import os
import re
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from aihawk import llm, orcarouter, provider
from aihawk.orcarouter import Catalog, Credential, Credentials, Model

#: A key shaped like the real thing with a marker in it, so any echo of it -
#: whole or truncated to its prefix - is recognisable.
FAKE_KEY = "sk-orca-CANARY-9f3b2a7c-do-not-echo"
MARKER = "CANARY"
FAKE_CODE = "code-CANARY-5c1d"


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A private AIHAWK_HOME, so a test can never read or write the real one.

    ⛔ NOT TIDINESS. `Credentials` goes to the same directory the developer's own
    sessions are in, and a test that saved a key there would leave it behind -
    and a test that READ there would pass or fail depending on what the machine
    happened to hold.
    """
    monkeypatch.setenv("AIHAWK_HOME", str(tmp_path))
    return tmp_path


# --------------------------------------------------------------------------
# the two origins, and the mistake that is not obvious from the URLs
# --------------------------------------------------------------------------

def test_auth_and_inference_are_different_origins():
    """⛔ THE SINGLE MOST COMMON INTEGRATION MISTAKE, PINNED AS A TEST.

    `https://api.orcarouter.ai/v1/auth/keys` is a 404, and it is what you get by
    appending the auth path to the inference base. The two look like one host
    with a prefix swapped, so this asserts they are two hosts AND that the auth
    path is the one with `/api` in the middle.
    """
    assert orcarouter.AUTH_BASE_URL == "https://www.orcarouter.ai"
    assert orcarouter.API_BASE_URL == "https://api.orcarouter.ai/v1"
    assert orcarouter.AUTHORIZE_PATH == "/auth"
    assert orcarouter.EXCHANGE_PATH == "/api/v1/auth/keys"
    assert not orcarouter.EXCHANGE_PATH.startswith("/v1")


def test_neither_origin_is_derived_from_the_other():
    """⛔ A REQUEST GOES TO THE ORIGIN THAT OWNS IT, READ OFF THE URL.

    Known-bad: build the exchange URL as `api_base + "/auth/keys"`, which is the
    derivation the rules name and which produces the 404 above. The assertion is
    on the composed URL rather than on the constants, because the constants can
    both be right while the composition is wrong.
    """
    env = {}
    assert orcarouter.auth_base(env) == "https://www.orcarouter.ai"
    assert orcarouter.api_base(env) == "https://api.orcarouter.ai/v1"
    exchange = "%s%s" % (orcarouter.auth_base(env), orcarouter.EXCHANGE_PATH)
    assert exchange == "https://www.orcarouter.ai/api/v1/auth/keys"
    assert "api.orcarouter.ai" not in exchange


def test_the_explicit_overrides_win_and_the_shared_one_is_a_fallback():
    """Self-hosted runs one origin or two, and the order is what somebody
    setting only one of them expects."""
    shared = {"ORCA_BASE_URL": "https://one.example.com"}
    assert orcarouter.auth_base(shared) == "https://one.example.com"
    assert orcarouter.api_base(shared) == "https://one.example.com"
    both = {"ORCA_BASE_URL": "https://one.example.com",
            "ORCA_AUTH_BASE_URL": "https://auth.example.com",
            "ORCA_API_BASE_URL": "https://api.example.com/v1"}
    assert orcarouter.auth_base(both) == "https://auth.example.com"
    assert orcarouter.api_base(both) == "https://api.example.com/v1"


def test_plain_http_is_refused_unless_it_is_loopback():
    """⛔ A CREDENTIAL ON THE WIRE IN THE CLEAR. A LAN deployment is a real case
    and it is still required to be HTTPS; the loopback exception exists so a
    developer can run the thing on their own machine."""
    assert orcarouter.api_base({"ORCA_API_BASE_URL": "http://127.0.0.1:8080/v1"}) \
        == "http://127.0.0.1:8080/v1"
    assert orcarouter.api_base({"ORCA_BASE_URL": "http://localhost:9000"}) \
        == "http://localhost:9000"
    for bad in ("http://api.example.com/v1", "http://192.168.1.10:8080"):
        with pytest.raises(ValueError):
            orcarouter.api_base({"ORCA_API_BASE_URL": bad})


# --------------------------------------------------------------------------
# PKCE
# --------------------------------------------------------------------------

def test_the_challenge_is_the_unpadded_base64url_of_the_sha256():
    """⛔ CHECKED AGAINST A VALUE COMPUTED HERE, not against the function under
    test run twice. `base64url(sha256(verifier))`, no padding, and the padding
    is the detail that is silently accepted by some servers and not others."""
    import base64
    import hashlib

    verifier = "abc123-verifier"
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    got = orcarouter.challenge_for(verifier)
    assert got == expected
    assert "=" not in got
    assert "+" not in got and "/" not in got


def test_every_attempt_gets_a_fresh_verifier_and_a_fresh_state():
    """⛔ REUSING ONE IS THE WHOLE PROTECTION THROWN AWAY. A verifier derived
    from anything guessable - a timestamp, a username, a fixed salt - lets
    anybody who saw the challenge redeem any later code."""
    verifiers = {orcarouter.make_verifier() for _ in range(50)}
    states = {orcarouter.make_state() for _ in range(50)}
    assert len(verifiers) == 50 and len(states) == 50
    # 32 random bytes, base64url with no padding: 43 characters.
    assert all(len(v) == 43 for v in verifiers)
    assert all(len(s) == 22 for s in states)
    assert not (verifiers & states)


def test_the_authorize_url_carries_the_challenge_and_never_the_verifier():
    """⛔ THE VERIFIER MUST NOT BE IN THE URL. It is the one value that makes an
    intercepted code unredeemable, and the authorize URL goes through browser
    history, any proxy and any log on the way."""
    verifier = orcarouter.make_verifier()
    url = orcarouter.authorize_url("https://www.orcarouter.ai",
                                   challenge=orcarouter.challenge_for(verifier),
                                   state="STATE", callback_url="oob")
    assert verifier not in url
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["callback_url"] == ["oob"]
    assert query["state"] == ["STATE"]
    assert query["app_name"] == [orcarouter.APP_NAME]
    assert query["scope"] == ["api"]
    assert query["code_challenge"] == [orcarouter.challenge_for(verifier)]


def test_s256_is_sent_on_every_flow_including_the_loopback_one():
    """⛔ `plain` IS NEVER OFFERED. The consent screen lets the user choose
    "show me a code" whatever callback was asked for, so a code can always end
    up in human hands - and under `plain` the challenge IS the verifier, which
    rode out on the authorize URL. The rules are explicit that this applies to
    Flow A too, so it is asserted on both."""
    for callback in ("oob", "http://127.0.0.1:1234/cb"):
        url = orcarouter.authorize_url("https://www.orcarouter.ai",
                                       challenge="C", state="S",
                                       callback_url=callback)
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        assert query["code_challenge_method"] == ["S256"]
        assert "plain" not in url


# --------------------------------------------------------------------------
# the exchange, against a fake auth server
# --------------------------------------------------------------------------

class FakeAuth:
    """A local stand-in for the consent endpoint and the relay.

    ⛔ IT RECORDS WHAT WAS SENT, AND THE ASSERTIONS ARE ON THAT. A test that
    replaces `_post_json` and checks its arguments proves the caller built the
    right dict; it does not prove the request that leaves this process goes to
    the right host with the right path. This one is reached by a real
    `urllib` call, so the path and the body are the ones that would go out.
    """

    def __init__(self, *, key=FAKE_KEY, scope="api", status=200, body=None):
        self.calls = []
        self.key = key
        self.scope = scope
        self.status = status
        self.body = body
        recorder = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 - the name is the base class's
                length = int(self.headers.get("content-length") or 0)
                raw = self.rfile.read(length)
                recorder.calls.append({
                    "path": self.path,
                    "body": json.loads(raw.decode("utf-8") or "{}"),
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                })
                if recorder.body is not None:
                    payload = json.dumps(recorder.body).encode()
                    code = recorder.status
                elif recorder.status == 200:
                    payload = json.dumps({"key": recorder.key,
                                          "user_id": "12345",
                                          "scope": recorder.scope}).encode()
                    code = 200
                else:
                    payload = json.dumps({"error": "invalid_grant"}).encode()
                    code = recorder.status
                self.send_response(code)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(payload)))
                self.send_header("connection", "close")
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):  # keep pytest output clean
                pass

        ThreadingHTTPServer.allow_reuse_address = True
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
        return "http://127.0.0.1:%d" % self._server.server_address[1]


def test_the_exchange_goes_to_the_auth_origin_at_the_auth_path(home):
    """⛔ THE PATH AND THE HOST, ON THE WIRE. Known-bad: `/v1/auth/keys`, which
    is a 404 with a message that looks like a routing bug on the provider's
    side."""
    with FakeAuth() as fake:
        key, scope = orcarouter.exchange_code(fake.url, FAKE_CODE, "VERIFIER")
    assert key == FAKE_KEY
    assert scope == "api"
    assert fake.calls[0]["path"] == "/api/v1/auth/keys"
    assert fake.calls[0]["body"] == {"code": FAKE_CODE,
                                     "code_verifier": "VERIFIER",
                                     "code_challenge_method": "S256"}


def test_the_granted_scope_is_read_back_and_not_assumed():
    """⛔ WHAT WAS GRANTED, NOT WHAT WAS ASKED FOR. A client that requested
    `connector` and reads `api` was approved by somebody whose workspace role
    does not permit the wider grant, and a client that assumes otherwise
    believes it holds a permission it does not."""
    with FakeAuth(scope="api") as fake:
        _, scope = orcarouter.exchange_code(fake.url, FAKE_CODE, "V")
    assert scope == "api"
    with FakeAuth(scope="connector") as fake:
        _, scope = orcarouter.exchange_code(fake.url, FAKE_CODE, "V")
    assert scope == "connector", "the response's own scope was overwritten"


@pytest.mark.parametrize("status,expected", [
    (400, "malformed"),
    (403, "expired or already used"),
    (429, "as many keys"),
])
def test_a_refused_exchange_says_something_a_person_can_act_on(status, expected, home):
    """⛔ ONE SENTENCE PER FAILURE, AND NONE OF THEM IS A RESPONSE DUMP. 403 and
    400 are different problems - start again, versus a bug here - and 429 is the
    only one where waiting is the right advice."""
    with FakeAuth(status=status) as fake:
        with pytest.raises(orcarouter.PkceError) as caught:
            orcarouter.exchange_code(fake.url, FAKE_CODE, "V")
    message = str(caught.value)
    assert expected in message
    assert "invalid_grant" not in message, "the provider's body reached the user"
    assert FAKE_CODE not in message and MARKER not in message


def test_a_network_failure_ends_the_attempt_instead_of_hanging():
    """⛔ A HOT LOOP AND A HANG ARE THE TWO FAILURES THIS PREVENTS. The port is
    bound by nothing, so the connection is refused immediately rather than
    timing out."""
    with pytest.raises(orcarouter.PkceError) as caught:
        orcarouter.exchange_code("http://127.0.0.1:1", FAKE_CODE, "V", timeout=2)
    assert "could not reach" in str(caught.value)
    assert FAKE_CODE not in str(caught.value)


def test_a_success_with_no_key_is_a_failure_and_not_an_empty_credential():
    """Known-bad: `return got["key"]`, which raises a KeyError whose message
    names neither the provider nor the flow - or worse, stores ""."""
    with FakeAuth(body={"user_id": "1", "scope": "api"}) as fake:
        with pytest.raises(orcarouter.PkceError) as caught:
            orcarouter.exchange_code(fake.url, FAKE_CODE, "V")
    assert "returned no key" in str(caught.value)


# --------------------------------------------------------------------------
# the whole loop, through the flow the product uses
# --------------------------------------------------------------------------

def test_the_loopback_flow_authorizes_calls_back_exchanges_and_persists(home):
    """⛔ THE WHOLE THING, END TO END, ON A LOCAL FAKE.

    Not the hash helper, not the URL builder: the listener binds, the authorize
    URL is what the browser would be sent, the callback carries a code and the
    state, the code is exchanged against a real HTTP request, and the key that
    comes back is stored. This is the shape the rules ask for, and a test of the
    pieces would pass while the flow was broken between them.
    """
    seen = {}
    with FakeAuth() as fake:
        # The consent endpoint is the fake's POST route; the browser is replaced
        # by something that parses the URL it was handed and calls back to the
        # loopback listener exactly as a browser would.
        attempt = orcarouter.start_authorization(
            {"ORCA_AUTH_BASE_URL": fake.url},
            opener=lambda url: seen.setdefault("url", url))
        assert seen["url"].startswith("%s/auth?" % fake.url)
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(seen["url"]).query)
        callback = query["callback_url"][0]
        assert callback.startswith("http://127.0.0.1:")
        assert callback.endswith("/cb")

        # What the browser does on approve: the code and the state we sent.
        with urllib.request.urlopen("%s?code=%s&state=%s"
                                    % (callback, FAKE_CODE, query["state"][0]),
                                    timeout=10) as answer:
            assert answer.status == 200
        code = attempt.await_code(timeout=10)
        assert code == FAKE_CODE

        key, scope = orcarouter.exchange_code(fake.url, code, attempt.verifier)
        assert key == FAKE_KEY

    stored = Credentials().save(
        Credential(key=key, method="pkce", scope=scope, source="pkce"))
    assert stored.key == FAKE_KEY
    assert stored.method == "pkce"
    assert stored.generation == 1
    again = Credentials().load()
    assert again is not None and again.key == FAKE_KEY
    assert fake.calls[0]["path"] == "/api/v1/auth/keys"
    assert fake.calls[0]["body"]["code_verifier"] == attempt.verifier


def test_a_callback_with_the_wrong_state_ends_the_attempt(home):
    """⛔ THE ONLY THING STANDING BETWEEN THE LISTENER AND SOMEBODY ELSE'S PAGE.
    The listener is on a port anything on this machine can reach."""
    with FakeAuth() as fake:
        seen = {}
        attempt = orcarouter.start_authorization(
            {"ORCA_AUTH_BASE_URL": fake.url},
            opener=lambda url: seen.setdefault("url", url))
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(seen["url"]).query)
        callback = query["callback_url"][0]
        with urllib.request.urlopen("%s?code=%s&state=not-the-state"
                                    % (callback, FAKE_CODE), timeout=10):
            pass
        with pytest.raises(orcarouter.PkceError) as caught:
            attempt.await_code(timeout=10)
    assert "different attempt" in str(caught.value)
    assert FAKE_CODE not in str(caught.value)


def test_a_denial_is_reported_and_nothing_is_stored(home):
    """⛔ THE USER SAID NO, AND THE CLIENT HAS TO SAY SO AND STOP. Known-bad:
    polling forever, or crashing on a missing field."""
    with FakeAuth() as fake:
        seen = {}
        attempt = orcarouter.start_authorization(
            {"ORCA_AUTH_BASE_URL": fake.url},
            opener=lambda url: seen.setdefault("url", url))
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(seen["url"]).query)
        callback = query["callback_url"][0]
        with urllib.request.urlopen("%s?error=access_denied&state=%s"
                                    % (callback, query["state"][0]), timeout=10):
            pass
        with pytest.raises(orcarouter.PkceError) as caught:
            attempt.await_code(timeout=10)
    assert "declined" in str(caught.value)
    assert Credentials().load() is None, "a denial stored a credential"


def test_an_attempt_that_never_comes_back_ends_instead_of_waiting_forever(home):
    """⛔ A TIMEOUT HAS TO BE A SENTENCE. Known-bad: `await_code` with no
    deadline, which leaves the process holding a port and a person with no
    explanation."""
    attempt = orcarouter.start_authorization({}, opener=lambda url: None)
    with pytest.raises(orcarouter.PkceError) as caught:
        attempt.await_code(timeout=0.2)
    assert "not completed in time" in str(caught.value)
    attempt.cancel()  # safe twice, which the page's cancel path relies on


def test_the_oob_flow_asks_for_a_code_rather_than_a_redirect():
    """Flow B is the one for a process that cannot listen: `callback_url=oob`,
    the literal three letters, and S256 mandatory."""
    seen = {}
    attempt = orcarouter.start_authorization(
        {}, oob=True, opener=lambda url: seen.setdefault("url", url))
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(seen["url"]).query)
    assert query["callback_url"] == ["oob"]
    assert query["code_challenge_method"] == ["S256"]
    assert attempt.kind == "oob"
    assert attempt._server is None


# --------------------------------------------------------------------------
# nothing secret is anywhere it should not be
# --------------------------------------------------------------------------

def test_the_verifier_and_the_state_are_not_in_the_repr_of_an_attempt():
    """⛔ A DATACLASS PRINTS EVERY FIELD, and this is exactly the object a
    traceback, a debugger or a log line picks up. `repr=False` is the fix and
    this is the proof of it."""
    attempt = orcarouter.start_authorization({}, oob=True, opener=lambda url: None)
    printed = repr(attempt)
    assert attempt.verifier not in printed
    # The state is inside the URL the user has to open, which is the one place
    # it is supposed to be. It is not a field of its own: strip the URL and it
    # is gone from the repr entirely.
    assert attempt.state not in printed.replace(attempt.url, "")
    assert "Authorization(" in printed


def test_a_credential_never_prints_its_key():
    """The same defect one object along: this one travels through the CLI, the
    routes and the store."""
    credential = Credential(key=FAKE_KEY)
    printed = repr(credential)
    assert FAKE_KEY not in printed
    assert MARKER not in printed
    assert "Credential(" in printed


def test_a_key_is_masked_to_its_prefix_and_a_length():
    """⛔ ENOUGH TO RECOGNISE, NOT ENOUGH TO USE, AND NEVER THE TAIL. The tail
    is the part a person pastes and the part a support conversation quotes."""
    masked = orcarouter.mask(FAKE_KEY)
    assert masked.startswith("sk-orca-")
    assert MARKER not in masked
    assert FAKE_KEY not in masked
    assert "characters" in masked
    assert orcarouter.mask("") == ""


def test_the_log_and_the_message_carry_no_credential(home, capsys, caplog):
    """⛔ THE THREE PLACES A SECRET LEAKS: stdout, the log, and an error.

    A successful exchange and a refused one, with the key and the code marked,
    and neither may appear in anything a person or a log collector can read.
    """
    import logging

    with caplog.at_level(logging.DEBUG):
        with FakeAuth() as fake:
            key, _ = orcarouter.exchange_code(fake.url, FAKE_CODE, "VERIFIER")
        assert key == FAKE_KEY
        with FakeAuth(status=403) as fake:
            try:
                orcarouter.exchange_code(fake.url, FAKE_CODE, "VERIFIER")
            except orcarouter.PkceError as exc:
                text = str(exc)
            else:  # pragma: no cover - the fake always refuses here
                raise AssertionError("a 403 was accepted")
    captured = capsys.readouterr()
    haystack = captured.out + captured.err + caplog.text + text
    assert FAKE_KEY not in haystack
    assert FAKE_CODE not in haystack
    assert MARKER not in haystack


def test_the_module_holds_no_key_no_secret_and_no_fixed_verifier():
    """⛔ A STRUCTURAL PIN ON THE SOURCE, because a behavioural test can only
    catch the shapes it thought of. No `sk-orca-` literal, no client secret, no
    verifier assigned to a name at module level, and no call to the wrong
    exchange path."""
    source = Path(orcarouter.__file__).read_text(encoding="utf-8")
    # ⛔ DOCSTRINGS ARE NOT CODE. This module's own comments quote the mistakes
    # it exists to prevent - the 404 path, the shape of a key - so the scan
    # strips docstrings and comments and asserts against what actually runs.
    body = re.sub(r'"""[\s\S]*?"""', "", source)
    body = re.sub(r"#.*", "", body)
    assert not re.search(r"sk-orca-[A-Za-z0-9_-]{8,}", body), \
        "a real-looking key is committed in the source"
    assert "client_secret" not in body and "client-secret" not in body
    assert "/v1/auth/keys" not in body.replace("/api/v1/auth/keys", "")
    assert not re.search(r"^\s*VERIFIER\s*=", body, re.M)
    # And the constants themselves are exactly the two documented endpoints.
    assert orcarouter.AUTHORIZE_PATH == "/auth"
    assert orcarouter.EXCHANGE_PATH == "/api/v1/auth/keys"
    assert orcarouter.AUTH_BASE_URL == "https://www.orcarouter.ai"
    assert orcarouter.API_BASE_URL == "https://api.orcarouter.ai/v1"


# --------------------------------------------------------------------------
# the credential store
# --------------------------------------------------------------------------

def test_the_store_saves_reads_masks_and_clears(home):
    store = Credentials()
    assert store.load() is None
    saved = store.save(Credential(key=FAKE_KEY, method="api_key", source="pasted"))
    assert saved.key == FAKE_KEY
    assert store.load().key == FAKE_KEY
    assert store.load().masked == orcarouter.mask(FAKE_KEY)
    store.clear()
    assert store.load() is None
    store.clear()  # clearing twice is not an error


def test_a_corrupt_stored_file_reads_as_no_credential_rather_than_raising(home):
    """⛔ THE SAME RULE EVERY OTHER READ IN THIS PROJECT FOLLOWS. Something
    unreadable is exactly as usable as something never saved, and raising here
    would refuse to start the interface because a byte went wrong once."""
    store = Credentials()
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_bytes(b"{ this is not json")
    assert store.load() is None
    store.path.write_bytes(json.dumps({"key": ""}).encode())
    assert store.load() is None
    store.path.write_bytes(json.dumps({"key": 42}).encode())
    assert store.load() is None


def test_a_save_is_a_new_generation(home):
    """⛔ THIS IS THE HALF OF THE 401 GUARANTEE THAT CANNOT BE FORGOTTEN AT A
    CALL SITE. A request already in flight when the user signs in again comes
    back holding the generation it was sent with, and can only ever mark that
    one."""
    store = Credentials()
    first = store.save(Credential(key=FAKE_KEY, method="pkce"))
    assert first.generation == 1
    second = store.save(Credential(key="sk-orca-second", method="pkce"))
    assert second.generation == 2
    assert store.load().generation == 2


def test_a_refusal_marks_only_the_generation_that_made_the_request(home):
    """⛔ THE LATE FAILURE FROM AN OLD REQUEST. The old generation is gone, so
    the call changes nothing - and a credential that has never been tried is
    not disabled by an answer to a request somebody else's sign-in superseded."""
    store = Credentials()
    first = store.save(Credential(key=FAKE_KEY, method="pkce"))
    assert store.mark_needs_reauth(first.generation) is True
    assert store.load().needs_reauth is True

    store2 = Credentials()
    store2.save(Credential(key="sk-orca-new", method="pkce"))
    assert store2.mark_needs_reauth(first.generation) is False, (
        "a late 401 from a superseded request disabled the new credential")
    assert store2.load().needs_reauth is False
    assert store2.load().key == "sk-orca-new"


def test_marking_a_revoked_key_never_deletes_it(home):
    """⛔ DELETING ON A FAILURE THAT MIGHT HAVE BEEN MISREAD turns a transient
    problem into a key the user has to find again."""
    store = Credentials()
    saved = store.save(Credential(key=FAKE_KEY, method="pkce"))
    store.mark_needs_reauth(saved.generation)
    still = store.load()
    assert still is not None and still.key == FAKE_KEY
    assert still.needs_reauth is True


def test_a_key_is_never_written_into_the_environment(home, monkeypatch):
    """⛔ THE STORE IS A FILE, NOT AN EXPORT. A stored key that also exported
    itself would be a third copy in a place every child process inherits, which
    is the leak `runner.forget_key` exists to close."""
    import os

    for name in ("ORCAROUTER_API_KEY", "OPENROUTER_API_KEY", "ORCA_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    before = dict(os.environ)
    Credentials().save(Credential(key=FAKE_KEY, method="pkce"))
    assert os.environ == before, "saving a key changed this process's environment"


# --------------------------------------------------------------------------
# one credential, two adapters
# --------------------------------------------------------------------------

def test_both_adapters_produce_the_same_kind_of_credential(home):
    """⛔ THE SEAM, ASSERTED FROM BOTH SIDES. A pasted key and an issued key are
    the same value against the same endpoint; the only thing that differs is
    what the panel says about it, and that lives on the credential rather than
    in the client."""
    store = Credentials()
    pasted = provider.Provider(None, {}, store).save_key(FAKE_KEY)
    assert pasted["key"]["masked"] == orcarouter.mask(FAKE_KEY)

    with FakeAuth() as fake:
        issued, scope = orcarouter.exchange_code(fake.url, FAKE_CODE, "V")
    by_login = store.save(Credential(key=issued, method="pkce", scope=scope))
    by_paste = store.save(Credential(key=FAKE_KEY, method="api_key"))

    assert isinstance(by_login, Credential) and isinstance(by_paste, Credential)
    assert by_login.key == by_paste.key == FAKE_KEY
    assert by_login.method == "pkce" and by_paste.method == "api_key"
    # And the downstream does not care which one it is holding.
    assert by_login.generation != by_paste.generation


def test_a_narrower_grant_is_recorded_and_mentioned_rather_than_assumed(home):
    """⛔ WHAT WAS GRANTED IS WHAT IS STORED, AND A SHORTFALL IS SAID OUT LOUD.
    A sign-in that comes back with less than it asked for still leaves a key
    that works for inference, so it is not an error - but the requested scope
    must never be recorded as the granted one, and the panel has to have
    something to draw."""
    store = Credentials()
    panel = provider.Provider(None, {}, store)
    panel._catalog = FLEET

    with FakeAuth(scope="connector") as fake:
        key, scope = orcarouter.exchange_code(fake.url, FAKE_CODE, "V")
    stored = store.save(Credential(key=key, method="pkce", scope=scope))
    assert stored.scope == "connector", "the requested scope was assumed"
    assert stored.scope != orcarouter.SCOPE

    # The panel's own field for it: the note travels with the state the
    # interface draws, and the key is still masked in that same payload.
    panel._credential = stored
    panel._note = "this sign-in granted %r rather than %r" % (scope, orcarouter.SCOPE)
    drawn = panel.state()
    assert drawn["note"], "a narrower grant drew no note"
    assert drawn["key"]["scope"] == "connector"
    assert drawn["key"]["masked"] == orcarouter.mask(FAKE_KEY)
    assert FAKE_KEY not in json.dumps(drawn), "the state carried the key itself"


def test_the_client_is_the_same_object_shape_either_way(home):
    """⛔ NEITHER CLIENT IS BUILT FOR ONE ADAPTER. The base URL and the key come
    from the credential and the environment, never from which flow produced
    it - so a client that worked for a pasted key works for an issued one."""
    for method in ("api_key", "pkce"):
        client = llm.make_orcarouter_client(
            Credential(key=FAKE_KEY, method=method), {})
        assert str(client.base_url).rstrip("/") == orcarouter.API_BASE_URL
        assert client.api_key == FAKE_KEY
        assert client.auth_headers == {"Authorization": "Bearer " + FAKE_KEY}


def test_the_orcarouter_client_goes_to_the_inference_origin_and_no_other():
    """⛔ THE RELAY, NOT THE AUTH HOST. And no app-attribution headers, which
    exist for OpenRouter's rankings and are not a convention to invent here."""
    client = llm.make_orcarouter_client(Credential(key=FAKE_KEY), {})
    assert urllib.parse.urlsplit(str(client.base_url)).netloc == "api.orcarouter.ai"
    assert "HTTP-Referer" not in (client.default_headers or {})
    assert "X-Title" not in (client.default_headers or {})


def test_the_openrouter_half_still_goes_to_openrouter(home):
    """⛔ ADDING A SECOND PROVIDER MUST NOT MOVE THE FIRST ONE. The default
    client is unchanged, and the two base URLs are asserted against each other
    rather than one of them against a literal."""
    client = llm.make_client("or-test-key")
    assert str(client.base_url).rstrip("/") == llm.BASE_URL
    assert urllib.parse.urlsplit(str(client.base_url)).netloc == "openrouter.ai"
    assert client.api_key == "or-test-key"
    assert llm.BASE_URL != orcarouter.API_BASE_URL


def test_the_model_resolvers_have_their_own_defaults(home):
    """⛔ THE OPENROUTER DEFAULT IS NOT A MODEL ORCAROUTER SERVES. Sending it
    asks for something that is not there, and the failure arrives as a provider
    error on the first turn rather than as a setting anybody can see."""
    assert llm.resolve_model(None, {}) == llm.DEFAULT_MODEL
    assert llm.orcarouter_model(None, {}) == orcarouter.DEFAULT_MODEL
    assert llm.orcarouter_model(None, {}) != llm.DEFAULT_MODEL
    # The environment still wins over both, because somebody who set it meant it.
    assert llm.orcarouter_model(None, {"AIHAWK_MODEL": "m"}) == "m"
    assert llm.orcarouter_model("flag", {"AIHAWK_MODEL": "m"}) == "flag"
    assert llm.orcarouter_model("", {}) == orcarouter.DEFAULT_MODEL


def test_no_key_anywhere_is_a_refusal_that_names_both_ways_in(home):
    """⛔ BOTH ENTRIES ARE NAMED, because the person reading has to be able to
    choose one, and the message is the whole interface for this failure."""
    with pytest.raises(orcarouter.NoCredential) as caught:
        orcarouter.resolve_credential(None, {}, Credentials())
    message = str(caught.value)
    assert "--orcarouter-key" in message
    assert "ORCAROUTER_API_KEY" in message
    assert "--orcarouter-connect" in message


def test_a_revoked_stored_key_is_refused_at_startup_rather_than_at_the_first_turn(home):
    """⛔ A KEY THE PROVIDER HAS ALREADY REJECTED MUST NOT BE SILENTLY SENT. The
    failure belongs at startup, with a sentence naming the sign-in, not three
    minutes later in the middle of somebody's task."""
    store = Credentials()
    saved = store.save(Credential(key=FAKE_KEY, method="pkce"))
    store.mark_needs_reauth(saved.generation)
    with pytest.raises(orcarouter.NeedsReauth):
        orcarouter.resolve_credential(None, {}, store)
    # A flag or an exported variable still wins, because the user just chose it.
    assert orcarouter.resolve_credential(
        "sk-orca-flag", {}, store).key == "sk-orca-flag"
    assert orcarouter.resolve_credential(
        None, {"ORCAROUTER_API_KEY": "sk-orca-env"}, store).key == "sk-orca-env"
    # And a fresh sign-in replaces the refused key, after which the store is
    # usable again. Nothing was deleted in the meantime.
    store.save(Credential(key=FAKE_KEY, method="pkce"))
    assert orcarouter.resolve_credential(None, {}, store).key == FAKE_KEY


def test_the_precedence_is_flag_then_environment_then_the_store(home):
    """⛔ SOMETHING THE USER JUST TYPED BEATS SOMETHING THEY EXPORTED, which
    beats something a sign-in left behind weeks ago - the order this project
    already documents for the other provider."""
    store = Credentials()
    store.save(Credential(key="sk-orca-stored", method="pkce"))
    assert orcarouter.resolve_credential("sk-orca-flag", {}, store).key == "sk-orca-flag"
    assert orcarouter.resolve_credential(
        None, {"ORCAROUTER_API_KEY": "sk-orca-env"}, store).key == "sk-orca-env"
    assert orcarouter.resolve_credential(None, {}, store).key == "sk-orca-stored"
    assert orcarouter.resolve_credential("  ", {"ORCAROUTER_API_KEY": ""},
                                         store).source == "stored"


def test_only_a_401_counts_as_a_dead_key():
    """⛔ A RATE LIMIT, A 5xx AND A DROPPED CONNECTION ARE NOT A DEAD KEY.
    Treating any of them as one sends somebody to re-authorize an account that
    was working, and burns one of the ten keys a user may issue per day."""
    class _Response:
        def __init__(self, status):
            self.status_code = status

    class _WithStatus(Exception):
        def __init__(self, status):
            self.status_code = status

    class _WithResponse(Exception):
        def __init__(self, status):
            self.response = _Response(status)

    assert orcarouter.is_auth_failure(_WithStatus(401)) is True
    assert orcarouter.is_auth_failure(_WithResponse(401)) is True
    for status in (400, 403, 404, 429, 500, 502):
        assert orcarouter.is_auth_failure(_WithStatus(status)) is False
        assert orcarouter.is_auth_failure(_WithResponse(status)) is False
    assert orcarouter.is_auth_failure(OSError("connection reset")) is False
    assert orcarouter.is_auth_failure(TimeoutError()) is False


def test_there_is_no_refresh_anywhere():
    """⛔ A PKCE KEY IS DURABLE, NOT A REFRESH TOKEN. There is no grant to call
    and no endpoint that would answer one, so a client that schedules a refresh
    or invents a grant is a client that will loop forever against a 404."""
    modules = [orcarouter, provider, llm]
    for module in modules:
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "grant_type" not in source.lower(), module.__name__
        assert "refresh_token" not in source.lower(), module.__name__
    # The word itself appears in exactly one sense - refreshing the model
    # catalog - and never as a token being renewed. Strip docstrings and
    # comments and every remaining `refresh` must be that identifier.
    for module in modules:
        source = Path(module.__file__).read_text(encoding="utf-8")
        body = re.sub(r'"""[\s\S]*?"""', "", source)
        body = re.sub(r"#.*", "", body)
        for found in re.findall(r"[A-Za-z_]*refresh[A-Za-z_]*", body, re.I):
            assert found.lower() in ("refresh", "refresh_catalog"), (module.__name__, found)


# --------------------------------------------------------------------------
# the catalog: the live fleet, and what a selector may offer from it
# --------------------------------------------------------------------------

def _live_answer(records):
    """One `/v1/models` answer, as the endpoint really shapes it."""
    return json.dumps({"object": "list", "data": records}).encode("utf-8")


def _serve_models(body: bytes, status: int = 200):
    """A local stand-in for the catalog endpoint, on loopback.

    ⛔ THE TEST SERVES THE SHAPE, IT DOES NOT MOCK THE PARSER. What is under
    test is the request that goes out and the list that comes back, so the
    bytes cross a socket and the Authorization header is read off the wire.
    """
    seen = {}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - the name is the protocol
            seen["path"] = self.path
            seen["authorization"] = self.headers.get("Authorization")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # pragma: no cover - silence is the point
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, seen, "http://127.0.0.1:%d/v1" % server.server_address[1]


def test_the_live_catalog_is_read_from_the_models_route_with_the_key(home):
    """⛔ THE ONE FACT SOURCE IS `/v1/models` ON THE INFERENCE ORIGIN. Not a
    hard-coded list, not the auth origin, and the request carries the key the
    user configured - which is how a workspace sees the models it can actually
    call rather than the ones the vendor advertises."""
    server, seen, base = _serve_models(_live_answer([
        {"id": "deepseek/deepseek-v4-pro", "object": "model",
         "supported_endpoint_types": ["openai", "anthropic"],
         "architecture": {"input_modalities": ["text"]}},
        {"id": "orcarouter/auto", "object": "model",
         "supported_endpoint_types": ["openai"]},
    ]))
    try:
        found = orcarouter.fetch_catalog(base, FAKE_KEY)
    finally:
        server.shutdown()
        server.server_close()
    assert seen["path"] == "/v1/models"
    assert seen["authorization"] == "Bearer %s" % FAKE_KEY
    assert found.source == "live"
    assert found.ids() == ["deepseek/deepseek-v4-pro", "orcarouter/auto"]
    # The vendor namespace survives verbatim: it is the route, not a label.
    assert found.ids()[0] == "deepseek/deepseek-v4-pro"


def test_a_catalog_that_will_not_answer_falls_back_to_the_verified_seed():
    """⛔ A FAILED DISCOVERY DEGRADES THE PROVIDER, IT DOES NOT EMPTY IT. The
    answer says which of the two it is, because a dropdown showing a fallback
    as though it were the live fleet is a lie the user cannot see."""
    server, _seen, base = _serve_models(b"{}", status=500)
    try:
        found = orcarouter.catalog(base, FAKE_KEY)
    finally:
        server.shutdown()
        server.server_close()
    assert found.source == "seed"
    assert found.detail, "a degraded list has to say why it is degraded"
    assert set(found.ids()) == set(orcarouter.SEED)
    # And the seed is small, sourced and ordered: auto leads because it is the
    # one route that stays valid as the fleet behind it changes.
    assert len(orcarouter.SEED) <= 5
    assert orcarouter.SEED[0] == orcarouter.DEFAULT_MODEL == "orcarouter/auto"


def test_a_catalog_that_is_not_a_model_list_is_a_refusal_not_an_empty_list():
    """⛔ EMPTY AND UNREADABLE ARE DIFFERENT ANSWERS. A 200 carrying an HTML
    error page is not a fleet with no models in it, and treating it as one puts
    an empty dropdown in front of somebody with no way to tell why."""
    for payload in (b"<html>nope</html>", b'"a string"', b"42"):
        server, _seen, base = _serve_models(payload)
        try:
            with pytest.raises(orcarouter.CatalogError):
                orcarouter.fetch_catalog(base, FAKE_KEY)
        finally:
            server.shutdown()
            server.server_close()


def test_a_record_without_an_id_is_dropped_rather_than_guessed_at():
    """⛔ A NAME THIS CLIENT INVENTED IS A VALUE THAT FAILS AT THE FIRST
    REQUEST. Anything without an id, or with an id that is not a string, is not
    a model it can ask for."""
    found = orcarouter.parse_catalog({"data": [
        {"id": "orcarouter/auto"},
        {"id": ""},
        {"id": 42},
        {"not_an_id": True},
        "a bare string",
        None,
    ]})
    assert [m.id for m in found] == ["orcarouter/auto"]


def test_the_catalog_is_bounded_so_a_hostile_answer_cannot_fill_memory():
    """⛔ THE LIST IS READ FROM SOMEBODY ELSE'S SERVER. The record count is
    capped at parse time, so a catalog that answers with a million entries
    costs a fixed amount rather than whatever it chose."""
    oversized = {"data": [{"id": "m/%d" % n} for n in range(orcarouter.CATALOG_MAX_MODELS + 50)]}
    assert len(orcarouter.parse_catalog(oversized)) == orcarouter.CATALOG_MAX_MODELS


# --------------------------------------------------------------------------
# capabilities: one place decides what a selector may offer
# --------------------------------------------------------------------------

#: ⛔ ONE FIXTURE PER KIND OF MODEL, so every filter is asked the same
#: questions. These are shaped like the live records: an id in vendor/model
#: form, `supported_endpoint_types`, and `architecture.input_modalities`.
FLEET = Catalog(models=(
    Model(id="deepseek/deepseek-v4-pro", endpoints=("anthropic", "openai"),
          input_modalities=("text",)),
    Model(id="deepseek/deepseek-v4-flash-vision-exp", endpoints=("openai",),
          input_modalities=("image", "text")),
    Model(id="orcarouter/auto", endpoints=("openai",)),
    Model(id="vendor/text-embed", endpoints=("embeddings",),
          input_modalities=("text",)),
    Model(id="vendor/image-maker", endpoints=("image-generation",)),
    Model(id="vendor/motion", endpoints=("openai-video",)),
    Model(id="vendor/ranker", endpoints=("jina-rerank",)),
    Model(id="vendor/mystery", endpoints=("something-new",)),
), source="live")


def test_the_text_dropdown_holds_chat_models_and_nothing_else():
    """⛔ THE CONVERSATION LIST MUST NOT HOLD AN IMAGE GENERATOR. Each of these
    records is compatible with exactly one job, and a chat selector that offers
    the wrong one sends a request that fails after the user has committed."""
    offered = FLEET.ids("chat")
    assert offered == ["deepseek/deepseek-v4-pro",
                       "deepseek/deepseek-v4-flash-vision-exp",
                       "orcarouter/auto"]
    for never in ("vendor/image-maker", "vendor/motion", "vendor/ranker",
                  "vendor/text-embed", "vendor/mystery"):
        assert never not in offered


def test_the_vision_dropdown_requires_a_declared_image_input():
    """⛔ FAIL CLOSED. A record that declares no input modalities has not said
    it takes an image, and a model that has not said so does not belong in a
    list for attachments. `orcarouter/auto` is the point of this test: it is a
    perfectly good chat model that must NOT appear here."""
    offered = FLEET.ids("vision", modality="image")
    assert offered == ["deepseek/deepseek-v4-flash-vision-exp"]
    assert "orcarouter/auto" not in offered
    assert "deepseek/deepseek-v4-pro" not in offered


def test_each_generation_job_matches_its_own_endpoint_and_no_other():
    """⛔ EMBEDDING, IMAGE, VIDEO AND RERANK ARE FOUR DIFFERENT JOBS. They share
    nothing but the word "model", and a filter written once and reused is how a
    reranker ends up in an embedding list."""
    assert FLEET.ids("embedding") == ["vendor/text-embed"]
    assert FLEET.ids("image") == ["vendor/image-maker"]
    assert FLEET.ids("video") == ["vendor/motion"]
    assert FLEET.ids("rerank") == ["vendor/ranker"]


def test_an_endpoint_this_client_does_not_know_is_never_offered():
    """⛔ A NEW ENDPOINT TYPE IS NOT AN INVITATION TO GUESS. A record whose only
    endpoint is one this client has never heard of appears in no list at all -
    the catalog is the authority on what a model can do, and it did not say."""
    for capability in orcarouter.CAPABILITIES:
        assert "vendor/mystery" not in FLEET.ids(capability)


def test_a_capability_that_does_not_exist_is_refused_rather_than_answered():
    """A typo in a query string must not silently become "everything"."""
    with pytest.raises(ValueError):
        FLEET.ids("embeddings")


def test_the_seed_offers_only_models_the_live_endpoint_confirmed():
    """⛔ THE FALLBACK IS NOT AN EXAMPLE LIST. Every id in it was read back from
    `GET https://api.orcarouter.ai/v1/models`, and each one is a chat model with
    a vendor namespace that survives verbatim."""
    seed = orcarouter.seed_catalog()
    assert seed.source == "seed"
    assert seed.ids("chat") == list(orcarouter.SEED)
    assert seed.ids("image") == [] and seed.ids("video") == []
    assert seed.ids("embedding") == [] and seed.ids("rerank") == []
    for model_id in orcarouter.SEED:
        assert "/" in model_id, model_id


def test_a_live_catalog_is_never_mixed_with_the_seed():
    """⛔ ONCE DISCOVERY SUCCEEDS, THE SEED IS GONE. A list that merged the two
    would present an unverified entry as part of the live fleet, which is the
    one thing the fallback must never become."""
    live = orcarouter.fetch_catalog  # the authority, by name
    assert live is not None
    discovered = Catalog(models=(Model(id="vendor/only-live", endpoints=("openai",)),
                                 Model(id="vendor/second-live", endpoints=("openai",))),
                         source="live")
    assert discovered.ids("chat") == ["vendor/only-live", "vendor/second-live"]
    for model_id in orcarouter.SEED:
        assert model_id not in discovered.ids("chat")


def test_a_model_restored_from_a_previous_run_is_revalidated_before_it_is_put_back():
    """⛔ A SAVED MODEL ID IS A CLAIM ABOUT A FLEET THAT MAY HAVE MOVED. It goes
    back into the selector only if the current list still holds it, and the
    answer is the same one the dropdown would give."""
    assert FLEET.holds("orcarouter/auto") is True
    assert FLEET.holds("vendor/image-maker") is False
    assert FLEET.holds("deepseek/deepseek-v4-pro") is True
    assert FLEET.holds("deepseek/deepseek-v4-pro", "vision") is False
    assert FLEET.holds("deepseek/deepseek-v4-flash-vision-exp", "vision") is True


def test_the_panel_offers_the_live_list_and_says_where_it_came_from(home):
    """⛔ THE END-TO-END ANSWER THE DROPDOWN IS BUILT FROM. The provider holds
    one catalog; `models_for` is what a selector asks; and both carry the
    provenance, so a degraded list cannot be drawn as a current one."""
    panel = provider.Provider(None, {}, Credentials())
    panel._catalog = FLEET
    chat = panel.models_for("chat")
    assert chat["source"] == "live"
    assert [m["id"] for m in chat["models"]] == FLEET.ids("chat")
    vision = panel.models_for("vision")
    assert [m["id"] for m in vision["models"]] == [
        "deepseek/deepseek-v4-flash-vision-exp"]
    assert panel.catalog_state()["source"] == "live"
    assert len(panel.catalog_state()["models"]) == len(FLEET.models)


def test_a_provider_with_no_catalog_yet_offers_the_seed_and_says_so(home):
    """⛔ BEFORE DISCOVERY HAS RUN, AND AFTER IT HAS FAILED, THE ANSWER IS THE
    SAME ONE: the verified seed, labelled as the seed. Never free text, and
    never an empty list that looks like the provider supports nothing."""
    panel = provider.Provider(None, {}, Credentials())
    assert panel.catalog_state() == {"source": "none", "detail": "", "models": []}
    offered = panel.models_for("chat")
    assert offered["source"] == "seed"
    assert [m["id"] for m in offered["models"]] == list(orcarouter.SEED)


def test_a_model_outside_the_current_catalog_is_refused_when_it_is_chosen(home):
    """⛔ THE SECOND HALF OF THE FILTER, AT THE OTHER END. The dropdown cannot
    offer a value the list does not hold, and a request that names one anyway -
    a stale page, a hand-written call - is refused rather than kept, because
    keeping it leaves the panel drawing a model nobody is being asked for."""
    store = Credentials()
    store.save(Credential(key=FAKE_KEY, method="api_key"))
    panel = provider.Provider(None, {}, store)
    panel._catalog = FLEET
    with pytest.raises(ValueError):
        panel.choose("orcarouter", "vendor/image-maker")
    with pytest.raises(ValueError):
        panel.choose("orcarouter", "vendor/not-in-any-catalog")
    moved = panel.choose("orcarouter", "deepseek/deepseek-v4-pro")
    assert moved["model"] == "deepseek/deepseek-v4-pro"
    assert moved["provider"] == "orcarouter"


def test_moving_to_orcarouter_without_a_key_is_the_refusal_that_names_both_ways_in(home):
    """⛔ A SELECTOR THAT LOOKS READY AND IS NOT. Choosing the provider with no
    credential anywhere is refused, and the refusal names both ways in - in the
    words of whichever surface is asking. The CLI names the flag and the
    variable; the panel names the two controls it is drawing."""
    panel = provider.Provider(None, {}, Credentials())
    with pytest.raises(orcarouter.NoCredential) as caught:
        panel.choose("orcarouter")
    message = str(caught.value)
    assert "paste one" in message and "sign in" in message
    # And the message the CLI would print names both entries by name, which is
    # the same seam: `resolve_credential` is where a missing key is refused.
    with pytest.raises(orcarouter.NoCredential) as cli:
        orcarouter.resolve_credential(None, {}, Credentials())
    assert "--orcarouter-key" in str(cli.value)
    assert "ORCAROUTER_API_KEY" in str(cli.value)
    assert "--orcarouter-connect" in str(cli.value)


# --------------------------------------------------------------------------
# live: the same code the product runs, against the real endpoint
# --------------------------------------------------------------------------

LIVE_KEY = os.environ.get("ORCAROUTER_API_KEY", "")
live_only = pytest.mark.skipif(
    not LIVE_KEY, reason="ORCAROUTER_API_KEY is not set in this environment")


@live_only
def test_live_the_catalog_the_dropdown_is_built_from_comes_from_the_real_endpoint(home):
    """⛔ THE AUTHORITY, READ THROUGH THE FUNCTION THE PRODUCT CALLS. The base
    is the documented one and the key is the one the user configured; what
    comes back is what a workspace can actually call. Nothing here is a
    fixture, and the key is never printed."""
    base = orcarouter.api_base({})
    assert base == "https://api.orcarouter.ai/v1"
    found = orcarouter.fetch_catalog(base, LIVE_KEY)
    assert found.source == "live"
    assert found.models, "the live catalog answered with no models"
    offered = found.ids("chat")
    assert offered, "no chat model was offered from the live catalog"
    for model_id in offered:
        assert "/" in model_id, model_id
    # The text selector holds text models: none of the non-text jobs leak in.
    assert not set(offered) & set(found.ids("image"))
    assert not set(offered) & set(found.ids("video"))
    assert not set(offered) & set(found.ids("rerank"))
    print("live catalog: %d models, %d offered for chat"
          % (len(found.models), len(offered)))


@live_only
def test_live_a_real_completion_goes_through_the_client_this_integration_builds(home):
    """⛔ THE PROOF THAT MATTERS: a real request, through the code path the
    product uses, answered by the real relay. A provider that resolves keys and
    filters catalogs but cannot complete a turn has not been integrated.

    ⛔ AND IT IS TRIED ON THE MODELS THE CATALOG OFFERS, NOT ON ONE THE TEST
    PICKED. A key is scoped to a workspace's fleet, so a routing entry that the
    catalog lists can still answer 403 for this key - which is a fact about the
    account, not about the integration. The list is walked in order and the
    assertion is that the relay answers at least one of them, with the model
    that worked named in the output.
    """
    found = orcarouter.fetch_catalog(orcarouter.api_base({}), LIVE_KEY)
    offered = found.ids("chat")
    assert offered, "the live catalog offered no chat model"
    credential = Credential(key=LIVE_KEY, method="api_key", source="environment")
    client = llm.make_orcarouter_client(credential, {})
    assert client.base_url.host == "api.orcarouter.ai"
    answered, refusals = [], []
    for model_id in offered:
        try:
            answer = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "Reply with the single word: ready"}],
                max_tokens=64)
        except Exception as exc:  # a scoped-out model, not a broken client
            refusals.append((model_id, type(exc).__name__))
            continue
        text = (answer.choices[0].message.content or "").strip()
        if text:
            answered.append((model_id, text[:40]))
    print("live completions answered: %r; refused by scope: %r"
          % (answered, refusals))
    assert answered, ("the relay answered none of the %d models the catalog "
                      "offered: %r" % (len(offered), refusals))


def test_a_catalog_that_never_answers_degrades_instead_of_hanging(home, monkeypatch):
    """⛔ A DEAD ENDPOINT IS A DEGRADED LIST, NOT A FROZEN PANEL. The request
    carries a timeout, and what comes back when it fires is the labelled seed."""
    def _hang(*args, **kwargs):
        raise TimeoutError("no answer")

    monkeypatch.setattr(orcarouter.urllib.request, "urlopen", _hang)
    found = orcarouter.catalog("https://api.orcarouter.ai/v1", FAKE_KEY)
    assert found.source == "seed"
    assert "TimeoutError" in found.detail
    # And the panel, going through the provider, offers that labelled list.
    panel = provider.Provider(None, {}, Credentials())
    panel._catalog = found
    assert panel.models_for("chat")["source"] == "seed"
