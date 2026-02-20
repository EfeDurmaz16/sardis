"""Bridge provider wrapper - implements RampProvider interface."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal, Optional

from ..base import RampProvider, RampQuote, RampSession, RampStatus
from ..ramp import SardisFiatRamp
from ..ramp_types import BankAccount

logger = logging.getLogger(__name__)


class BridgeProvider(RampProvider):
    """
    Bridge.xyz ramp provider.

    Supports both on-ramp and off-ramp via Bridge's fiat-to-crypto infrastructure.
    Wraps the existing SardisFiatRamp implementation.
    """

    def __init__(
        self,
        sardis_api_key: Optional[str] = None,
        bridge_api_key: Optional[str] = None,
        environment: Literal["sandbox", "production"] = "sandbox",
    ):
        """
        Initialize Bridge provider.

        Args:
            sardis_api_key: Sardis API key
            bridge_api_key: Bridge API key
            environment: "sandbox" or "production"
        """
        self._ramp = SardisFiatRamp(
            sardis_api_key=sardis_api_key,
            bridge_api_key=bridge_api_key,
            environment=environment,
        )
        self._environment = environment

    @property
    def provider_name(self) -> str:
        return "bridge"

    @property
    def supports_onramp(self) -> bool:
        return True

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
        """
        Get a quote from Bridge.

        Note: Bridge doesn't have a direct quote endpoint, so we estimate based on
        their fee structure (typically 0.5-1% for on-ramp, 1% for off-ramp).
        """
        # Bridge typical fees
        fee_percent = Decimal("0.8") if direction == "onramp" else Decimal("1.0")
        fee_amount = amount * (fee_percent / 100)

        if direction == "onramp":
            # Fiat → Crypto
            amount_crypto = amount - fee_amount
            return RampQuote(
                provider="bridge",
                amount_fiat=amount,
                amount_crypto=amount_crypto,
                fiat_currency=source_currency.upper(),
                crypto_currency=destination_currency.upper(),
                chain=chain,
                fee_amount=fee_amount,
                fee_percent=fee_percent,
                exchange_rate=Decimal("1.0"),  # Assuming 1:1 for stablecoins
                expires_at=datetime.utcnow() + timedelta(minutes=15),
            )
        else:
            # Crypto → Fiat
            amount_fiat = amount - fee_amount
            return RampQuote(
                provider="bridge",
                amount_fiat=amount_fiat,
                amount_crypto=amount,
                fiat_currency=destination_currency.upper(),
                crypto_currency=source_currency.upper(),
                chain=chain,
                fee_amount=fee_amount,
                fee_percent=fee_percent,
                exchange_rate=Decimal("1.0"),
                expires_at=datetime.utcnow() + timedelta(minutes=15),
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
        """Create on-ramp session via Bridge."""
        if not wallet_id:
            raise ValueError("wallet_id required for Bridge on-ramp")

        # Use existing fund_wallet implementation
        result = await self._ramp.fund_wallet(
            wallet_id=wallet_id,
            amount_usd=float(amount_fiat),
            method="bank",
        )

        return RampSession(
            session_id=result.transfer_id or "unknown",
            provider="bridge",
            direction="onramp",
            status=RampStatus.PENDING,
            amount_fiat=amount_fiat,
            amount_crypto=amount_fiat,  # Approximate, actual will depend on fees
            fiat_currency=fiat_currency.upper(),
            crypto_currency=crypto_currency.upper(),
            chain=chain,
            destination_address=destination_address,
            payment_url=result.payment_link,
            payment_method="bank" if result.ach_instructions else "card",
            created_at=datetime.utcnow(),
            metadata=metadata or {},
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
        """Create off-ramp session via Bridge."""
        if not wallet_id:
            raise ValueError("wallet_id required for Bridge off-ramp")

        # Convert dict to BankAccount
        bank = BankAccount(
            account_holder_name=bank_account["account_holder_name"],
            account_number=bank_account["account_number"],
            routing_number=bank_account["routing_number"],
            account_type=bank_account.get("account_type", "checking"),
        )

        # Use existing withdraw_to_bank implementation
        result = await self._ramp.withdraw_to_bank(
            wallet_id=wallet_id,
            amount_usd=float(amount_crypto),
            bank_account=bank,
        )

        return RampSession(
            session_id=result.payout_id,
            provider="bridge",
            direction="offramp",
            status=RampStatus.PROCESSING,
            amount_fiat=amount_crypto,  # Approximate, actual will depend on fees
            amount_crypto=amount_crypto,
            fiat_currency=fiat_currency.upper(),
            crypto_currency=crypto_currency.upper(),
            chain=chain,
            destination_address=bank_account["account_number"],
            tx_hash=result.tx_hash,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )

    async def get_status(self, session_id: str) -> RampSession:
        """Get status of a Bridge session."""
        try:
            # Try as transfer (on-ramp)
            status = await self._ramp.get_funding_status(session_id)
            bridge_status = status.get("status", "pending")

            return RampSession(
                session_id=session_id,
                provider="bridge",
                direction="onramp",
                status=self._map_bridge_status(bridge_status),
                amount_fiat=Decimal(status.get("amount", "0")),
                amount_crypto=Decimal(status.get("amount", "0")),
                fiat_currency="USD",
                crypto_currency="USDC",
                chain=status.get("destination", {}).get("chain", "unknown"),
                destination_address=status.get("destination", {}).get("to_address", ""),
                tx_hash=status.get("destination_tx_hash"),
                updated_at=datetime.utcnow(),
            )
        except Exception:
            # Try as payout (off-ramp)
            status = await self._ramp.get_withdrawal_status(session_id)
            bridge_status = status.get("status", "pending")

            return RampSession(
                session_id=session_id,
                provider="bridge",
                direction="offramp",
                status=self._map_bridge_status(bridge_status),
                amount_fiat=Decimal(status.get("amount", "0")),
                amount_crypto=Decimal(status.get("amount", "0")),
                fiat_currency="USD",
                crypto_currency="USDC",
                chain=status.get("source", {}).get("chain", "unknown"),
                destination_address=status.get("destination", {}).get("account_number", ""),
                updated_at=datetime.utcnow(),
            )

    async def handle_webhook(self, payload: bytes, headers: dict) -> dict:
        """Handle Bridge webhook."""
        signature = headers.get("Bridge-Signature", headers.get("bridge-signature", ""))

        if not self._ramp.verify_webhook(payload, signature):
            raise ValueError("Invalid webhook signature")

        # Parse and return the event
        import json
        event = json.loads(payload)

        return {
            "provider": "bridge",
            "event_type": event.get("type"),
            "session_id": event.get("data", {}).get("id"),
            "status": self._map_bridge_status(event.get("data", {}).get("status")),
            "raw_event": event,
        }

    def _map_bridge_status(self, bridge_status: str) -> RampStatus:
        """Map Bridge status to RampStatus."""
        mapping = {
            "pending": RampStatus.PENDING,
            "processing": RampStatus.PROCESSING,
            "completed": RampStatus.COMPLETED,
            "failed": RampStatus.FAILED,
            "cancelled": RampStatus.FAILED,
            "expired": RampStatus.EXPIRED,
        }
        return mapping.get(bridge_status.lower(), RampStatus.PENDING)

    async def close(self):
        """Close the underlying ramp client."""
        await self._ramp.close()
