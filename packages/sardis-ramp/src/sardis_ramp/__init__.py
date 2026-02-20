"""Sardis Fiat Ramp - Multi-provider fiat on/off-ramp infrastructure."""

# Legacy Bridge-only implementation (preserved for backward compatibility)
from .ramp import SardisFiatRamp
from .ramp_types import (
    FundingResult,
    WithdrawalResult,
    PaymentResult,
    BankAccount,
    MerchantAccount,
    FundingMethod,
)

# New multi-provider architecture
from .base import RampProvider, RampQuote, RampSession, RampStatus
from .providers import BridgeProvider, CoinbaseOnrampProvider
from .router import RampRouter

__version__ = "0.2.0"
__all__ = [
    # Legacy exports
    "SardisFiatRamp",
    "FundingResult",
    "WithdrawalResult",
    "PaymentResult",
    "BankAccount",
    "MerchantAccount",
    "FundingMethod",
    # New multi-provider exports
    "RampProvider",
    "RampQuote",
    "RampSession",
    "RampStatus",
    "BridgeProvider",
    "CoinbaseOnrampProvider",
    "RampRouter",
]
