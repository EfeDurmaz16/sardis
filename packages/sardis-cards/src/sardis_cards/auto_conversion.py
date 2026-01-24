"""
Unified Balance and Auto-Conversion Service for Sardis.

Implements Coinbase-style USDC/USD unification where:
- USDC and USD are treated as equivalent (1:1)
- User can deposit either fiat or crypto
- Agent can spend via crypto or virtual card from the same balance
- Automatic conversion happens seamlessly behind the scenes

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                 UNIFIED BALANCE (USDC = USD)                    │
│   Sardis Wallet                                                 │
│   ┌─────────────────────────────────────────┐                  │
│   │  Balance: $500.00 (USDC/USD)            │                  │
│   │  ├── On-chain: 500 USDC                 │                  │
│   │  └── Fiat Available: $500 USD           │                  │
│   └─────────────────────────────────────────┘                  │
│          ┌──────────────┼──────────────┐                       │
│          ▼              ▼              ▼                        │
│     Crypto Payment   Card Payment   Bank Withdraw              │
│     (Uses USDC)      (USDC→USD 1:1) (USDC→USD→ACH)            │
└─────────────────────────────────────────────────────────────────┘
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


class ConversionDirection(str, Enum):
    """Direction of conversion."""
    USDC_TO_USD = "usdc_to_usd"
    USD_TO_USDC = "usd_to_usdc"


class ConversionStatus(str, Enum):
    """Status of a conversion operation."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class UnifiedBalance:
    """
    Unified balance view combining USDC and USD.

    Treats USDC and USD as equivalent at 1:1 ratio.
    """
    wallet_id: str

    # Component balances
    usdc_balance_minor: int = 0  # In minor units (6 decimals)
    usd_balance_cents: int = 0   # In cents

    # Optional breakdown
    chain: str = "base"
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def usdc_balance(self) -> Decimal:
        """USDC balance as Decimal."""
        return Decimal(self.usdc_balance_minor) / Decimal(1_000_000)

    @property
    def usd_balance(self) -> Decimal:
        """USD balance as Decimal."""
        return Decimal(self.usd_balance_cents) / Decimal(100)

    @property
    def total_balance_cents(self) -> int:
        """Total unified balance in cents (USDC + USD)."""
        # USDC has 6 decimals, convert to cents (2 decimals)
        usdc_in_cents = self.usdc_balance_minor // 10_000
        return usdc_in_cents + self.usd_balance_cents

    @property
    def total_balance(self) -> Decimal:
        """Total unified balance as Decimal."""
        return Decimal(self.total_balance_cents) / Decimal(100)

    @property
    def display_balance(self) -> str:
        """Human-readable unified balance."""
        return f"${self.total_balance:,.2f}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "wallet_id": self.wallet_id,
            "unified_balance": {
                "amount": str(self.total_balance),
                "display": self.display_balance,
                "currency": "USD",
            },
            "breakdown": {
                "usdc": {
                    "amount": str(self.usdc_balance),
                    "minor": self.usdc_balance_minor,
                    "chain": self.chain,
                },
                "usd": {
                    "amount": str(self.usd_balance),
                    "cents": self.usd_balance_cents,
                },
            },
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class ConversionRecord:
    """Record of a conversion operation."""
    conversion_id: str
    wallet_id: str
    direction: ConversionDirection
    input_amount_minor: int
    output_amount_cents: int
    exchange_rate: Decimal = Decimal("1.0")
    fee_cents: int = 0
    status: ConversionStatus = ConversionStatus.PENDING
    trigger: str = "card_payment"  # card_payment, manual, auto_top_up
    provider_tx_id: Optional[str] = None
    card_transaction_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class WalletProvider(Protocol):
    """Protocol for wallet operations."""

    async def get_usdc_balance(self, wallet_id: str, chain: str = "base") -> int:
        """Get USDC balance in minor units."""
        ...

    async def get_wallet_address(self, wallet_id: str) -> str:
        """Get wallet address."""
        ...


class OfframpProvider(Protocol):
    """Protocol for off-ramp operations (USDC → USD)."""

    async def convert_to_fiat(
        self,
        wallet_id: str,
        usdc_amount_minor: int,
        destination: str,
        chain: str = "base",
    ) -> str:
        """
        Convert USDC to USD (1:1).

        Returns provider transaction ID.
        """
        ...


class OnrampProvider(Protocol):
    """Protocol for on-ramp operations (USD → USDC)."""

    async def convert_to_crypto(
        self,
        wallet_id: str,
        usd_amount_cents: int,
        destination_address: str,
        chain: str = "base",
    ) -> str:
        """
        Convert USD to USDC (1:1).

        Returns provider transaction ID.
        """
        ...


class UnifiedBalanceService:
    """
    Service for managing unified USDC/USD balances.

    Provides a single view of wallet balance that combines
    on-chain USDC and off-chain USD at 1:1 parity.
    """

    def __init__(
        self,
        wallet_provider: WalletProvider,
    ):
        self._wallet_provider = wallet_provider
        self._usd_balances: Dict[str, int] = {}  # wallet_id -> cents

    async def get_unified_balance(
        self,
        wallet_id: str,
        chain: str = "base",
    ) -> UnifiedBalance:
        """
        Get unified balance for a wallet.

        Args:
            wallet_id: The wallet ID
            chain: Blockchain for USDC balance

        Returns:
            UnifiedBalance combining USDC and USD
        """
        # Get USDC balance from chain
        usdc_balance = await self._wallet_provider.get_usdc_balance(wallet_id, chain)

        # Get USD balance (from internal ledger or card funding account)
        usd_balance = self._usd_balances.get(wallet_id, 0)

        return UnifiedBalance(
            wallet_id=wallet_id,
            usdc_balance_minor=usdc_balance,
            usd_balance_cents=usd_balance,
            chain=chain,
        )

    async def check_sufficient_balance(
        self,
        wallet_id: str,
        amount_cents: int,
        chain: str = "base",
    ) -> bool:
        """
        Check if wallet has sufficient unified balance.

        Args:
            wallet_id: The wallet ID
            amount_cents: Required amount in cents
            chain: Blockchain for USDC balance

        Returns:
            True if sufficient balance available
        """
        balance = await self.get_unified_balance(wallet_id, chain)
        return balance.total_balance_cents >= amount_cents

    def add_usd_balance(self, wallet_id: str, amount_cents: int) -> None:
        """Add USD balance to wallet (e.g., from fiat deposit)."""
        current = self._usd_balances.get(wallet_id, 0)
        self._usd_balances[wallet_id] = current + amount_cents
        logger.info(
            f"Added ${amount_cents / 100:.2f} USD to wallet {wallet_id}, "
            f"new USD balance: ${self._usd_balances[wallet_id] / 100:.2f}"
        )

    def deduct_usd_balance(self, wallet_id: str, amount_cents: int) -> bool:
        """
        Deduct USD balance from wallet.

        Returns True if deduction successful, False if insufficient.
        """
        current = self._usd_balances.get(wallet_id, 0)
        if current < amount_cents:
            return False
        self._usd_balances[wallet_id] = current - amount_cents
        logger.info(
            f"Deducted ${amount_cents / 100:.2f} USD from wallet {wallet_id}, "
            f"new USD balance: ${self._usd_balances[wallet_id] / 100:.2f}"
        )
        return True


class AutoConversionService:
    """
    Service for automatic USDC ↔ USD conversion.

    Handles automatic conversion when:
    1. Card payment requires USD but wallet has USDC
    2. Crypto payment requires USDC but wallet has USD

    Uses 1:1 conversion rate (like Coinbase USDC/USD).
    """

    def __init__(
        self,
        balance_service: UnifiedBalanceService,
        offramp_provider: Optional[OfframpProvider] = None,
        onramp_provider: Optional[OnrampProvider] = None,
        on_conversion_complete: Optional[Callable[[ConversionRecord], None]] = None,
    ):
        self._balance_service = balance_service
        self._offramp_provider = offramp_provider
        self._onramp_provider = onramp_provider
        self._on_conversion_complete = on_conversion_complete
        self._conversions: Dict[str, ConversionRecord] = {}
        self._conversion_counter = 0

    async def convert_for_card_payment(
        self,
        wallet_id: str,
        amount_cents: int,
        card_transaction_id: Optional[str] = None,
        chain: str = "base",
    ) -> ConversionRecord:
        """
        Convert USDC to USD for a card payment.

        This is triggered when a card payment happens and we need
        to convert crypto balance to fund the card.

        Args:
            wallet_id: The wallet ID
            amount_cents: Amount needed in cents
            card_transaction_id: Optional card transaction ID for tracking
            chain: Blockchain for USDC

        Returns:
            ConversionRecord with conversion details
        """
        self._conversion_counter += 1
        conversion_id = f"conv_{self._conversion_counter}_{wallet_id[:8]}"

        # USDC minor units for the amount (1:1, so cents → minor)
        # $1.00 = 100 cents = 1_000_000 minor units
        usdc_amount_minor = amount_cents * 10_000

        record = ConversionRecord(
            conversion_id=conversion_id,
            wallet_id=wallet_id,
            direction=ConversionDirection.USDC_TO_USD,
            input_amount_minor=usdc_amount_minor,
            output_amount_cents=amount_cents,
            exchange_rate=Decimal("1.0"),  # 1:1 USDC/USD
            fee_cents=0,  # No fee for 1:1 conversion
            status=ConversionStatus.PENDING,
            trigger="card_payment",
            card_transaction_id=card_transaction_id,
        )

        self._conversions[conversion_id] = record

        logger.info(
            f"Initiating auto-conversion for card payment: "
            f"wallet={wallet_id}, amount=${amount_cents / 100:.2f}, "
            f"usdc_needed={usdc_amount_minor / 1_000_000:.6f} USDC"
        )

        try:
            # Check if wallet has enough USDC
            balance = await self._balance_service.get_unified_balance(wallet_id, chain)

            if balance.usdc_balance_minor < usdc_amount_minor:
                record.status = ConversionStatus.FAILED
                record.error_message = (
                    f"Insufficient USDC balance: have {balance.usdc_balance_minor}, "
                    f"need {usdc_amount_minor}"
                )
                logger.error(f"Auto-conversion failed: {record.error_message}")
                return record

            # Execute conversion via off-ramp provider
            if self._offramp_provider:
                record.status = ConversionStatus.PROCESSING

                provider_tx_id = await self._offramp_provider.convert_to_fiat(
                    wallet_id=wallet_id,
                    usdc_amount_minor=usdc_amount_minor,
                    destination="card_funding",  # Fund the card account
                    chain=chain,
                )

                record.provider_tx_id = provider_tx_id
                record.status = ConversionStatus.COMPLETED
                record.completed_at = datetime.now(timezone.utc)

                # Update USD balance in balance service
                self._balance_service.add_usd_balance(wallet_id, amount_cents)

                logger.info(
                    f"Auto-conversion completed: conversion_id={conversion_id}, "
                    f"provider_tx={provider_tx_id}"
                )
            else:
                # Mock conversion for testing
                record.status = ConversionStatus.COMPLETED
                record.completed_at = datetime.now(timezone.utc)
                record.provider_tx_id = f"mock_{conversion_id}"

                # Update USD balance
                self._balance_service.add_usd_balance(wallet_id, amount_cents)

                logger.info(
                    f"Auto-conversion completed (mock): conversion_id={conversion_id}"
                )

            # Notify callback if registered
            if self._on_conversion_complete:
                self._on_conversion_complete(record)

        except Exception as e:
            record.status = ConversionStatus.FAILED
            record.error_message = str(e)
            logger.error(f"Auto-conversion failed: {e}")

        return record

    async def convert_for_crypto_payment(
        self,
        wallet_id: str,
        usdc_amount_minor: int,
        chain: str = "base",
    ) -> ConversionRecord:
        """
        Convert USD to USDC for a crypto payment.

        This is triggered when a crypto payment is needed but wallet
        only has USD balance.

        Args:
            wallet_id: The wallet ID
            usdc_amount_minor: USDC amount needed in minor units
            chain: Target blockchain

        Returns:
            ConversionRecord with conversion details
        """
        self._conversion_counter += 1
        conversion_id = f"conv_{self._conversion_counter}_{wallet_id[:8]}"

        # USD cents for the amount (1:1)
        usd_amount_cents = usdc_amount_minor // 10_000

        record = ConversionRecord(
            conversion_id=conversion_id,
            wallet_id=wallet_id,
            direction=ConversionDirection.USD_TO_USDC,
            input_amount_minor=usd_amount_cents * 10_000,  # Store consistently
            output_amount_cents=usd_amount_cents,
            exchange_rate=Decimal("1.0"),
            fee_cents=0,
            status=ConversionStatus.PENDING,
            trigger="crypto_payment",
        )

        self._conversions[conversion_id] = record

        logger.info(
            f"Initiating auto-conversion for crypto payment: "
            f"wallet={wallet_id}, amount={usdc_amount_minor / 1_000_000:.6f} USDC"
        )

        try:
            # Check if wallet has enough USD
            balance = await self._balance_service.get_unified_balance(wallet_id, chain)

            if balance.usd_balance_cents < usd_amount_cents:
                record.status = ConversionStatus.FAILED
                record.error_message = (
                    f"Insufficient USD balance: have {balance.usd_balance_cents}, "
                    f"need {usd_amount_cents}"
                )
                logger.error(f"Auto-conversion failed: {record.error_message}")
                return record

            # Deduct USD balance
            if not self._balance_service.deduct_usd_balance(wallet_id, usd_amount_cents):
                record.status = ConversionStatus.FAILED
                record.error_message = "Failed to deduct USD balance"
                return record

            # Execute conversion via on-ramp provider
            if self._onramp_provider:
                record.status = ConversionStatus.PROCESSING

                # Get wallet address for USDC deposit
                wallet_address = await self._balance_service._wallet_provider.get_wallet_address(wallet_id)

                provider_tx_id = await self._onramp_provider.convert_to_crypto(
                    wallet_id=wallet_id,
                    usd_amount_cents=usd_amount_cents,
                    destination_address=wallet_address,
                    chain=chain,
                )

                record.provider_tx_id = provider_tx_id
                record.status = ConversionStatus.COMPLETED
                record.completed_at = datetime.now(timezone.utc)

                logger.info(
                    f"Auto-conversion completed: conversion_id={conversion_id}, "
                    f"provider_tx={provider_tx_id}"
                )
            else:
                # Mock conversion
                record.status = ConversionStatus.COMPLETED
                record.completed_at = datetime.now(timezone.utc)
                record.provider_tx_id = f"mock_{conversion_id}"

                logger.info(
                    f"Auto-conversion completed (mock): conversion_id={conversion_id}"
                )

            if self._on_conversion_complete:
                self._on_conversion_complete(record)

        except Exception as e:
            record.status = ConversionStatus.FAILED
            record.error_message = str(e)
            logger.error(f"Auto-conversion failed: {e}")

        return record

    def get_conversion(self, conversion_id: str) -> Optional[ConversionRecord]:
        """Get conversion record by ID."""
        return self._conversions.get(conversion_id)

    def list_conversions(
        self,
        wallet_id: Optional[str] = None,
        status: Optional[ConversionStatus] = None,
        limit: int = 50,
    ) -> List[ConversionRecord]:
        """List conversion records with optional filters."""
        records = list(self._conversions.values())

        if wallet_id:
            records = [r for r in records if r.wallet_id == wallet_id]

        if status:
            records = [r for r in records if r.status == status]

        # Sort by created_at descending
        records.sort(key=lambda r: r.created_at, reverse=True)

        return records[:limit]


class CardPaymentAutoConverter:
    """
    Integration layer for auto-converting on card payments.

    Hooks into card webhook events to trigger automatic
    USDC → USD conversion when needed.
    """

    def __init__(
        self,
        auto_conversion_service: AutoConversionService,
        card_to_wallet_mapping: Dict[str, str],  # card_id -> wallet_id
    ):
        self._auto_conversion = auto_conversion_service
        self._card_wallet_map = card_to_wallet_mapping

    async def handle_card_authorization(
        self,
        card_id: str,
        amount_cents: int,
        merchant_name: str,
        transaction_id: str,
    ) -> Optional[ConversionRecord]:
        """
        Handle card authorization event.

        When a card transaction is authorized, this triggers
        automatic conversion from USDC to USD to cover the payment.

        Args:
            card_id: The card ID
            amount_cents: Transaction amount in cents
            merchant_name: Merchant name
            transaction_id: Card transaction ID

        Returns:
            ConversionRecord if conversion was performed
        """
        wallet_id = self._card_wallet_map.get(card_id)
        if not wallet_id:
            logger.warning(f"No wallet mapping found for card {card_id}")
            return None

        logger.info(
            f"Card authorization detected: card={card_id}, wallet={wallet_id}, "
            f"amount=${amount_cents / 100:.2f}, merchant={merchant_name}"
        )

        # Trigger auto-conversion
        record = await self._auto_conversion.convert_for_card_payment(
            wallet_id=wallet_id,
            amount_cents=amount_cents,
            card_transaction_id=transaction_id,
        )

        return record

    def register_card(self, card_id: str, wallet_id: str) -> None:
        """Register a card to wallet mapping."""
        self._card_wallet_map[card_id] = wallet_id
        logger.info(f"Registered card {card_id} to wallet {wallet_id}")

    def unregister_card(self, card_id: str) -> None:
        """Remove a card from wallet mapping."""
        if card_id in self._card_wallet_map:
            del self._card_wallet_map[card_id]
            logger.info(f"Unregistered card {card_id}")
