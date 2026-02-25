"""
Sardis: Payment OS for the Agent Economy

Quick start::

    >>> from sardis import SardisClient
    >>> client = SardisClient(api_key="sk_...")
    >>> wallet = client.wallets.create(name="my-agent", chain="base", policy="Max $100/day")
    >>> tx = wallet.pay(to="openai.com", amount="25.00", token="USDC")
    >>> print(tx.success)  # True

The SardisClient works in two modes:

1. **Simulation mode** (default): All operations run locally, no API key needed.
   Great for prototyping and testing agent payment flows.

2. **Production mode**: When ``sardis-sdk`` is installed and a real API key is
   provided, operations delegate to the Sardis platform.
"""

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Quick-start / simulation classes (always available)
# ---------------------------------------------------------------------------
from .wallet import Wallet
from .transaction import Transaction, TransactionResult, TransactionStatus
from .policy import Policy, PolicyResult
from .agent import Agent
from .group import AgentGroup
from .client import SardisClient, ManagedWallet, ManagedGroup, LedgerEntry

# ---------------------------------------------------------------------------
# Production SDK re-exports (available when sardis-sdk is installed)
# ---------------------------------------------------------------------------
try:
    from sardis_sdk import (
        AsyncSardisClient,
        RetryConfig,
        TimeoutConfig,
    )
    _HAS_SDK = True
except ImportError:
    _HAS_SDK = False

__all__ = [
    # Client (always available — simulation or production)
    "SardisClient",
    "ManagedWallet",
    "ManagedGroup",
    "LedgerEntry",
    # Quick-start classes
    "Wallet",
    "Transaction",
    "TransactionResult",
    "TransactionStatus",
    "Policy",
    "PolicyResult",
    "Agent",
    "AgentGroup",
]

if _HAS_SDK:
    __all__ += [
        "AsyncSardisClient",
        "RetryConfig",
        "TimeoutConfig",
    ]
