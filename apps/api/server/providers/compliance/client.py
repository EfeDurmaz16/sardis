"""Thin HTTP clients for the compliance providers Sardis supports.

Two providers live here, each researched against its CURRENT (2026) API.  A
compliance adapter NEVER authorizes/initiates/settles money: it only *creates an
identity session* (KYC/KYB) or *reports a screening verdict* (AML/KYT).  The
orchestrator (the authority core / moat) decides allow/deny — the port only
reports.  Both providers are therefore identity/verdict services, not custody:
they are surfaced with ``CustodyModel.PARTNER_CUSTODIED`` because a regulated
verification partner performs the verification of record, while Sardis never
takes custody of funds on these paths.

No secret is hardcoded; credentials arrive via the registry from env.

Didit (one /v3/ API — KYC + KYB w/ UBO + AML + wallet KYT)
----------------------------------------------------------
Researched via WebSearch + context7 ``/websites/didit_me``
(``docs.didit.me``, ``docs.didit.me/openapi-25.json``,
``docs.didit.me/integration/webhooks``,
``docs.didit.me/business-verification/integration-guide``) and the existing
backend client ``packages/sardis/src/sardis/compliance/providers/didit.py``:

* **Auth/base:** header ``x-api-key: <DIDIT_API_KEY>``; base
  ``https://verification.didit.me``.  Single unified ``/v3/`` API.
* **Create session (KYC *or* KYB):** ``POST /v3/session/`` with
  ``{workflow_id, vendor_data, callback_url?, metadata?, contact_details?,
  expected_details?}``.  The ``workflow_id`` alone decides whether the session
  is KYC or KYB (a KYB workflow returns Key People / UBOs).  Returns
  ``{session_id, session_token, url, status}``.
* **Decision/status:** ``GET /v3/session/{session_id}/decision/`` returns
  ``{status, id_verifications?, liveness_checks?, face_matches?,
  aml_screenings?, kyb / key_people_checks? / ubo_kyc_summary? (KYB)}``.
  Statuses (Title Case): ``Approved`` | ``Declined`` | ``In Review`` |
  ``In Progress`` | ``Not Started`` | ``Resubmitted`` | ``Expired`` | …
* **Standalone AML screening (KYT counterparty):** ``POST /v3/aml/`` with
  ``{entity_type:"person"|"company", include_ongoing_monitoring?, ...name
  fields}``.  Returns ``{request_id, aml:{status, total_hits, entity_type,
  hits:[{id, match, score, caption, datasets, ...}]}}``.
* **Webhooks (HMAC-SHA256):** headers ``X-Signature`` (HMAC of the *raw* body),
  ``X-Signature-V2`` (HMAC of the ASCII-escaped JSON body — middleware-safe),
  and ``X-Timestamp``.  Verification = constant-time compare of
  ``HMAC_SHA256(WEBHOOK_SECRET, raw_body)`` against ``X-Signature`` **and** a
  freshness check that ``|now - X-Timestamp| <= 300s``.  Fail-closed when the
  secret is unset or any header is missing.

Didit has no native on-chain wallet-address KYT primitive in the documented
``/v3/`` surface; wallet/counterparty screening on the KytPort therefore routes
its *named-counterparty* check to ``/v3/aml/``.  Raw on-chain *address*
screening is delegated to OpenSanctions (below), which the registry wires as the
KYT provider when its key is present.

OpenSanctions (self-serve, pay-as-you-go sanctions / PEP / watchlist screening)
-------------------------------------------------------------------------------
Researched via WebSearch + ``opensanctions.org/docs/api`` +
``api.opensanctions.org/openapi.json``:

* **Auth/base:** header ``Authorization: ApiKey <OPENSANCTIONS_API_KEY>``; base
  ``https://api.opensanctions.org``.
* **Match (screening) endpoint:** ``POST /match/{scope}`` where ``scope`` is a
  dataset/collection (``default`` = all entities; ``sanctions`` = sanctions
  only; or a specific list like ``us_ofac_sdn``).  Query params: ``algorithm``
  (default ``best``), ``threshold`` (default ``0.7``), ``limit`` (default 5,
  max 500).  Body = ``{"queries": {"<qid>": {"schema": "Person"|"Company"|...,
  "properties": {"name": [...], ...}}}}``.  Response =
  ``{"responses": {"<qid>": {"results": [{"id", "score", "match", "schema",
  "properties", "datasets", "topics", ...}], "total": {"value": N}}}}``.
* No native on-chain address topic exists; an EVM/crypto address is screened by
  passing it as a ``cryptoWallet`` property (the FollowTheMoney ``CryptoWallet``
  schema) and, where a name is unknown, as the entity ``name`` so the matcher
  can still surface a sanctioned wallet listed by address.

No compliance client ever holds/authorizes/initiates/settles funds.  No
policy / KYA / mandate decision happens here (those live in the moat) — the
client returns a normalized verdict and the orchestrator decides.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# -- Didit -----------------------------------------------------------------
_DIDIT_BASE = "https://verification.didit.me"

# -- OpenSanctions ---------------------------------------------------------
_OPENSANCTIONS_BASE = "https://api.opensanctions.org"

_DEFAULT_TIMEOUT = 30.0

#: Max clock skew (seconds) tolerated for a Didit webhook ``X-Timestamp``.
_WEBHOOK_MAX_SKEW_SECONDS = 300


def _is_sandbox_env(environment: str) -> bool:
    return environment.strip().lower() in {
        "sandbox",
        "staging",
        "test",
        "development",
        "dev",
    }


@dataclass
class KycSession:
    """Normalized identity-verification session (KYC *or* KYB).

    ``session_id`` is the Didit session id; ``verification_url`` is the hosted
    link the subject completes.  Never carries PII beyond what the caller
    supplied; the raw vendor payload is kept in ``raw`` for audit replay.
    """

    session_id: str
    #: Normalized status: ``pending`` | ``approved`` | ``declined`` |
    #: ``needs_review`` | ``expired`` | ``not_started`` | raw when unmapped.
    status: str
    kind: str = "kyc"
    verification_url: str | None = None
    session_token: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreeningHit:
    """A single sanctions/PEP/watchlist match, normalized across providers."""

    hit_id: str
    caption: str | None = None
    score: float | None = None
    match: bool = False
    datasets: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreeningResult:
    """Normalized screening verdict.  The port reports; the moat decides.

    ``status`` is one of ``clear`` (no confirmed hits) | ``hit`` (>=1 match) |
    ``review`` (potential but unconfirmed) — but the orchestrator makes the
    allow/deny call; this is a *report*, not a decision.
    """

    status: str
    total_hits: int
    hits: list[ScreeningHit] = field(default_factory=list)
    reference: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


# =========================================================================
# Didit (KYC + KYB + AML) — one /v3/ API
# =========================================================================


@dataclass(frozen=True)
class DiditConfig:
    """Resolved Didit runtime.  No secret is ever logged.

    ``kyc_workflow_id`` / ``kyb_workflow_id`` select KYC vs KYB at session
    creation.  ``webhook_secret`` backs HMAC-SHA256 webhook verification; when
    absent, :meth:`DiditClient.verify_webhook` fails closed.
    """

    api_key: str
    kyc_workflow_id: str | None = None
    kyb_workflow_id: str | None = None
    webhook_secret: str | None = None
    callback_url: str | None = None
    environment: str = "production"
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        return _is_sandbox_env(self.environment)


class DiditClient:
    """``POST /v3/session/`` + ``GET .../decision/`` + ``POST /v3/aml/``."""

    #: Map Didit status (Title Case, spaces) -> normalized verb.
    _STATUS_MAP = {
        "not started": "not_started",
        "in progress": "pending",
        "approved": "approved",
        "declined": "declined",
        "in review": "needs_review",
        "resubmitted": "pending",
        "expired": "expired",
        "abandoned": "expired",
        "kyc expired": "expired",
        "awaiting user": "pending",
    }

    def __init__(self, config: DiditConfig) -> None:
        if not config.api_key:
            raise ValueError("Didit API key is required")
        self._config = config
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    @property
    def has_webhook_secret(self) -> bool:
        return bool(self._config.webhook_secret)

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=_DIDIT_BASE,
                timeout=self._config.timeout_seconds,
                headers={
                    "x-api-key": self._config.api_key,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    @classmethod
    def _normalize_status(cls, raw_status: str | None) -> str:
        s = (raw_status or "").strip().lower()
        mapped = cls._STATUS_MAP.get(s)
        if mapped is None:
            logger.warning("Didit: unknown status %r -> pending", raw_status)
            return "pending"
        return mapped

    def _workflow_for(self, kind: str) -> str:
        kind_l = kind.strip().lower()
        if kind_l in {"kyb", "business"}:
            wf = self._config.kyb_workflow_id
            if not wf:
                raise ValueError("DIDIT_KYB_WORKFLOW_ID is required for a KYB session")
            return wf
        wf = self._config.kyc_workflow_id
        if not wf:
            raise ValueError("DIDIT_KYC_WORKFLOW_ID is required for a KYC session")
        return wf

    async def create_session(
        self,
        *,
        subject_ref: str,
        kind: str = "kyc",
        metadata: dict[str, Any] | None = None,
    ) -> KycSession:
        """``POST /v3/session/`` — create a KYC or KYB verification session."""
        body: dict[str, Any] = {
            "workflow_id": self._workflow_for(kind),
            "vendor_data": subject_ref,
        }
        if self._config.callback_url:
            body["callback_url"] = self._config.callback_url
        meta = dict(metadata or {})
        # Optional contact/expected detail passthrough (no PII is mandatory).
        contact = meta.pop("contact_details", None)
        expected = meta.pop("expected_details", None)
        if contact:
            body["contact_details"] = contact
        if expected:
            body["expected_details"] = expected
        if meta:
            body["metadata"] = meta

        client = await self._client_()
        resp = await client.post("/v3/session/", json=body)
        resp.raise_for_status()
        data = resp.json()
        return KycSession(
            session_id=str(data.get("session_id") or ""),
            status=self._normalize_status(data.get("status")),
            kind="kyb" if kind.strip().lower() in {"kyb", "business"} else "kyc",
            verification_url=data.get("url") or None,
            session_token=data.get("session_token") or None,
            raw=data,
        )

    async def get_decision(self, session_id: str) -> KycSession:
        """``GET /v3/session/{id}/decision/`` — fetch the session decision."""
        client = await self._client_()
        resp = await client.get(f"/v3/session/{session_id}/decision/")
        resp.raise_for_status()
        data = resp.json()
        is_kyb = bool(
            data.get("kyb") or data.get("key_people_checks") or data.get("ubo_kyc_summary")
        )
        return KycSession(
            session_id=session_id,
            status=self._normalize_status(data.get("status")),
            kind="kyb" if is_kyb else "kyc",
            verification_url=data.get("url") or None,
            raw=data,
        )

    async def screen_aml(
        self,
        *,
        name: str,
        entity_type: str = "person",
        include_ongoing_monitoring: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> ScreeningResult:
        """``POST /v3/aml/`` — standalone AML/PEP/watchlist screening."""
        et = entity_type.strip().lower()
        if et not in {"person", "company"}:
            raise ValueError("entity_type must be 'person' or 'company'")
        body: dict[str, Any] = {
            "entity_type": et,
            "name": name,
            "include_ongoing_monitoring": bool(include_ongoing_monitoring),
        }
        if metadata:
            body.update(metadata)
        client = await self._client_()
        resp = await client.post("/v3/aml/", json=body)
        resp.raise_for_status()
        data = resp.json()
        aml = data.get("aml") or {}
        hits_raw = aml.get("hits") or []
        hits = [
            ScreeningHit(
                hit_id=str(h.get("id") or ""),
                caption=h.get("caption"),
                score=_as_float(h.get("score")),
                match=bool(h.get("match")),
                datasets=list(h.get("datasets") or []),
                raw=h,
            )
            for h in hits_raw
        ]
        total_hits = int(aml.get("total_hits") or 0)
        return ScreeningResult(
            status=_screening_status(total_hits=total_hits, hits=hits),
            total_hits=total_hits,
            hits=hits,
            reference=str(data.get("request_id") or "") or None,
            raw=data,
        )

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> bool:
        """Verify a Didit webhook.  Fail-CLOSED.

        Checks (per docs.didit.me/integration/webhooks):

        1. ``WEBHOOK_SECRET`` is configured (else fail closed);
        2. ``X-Signature`` and ``X-Timestamp`` headers are present;
        3. ``X-Timestamp`` is within ``300s`` of now (replay/staleness guard);
        4. ``HMAC_SHA256(secret, raw_body)`` matches ``X-Signature`` via a
           constant-time compare.

        Header lookups are case-insensitive (frameworks normalize casing).
        """
        secret = self._config.webhook_secret
        if not secret:
            logger.warning("Didit webhook secret not configured; failing closed")
            return False
        h = {k.lower(): v for k, v in headers.items()}
        signature = h.get("x-signature")
        timestamp = h.get("x-timestamp")
        if not signature or not timestamp:
            logger.warning("Didit webhook missing X-Signature/X-Timestamp; failing closed")
            return False
        try:
            incoming = int(timestamp)
        except (TypeError, ValueError):
            logger.warning("Didit webhook X-Timestamp not an int; failing closed")
            return False
        if abs(int(time.time()) - incoming) > _WEBHOOK_MAX_SKEW_SECONDS:
            logger.warning(
                "Didit webhook timestamp stale (>%ss); failing closed", _WEBHOOK_MAX_SKEW_SECONDS
            )
            return False
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            logger.warning("Didit webhook signature mismatch; failing closed")
            return False
        return True


# =========================================================================
# OpenSanctions (sanctions / PEP / watchlist screening)
# =========================================================================


@dataclass(frozen=True)
class OpenSanctionsConfig:
    """Resolved OpenSanctions runtime.  The API key is never logged."""

    api_key: str
    #: Dataset/collection scope for the match endpoint.  ``default`` = all
    #: entities; ``sanctions`` = sanctions-only; or a specific list id.
    scope: str = "default"
    algorithm: str = "best"
    threshold: float = 0.7
    limit: int = 5
    environment: str = "production"
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        # OpenSanctions has one host; treat a non-prod env label as sandbox so a
        # dev deployment never reports a verdict as a production screening.
        return _is_sandbox_env(self.environment)


class OpenSanctionsClient:
    """``POST /match/{scope}`` over httpx (Authorization: ApiKey <key>)."""

    def __init__(self, config: OpenSanctionsConfig) -> None:
        if not config.api_key:
            raise ValueError("OpenSanctions API key is required")
        self._config = config
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=_OPENSANCTIONS_BASE,
                timeout=self._config.timeout_seconds,
                headers={
                    "Authorization": f"ApiKey {self._config.api_key}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def match(
        self,
        *,
        properties: dict[str, list[str]],
        schema: str = "Person",
        query_id: str = "q1",
    ) -> ScreeningResult:
        """``POST /match/{scope}`` — query-by-example screening.

        ``properties`` is a FollowTheMoney property map (e.g.
        ``{"name": [...]}`` or ``{"cryptoWallet": [...]}``); values are always
        lists.  Returns a normalized verdict; the orchestrator decides.
        """
        body = {"queries": {query_id: {"schema": schema, "properties": properties}}}
        params = {
            "algorithm": self._config.algorithm,
            "threshold": self._config.threshold,
            "limit": self._config.limit,
        }
        client = await self._client_()
        resp = await client.post(f"/match/{self._config.scope}", json=body, params=params)
        resp.raise_for_status()
        data = resp.json()
        responses = data.get("responses") or {}
        block = responses.get(query_id) or {}
        results = block.get("results") or []
        hits = [
            ScreeningHit(
                hit_id=str(r.get("id") or ""),
                caption=r.get("caption") or _first_name(r),
                score=_as_float(r.get("score")),
                match=bool(r.get("match")),
                datasets=list(r.get("datasets") or []),
                topics=list(r.get("topics") or []),
                raw=r,
            )
            for r in results
        ]
        confirmed = [h for h in hits if h.match]
        return ScreeningResult(
            status=_screening_status(total_hits=len(confirmed), hits=hits),
            total_hits=len(confirmed),
            hits=hits,
            reference=query_id,
            raw=block,
        )


# -- shared normalization helpers -----------------------------------------


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_name(result: dict[str, Any]) -> str | None:
    props = result.get("properties") or {}
    names = props.get("name") if isinstance(props, dict) else None
    if isinstance(names, list) and names:
        return str(names[0])
    return None


def _screening_status(*, total_hits: int, hits: list[ScreeningHit]) -> str:
    """Normalize a screening verdict to ``clear`` | ``hit`` | ``review``.

    A confirmed match (``match=True`` / ``total_hits>0``) is a ``hit``.  Any
    unconfirmed candidate is ``review`` (the orchestrator may treat review as a
    hold).  No candidates at all is ``clear``.  The port only reports — the moat
    makes the allow/deny decision.
    """
    if total_hits > 0 or any(h.match for h in hits):
        return "hit"
    if hits:
        return "review"
    return "clear"
