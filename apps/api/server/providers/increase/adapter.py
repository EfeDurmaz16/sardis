"""Port adapters over :class:`IncreaseClient`.

Two adapters:

* :class:`IncreaseFiatAccountAdapter` — :class:`FiatAccountPort`.  Creates
  customer-titled named accounts and pays out over ACH / Wire / RTP.
* :class:`IncreaseOfframpAdapter` — :class:`OfframpPort` (the bank leg of a
  crypto->fiat offramp): the crypto burn/settlement happens upstream; this
  pushes USD to the destination bank account once the orchestrator has
  authorized the payout.

Custody: **partner-custodied** — Increase's partner bank holds the USD while a
rail settles.  Neither adapter authorizes money; the moat already did.

The ``destination_ref`` / ``destination_bank_ref`` strings the orchestrator
passes are opaque ``routing_number:account_number[:name]`` descriptors that the
moat already authorized; the adapter only normalizes + executes.
"""

from __future__ import annotations

from typing import Any

from ..ports.types import (
    CustodyModel,
    MinorUnits,
    NormalizedTxn,
    ProviderCapability,
    ProviderError,
    ProviderResult,
)
from .client import IncreaseClient


def _parse_bank_ref(ref: str) -> tuple[str, str, str]:
    """Split ``routing_number:account_number[:name]`` into its parts.

    The orchestrator authorized this destination; we only normalize the
    opaque descriptor into the fields Increase's rails require.
    """
    parts = ref.split(":")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(
            "increase destination_ref must be 'routing_number:account_number[:name]'"
        )
    routing, account = parts[0], parts[1]
    name = parts[2] if len(parts) > 2 and parts[2] else "Sardis Payout"
    return routing, account, name


def _require_minor(amount_minor: MinorUnits, *, provider: str, capability: ProviderCapability) -> None:
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
        raise ProviderError(
            "amount_minor must be integer minor units (USD cents)",
            provider=provider,
            capability=capability,
        )


class IncreaseFiatAccountAdapter:
    """:class:`FiatAccountPort` over Increase named accounts + bank rails."""

    capability = ProviderCapability.FIAT_ACCOUNT

    def __init__(self, client: IncreaseClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "increase"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    async def create_account(
        self,
        *,
        owner_ref: str,
        currency: str = "USD",
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        if currency.upper() != "USD":
            raise ProviderError(
                f"increase accounts are USD-only, got {currency!r}",
                provider=self.provider,
                capability=self.capability,
            )
        name = (metadata or {}).get("name") or owner_ref
        try:
            account = await self._client.create_account(
                name=name, idempotency_key=(metadata or {}).get("idempotency_key")
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"increase_create_account_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=account.id,
            status=account.status,
            raw=account.raw,
        )

    async def get_balance(self, account_ref: str) -> tuple[MinorUnits, str]:
        try:
            account = await self._client.get_account(account_ref)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"increase_get_balance_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        # Increase balances are integer cents; absent until the balance surface
        # is populated, in which case we report 0 rather than a float.
        return (account.available_minor or 0, account.currency)

    async def create_payout(
        self,
        *,
        account_ref: str,
        destination_ref: str,
        amount_minor: MinorUnits,
        currency: str = "USD",
        method: str = "ACH_NEXT_DAY",
        idempotency_key: str | None = None,
        memo: str | None = None,
    ) -> NormalizedTxn:
        _require_minor(amount_minor, provider=self.provider, capability=self.capability)
        routing, account_number, name = _parse_bank_ref(destination_ref)
        descriptor = (memo or "Sardis")[:10]
        rail = (method or "").upper()
        try:
            if rail in {"WIRE", "FEDWIRE"}:
                transfer = await self._client.create_wire_transfer(
                    account_id=account_ref,
                    account_number=account_number,
                    routing_number=routing,
                    amount_minor=amount_minor,
                    creditor_name=name,
                    message=memo or "Sardis payout",
                    idempotency_key=idempotency_key,
                )
            elif rail in {"RTP", "REAL_TIME_PAYMENTS"}:
                transfer = await self._client.create_rtp_transfer(
                    source_account_number_id=account_ref,
                    account_number=account_number,
                    routing_number=routing,
                    amount_minor=amount_minor,
                    creditor_name=name,
                    remittance=memo or "Sardis payout",
                    idempotency_key=idempotency_key,
                )
            else:
                transfer = await self._client.create_ach_transfer(
                    account_id=account_ref,
                    account_number=account_number,
                    routing_number=routing,
                    amount_minor=amount_minor,
                    statement_descriptor=descriptor,
                    idempotency_key=idempotency_key,
                )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"increase_create_payout_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return NormalizedTxn(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            reference=transfer.id,
            status=transfer.status,
            amount_minor=transfer.amount_minor,
            currency=transfer.currency or currency,
            sandbox=self.sandbox,
            source=account_ref,
            destination=destination_ref,
            raw={"rail": transfer.rail, **transfer.raw},
        )

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> bool:
        return self._client.verify_webhook(body=body, headers=headers)


class IncreaseOfframpAdapter:
    """:class:`OfframpPort` over Increase — the bank leg of crypto->fiat.

    The crypto burn/settlement is handled upstream (CCTP / a custody partner);
    this adapter only pushes the resulting USD to the destination bank account
    over the requested rail.  ``source_account_id`` must be supplied via
    ``metadata['source_account_id']`` (the Increase account holding the USD).
    """

    capability = ProviderCapability.OFFRAMP

    def __init__(self, client: IncreaseClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "increase"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    async def create_payout(
        self,
        *,
        source_chain: str,
        source_token: str,
        amount_minor: MinorUnits,
        destination_bank_ref: str,
        fiat_currency: str = "USD",
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> NormalizedTxn:
        _require_minor(amount_minor, provider=self.provider, capability=self.capability)
        if fiat_currency.upper() != "USD":
            raise ProviderError(
                f"increase offramp is USD-only, got {fiat_currency!r}",
                provider=self.provider,
                capability=self.capability,
            )
        meta = metadata or {}
        source_account_id = meta.get("source_account_id")
        if not source_account_id:
            raise ProviderError(
                "increase offramp requires metadata['source_account_id']",
                provider=self.provider,
                capability=self.capability,
            )
        routing, account_number, name = _parse_bank_ref(destination_bank_ref)
        rail = str(meta.get("method", "ACH_NEXT_DAY")).upper()
        try:
            if rail in {"WIRE", "FEDWIRE"}:
                transfer = await self._client.create_wire_transfer(
                    account_id=source_account_id,
                    account_number=account_number,
                    routing_number=routing,
                    amount_minor=amount_minor,
                    creditor_name=name,
                    message=str(meta.get("memo", "Sardis offramp")),
                    idempotency_key=idempotency_key,
                )
            elif rail in {"RTP", "REAL_TIME_PAYMENTS"}:
                transfer = await self._client.create_rtp_transfer(
                    source_account_number_id=source_account_id,
                    account_number=account_number,
                    routing_number=routing,
                    amount_minor=amount_minor,
                    creditor_name=name,
                    remittance=str(meta.get("memo", "Sardis offramp")),
                    idempotency_key=idempotency_key,
                )
            else:
                transfer = await self._client.create_ach_transfer(
                    account_id=source_account_id,
                    account_number=account_number,
                    routing_number=routing,
                    amount_minor=amount_minor,
                    statement_descriptor=str(meta.get("memo", "Sardis"))[:10],
                    idempotency_key=idempotency_key,
                )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"increase_offramp_payout_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return NormalizedTxn(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            reference=transfer.id,
            status=transfer.status,
            amount_minor=transfer.amount_minor,
            currency=fiat_currency,
            sandbox=self.sandbox,
            chain=source_chain,
            source=source_token,
            destination=destination_bank_ref,
            raw={"rail": transfer.rail, **transfer.raw},
        )

    async def get_status(self, payout_ref: str) -> ProviderResult:
        # Increase transfer status lives under the rail-specific resource; the
        # orchestrator records the rail at creation. Default to the ACH read.
        try:
            data = await self._client._get(f"/ach_transfers/{payout_ref}")
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"increase_offramp_status_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=str(data.get("id", payout_ref)),
            status=str(data.get("status", "pending")),
            raw=data,
        )
