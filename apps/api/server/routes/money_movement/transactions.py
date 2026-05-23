"""Transaction status and gas estimation API routes."""
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sardis_chain.executor import (
    CHAIN_CONFIGS,
    STABLECOIN_ADDRESSES,
    ChainExecutor,
)

from server.authz import Principal, require_principal
from server.canonical_state_machine import normalize_stablecoin_event
from server.idempotency import get_idempotency_key, run_idempotent

router = APIRouter(dependencies=[Depends(require_principal)], tags=["transactions"])


# Request/Response Models

class GasEstimateRequest(BaseModel):
    """Request for gas estimation."""
    chain: str = Field(default="base_sepolia", description="Chain to estimate gas for")
    token: str = Field(default="USDC", description="Token to transfer")
    amount: str = Field(..., description="Amount in minor units (e.g., cents for USDC)")
    destination: str = Field(..., description="Destination address")


class GasEstimateResponse(BaseModel):
    """Gas estimation response."""
    gas_limit: int
    gas_price_gwei: str
    max_fee_gwei: str
    max_priority_fee_gwei: str
    estimated_cost_wei: int
    estimated_cost_eth: str


class TransactionStatusResponse(BaseModel):
    """Transaction status response."""
    tx_hash: str
    chain: str
    status: str
    block_number: int | None = None
    confirmations: int | None = None
    explorer_url: str | None = None


class ChainInfoResponse(BaseModel):
    """Chain information response."""
    name: str
    chain_id: int
    rpc_url: str
    explorer: str
    native_token: str
    supported_tokens: list[str]


class SupportedChainsResponse(BaseModel):
    """List of supported chains."""
    chains: list[ChainInfoResponse]


class BatchTransferItem(BaseModel):
    """Single transfer in a batch."""
    destination: str = Field(..., description="Destination address")
    amount: str = Field(..., description="Amount in minor units (e.g., cents for USDC)")
    reference: str | None = Field(None, description="Optional reference ID for this transfer")


class BatchTransferRequest(BaseModel):
    """Request for batch transfers."""
    wallet_id: str = Field(..., description="Wallet ID to transfer from")
    chain: str = Field(default="base", description="Chain to execute on")
    token: str = Field(default="USDC", description="Token to transfer")
    transfers: list[BatchTransferItem] = Field(..., description="List of transfers to execute")


class BatchTransferItemResult(BaseModel):
    """Result of a single transfer in a batch."""
    reference: str | None = None
    destination: str
    amount: str
    tx_hash: str | None = None
    status: str  # "success", "failed", "pending"
    error: str | None = None


class BatchTransferResponse(BaseModel):
    """Response for batch transfer."""
    batch_id: str
    wallet_id: str
    chain: str
    token: str
    total_transfers: int
    successful: int
    failed: int
    results: list[BatchTransferItemResult]


# Dependencies

class TransactionDependencies:
    """Dependencies for transaction routes."""
    def __init__(self, chain_executor: ChainExecutor, canonical_repo=None):
        self.chain_executor = chain_executor
        self.canonical_repo = canonical_repo


def get_deps() -> TransactionDependencies:
    """Dependency injection placeholder."""
    raise NotImplementedError("Must be overridden")


# Routes

@router.get("/chains", response_model=SupportedChainsResponse)
async def list_supported_chains():
    """List all supported blockchain networks."""
    chains = []
    for name, config in CHAIN_CONFIGS.items():
        tokens = list(STABLECOIN_ADDRESSES.get(name, {}).keys())
        chains.append(ChainInfoResponse(
            name=name,
            chain_id=config["chain_id"],
            rpc_url=config["rpc_url"],
            explorer=config["explorer"],
            native_token=config["native_token"],
            supported_tokens=tokens,
        ))
    return SupportedChainsResponse(chains=chains)


@router.post("/estimate-gas", response_model=GasEstimateResponse)
async def estimate_gas(
    request: GasEstimateRequest,
    deps: TransactionDependencies = Depends(get_deps),
):
    """Estimate gas for a stablecoin transfer."""
    from sardis.core.mandates import PaymentMandate

    # Validate chain
    if request.chain not in CHAIN_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported chain: {request.chain}. Supported: {list(CHAIN_CONFIGS.keys())}",
        )

    # Validate token
    supported_tokens = STABLECOIN_ADDRESSES.get(request.chain, {})
    if request.token not in supported_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token {request.token} not supported on {request.chain}. Supported: {list(supported_tokens.keys())}",
        )

    # Create a sentinel mandate for gas estimation (bypasses proof verification)
    import hashlib
    import time

    from sardis.core.mandates import VCProof

    _gas_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _gas_nonce = hashlib.sha256(f"gas_estimate:{request.chain}:{request.destination}:{request.amount}".encode()).hexdigest()[:16]
    proof = VCProof(
        verification_method="did:sardis:system#gas-estimate",
        created=_gas_ts,
        proof_purpose="gas_estimation",
        proof_value=hashlib.sha256(f"gas:{_gas_nonce}:{_gas_ts}".encode()).hexdigest(),
    )

    mandate = PaymentMandate(
        mandate_id=f"gas_estimate_{_gas_nonce}",
        mandate_type="payment",
        issuer="system",
        subject="system",
        expires_at=int(time.time()) + 300,
        nonce=_gas_nonce,
        proof=proof,
        domain="sardis.sh",
        purpose="gas_estimation",
        destination=request.destination,
        amount_minor=int(request.amount),
        token=request.token,
        chain=request.chain,
        audit_hash=hashlib.sha256(f"gas:{_gas_nonce}".encode()).hexdigest(),
    )

    try:
        estimate = await deps.chain_executor.estimate_gas(mandate)

        return GasEstimateResponse(
            gas_limit=estimate.gas_limit,
            gas_price_gwei=str(estimate.gas_price_gwei),
            max_fee_gwei=str(estimate.max_fee_gwei),
            max_priority_fee_gwei=str(estimate.max_priority_fee_gwei),
            estimated_cost_wei=estimate.estimated_cost_wei,
            estimated_cost_eth=str(Decimal(estimate.estimated_cost_wei) / Decimal(10**18)),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gas estimation failed: {str(e)}",
        )


@router.get("/status/{tx_hash}", response_model=TransactionStatusResponse)
async def get_transaction_status(
    tx_hash: str,
    chain: str = "base_sepolia",
    deps: TransactionDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Get the status of a transaction."""
    if chain not in CHAIN_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported chain: {chain}",
        )

    try:
        tx_status = await deps.chain_executor.get_transaction_status(tx_hash, chain)
        status_value = tx_status.value

        # Build explorer URL
        explorer = CHAIN_CONFIGS[chain]["explorer"]
        explorer_url = f"{explorer}/tx/{tx_hash}"

        if deps.canonical_repo is not None:
            normalized_status = str(status_value).strip().lower()
            canonical_state = "processing"
            canonical_event_type = "stablecoin.tx.pending"
            if normalized_status in {"confirmed", "success", "succeeded"}:
                canonical_state = "settled"
                canonical_event_type = "stablecoin.tx.confirmed"
            elif normalized_status in {"failed", "reverted", "dropped"}:
                canonical_state = "failed"
                canonical_event_type = "stablecoin.tx.failed"
            event = normalize_stablecoin_event(
                organization_id=principal.organization_id,
                rail="stablecoin_tx",
                reference=tx_hash,
                provider_event_id=f"{tx_hash}:{normalized_status}",
                provider_event_type=f"ONCHAIN_TX_STATUS_{normalized_status.upper()}",
                canonical_event_type=canonical_event_type,
                canonical_state=canonical_state,
                amount_minor=None,
                currency="USDC",
                metadata={"chain": chain, "status": normalized_status},
                raw_payload={"tx_hash": tx_hash, "chain": chain, "status": normalized_status},
            )
            await deps.canonical_repo.ingest_event(
                event,
                drift_tolerance_minor=0,
            )

        return TransactionStatusResponse(
            tx_hash=tx_hash,
            chain=chain,
            status=status_value,
            explorer_url=explorer_url,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transaction status: {str(e)}",
        )


@router.get("/tokens/{chain}")
async def list_chain_tokens(chain: str):
    """List supported tokens for a chain."""
    if chain not in CHAIN_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported chain: {chain}",
        )

    tokens = STABLECOIN_ADDRESSES.get(chain, {})
    return {
        "chain": chain,
        "tokens": [
            {"symbol": symbol, "address": address}
            for symbol, address in tokens.items()
        ],
    }


@router.post("/batch", response_model=BatchTransferResponse)
async def batch_transfer(
    body: BatchTransferRequest,
    request: Request,
    deps: TransactionDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    idem_key = get_idempotency_key(request)
    if idem_key:
        async def _execute_idempotent() -> tuple[int, Any]:
            response = await _execute_batch_transfer(body=body, deps=deps)
            return status.HTTP_200_OK, response.model_dump(mode="json")

        return await run_idempotent(
            request=request,
            principal=principal,
            operation="transactions.batch",
            key=idem_key,
            payload=body.model_dump(mode="json"),
            fn=_execute_idempotent,
        )

    return await _execute_batch_transfer(body=body, deps=deps)


async def _execute_batch_transfer(
    *,
    body: BatchTransferRequest,
    deps: TransactionDependencies,
):
    """
    Execute multiple transfers in a batch.

    This endpoint allows sending multiple transfers atomically or sequentially.
    Each transfer is validated and executed independently. If one fails, others
    may still succeed (fail-safe behavior).

    Use this for:
    - Payroll distributions
    - Bulk payments to multiple recipients
    - Multi-recipient airdrops
    """
    import time
    import uuid

    from sardis.core.mandates import PaymentMandate, VCProof

    # Validate inputs
    if not body.transfers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one transfer required",
        )

    if len(body.transfers) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 transfers per batch",
        )

    if body.chain not in CHAIN_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported chain: {body.chain}",
        )

    supported_tokens = STABLECOIN_ADDRESSES.get(body.chain, {})
    if body.token not in supported_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token {body.token} not supported on {body.chain}",
        )

    # Generate batch ID
    batch_id = f"batch_{uuid.uuid4().hex[:16]}"

    # Build mandates up-front
    mandates_with_transfers: list[tuple[int, BatchTransferItem, PaymentMandate]] = []
    for idx, transfer in enumerate(body.transfers):
        proof = VCProof(
            verification_method=f"did:key:{body.wallet_id}#key-1",
            created=f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
            proof_value=f"batch_transfer_{batch_id}_{idx}",
        )
        mandate = PaymentMandate(
            mandate_id=f"{batch_id}_tx_{idx}",
            mandate_type="payment",
            issuer=body.wallet_id,
            subject=body.wallet_id,
            expires_at=int(time.time()) + 300,
            nonce=f"{batch_id}_{idx}",
            proof=proof,
            domain="sardis.sh",
            purpose="batch_transfer",
            destination=transfer.destination,
            amount_minor=int(transfer.amount),
            token=body.token,
            chain=body.chain,
            audit_hash=f"batch_{batch_id}_{idx}",
        )
        mandates_with_transfers.append((idx, transfer, mandate))

    # Execute transfers concurrently with bounded concurrency
    sem = asyncio.Semaphore(10)

    async def _execute_one(
        idx: int, transfer: BatchTransferItem, mandate: PaymentMandate
    ) -> BatchTransferItemResult:
        async with sem:
            try:
                receipt = await deps.chain_executor.execute_mandate(mandate)
                return BatchTransferItemResult(
                    reference=transfer.reference,
                    destination=transfer.destination,
                    amount=transfer.amount,
                    tx_hash=receipt.tx_hash,
                    status="success",
                )
            except Exception as e:
                return BatchTransferItemResult(
                    reference=transfer.reference,
                    destination=transfer.destination,
                    amount=transfer.amount,
                    tx_hash=None,
                    status="failed",
                    error=str(e),
                )

    results = await asyncio.gather(
        *[_execute_one(idx, t, m) for idx, t, m in mandates_with_transfers]
    )

    successful = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "failed")

    return BatchTransferResponse(
        batch_id=batch_id,
        wallet_id=body.wallet_id,
        chain=body.chain,
        token=body.token,
        total_transfers=len(body.transfers),
        successful=successful,
        failed=failed,
        results=results,
    )
