"""Wallet models for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import Field

from .base import SardisModel


class TokenLimit(SardisModel):
    """Token-specific spending limits (for policy tracking only, not balance storage)."""
    
    token: str
    limit_per_tx: Optional[Decimal] = None
    limit_total: Optional[Decimal] = None
    # Note: No balance field - balances are read from chain (non-custodial)


class Wallet(SardisModel):
    """
    Non-custodial wallet for an agent.
    
    This wallet never holds funds. It only:
    - Stores MPC provider and addresses
    - Signs transactions via MPC
    - Reads balances from chain (on-demand)
    """
    
    wallet_id: str
    agent_id: str
    mpc_provider: str = "turnkey"  # "turnkey" | "fireblocks" | "local"
    addresses: dict[str, str] = Field(default_factory=dict)  # chain -> address mapping
    currency: str = "USDC"  # Default currency for display
    token_limits: dict[str, TokenLimit] = Field(default_factory=dict)  # Token-specific limits
    limit_per_tx: Decimal = Decimal("100")
    limit_total: Decimal = Decimal("1000")
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class WalletBalance(SardisModel):
    """Wallet balance from chain (read-only, non-custodial)."""
    
    wallet_id: str
    chain: str
    token: str
    balance: Decimal
    address: str


class CreateWalletRequest(SardisModel):
    """Request to create a non-custodial wallet."""
    agent_id: str
    mpc_provider: str = "turnkey"  # "turnkey" | "fireblocks" | "local"
    currency: str = "USDC"
    limit_per_tx: Optional[Decimal] = None
    limit_total: Optional[Decimal] = None


# Aliases
WalletCreate = CreateWalletRequest
TokenBalance = TokenLimit  # Backwards compatibility alias