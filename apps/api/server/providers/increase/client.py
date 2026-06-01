"""Thin HTTP client for the Increase banking API.

Researched against the current (2026) Increase API via context7
(``/websites/increase``) and https://increase.com/documentation/api:

* **Auth:** Bearer token — ``Authorization: Bearer <api_key>``.
* **Base URLs:** sandbox ``https://sandbox.increase.com``; production
  ``https://api.increase.com``.  Sandbox keys are prefixed ``sandbox_key_…``,
  production keys ``secret_key_…``.
* **Idempotency:** ``Idempotency-Key`` request header on POSTs.
* **Money:** all amounts are **integer USD cents** (e.g. ``"amount": 100``).
* **Endpoints used here:**
  ``POST /accounts``                         (create a named account)
  ``GET  /accounts/{id}``                    (read account; balances inline)
  ``POST /account_numbers``                  (inbound ACH/Wire routing+account no.)
  ``POST /ach_transfers``                    (outbound ACH)
  ``POST /wire_transfers``                   (outbound Fedwire)
  ``POST /real_time_payments_transfers``     (outbound RTP)
* **Webhooks:** Standard Webhooks spec (``webhook-id`` / ``webhook-timestamp``
  / ``webhook-signature: v1,<base64 hmac-sha256>``); signing secret is
  ``whsec_…``-prefixed base64 — identical to the scheme the Lithic client
  already implements, so the verifier here is intentionally the same shape.

This client only *executes* an instruction the orchestrator already authorized.
It performs no policy / KYA / sanctions / mandate checks — those live in the
authority core.  No secret is hardcoded; credentials arrive via the registry
from the environment.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_SANDBOX_BASE = "https://sandbox.increase.com"
_PRODUCTION_BASE = "https://api.increase.com"

# Reject Standard-Webhooks deliveries whose timestamp drifts more than this many
# seconds from now (replay window), matching Increase's recommendation.
_WEBHOOK_TOLERANCE_SECONDS = 5 * 60


@dataclass(frozen=True)
class IncreaseConfig:
    """Resolved Increase credentials/runtime.  Never logged."""

    api_key: str
    environment: str = "sandbox"
    webhook_secret: str | None = None
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
class IncreaseAccount:
    """Normalized Increase account (named, customer-titled)."""

    id: str
    status: str
    currency: str
    #: Available balance in integer minor units (USD cents), when returned.
    available_minor: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class IncreaseTransfer:
    """Normalized Increase transfer across ACH / Wire / RTP."""

    id: str
    status: str
    amount_minor: int
    currency: str
    rail: str
    raw: dict[str, Any] = field(default_factory=dict)


class IncreaseClient:
    """HTTP adapter for Increase accounts + transfers.

    Constructed by the :class:`ProviderRegistry` only when an
    ``INCREASE_API_KEY`` is present in the environment.
    """

    def __init__(self, config: IncreaseConfig) -> None:
        if not config.api_key:
            raise ValueError("Increase API key is required")
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
                    "Authorization": f"Bearer {self._config.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _post(
        self, path: str, json: dict[str, Any], *, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        client = await self._client_()
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        resp = await client.post(path, json=json, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _get(self, path: str) -> dict[str, Any]:
        client = await self._client_()
        resp = await client.get(path)
        resp.raise_for_status()
        return resp.json()

    # -- Accounts ------------------------------------------------------------

    async def create_account(
        self, *, name: str, idempotency_key: str | None = None
    ) -> IncreaseAccount:
        """``POST /accounts`` — Increase accounts are named + customer-titled."""
        data = await self._post(
            "/accounts", {"name": name}, idempotency_key=idempotency_key
        )
        return self._account_from(data)

    async def get_account(self, account_id: str) -> IncreaseAccount:
        data = await self._get(f"/accounts/{account_id}")
        return self._account_from(data)

    async def create_account_number(
        self, *, account_id: str, name: str
    ) -> dict[str, Any]:
        """``POST /account_numbers`` — inbound routing+account number on an account."""
        return await self._post(
            "/account_numbers", {"account_id": account_id, "name": name}
        )

    @staticmethod
    def _account_from(data: dict[str, Any]) -> IncreaseAccount:
        # Increase returns balances as integer cents; field is nested when
        # present (``balances.available_balance`` on the balance endpoint, or
        # absent on the bare account object).
        balances = data.get("balances") or {}
        available = balances.get("available_balance")
        return IncreaseAccount(
            id=str(data.get("id", "")),
            status=str(data.get("status", "unknown")),
            currency=str(data.get("currency", "USD")),
            available_minor=int(available) if isinstance(available, int) else None,
            raw=data,
        )

    # -- Transfers (already-authorized; orchestrator decided) ---------------

    async def create_ach_transfer(
        self,
        *,
        account_id: str,
        account_number: str,
        routing_number: str,
        amount_minor: int,
        statement_descriptor: str,
        idempotency_key: str | None = None,
    ) -> IncreaseTransfer:
        data = await self._post(
            "/ach_transfers",
            {
                "account_id": account_id,
                "account_number": account_number,
                "routing_number": routing_number,
                "amount": amount_minor,
                "statement_descriptor": statement_descriptor,
            },
            idempotency_key=idempotency_key,
        )
        return self._transfer_from(data, rail="ach", amount_minor=amount_minor)

    async def create_wire_transfer(
        self,
        *,
        account_id: str,
        account_number: str,
        routing_number: str,
        amount_minor: int,
        creditor_name: str,
        message: str,
        idempotency_key: str | None = None,
    ) -> IncreaseTransfer:
        data = await self._post(
            "/wire_transfers",
            {
                "account_id": account_id,
                "account_number": account_number,
                "routing_number": routing_number,
                "amount": amount_minor,
                "creditor": {"name": creditor_name},
                "remittance": {
                    "category": "unstructured",
                    "unstructured": {"message": message},
                },
            },
            idempotency_key=idempotency_key,
        )
        return self._transfer_from(data, rail="wire", amount_minor=amount_minor)

    async def create_rtp_transfer(
        self,
        *,
        source_account_number_id: str,
        account_number: str,
        routing_number: str,
        amount_minor: int,
        creditor_name: str,
        remittance: str,
        idempotency_key: str | None = None,
    ) -> IncreaseTransfer:
        data = await self._post(
            "/real_time_payments_transfers",
            {
                "source_account_number_id": source_account_number_id,
                "account_number": account_number,
                "routing_number": routing_number,
                "amount": amount_minor,
                "creditor_name": creditor_name,
                "unstructured_remittance_information": remittance,
            },
            idempotency_key=idempotency_key,
        )
        return self._transfer_from(data, rail="rtp", amount_minor=amount_minor)

    @staticmethod
    def _transfer_from(
        data: dict[str, Any], *, rail: str, amount_minor: int
    ) -> IncreaseTransfer:
        amt = data.get("amount")
        return IncreaseTransfer(
            id=str(data.get("id", "")),
            status=str(data.get("status", "pending")),
            amount_minor=int(amt) if isinstance(amt, int) else amount_minor,
            currency=str(data.get("currency", "USD")),
            rail=rail,
            raw=data,
        )

    # -- Webhooks (Standard Webhooks / Svix scheme) -------------------------

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> bool:
        """Verify a Standard-Webhooks signature.  Fail-closed (return False).

        Signed content is ``f"{id}.{timestamp}.{body}"``; the key is the
        base64 decode of the ``whsec_``-prefixed secret; the signature header
        carries one or more space-separated ``v1,<base64>`` tags.
        """
        secret = self._config.webhook_secret
        if not secret:
            return False
        lower = {k.lower(): v for k, v in headers.items()}
        webhook_id = lower.get("webhook-id") or lower.get("svix-id")
        timestamp = lower.get("webhook-timestamp") or lower.get("svix-timestamp")
        sig_header = lower.get("webhook-signature") or lower.get("svix-signature")
        if not (webhook_id and timestamp and sig_header):
            return False
        try:
            ts_int = int(timestamp)
        except (TypeError, ValueError):
            return False
        import time as _time

        if abs(_time.time() - ts_int) > _WEBHOOK_TOLERANCE_SECONDS:
            return False
        key = self._decode_secret(secret)
        if key is None:
            return False
        signed = b"%s.%s.%s" % (webhook_id.encode(), timestamp.encode(), body)
        expected = base64.b64encode(
            hmac.new(key, signed, hashlib.sha256).digest()
        ).decode()
        for tag in sig_header.split():
            version, _, value = tag.partition(",")
            if version == "v1" and hmac.compare_digest(value, expected):
                return True
        return False

    @staticmethod
    def _decode_secret(secret: str) -> bytes | None:
        if secret.startswith("whsec_"):
            secret = secret[len("whsec_") :]
        try:
            return base64.b64decode(secret)
        except Exception:  # noqa: BLE001 - malformed secret fails closed
            return None
