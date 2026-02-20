"""Abstract RampProvider interface for multi-provider fiat ramp support."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal, Optional


class RampStatus(str, Enum):
    """Ramp session status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class RampQuote:
    """Quote for a fiat ramp operation."""
    provider: str
    amount_fiat: Decimal
    amount_crypto: Decimal
    fiat_currency: str
    crypto_currency: str
    chain: str
    fee_amount: Decimal
    fee_percent: Decimal
    exchange_rate: Decimal
    expires_at: datetime
    estimated_completion: Optional[datetime] = None
    quote_id: Optional[str] = None


@dataclass
class RampSession:
    """Active ramp session (on-ramp or off-ramp)."""
    session_id: str
    provider: str
    direction: Literal["onramp", "offramp"]
    status: RampStatus
    amount_fiat: Decimal
    amount_crypto: Decimal
    fiat_currency: str
    crypto_currency: str
    chain: str
    destination_address: str

    # Payment details
    payment_url: Optional[str] = None
    payment_method: Optional[str] = None

    # Tracking
    tx_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Metadata
    metadata: Optional[dict] = None


class RampProvider(ABC):
    """
    Abstract base class for fiat ramp providers.

    Providers implement on-ramp (fiat → crypto) and/or off-ramp (crypto → fiat).

    Example providers:
    - Bridge: Full on-ramp and off-ramp
    - Coinbase Onramp: On-ramp only (0% fee for USDC)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name."""
        pass

    @property
    @abstractmethod
    def supports_onramp(self) -> bool:
        """Whether this provider supports on-ramp (fiat → crypto)."""
        pass

    @property
    @abstractmethod
    def supports_offramp(self) -> bool:
        """Whether this provider supports off-ramp (crypto → fiat)."""
        pass

    @abstractmethod
    async def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        destination_currency: str,
        chain: str,
        direction: Literal["onramp", "offramp"],
    ) -> RampQuote:
        """
        Get a quote for a ramp operation.

        Args:
            amount: Amount in source currency
            source_currency: Source currency code (USD, USDC, etc.)
            destination_currency: Destination currency code
            chain: Blockchain network (base, ethereum, polygon, etc.)
            direction: "onramp" (fiat → crypto) or "offramp" (crypto → fiat)

        Returns:
            RampQuote with pricing and fee details

        Raises:
            ValueError: If the operation is not supported
        """
        pass

    @abstractmethod
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
        Create an on-ramp session (fiat → crypto).

        Args:
            amount_fiat: Amount of fiat to spend
            fiat_currency: Fiat currency code (USD, EUR, etc.)
            crypto_currency: Crypto to receive (USDC, USDT, etc.)
            chain: Destination blockchain
            destination_address: Address to receive crypto
            wallet_id: Optional Sardis wallet ID for policy checks
            metadata: Optional metadata to attach to the session

        Returns:
            RampSession with payment instructions

        Raises:
            NotImplementedError: If provider doesn't support on-ramp
        """
        pass

    @abstractmethod
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
        Create an off-ramp session (crypto → fiat).

        Args:
            amount_crypto: Amount of crypto to sell
            crypto_currency: Crypto to sell (USDC, USDT, etc.)
            chain: Source blockchain
            fiat_currency: Fiat currency to receive (USD, EUR, etc.)
            bank_account: Bank account details for payout
            wallet_id: Optional Sardis wallet ID for policy checks
            metadata: Optional metadata to attach to the session

        Returns:
            RampSession with deposit instructions

        Raises:
            NotImplementedError: If provider doesn't support off-ramp
        """
        pass

    @abstractmethod
    async def get_status(self, session_id: str) -> RampSession:
        """
        Get the current status of a ramp session.

        Args:
            session_id: The session ID to query

        Returns:
            Updated RampSession with current status
        """
        pass

    @abstractmethod
    async def handle_webhook(self, payload: bytes, headers: dict) -> dict:
        """
        Handle webhook callbacks from the provider.

        Args:
            payload: Raw webhook payload bytes
            headers: HTTP headers from the webhook request

        Returns:
            Parsed webhook event data

        Raises:
            ValueError: If webhook signature is invalid
        """
        pass

    async def close(self):
        """Close any resources (HTTP clients, etc.)."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
