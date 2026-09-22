"""OrcaRouter: the two origins, the PKCE sign-in, and the model catalogue.

OrcaRouter is an OpenAI-compatible gateway that routes many providers behind
one endpoint, so the wire format this package already speaks is the right one
and what is missing is the credential and the list of models the account can
actually call.

⛔ THE TWO ORIGINS ARE NOT DERIVED FROM EACH OTHER, AND THAT IS THE SINGLE
MOST EXPENSIVE MISTAKE IN THIS INTEGRATION. Authentication lives on
`www.orcarouter.ai` and its endpoints are under `/api/v1/auth`; inference and
the model catalogue live on `api.orcarouter.ai` under `/v1`. So
`https://api.orcarouter.ai/v1/auth/keys` is a 404, and it is a 404 that reads
like a routing bug on the far side rather than a path this file got wrong.
Nothing here ever builds one origin by replacing the other's hostname or by
appending `/v1` to it: `AUTH_BASE_URL` and `API_BASE_URL` are two constants
and `origins()` is the only thing that resolves either.

⛔ AND THEY ARE BOTH CONFIGURABLE, WHICH IS THE OTHER HALF OF THE SAME RULE. A
self-hosted deployment may serve both from one origin or from two. The
explicit overrides win, then the shared fallback, then the public default -
the order every other option in this package already uses (`--flag`, the
environment, `.env`, the default). Remote origins must be HTTPS; plain HTTP is
allowed only for loopback, because a key exchanged over cleartext is a key
somebody else has.

The sign-in is OAuth 2.0 with PKCE and no client secret: there is nothing to
register, no redirect URI to pre-declare, and the auth code is useless to
whoever might intercept it because the verifier never leaves this process. What
comes back is an ordinary durable `sk-orca-...` API key - not an access token
and not a refresh token. There is no refresh grant to call and this module
never invents one.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

#: Where the consent screen is. Not an API: a browser is sent here.
AUTH_BASE_URL = "https://www.orcarouter.ai"

#: Where inference and the model catalogue are. Everything the agent asks for
#: once it holds a key goes here, and nothing else in this file does.
API_BASE_URL = "https://api.orcarouter.ai/v1"

#: The consent screen and the code exchange, both fixed, both on the AUTH
#: origin. `/api/v1/auth/keys` and never `/v1/auth/keys`.
AUTHORIZE_PATH = "/auth"
EXCHANGE_PATH = "/api/v1/auth/keys"

#: The catalogue, on the API origin, relative to `API_BASE_URL`.
MODELS_PATH = "/models"

#: The loopback path a redirect comes back on. Fixed, and it is the whole
#: reason there is no redirect URI to register: the port is chosen at bind
#: time and the address is always this machine.
CALLBACK_PATH = "/callback"

#: The one name the key is expected under in the environment, beside the flag.
#: `ORCA_KEY` is accepted as well, because that is the name the provider table
#: in the public integration guide uses and somebody will have exported it.
KEY_VARIABLE = "ORCAROUTER_API_KEY"

#: Names checked, in order, when no explicit key is given.
KEY_VARIABLES = ("ORCAROUTER_API_KEY", "ORCA_KEY")

#: The shared self-hosted fallback and the two explicit overrides. Read here
#: and nowhere else, so there is one answer to "which origin is this request
#: going to" for both the exchange and the catalogue.
AUTH_BASE_VARIABLE = "ORCAROUTER_AUTH_BASE_URL"
API_BASE_VARIABLE = "ORCAROUTER_API_BASE_URL"
SHARED_BASE_VARIABLE = "ORCAROUTER_BASE_URL"

#: Bounded, all three, because a catalogue response is somebody else's bytes:
#: a timeout so a slow endpoint cannot hold a request open forever, a byte cap
#: so one cannot be streamed into memory without end, and an item cap so a
#: thousand-entry answer cannot become a thousand-entry dropdown.
TIMEOUT = 20.0
MAX_CATALOG_BYTES = 4 * 1024 * 1024
MAX_CATALOG_ITEMS = 500
MAX_ID_LENGTH = 200

#: The endpoint types this client can actually speak. A record that advertises
#: only a wire protocol outside this set is one this package would fail on, so
#: it is not offered.
CHAT_ENDPOINTS = ("openai", "anthropic", "gemini", "openai-response")

#: Types that are specialised for something other than a text chat, and are
#: excluded from the chat list even when they also advertise a chat endpoint.
#: An image generator that answers `openai` too is still not a chat model.
NON_CHAT_ENDPOINTS = ("image-generation", "openai-video", "jina-rerank",
                      "embeddings", "rerank")

#: What each capability means, in the one place that decides it. A model is
#: never guessed into a capability from its name: a record that does not say
#: it supports the thing is not offered for it.
CAPABILITIES = {
    "chat": CHAT_ENDPOINTS,
    "embedding": ("embeddings",),
    "image": ("image-generation",),
    "video": ("openai-video",),
    "rerank": ("jina-rerank",),
}

#: ⛔ THE COLD-START SEED, AND IT IS LABELLED WHEREVER IT IS SHOWN. A fresh
#: install with no network, or an account whose catalogue endpoint is having a
#: bad afternoon, must still offer something callable rather than an empty
#: dropdown and a free-text box. These ids were read back from
#: `https://api.orcarouter.ai/v1/models` on 2026-09-22 and each one is
#: confirmed present in the live catalogue. They are NOT mixed into a live
#: answer: when discovery succeeds its result is the whole list, and the seed
#: is used only when it fails.
SEED_MODELS = (
    "orcarouter/auto",
    "deepseek/deepseek-v4-pro",
    "deepseek/deepseek-v4-flash",
)

#: The model a run uses when OrcaRouter is selected and nobody named one. It
#: is the first entry of the verified seed, so it is a route the gateway knows
#: and one this account can call.
DEFAULT_MODEL = SEED_MODELS[0]

#: Which of the two lists a dropdown is showing. The page says so, in the
#: panel and on the control itself, because a seed presented as a live
#: catalogue is a claim about the account that nobody verified.
LIVE_SOURCE = "live"
SEED_SOURCE = "seed"

#: How the credential was obtained. Two adapters, one credential: nothing
#: downstream of this - not the client, not the catalogue, not the agent loop -
#: asks which of the two it was.
BY_KEY = "api-key"
BY_PKCE = "pkce"


def _b64url(raw: bytes) -> str:
    """base64url with no padding, which is what the challenge must be."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def new_verifier() -> str:
    """A fresh PKCE verifier, from the cryptographic RNG, per attempt.

    ⛔ PER ATTEMPT, AND FROM `secrets`. A verifier reused across attempts, or
    derived from anything guessable - a timestamp, a user name, a fixed salt -
    is the whole defence gone: it is the one secret an intercepted auth code
    cannot be redeemed without.
    """
    return _b64url(secrets.token_bytes(32))


def new_state() -> str:
    """A fresh CSRF token, per attempt, from the same RNG."""
    return _b64url(secrets.token_bytes(16))


def challenge_for(verifier: str) -> str:
    """`base64url(sha256(verifier))`, unpadded. S256 and never `plain`.

    `plain` is refused by the consent endpoint for a displayed code and is
    merely unwise for a redirect, so there is one method here and it is S256.
    """
    return _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


def state_matches(given: str, expected: str) -> bool:
    """Whether a redirect carried the state this attempt sent.

    ⛔ CONSTANT TIME, AND BEFORE THE CODE IS USED. This comparison is the only
    thing standing between the loopback listener and an auth code that
    somebody else's page dropped on it, so it runs first and it does not leak
    how much of a wrong guess was right.
    """
    if not given or not expected:
        return False
    return hmac.compare_digest(given, expected)


def origins(env: Optional[Mapping[str, str]] = None) -> Tuple[str, str]:
    """`(auth origin, api origin)`, from the environment, in that order.

    The explicit overrides win, then the shared self-hosted fallback, then the
    public defaults. Neither public origin is ever computed from the other.
    """
    env = os.environ if env is None else env
    shared = (env.get(SHARED_BASE_VARIABLE) or "").strip().rstrip("/")
    auth = (env.get(AUTH_BASE_VARIABLE) or "").strip().rstrip("/") or shared or AUTH_BASE_URL
    api = (env.get(API_BASE_VARIABLE) or "").strip().rstrip("/") or shared or API_BASE_URL
    return auth, api


def require_https(url: str) -> str:
    """The same URL, or a refusal that names what is wrong with it.

    A key exchanged over plain HTTP to a remote host is a key in somebody
    else's logs. Loopback is the one exception, and it is the one this
    product's own redirect listener uses.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "https":
        return url
    if parsed.scheme == "http" and (parsed.hostname or "") in ("127.0.0.1", "localhost", "::1"):
        return url
    raise ValueError("an OrcaRouter origin must be https (http only on loopback): %r"
                     % (url,))


def authorize_url(auth_base: str, callback_url: str, challenge: str, state: str,
                  app_name: str = "AIHawk", scope: str = "api") -> str:
    """The consent URL a browser is opened at.

    `S256` on every flow, including the loopback one, because the consent
    screen lets the user ask for a code to be displayed instead of delivered -
    and a code in human hands must be redeemable only by the process holding
    the verifier.
    """
    query = urllib.parse.urlencode({
        "callback_url": callback_url,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "app_name": app_name,
        "scope": scope,
    })
    return "%s%s?%s" % (require_https(auth_base).rstrip("/"), AUTHORIZE_PATH, query)


def exchange_body(code: str, verifier: str) -> bytes:
    """The JSON body the code is redeemed with.

    ⛔ THE VERIFIER IS IN THE BODY AND NOWHERE ELSE. It never rides on a URL,
    never reaches a log, and never appears in a message this module raises.
    """
    return json.dumps({
        "code": code,
        "code_verifier": verifier,
        "code_challenge_method": "S256",
    }).encode("utf-8")


def granted_scope(payload: Mapping[str, Any], wanted: str = "api") -> Tuple[str, bool]:
    """What was GRANTED, and whether it covers what this client asked for.

    ⛔ READ BACK RATHER THAN ASSUMED. Asking for `connector` and being given
    `api` means the account's role does not permit the wider grant, and a
    client that assumes it holds what it requested will fail later in a place
    that says nothing about the cause.
    """
    got = str(payload.get("scope") or wanted)
    return got, got == wanted


def _read_json(url: str, *, data: Optional[bytes] = None,
               headers: Optional[Mapping[str, str]] = None,
               cap: int = MAX_CATALOG_BYTES) -> Tuple[int, Any]:
    """One request, bounded, returning `(status, parsed-or-None)`.

    Written on `urllib.request` rather than on a new HTTP dependency: this is
    two calls, both JSON, and the package already refuses to grow a dependency
    for something its own standard library does.
    """
    request = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    request.add_header("Accept", "application/json")
    for name, value in (headers or {}).items():
        request.add_header(name, value)
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
            raw = answer.read(cap)
            try:
                return answer.status, json.loads(raw.decode("utf-8"))
            except ValueError:
                return answer.status, None
    except urllib.error.HTTPError as exc:
        # The status is the answer, and the body is read only so the connection
        # is closed cleanly. It is NOT put into any message: an error body from
        # an auth endpoint is not a place to copy bytes out of.
        exc.read(cap)
        return exc.code, None


# --- the credential seam --------------------------------------------------------

class Credential:
    """One OrcaRouter credential, whatever road it arrived by.

    ⛔ THIS IS THE SEAM. A pasted API key and a PKCE sign-in are two adapters
    over this one shape, and everything downstream - the inference client, the
    catalogue, the agent loop - takes a `Credential` and never asks which
    adapter produced it. `method` exists so the panel can say which road the
    user took; nothing that spends the key reads it.
    """

    def __init__(self, key: str, *, method: str = BY_KEY, source: str = "",
                 generation: int = 1, scope: str = "", account: str = "") -> None:
        self.key = key
        self.method = method
        self.source = source
        self.generation = generation
        self.scope = scope
        self.account = account
        self.needs_reauth = False

    @property
    def masked(self) -> str:
        """The key as it may be shown: never the whole thing.

        ⛔ FOUR CHARACTERS, NOT TWENTY. A masked key still identifies which
        credential is in use when somebody has two, and it cannot be used.
        """
        tail = self.key[-4:] if len(self.key) > 8 else ""
        return ("sk-orca-...%s" % tail) if tail else "(set)"

    def as_state(self) -> dict:
        """What the panel may be told about this credential. No key in it."""
        return {"set": True, "masked": self.masked, "method": self.method,
                "source": self.source, "generation": self.generation,
                "scope": self.scope, "needs_reauth": self.needs_reauth}


def key_from_environment(env: Optional[Mapping[str, str]] = None) -> str:
    """The first of the accepted variable names that holds something."""
    env = os.environ if env is None else env
    for name in KEY_VARIABLES:
        value = (env.get(name) or "").strip()
        if value:
            return value
    return ""


def resolve_key(explicit: Optional[str], env: Optional[Mapping[str, str]] = None) -> str:
    """The key to use, or a refusal that names both ways to supply one.

    `explicit` first, because a flag is what somebody just typed; the
    environment second, which is where `.env` lands; and an empty string
    counts as absent, because `--orcarouter-key ""` is not a key.
    """
    return (explicit or "").strip() or key_from_environment(env)


# --- the catalogue --------------------------------------------------------------

class Model:
    """One catalogue record, with only the fields a client may rely on."""

    def __init__(self, id: str, endpoints: Sequence[str] = (),
                 modalities: Sequence[str] = ()) -> None:
        # ⛔ THE ID IS KEPT VERBATIM, namespace and all. `deepseek/deepseek-v4-pro`
        # is a route, not a display name: trimming the vendor prefix produces a
        # model id the gateway does not know.
        self.id = id
        self.endpoints = tuple(endpoints)
        self.modalities = tuple(modalities)

    def as_state(self) -> dict:
        return {"id": self.id, "endpoints": list(self.endpoints),
                "modalities": list(self.modalities)}


def catalog_from(payload: Any) -> List[Model]:
    """The models in one catalogue answer, bounded and shape-checked.

    A record that is not a dict, has no usable id, or advertises an endpoint
    type outside the set this client can speak is DROPPED rather than guessed
    at: a dropdown that offers a model the client cannot call is worse than a
    short one.
    """
    if isinstance(payload, dict):
        items = payload.get("data")
    else:
        items = payload
    if not isinstance(items, list):
        return []
    known = set(CHAT_ENDPOINTS) | set(NON_CHAT_ENDPOINTS)
    out: List[Model] = []
    for item in items[:MAX_CATALOG_ITEMS]:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if not isinstance(model_id, str):
            continue
        model_id = model_id.strip()
        if not model_id or len(model_id) > MAX_ID_LENGTH:
            continue
        endpoints = item.get("supported_endpoint_types")
        endpoints = [e for e in endpoints if isinstance(e, str) and e in known] \
            if isinstance(endpoints, list) else []
        architecture = item.get("architecture")
        modalities = architecture.get("input_modalities") if isinstance(architecture, dict) else None
        modalities = [m for m in modalities if isinstance(m, str)] \
            if isinstance(modalities, list) else []
        out.append(Model(model_id, endpoints, modalities))
    return out


def models_for(models: Iterable[Model], capability: str = "chat",
               modality: Optional[str] = None) -> List[Model]:
    """The models that can do this, from what the catalogue said about them.

    ⛔ FAIL CLOSED. A record that does not name the capability is not offered
    for it - including the multimodal case, where a model that declares no
    input modalities at all is not offered for an image. Guessing from a model
    name is how a dropdown offers something that then fails at the first
    request, in a place that says nothing about why.
    """
    wanted = CAPABILITIES.get(capability, ())
    out = []
    for model in models:
        endpoints = set(model.endpoints)
        if capability == "chat":
            if not endpoints & set(CHAT_ENDPOINTS) or endpoints & set(NON_CHAT_ENDPOINTS):
                continue
        elif not endpoints & set(wanted):
            continue
        if modality is not None and modality not in model.modalities:
            continue
        out.append(model)
    return out


def seed_models() -> List[Model]:
    """The verified cold-start list, as records, so it can be filtered too."""
    return [Model(model_id, CHAT_ENDPOINTS) for model_id in SEED_MODELS]


def catalog_url(api_base: str, capability: Optional[str] = None) -> str:
    """The catalogue URL, with the capability filter when one is asked for."""
    url = require_https(api_base).rstrip("/") + MODELS_PATH
    return "%s?capability=%s" % (url, urllib.parse.quote(capability)) if capability else url


async def fetch_catalog(key: str, *, api_base: Optional[str] = None,
                        capability: Optional[str] = None) -> List[Model]:
    """`GET /v1/models` with the account's own key, in a thread.

    In a thread because `urllib` is synchronous and this runs inside the
    server's event loop, where a blocking call would stop the frame pump and
    the stop button for as long as somebody else's endpoint takes to answer.
    """
    base = api_base or origins()[1]
    status, payload = await asyncio.to_thread(
        _read_json, catalog_url(base, capability),
        headers={"Authorization": "Bearer %s" % key})
    if status != 200:
        raise CatalogError("the model catalogue answered %d" % status)
    return catalog_from(payload)


class CatalogError(RuntimeError):
    """The catalogue could not be read. The seed is the fallback, not a crash."""


# --- the PKCE sign-in -----------------------------------------------------------

class PkceLogin:
    """One sign-in attempt: a fresh verifier, a listener, and a URL to open.

    ⛔ ONE ATTEMPT, ONE VERIFIER, ONE STATE, AND NO SECOND USE. The object is
    built per attempt and thrown away when it ends, so a retry cannot inherit
    the verifier of the attempt before it. `close()` releases the loopback
    port on every way out - success, denial, error, timeout and an explicit
    cancel - because a listener left bound is a port that stays open and a
    second sign-in that fails for a reason nobody can see.

    Flow A (loopback redirect) is what this product uses: the interface is a
    local server on the user's own machine, so a browser on that machine can
    reach `127.0.0.1` and the user clicks once. Flow B is the same object with
    `submit()` instead of the listener - the consent screen may offer to show
    a code rather than redirect, and that is the user's choice, not a
    parameter this client can set.
    """

    def __init__(self, app_name: str = "AIHawk", *,
                 auth_base: Optional[str] = None) -> None:
        self.verifier = new_verifier()
        self.state = new_state()
        self.challenge = challenge_for(self.verifier)
        self.auth_base = (auth_base or origins()[0]).rstrip("/")
        self.app_name = app_name
        self.port = 0
        self._queue: Optional[asyncio.Queue] = None
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._closed = False

    @property
    def callback_url(self) -> str:
        """Where the code comes back to, or the literal `oob` before binding."""
        return ("http://127.0.0.1:%d%s" % (self.port, CALLBACK_PATH)) if self.port else "oob"

    def start(self) -> str:
        """Bind loopback FIRST, then answer with the URL to open.

        ⛔ BOUND BEFORE THE URL EXISTS, so the port on the URL is the port that
        is actually listening. Building the URL first and binding after is a
        race the browser usually wins.
        """
        self._queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        # ⛔ THE ATTEMPT, BOUND BY NAME, because `self` inside the handler below
        # is the HANDLER. Reaching for `self.state` there reads an attribute the
        # request handler does not have, so the comparison that guards the code
        # would raise instead of refusing - the one line in this file that must
        # never be the thing that is wrong.
        login = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(handler):  # noqa: N802 - name fixed by the base class
                url = urllib.parse.urlparse(handler.path)
                if url.path != CALLBACK_PATH:
                    handler.send_response(404)
                    handler.end_headers()
                    return
                query = urllib.parse.parse_qs(url.query)
                handler.send_response(200)
                handler.send_header("Content-Type", "text/html; charset=utf-8")
                handler.end_headers()
                handler.wfile.write(b"<p>Connected. You can close this tab.</p>")
                given = (query.get("state") or [""])[0]
                if not state_matches(given, login.state):
                    loop.call_soon_threadsafe(
                        login._queue.put_nowait, ("error", "state mismatch"))
                    return
                refused = (query.get("error") or [""])[0]
                if refused:
                    loop.call_soon_threadsafe(
                        login._queue.put_nowait,
                        ("error", "the authorization was refused"))
                    return
                loop.call_soon_threadsafe(
                    login._queue.put_nowait,
                    ("code", (query.get("code") or [""])[0]))

            def log_message(self, *args):
                """Silence. The request line carries the code, and a log line
                is a second copy of it on disk."""

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._server.daemon_threads = True
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._serve_forever, daemon=True)
        self._thread.start()
        return authorize_url(self.auth_base, self.callback_url, self.challenge,
                             self.state, self.app_name)

    def _serve_forever(self) -> None:
        """Serve, with a short poll interval so `close` returns promptly.

        The default interval is half a second and `shutdown` waits for it, so
        cancelling a sign-in would stall the event loop that the frame pump and
        the stop button share.
        """
        server = self._server
        if server is not None:
            server.serve_forever(poll_interval=0.05)

    def submit(self, code: str) -> None:
        """Flow B: the code the user read off the consent screen."""
        if self._queue is not None:
            self._queue.put_nowait(("code", (code or "").strip()))

    async def wait(self, timeout: float = 300.0) -> str:
        """The code, or a refusal that says which of the ways it failed.

        A denial, a state mismatch and a timeout are three different sentences
        to a user and one shape to the caller. What none of them is is a hang:
        the timeout ends the wait rather than leaving a request open forever.
        """
        if self._queue is None:
            raise PkceError("this sign-in was never started")
        try:
            kind, value = await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            raise PkceError("the authorization timed out") from None
        if kind == "error":
            raise PkceError(value)
        if not value:
            raise PkceError("the authorization came back without a code")
        return value

    async def exchange(self, code: str) -> Credential:
        """Redeem the code for a durable API key.

        ⛔ THE EXCHANGE GOES TO THE AUTH ORIGIN, and its path is
        `EXCHANGE_PATH`. A 400 means the challenge method was not recognised
        or differs from the one sent at authorize time; a 403 means the code is
        unknown, expired, or already used, or the verifier does not match. Both
        are reported as one sentence each and neither copies the response body
        into a message, because that body is not a place to take bytes out of.
        """
        url = require_https(self.auth_base).rstrip("/") + EXCHANGE_PATH
        status, payload = await asyncio.to_thread(
            _read_json, url, data=exchange_body(code, self.verifier))
        if status == 400:
            raise PkceError("the code exchange was refused (400): the challenge "
                            "method did not match the one this sign-in sent")
        if status == 403:
            raise PkceError("the code was refused (403): it is unknown, expired "
                            "or already used, or it belongs to another sign-in")
        if status == 429:
            raise PkceError("the sign-in was refused (429): too many keys have "
                            "been issued for this account in the last day")
        if status != 200 or not isinstance(payload, dict):
            raise PkceError("the code exchange failed (%d)" % status)
        key = payload.get("key")
        if not isinstance(key, str) or not key.strip():
            raise PkceError("the code exchange answered without a key")
        scope, enough = granted_scope(payload)
        credential = Credential(key.strip(), method=BY_PKCE, source="pkce", scope=scope)
        if not enough:
            # Said rather than smoothed over: the key works, and it does not
            # carry what this client asked for.
            raise PkceError("the account granted %r rather than %r" % (scope, "api"))
        return credential

    def close(self) -> None:
        """Release the listener. Safe to call on every path, and twice."""
        if self._closed:
            return
        self._closed = True
        server = self._server
        self._server = None
        # ⛔ THE PORT GOES WITH THE LISTENER. `callback_url` reports `oob` while
        # nothing is bound, and a closed login that still named a port would
        # describe a listener that is not there - which is what the authorize
        # URL is built from.
        self.port = 0
        if server is not None:
            server.shutdown()
            server.server_close()
        self._thread = None


class PkceError(RuntimeError):
    """A sign-in that ended without a key. Every sentence is actionable."""
