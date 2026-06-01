"""Thin HTTP clients for the card-issuing providers Sardis supports.

Three providers live here, each researched against its CURRENT (2026) API.  A
card-issuing adapter NEVER authorizes a transaction on its own: it only issues a
card / sets a control / changes a card's state that the orchestrator already
authorized, then normalizes the vendor response.  All three are
**partner-custodied** — a regulated issuer (Crossmint+Rain, Lithic, Stripe)
holds the card program / settlement relationship; Sardis remains non-custodial.

A real PAN (full card number) is never returned by these clients — only
tokenized references (card id, last four, expiry).  Money crosses the boundary
as integer minor units (USD cents) and is converted to the vendors' integer/
string fields with ``int``/``str`` only — never ``float``.

Crossmint Agentic Cards (PRIMARY — non-custodial dual-key, agent-bound VCs)
--------------------------------------------------------------------------
Researched via WebSearch + context7 ``/websites/crossmint``
(``docs.crossmint.com/api-reference/introduction``,
``docs.crossmint.com/wallets/guides/wallet-extensions/credit-cards``,
``crossmint.com/products/agentic-cards``):

* **Crossmint platform auth/base:** header ``X-API-KEY``; hosts
  ``https://staging.crossmint.com/api`` (testnets) and
  ``https://www.crossmint.com/api`` (mainnets).  Card issuance on Crossmint is
  delivered through its **Rain** card-issuing extension, so the concrete card
  endpoints are Rain's (below).  The Crossmint key is carried so wallet-bound /
  agentic-card flows that ride the Crossmint platform can be wired later without
  changing the port.
* **Agentic-card model:** scoped, single-use virtual credentials derived from a
  card on file; spend limits, merchant-category and approval rules; revocable at
  any time; the real PAN never leaves Crossmint's PCI vault and is never exposed
  to agent tools (we only ever surface tokenized refs).
* **Rain issuing API (the card surface):** header ``Api-Key``; base
  ``https://api-dev.raincards.xyz/v1`` (dev/sandbox) and
  ``https://api.raincards.xyz/v1`` (production).
  - Issue card: ``POST /issuing/users/{userId}/cards`` with
    ``{type:"virtual", limit:{frequency, amount}, displayName, status}``.
    Returns ``{id, type, status, last4, expirationMonth, expirationYear,
    limit}`` — tokenized, no PAN.
  - List cards: ``GET /issuing/cards?userId={userId}&limit=N``.
  - Update / freeze / set-limit: ``PATCH /issuing/cards/{cardId}`` with the
    fields to change (``status`` for freeze/active, ``limit`` for the cap).  The
    exact PATCH path is not fully published; it is gated behind a live key and
    surfaced explicitly as not-verifiable-without-keys.
  - Frequency for an all-time cap is ``allTime``; ``amount`` is the limit value.

Lithic (FALLBACK — Sardis's own BIN, already partially in backend)
------------------------------------------------------------------
Researched via WebSearch + Lithic docs (``docs.lithic.com``):

* **Auth/base:** header ``Authorization: <api_key>``; hosts
  ``https://sandbox.lithic.com/v1`` (sandbox) and ``https://api.lithic.com/v1``
  (production).
* **Issue card:** ``POST /cards`` with ``{type:"VIRTUAL",
  spend_limit:<cents int>, spend_limit_duration:"MONTHLY"|"TRANSACTION"|
  "ANNUALLY"|"FOREVER", state:"OPEN", memo}``.  Returns ``{token, state,
  last_four, ...}`` — tokenized; the PAN is only ever returned via Lithic's
  enrollment/PCI surface, never by this client.
* **Freeze / set state:** ``PATCH /cards/{card_token}`` with
  ``{state:"OPEN"|"PAUSED"|"CLOSED"}`` (CLOSED is terminal).
* **Set limit:** ``PATCH /cards/{card_token}`` with ``{spend_limit,
  spend_limit_duration}``.

Stripe Issuing (FALLBACK)
-------------------------
Researched via WebSearch + Stripe docs (``docs.stripe.com/issuing``):

* **Auth/base:** HTTP Basic with the secret key as the username (``Bearer
  <sk_...>`` also accepted); host ``https://api.stripe.com/v1``.  No separate
  sandbox host — a test-mode key (``sk_test_...``) is the sandbox.
* **Issue card:** ``POST /issuing/cards`` (form-encoded) with
  ``cardholder=<id>``, ``currency=usd``, ``type=virtual``, ``status=active``,
  and ``spending_controls[spending_limits][0][amount]`` (cents int) +
  ``[interval]`` (``per_authorization``|``monthly``|``all_time``).  Returns
  ``{id, status, last4, ...}`` — tokenized; the PAN requires the Issuing
  Elements / ephemeral-key surface and is never returned here.
* **Freeze / set state:** ``POST /issuing/cards/{card}`` with
  ``status=active|inactive|canceled`` (canceled is terminal).
* **Set limit:** ``POST /issuing/cards/{card}`` with the same
  ``spending_controls[spending_limits][...]`` form fields.

No card client ever holds, authorizes, initiates, or settles funds beyond
executing the already-authorized issue/freeze/limit instruction.  No policy /
KYA / sanctions / mandate checks happen here (those live in the moat).  No
secret is hardcoded; credentials arrive via the registry from env.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# -- Crossmint platform ----------------------------------------------------
_CROSSMINT_PROD_BASE = "https://www.crossmint.com/api"
_CROSSMINT_STAGING_BASE = "https://staging.crossmint.com/api"

# -- Rain (Crossmint's card-issuing extension) -----------------------------
_RAIN_PROD_BASE = "https://api.raincards.xyz/v1"
_RAIN_DEV_BASE = "https://api-dev.raincards.xyz/v1"

# -- Lithic ----------------------------------------------------------------
_LITHIC_PROD_BASE = "https://api.lithic.com/v1"
_LITHIC_SANDBOX_BASE = "https://sandbox.lithic.com/v1"

# -- Stripe Issuing --------------------------------------------------------
_STRIPE_BASE = "https://api.stripe.com/v1"

_DEFAULT_TIMEOUT = 20.0


def _is_sandbox_env(environment: str) -> bool:
    return environment.strip().lower() in {
        "sandbox",
        "staging",
        "test",
        "development",
        "dev",
    }


@dataclass
class IssuedCard:
    """Normalized issued-card descriptor.  TOKENIZED ONLY — never a real PAN.

    ``spend_limit_minor`` is an integer number of minor units (USD cents) or
    ``None`` when unlimited / unknown.  No float ever touches this struct.
    """

    card_id: str
    #: Normalized lifecycle status: ``active`` | ``frozen`` | ``closed`` |
    #: ``pending`` | the raw vendor status when it does not map cleanly.
    status: str
    last_four: str | None = None
    expiration_month: str | None = None
    expiration_year: str | None = None
    spend_limit_minor: int | None = None
    currency: str = "USD"
    raw: dict[str, Any] = field(default_factory=dict)


def _require_int_minor(
    amount_minor: int | None, *, field_name: str = "spend_limit_minor"
) -> int | None:
    if amount_minor is None:
        return None
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
        raise ValueError(f"{field_name} must be integer minor units (cents)")
    if amount_minor < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return amount_minor


# =========================================================================
# Crossmint Agentic Cards (Rain-backed)
# =========================================================================


@dataclass(frozen=True)
class CrossmintConfig:
    """Resolved Crossmint+Rain runtime.  Neither key is ever logged.

    ``api_key`` is the Crossmint ``X-API-KEY`` (platform / agentic-wallet
    surface).  ``rain_api_key`` is the Rain ``Api-Key`` that backs the concrete
    card-issuing endpoints; when absent, issuance cannot proceed and the adapter
    fails closed (the registry will have fallen back to the sandbox card).
    """

    api_key: str
    rain_api_key: str | None = None
    environment: str = "production"
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        return _is_sandbox_env(self.environment)


class CrossmintCardClient:
    """Crossmint agentic-card issuance via the Rain issuing API."""

    def __init__(self, config: CrossmintConfig) -> None:
        if not config.api_key:
            raise ValueError("Crossmint API key is required")
        self._config = config
        self._crossmint_base = (
            _CROSSMINT_STAGING_BASE if config.is_sandbox else _CROSSMINT_PROD_BASE
        )
        self._rain_base = _RAIN_DEV_BASE if config.is_sandbox else _RAIN_PROD_BASE
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    @property
    def has_rain(self) -> bool:
        return bool(self._config.rain_api_key)

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=self._config.timeout_seconds,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _rain_headers(self) -> dict[str, str]:
        if not self._config.rain_api_key:
            raise ValueError("Rain API key (CROSSMINT_RAIN_API_KEY) required for card issuance")
        return {
            "Api-Key": self._config.rain_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def _normalize_status(raw_status: str | None) -> str:
        s = (raw_status or "").strip().lower()
        if s in {"active", "open"}:
            return "active"
        if s in {"frozen", "paused", "inactive", "suspended"}:
            return "frozen"
        if s in {"closed", "canceled", "cancelled", "terminated", "revoked"}:
            return "closed"
        if s in {"pending"}:
            return "pending"
        return s or "unknown"

    def _to_issued_card(self, data: dict[str, Any]) -> IssuedCard:
        limit = data.get("limit") or {}
        amount = limit.get("amount") if isinstance(limit, dict) else None
        spend_limit_minor = None
        if amount is not None:
            # Rain limit amounts are whole-dollar integers; convert to cents
            # with integer arithmetic (no float).
            spend_limit_minor = int(amount) * 100
        return IssuedCard(
            card_id=str(data.get("id") or data.get("cardId") or ""),
            status=self._normalize_status(data.get("status")),
            last_four=str(data["last4"]) if data.get("last4") is not None else None,
            expiration_month=(
                str(data["expirationMonth"]) if data.get("expirationMonth") is not None else None
            ),
            expiration_year=(
                str(data["expirationYear"]) if data.get("expirationYear") is not None else None
            ),
            spend_limit_minor=spend_limit_minor,
            raw=data,
        )

    async def issue_card(
        self,
        *,
        user_ref: str,
        display_name: str,
        spend_limit_minor: int | None = None,
        frequency: str = "allTime",
    ) -> IssuedCard:
        """``POST /issuing/users/{userId}/cards`` — issue a virtual agentic card.

        ``spend_limit_minor`` is USD cents; Rain's ``limit.amount`` is in whole
        dollars, so we convert with integer arithmetic and reject a non-whole-
        dollar limit rather than silently truncating money.
        """
        amount_minor = _require_int_minor(spend_limit_minor)
        body: dict[str, Any] = {
            "type": "virtual",
            "displayName": display_name,
            "status": "active",
        }
        if amount_minor is not None:
            if amount_minor % 100 != 0:
                raise ValueError(
                    "Rain spend limit must be a whole-dollar amount (cents % 100 == 0)"
                )
            body["limit"] = {"frequency": frequency, "amount": amount_minor // 100}
        client = await self._client_()
        resp = await client.post(
            f"{self._rain_base}/issuing/users/{user_ref}/cards",
            json=body,
            headers=self._rain_headers(),
        )
        resp.raise_for_status()
        return self._to_issued_card(resp.json())

    async def update_card(
        self,
        *,
        card_id: str,
        status: str | None = None,
        spend_limit_minor: int | None = None,
        frequency: str = "allTime",
    ) -> IssuedCard:
        """``PATCH /issuing/cards/{cardId}`` — freeze/activate/close or re-cap.

        NOTE: the exact PATCH path for card mutation is not fully published by
        Rain; it is exercised only with a live key (see module docstring /
        not-verifiable list).  Status verbs map: ``active`` -> ``active``,
        ``frozen`` -> ``frozen``, ``closed`` -> ``closed``.
        """
        amount_minor = _require_int_minor(spend_limit_minor)
        body: dict[str, Any] = {}
        if status is not None:
            body["status"] = status
        if amount_minor is not None:
            if amount_minor % 100 != 0:
                raise ValueError(
                    "Rain spend limit must be a whole-dollar amount (cents % 100 == 0)"
                )
            body["limit"] = {"frequency": frequency, "amount": amount_minor // 100}
        if not body:
            raise ValueError("update_card requires status and/or spend_limit_minor")
        client = await self._client_()
        resp = await client.patch(
            f"{self._rain_base}/issuing/cards/{card_id}",
            json=body,
            headers=self._rain_headers(),
        )
        resp.raise_for_status()
        return self._to_issued_card(resp.json())


# =========================================================================
# Lithic (own BIN)
# =========================================================================


@dataclass(frozen=True)
class LithicCardConfig:
    """Resolved Lithic card-issuing runtime.  The API key is never logged."""

    api_key: str
    environment: str = "production"
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        return _is_sandbox_env(self.environment)


class LithicCardClient:
    """``POST /cards`` + ``PATCH /cards/{token}`` over httpx."""

    #: Map normalized verbs -> Lithic ``state`` enum.
    _STATE_MAP = {"active": "OPEN", "frozen": "PAUSED", "closed": "CLOSED"}

    def __init__(self, config: LithicCardConfig) -> None:
        if not config.api_key:
            raise ValueError("Lithic API key is required")
        self._config = config
        self._base = _LITHIC_SANDBOX_BASE if config.is_sandbox else _LITHIC_PROD_BASE
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._base,
                timeout=self._config.timeout_seconds,
                headers={
                    "Authorization": self._config.api_key,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    @staticmethod
    def _normalize_status(raw_status: str | None) -> str:
        s = (raw_status or "").strip().upper()
        if s == "OPEN":
            return "active"
        if s in {"PAUSED"}:
            return "frozen"
        if s in {"CLOSED"}:
            return "closed"
        if s in {"PENDING_ACTIVATION", "PENDING_FULFILLMENT"}:
            return "pending"
        return s.lower() or "unknown"

    def _to_issued_card(self, data: dict[str, Any]) -> IssuedCard:
        spend_limit = data.get("spend_limit")
        return IssuedCard(
            card_id=str(data.get("token") or ""),
            status=self._normalize_status(data.get("state")),
            last_four=str(data["last_four"]) if data.get("last_four") is not None else None,
            expiration_month=(
                str(data["exp_month"]) if data.get("exp_month") is not None else None
            ),
            expiration_year=str(data["exp_year"]) if data.get("exp_year") is not None else None,
            # Lithic spend_limit is already in minor units (cents).
            spend_limit_minor=int(spend_limit) if spend_limit is not None else None,
            raw=data,
        )

    async def issue_card(
        self,
        *,
        memo: str,
        spend_limit_minor: int | None = None,
        spend_limit_duration: str = "MONTHLY",
    ) -> IssuedCard:
        amount_minor = _require_int_minor(spend_limit_minor)
        body: dict[str, Any] = {"type": "VIRTUAL", "state": "OPEN", "memo": memo}
        if amount_minor is not None:
            body["spend_limit"] = amount_minor  # already cents
            body["spend_limit_duration"] = spend_limit_duration
        client = await self._client_()
        resp = await client.post("/cards", json=body)
        resp.raise_for_status()
        return self._to_issued_card(resp.json())

    async def set_state(self, *, card_id: str, state_verb: str) -> IssuedCard:
        lithic_state = self._STATE_MAP.get(state_verb)
        if lithic_state is None:
            raise ValueError(f"unknown card state verb {state_verb!r}")
        client = await self._client_()
        resp = await client.patch(f"/cards/{card_id}", json={"state": lithic_state})
        resp.raise_for_status()
        return self._to_issued_card(resp.json())

    async def set_limit(
        self, *, card_id: str, spend_limit_minor: int, spend_limit_duration: str = "MONTHLY"
    ) -> IssuedCard:
        amount_minor = _require_int_minor(spend_limit_minor)
        client = await self._client_()
        resp = await client.patch(
            f"/cards/{card_id}",
            json={"spend_limit": amount_minor, "spend_limit_duration": spend_limit_duration},
        )
        resp.raise_for_status()
        return self._to_issued_card(resp.json())


# =========================================================================
# Stripe Issuing
# =========================================================================


@dataclass(frozen=True)
class StripeIssuingConfig:
    """Resolved Stripe Issuing runtime.  The secret key is never logged.

    Stripe has a single host; a ``sk_test_...`` key is the sandbox.  The
    ``environment`` label is kept so a non-prod deployment never reports a
    result as a settled production movement.
    """

    api_key: str
    environment: str = "production"
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        # A test-mode key is the canonical sandbox signal; the env label is a
        # secondary override.
        if self.api_key.startswith("sk_test_"):
            return True
        return _is_sandbox_env(self.environment)


class StripeIssuingClient:
    """``POST /issuing/cards`` (form-encoded) over httpx."""

    #: Map normalized verbs -> Stripe ``status`` enum.
    _STATUS_MAP = {"active": "active", "frozen": "inactive", "closed": "canceled"}

    def __init__(self, config: StripeIssuingConfig) -> None:
        if not config.api_key:
            raise ValueError("Stripe API key is required")
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
                    # Stripe accepts the secret key as a Bearer token.
                    "Authorization": f"Bearer {self._config.api_key}",
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    @staticmethod
    def _normalize_status(raw_status: str | None) -> str:
        s = (raw_status or "").strip().lower()
        if s == "active":
            return "active"
        if s == "inactive":
            return "frozen"
        if s == "canceled":
            return "closed"
        return s or "unknown"

    def _to_issued_card(self, data: dict[str, Any]) -> IssuedCard:
        controls = data.get("spending_controls") or {}
        limits = controls.get("spending_limits") or []
        spend_limit_minor = None
        if limits and isinstance(limits, list):
            first = limits[0] or {}
            amt = first.get("amount")
            if amt is not None:
                spend_limit_minor = int(amt)  # Stripe amounts are cents.
        return IssuedCard(
            card_id=str(data.get("id") or ""),
            status=self._normalize_status(data.get("status")),
            last_four=str(data["last4"]) if data.get("last4") is not None else None,
            expiration_month=(
                str(data["exp_month"]) if data.get("exp_month") is not None else None
            ),
            expiration_year=str(data["exp_year"]) if data.get("exp_year") is not None else None,
            spend_limit_minor=spend_limit_minor,
            currency=str(data.get("currency", "usd")).upper(),
            raw=data,
        )

    @staticmethod
    def _limit_form(
        amount_minor: int, interval: str, prefix: str = "spending_controls"
    ) -> dict[str, Any]:
        return {
            f"{prefix}[spending_limits][0][amount]": amount_minor,
            f"{prefix}[spending_limits][0][interval]": interval,
        }

    async def issue_card(
        self,
        *,
        cardholder: str,
        spend_limit_minor: int | None = None,
        currency: str = "usd",
        interval: str = "monthly",
    ) -> IssuedCard:
        amount_minor = _require_int_minor(spend_limit_minor)
        form: dict[str, Any] = {
            "cardholder": cardholder,
            "currency": currency.lower(),
            "type": "virtual",
            "status": "active",
        }
        if amount_minor is not None:
            form.update(self._limit_form(amount_minor, interval))
        client = await self._client_()
        resp = await client.post("/issuing/cards", data=form)
        resp.raise_for_status()
        return self._to_issued_card(resp.json())

    async def set_status(self, *, card_id: str, state_verb: str) -> IssuedCard:
        status = self._STATUS_MAP.get(state_verb)
        if status is None:
            raise ValueError(f"unknown card state verb {state_verb!r}")
        client = await self._client_()
        resp = await client.post(f"/issuing/cards/{card_id}", data={"status": status})
        resp.raise_for_status()
        return self._to_issued_card(resp.json())

    async def set_limit(
        self, *, card_id: str, spend_limit_minor: int, interval: str = "monthly"
    ) -> IssuedCard:
        amount_minor = _require_int_minor(spend_limit_minor)
        assert amount_minor is not None  # set_limit always has a limit
        client = await self._client_()
        resp = await client.post(
            f"/issuing/cards/{card_id}", data=self._limit_form(amount_minor, interval)
        )
        resp.raise_for_status()
        return self._to_issued_card(resp.json())
