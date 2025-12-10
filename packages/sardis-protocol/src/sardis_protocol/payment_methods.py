"""Payment method definitions for multi-payment support.

Sardis supports multiple payment methods as part of AP2's payment-agnostic design:
- Stablecoins (USDC, USDT, PYUSD, EURC) - Crypto-native payments
- Virtual Cards (Lithic) - Fiat on-ramp for traditional merchants
- x402 Micropayments - Pay-per-API-call use cases
- Bank Transfers (ACH/SEPA) - Future high-value transfers

Reference: https://github.com/google-agentic-commerce/a2a-x402
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class PaymentMethod(str, Enum):
    """Supported payment methods in Sardis."""
    
    # Crypto-native payments
    STABLECOIN = "stablecoin"
    
    # Pre-loaded virtual cards (fiat on-ramp)
    VIRTUAL_CARD = "virtual_card"
    
    # x402 micropayments for API access
    X402 = "x402"
    
    # Future: Direct bank transfers
    BANK_TRANSFER = "bank_transfer"
    
    # Legacy: Credit/debit card (via processor)
    CARD = "card"


class X402PaymentType(str, Enum):
    """x402 specific payment types."""
    
    # Pay per request
    PER_REQUEST = "per_request"
    
    # Streaming payments
    STREAMING = "streaming"
    
    # Pre-authorized spending limit
    BUDGET = "budget"


@dataclass
class PaymentMethodConfig:
    """Configuration for a payment method."""
    
    method: PaymentMethod
    enabled: bool = True
    
    # Fee configuration
    fee_percentage: Decimal = field(default_factory=lambda: Decimal("0.005"))  # 0.5%
    min_fee: Decimal = field(default_factory=lambda: Decimal("0.01"))
    max_fee: Decimal = field(default_factory=lambda: Decimal("100.00"))
    
    # Limits
    min_amount: Decimal = field(default_factory=lambda: Decimal("0.01"))
    max_amount: Decimal = field(default_factory=lambda: Decimal("100000.00"))
    
    # Provider-specific config
    provider: Optional[str] = None
    provider_config: dict = field(default_factory=dict)


@dataclass
class X402PaymentRequest:
    """
    x402 payment request structure.
    
    Based on the x402 protocol specification for micropayments.
    Reference: https://www.x402.org/
    """
    
    # Payment identification
    payment_id: str = ""
    
    # Payment type
    payment_type: X402PaymentType = X402PaymentType.PER_REQUEST
    
    # Amount in smallest unit (e.g., cents for USD)
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USD"
    
    # Resource being paid for
    resource_uri: str = ""
    resource_type: str = ""  # e.g., "api_call", "data_access"
    
    # Payer information (agent)
    payer_address: str = ""
    payer_signature: str = ""
    
    # Payee information (API provider)
    payee_address: str = ""
    
    # Metadata
    metadata: dict = field(default_factory=dict)
    
    # x402 specific fields
    x402_version: str = "1.0"
    x402_network: str = "base"  # Chain to use for settlement


@dataclass
class X402PaymentResponse:
    """Response from an x402 payment."""
    
    payment_id: str
    status: str  # pending, completed, failed
    
    # Settlement info
    tx_hash: Optional[str] = None
    chain: str = "base"
    
    # Access token (if payment grants access)
    access_token: Optional[str] = None
    expires_at: Optional[str] = None
    
    # Error info
    error_code: Optional[str] = None
    error_message: Optional[str] = None


def get_default_payment_methods() -> dict[PaymentMethod, PaymentMethodConfig]:
    """Get default payment method configurations."""
    return {
        PaymentMethod.STABLECOIN: PaymentMethodConfig(
            method=PaymentMethod.STABLECOIN,
            enabled=True,
            fee_percentage=Decimal("0.005"),  # 0.5%
            min_amount=Decimal("0.01"),
            max_amount=Decimal("1000000.00"),
        ),
        PaymentMethod.VIRTUAL_CARD: PaymentMethodConfig(
            method=PaymentMethod.VIRTUAL_CARD,
            enabled=True,
            fee_percentage=Decimal("0.015"),  # 1.5% (includes interchange)
            min_amount=Decimal("1.00"),
            max_amount=Decimal("10000.00"),
            provider="lithic",
        ),
        PaymentMethod.X402: PaymentMethodConfig(
            method=PaymentMethod.X402,
            enabled=True,
            fee_percentage=Decimal("0.002"),  # 0.2% (optimized for micropayments)
            min_amount=Decimal("0.001"),  # Sub-cent micropayments
            max_amount=Decimal("100.00"),  # Cap for x402
        ),
        PaymentMethod.BANK_TRANSFER: PaymentMethodConfig(
            method=PaymentMethod.BANK_TRANSFER,
            enabled=False,  # Future
            fee_percentage=Decimal("0.001"),  # 0.1%
            min_amount=Decimal("100.00"),
            max_amount=Decimal("1000000.00"),
        ),
    }


def parse_payment_method_from_mandate(mandate_payload: dict) -> PaymentMethod:
    """
    Parse payment method from an AP2 mandate payload.
    
    AP2 mandates can specify payment methods in several ways:
    - Explicit payment_method field
    - Inferred from payment details (e.g., card vs crypto address)
    - Default to stablecoin if not specified
    """
    # Check explicit payment_method field
    if "payment_method" in mandate_payload:
        method_str = mandate_payload["payment_method"]
        try:
            return PaymentMethod(method_str)
        except ValueError:
            pass
    
    # Check for x402 specific fields
    if "x402" in mandate_payload or mandate_payload.get("protocol") == "x402":
        return PaymentMethod.X402
    
    # Check for card-related fields
    payment_details = mandate_payload.get("payment_details", {})
    if "card_id" in payment_details or "virtual_card_id" in payment_details:
        return PaymentMethod.VIRTUAL_CARD
    
    # Check for bank transfer fields
    if "bank_account" in payment_details or "ach" in payment_details:
        return PaymentMethod.BANK_TRANSFER
    
    # Default to stablecoin
    return PaymentMethod.STABLECOIN
