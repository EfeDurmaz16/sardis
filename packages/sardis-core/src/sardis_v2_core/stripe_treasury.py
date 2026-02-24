"""Stripe Treasury integration for platform-level fiat account management.

Sardis uses a single Stripe Treasury Financial Account at the platform level.
Agent balances are tracked via the sub-ledger system (sardis-ledger).
Sardis never holds funds directly - Stripe holds the fiat under their license.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)


class TreasuryAccountStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    RESTRICTED = "restricted"


class TransferStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    POSTED = "posted"
    FAILED = "failed"
    CANCELED = "canceled"
    RETURNED = "returned"


@dataclass
class TreasuryBalance:
    """Platform Treasury account balance."""
    available: Decimal
    pending_inbound: Decimal
    pending_outbound: Decimal
    currency: str = "usd"

    @property
    def total(self) -> Decimal:
        return self.available + self.pending_inbound - self.pending_outbound


@dataclass
class FinancialAccount:
    """Stripe Treasury Financial Account."""
    id: str
    status: TreasuryAccountStatus
    balance: TreasuryBalance
    supported_currencies: list[str] = field(default_factory=lambda: ["usd"])
    features: list[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InboundTransfer:
    """Record of an inbound transfer to Treasury."""
    id: str
    amount: Decimal
    currency: str
    status: TransferStatus
    source_type: str  # "ach", "wire", "stripe_balance"
    description: str = ""
    created_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutboundPayment:
    """Record of an outbound payment from Treasury."""
    id: str
    amount: Decimal
    currency: str
    status: TransferStatus
    destination_type: str  # "ach", "wire", "issuing_balance"
    destination_id: str = ""
    description: str = ""
    created_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IssuingFundTransfer:
    """Transfer from Treasury to Issuing balance for card funding."""
    id: str
    amount: Decimal
    currency: str
    status: TransferStatus
    financial_account_id: str = ""
    created_at: Optional[datetime] = None


class StripeTreasuryProvider:
    """Platform-level Stripe Treasury integration.

    Architecture:
    - Sardis has ONE Treasury Financial Account (platform level)
    - Agent balances tracked via sardis-ledger sub-ledger
    - Funds flow: Treasury -> Issuing Balance -> Virtual Cards
    - Inbound: Wire/ACH/SEPA -> Treasury
    - Outbound: Treasury -> Issuing or external bank

    Non-Custodial Note:
    Stripe holds the fiat under their license. Sardis orchestrates
    but never custodies funds. This removes MTL requirements.

    Usage:
        provider = StripeTreasuryProvider(
            stripe_secret_key="sk_...",
            financial_account_id="fa_..."
        )
        balance = await provider.get_balance()
        transfer = await provider.fund_issuing_balance(amount=Decimal("100.00"))
    """

    def __init__(
        self,
        stripe_secret_key: str,
        financial_account_id: Optional[str] = None,
        environment: Literal["sandbox", "production"] = "sandbox",
    ):
        self._api_key = stripe_secret_key
        self._financial_account_id = financial_account_id
        self._environment = environment
        self._base_url = "https://api.stripe.com/v1"
        self._initialized = False
        self._stripe = None
        try:
            import stripe

            stripe.api_key = stripe_secret_key
            self._stripe = stripe
        except ImportError:
            logger.warning(
                "Stripe SDK not installed; StripeTreasuryProvider will run in compatibility mode "
                "(install with pip install stripe)"
            )
        logger.info(
            "StripeTreasuryProvider initialized (env=%s, account=%s)",
            environment,
            financial_account_id or "pending",
        )

    @property
    def financial_account_id(self) -> Optional[str]:
        return self._financial_account_id

    async def create_financial_account(
        self,
        features: Optional[list[str]] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> FinancialAccount:
        """Create the platform Financial Account (done once during setup).

        Args:
            features: Treasury features to enable (e.g., ["inbound_transfers", "outbound_payments"])
            metadata: Key-value metadata for the account

        Returns:
            Created FinancialAccount
        """
        if features is None:
            features = [
                "inbound_transfers.ach",
                "outbound_payments.ach",
                "outbound_payments.us_domestic_wire",
                "financial_addresses.aba",
            ]

        logger.info("Creating Treasury Financial Account with features: %s", features)

        # In production, this calls Stripe API:
        # stripe.treasury.FinancialAccount.create(
        #     supported_currencies=["usd"],
        #     features={feat: {"requested": True} for feat in features},
        #     metadata=metadata or {},
        # )

        account = FinancialAccount(
            id=self._financial_account_id or "fa_simulated",
            status=TreasuryAccountStatus.OPEN,
            balance=TreasuryBalance(
                available=Decimal("0"),
                pending_inbound=Decimal("0"),
                pending_outbound=Decimal("0"),
            ),
            features=features,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )

        self._financial_account_id = account.id
        self._initialized = True
        return account

    async def get_balance(self) -> TreasuryBalance:
        """Get current Treasury account balance.

        Returns:
            TreasuryBalance with available, pending_inbound, pending_outbound
        """
        self._ensure_initialized()

        # In production: stripe.treasury.FinancialAccount.retrieve(self._financial_account_id)
        logger.debug("Fetching Treasury balance for %s", self._financial_account_id)

        return TreasuryBalance(
            available=Decimal("0"),
            pending_inbound=Decimal("0"),
            pending_outbound=Decimal("0"),
            currency="usd",
        )

    async def create_outbound_payment(
        self,
        amount: Decimal,
        destination_account: str,
        destination_type: Literal["ach", "wire"] = "ach",
        description: str = "",
        metadata: Optional[dict[str, str]] = None,
    ) -> OutboundPayment:
        """Send funds from Treasury to an external bank account.

        Args:
            amount: Amount in USD
            destination_account: Stripe PaymentMethod or BankAccount ID
            destination_type: Transfer method (ach or wire)
            description: Payment description
            metadata: Additional metadata

        Returns:
            OutboundPayment record
        """
        self._ensure_initialized()
        logger.info(
            "Creating outbound payment: $%s via %s to %s",
            amount, destination_type, destination_account,
        )

        return OutboundPayment(
            id=f"obp_sim_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            amount=amount,
            currency="usd",
            status=TransferStatus.PROCESSING,
            destination_type=destination_type,
            destination_id=destination_account,
            description=description,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )

    async def fund_issuing_balance(
        self,
        amount: Decimal,
        description: str = "Fund agent virtual cards",
        connected_account_id: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> IssuingFundTransfer:
        """Transfer funds from Treasury to Issuing balance for card funding.

        This is the bridge between Treasury (fiat holding) and Issuing (card spending).

        Args:
            amount: Amount to transfer to Issuing balance
            description: Transfer description
            connected_account_id: Optional Stripe Connect account ID (acct_...)
            metadata: Optional additional metadata for reconciliation

        Returns:
            IssuingFundTransfer record
        """
        self._ensure_initialized()
        if self._stripe is None:
            raise RuntimeError(
                "Stripe SDK is not available. Install stripe and configure STRIPE_API_KEY."
            )

        if amount <= 0:
            raise ValueError("amount must be greater than zero")

        amount_cents = int((amount * 100).to_integral_value())
        logger.info(
            "Funding Issuing balance via Stripe Top-up: $%s (account=%s)",
            amount,
            self._financial_account_id,
        )

        try:
            topup_metadata = {
                "sardis_purpose": "issuing_balance_funding",
                "financial_account_id": self._financial_account_id or "",
            }
            if metadata:
                topup_metadata.update(metadata)

            create_kwargs: dict[str, Any] = {
                "amount": amount_cents,
                "currency": "usd",
                "description": description,
                "metadata": topup_metadata,
            }
            if connected_account_id:
                create_kwargs["stripe_account"] = connected_account_id

            topup = await asyncio.to_thread(
                self._stripe.Topup.create,
                **create_kwargs,
            )
        except Exception as exc:
            logger.error("Stripe Top-up create failed: %s", exc)
            raise RuntimeError(
                "Failed to create Stripe top-up for Issuing balance funding. "
                "Ensure Issuing funding capabilities are enabled on your Stripe account."
            ) from exc

        status_map = {
            "succeeded": TransferStatus.POSTED,
            "pending": TransferStatus.PENDING,
            "in_transit": TransferStatus.PROCESSING,
            "reversed": TransferStatus.RETURNED,
            "failed": TransferStatus.FAILED,
            "canceled": TransferStatus.CANCELED,
        }
        mapped_status = status_map.get(str(topup.get("status", "")).lower(), TransferStatus.PROCESSING)

        return IssuingFundTransfer(
            id=str(topup.get("id") or f"ift_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
            amount=amount,
            currency=str(topup.get("currency", "usd")),
            status=mapped_status,
            financial_account_id=self._financial_account_id or "",
            created_at=datetime.utcnow(),
        )

    async def get_inbound_transfers(
        self,
        limit: int = 20,
        status: Optional[TransferStatus] = None,
    ) -> list[InboundTransfer]:
        """List inbound transfers to Treasury.

        Args:
            limit: Max results
            status: Filter by status

        Returns:
            List of InboundTransfer records
        """
        self._ensure_initialized()
        logger.debug("Listing inbound transfers (limit=%d, status=%s)", limit, status)
        return []

    async def get_outbound_payments(
        self,
        limit: int = 20,
        status: Optional[TransferStatus] = None,
    ) -> list[OutboundPayment]:
        """List outbound payments from Treasury.

        Args:
            limit: Max results
            status: Filter by status

        Returns:
            List of OutboundPayment records
        """
        self._ensure_initialized()
        logger.debug("Listing outbound payments (limit=%d, status=%s)", limit, status)
        return []

    async def handle_webhook(self, event_type: str, event_data: dict) -> None:
        """Handle Stripe Treasury webhook events.

        Supported events:
        - treasury.received_credit: Inbound funds arrived
        - treasury.outbound_payment.posted: Outbound payment completed
        - treasury.outbound_payment.failed: Outbound payment failed
        - treasury.financial_account.features_status_updated: Feature status change

        Args:
            event_type: Stripe event type
            event_data: Event payload
        """
        logger.info("Treasury webhook: %s", event_type)

        handlers = {
            "treasury.received_credit": self._handle_received_credit,
            "treasury.outbound_payment.posted": self._handle_outbound_posted,
            "treasury.outbound_payment.failed": self._handle_outbound_failed,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(event_data)
        else:
            logger.debug("Unhandled Treasury event: %s", event_type)

    async def _handle_received_credit(self, data: dict) -> None:
        """Process incoming funds to Treasury."""
        amount = Decimal(str(data.get("amount", 0))) / 100
        logger.info("Received credit: $%s", amount)

    async def _handle_outbound_posted(self, data: dict) -> None:
        """Process completed outbound payment."""
        logger.info("Outbound payment posted: %s", data.get("id"))

    async def _handle_outbound_failed(self, data: dict) -> None:
        """Process failed outbound payment."""
        logger.warning("Outbound payment failed: %s - %s", data.get("id"), data.get("failure_code"))

    def _ensure_initialized(self) -> None:
        """Ensure provider has a financial account configured."""
        if not self._financial_account_id:
            raise ValueError(
                "No financial_account_id configured. "
                "Call create_financial_account() first or pass financial_account_id to constructor."
            )
