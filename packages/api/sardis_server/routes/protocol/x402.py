"""x402 facilitator API router.

Provides endpoints for third parties to verify, settle, and inspect
x402 payments through Sardis's policy-gated infrastructure.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["x402"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class X402VerifyPayloadRequest(BaseModel):
    payment_id: str
    payer_address: str
    amount: str
    nonce: str
    signature: str
    authorization: dict = Field(default_factory=dict)
    challenge_header: str = Field(description="Base64-encoded challenge from PaymentRequired header")


class X402VerifyPayloadResponse(BaseModel):
    accepted: bool
    payment_id: str
    reason: str | None = None


class X402SettlePaymentRequest(BaseModel):
    payment_id: str


class X402SettlePaymentResponse(BaseModel):
    payment_id: str
    status: str
    tx_hash: str | None = None
    settled_at: str | None = None
    error: str | None = None


class X402SettlementStatusResponse(BaseModel):
    payment_id: str
    status: str
    tx_hash: str | None = None
    settled_at: str | None = None
    error: str | None = None
    source: str = "facilitator"
    network: str = "base"
    amount: str | None = None
    currency: str = "USDC"


class X402DryRunRequest(BaseModel):
    payment_id: str
    payer_address: str
    amount: str
    nonce: str
    challenge_header: str


class X402DryRunResponse(BaseModel):
    would_succeed: bool
    payment_id: str
    failure_reasons: list[str] = Field(default_factory=list)


class X402ChallengeGenerateRequest(BaseModel):
    resource_uri: str
    amount: str
    currency: str = "USDC"
    network: str = "base"
    payee_address: str
    ttl_seconds: int = Field(default=300, ge=30, le=3600)


class X402ChallengeGenerateResponse(BaseModel):
    payment_id: str
    resource_uri: str
    amount: str
    currency: str
    network: str
    payee_address: str
    expires_at: int
    nonce: str
    challenge_header: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/verify", response_model=X402VerifyPayloadResponse)
async def verify_x402_payload(request: X402VerifyPayloadRequest):
    """Verify an x402 payment payload (unauthenticated — anyone can verify)."""
    try:
        from sardis_protocol.x402 import (
            X402PaymentPayload,
            parse_challenge_header,
            verify_payment_payload,
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="x402 protocol module not available",
        )

    try:
        challenge = parse_challenge_header(request.challenge_header)
    except ValueError as e:
        return X402VerifyPayloadResponse(
            accepted=False,
            payment_id=request.payment_id,
            reason=f"invalid_challenge: {e}",
        )

    payload = X402PaymentPayload(
        payment_id=request.payment_id,
        payer_address=request.payer_address,
        amount=request.amount,
        nonce=request.nonce,
        signature=request.signature,
        authorization=request.authorization,
    )

    result = verify_payment_payload(payload=payload, challenge=challenge)

    # Persist to settlement store
    try:
        from sardis_protocol.x402_settlement import (
            DatabaseSettlementStore,
            X402Settlement,
            X402SettlementStatus,
        )

        settlement = X402Settlement(
            payment_id=request.payment_id,
            status=X402SettlementStatus.VERIFIED if result.accepted else X402SettlementStatus.FAILED,
            challenge=challenge,
            payload=payload,
            error=result.reason if not result.accepted else None,
        )
        store = DatabaseSettlementStore()
        await store.save(settlement)
    except Exception as e:
        logger.warning("Failed to persist x402 verification: %s", e)

    return X402VerifyPayloadResponse(
        accepted=result.accepted,
        payment_id=request.payment_id,
        reason=result.reason,
    )


@router.post("/settle", response_model=X402SettlePaymentResponse)
async def settle_x402_payment(request: X402SettlePaymentRequest):
    """Settle a verified x402 payment on-chain (requires API key)."""
    try:
        from sardis_protocol.x402_settlement import (
            DatabaseSettlementStore,
            X402SettlementStatus,
            X402Settler,
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="x402 settlement module not available",
        )

    store = DatabaseSettlementStore()
    settlement = await store.get(request.payment_id)
    if not settlement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Settlement not found",
        )

    if settlement.status != X402SettlementStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Settlement status is {settlement.status.value}, expected 'verified'",
        )

    # Use chain executor from app state if available
    from sardis_chain.executor import ChainExecutor
    settler = X402Settler(store=store, chain_executor=ChainExecutor())
    result = await settler.settle(settlement)

    return X402SettlePaymentResponse(
        payment_id=result.payment_id,
        status=result.status.value,
        tx_hash=result.tx_hash,
        settled_at=result.settled_at.isoformat() if result.settled_at else None,
        error=result.error,
    )


@router.get("/settlements/{payment_id}", response_model=X402SettlementStatusResponse)
async def get_x402_settlement(payment_id: str):
    """Get settlement status by payment ID."""
    try:
        from sardis_protocol.x402_settlement import DatabaseSettlementStore
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="x402 settlement module not available",
        )

    store = DatabaseSettlementStore()
    settlement = await store.get(payment_id)
    if not settlement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Settlement not found",
        )

    return X402SettlementStatusResponse(
        payment_id=settlement.payment_id,
        status=settlement.status.value,
        tx_hash=settlement.tx_hash,
        settled_at=settlement.settled_at.isoformat() if settlement.settled_at else None,
        error=settlement.error,
    )


@router.post("/dry-run", response_model=X402DryRunResponse)
async def dry_run_x402_payment(request: X402DryRunRequest):
    """Simulate an x402 payment without executing."""
    try:
        from sardis_protocol.x402 import (
            X402PaymentPayload,
            parse_challenge_header,
            verify_payment_payload,
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="x402 protocol module not available",
        )

    try:
        challenge = parse_challenge_header(request.challenge_header)
    except ValueError as e:
        return X402DryRunResponse(
            would_succeed=False,
            payment_id=request.payment_id,
            failure_reasons=[f"invalid_challenge: {e}"],
        )

    payload = X402PaymentPayload(
        payment_id=request.payment_id,
        payer_address=request.payer_address,
        amount=request.amount,
        nonce=request.nonce,
        signature="",  # Dry run skips signature verification
    )

    result = verify_payment_payload(payload=payload, challenge=challenge)

    failure_reasons = []
    if not result.accepted and result.reason:
        # Ignore signature failures in dry-run mode
        if result.reason != "x402_signature_invalid":
            failure_reasons.append(result.reason)

    return X402DryRunResponse(
        would_succeed=len(failure_reasons) == 0,
        payment_id=request.payment_id,
        failure_reasons=failure_reasons,
    )


@router.post("/challenges", response_model=X402ChallengeGenerateResponse)
async def generate_x402_challenge(request: X402ChallengeGenerateRequest):
    """Generate an x402 payment challenge."""
    try:
        from sardis_protocol.x402 import generate_challenge, serialize_challenge_header
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="x402 protocol module not available",
        )

    challenge_response = generate_challenge(
        resource_uri=request.resource_uri,
        amount=request.amount,
        currency=request.currency,
        payee_address=request.payee_address,
        network=request.network,
        ttl_seconds=request.ttl_seconds,
    )
    challenge = challenge_response.challenge
    header = serialize_challenge_header(challenge)

    return X402ChallengeGenerateResponse(
        payment_id=challenge.payment_id,
        resource_uri=challenge.resource_uri,
        amount=challenge.amount,
        currency=challenge.currency,
        network=challenge.network,
        payee_address=challenge.payee_address,
        expires_at=challenge.expires_at,
        nonce=challenge.nonce,
        challenge_header=header,
    )
