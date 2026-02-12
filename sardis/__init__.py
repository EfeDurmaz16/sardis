"""
Sardis: Payment OS for the Agent Economy

This package provides two interfaces:

1. **Quick-start (local simulation):**
   Simple classes for prototyping agent payment flows without an API key.

       >>> from sardis import Wallet, Transaction
       >>> wallet = Wallet(initial_balance=100)
       >>> tx = Transaction(from_wallet=wallet, to="merchant:api", amount=25)

2. **Production SDK (recommended):**
   Full API client for the Sardis platform. Requires ``sardis-sdk`` package.

       >>> from sardis import SardisClient
       >>> client = SardisClient(api_key="sk_...")
       >>> wallet = client.wallets.create(chain="base", token="USDC")

   Install the production SDK: ``pip install sardis-sdk``
"""

__version__ = "0.3.0"

# ---------------------------------------------------------------------------
# Production SDK re-exports (available when sardis-sdk is installed)
# ---------------------------------------------------------------------------
try:
    from sardis_sdk import (
        SardisClient,
        AsyncSardisClient,
        RetryConfig,
        TimeoutConfig,
    )

    _HAS_SDK = True
except ImportError:
    _HAS_SDK = False

# ---------------------------------------------------------------------------
# Quick-start / simulation classes (always available)
# ---------------------------------------------------------------------------
from .wallet import Wallet
from .transaction import Transaction, TransactionResult, TransactionStatus
from .policy import Policy, PolicyResult
from .agent import Agent

__all__ = [
    # Quick-start classes
    "Wallet",
    "Transaction",
    "TransactionResult",
    "TransactionStatus",
    "Policy",
    "PolicyResult",
    "Agent",
]

if _HAS_SDK:
    __all__ += [
        "SardisClient",
        "AsyncSardisClient",
        "RetryConfig",
        "TimeoutConfig",
    ]
