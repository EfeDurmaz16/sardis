"""Batch Payment API — atomic multi-transfer via Tempo type 0x76.

Accepts an array of transfers and executes them as a single
atomic batch transaction on Tempo. All transfers succeed or
all fail — no partial settlement.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(dependencies=[Depends(require_principal)])
logger = logging.getLogger(__name__)


class TransferItem(BaseModel):
    to: str = Field(..., description="Recipient address")
    amount: Decimal = Field(..., gt=0)
    token: str = Field(default="USDC")
    memo: str | None = Field(default=None, max_length=64, description="32-byte memo (hex or UTF-8)")


class BatchPaymentRequest(BaseModel):
    transfers: list[TransferItem] = Field(..., min_length=1, max_length=50)
    chain: str = Field(default="tempo")
    mandate_id: str | None = Field(default=None, description="Optional spending mandate to validate against")


class BatchTransferResult(BaseModel):
    index: int
    to: str
    amount: str
    token: str
    status: str  # "included"


class BatchPaymentResponse(BaseModel):
    tx_hash: str
    chain: str
    transfer_count: int
    total_amount: str
    status: str  # "submitted", "confirmed", "failed"
    transfers: list[BatchTransferResult]


@router.post(
    "/payments/batch",
    response_model=BatchPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute atomic batch payment (Tempo type 0x76)",
)
async def batch_payment(
    req: BatchPaymentRequest,
    principal: Principal = Depends(require_principal),
) -> BatchPaymentResponse:
    """Execute multiple transfers in a single atomic transaction.

    On Tempo, uses type 0x76 batch transactions. All transfers
    succeed or all fail — no partial settlement.
    """
    if req.chain != "tempo":
        raise HTTPException(
            status_code=422,
            detail="Batch payments are only supported on Tempo (type 0x76)",
        )

    # Validate mandate if provided
    if req.mandate_id:
        from sardis_v2_core.database import Database
        mandate = await Database.fetchrow(
            "SELECT * FROM spending_mandates WHERE id = $1 AND org_id = $2 AND status = 'active'",
            req.mandate_id, principal.org_id,
        )
        if not mandate:
            raise HTTPException(status_code=404, detail="Active mandate not found")

        total = sum(t.amount for t in req.transfers)
        if mandate["amount_per_tx"] is not None and total > mandate["amount_per_tx"]:
            raise HTTPException(
                status_code=422,
                detail=f"Batch total {total} exceeds mandate per-tx limit {mandate['amount_per_tx']}",
            )

    # Build batch transfer list for Tempo executor
    transfer_dicts = []
    for t in req.transfers:
        from sardis_v2_core.tokens import TOKEN_REGISTRY, TokenType
        token_meta = TOKEN_REGISTRY.get(TokenType(t.token))
        token_addr = token_meta.contract_addresses.get("tempo", "") if token_meta else ""
        if not token_addr:
            raise HTTPException(status_code=422, detail=f"Token {t.token} not available on Tempo")

        memo_bytes = None
        if t.memo:
            memo_bytes = t.memo.encode("utf-8")[:32]

        transfer_dicts.append({
            "token": token_addr,
            "to": t.to,
            "amount": token_meta.to_raw_amount(t.amount) if token_meta else int(t.amount * 10**6),
            "memo": memo_bytes,
        })

    # Execute via TempoExecutor
    from sardis_chain.tempo.executor import TempoExecutor
    executor = TempoExecutor()
    receipt = await executor.execute_batch_transfers(transfer_dicts)

    total_amount = sum(t.amount for t in req.transfers)
    results = [
        BatchTransferResult(
            index=i,
            to=t.to,
            amount=str(t.amount),
            token=t.token,
            status="included",
        )
        for i, t in enumerate(req.transfers)
    ]

    logger.info(
        "Batch payment: %d transfers, %s total, tx=%s",
        len(req.transfers), total_amount, receipt.tx_hash,
    )

    return BatchPaymentResponse(
        tx_hash=receipt.tx_hash,
        chain=req.chain,
        transfer_count=len(req.transfers),
        total_amount=str(total_amount),
        status="confirmed" if receipt.status else "failed",
        transfers=results,
    )
