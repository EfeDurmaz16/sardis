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
# Signature verification (EIP-3009 / EIP-712) — fail-closed
# ---------------------------------------------------------------------------

def _verify_x402_signature(payload, challenge) -> tuple[bool, str | None]:
    """Verify the x402 payload's EIP-3009 signature against its challenge.

    Returns (True, None) only when the signature recovers to the claimed payer,
    the authorization binds to the challenge's payee + amount, and timing is
    valid. Any inconsistency → (False, reason). Fail-closed: a missing
    authorization or signature is a rejection, not a pass.
    """
    from sardis.protocol.x402_erc3009 import (
        ERC3009Authorization,
        verify_transfer_authorization,
    )

    auth = payload.authorization or {}
    if not isinstance(auth, dict) or not auth:
        return False, "x402_authorization_missing"
    if not payload.signature:
        return False, "x402_signature_missing"

    # Required ERC-3009 authorization fields (canonical x402 wire format).
    try:
        from_address = str(auth["from"])
        to_address = str(auth["to"])
        value = int(auth["value"])
        valid_after = int(auth.get("validAfter", auth.get("valid_after", 0)))
        valid_before = int(auth["validBefore"] if "validBefore" in auth else auth["valid_before"])
        nonce = str(auth["nonce"])
    except (KeyError, TypeError, ValueError):
        return False, "x402_authorization_malformed"

    # Bind the signed authorization to the challenge it claims to satisfy.
    if from_address.lower() != payload.payer_address.lower():
        return False, "x402_authorization_from_mismatch"
    if to_address.lower() != challenge.payee_address.lower():
        return False, "x402_authorization_to_mismatch"
    if str(value) != str(challenge.amount):
        return False, "x402_authorization_value_mismatch"

    erc_auth = ERC3009Authorization(
        from_address=from_address,
        to_address=to_address,
        value=value,
        valid_after=valid_after,
        valid_before=valid_before,
        nonce=nonce,
    )

    ok, reason = verify_transfer_authorization(
        erc_auth,
        payload.signature,
        network=challenge.network,
        expected_payer=payload.payer_address,
    )
    if not ok:
        return False, f"x402_signature_invalid:{reason}"
    return True, None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/verify", response_model=X402VerifyPayloadResponse)
async def verify_x402_payload(request: X402VerifyPayloadRequest):
    """Verify an x402 payment payload (unauthenticated — anyone can verify)."""
    try:
        from sardis.protocol.x402 import (
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

    # Field-level checks (expiry / nonce / amount / payment_id).
    result = verify_payment_payload(payload=payload, challenge=challenge)

    # Real EIP-3009 signature verification (fail-closed, MANDATORY on /verify).
    # The x402 payment proof is an EIP-712-signed USDC TransferWithAuthorization;
    # we recover the signer from the signature and bind it to the claimed payer
    # AND to the challenge's payee/amount/network. A forged or unsigned payload
    # is rejected here — there is no "accepted without signature" path.
    if result.accepted:
        sig_ok, sig_reason = _verify_x402_signature(payload, challenge)
        if not sig_ok:
            result = type(result)(False, sig_reason)

    # Persist to settlement store
    try:
        from sardis.protocol.x402_settlement import (
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
        from sardis.protocol.x402_settlement import (
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
    from sardis.chain.executor import ChainExecutor
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
        from sardis.protocol.x402_settlement import DatabaseSettlementStore
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
        from sardis.protocol.x402 import (
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
        from sardis.protocol.x402 import generate_challenge, serialize_challenge_header
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
