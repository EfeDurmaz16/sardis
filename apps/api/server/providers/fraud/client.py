"""Thin HTTP clients for the external fraud-signal feeds.

Each provider was researched against its CURRENT (2026) API.

Stripe Radar (network fraud model; risk_score on the Charge outcome)
--------------------------------------------------------------------
Researched via WebSearch + Stripe docs
(``docs.stripe.com/radar/risk-evaluation``, ``docs.stripe.com/radar``,
``docs.stripe.com/radar/reviews/risk-insights``):

* Radar does not expose a standalone "score this transaction" endpoint for
  arbitrary off-Stripe payments.  The Radar risk score rides on the
  ``charge.outcome`` object of a Stripe-processed PaymentIntent / Charge:
  ``outcome.risk_score`` (0-99, Radar **for Fraud Teams** only),
  ``outcome.risk_level`` (``normal`` | ``elevated`` | ``highest`` |
  ``not_assessed`` | ``unknown``), ``outcome.network_status``,
  ``outcome.reason`` (e.g. ``highest_risk_level``), ``outcome.type``
  (``authorized`` | ``manual_review`` | ``blocked``).
* Default risk bands (docs): 0-64 normal (allowed), 65-74 elevated (review),
  75-99 highest (blocked by default).
* Integration here: when an upstream Stripe charge/PaymentIntent id is supplied
  in the context (the agent paid a card leg through Stripe Issuing / a Stripe
  checkout), we read its outcome via ``GET /v1/charges/{id}`` and surface the
  network score as a signal.  No charge id -> NOT_ASSESSED (Sardis-native
  on-chain legs are not Stripe-scored).  Auth: ``Authorization: Bearer
  sk_...`` — never hardcoded; arrives from env via the registry.
* Base URL: ``https://api.stripe.com``.

SEON (device / email / IP / phone intelligence; Fraud API v2)
-------------------------------------------------------------
Researched via WebSearch + SEON docs
(``docs.seon.io/api-reference/fraud-api``,
``docs.seon.io/knowledge-base/transactions-scoring/score-calculation-logic``):

* ``POST {base}/SeonRestService/fraud-api/v2.0`` (EU host
  ``https://api.seon.io``; US ``https://api.us-east-1-main.seon.io`` with
  ``/v2/``).  Auth header ``X-API-KEY: <key>``.
* Response ``data.fraud_score`` (0-100, higher = riskier),
  ``data.state`` (``APPROVE`` | ``REVIEW`` | ``DECLINE``),
  ``data.applied_rules`` (``[{id,name,operation,score}]``), ``data.id``.
* Request body carries optional intelligence fields the engine supplies when it
  has them: ``transaction_amount``, ``transaction_currency``, ``email``,
  ``ip``, ``user_id``, ``user_fullname``, plus config flags
  (``email_api`` / ``ip_api`` / ``device_fingerprinting``).  SEON scores on
  whatever subset is present, so an agent payment with only an amount + a
  pseudonymous ``user_id`` still returns a score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

_STRIPE_BASE = "https://api.stripe.com"
_SEON_EU_BASE = "https://api.seon.io"


def _is_sandbox_env(environment: str | None) -> bool:
    return (environment or "sandbox").strip().lower() not in ("production", "prod", "live")


# ──────────────────────────────────────────────────────────────────────────
# Stripe Radar
# ──────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StripeRadarConfig:
    api_key: str
    environment: str = "sandbox"
    timeout_seconds: float = 8.0

    @property
    def is_sandbox(self) -> bool:
        # A live Stripe secret key (sk_live_...) is production; test keys
        # (sk_test_...) and any non-prod environment are sandbox.
        if self.api_key.startswith("sk_live_"):
            return False
        return _is_sandbox_env(self.environment)


@dataclass(frozen=True)
class StripeOutcome:
    """Normalized Stripe charge outcome (the Radar read)."""

    charge_id: str
    risk_level: str          # normal | elevated | highest | not_assessed | unknown
    risk_score: int | None   # 0-99 (Fraud Teams only); None otherwise
    outcome_type: str | None  # authorized | manual_review | blocked
    reason: str | None
    raw: dict[str, Any]


class StripeRadarClient:
    """``GET /v1/charges/{id}`` — reads the Radar outcome of a Stripe charge."""

    def __init__(self, config: StripeRadarConfig) -> None:
        if not config.api_key:
            raise ValueError("Stripe Radar api_key is required")
        self._config = config
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=_STRIPE_BASE,
                timeout=self._config.timeout_seconds,
                headers={
                    "Authorization": f"Bearer {self._config.api_key}",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def get_charge_outcome(self, charge_id: str) -> StripeOutcome:
        client = await self._client_()
        resp = await client.get(f"/v1/charges/{charge_id}")
        resp.raise_for_status()
        data = resp.json()
        outcome = data.get("outcome") or {}
        score = outcome.get("risk_score")
        return StripeOutcome(
            charge_id=str(data.get("id") or charge_id),
            risk_level=str(outcome.get("risk_level") or "not_assessed"),
            risk_score=int(score) if isinstance(score, (int, float)) else None,
            outcome_type=outcome.get("type"),
            reason=outcome.get("reason"),
            raw=data,
        )


# ──────────────────────────────────────────────────────────────────────────
# SEON
# ──────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SeonConfig:
    api_key: str
    environment: str = "sandbox"
    base_url: str = _SEON_EU_BASE
    timeout_seconds: float = 8.0

    @property
    def is_sandbox(self) -> bool:
        return _is_sandbox_env(self.environment)


@dataclass(frozen=True)
class SeonResult:
    """Normalized SEON fraud-api response."""

    seon_id: str
    fraud_score: float       # 0-100, higher = riskier
    state: str               # APPROVE | REVIEW | DECLINE
    applied_rules: list[dict[str, Any]]
    raw: dict[str, Any]


class SeonClient:
    """``POST /SeonRestService/fraud-api/v2.0`` — SEON fraud score + state."""

    _PATH = "/SeonRestService/fraud-api/v2.0"

    def __init__(self, config: SeonConfig) -> None:
        if not config.api_key:
            raise ValueError("SEON api_key is required")
        self._config = config
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._config.base_url,
                timeout=self._config.timeout_seconds,
                headers={
                    "X-API-KEY": self._config.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def score(self, body: dict[str, Any]) -> SeonResult:
        client = await self._client_()
        resp = await client.post(self._PATH, json=body)
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("success", True):
            err = payload.get("error") or {}
            raise httpx.HTTPError(f"seon_error: {err}")
        data = payload.get("data") or {}
        raw_score = data.get("fraud_score", 0)
        return SeonResult(
            seon_id=str(data.get("id") or data.get("seon_id") or ""),
            fraud_score=float(raw_score) if isinstance(raw_score, (int, float)) else 0.0,
            state=str(data.get("state") or "APPROVE"),
            applied_rules=list(data.get("applied_rules") or []),
            raw=payload,
        )
