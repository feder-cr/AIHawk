"""Which provider this interface is talking to, and the two ways to be let in.

⛔ ONE PLACE OWNS THE CHOICE, AND EVERYTHING ELSE ASKS IT. Before this the
provider was decided once, in `cli.ui`, and never mentioned again: the key was
resolved from a flag, a client was built, and a brain factory closed over both.
That is exactly right for one provider and exactly wrong for two, because the
page can now change its mind while it is open - a model is picked from a
dropdown and the conversation that is already on screen has to start sending
there.

⛔ AND THE TWO AUTHENTICATION ENTRIES END IN ONE CREDENTIAL. Pasting a key and
signing in produce the same `Credential`; the panel, the client and the catalog
all read that and none of them can tell which one it was, except where the
difference is real - which sentence to show when the key stops working.

⛔ THE LOGIN IS A SERVER-SIDE OBJECT WITH A GENERATION, NOT A FLAG ON A PAGE.
The browser can go away mid-sign-in: the tab is closed, the window is hidden,
the machine sleeps, the page is restored from the back-forward cache. Every one
of those has to end the attempt on this side, and every answer that arrives
afterwards has to be recognised as belonging to an attempt nobody is waiting
for. A monotonic number is what makes that decidable, and it is kept here
because the page is the thing that goes away.
"""
from __future__ import annotations

import asyncio
from typing import Dict, Mapping, Optional

from . import llm, orcarouter
from .orcarouter import Credential, Credentials, PkceError

#: The two providers this interface can be on. The default is the one that was
#: the only one, so an installation that upgrades lands exactly where it was.
OPENROUTER = "openrouter"
ORCAROUTER = "orcarouter"
PROVIDERS = (OPENROUTER, ORCAROUTER)


class Provider:
    """The current provider, its model, and the OrcaRouter credential.

    Owned by the app rather than by a request: the choice outlives any one
    call, and it has to be readable by a route that did not make it.
    """

    def __init__(self, sessions=None, env: Optional[Mapping[str, str]] = None,
                 credentials: Optional[Credentials] = None) -> None:
        self._sessions = sessions
        self._env = env if env is not None else {}
        self._credentials = credentials if credentials is not None else Credentials()
        self.name = OPENROUTER
        self.model = llm.resolve_model(None, self._env)
        self._env_names = llm.orcarouter_env(self._env)
        self._credential: Optional[Credential] = None
        self._openrouter: Optional[str] = None
        self._client = None
        self._catalog: Optional[orcarouter.Catalog] = None
        #: One entry per attempt that has been started and not yet resolved.
        #: Keyed by the attempt id the page is given, so a late answer names
        #: which attempt it belongs to instead of being applied to whatever is
        #: current.
        self._attempts: Dict[str, orcarouter.Authorization] = {}
        self._generation = 0
        #: Something the user should read once, in the words of the surface
        #: that just answered. A scope that came back narrower than it was
        #: asked for is the case it exists for; the panel draws it beside the
        #: key it describes and it is cleared by the next choice.
        self._note = ""

    # --- what the panel draws ------------------------------------------------

    def state(self) -> dict:
        """Everything the settings panel needs, and nothing that is a secret.

        ⛔ THE KEY IS MASKED HERE AND NOWHERE ELSE IS ASKED TO REMEMBER. A
        route that had to remember to mask would be one route away from putting
        a key in a response body, and the panel is the only thing that draws it.
        """
        stored = self._credentials.load()
        live = self._credential or stored
        return {
            "provider": self.name,
            "model": self.model,
            "providers": list(PROVIDERS),
            "note": self._note,
            "key": {
                "present": bool(live and live.key),
                "masked": live.masked if live else "",
                "method": live.method if live else "",
                "source": live.source if live else "",
                "needs_reauth": bool(live.needs_reauth) if live else False,
                "scope": live.scope if live else "",
            },
            "catalog": self.catalog_state(),
            "console": orcarouter.CONSOLE_URL,
        }

    def catalog_state(self) -> dict:
        """The models on offer, with the provenance of the list.

        ⛔ ``source`` TRAVELS WITH THE LIST. A dropdown that cannot say whether
        it is showing the live fleet or a fallback is a dropdown that shows a
        stale fleet as though it were current.
        """
        live = self._catalog
        if live is None:
            return {"source": "none", "detail": "", "models": []}
        return {"source": live.source, "detail": live.detail,
                "models": [{"id": m.id, "modalities": list(m.modalities)}
                           for m in live.models]}

    def models_for(self, capability: str = "chat") -> dict:
        """The ids a selector for that job may offer, with its provenance."""
        catalog = self._catalog or orcarouter.seed_catalog()
        chosen = orcarouter.models_for(catalog, capability)
        return {"capability": capability,
                "source": catalog.source,
                "detail": catalog.detail,
                "models": [{"id": m.id, "modalities": list(m.modalities)}
                           for m in chosen]}

    # --- choosing ------------------------------------------------------------

    def choose(self, name: str, model: Optional[str] = None) -> dict:
        """Move to a provider, and to a model within it.

        ⛔ A MODEL THE CURRENT LIST DOES NOT HOLD IS REFUSED, NOT KEPT. The
        dropdown is built from the catalog, so a value outside it is either a
        stale page or a hand-written request; keeping it would leave the panel
        drawing a model the provider is not being asked for.
        """
        if name not in PROVIDERS:
            raise ValueError("no such provider: %r" % (name,))
        self._client = None
        if name == ORCAROUTER:
            credential = self._credential or self._credentials.load()
            if credential is None or credential.needs_reauth:
                raise orcarouter.NoCredential(
                    "no OrcaRouter key yet: paste one or sign in first")
            self._credential = credential
            catalog = self._catalog
            if model:
                if catalog is not None and not catalog.holds(model):
                    raise ValueError("that model is not in the current catalog")
                self.model = model
            elif self.model not in (catalog.ids() if catalog else []):
                self.model = orcarouter.DEFAULT_MODEL
            self._rewire(self.model)
            self.name = ORCAROUTER
            if self._sessions is not None:
                self._sessions.use_credential(self._credential, self._credentials)
            return self.state()
        self.name = OPENROUTER
        self.model = llm.resolve_model(model, self._env)
        self._rewire(self.model)
        return self.state()

    def _rewire(self, model: str) -> None:
        """Point the open conversations at this provider's brain, if there is a
        registry to point. A `Provider` built without one - which is how the
        panel is tested - still resolves keys, catalogs and models."""
        if self._sessions is not None:
            self._sessions.rewire(self._brain, model)

    def set_model(self, explicit: Optional[str]) -> str:
        """Resolve the model for the provider that is current now.

        ⛔ THE SAME FLAG MEANS TWO DIFFERENT DEFAULTS. ``--model`` names a model
        on whichever provider is being started, and an id that exists on one is
        not an id on the other - so the default it falls back to is the
        provider's own, and this is the one place that decides which.
        """
        if self.name == ORCAROUTER:
            self.model = llm.orcarouter_model(explicit, self._env)
        else:
            self.model = llm.resolve_model(explicit, self._env)
        return self.model

    @property
    def credential(self) -> Optional[Credential]:
        """The OrcaRouter credential this interface is running on, if it is."""
        return self._credential or self._credentials.load()

    @property
    def label(self) -> str:
        """Where the requests go, for the one line the CLI prints at startup.

        ⛔ READ OFF THE SAME FUNCTION THE CLIENT IS BUILT FROM. A second string
        naming the endpoint is a second answer to "where did that go", and the
        two would disagree the first time somebody sets an override.
        """
        if self.name == ORCAROUTER:
            return orcarouter.api_base(self._env)
        return llm.BASE_URL

    def client(self):
        """The one client this interface talks through, built once.

        ⛔ ONE CLIENT, A BRAIN PER CONVERSATION. The client is a connection and
        the brain is a transcript: sharing the first is what it is for, and
        sharing the second would give every session in the column the same
        memory, so asking one thing in a session would answer with another
        session's work. Built here rather than per conversation, and thrown
        away only when the provider or the key changes - which is the one thing
        that makes it a different connection.
        """
        if self._client is None:
            if self.name == ORCAROUTER:
                credential = self._credential or self._credentials.load()
                self._client = llm.make_orcarouter_client(credential, self._env)
            else:
                self._client = llm.make_client(self._openrouter_key())
        return self._client

    def make_brain(self):
        """One conversation's brain, for the provider that is current now.

        Read at the moment a conversation is made, which is what lets a
        conversation opened after a switch land on the new provider without
        anything having to be pushed at it.
        """
        from .agent import OpenRouterBrain

        return OpenRouterBrain(self.client(), self.model)

    def use_openrouter_key(self, key: str) -> None:
        """The key the CLI resolved, which is not always one the environment
        holds: `--openrouter-key` puts it on a command line and nowhere else, by
        design, so that it never reaches a child process.

        ⛔ THE RESOLVED KEY, NOT A SECOND LOOK AT THE ENVIRONMENT. `resolve_key`
        already decided between the flag and the variable, with the precedence
        this project documents; reading the environment again here would be a
        second answer to the same question, and it would be wrong for exactly
        the case the flag exists for.
        """
        self._openrouter = (key or "").strip() or None
        self._client = None

    def _openrouter_key(self) -> str:
        key = self._openrouter or self._env.get("OPENROUTER_API_KEY")
        if not key:
            raise orcarouter.NoCredential("no OpenRouter key")
        return key

    # --- the API-key entry ---------------------------------------------------

    def save_key(self, text: str) -> dict:
        """Store a pasted key as this interface's OrcaRouter credential.

        ⛔ A LIGHTWEIGHT SHAPE CHECK AND NOTHING MORE. The `sk-orca-` prefix
        catches a pasted OpenRouter key or a line of prose before it becomes a
        failed request, and that is all it is: a prefix is not proof that a key
        is valid, and validating it for real would mean spending an inference
        request to make a settings form say "valid", which is not a thing this
        product does.
        """
        cleaned = (text or "").strip()
        if not cleaned:
            raise ValueError("no key was given")
        if not cleaned.startswith("sk-orca-"):
            raise ValueError("an OrcaRouter key starts with sk-orca-")
        stored = self._credentials.save(
            Credential(key=cleaned, method="api_key", source="pasted"))
        self._credential = stored
        self._client = None
        self.refresh_catalog()
        return self.state()

    def clear_key(self) -> dict:
        """Forget the key, and leave the provider rather than sitting on a
        credential that is not there."""
        self._credentials.clear()
        self._credential = None
        self._catalog = None
        self._client = None
        if self._sessions is not None:
            self._sessions.use_credential(None, None)
        if self.name == ORCAROUTER:
            self.choose(OPENROUTER)
        return self.state()

    # --- the catalog ---------------------------------------------------------

    def refresh_catalog(self) -> dict:
        """Read the live fleet, or fall back to the verified seed.

        Never raises: an outage degrades the provider, it does not make it
        unusable, and the answer says which of the two the panel is looking at.
        """
        credential = self._credential or self._credentials.load()
        if credential is None or credential.needs_reauth:
            self._catalog = orcarouter.seed_catalog()
            return self.catalog_state()
        self._catalog = orcarouter.catalog(
            orcarouter.api_base(self._env), credential.key)
        return self.catalog_state()

    # --- the sign-in entry ---------------------------------------------------

    def begin_login(self, *, oob: bool = False,
                    opener=None) -> dict:
        """Start an authorization attempt and answer where to send the browser.

        ⛔ A NEW ATTEMPT SUPERSEDES EVERY OLDER ONE. Two sign-ins in two tabs is
        an ordinary thing to do, and the second one wins: the generation moves
        here, so an answer that arrives for the first is recognised as stale
        and cannot overwrite the credential the second one is about to set.
        """
        self._generation += 1
        self._forget_attempts()
        attempt = orcarouter.start_authorization(self._env, oob=oob, opener=opener)
        attempt_id = "a%d" % self._generation
        self._attempts[attempt_id] = attempt
        return {"attempt": attempt_id, "url": attempt.url, "kind": attempt.kind}

    def finish_login(self, attempt_id: str, code: str) -> dict:
        """Redeem the code, store the key, and answer what the panel draws.

        ⛔ THE ATTEMPT HAS TO BE THE CURRENT ONE. A code that arrives for a
        superseded or cancelled attempt is refused rather than redeemed: it
        would otherwise replace a credential that a newer attempt is in the
        middle of setting, which is the same defect as a stale response
        overwriting a newer sign-in.
        """
        attempt = self._attempts.get(attempt_id)
        if attempt is None:
            raise PkceError("that sign-in is no longer waiting for a code. "
                            "Start again.")
        try:
            key, scope = orcarouter.exchange_code(
                orcarouter.auth_base(self._env), code, attempt.verifier)
        finally:
            attempt.cancel()
            self._attempts.pop(attempt_id, None)
        if scope and scope != orcarouter.SCOPE:
            # ⛔ GRANTED LESS THAN WAS ASKED FOR, AND THE USER IS TOLD. The key
            # still works for inference - that is the only thing this product
            # does with it - so this is not a failure. It is the difference
            # between a note and a surprise, and the requested scope is never
            # recorded as though it were the granted one.
            self._note = ("this sign-in granted %r rather than %r, so the key "
                          "may reach less than expected"
                          % (scope, orcarouter.SCOPE))
        else:
            self._note = ""
        stored = self._credentials.save(
            Credential(key=key, method="pkce", scope=scope, source="pkce"))
        self._credential = stored
        self._client = None
        self.refresh_catalog()
        self.name = ORCAROUTER
        if self.model not in (self._catalog.ids() if self._catalog else []):
            self.model = orcarouter.DEFAULT_MODEL
        self._rewire(self.model)
        if self._sessions is not None:
            self._sessions.use_credential(stored, self._credentials)
        return self.state()

    def collect_login(self, attempt_id: str) -> dict:
        """The code the loopback listener has received, if it has one yet.

        ⛔ IT ANSWERS, IT DOES NOT WAIT. A route that blocked here would hold an
        HTTP connection open for as long as the person takes in their browser,
        and the page that asked may be gone by then - closed tab, restored from
        the back-forward cache, or a second sign-in started over it. The page
        asks on its own cadence, and stops asking when it is told the attempt
        is over.
        """
        attempt = self._attempts.get(attempt_id)
        if attempt is None:
            raise PkceError("that sign-in is no longer waiting. Start again.")
        found = attempt.poll()
        if found is None:
            return {"state": "waiting"}
        if found["state"] == "error":
            self.cancel_login(attempt_id)
            return {"state": "error", "detail": found["detail"]}
        return self.finish_login(attempt_id, found["code"])

    def cancel_login(self, attempt_id: Optional[str] = None) -> dict:
        """End an attempt, and free the listener it was holding.

        ⛔ CALLED ON EVERY WAY OUT, INCLUDING THE ONES THE PAGE CANNOT REPORT.
        A tab that is closed mid-sign-in never sends a cancellation, which is
        why the page also sends one on `pagehide` with `keepalive` - and why
        this is safe to call twice, and safe to call for an attempt that
        already finished.
        """
        self._generation += 1
        if attempt_id:
            attempt = self._attempts.pop(attempt_id, None)
            if attempt is not None:
                attempt.cancel()
        else:
            self._forget_attempts()
        return {"cancelled": True, "attempts": 0}

    def _forget_attempts(self) -> None:
        for attempt in list(self._attempts.values()):
            attempt.cancel()
        self._attempts.clear()

    @property
    def waiting(self) -> int:
        """How many attempts are open, for the tests that prove they close."""
        return len(self._attempts)

    def adopt(self, credential: Optional[Credential]) -> None:
        """Start on an OrcaRouter credential chosen before the app was built."""
        self._credential = credential
        self._client = None
        if credential is not None:
            self.name = ORCAROUTER
            if self._sessions is not None:
                self._sessions.use_credential(credential, self._credentials)


async def warm(provider: Provider) -> None:
    """Read the catalog off the event loop, once, at startup.

    ⛔ THE REQUEST IS BLOCKING AND IT IS IN FRONT OF A PAGE THAT IS ABOUT TO
    DRAW. `urllib` is synchronous, so reading the fleet on the loop would stop
    the frame pump, the transcript and the stop button for the length of a
    network call to another company's service. A thread costs one line and
    keeps the page live while it happens.
    """
    await asyncio.to_thread(provider.refresh_catalog)
