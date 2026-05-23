"""Type definitions for Sardis Fiat Ramp."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal


class FundingMethod(str, Enum):
    """Available funding methods."""
    BANK = "bank"
    CARD = "card"
    CRYPTO = "crypto"


@dataclass
class BankAccount:
    """Bank account details for payouts."""
    account_holder_name: str
    account_number: str
    routing_number: str
    account_type: Literal["checking", "savings"] = "checking"
    bank_name: str | None = None

    # For international wires
    swift_code: str | None = None
    iban: str | None = None
    bank_address: str | None = None


@dataclass
class MerchantAccount:
    """Merchant receiving payment."""
    name: str
    bank_account: BankAccount
    merchant_id: str | None = None
    category: str | None = None


@dataclass
class ACHDetails:
    """ACH transfer instructions."""
    account_number: str
    routing_number: str
    bank_name: str
    account_holder: str
    reference: str


@dataclass
class WireDetails:
    """Wire transfer instructions."""
    account_number: str
    routing_number: str
    swift_code: str
    bank_name: str
    bank_address: str
    account_holder: str
    reference: str


@dataclass
class FundingResult:
    """Result of a funding operation."""
    type: Literal["crypto", "fiat"]

    # For crypto deposits
    deposit_address: str | None = None
    chain: str | None = None
    token: str | None = None

    # For fiat deposits
    payment_link: str | None = None
    ach_instructions: ACHDetails | None = None
    wire_instructions: WireDetails | None = None
    estimated_arrival: datetime | None = None
    fee_percent: Decimal | None = None

    # Transfer ID for tracking
    transfer_id: str | None = None


@dataclass
class WithdrawalResult:
    """Result of a withdrawal to bank."""
    tx_hash: str
    payout_id: str
    estimated_arrival: datetime
    fee: Decimal
    status: Literal["pending", "processing", "completed", "failed"] = "pending"


@dataclass
class PaymentResult:
    """Result of a fiat payment to merchant."""
    status: Literal["completed", "pending_approval", "failed"]

    # For completed payments
    payment_id: str | None = None
    merchant_received: Decimal | None = None
    fee: Decimal | None = None
    tx_hash: str | None = None

    # For pending approval
    approval_request: dict | None = None

    # For failed payments
    error: str | None = None


@dataclass
class RampConfig:
    """Configuration for the fiat ramp."""
    sardis_key: str
    bridge_api_key: str
    environment: Literal["sandbox", "production"] = "sandbox"
    default_chain: str = "base"
