"""Which model this interface talks to, and where its credential came from.

Until this file existed there was one provider, hard-coded: `llm.make_client`
built an `OpenAI` aimed at OpenRouter, `OPENROUTER_API_KEY` was the only
credential the interface knew, and the model was a string resolved from
`--model` or the environment. That is still the default and nothing about it
changes - OpenRouter is the provider a run gets when nobody says otherwise.

⛔ TWO ROADS IN, ONE CREDENTIAL, AND ONE PLACE THAT DECIDES. A pasted
`sk-orca-...` key and a completed PKCE sign-in both end as an
`orcarouter.Credential`, and both end as an ordinary OrcaRouter API key in the
same store. Nothing downstream asks which road it was: the inference client
takes the key, the catalogue takes the key, and the agent loop takes the client.
What the panel is told is which road the USER took, because that is a fact about
their account and not about the request.

⛔ AND THE KEY IS NOT WRITTEN ANYWHERE IT WOULD BE A LEAK. The store is the
one this package already uses for saved things (`storage.home()`), the file is
written with the same atomic replace as a saved conversation, and the key is
never logged, never echoed, never put in a URL and never returned to the page -
the panel is told a mask and nothing else. The catalogue is fetched by the
SERVER and the page is handed the model list, because a browser is not a place
to hold a credential.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from . import orcarouter, storage
from .quiet import swallow

#: The provider a run uses when nobody names one. OpenRouter, because that is
#: what every existing install already has configured and a change of default
#: would silently move somebody's traffic to a different company.
DEFAULT_PROVIDER = "openrouter"

#: The two, and their names as a person reads them. `orcarouter` is the pasted
#: key and `orcarouter-oauth` is the sign-in: two ids rather than one, so the
#: status, the logout and the reauthentication each have an unambiguous subject
#: and a generic button that sometimes asks for a key and sometimes opens a
#: browser is not a thing this product can build.
PROVIDERS = {
    "openrouter": "OpenRouter",
    "orcarouter": "OrcaRouter - API",
    "orcarouter-oauth": "OrcaRouter - Auth",
}

#: The directory the credential is kept in, beside `chats/` and `sessions/`.
KIND = "credentials"

#: The one file inside it. One OrcaRouter credential per installation, because
#: that is the shape the panel offers: one provider, two ways to fill it.
FILENAME = "orcarouter.json"


def is_orcarouter(name: str) -> bool:
    """Whether this provider id is one of the two OrcaRouter entries."""
    return name in ("orcarouter", "orcarouter-oauth")


def known(name: Optional[str]) -> str:
    """The provider id, or the default. Never a refusal: an id nobody declared
    is a page that is older than this server, and the honest answer to that is
    the default provider rather than a 500."""
    return name if name in PROVIDERS else DEFAULT_PROVIDER


def credential_path():
    """Where the OrcaRouter credential lives."""
    return storage.home() / KIND / FILENAME


def save_credential(credential: orcarouter.Credential) -> None:
    """Write this credential down, atomically, with the mode a secret needs.

    ⛔ THE GENERATION GOES WITH IT, AND IT ONLY EVER GOES UP. It is what makes
    a `401` land on the credential that caused it: a late failure from a
    request made under generation 3 must not mark the credential a newer
    sign-in just stored as broken.
    """
    blob = {
        "key": credential.key,
        "method": credential.method,
        "scope": credential.scope,
        "generation": credential.generation,
        "account": credential.account,
    }
    import json

    where = credential_path()
    storage.write_atomically(where, json.dumps(blob).encode("utf-8"))
    with swallow("a mode this platform will not set is not a reason to lose the credential"):
        where.chmod(0o600)


def load_credential(env: Optional[Mapping[str, str]] = None) -> Optional[orcarouter.Credential]:
    """The stored credential, or the one in the environment, or nothing.

    ⛔ THE ENVIRONMENT IS READ SECOND, NOT FIRST, AND BOTH ARE READ HERE. A key
    exported in a shell is a deliberate act for one run; a key the user signed
    in for is a decision about this installation. Neither is a second store -
    the environment is the mechanism this package already documents for a key,
    and the file is the one it already uses for saved things.
    """
    saved = storage.read_json(credential_path())
    if isinstance(saved, dict) and isinstance(saved.get("key"), str) and saved["key"].strip():
        return orcarouter.Credential(
            saved["key"].strip(),
            method=saved.get("method") or orcarouter.BY_KEY,
            source="stored",
            generation=int(saved.get("generation") or 1),
            scope=str(saved.get("scope") or ""),
            account=str(saved.get("account") or ""),
        )
    from_env = orcarouter.key_from_environment(env)
    if from_env:
        return orcarouter.Credential(from_env, method=orcarouter.BY_KEY,
                                     source="environment")
    return None


def forget_credential() -> None:
    """Delete the stored credential.

    ⛔ NOT CALLED BEFORE A REPLACEMENT SUCCEEDS. A `401` marks the credential
    that made the request; it does not delete anything, because a failure that
    was transient or misclassified would then be irreversible, and the user
    would have to sign in again to recover from a blip.
    """
    storage.erase(credential_path())


class ProviderState:
    """What the panel draws, and the one writer of it.

    ⛔ ONE OWNER, BECAUSE THE ALTERNATIVE IS TWO SCREENS THAT DISAGREE. The
    provider, its credential, the model list and which sign-in attempt is live
    are one piece of state: choosing OrcaRouter has to recompute the model list,
    and a model chosen under OpenRouter has to be refused under OrcaRouter. Kept
    here so the routes read a fact rather than each assembling their own.
    """

    def __init__(self, env: Optional[Mapping[str, str]] = None) -> None:
        self._env = env
        self.provider = DEFAULT_PROVIDER
        self.model = ""
        self.credential: Optional[orcarouter.Credential] = None
        #: ⛔ THE SEED IS WHAT A PROVIDER THAT HAS NOTHING YET OFFERS, and the
        #: source says so from the first answer rather than only after a failed
        #: refresh. A panel that showed an empty list until somebody signed in
        #: would be a panel that looks broken, and one that showed an empty
        #: list LABELLED `live` would be a claim about an account that has not
        #: been read yet.
        self.models: List[orcarouter.Model] = orcarouter.seed_models()
        self.source = orcarouter.SEED_SOURCE
        self.attempt = 0
        self.catalog_error = ""

    @property
    def chosen(self) -> str:
        """The provider this run actually talks to, as an id."""
        return self.provider

    def choose(self, name: Optional[str], model: Optional[str] = None) -> None:
        """Point this interface at a provider, and at a model if one is given.

        ⛔ THE MODEL IS RECOMPUTED, NOT KEPT. A model id chosen while OpenRouter
        was selected is not in OrcaRouter's catalogue and would be a request
        that fails at the first turn with the reason nowhere near the cause, so
        changing provider clears it unless the caller names one that the new
        provider offers.
        """
        self.provider = known(name)
        if model is not None:
            self.model = self._acceptable(model)
        elif self.provider != DEFAULT_PROVIDER:
            self.model = ""

    def _acceptable(self, model: str) -> str:
        """This model id if the current provider can serve it, else empty.

        ⛔ REVALIDATED AGAINST THE CURRENT LIST, every time. A saved id restored
        from disk, or one typed before the catalogue changed, is a request that
        fails later in a place that says nothing about where the id came from.
        """
        wanted = (model or "").strip()
        if not wanted:
            return ""
        if self.provider == DEFAULT_PROVIDER:
            return wanted
        if not self.models:
            # ⛔ NOTHING HAS BEEN DISCOVERED YET, SO NOTHING CAN BE CHECKED, and
            # the id is taken on trust UNTIL `set_catalog` arrives - which
            # revalidates it and clears it if the catalogue does not offer it.
            # Refusing here instead would throw away an explicit --model before
            # the list that judges it has been read.
            return wanted
        offered = {m.id for m in self.offered("chat")}
        return wanted if wanted in offered else ""

    def set_credential(self, credential: Optional[orcarouter.Credential]) -> None:
        """Take this credential, or none, as the current one.

        ⛔ THE GENERATION IS INCREASED BY THE CALLER, NOT HERE, and that is what
        keeps a late answer from an old attempt out of a new credential: the
        route builds a credential with a generation it owns and this method
        never invents one.
        """
        self.credential = credential
        if credential is not None and not is_orcarouter(self.provider):
            # ⛔ A CREDENTIAL IS AN ORCAROUTER CREDENTIAL, so taking one moves
            # the provider with it. `is_orcarouter` is the one place that
            # decides which ids those are, so a third OrcaRouter id added later
            # is not a second list to keep in step.
            self.provider = "orcarouter"
        if credential is None:
            self.models = []
            self.source = orcarouter.LIVE_SOURCE
            self.catalog_error = ""

    def set_catalog(self, models: List[orcarouter.Model], source: str,
                    error: str = "") -> None:
        """Take this catalogue as the list the dropdown draws.

        ⛔ A LIVE ANSWER REPLACES THE SEED ENTIRELY. Mixing the two would make
        the dropdown a claim about the account that is partly verified and
        partly not, and there would be no way to tell which rows those were.
        """
        self.models = list(models)
        self.source = source
        self.catalog_error = error
        if self.model and not self._acceptable(self.model):
            # ⛔ CLEARED, NOT KEPT. A model that is no longer in the compatible
            # list is a request that will fail; leaving it selected and hoping
            # is how a person sends a turn that dies for a reason the screen
            # does not show.
            self.model = ""

    def offered(self, capability: str = "chat",
                modality: Optional[str] = None) -> List[orcarouter.Model]:
        """The models this provider offers for one capability.

        From the seed only when a live discovery failed, and from the live
        answer whenever there is one - the same rule `set_catalog` states.
        """
        return orcarouter.models_for(self.models, capability, modality)

    def model_label(self) -> str:
        """What the badge in the header says this conversation is running on."""
        if self.provider == DEFAULT_PROVIDER:
            return ""
        return self.model or "no model chosen"

    def as_state(self) -> Dict[str, Any]:
        """What the page may be told. ⛔ No key, ever, in any field."""
        credential = self.credential.as_state() if self.credential else {
            "set": False, "masked": "", "method": "", "source": "",
            "generation": 0, "scope": "", "needs_reauth": False}
        return {
            "provider": self.provider,
            "providers": dict(PROVIDERS),
            "model": self.model,
            "credential": credential,
            "source": self.source,
            "catalog_error": self.catalog_error,
            "attempt": self.attempt,
            "models": [m.as_state() for m in self.offered("chat")],
        }
