"""Bridge.xyz adapter — fiat on/off-ramp for Tempo stablecoins.

Bridge.xyz provides native Tempo support for:
- Fiat → USDC/EURC on Tempo (onramp via ACH/wire)
- USDC/EURC → fiat bank account (offramp via liquidation addresses)
- Virtual accounts with bank routing numbers

EURC on Tempo: 0x20c0000000000000000000001621e21f71cf12fb
USDC on Tempo: 0x20c000000000000000000000b9537d11c60e8b50

Reference: https://apidocs.bridge.xyz/get-started/guides/move-money/tempo-integration-guide
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.chain.bridge_xyz")

BRIDGE_API_BASE = "https://api.bridge.xyz"

# Token addresses on Tempo (from Bridge.xyz docs)
TEMPO_TOKENS = {
    "USDC": "0x20c000000000000000000000b9537d11c60e8b50",
    "EURC": "0x20c0000000000000000000001621e21f71cf12fb",
}


@dataclass
class LiquidationAddress:
    """Auto-convert address: stablecoin deposit → fiat settlement."""
    address_id: str = ""
    chain: str = "tempo"
    token: str = "EURC"
    deposit_address: str = ""
    destination_currency: str = "eur"
    destination_payment_rail: str = "wire"
    external_account_id: str = ""
    status: str = "active"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class OfframpTransfer:
    """A fiat off-ramp transfer."""
    transfer_id: str = ""
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    source_currency: str = "EURC"
    destination_currency: str = "eur"
    payment_rail: str = "wire"
    status: str = "pending"
    fee: Decimal = field(default_factory=lambda: Decimal("0"))
    receipt: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class BridgeXYZAdapter:
    """Bridge.xyz adapter for Tempo fiat on/off-ramp.

    Provides liquidation addresses (auto-convert stablecoin → fiat)
    and direct transfers (wallet → bank account).
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = BRIDGE_API_BASE,
    ) -> None:
        self._api_key = api_key or os.getenv("BRIDGE_API_KEY", "")
        self._base_url = base_url

    def _headers(self) -> dict[str, str]:
        return {
            "Api-Key": self._api_key,
            "Content-Type": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def create_liquidation_address(
        self,
        customer_id: str,
        token: str = "EURC",
        destination_currency: str = "eur",
        payment_rail: str = "wire",
        external_account_id: str = "",
        developer_fee_percent: Decimal = Decimal("0"),
    ) -> LiquidationAddress:
        """Create a liquidation address for auto fiat conversion.

        When stablecoins are deposited to this address, they are
        automatically converted to fiat and settled to the linked
        bank account.

        Args:
            customer_id: Bridge customer ID.
            token: EURC or USDC.
            destination_currency: Target fiat (eur, usd, etc.).
            payment_rail: Settlement rail (wire, ach, sepa).
            external_account_id: Linked bank account ID.
            developer_fee_percent: Optional fee percentage.
        """
        import httpx

        if not self._api_key:
            raise ValueError("BRIDGE_API_KEY not set")

        token_address = TEMPO_TOKENS.get(token.upper(), "")
        if not token_address:
            raise ValueError(f"Unknown token: {token}")

        idempotency_key = uuid4().hex

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base_url}/v0/customers/{customer_id}/liquidation_addresses",
                headers={**self._headers(), "Idempotency-Key": idempotency_key},
                json={
                    "chain": "tempo",
                    "currency": token.lower(),
                    "destination_payment_rail": payment_rail,
                    "destination_currency": destination_currency,
                    "external_account_id": external_account_id,
                    **({"developer_fee_percent": str(developer_fee_percent)} if developer_fee_percent else {}),
                },
            )
            resp.raise_for_status()
            data = resp.json()

        result = LiquidationAddress(
            address_id=data.get("id", ""),
            chain="tempo",
            token=token,
            deposit_address=data.get("address", ""),
            destination_currency=destination_currency,
            destination_payment_rail=payment_rail,
            external_account_id=external_account_id,
        )

        logger.info(
            "Bridge.xyz liquidation address created: %s (%s → %s via %s)",
            result.deposit_address, token, destination_currency, payment_rail,
        )
        return result

    async def create_offramp_transfer(
        self,
        customer_id: str,
        amount: Decimal,
        source_currency: str = "eurc",
        destination_currency: str = "eur",
        payment_rail: str = "wire",
        external_account_id: str = "",
        source_wallet_id: str = "",
    ) -> OfframpTransfer:
        """Initiate a fiat off-ramp transfer from Tempo wallet to bank.

        Args:
            customer_id: Bridge customer ID.
            amount: Amount in source currency.
            source_currency: Stablecoin (eurc, usdc).
            destination_currency: Fiat (eur, usd).
            payment_rail: Settlement method (wire, ach, sepa).
            external_account_id: Destination bank account ID.
            source_wallet_id: Bridge wallet ID holding the stablecoins.
        """
        import httpx

        if not self._api_key:
            raise ValueError("BRIDGE_API_KEY not set")

        idempotency_key = uuid4().hex

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base_url}/v0/transfers",
                headers={**self._headers(), "Idempotency-Key": idempotency_key},
                json={
                    "amount": str(amount),
                    "on_behalf_of": customer_id,
                    "source": {
                        "payment_rail": "tempo",
                        "currency": source_currency,
                        **({"from_address": source_wallet_id} if source_wallet_id else {}),
                    },
                    "destination": {
                        "payment_rail": payment_rail,
                        "currency": destination_currency,
                        "external_account_id": external_account_id,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()

        result = OfframpTransfer(
            transfer_id=data.get("id", ""),
            amount=amount,
            source_currency=source_currency,
            destination_currency=destination_currency,
            payment_rail=payment_rail,
            status=data.get("state", "pending"),
            fee=Decimal(str(data.get("receipt", {}).get("developer_fee", "0"))),
            receipt=data.get("receipt", {}),
        )

        logger.info(
            "Bridge.xyz offramp transfer: %s %s → %s %s (status=%s)",
            amount, source_currency, destination_currency, payment_rail, result.status,
        )
        return result

    async def create_customer(self, email: str, name: str = "") -> str:
        """Create a Bridge.xyz customer. Returns customer_id."""
        import httpx

        if not self._api_key:
            raise ValueError("BRIDGE_API_KEY not set")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base_url}/v0/customers",
                headers=self._headers(),
                json={"email": email, **({"full_name": name} if name else {})},
            )
            resp.raise_for_status()
            return resp.json().get("id", "")
