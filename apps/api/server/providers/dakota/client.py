"""Thin HTTP client for the Dakota stablecoin/banking API.

Researched against the current (2026) Dakota API via the published docs
(https://docs.dakota.xyz, https://docs.dakota.xyz/llms.txt and
https://docs.dakota.xyz/documentation/webhooks.md):

* **Auth:** ``x-api-key: <api_key>`` header (key created in the dashboard).
* **Base URLs:** sandbox ``https://api.platform.sandbox.dakota.xyz``;
  production ``https://api.platform.dakota.xyz``.
* **SDKs exist** (``@dakota-xyz/ts-sdk``, ``github.com/dakota-xyz/go-sdk``) but
  there is no first-party Python SDK, so per the minimal-dependency rule we
  call the REST API directly over httpx.
* **Endpoints used here:**
  ``POST /customers``                       (create a customer)
  ``POST /accounts``                        (create an onramp/offramp/swap account)
  ``GET  /accounts/{id}``                   (read account; includes deposit
                                             instructions for inbound fiat that
                                             auto-settles to USDC)
  ``POST /wallets``                         (create a wallet under a customer)
  ``GET  /wallets/{id}/balances``           (balances grouped by asset+network)
  ``POST /recipients``                      (create a payout recipient)
  ``POST /recipients/{id}/destinations``    (crypto / fiat_us / fiat_iban dest.)
  ``POST /transactions/transfers``          (one-off transfer: offramp to bank
                                             via ACH/Fedwire/SWIFT, or swap to
                                             crypto)
  ``GET  /info/networks``                   (supported blockchain networks)
* **Money:** Dakota's REST surface takes a decimal-string ``amount`` + ``asset``
  (e.g. ``"USDC"``) and ``network`` (e.g. ``"base"``, ``"solana"``).  We convert
  between integer minor units and that decimal string with ``Decimal`` only —
  never ``float``.
* **Webhooks:** **Ed25519** signatures (NOT HMAC).  Headers
  ``X-Webhook-Signature`` (base64 Ed25519 sig over ``timestamp + body``),
  ``X-Webhook-Timestamp`` (reject if >5 min old), ``X-Dakota-Event-ID``.  The
  verifying public key is environment-specific and supplied via env, never
  hardcoded.

This client only *executes* an already-authorized instruction; it performs no
policy / KYA / sanctions / mandate checks (those live in the moat).  No secret
is hardcoded; credentials arrive via the registry from the environment.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx

from ..ports.types import from_minor_units

logger = logging.getLogger(__name__)

_SANDBOX_BASE = "https://api.platform.sandbox.dakota.xyz"
_PRODUCTION_BASE = "https://api.platform.dakota.xyz"

_WEBHOOK_TOLERANCE_SECONDS = 5 * 60

#: USDC carries 6 decimals on every chain Dakota settles to.
USDC_DECIMALS = 6


@dataclass(frozen=True)
class DakotaConfig:
    """Resolved Dakota credentials/runtime.  Never logged."""

    api_key: str
    environment: str = "sandbox"
    #: Hex-encoded Ed25519 public key Dakota signs webhooks with (per env).
    webhook_public_key_hex: str | None = None
    timeout_seconds: float = 20.0

    @property
    def is_sandbox(self) -> bool:
        return self.environment.strip().lower() in {
            "sandbox",
            "test",
            "development",
            "dev",
        }


@dataclass
class DakotaAccount:
    id: str
    status: str
    customer_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class DakotaTransfer:
    id: str
    status: str
    amount_minor: int
    asset: str
    raw: dict[str, Any] = field(default_factory=dict)


class DakotaClient:
    """HTTP adapter for Dakota customers, accounts, balances and transfers."""

    def __init__(self, config: DakotaConfig) -> None:
        if not config.api_key:
            raise ValueError("Dakota API key is required")
        self._config = config
        self._base_url = _SANDBOX_BASE if config.is_sandbox else _PRODUCTION_BASE
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._config.timeout_seconds,
                headers={
                    "x-api-key": self._config.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        client = await self._client_()
        resp = await client.post(path, json=json)
        resp.raise_for_status()
        return resp.json()

    async def _get(self, path: str) -> dict[str, Any]:
        client = await self._client_()
        resp = await client.get(path)
        resp.raise_for_status()
        return resp.json()

    # -- Customers + accounts ----------------------------------------------

    async def create_account(
        self, *, name: str, account_type: str = "onramp", customer_id: str | None = None
    ) -> DakotaAccount:
        """``POST /accounts`` — named onramp/offramp/swap account.

        Inbound fiat to this account auto-settles to USDC; the deposit
        instructions are returned on ``GET /accounts/{id}``.
        """
        payload: dict[str, Any] = {"name": name, "type": account_type}
        if customer_id:
            payload["customer_id"] = customer_id
        data = await self._post("/accounts", payload)
        return self._account_from(data)

    async def get_account(self, account_id: str) -> DakotaAccount:
        data = await self._get(f"/accounts/{account_id}")
        return self._account_from(data)

    @staticmethod
    def _account_from(data: dict[str, Any]) -> DakotaAccount:
        return DakotaAccount(
            id=str(data.get("id", "")),
            status=str(data.get("status", "unknown")),
            customer_id=(str(data["customer_id"]) if data.get("customer_id") else None),
            raw=data,
        )

    # -- Balances -----------------------------------------------------------

    async def get_wallet_balances(self, wallet_id: str) -> dict[str, Any]:
        """``GET /wallets/{id}/balances`` — balances grouped by asset+network."""
        return await self._get(f"/wallets/{wallet_id}/balances")

    @staticmethod
    def usdc_minor_from_balances(
        balances: dict[str, Any], *, network: str | None = None
    ) -> int:
        """Sum USDC balances (as integer 6-decimal minor units) from a response.

        Accepts the documented shape ``{"balances": [{"asset","network",
        "amount"}, ...]}`` where ``amount`` is a decimal string.  Never uses
        ``float``: each amount is parsed with ``Decimal`` and scaled exactly.
        """
        rows = balances.get("balances", balances.get("data", []))
        total = Decimal(0)
        for row in rows or []:
            if str(row.get("asset", "")).upper() != "USDC":
                continue
            if network and str(row.get("network", "")).lower() != network.lower():
                continue
            amount = row.get("amount", "0")
            total += amount if isinstance(amount, Decimal) else Decimal(str(amount))
        scaled = total * (Decimal(10) ** USDC_DECIMALS)
        if scaled != scaled.to_integral_value():
            raise ValueError("USDC balance has more precision than 6 decimals allow")
        return int(scaled)

    # -- Transfers (already-authorized) ------------------------------------

    async def create_transfer(
        self,
        *,
        source_account_id: str,
        destination_id: str,
        amount_minor: int,
        asset: str = "USDC",
        idempotency_key: str | None = None,
    ) -> DakotaTransfer:
        """``POST /transactions/transfers`` — one-off transfer.

        ``destination_id`` is a recipient destination the orchestrator already
        created/authorized (a bank for offramp, or a crypto address).  Amount
        crosses to Dakota as a decimal string built exactly from minor units.
        """
        amount_str = format(from_minor_units(amount_minor, USDC_DECIMALS), "f")
        payload: dict[str, Any] = {
            "source": {"account_id": source_account_id},
            "destination": {"id": destination_id},
            "amount": amount_str,
            "asset": asset.upper(),
        }
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        data = await self._post("/transactions/transfers", payload)
        return self._transfer_from(data, amount_minor=amount_minor, asset=asset)

    @staticmethod
    def _transfer_from(
        data: dict[str, Any], *, amount_minor: int, asset: str
    ) -> DakotaTransfer:
        return DakotaTransfer(
            id=str(data.get("id", "")),
            status=str(data.get("status", "processing")),
            amount_minor=amount_minor,
            asset=str(data.get("asset", asset)).upper(),
            raw=data,
        )

    # -- Webhooks (Ed25519) -------------------------------------------------

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> bool:
        """Verify a Dakota Ed25519 webhook signature.  Fail-closed.

        Signed content is ``timestamp + body`` (timestamp string concatenated
        with the raw body bytes).  The signature header is base64-encoded; the
        public key is the env-supplied hex key for this environment.
        """
        public_key_hex = self._config.webhook_public_key_hex
        if not public_key_hex:
            return False
        lower = {k.lower(): v for k, v in headers.items()}
        signature_b64 = lower.get("x-webhook-signature")
        timestamp = lower.get("x-webhook-timestamp")
        if not (signature_b64 and timestamp):
            return False
        try:
            ts_int = int(timestamp)
        except (TypeError, ValueError):
            return False
        if abs(time.time() - ts_int) > _WEBHOOK_TOLERANCE_SECONDS:
            return False
        try:
            import base64

            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PublicKey,
            )

            public_key = Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(public_key_hex)
            )
            signature = base64.b64decode(signature_b64)
            signed = timestamp.encode() + body
            public_key.verify(signature, signed)
            return True
        except (InvalidSignature, ValueError):
            return False
        except Exception:  # noqa: BLE001 - any crypto/parse error fails closed
            return False
