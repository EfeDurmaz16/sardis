"""Wallet API endpoints."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from sardis_v2_core import Wallet, WalletRepository

router = APIRouter()


# Request/Response Models
class CreateWalletRequest(BaseModel):
    agent_id: str
    currency: str = "USDC"
    initial_balance: Decimal = Field(default=Decimal("0.00"))
    limit_per_tx: Decimal = Field(default=Decimal("100.00"))
    limit_total: Decimal = Field(default=Decimal("1000.00"))


class UpdateWalletRequest(BaseModel):
    limit_per_tx: Optional[Decimal] = None
    limit_total: Optional[Decimal] = None
    is_active: Optional[bool] = None


class SetLimitsRequest(BaseModel):
    limit_per_tx: Optional[Decimal] = None
    limit_total: Optional[Decimal] = None


class DepositRequest(BaseModel):
    amount: Decimal
    token: Optional[str] = None


class WithdrawRequest(BaseModel):
    amount: Decimal
    token: Optional[str] = None


class WalletResponse(BaseModel):
    wallet_id: str
    agent_id: str
    balance: str
    currency: str
    limit_per_tx: str
    limit_total: str
    spent_total: str
    remaining_limit: str
    is_active: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_wallet(cls, wallet: Wallet) -> "WalletResponse":
        return cls(
            wallet_id=wallet.wallet_id,
            agent_id=wallet.agent_id,
            balance=str(wallet.balance),
            currency=wallet.currency,
            limit_per_tx=str(wallet.limit_per_tx),
            limit_total=str(wallet.limit_total),
            spent_total=str(wallet.spent_total),
            remaining_limit=str(wallet.remaining_limit()),
            is_active=wallet.is_active,
            created_at=wallet.created_at.isoformat(),
            updated_at=wallet.updated_at.isoformat(),
        )


# Dependency
class WalletDependencies:
    def __init__(self, wallet_repo: WalletRepository):
        self.wallet_repo = wallet_repo


def get_deps() -> WalletDependencies:
    raise NotImplementedError("Dependency override required")


# Endpoints
@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    request: CreateWalletRequest,
    deps: WalletDependencies = Depends(get_deps),
):
    """Create a new wallet for an agent."""
    wallet = await deps.wallet_repo.create(
        agent_id=request.agent_id,
        currency=request.currency,
        balance=request.initial_balance,
        limit_per_tx=request.limit_per_tx,
        limit_total=request.limit_total,
    )
    return WalletResponse.from_wallet(wallet)


@router.get("", response_model=List[WalletResponse])
async def list_wallets(
    agent_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    deps: WalletDependencies = Depends(get_deps),
):
    """List all wallets."""
    wallets = await deps.wallet_repo.list(
        agent_id=agent_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return [WalletResponse.from_wallet(w) for w in wallets]


@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: str,
    deps: WalletDependencies = Depends(get_deps),
):
    """Get wallet details."""
    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return WalletResponse.from_wallet(wallet)


@router.patch("/{wallet_id}", response_model=WalletResponse)
async def update_wallet(
    wallet_id: str,
    request: UpdateWalletRequest,
    deps: WalletDependencies = Depends(get_deps),
):
    """Update wallet settings."""
    wallet = await deps.wallet_repo.update(
        wallet_id,
        limit_per_tx=request.limit_per_tx,
        limit_total=request.limit_total,
        is_active=request.is_active,
    )
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return WalletResponse.from_wallet(wallet)


@router.delete("/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wallet(
    wallet_id: str,
    deps: WalletDependencies = Depends(get_deps),
):
    """Delete a wallet."""
    deleted = await deps.wallet_repo.delete(wallet_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")


@router.post("/{wallet_id}/limits", response_model=WalletResponse)
async def set_wallet_limits(
    wallet_id: str,
    request: SetLimitsRequest,
    deps: WalletDependencies = Depends(get_deps),
):
    """Set spending limits for a wallet."""
    wallet = await deps.wallet_repo.set_limits(
        wallet_id,
        limit_per_tx=request.limit_per_tx,
        limit_total=request.limit_total,
    )
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return WalletResponse.from_wallet(wallet)


@router.post("/{wallet_id}/deposit", response_model=WalletResponse)
async def deposit_to_wallet(
    wallet_id: str,
    request: DepositRequest,
    deps: WalletDependencies = Depends(get_deps),
):
    """Deposit funds to a wallet."""
    wallet = await deps.wallet_repo.deposit(
        wallet_id,
        amount=request.amount,
        token=request.token,
    )
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return WalletResponse.from_wallet(wallet)


@router.post("/{wallet_id}/withdraw", response_model=WalletResponse)
async def withdraw_from_wallet(
    wallet_id: str,
    request: WithdrawRequest,
    deps: WalletDependencies = Depends(get_deps),
):
    """Withdraw funds from a wallet."""
    wallet = await deps.wallet_repo.withdraw(
        wallet_id,
        amount=request.amount,
        token=request.token,
    )
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet not found or insufficient balance",
        )
    return WalletResponse.from_wallet(wallet)


@router.get("/agent/{agent_id}", response_model=WalletResponse)
async def get_wallet_by_agent(
    agent_id: str,
    deps: WalletDependencies = Depends(get_deps),
):
    """Get wallet for a specific agent."""
    wallet = await deps.wallet_repo.get_by_agent(agent_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found for agent")
    return WalletResponse.from_wallet(wallet)
