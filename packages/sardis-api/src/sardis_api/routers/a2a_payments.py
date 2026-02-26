"""Agent-to-Agent Payment Protocol API endpoints.

This module provides REST API endpoints for the A2A escrow and settlement protocol:

Escrow Endpoints:
    POST   /api/v2/a2a/escrows              - Create new escrow
    GET    /api/v2/a2a/escrows/{escrow_id}  - Get escrow details
    POST   /api/v2/a2a/escrows/{escrow_id}/fund     - Fund escrow
    POST   /api/v2/a2a/escrows/{escrow_id}/deliver  - Confirm delivery
    POST   /api/v2/a2a/escrows/{escrow_id}/release  - Release payment
    POST   /api/v2/a2a/escrows/{escrow_id}/refund   - Refund payment
    POST   /api/v2/a2a/escrows/{escrow_id}/dispute  - Open dispute
    GET    /api/v2/a2a/escrows              - List escrows

Settlement Endpoints:
    GET    /api/v2/a2a/settlements          - List settlements

Usage:
    # Create escrow
    POST /api/v2/a2a/escrows
    {
        "payer_agent_id": "agent_123",
        "payee_agent_id": "agent_456",
        "amount": "100.00",
        "token": "USDC",
        "chain": "base",
        "timeout_hours": 24
    }

    # Fund escrow (after on-chain deposit)
    POST /api/v2/a2a/escrows/{escrow_id}/fund
    {
        "tx_hash": "0x..."
    }

    # Confirm delivery
    POST /api/v2/a2a/escrows/{escrow_id}/deliver
    {
        "proof": "delivery_hash_or_receipt"
    }

    # Release funds
    POST /api/v2/a2a/escrows/{escrow_id}/release
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, Literal, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from sardis_v2_core.a2a_escrow import EscrowManager, Escrow, EscrowState
from sardis_v2_core.a2a_settlement import SettlementEngine, SettlementResult
from sardis_v2_core.tokens import TokenType
from sardis_v2_core.exceptions import (
    SardisNotFoundError,
    SardisValidationError,
    SardisConflictError,
    SardisTransactionFailedError,
)
from sardis_api.authz import Principal, require_principal

# Create router with authentication
router = APIRouter(
    prefix="/a2a",
    tags=["a2a-payments"],
    dependencies=[Depends(require_principal)],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateEscrowRequest(BaseModel):
    """Request to create a new escrow."""
    payer_agent_id: str = Field(description="Payer agent identifier")
    payee_agent_id: str = Field(description="Payee agent identifier")
    amount: Decimal = Field(gt=0, description="Escrow amount in token units")
    token: str = Field(default="USDC", description="Token type (USDC, USDT, etc.)")
    chain: str = Field(default="base", description="Blockchain network")
    timeout_hours: int = Field(default=24, gt=0, le=168, description="Escrow timeout in hours (max 7 days)")
    metadata: Optional[dict] = Field(default=None, description="Optional metadata")


class FundEscrowRequest(BaseModel):
    """Request to mark escrow as funded."""
    tx_hash: str = Field(description="On-chain funding transaction hash")


class ConfirmDeliveryRequest(BaseModel):
    """Request to confirm delivery of goods/services."""
    proof: str = Field(description="Delivery proof (hash, receipt, signature, etc.)")


class RefundEscrowRequest(BaseModel):
    """Request to refund an escrow."""
    reason: str = Field(description="Reason for refund")
    tx_hash: Optional[str] = Field(default=None, description="Optional refund transaction hash")


class DisputeEscrowRequest(BaseModel):
    """Request to open a dispute."""
    reason: str = Field(description="Dispute reason")


class ReleaseEscrowRequest(BaseModel):
    """Request to release escrow funds."""
    tx_hash: Optional[str] = Field(default=None, description="Optional settlement transaction hash")


class EscrowResponse(BaseModel):
    """Escrow details response."""
    id: str
    payer_agent_id: str
    payee_agent_id: str
    amount: str
    token: str
    chain: str
    state: str
    created_at: datetime
    expires_at: datetime
    funded_at: Optional[datetime] = None
    funding_tx_hash: Optional[str] = None
    delivery_proof: Optional[str] = None
    delivered_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    release_tx_hash: Optional[str] = None
    refunded_at: Optional[datetime] = None
    refund_tx_hash: Optional[str] = None
    refund_reason: Optional[str] = None
    disputed_at: Optional[datetime] = None
    dispute_reason: Optional[str] = None
    dispute_resolution: Optional[str] = None
    metadata: dict
    updated_at: datetime

    @classmethod
    def from_escrow(cls, escrow: Escrow) -> "EscrowResponse":
        """Convert Escrow to response model."""
        return cls(
            id=escrow.id,
            payer_agent_id=escrow.payer_agent_id,
            payee_agent_id=escrow.payee_agent_id,
            amount=str(escrow.amount),
            token=escrow.token,
            chain=escrow.chain,
            state=escrow.state.value,
            created_at=escrow.created_at,
            expires_at=escrow.expires_at,
            funded_at=escrow.funded_at,
            funding_tx_hash=escrow.funding_tx_hash,
            delivery_proof=escrow.delivery_proof,
            delivered_at=escrow.delivered_at,
            released_at=escrow.released_at,
            release_tx_hash=escrow.release_tx_hash,
            refunded_at=escrow.refunded_at,
            refund_tx_hash=escrow.refund_tx_hash,
            refund_reason=escrow.refund_reason,
            disputed_at=escrow.disputed_at,
            dispute_reason=escrow.dispute_reason,
            dispute_resolution=escrow.dispute_resolution,
            metadata=escrow.metadata,
            updated_at=escrow.updated_at,
        )


class SettlementResponse(BaseModel):
    """Settlement details response."""
    escrow_id: str
    tx_hash: Optional[str]
    settlement_type: str
    ledger_entries: List[str]
    settled_at: datetime
    payer_agent_id: str
    payee_agent_id: str
    amount: str
    token: str
    chain: str
    block_number: Optional[int] = None
    explorer_url: Optional[str] = None
    execution_path: Optional[str] = None
    user_op_hash: Optional[str] = None

    @classmethod
    def from_settlement(cls, settlement: SettlementResult) -> "SettlementResponse":
        """Convert SettlementResult to response model."""
        return cls(
            escrow_id=settlement.escrow_id,
            tx_hash=settlement.tx_hash,
            settlement_type=settlement.settlement_type,
            ledger_entries=settlement.ledger_entries,
            settled_at=settlement.settled_at,
            payer_agent_id=settlement.payer_agent_id,
            payee_agent_id=settlement.payee_agent_id,
            amount=str(settlement.amount),
            token=settlement.token,
            chain=settlement.chain,
            block_number=settlement.block_number,
            explorer_url=settlement.explorer_url,
            execution_path=settlement.execution_path,
            user_op_hash=settlement.user_op_hash,
        )


class EscrowListResponse(BaseModel):
    """List of escrows response."""
    escrows: List[EscrowResponse]
    total: int


class SettlementListResponse(BaseModel):
    """List of settlements response."""
    settlements: List[SettlementResponse]
    total: int


# ============================================================================
# Escrow Endpoints
# ============================================================================

@router.post("/escrows", response_model=EscrowResponse, status_code=status.HTTP_201_CREATED)
async def create_escrow(
    request: CreateEscrowRequest,
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    """
    Create a new escrow between two agents.

    The escrow will be in CREATED state until funded. Payer must deposit
    funds on-chain and then call the /fund endpoint with the transaction hash.
    """
    manager = EscrowManager()

    try:
        # Validate token
        token = TokenType(request.token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported token: {request.token}",
        )

    try:
        escrow = await manager.create_escrow(
            payer=request.payer_agent_id,
            payee=request.payee_agent_id,
            amount=request.amount,
            token=token,
            chain=request.chain,
            timeout_hours=request.timeout_hours,
            metadata=request.metadata,
        )
        return EscrowResponse.from_escrow(escrow)

    except SardisValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.get("/escrows/{escrow_id}", response_model=EscrowResponse)
async def get_escrow(
    escrow_id: str,
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    """
    Get escrow details by ID.
    """
    manager = EscrowManager()

    try:
        escrow = await manager.get_escrow(escrow_id)
        return EscrowResponse.from_escrow(escrow)

    except SardisNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.post("/escrows/{escrow_id}/fund", response_model=EscrowResponse)
async def fund_escrow(
    escrow_id: str,
    request: FundEscrowRequest,
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    """
    Mark escrow as funded after on-chain deposit.

    Payer should deposit funds to the escrow wallet on-chain, then call
    this endpoint with the transaction hash to mark the escrow as FUNDED.
    """
    manager = EscrowManager()

    try:
        escrow = await manager.fund_escrow(escrow_id, request.tx_hash)
        return EscrowResponse.from_escrow(escrow)

    except SardisNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except SardisConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )


@router.post("/escrows/{escrow_id}/deliver", response_model=EscrowResponse)
async def confirm_delivery(
    escrow_id: str,
    request: ConfirmDeliveryRequest,
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    """
    Confirm delivery of goods/services.

    Payee calls this endpoint to confirm that goods or services have been
    delivered. The proof can be a hash, receipt, signature, or any other
    evidence of delivery.
    """
    manager = EscrowManager()

    try:
        escrow = await manager.confirm_delivery(escrow_id, request.proof)
        return EscrowResponse.from_escrow(escrow)

    except SardisNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except SardisConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )


@router.post("/escrows/{escrow_id}/release", response_model=EscrowResponse)
async def release_escrow(
    escrow_id: str,
    http_request: Request,
    request: ReleaseEscrowRequest = ReleaseEscrowRequest(),
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    """
    Release escrowed funds to payee.

    After delivery is confirmed, call this endpoint to release the funds.
    This triggers settlement (either on-chain or off-chain depending on
    the agents' wallet configuration).
    """
    manager = EscrowManager()
    engine = SettlementEngine(
        chain_executor=getattr(http_request.app.state, "chain_executor", None),
        wallet_repo=getattr(http_request.app.state, "wallet_repo", None),
    )

    try:
        settlement_tx_hash = request.tx_hash
        if settlement_tx_hash is None:
            escrow = await manager.get_escrow(escrow_id)
            settlement = await engine.settle_on_chain(escrow)
            settlement_tx_hash = settlement.tx_hash

        escrow = await manager.release_escrow(escrow_id, settlement_tx_hash)
        return EscrowResponse.from_escrow(escrow)

    except SardisNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except SardisConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except SardisTransactionFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=e.message,
        )
    except SardisValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post("/escrows/{escrow_id}/refund", response_model=EscrowResponse)
async def refund_escrow(
    escrow_id: str,
    request: RefundEscrowRequest,
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    """
    Refund escrowed funds to payer.

    If the transaction fails or needs to be cancelled, call this endpoint
    to refund the funds to the payer.
    """
    manager = EscrowManager()

    try:
        escrow = await manager.refund_escrow(escrow_id, request.reason, request.tx_hash)
        return EscrowResponse.from_escrow(escrow)

    except SardisNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except SardisConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )


@router.post("/escrows/{escrow_id}/dispute", response_model=EscrowResponse)
async def dispute_escrow(
    escrow_id: str,
    request: DisputeEscrowRequest,
    principal: Principal = Depends(require_principal),
) -> EscrowResponse:
    """
    Open a dispute for an escrow.

    If there's a disagreement about delivery or payment, either party can
    open a dispute. The escrow enters DISPUTED state and requires manual
    resolution.
    """
    manager = EscrowManager()

    try:
        escrow = await manager.dispute_escrow(escrow_id, request.reason)
        return EscrowResponse.from_escrow(escrow)

    except SardisNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except SardisConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )


@router.get("/escrows", response_model=EscrowListResponse)
async def list_escrows(
    agent_id: str = Query(..., description="Agent ID to filter by"),
    role: Literal["payer", "payee", "any"] = Query("any", description="Filter by role"),
    state: Optional[str] = Query(None, description="Filter by state"),
    principal: Principal = Depends(require_principal),
) -> EscrowListResponse:
    """
    List escrows for an agent.

    Returns all escrows where the agent is either payer or payee,
    with optional filtering by role and state.
    """
    manager = EscrowManager()

    # Validate state if provided
    state_filter = None
    if state:
        try:
            state_filter = EscrowState(state)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state: {state}",
            )

    escrows = await manager.list_escrows(
        agent_id=agent_id,
        role=role,
        state=state_filter,
    )

    return EscrowListResponse(
        escrows=[EscrowResponse.from_escrow(e) for e in escrows],
        total=len(escrows),
    )


# ============================================================================
# Settlement Endpoints
# ============================================================================

@router.get("/settlements", response_model=SettlementListResponse)
async def list_settlements(
    agent_id: Optional[str] = Query(None, description="Filter by payer or payee agent ID"),
    settlement_type: Optional[Literal["on_chain", "off_chain"]] = Query(None, description="Filter by settlement type"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results to return"),
    principal: Principal = Depends(require_principal),
) -> SettlementListResponse:
    """
    List settlements with optional filters.

    Returns settlement records showing how escrows were finalized,
    including transaction hashes and ledger entries.
    """
    engine = SettlementEngine()

    settlements = await engine.list_settlements(
        agent_id=agent_id,
        settlement_type=settlement_type,
        limit=limit,
    )

    return SettlementListResponse(
        settlements=[SettlementResponse.from_settlement(s) for s in settlements],
        total=len(settlements),
    )


@router.get("/settlements/{escrow_id}", response_model=SettlementResponse)
async def get_settlement(
    escrow_id: str,
    principal: Principal = Depends(require_principal),
) -> SettlementResponse:
    """
    Get settlement details for a specific escrow.
    """
    engine = SettlementEngine()

    settlement = await engine.get_settlement(escrow_id)
    if not settlement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No settlement found for escrow {escrow_id}",
        )

    return SettlementResponse.from_settlement(settlement)
