"""Lightspark Grid payout provider — ACH, RTP, FedNow, Wire."""
from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal, Optional

from sardis_ramp.base import RampProvider, RampQuote, RampSession, RampStatus

from .client import GridClient
from .models import GridPaymentRail

logger = logging.getLogger(__name__)


class GridPayoutProvider(RampProvider):
    """
    Lightspark Grid payout provider.

    Supports:
    - ACH (1-3 business days)
    - ACH Same Day
    - RTP (Real-Time Payments, < 10 seconds)
    - FedNow (< 10 seconds)
    - Wire (same/next day)

    Implements RampProvider ABC for integration with RampRouter.
    """

    # Fee schedule by rail (in basis points)
    RAIL_FEES_BPS = {
        GridPaymentRail.ACH: 25,           # 0.25%
        GridPaymentRail.ACH_SAME_DAY: 50,  # 0.50%
        GridPaymentRail.RTP: 75,           # 0.75%
        GridPaymentRail.FEDNOW: 75,        # 0.75%
        GridPaymentRail.WIRE: 100,         # 1.00% (+ flat fee typically)
    }

    def __init__(
        self,
        client: GridClient,
        default_rail: GridPaymentRail = GridPaymentRail.ACH,
    ):
        self._client = client
        self._default_rail = default_rail

    @property
    def provider_name(self) -> str:
        return "lightspark_grid"

    @property
    def supports_onramp(self) -> bool:
        return False  # Grid is payout-focused; on-ramp via Plaid + ACH pull

    @property
    def supports_offramp(self) -> bool:
        return True

    async def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        destination_currency: str,
        chain: str,
        direction: Literal["onramp", "offramp"],
    ) -> RampQuote:
        """Get quote for a Grid payout."""
        if direction == "onramp":
            raise ValueError("Grid does not support on-ramp directly")

        fee_bps = self.RAIL_FEES_BPS.get(self._default_rail, 50)
        fee_amount = amount * Decimal(fee_bps) / Decimal(10000)
        output_amount = amount - fee_amount

        return RampQuote(
            provider=self.provider_name,
            amount_fiat=output_amount,
            amount_crypto=amount,
            fiat_currency=destination_currency,
            crypto_currency=source_currency,
            chain=chain,
            fee_amount=fee_amount,
            fee_percent=Decimal(fee_bps) / Decimal(100),
            exchange_rate=Decimal("1.0"),
            expires_at=datetime.now(UTC),
        )

    async def create_onramp(
        self,
        amount_fiat: Decimal,
        fiat_currency: str,
        crypto_currency: str,
        chain: str,
        destination_address: str,
        wallet_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> RampSession:
        """Not supported — Grid is payout-focused."""
        raise NotImplementedError("Grid does not support on-ramp directly")

    async def create_offramp(
        self,
        amount_crypto: Decimal,
        crypto_currency: str,
        chain: str,
        fiat_currency: str,
        bank_account: dict,
        wallet_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> RampSession:
        """Create a payout via Grid (ACH/RTP/FedNow/Wire)."""
        rail = bank_account.get("rail", self._default_rail.value)
        if isinstance(rail, str):
            rail_enum = GridPaymentRail(rail) if rail in [r.value for r in GridPaymentRail] else self._default_rail
        else:
            rail_enum = rail

        result = await self._client.request(
            "POST",
            "/transfers",
            {
                "amount": int(amount_crypto * 100),
                "currency": fiat_currency.upper(),
                "rail": rail_enum.value,
                "destination": bank_account.get("account_id", bank_account.get("plaid_account_id", "")),
                "reference": bank_account.get("reference", "Sardis payout"),
            },
        )

        return RampSession(
            session_id=result.get("transferId", f"grid_{secrets.token_hex(8)}"),
            provider=self.provider_name,
            direction="offramp",
            status=RampStatus.PROCESSING,
            amount_fiat=amount_crypto,
            amount_crypto=amount_crypto,
            fiat_currency=fiat_currency.upper(),
            crypto_currency=crypto_currency,
            chain=chain,
            destination_address=bank_account.get("account_id", ""),
            payment_method=rail_enum.value,
            metadata=metadata,
            created_at=datetime.now(UTC),
        )

    async def get_status(self, session_id: str) -> RampSession:
        """Get Grid payout status."""
        result = await self._client.request("GET", f"/transfers/{session_id}")

        status_map = {
            "pending": RampStatus.PENDING,
            "processing": RampStatus.PROCESSING,
            "completed": RampStatus.COMPLETED,
            "failed": RampStatus.FAILED,
        }

        return RampSession(
            session_id=session_id,
            provider=self.provider_name,
            direction="offramp",
            status=status_map.get(result.get("status", "pending"), RampStatus.PENDING),
            amount_fiat=Decimal(str(result.get("targetAmount", 0))) / 100,
            amount_crypto=Decimal(str(result.get("sourceAmount", 0))) / 100,
            fiat_currency=result.get("targetCurrency", "USD"),
            crypto_currency=result.get("sourceCurrency", "USD"),
            chain="",
            destination_address=result.get("destination", ""),
            payment_method=result.get("rail", "ach"),
        )

    async def handle_webhook(self, payload: bytes, headers: dict) -> dict:
        """Handle Grid payout webhook."""
        import json

        data = json.loads(payload)
        return {
            "event_type": data.get("type", ""),
            "transfer_id": data.get("transferId", ""),
            "status": data.get("status", ""),
        }
