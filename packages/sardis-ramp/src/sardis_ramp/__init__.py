"""Sardis Fiat Ramp - Bridge crypto wallets to traditional banking."""

from .ramp import SardisFiatRamp
from .ramp_types import (
    FundingResult,
    WithdrawalResult,
    PaymentResult,
    BankAccount,
    MerchantAccount,
    FundingMethod,
)

__version__ = "0.1.2"
__all__ = [
    "SardisFiatRamp",
    "FundingResult",
    "WithdrawalResult",
    "PaymentResult",
    "BankAccount",
    "MerchantAccount",
    "FundingMethod",
]
