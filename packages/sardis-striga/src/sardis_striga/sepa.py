"""Striga SEPA payout provider — EUR payouts via SEPA and SEPA Instant."""
from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal, Optional

from sardis_ramp.base import RampProvider, RampQuote, RampSession, RampStatus

from .client import StrigaClient

logger = logging.getLogger(__name__)


class StrigaSEPAProvider(RampProvider):
    """
    Striga SEPA payout provider.

    Supports:
    - SEPA Credit Transfer (EUR, 1-2 business days)
    - SEPA Instant (EUR, < 10 seconds)

    Implements RampProvider ABC for integration with RampRouter.
    """

    def __init__(
        self,
        client: StrigaClient,
        default_user_id: str = "",
        default_rail: Literal["sepa", "sepa_instant"] = "sepa",
    ):
        self._client = client
        self._default_user_id = default_user_id
        self._default_rail = default_rail

    @property
    def provider_name(self) -> str:
        return "striga_sepa"

    @property
    def supports_onramp(self) -> bool:
        return True  # SEPA incoming via vIBAN

    @property
    def supports_offramp(self) -> bool:
        return True  # SEPA outgoing payouts

    async def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        destination_currency: str,
        chain: str,
        direction: Literal["onramp", "offramp"],
    ) -> RampQuote:
        """Get quote for SEPA operation."""
        # Striga SEPA: ~0.1% fee for standard, ~0.5% for instant
        fee_bps = 10 if self._default_rail == "sepa" else 50
        fee_amount = amount * Decimal(fee_bps) / Decimal(10000)
        output_amount = amount - fee_amount

        return RampQuote(
            provider=self.provider_name,
            amount_fiat=amount if direction == "onramp" else output_amount,
            amount_crypto=output_amount if direction == "onramp" else amount,
            fiat_currency=destination_currency if direction == "offramp" else source_currency,
            crypto_currency=source_currency if direction == "offramp" else destination_currency,
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
        """Create SEPA on-ramp — receive EUR via vIBAN."""
        session_id = f"striga_sepa_in_{secrets.token_hex(8)}"

        # Striga handles SEPA incoming via vIBAN — return instructions
        return RampSession(
            session_id=session_id,
            provider=self.provider_name,
            direction="onramp",
            status=RampStatus.PENDING,
            amount_fiat=amount_fiat,
            amount_crypto=amount_fiat,  # 1:1 EUR
            fiat_currency=fiat_currency,
            crypto_currency=crypto_currency,
            chain=chain,
            destination_address=destination_address,
            payment_method="sepa_transfer",
            metadata=metadata,
            created_at=datetime.now(UTC),
        )

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
        """Create SEPA payout — send EUR via SEPA."""
        if fiat_currency.upper() != "EUR":
            raise ValueError(f"Striga SEPA only supports EUR, got {fiat_currency}")

        result = await self._client.request(
            "POST",
            "/wallets/send/sepa",
            {
                "userId": self._default_user_id,
                "walletId": wallet_id or "",
                "amount": int(amount_crypto * 100),
                "currency": "EUR",
                "iban": bank_account.get("iban", ""),
                "bic": bank_account.get("bic", ""),
                "beneficiaryName": bank_account.get("name", ""),
                "reference": bank_account.get("reference", "Sardis payout"),
                "instant": self._default_rail == "sepa_instant",
            },
        )

        return RampSession(
            session_id=result.get("transactionId", f"striga_sepa_{secrets.token_hex(8)}"),
            provider=self.provider_name,
            direction="offramp",
            status=RampStatus.PROCESSING,
            amount_fiat=amount_crypto,  # EUR 1:1
            amount_crypto=amount_crypto,
            fiat_currency="EUR",
            crypto_currency=crypto_currency,
            chain=chain,
            destination_address=bank_account.get("iban", ""),
            payment_method=self._default_rail,
            metadata=metadata,
            created_at=datetime.now(UTC),
        )

    async def get_status(self, session_id: str) -> RampSession:
        """Get SEPA transfer status."""
        result = await self._client.request("GET", f"/transactions/{session_id}")

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
            amount_fiat=Decimal(str(result.get("amount", 0))) / 100,
            amount_crypto=Decimal(str(result.get("amount", 0))) / 100,
            fiat_currency="EUR",
            crypto_currency="EUR",
            chain="",
            destination_address=result.get("destinationIban", ""),
        )

    async def handle_webhook(self, payload: bytes, headers: dict) -> dict:
        """Handle Striga SEPA webhook."""
        import json

        data = json.loads(payload)
        return {
            "event_type": data.get("type", ""),
            "transaction_id": data.get("transactionId", ""),
            "status": data.get("status", ""),
        }
