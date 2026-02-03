"""Wallet API endpoints."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from sardis_v2_core import Wallet, WalletRepository
from sardis_chain.executor import ChainExecutor, ChainRPCClient, STABLECOIN_ADDRESSES, CHAIN_CONFIGS
from sardis_api.authz import require_principal
from sardis_v2_core.transactions import validate_wallet_not_frozen
from sardis_ledger.records import LedgerStore

router = APIRouter(dependencies=[Depends(require_principal)])


# Request/Response Models
class CreateWalletRequest(BaseModel):
    agent_id: str
    mpc_provider: str = "turnkey"  # "turnkey" | "fireblocks" | "local"
    currency: str = "USDC"
    limit_per_tx: Decimal = Field(default=Decimal("100.00"))
    limit_total: Decimal = Field(default=Decimal("1000.00"))
    wallet_name: Optional[str] = Field(default=None, description="Optional provider wallet name (Turnkey)")


class UpdateWalletRequest(BaseModel):
    limit_per_tx: Optional[Decimal] = None
    limit_total: Optional[Decimal] = None
    is_active: Optional[bool] = None


class SetLimitsRequest(BaseModel):
    limit_per_tx: Optional[Decimal] = None
    limit_total: Optional[Decimal] = None


class SetAddressRequest(BaseModel):
    chain: str
    address: str


class FreezeWalletRequest(BaseModel):
    """Request to freeze a wallet."""
    reason: str = Field(description="Reason for freezing the wallet")
    frozen_by: str = Field(description="Admin or system identifier that froze the wallet")


class TransferRequest(BaseModel):
    """Request to transfer crypto from this wallet to another address."""
    destination: str = Field(description="Destination wallet address (0x...)")
    amount: Decimal = Field(gt=0, description="Amount in token units (e.g. 10.50 USDC)")
    token: str = Field(default="USDC")
    chain: str = Field(default="base_sepolia")
    domain: str = Field(default="localhost", description="Logical merchant/domain label for policy enforcement")
    memo: Optional[str] = Field(default=None, description="Optional memo for audit/logging")


class TransferResponse(BaseModel):
    tx_hash: str
    status: str
    from_address: str
    to_address: str
    amount: str
    token: str
    chain: str
    audit_anchor: Optional[str] = None


class WalletResponse(BaseModel):
    wallet_id: str
    agent_id: str
    mpc_provider: str
    addresses: dict[str, str]  # chain -> address mapping
    currency: str
    limit_per_tx: str
    limit_total: str
    is_active: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_wallet(cls, wallet: Wallet) -> "WalletResponse":
        return cls(
            wallet_id=wallet.wallet_id,
            agent_id=wallet.agent_id,
            mpc_provider=wallet.mpc_provider,
            addresses=wallet.addresses,
            currency=wallet.currency,
            limit_per_tx=str(wallet.limit_per_tx),
            limit_total=str(wallet.limit_total),
            is_active=wallet.is_active,
            created_at=wallet.created_at.isoformat(),
            updated_at=wallet.updated_at.isoformat(),
        )


class BalanceResponse(BaseModel):
    wallet_id: str
    chain: str
    token: str
    balance: str
    address: str


# Dependency
class WalletDependencies:
    def __init__(
        self,
        wallet_repo: WalletRepository,
        chain_executor: ChainExecutor | None = None,
        wallet_manager: any | None = None,
        ledger: LedgerStore | None = None,
    ):
        self.wallet_repo = wallet_repo
        self.chain_executor = chain_executor
        self.wallet_manager = wallet_manager
        self.ledger = ledger


def get_deps() -> WalletDependencies:
    raise NotImplementedError("Dependency override required")


# Endpoints
@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    request: CreateWalletRequest,
    deps: WalletDependencies = Depends(get_deps),
):
    """Create a new non-custodial wallet for an agent."""
    wallet_id_override: str | None = None
    addresses: dict[str, str] | None = None

    if request.mpc_provider == "turnkey":
        if not deps.wallet_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Turnkey wallet manager not configured",
            )

        wallet_name = request.wallet_name or f"agent_{request.agent_id}"
        provider = await deps.wallet_manager.create_turnkey_wallet(  # type: ignore[call-arg]
            wallet_name=wallet_name,
            agent_id=request.agent_id,
        )
        wallet_id_override = provider.get("wallet_id")
        addrs = provider.get("addresses") or []
        first = None
        if addrs:
            first = addrs[0].get("address") if isinstance(addrs[0], dict) else addrs[0]
        if isinstance(first, str) and first:
            # Same EVM address is valid across supported EVM chains.
            addresses = {
                "base_sepolia": first,
                "base": first,
                "ethereum": first,
                "polygon": first,
                "arbitrum": first,
                "optimism": first,
            }

        if wallet_id_override:
            existing = await deps.wallet_repo.get(wallet_id_override)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Wallet already exists",
                )

    wallet = await deps.wallet_repo.create(
        agent_id=request.agent_id,
        wallet_id=wallet_id_override,
        mpc_provider=request.mpc_provider,
        currency=request.currency,
        limit_per_tx=request.limit_per_tx,
        limit_total=request.limit_total,
        addresses=addresses,
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


@router.get("/{wallet_id}/balance", response_model=BalanceResponse)
async def get_wallet_balance(
    wallet_id: str,
    chain: str = Query(default="base_sepolia", description="Chain identifier"),
    token: str = Query(default="USDC", description="Token type"),
    deps: WalletDependencies = Depends(get_deps),
):
    """Get wallet balance from chain (non-custodial, read-only)."""
    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    address = wallet.get_address(chain)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No address found for chain {chain}",
        )

    # Validate token
    from sardis_v2_core.tokens import TokenType
    try:
        token_enum = TokenType(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid token: {token}",
        )

    # Query balance from chain
    balance = Decimal("0.00")

    if deps.chain_executor:
        try:
            # Get the RPC client for this chain
            rpc_client = deps.chain_executor._get_rpc_client(chain)

            # Get token contract address
            token_addresses = STABLECOIN_ADDRESSES.get(chain, {})
            token_address = token_addresses.get(token)

            if token_address:
                # Query ERC20 balance using balanceOf(address)
                # balanceOf selector: 0x70a08231
                balance_data = "0x70a08231" + address[2:].lower().zfill(64)
                result = await rpc_client._call("eth_call", [
                    {"to": token_address, "data": balance_data},
                    "latest"
                ])

                if result and result != "0x":
                    # Convert from minor units (6 decimals for USDC)
                    balance_minor = int(result, 16)
                    balance = Decimal(balance_minor) / Decimal(10**6)
        except Exception as e:
            # Log error but return 0 balance instead of failing
            import logging
            logging.getLogger(__name__).warning(f"Failed to query balance for {wallet_id}: {e}")

    return BalanceResponse(
        wallet_id=wallet_id,
        chain=chain,
        token=token,
        balance=str(balance),
        address=address,
    )


@router.get("/{wallet_id}/addresses", response_model=dict[str, str])
async def get_wallet_addresses(
    wallet_id: str,
    deps: WalletDependencies = Depends(get_deps),
):
    """Get all wallet addresses (chain -> address mapping)."""
    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return wallet.addresses


@router.post("/{wallet_id}/addresses", response_model=WalletResponse)
async def set_wallet_address(
    wallet_id: str,
    request: SetAddressRequest,
    deps: WalletDependencies = Depends(get_deps),
):
    """Set wallet address for a chain."""
    wallet = await deps.wallet_repo.set_address(
        wallet_id,
        chain=request.chain,
        address=request.address,
    )
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
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


@router.post("/{wallet_id}/transfer", response_model=TransferResponse)
async def transfer_crypto(
    wallet_id: str,
    request: TransferRequest,
    deps: WalletDependencies = Depends(get_deps),
):
    """Transfer crypto from wallet to any address (including A2A transfers)."""
    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    if not wallet.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet is inactive")

    freeze_ok, freeze_reason = validate_wallet_not_frozen(wallet)
    if not freeze_ok:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=freeze_reason)

    source_address = wallet.get_address(request.chain)
    if not source_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No address for chain {request.chain}",
        )

    if not deps.chain_executor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chain executor not available",
        )

    # Build a PaymentMandate for the chain executor
    import time
    import uuid
    import hashlib
    from sardis_v2_core.mandates import PaymentMandate, VCProof
    from sardis_v2_core.tokens import TokenType, to_raw_token_amount

    try:
        amount_minor = to_raw_token_amount(TokenType(request.token.upper()), request.amount)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported_token: {request.token}",
        ) from exc

    mandate = PaymentMandate(
        mandate_id=f"transfer_{uuid.uuid4().hex[:16]}",
        mandate_type="payment",
        issuer=f"wallet:{wallet_id}",
        subject=wallet.agent_id,
        expires_at=int(time.time()) + 300,
        nonce=uuid.uuid4().hex,
        proof=VCProof(
            verification_method=f"wallet:{wallet_id}#key-1",
            created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            proof_value="internal-transfer",
        ),
        domain=request.domain,
        purpose="checkout",
        chain=request.chain,
        token=request.token,
        amount_minor=amount_minor,
        destination=request.destination,
        audit_hash=hashlib.sha256(
            f"{wallet_id}:{request.destination}:{amount_minor}:{request.domain}:{request.memo or ''}".encode()
        ).hexdigest(),
        wallet_id=wallet_id,
    )

    if deps.wallet_manager:
        policy = await deps.wallet_manager.async_validate_policies(mandate)  # type: ignore[call-arg]
        if not getattr(policy, "allowed", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=getattr(policy, "reason", None) or "policy_denied",
            )

    try:
        receipt = await deps.chain_executor.dispatch_payment(mandate)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transfer failed: {str(e)}",
        )

    if deps.ledger:
        try:
            deps.ledger.append(payment_mandate=mandate, chain_receipt=receipt)
        except Exception:
            # Don't fail the transfer response if ledger append fails; this is best-effort for demo.
            pass

    return TransferResponse(
        tx_hash=receipt.tx_hash if hasattr(receipt, "tx_hash") else str(receipt),
        status="submitted",
        from_address=source_address,
        to_address=request.destination,
        amount=str(request.amount),
        token=request.token,
        chain=request.chain,
        audit_anchor=getattr(receipt, "audit_anchor", None),
    )


@router.post("/{wallet_id}/freeze", response_model=WalletResponse)
async def freeze_wallet(
    wallet_id: str,
    request: FreezeWalletRequest,
    deps: WalletDependencies = Depends(get_deps),
):
    """
    Freeze a wallet to block all transactions.

    Use this for compliance holds, suspicious activity, or risk mitigation.
    Frozen wallets cannot send transactions until unfrozen.
    """
    wallet = await deps.wallet_repo.freeze(
        wallet_id=wallet_id,
        frozen_by=request.frozen_by,
        reason=request.reason,
    )
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return WalletResponse.from_wallet(wallet)


@router.post("/{wallet_id}/unfreeze", response_model=WalletResponse)
async def unfreeze_wallet(
    wallet_id: str,
    deps: WalletDependencies = Depends(get_deps),
):
    """
    Unfreeze a wallet to restore normal operations.

    This removes the freeze hold and allows transactions to proceed.
    """
    wallet = await deps.wallet_repo.unfreeze(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return WalletResponse.from_wallet(wallet)
