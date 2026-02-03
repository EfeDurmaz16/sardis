"""Transaction status and gas estimation API routes."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_chain.executor import ChainExecutor, TransactionStatus, CHAIN_CONFIGS, STABLECOIN_ADDRESSES


router = APIRouter(tags=["transactions"])


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
    block_number: Optional[int] = None
    confirmations: Optional[int] = None
    explorer_url: Optional[str] = None


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
    reference: Optional[str] = Field(None, description="Optional reference ID for this transfer")


class BatchTransferRequest(BaseModel):
    """Request for batch transfers."""
    wallet_id: str = Field(..., description="Wallet ID to transfer from")
    chain: str = Field(default="base", description="Chain to execute on")
    token: str = Field(default="USDC", description="Token to transfer")
    transfers: List[BatchTransferItem] = Field(..., description="List of transfers to execute")


class BatchTransferItemResult(BaseModel):
    """Result of a single transfer in a batch."""
    reference: Optional[str] = None
    destination: str
    amount: str
    tx_hash: Optional[str] = None
    status: str  # "success", "failed", "pending"
    error: Optional[str] = None


class BatchTransferResponse(BaseModel):
    """Response for batch transfer."""
    batch_id: str
    wallet_id: str
    chain: str
    token: str
    total_transfers: int
    successful: int
    failed: int
    results: List[BatchTransferItemResult]


# Dependencies

class TransactionDependencies:
    """Dependencies for transaction routes."""
    def __init__(self, chain_executor: ChainExecutor):
        self.chain_executor = chain_executor


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
    from sardis_v2_core.mandates import PaymentMandate
    
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
    
    # Create a mock mandate for gas estimation
    from sardis_v2_core.mandates import VCProof
    import time
    
    proof = VCProof(
        verification_method="did:key:system#key-1",
        created="2025-01-01T00:00:00Z",
        proof_value="mock_signature",
    )
    
    mandate = PaymentMandate(
        mandate_id="gas_estimate",
        mandate_type="payment",
        issuer="system",
        subject="system",
        expires_at=int(time.time()) + 300,
        nonce="gas_estimate_nonce",
        proof=proof,
        domain="sardis.network",
        purpose="checkout",
        destination=request.destination,
        amount_minor=int(request.amount),
        token=request.token,
        chain=request.chain,
        audit_hash="gas_estimate_hash",
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
):
    """Get the status of a transaction."""
    if chain not in CHAIN_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported chain: {chain}",
        )
    
    try:
        tx_status = await deps.chain_executor.get_transaction_status(tx_hash, chain)
        
        # Build explorer URL
        explorer = CHAIN_CONFIGS[chain]["explorer"]
        explorer_url = f"{explorer}/tx/{tx_hash}"
        
        return TransactionStatusResponse(
            tx_hash=tx_hash,
            chain=chain,
            status=tx_status.value,
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
    request: BatchTransferRequest,
    deps: TransactionDependencies = Depends(get_deps),
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
    import uuid
    import time
    from sardis_v2_core.mandates import PaymentMandate, VCProof

    # Validate inputs
    if not request.transfers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one transfer required",
        )

    if len(request.transfers) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 transfers per batch",
        )

    if request.chain not in CHAIN_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported chain: {request.chain}",
        )

    supported_tokens = STABLECOIN_ADDRESSES.get(request.chain, {})
    if request.token not in supported_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token {request.token} not supported on {request.chain}",
        )

    # Generate batch ID
    batch_id = f"batch_{uuid.uuid4().hex[:16]}"

    # Execute transfers
    results = []
    successful = 0
    failed = 0

    for idx, transfer in enumerate(request.transfers):
        try:
            # Create mandate for this transfer
            proof = VCProof(
                verification_method=f"did:key:{request.wallet_id}#key-1",
                created=f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
                proof_value=f"batch_transfer_{batch_id}_{idx}",
            )

            mandate = PaymentMandate(
                mandate_id=f"{batch_id}_tx_{idx}",
                mandate_type="payment",
                issuer=request.wallet_id,
                subject=request.wallet_id,
                expires_at=int(time.time()) + 300,
                nonce=f"{batch_id}_{idx}",
                proof=proof,
                domain="sardis.network",
                purpose="batch_transfer",
                destination=transfer.destination,
                amount_minor=int(transfer.amount),
                token=request.token,
                chain=request.chain,
                audit_hash=f"batch_{batch_id}_{idx}",
            )

            # Execute transfer
            receipt = await deps.chain_executor.execute_mandate(mandate)

            results.append(BatchTransferItemResult(
                reference=transfer.reference,
                destination=transfer.destination,
                amount=transfer.amount,
                tx_hash=receipt.tx_hash,
                status="success",
            ))
            successful += 1

        except Exception as e:
            results.append(BatchTransferItemResult(
                reference=transfer.reference,
                destination=transfer.destination,
                amount=transfer.amount,
                tx_hash=None,
                status="failed",
                error=str(e),
            ))
            failed += 1

    return BatchTransferResponse(
        batch_id=batch_id,
        wallet_id=request.wallet_id,
        chain=request.chain,
        token=request.token,
        total_transfers=len(request.transfers),
        successful=successful,
        failed=failed,
        results=results,
    )
