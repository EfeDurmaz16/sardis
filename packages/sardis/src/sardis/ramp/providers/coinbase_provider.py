"""Coinbase Onramp provider - 0% fee USDC on-ramp."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal, Optional

import httpx

from ..base import RampProvider, RampQuote, RampSession, RampStatus

logger = logging.getLogger(__name__)


class CoinbaseOnrampProvider(RampProvider):
    """
    Coinbase Onramp provider.

    Features:
    - 0% fee for USDC (promotional, subject to change)
    - Guest checkout (no Coinbase account required)
    - On-ramp only (no off-ramp support)
    - Supports multiple blockchains (Ethereum, Base, Polygon, etc.)

    Note: For off-ramp, use Bridge provider instead.
    """

    COINBASE_API_URL = "https://api.coinbase.com/onramp/v1"
    COINBASE_SANDBOX_URL = "https://api.sandbox.coinbase.com/onramp/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        environment: Literal["sandbox", "production"] = "sandbox",
    ):
        """
        Initialize Coinbase Onramp provider.

        Args:
            api_key: Coinbase API key (or set COINBASE_ONRAMP_API_KEY env var)
            environment: "sandbox" or "production"
        """
        self._api_key = api_key or os.environ.get("COINBASE_ONRAMP_API_KEY")
        if not self._api_key:
            raise ValueError("Coinbase API key required")

        self._environment = environment
        self._base_url = (
            self.COINBASE_SANDBOX_URL if environment == "sandbox"
            else self.COINBASE_API_URL
        )
        self._webhook_secret = os.environ.get("COINBASE_WEBHOOK_SECRET")
        self._http = httpx.AsyncClient(timeout=30.0)

    @property
    def provider_name(self) -> str:
        return "coinbase"

    @property
    def supports_onramp(self) -> bool:
        return True

    @property
    def supports_offramp(self) -> bool:
        return False

    async def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        destination_currency: str,
        chain: str,
        direction: Literal["onramp", "offramp"],
    ) -> RampQuote:
        """
        Get a quote from Coinbase Onramp.

        Note: USDC has 0% fee (promotional). Other tokens may have fees.
        """
        if direction == "offramp":
            raise ValueError("Coinbase Onramp does not support off-ramp. Use Bridge provider.")

        # USDC is 0% fee (promotional)
        is_usdc = destination_currency.upper() == "USDC"
        fee_percent = Decimal("0.0") if is_usdc else Decimal("1.0")
        fee_amount = amount * (fee_percent / 100)

        return RampQuote(
            provider="coinbase",
            amount_fiat=amount,
            amount_crypto=amount - fee_amount,
            fiat_currency=source_currency.upper(),
            crypto_currency=destination_currency.upper(),
            chain=chain,
            fee_amount=fee_amount,
            fee_percent=fee_percent,
            exchange_rate=Decimal("1.0"),  # Assuming 1:1 for stablecoins
            expires_at=datetime.utcnow() + timedelta(minutes=10),
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
        """
        Create Coinbase on-ramp session.

        Creates a guest checkout session that allows users to buy crypto with fiat
        without needing a Coinbase account.
        """
        # Create on-ramp session via Coinbase API
        response = await self._coinbase_request(
            "POST",
            "/buy/session",
            json={
                "destination_wallet_address": destination_address,
                "destination_asset": crypto_currency.upper(),
                "destination_network": self._chain_to_coinbase(chain),
                "source_amount": str(amount_fiat),
                "source_currency": fiat_currency.upper(),
                "partner_user_id": wallet_id or metadata.get("user_id", "guest"),
                "guest_checkout": True,  # Allow purchase without Coinbase account
            }
        )

        session_id = response["session_id"]
        payment_url = response["hosted_url"]

        # USDC is 0% fee
        is_usdc = crypto_currency.upper() == "USDC"
        fee_percent = Decimal("0.0") if is_usdc else Decimal("1.0")
        amount_crypto = amount_fiat * (1 - fee_percent / 100)

        return RampSession(
            session_id=session_id,
            provider="coinbase",
            direction="onramp",
            status=RampStatus.PENDING,
            amount_fiat=amount_fiat,
            amount_crypto=amount_crypto,
            fiat_currency=fiat_currency.upper(),
            crypto_currency=crypto_currency.upper(),
            chain=chain,
            destination_address=destination_address,
            payment_url=payment_url,
            payment_method="guest_checkout",
            created_at=datetime.utcnow(),
            metadata={
                **(metadata or {}),
                "fee_percent": float(fee_percent),
                "promotional_zero_fee": is_usdc,
            },
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
        """
        Coinbase Onramp does not support off-ramp.

        Raises:
            NotImplementedError: Always - use Bridge provider for off-ramp
        """
        raise NotImplementedError(
            "Coinbase Onramp does not support off-ramp (crypto → fiat). "
            "Use the Bridge provider for off-ramp operations."
        )

    async def get_status(self, session_id: str) -> RampSession:
        """Get status of a Coinbase on-ramp session."""
        response = await self._coinbase_request("GET", f"/buy/session/{session_id}")

        status = response.get("status", "pending")
        tx_hash = response.get("transaction_hash")

        return RampSession(
            session_id=session_id,
            provider="coinbase",
            direction="onramp",
            status=self._map_coinbase_status(status),
            amount_fiat=Decimal(response.get("source_amount", "0")),
            amount_crypto=Decimal(response.get("destination_amount", "0")),
            fiat_currency=response.get("source_currency", "USD"),
            crypto_currency=response.get("destination_asset", "USDC"),
            chain=self._coinbase_to_chain(response.get("destination_network", "base")),
            destination_address=response.get("destination_wallet_address", ""),
            payment_url=response.get("hosted_url"),
            tx_hash=tx_hash,
            updated_at=datetime.utcnow(),
            completed_at=datetime.fromisoformat(response["completed_at"]) if response.get("completed_at") else None,
        )

    async def handle_webhook(self, payload: bytes, headers: dict) -> dict:
        """
        Handle Coinbase Onramp webhook.

        Verifies HMAC-SHA256 signature and parses the event.
        """
        signature = headers.get("X-Coinbase-Signature", headers.get("x-coinbase-signature", ""))

        if not self._verify_webhook(payload, signature):
            raise ValueError("Invalid Coinbase webhook signature")

        event = json.loads(payload)

        return {
            "provider": "coinbase",
            "event_type": event.get("event_type"),
            "session_id": event.get("data", {}).get("session_id"),
            "status": self._map_coinbase_status(event.get("data", {}).get("status")),
            "tx_hash": event.get("data", {}).get("transaction_hash"),
            "raw_event": event,
        }

    def _verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify Coinbase webhook HMAC-SHA256 signature."""
        if not self._webhook_secret:
            logger.warning("Coinbase webhook secret not configured")
            # Fail open in sandbox, fail closed in production
            return self._environment == "sandbox"

        try:
            expected = hmac.new(
                self._webhook_secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception as e:
            logger.error(f"Coinbase webhook verification failed: {e}")
            return False

    async def _coinbase_request(self, method: str, path: str, **kwargs) -> dict:
        """Make authenticated request to Coinbase API."""
        resp = await self._http.request(
            method,
            f"{self._base_url}{path}",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            **kwargs
        )
        resp.raise_for_status()
        return resp.json()

    def _chain_to_coinbase(self, chain: str) -> str:
        """Convert Sardis chain name to Coinbase network name."""
        mapping = {
            "base": "base",
            "ethereum": "ethereum",
            "polygon": "polygon",
            "arbitrum": "arbitrum",
            "optimism": "optimism",
            "avalanche": "avalanche",
        }
        return mapping.get(chain.lower(), chain)

    def _coinbase_to_chain(self, coinbase_network: str) -> str:
        """Convert Coinbase network name to Sardis chain name."""
        mapping = {
            "base": "base",
            "ethereum": "ethereum",
            "polygon": "polygon",
            "arbitrum": "arbitrum",
            "optimism": "optimism",
            "avalanche": "avalanche",
        }
        return mapping.get(coinbase_network.lower(), coinbase_network)

    def _map_coinbase_status(self, coinbase_status: str) -> RampStatus:
        """Map Coinbase status to RampStatus."""
        mapping = {
            "pending": RampStatus.PENDING,
            "processing": RampStatus.PROCESSING,
            "completed": RampStatus.COMPLETED,
            "success": RampStatus.COMPLETED,
            "failed": RampStatus.FAILED,
            "cancelled": RampStatus.FAILED,
            "expired": RampStatus.EXPIRED,
        }
        return mapping.get(coinbase_status.lower(), RampStatus.PENDING)

    async def close(self):
        """Close HTTP client."""
        await self._http.aclose()
