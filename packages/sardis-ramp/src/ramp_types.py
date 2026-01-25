"""Type definitions for Sardis Fiat Ramp."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal, Optional


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
    bank_name: Optional[str] = None

    # For international wires
    swift_code: Optional[str] = None
    iban: Optional[str] = None
    bank_address: Optional[str] = None


@dataclass
class MerchantAccount:
    """Merchant receiving payment."""
    name: str
    bank_account: BankAccount
    merchant_id: Optional[str] = None
    category: Optional[str] = None


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
    deposit_address: Optional[str] = None
    chain: Optional[str] = None
    token: Optional[str] = None

    # For fiat deposits
    payment_link: Optional[str] = None
    ach_instructions: Optional[ACHDetails] = None
    wire_instructions: Optional[WireDetails] = None
    estimated_arrival: Optional[datetime] = None
    fee_percent: Optional[Decimal] = None

    # Transfer ID for tracking
    transfer_id: Optional[str] = None


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
    payment_id: Optional[str] = None
    merchant_received: Optional[Decimal] = None
    fee: Optional[Decimal] = None
    tx_hash: Optional[str] = None

    # For pending approval
    approval_request: Optional[dict] = None

    # For failed payments
    error: Optional[str] = None


@dataclass
class RampConfig:
    """Configuration for the fiat ramp."""
    sardis_api_key: str
    bridge_api_key: str
    environment: Literal["sandbox", "production"] = "sandbox"
    default_chain: str = "base"
