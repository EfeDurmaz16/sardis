"""Wallet models for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import Field

from .base import SardisModel


class TokenBalance(SardisModel):
    """Balance for a specific token."""
    
    token: str
    balance: Decimal
    spent_total: Decimal = Decimal("0")
    limit_per_tx: Optional[Decimal] = None
    limit_total: Optional[Decimal] = None


class Wallet(SardisModel):
    """An agent's wallet."""
    
    wallet_id: str = Field(alias="id")
    agent_id: str
    balance: Decimal = Decimal("0")
    currency: str = "USDC"
    token_balances: dict[str, TokenBalance] = Field(default_factory=dict)
    limit_per_tx: Decimal = Decimal("100")
    limit_total: Decimal = Decimal("1000")
    spent_total: Decimal = Decimal("0")
    chain_address: Optional[str] = None
    chain: str = "base"
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class WalletBalance(SardisModel):
    """Wallet balance summary."""
    
    wallet_id: str
    total_balance_usd: Decimal
    balances: dict[str, Decimal]
    remaining_limit: Decimal
    updated_at: datetime


class FundWalletRequest(SardisModel):
    """Request to fund a wallet."""
    
    amount: Decimal
    token: str = "USDC"
    source: str = "treasury"
