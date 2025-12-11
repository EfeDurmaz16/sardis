"""
Sardis: Programmable Payment Protocol for AI Agents

A simple, elegant API for agent-to-agent payments with policy enforcement.

Example:
    >>> from sardis import Wallet, Transaction
    >>> wallet = Wallet(initial_balance=100)
    >>> tx = Transaction(from_wallet=wallet, to="merchant:api", amount=25)
    >>> result = tx.execute()
    >>> print(wallet.balance)  # 75.00
"""

from .wallet import Wallet
from .transaction import Transaction, TransactionResult
from .policy import Policy, PolicyResult
from .agent import Agent

__version__ = "0.1.0"
__all__ = ["Wallet", "Transaction", "TransactionResult", "Policy", "PolicyResult", "Agent"]


