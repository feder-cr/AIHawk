"""OrcaRouter: the second provider, and the two ways to hold its key.

⛔ TWO AUTHENTICATION ENTRIES, ONE CREDENTIAL. OrcaRouter is reached with an
ordinary ``sk-orca-...`` key, and there are two honest ways to get one: paste a
key the user already has, or sign in and have one issued. They serve different
people - a user with a key in a password manager, and a user with an account and
no key - and they fail differently, so they stay two explicit choices rather
than one button that sometimes asks for a key and sometimes opens a browser.

What they share is everything downstream. ``Credential`` is the seam: the
provider client, the model catalog and the inference request all take a key and
none of them can tell which adapter produced it. Written once here rather than
per call site, because a rule about a secret is a rule that stops being applied
one call site after the one it was written for.

⛔ THE TWO ORIGINS ARE NOT DERIVED FROM EACH OTHER. Authentication is
``www.orcarouter.ai``; inference and model discovery are ``api.orcarouter.ai``
under ``/v1``. The two look like one host with a prefix swapped, which is
exactly the mistake this module exists to prevent: ``api.orcarouter.ai/v1/auth/keys``
is a 404, and a client that builds it from the inference base looks like a
routing bug on the provider's side rather than a bug here. ``auth_base`` and
``api_base`` are separate functions over separate variables, and nothing joins
them.

⛔ THE EXCHANGE RETURNS A DURABLE KEY, NOT A REFRESH TOKEN. There is no refresh
grant to call, and there is no endpoint that would answer one. A key that the
user revokes stops working and the only recovery is to sign in again, so nothing
here schedules a refresh or fabricates one.
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Optional

from . import storage

#: Where a key is expected to live. Read from the environment by name, and
#: stripped from the environment the browser server is handed by value.
KEY_VARIABLE = "ORCAROUTER_API_KEY"

#: Authentication and inference, and the reason they are two constants.
AUTH_BASE_URL = "https://www.orcarouter.ai"
API_BASE_URL = "https://api.orcarouter.ai/v1"

#: The consent screen, and the one endpoint that redeems an auth code. The
#: second is NOT under ``/v1``: it is ``/api/v1/auth/keys`` on the auth origin,
#: and the relay's own ``/v1`` prefix has nothing to do with it.
AUTHORIZE_PATH = "/auth"
EXCHANGE_PATH = "/api/v1/auth/keys"

#: The loopback listener's one route, and the literal that asks for a code
#: instead of a redirect. ``oob`` is spelled out rather than omitted so the mode
#: is asked for rather than guessed at.
CALLBACK_PATH = "/cb"
OOB = "oob"

#: The consent screen presents this as a claim about who is asking, so it is
#: the product's name and not the person's.
APP_NAME = "AIHawk"

#: What the flow asks for. ``api`` is the only scope this product can use: it
#: holds no connector.
SCOPE = "api"

#: Self-hosted deployments may run one origin or two. The shared value is a
#: fallback and the explicit ones win, which is the order a person setting only
#: one of them expects.
AUTH_BASE_VARIABLE = "ORCA_AUTH_BASE_URL"
API_BASE_VARIABLE = "ORCA_API_BASE_URL"
SHARED_BASE_VARIABLE = "ORCA_BASE_URL"

#: How long an exchange may take, and how long a catalog fetch may take. Both
#: are short on purpose: one is in front of a person who is waiting for a
#: browser to open, the other is in front of a settings panel.
EXCHANGE_TIMEOUT = 30.0
CATALOG_TIMEOUT = 10.0

#: ⛔ A CATALOG RESPONSE IS NOT TRUSTED TO BE SMALL. It comes from a service,
#: not from this process, so the bytes, the item count and the shape of each
#: item are all bounded here. Without a ceiling a single response can be read
#: into memory until the machine swaps, which is a denial of service that needs
#: no attacker - a misconfigured proxy answering with a directory listing is
#: enough.
CATALOG_MAX_BYTES = 2_000_000
CATALOG_MAX_MODELS = 2_000

#: Where a person manages and revokes the keys this app holds. Quoted in the
#: settings panel because revocation is the one thing a user needs and cannot
#: guess the address of, and the panel is the one thing that draws it.
CONSOLE_URL = "https://www.orcarouter.ai/console/authorized-apps"

#: The endpoint types a text conversation can be spoken over. A record that
#: carries none of these cannot be asked for prose, whatever it is called.
TEXT_ENDPOINTS = ("openai", "anthropic", "gemini", "openai-response")

#: Endpoint types that name a job which is NOT a text conversation. A record
#: carrying one of these is filtered out of the chat list even when it also
#: speaks an OpenAI-compatible dialect, because the dialect is how it is called
#: and not what it does.
NON_TEXT_ENDPOINTS = ("image-generation", "openai-video", "jina-rerank",
                      "embeddings", "rerank")

#: The capabilities a selector can be built for. One name per job the interface
#: can actually ask for; anything else has no entry point and therefore no
#: filter.
CAPABILITIES = ("chat", "vision", "embedding", "image", "video", "rerank")

#: What each capability requires of a record, as endpoint types. A capability
#: whose requirement is empty is satisfied by the chat rule instead.
CAPABILITY_ENDPOINTS = {
    "embedding": ("embeddings",),
    "image": ("image-generation",),
    "video": ("openai-video",),
    "rerank": ("jina-rerank",),
}

#: ⛔ A FALLBACK, NOT A CATALOG. Live discovery is the authority; this is what
#: a fresh installation can offer while the catalog endpoint is slow or down,
#: and it is deliberately small. Each id was read back from
#: ``GET https://api.orcarouter.ai/v1/models`` - they are not names that look
#: plausible - and ``orcarouter/auto`` leads because it is the one route that
#: stays valid as the fleet behind it changes.
#:
#: ``orcarouter/auto`` IS ALSO THE DEFAULT MODEL, and that is why the seed is
#: ordered the way it is. The catalog advertises a workspace's real fleet, which
#: for an account with nothing enabled is four routing entries; auto is the one
#: of them that is a route rather than a specific model, so a first run works
#: before anybody has chosen anything.
SEED = (
    "orcarouter/auto",
    "deepseek/deepseek-v4-pro",
    "deepseek/deepseek-v4-flash",
)

#: The model a run starts on when nothing else was chosen.
DEFAULT_MODEL = SEED[0]


class CatalogError(Exception):
    """The catalog endpoint could not be read, or answered something that is
    not a model list. Its own class so the caller can fall back to the seed
    rather than treating a provider outage as a configuration error."""


class PkceError(Exception):
    """An authorization attempt ended without a key.

    ⛔ ONE CLASS, AND THE MESSAGE IS THE INTERFACE. A denial, a state that does
    not match, an expired code and a network failure all end here, and what
    separates them is a sentence a person can act on - "you declined", "start
    again", "check your connection" - rather than a type nobody catches. The
    message never carries the code, the verifier or the response body.
    """


@dataclass(frozen=True)
class Model:
    """One record from the catalog, reduced to what a selector needs.

    ⛔ THE ID IS KEPT VERBATIM, vendor prefix included. ``deepseek/deepseek-v4-pro``
    is the name the relay routes on; a selector that showed the tail of it would
    be showing something the user cannot send.
    """

    id: str
    endpoints: tuple = ()
    input_modalities: tuple = ()
    owned_by: str = ""

    @property
    def name(self) -> str:
        """What the dropdown shows. The id, because the id is the route."""
        return self.id

    @property
    def modalities(self) -> tuple:
        """The input modalities this model declares, minus the one every model
        has. Empty means the record said nothing, which is not the same as
        saying "text only" and is treated as the narrower answer."""
        return tuple(m for m in self.input_modalities if m != "text")


@dataclass(frozen=True)
class Catalog:
    """What can be asked for, and whether that list is the live one.

    ⛔ ``source`` IS PART OF THE VALUE, NOT A LOG LINE. The panel draws a
    degraded state from it, and a list that cannot say whether it is current is
    a list that shows a stale fleet as though it were the live one.
    """

    models: tuple
    source: str
    detail: str = ""

    def ids(self, capability: str = "chat", *, modality: Optional[str] = None) -> list:
        return [m.id for m in models_for(self, capability, modality=modality)]

    def holds(self, model_id: str, capability: str = "chat") -> bool:
        """Whether this catalog can still offer that model for that job.

        ⛔ ASKED BEFORE A SAVED MODEL IS PUT BACK. A model id restored from a
        previous run is a claim about a fleet that may have moved, and putting
        it back unchecked is how a dropdown ends up holding a value that is not
        in its own list.
        """
        return any(m.id == model_id
                   for m in models_for(self, capability))


def seed_catalog() -> Catalog:
    """The verified fallback, as a Catalog. Built rather than stored so it
    cannot be mutated by a caller that found it convenient."""
    return Catalog(models=tuple(Model(id=m, endpoints=("openai",))
                                for m in SEED),
                   source="seed",
                   detail="the verified seed: live discovery has not succeeded")


def _origin(value: str, *, what: str) -> str:
    """One base URL, validated. HTTPS everywhere, HTTP only for loopback.

    ⛔ THE LOOPBACK EXCEPTION IS FOR DEVELOPMENT AND IT IS THE ONLY ONE. A
    self-hosted deployment on a LAN address is a real case, and it is still
    required to be HTTPS: plain HTTP to anything but the machine the request
    starts on puts a credential on the wire in the clear.
    """
    text = (value or "").strip().rstrip("/")
    if not text:
        raise ValueError("no %s" % what)
    parts = urllib.parse.urlsplit(text)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("%s is not an http(s) URL: %s" % (what, text))
    if parts.scheme == "http" and parts.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("%s must be https unless it is loopback: %s" % (what, text))
    return text


def auth_base(env: Mapping[str, str]) -> str:
    """Where authentication happens. Its own function over its own variables.

    ⛔ NEVER DERIVED FROM THE INFERENCE BASE. The two public origins are
    different hosts with different path layouts, and every attempt to compute
    one from the other produces a URL that 404s. The shared variable exists for
    a self-hosted deployment that genuinely runs one origin, and it is a
    fallback rather than a join.
    """
    return _origin(env.get(AUTH_BASE_VARIABLE)
                   or env.get(SHARED_BASE_VARIABLE) or AUTH_BASE_URL,
                   what="the OrcaRouter auth base")


def api_base(env: Mapping[str, str]) -> str:
    """Where inference and model discovery happen. ``/v1`` is part of it."""
    return _origin(env.get(API_BASE_VARIABLE)
                   or env.get(SHARED_BASE_VARIABLE) or API_BASE_URL,
                   what="the OrcaRouter API base")


# --- PKCE ---------------------------------------------------------------------


def _b64url(raw: bytes) -> str:
    """base64url with no padding, which is what the challenge must be."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def make_verifier() -> str:
    """A fresh verifier, from a cryptographic RNG, for ONE attempt.

    ⛔ FRESH PER ATTEMPT AND FROM ``secrets``. A verifier reused across attempts,
    or derived from anything guessable, is the whole protection of PKCE thrown
    away: anyone who saw the challenge once could redeem any later code. This is
    a function rather than a constant so there is no way to reach a stored one.
    """
    return _b64url(secrets.token_bytes(32))


def make_state() -> str:
    """An opaque CSRF token, fresh per attempt, echoed back verbatim."""
    return _b64url(secrets.token_bytes(16))


def challenge_for(verifier: str) -> str:
    """``base64url(sha256(verifier))``, unpadded. S256 and nothing else.

    ⛔ ``plain`` IS NOT OFFERED, INCLUDING ON THE LOOPBACK FLOW. The consent
    screen lets the user choose "show me a code" whatever callback was asked
    for, so a code can always end up in human hands - and under ``plain`` the
    challenge IS the verifier, which rode out on the authorize URL through
    browser history and any proxy in between.
    """
    return _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


def authorize_url(base: str, *, challenge: str, state: str,
                  callback_url: str) -> str:
    """The consent screen, with only the challenge - never the verifier.

    The verifier must not appear here, in a log, or anywhere else outside this
    process: it is presented once, at the exchange, and that is what binds the
    code to this attempt.
    """
    query = urllib.parse.urlencode({
        "callback_url": callback_url,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "app_name": APP_NAME,
        "scope": SCOPE,
    })
    return "%s%s?%s" % (base, AUTHORIZE_PATH, query)


def _post_json(url: str, payload: dict, timeout: float) -> dict:
    """One JSON POST, with every failure reduced to a PkceError sentence.

    ⛔ THE RESPONSE BODY IS NEVER PUT IN THE MESSAGE. On the happy path it is
    the key; on the failure path it is provider prose that may quote what was
    sent. Either way it is not something to carry into a log or a transcript, so
    what travels is a status and a fixed sentence.
    """
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            raw = answer.read(CATALOG_MAX_BYTES).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raise PkceError(_exchange_sentence(exc.code)) from None
    except (urllib.error.URLError, OSError) as exc:
        raise PkceError(
            "the authorization could not reach OrcaRouter (%s). Check the "
            "connection and start again." % type(exc).__name__) from None
    try:
        got = json.loads(raw)
    except ValueError:
        raise PkceError(
            "OrcaRouter answered something that is not JSON. Start again, and "
            "if it repeats, report it.") from None
    if not isinstance(got, dict):
        raise PkceError("OrcaRouter answered an unexpected shape. Start again.")
    return got


def _exchange_sentence(status: int) -> str:
    """What a failed exchange means, in words a person can act on.

    ⛔ 403 AND 400 ARE NOT ONE FAILURE. 403 is "that code is unknown, expired or
    already used, or the verifier does not match" - the answer is to start a new
    attempt. 400 is a downgrade defence or an unrecognised method, which is a
    bug here and not something the user did. 429 is the per-user issuance cap,
    which is the one failure where waiting is the right advice.
    """
    if status == 400:
        return ("OrcaRouter refused the exchange as malformed. Start again; if "
                "it repeats this is a bug in AIHawk, not in your account.")
    if status == 403:
        return ("that authorization code is unknown, expired or already used, "
                "or it was not issued for this attempt. Start again.")
    if status == 429:
        return ("OrcaRouter has issued as many keys for your account today as it "
                "allows. Try again tomorrow, or paste an API key instead.")
    return "OrcaRouter refused the exchange (HTTP %d). Start again." % status


def exchange_code(base: str, code: str, verifier: str,
                  *, timeout: float = EXCHANGE_TIMEOUT) -> tuple:
    """Redeem an auth code for a durable API key. Answers ``(key, scope)``.

    ⛔ ``scope`` IS WHAT WAS GRANTED, NOT WHAT WAS ASKED FOR. The flow requests
    ``api``; the answer says what the account was actually allowed to give, and
    a client that assumes its request was honoured is a client that believes it
    holds a permission it does not.
    """
    got = _post_json("%s%s" % (base, EXCHANGE_PATH), {
        "code": code,
        "code_verifier": verifier,
        "code_challenge_method": "S256",
    }, timeout)
    key = got.get("key")
    if not isinstance(key, str) or not key.strip():
        raise PkceError("OrcaRouter approved the sign-in but returned no key. "
                        "Start again.")
    return key.strip(), str(got.get("scope") or "")


# --- the two flows ------------------------------------------------------------


@dataclass
class Authorization:
    """One attempt: the secret half, the URL to open, and how a code arrives.

    ⛔ THE VERIFIER LIVES HERE AND NOWHERE ELSE UNTIL THE EXCHANGE. It is not
    passed to the page, not written to disk, not put in the URL and not printed.
    The flow object owns it, the exchange consumes it, and after that it is
    garbage.
    """

    url: str
    verifier: str = field(repr=False)
    state: str = field(repr=False)
    kind: str = "loopback"
    _server: Optional[object] = field(default=None, repr=False)
    _holder: dict = field(default_factory=dict, repr=False)
    _thread: Optional[threading.Thread] = field(default=None, repr=False)

    def __repr__(self) -> str:  # pragma: no cover - exercised through the tests
        """⛔ THE VERIFIER AND THE STATE ARE NOT IN THE REPR. A dataclass prints
        every field, and this object is exactly the one a traceback, a debugger
        or a log line would pick up. ``repr=False`` on the fields is the fix and
        this method is the proof of it."""
        return "Authorization(kind=%r, url=%r)" % (self.kind, self.url)

    def cancel(self) -> None:
        """Stop listening. Safe to call twice, and safe to call after a code
        already arrived."""
        server = self._server
        self._server = None
        if server is None:
            return
        try:
            server.shutdown()
            server.server_close()
        except Exception:  # pragma: no cover - closing twice, or already shut
            pass

    def poll(self) -> Optional[dict]:
        """What the listener has, WITHOUT waiting. None while nothing arrived.

        ⛔ THE PAGE POLLS THIS AND MUST NOT BLOCK. `await_code` is the right
        shape for a terminal, where there is one thread and one person waiting
        at it; over HTTP a blocking call holds a connection open for as long as
        the person takes in their browser, which is a request that outlives the
        page that made it. So the same state is readable in both shapes, and
        the meaning of a state mismatch is decided here once.
        """
        got = self._holder
        if not got:
            return None
        if got.get("state") != self.state:
            return {"state": "error", "detail": "state"}
        if got.get("error"):
            return {"state": "error", "detail": "declined"}
        if not got.get("code"):
            return {"state": "error", "detail": "no code"}
        return {"state": "code", "code": str(got["code"])}

    def await_code(self, timeout: float = 600.0) -> str:
        """Block until the browser comes back, or the attempt runs out.

        ⛔ THE STATE IS COMPARED BEFORE THE CODE IS LOOKED AT, and a mismatch
        ends the attempt rather than being ignored. The listener is on a port
        anything on this machine can reach, so without that comparison a page
        somebody else opened could hand this process a code.
        """
        if self._thread is not None:
            self._thread.join(timeout)
        got = self.poll()
        self.cancel()
        if got is None:
            raise PkceError("the sign-in was not completed in time. Start again.")
        if got["state"] == "error":
            if got["detail"] == "state":
                raise PkceError("the sign-in came back for a different attempt, "
                                "so it was discarded. Start again.")
            if got["detail"] == "declined":
                raise PkceError("the sign-in was declined in the browser. "
                                "Nothing was changed; you can paste an API key "
                                "instead.")
            raise PkceError("the sign-in came back without a code. Start again.")
        return got["code"]


def _loopback_authorization(base: str, opener: Callable[[str], object]) -> Authorization:
    """Flow A: listen on loopback first, so the port is known and nothing races.

    ⛔ THE LISTENER IS BOUND BEFORE THE BROWSER OPENS. Reading the URL off the
    screen and opening the browser are separated by a human; a server started
    afterwards is a window in which the redirect goes nowhere.
    """
    verifier, state = make_verifier(), make_state()
    holder: dict = {}
    landed = threading.Event()

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - the name is BaseHTTPRequestHandler's
            url = urllib.parse.urlsplit(self.path)
            if url.path != CALLBACK_PATH:
                self.send_response(404)
                self.end_headers()
                return
            query = urllib.parse.parse_qs(url.query)
            for name in ("code", "state", "error"):
                if name in query and query[name]:
                    holder[name] = query[name][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<p>OrcaRouter is connected. You can close this tab.</p>")
            landed.set()

        def log_message(self, *args):  # keep the terminal quiet
            pass

    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = authorize_url(base, challenge=challenge_for(verifier), state=state,
                        callback_url="http://127.0.0.1:%d%s" % (port, CALLBACK_PATH))
    attempt = Authorization(url=url, verifier=verifier, state=state,
                            kind="loopback", _server=server,
                            _holder=holder, _thread=thread)
    opener(url)
    return attempt


def _oob_authorization(base: str, opener: Callable[[str], object]) -> Authorization:
    """Flow B: ask for a code to be shown, and let the person paste it back.

    Chosen when there is no browser, or when this process cannot listen on
    loopback - a sandbox, a locked-down machine, a hosted deployment whose
    address is not this one. S256 is mandatory here rather than advisable, and
    it is what is sent on every flow anyway.
    """
    verifier, state = make_verifier(), make_state()
    url = authorize_url(base, challenge=challenge_for(verifier), state=state,
                        callback_url=OOB)
    opener(url)
    return Authorization(url=url, verifier=verifier, state=state, kind="oob")


def start_authorization(env: Mapping[str, str], *, oob: bool = False,
                        opener: Optional[Callable[[str], object]] = None) -> Authorization:
    """Begin one attempt, on the flow this process can actually run.

    ⛔ THE CALLER SAYS WHICH FLOW, AND THE REASON IS WHERE THIS PROCESS RUNS.
    Loopback needs a browser on this machine AND a port it can listen on;
    out-of-band needs only a browser somewhere. A process that guesses wrong
    hangs waiting for a redirect that has nowhere to land, which is the failure
    that looks like a frozen application.
    """
    base = auth_base(env)
    open_it = opener or (lambda url: webbrowser.open(url))
    if oob:
        return _oob_authorization(base, open_it)
    return _loopback_authorization(base, open_it)


# --- the catalog --------------------------------------------------------------


def _record(raw) -> Optional[Model]:
    """One catalog record, or None if it is not one.

    ⛔ UNKNOWN RECORDS ARE DROPPED, NOT GUESSED AT. A record with no id, or an
    id that is not a string, is not a model this client can ask for, and
    inventing a name for it would put a value in the dropdown that fails at the
    first request.
    """
    if not isinstance(raw, dict):
        return None
    identifier = raw.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        return None
    architecture = raw.get("architecture")
    architecture = architecture if isinstance(architecture, dict) else {}
    declared = architecture.get("input_modalities")
    modalities = tuple(sorted(str(m) for m in declared
                              if isinstance(m, str))) if isinstance(declared, (list, tuple)) else ()
    endpoints = raw.get("supported_endpoint_types")
    types = tuple(sorted(str(e) for e in endpoints
                         if isinstance(e, str))) if isinstance(endpoints, (list, tuple)) else ()
    return Model(id=identifier.strip(), endpoints=types, input_modalities=modalities,
                 owned_by=str(raw.get("owned_by") or ""))


def parse_catalog(payload) -> tuple:
    """The model records in a catalog response, bounded and filtered.

    Kept separate from the request so the shape rules can be tested against a
    literal, and so a malformed response is a raised error rather than a
    half-filled list.
    """
    if isinstance(payload, dict):
        data = payload.get("data")
    elif isinstance(payload, list):
        data = payload
    else:
        raise CatalogError("the catalog answer was not a model list")
    if not isinstance(data, list):
        raise CatalogError("the catalog answer had no model list in it")
    out = []
    for raw in data[:CATALOG_MAX_MODELS]:
        found = _record(raw)
        if found is not None:
            out.append(found)
    return tuple(out)


def fetch_catalog(base: str, key: str, *,
                  timeout: float = CATALOG_TIMEOUT) -> Catalog:
    """The live fleet, from the endpoint that owns it.

    ⛔ ``/v1/models`` ON THE INFERENCE ORIGIN, and the base already carries the
    ``/v1``. The auth origin has no models route at all, and asking it is the
    same mistake as the exchange path written the other way round.
    """
    request = urllib.request.Request(
        "%s/models" % base.rstrip("/"),
        headers={"Authorization": "Bearer %s" % key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            raw = answer.read(CATALOG_MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise CatalogError("the catalog endpoint answered HTTP %d" % exc.code) from None
    except (urllib.error.URLError, OSError) as exc:
        raise CatalogError("the catalog endpoint could not be reached (%s)"
                           % type(exc).__name__) from None
    if len(raw) > CATALOG_MAX_BYTES:
        raise CatalogError("the catalog answer was larger than this client reads")
    try:
        payload = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        raise CatalogError("the catalog answer was not JSON") from None
    return Catalog(models=parse_catalog(payload), source="live")


def catalog(base: str, key: str, *, timeout: float = CATALOG_TIMEOUT) -> Catalog:
    """The catalog to show: the live one, or the verified seed if it failed.

    ⛔ A FAILED DISCOVERY DOES NOT MAKE THE PROVIDER UNUSABLE. It degrades it to
    a small list that is labelled as a fallback, because the alternative - an
    empty dropdown - turns a provider outage into a product that appears to
    support no models at all. What it must never do is present the seed as the
    live fleet, which is why the answer carries its own source.
    """
    try:
        return fetch_catalog(base, key, timeout=timeout)
    except CatalogError as exc:
        fallback = seed_catalog()
        return Catalog(models=fallback.models, source="seed", detail=str(exc))


def models_for(source: Catalog, capability: str, *,
               modality: Optional[str] = None) -> list:
    """The records a selector for that job may offer.

    ⛔ ONE PLACE DECIDES WHAT A CAPABILITY MEANS. Five call sites filtering for
    themselves is five answers to "is this a chat model", and the one that
    drifts is the one that puts an image generator in the conversation list.
    Anything that cannot be proven compatible from the record's own metadata is
    left out: a model with no declared input modalities fails closed and does
    not appear in a multimodal list.
    """
    if capability not in CAPABILITIES:
        raise ValueError("no such capability: %r" % (capability,))
    wanted = CAPABILITY_ENDPOINTS.get(capability)
    out = []
    for model in source.models:
        if wanted:
            if any(e in wanted for e in model.endpoints):
                out.append(model)
            continue
        # chat, and vision as chat plus a declared non-text input.
        if not any(e in TEXT_ENDPOINTS for e in model.endpoints):
            continue
        if any(e in NON_TEXT_ENDPOINTS for e in model.endpoints):
            continue
        if capability == "vision":
            if modality and modality not in model.input_modalities:
                continue
            if not model.modalities:
                continue
        out.append(model)
    return out


def mask(key: str) -> str:
    """A key as it may be shown: enough to recognise, not enough to use.

    ⛔ NEVER THE WHOLE VALUE, AND NEVER THE TAIL. The tail is the part a person
    pastes and the part a support conversation quotes, so what is drawn is the
    prefix and a length - the two facts that answer "is a key here at all, and
    is it the one I think".
    """
    text = (key or "").strip()
    if not text:
        return ""
    head = text[:9] if text.startswith("sk-orca-") else text[:4]
    return "%s...(%d characters)" % (head, len(text))


# --- the credential -----------------------------------------------------------


class NoCredential(Exception):
    """No key anywhere, for OrcaRouter. Named so the CLI can present it the way
    it presents the OpenRouter refusal: one line, exit 1, both ways in."""


class NeedsReauth(Exception):
    """The stored key was revoked, or the account behind it no longer works.

    ⛔ TERMINAL, AND IT IS NOT A RETRY. A durable key that the user revoked from
    their console cannot be renewed by trying again, and there is no refresh
    grant to call: the only recovery is a new sign-in, and a client that loops
    on 401 instead spends a person's time and rate limit proving nothing.
    """


@dataclass(frozen=True)
class Credential:
    """One OrcaRouter key, and the two facts a caller needs about it.

    ⛔ ``method`` IS CARRIED, NOT INFERRED. The key itself is identical however
    it was obtained - that is the point of the seam - but what the panel says,
    what the user is told to do when it stops working, and which sign-out
    applies all differ between "you pasted this" and "we issued this". A caller
    that had to guess would guess wrong exactly when it matters.
    """

    key: str = field(repr=False)
    method: str = "api_key"
    scope: str = ""
    source: str = ""
    generation: int = 1
    needs_reauth: bool = False

    @property
    def masked(self) -> str:
        return mask(self.key)

    def __repr__(self) -> str:
        """⛔ THE KEY IS NOT IN THE REPR. This object travels through the CLI,
        the settings routes and the store, so it is the one a traceback or a
        debugger would print in full. ``repr=False`` hides it from the
        generated dataclass repr; this method is the proof that it stays
        hidden, and a test asserts it."""
        return ("Credential(method=%r, source=%r, generation=%d, needs_reauth=%r)"
                % (self.method, self.source, self.generation, self.needs_reauth))


class Credentials:
    """The OrcaRouter key, where this project already keeps what it must keep.

    ⛔ IT IS A FILE BESIDE THE SESSIONS, BECAUSE THAT IS WHAT THIS PROJECT HAS.
    The right home for a provider secret is the OS keychain, and this package
    has none - adding one would mean a new dependency and a second credential
    store, which is exactly what the integration rules forbid. So the key goes
    where the transcripts and the browser records already go, under the same
    ``AIHAWK_HOME``, through the same atomic write, and it is erased by the
    same code path as everything else. That it is a plain file is a property of
    the host, not a decision taken here, and the file carries the key and
    nothing else - no email, no user id, no workspace.

    ⛔ AND IT IS NOT WRITTEN INTO THE ENVIRONMENT. The key already has two ways
    in that the user controls, a flag and a variable; a stored key that also
    exported itself would be a third copy, in a place every child process
    inherits, which is the leak `runner.forget_key` exists to close.
    """

    KIND = "credentials"
    NAME = "orcarouter"

    def __init__(self, where: Optional[Path] = None) -> None:
        self._where = where or storage.file_for(self.KIND, self.NAME)

    @property
    def path(self) -> Path:
        return self._where

    def load(self) -> Optional[Credential]:
        """The stored credential, or None. A file that will not parse answers
        None, like every other read in this project: something unreadable is
        exactly as usable as something never saved."""
        blob = storage.read_json(self._where)
        if not isinstance(blob, dict):
            return None
        key = blob.get("key")
        if not isinstance(key, str) or not key.strip():
            return None
        try:
            generation = int(blob.get("generation") or 1)
        except (TypeError, ValueError):
            generation = 1
        method = blob.get("method")
        return Credential(
            key=key.strip(),
            method=method if method in ("api_key", "pkce") else "api_key",
            scope=str(blob.get("scope") or ""),
            source="stored",
            generation=max(1, generation),
            needs_reauth=bool(blob.get("needs_reauth")),
        )

    def save(self, credential: Credential) -> Credential:
        """Store a key as a NEW generation.

        ⛔ A SAVE IS A NEW GENERATION, AND THAT IS WHAT MAKES A LATE FAILURE
        HARMLESS. An asynchronous request that was already in flight when the
        user signed in again comes back holding the generation it was sent
        with, and can only ever mark that one. Bumping here - rather than
        leaving the number to whoever remembers - is the half of the guarantee
        that cannot be forgotten at a call site.
        """
        previous = self.load()
        fresh = Credential(
            key=credential.key.strip(),
            method=credential.method,
            scope=credential.scope,
            source=credential.source or "stored",
            generation=(previous.generation + 1) if previous else 1,
            needs_reauth=False,
        )
        storage.write_atomically(
            self._where,
            json.dumps({"key": fresh.key, "method": fresh.method,
                        "scope": fresh.scope, "generation": fresh.generation,
                        "needs_reauth": False},
                       indent=1).encode("utf-8"))
        return fresh

    def mark_needs_reauth(self, generation: int) -> bool:
        """Flag the credential that made a rejected request, if it is still the
        current one. Answers whether anything changed.

        ⛔ ONLY THAT GENERATION, AND ONLY IF IT IS STILL CURRENT. A 401 that
        arrives after the user has already signed in again describes a key that
        is no longer in use; marking the new one would disable a credential
        that has never been tried, which is the defect the generation exists to
        prevent.

        ⛔ AND NOTHING IS DELETED. A revoked key is replaced by a successful
        sign-in, never by this call: deleting on a failure that might have been
        misread turns a transient problem into a key the user has to find
        again.
        """
        current = self.load()
        if current is None or current.generation != generation:
            return False
        if current.needs_reauth:
            return False
        storage.write_atomically(
            self._where,
            json.dumps({"key": current.key, "method": current.method,
                        "scope": current.scope, "generation": current.generation,
                        "needs_reauth": True},
                       indent=1).encode("utf-8"))
        return True

    def clear(self) -> None:
        """Forget the key. The one control that must exist beside the one that
        sets it, and the reason the panel offers a sign-out at all."""
        storage.erase(self._where)


def resolve_credential(explicit: Optional[str], env: Mapping[str, str],
                       store: Optional[Credentials] = None) -> Credential:
    """The key to run on, in the order the user expects to be asked.

    ⛔ ``--orcarouter-key``  >  ``ORCAROUTER_API_KEY``  >  the stored key, which
    is the same precedence the OpenRouter half already documents and the same
    reason: something the user just typed beats something they exported, which
    beats something a sign-in left behind weeks ago. A stored credential that
    is flagged ``needs_reauth`` is NOT used - it is refused with a sentence
    naming the sign-in, because silently sending a key the provider has already
    rejected produces a failure at the first request instead of at startup.
    """
    text = (explicit or "").strip()
    if text:
        return Credential(key=text, method="api_key", source="flag")
    from_env = (env.get(KEY_VARIABLE) or "").strip()
    if from_env:
        return Credential(key=from_env, method="api_key", source="environment")
    if store is not None:
        found = store.load()
        if found is not None and found.needs_reauth:
            raise NeedsReauth(
                "the stored OrcaRouter key was revoked or refused. Sign in "
                "again, or pass --orcarouter-key.")
        if found is not None:
            return found
    raise NoCredential(
        "no OrcaRouter key: pass --orcarouter-key, set ORCAROUTER_API_KEY, or "
        "sign in with --orcarouter-connect")


# --- what an upstream refusal means -------------------------------------------


def is_auth_failure(exc: BaseException) -> bool:
    """Whether this is the provider refusing the CREDENTIAL.

    ⛔ ONLY 401, AND ONLY FROM THE RELAY. A 429 is a rate limit, a 5xx is the
    provider having a bad minute, and a connection error is neither: treating
    any of them as "your key is dead" would send somebody to re-authorize an
    account that was working. The status is read from the attribute the OpenAI
    SDK puts it on and from a nested response, because both shapes exist across
    its versions and neither is worth pinning.
    """
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
    if status is not None:
        return status == 401
    return type(exc).__name__ == "AuthenticationError"
