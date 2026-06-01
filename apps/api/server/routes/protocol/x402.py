"""x402 facilitator API router.

Provides endpoints for third parties to verify, settle, and inspect
x402 payments through Sardis's policy-gated infrastructure.

Two wire formats are served at this router:

- **Canonical x402 v1** (the real, interoperable format): ``POST /verify`` and
  ``POST /settle`` accept the spec body ``{x402Version, paymentPayload,
  paymentRequirements}`` and return ``{isValid, payer, invalidReason?}`` /
  ``{success, payer, transaction, network, errorReason?}``. ``GET /supported``
  returns ``{kinds:[...]}``. These route the canonical ``X-PAYMENT`` payload's
  EIP-3009 authorization through the existing ``verify_transfer_authorization``
  EIP-712 verifier (fail-closed). See ``sardis.protocol.x402_canonical``.
- **Sardis-native (legacy)**: the older flat ``{payment_id, challenge_header,
  ...}`` body is still accepted on ``/verify`` for backward compatibility; the
  endpoint sniffs the body shape and dispatches. New integrations should use the
  canonical shape.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
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
# Canonical x402 v1 verification (spec §6.1.2 + §7.1) — fail-closed
# ---------------------------------------------------------------------------

# EIP-712 USDC domain (name, version) per canonical network — the source of
# truth Sardis signs/recovers against. A PaymentRequirements.extra that
# disagrees is rejected; we never trust requirement-supplied domain (D2).
_CANONICAL_DOMAIN_BY_NETWORK = {
    "base": ("USD Coin", "2"),
    "base-sepolia": ("USDC", "2"),
    "ethereum": ("USD Coin", "2"),
    "polygon": ("USD Coin", "2"),
    "arbitrum": ("USD Coin", "2"),
    "optimism": ("USD Coin", "2"),
}


def _verify_canonical_payment(payload, requirements) -> tuple[bool, str | None, str | None]:
    """Verify a canonical x402 PaymentPayload against PaymentRequirements.

    Returns ``(is_valid, canonical_invalid_reason, payer_address)``. Fail-closed:
    any inconsistency returns ``(False, <canonical code>, payer_or_None)``.

    Routes the EIP-3009 ``authorization`` through the existing
    ``verify_transfer_authorization`` EIP-712 verifier (signer recovery + timing
    + binding). Money-path bindings enforced here:
      - scheme must be "exact"; network must be a Sardis-verifiable canonical id;
      - payload.network must equal requirements.network;
      - authorization.to == requirements.payTo (recipient binding);
      - authorization.value == requirements.maxAmountRequired (STRICT equality —
        see conformance caveat in the report; "exact" scheme, conservative);
      - requirements.extra.name/version (if present) must match Sardis's
        hardcoded USDC domain for the network (never trust client-supplied domain);
      - EIP-712 signature recovers to authorization.from.
    """
    from sardis.protocol.x402_canonical import (
        X402ErrorCode,
        canonical_invalid_reason,
        canonical_network_to_sardis,
    )
    from sardis.protocol.x402_erc3009 import (
        ERC3009Authorization,
        verify_transfer_authorization,
    )

    auth = payload.authorization
    payer = auth.from_

    # scheme / network on payload vs requirements.
    if requirements.scheme != "exact":
        return False, X402ErrorCode.UNSUPPORTED_SCHEME.value, payer
    if payload.scheme != requirements.scheme:
        return False, X402ErrorCode.INVALID_SCHEME.value, payer
    if payload.network != requirements.network:
        return False, X402ErrorCode.INVALID_NETWORK.value, payer

    # Resolve the Sardis network id for EIP-712 domain (fail-closed unknown).
    try:
        sardis_network = canonical_network_to_sardis(payload.network)
    except Exception:
        return False, X402ErrorCode.INVALID_NETWORK.value, payer

    # Recipient binding: authorization.to must equal payTo.
    if auth.to.lower() != requirements.pay_to.lower():
        return False, X402ErrorCode.RECIPIENT_MISMATCH.value, payer

    # Amount binding: STRICT equality (conservative money-path stance for the
    # "exact" scheme — EIP-3009 settles the signed value, so overpayment is not
    # silently accepted). Conformance caveat documented in report.
    try:
        value_int = int(auth.value)
        required_int = int(requirements.max_amount_required)
    except (TypeError, ValueError):
        return False, X402ErrorCode.INVALID_VALUE.value, payer
    if value_int != required_int:
        return False, X402ErrorCode.INVALID_VALUE.value, payer

    # Token EIP-712 domain cross-check (D2): never trust requirement-supplied
    # name/version — require it to match Sardis's hardcoded USDC domain.
    expected_domain = _CANONICAL_DOMAIN_BY_NETWORK.get(payload.network)
    extra = requirements.extra
    if isinstance(extra, dict) and ("name" in extra or "version" in extra):
        if expected_domain is None:
            return False, X402ErrorCode.INVALID_PAYMENT_REQUIREMENTS.value, payer
        exp_name, exp_version = expected_domain
        if str(extra.get("name")) != exp_name or str(extra.get("version")) != exp_version:
            return False, X402ErrorCode.INVALID_PAYMENT_REQUIREMENTS.value, payer

    # EIP-3009 / EIP-712 signature verification (timing + signer recovery +
    # signer == from). This is the existing, unchanged crypto.
    try:
        erc_auth = ERC3009Authorization(
            from_address=auth.from_,
            to_address=auth.to,
            value=value_int,
            valid_after=int(auth.valid_after),
            valid_before=int(auth.valid_before),
            nonce=auth.nonce,
        )
    except (TypeError, ValueError):
        return False, X402ErrorCode.INVALID_PAYLOAD.value, payer

    ok, reason = verify_transfer_authorization(
        erc_auth,
        payload.signature,
        network=sardis_network,
        expected_payer=payer,
    )
    if not ok:
        return False, canonical_invalid_reason(reason).value, payer
    return True, None, payer


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

class X402CanonicalVerifyResponse(BaseModel):
    isValid: bool  # noqa: N815 — canonical x402 field name
    payer: str | None = None
    invalidReason: str | None = None  # noqa: N815 — canonical x402 field name


class X402CanonicalSettleResponse(BaseModel):
    success: bool
    payer: str | None = None
    transaction: str = ""
    network: str = ""
    errorReason: str | None = None  # noqa: N815 — canonical x402 field name


def _is_canonical_body(body: Any) -> bool:
    """True if the request body is the canonical {paymentPayload, paymentRequirements} shape."""
    return isinstance(body, dict) and "paymentPayload" in body and "paymentRequirements" in body


def _parse_canonical_request(body: dict):
    """Parse a canonical /verify|/settle body into (PaymentPayload, PaymentRequirements).

    Raises X402WireError (mapped to a 400 by the caller) on malformed input.
    """
    from sardis.protocol.x402_canonical import (
        X402_VERSION,
        PaymentPayload,
        PaymentRequirements,
        X402ErrorCode,
        X402WireError,
    )

    version = body.get("x402Version")
    if version is not None and version != X402_VERSION:
        raise X402WireError(X402ErrorCode.INVALID_X402_VERSION, str(version))
    payload = PaymentPayload.from_dict(body["paymentPayload"])
    requirements = PaymentRequirements.from_dict(body["paymentRequirements"])
    return payload, requirements


@router.post("/verify")
async def verify_x402_payload(request: Request):
    """Verify an x402 payment payload (unauthenticated — anyone can verify).

    Accepts BOTH wire formats and dispatches on body shape:
    - Canonical x402 v1: ``{x402Version, paymentPayload, paymentRequirements}``
      → ``{isValid, payer, invalidReason?}`` (spec §7.1).
    - Sardis-native (legacy): ``{payment_id, challenge_header, ...}``
      → ``{accepted, payment_id, reason}``.
    """
    body = await request.json()

    if _is_canonical_body(body):
        from sardis.protocol.x402_canonical import X402WireError

        try:
            payload, requirements = _parse_canonical_request(body)
        except X402WireError as exc:
            # Malformed canonical input — fail-closed, surface the canonical code.
            return X402CanonicalVerifyResponse(isValid=False, invalidReason=exc.code.value)
        except (KeyError, TypeError):
            from sardis.protocol.x402_canonical import X402ErrorCode
            return X402CanonicalVerifyResponse(
                isValid=False, invalidReason=X402ErrorCode.INVALID_PAYLOAD.value
            )

        is_valid, invalid_reason, payer = _verify_canonical_payment(payload, requirements)
        return X402CanonicalVerifyResponse(
            isValid=is_valid, payer=payer, invalidReason=invalid_reason
        )

    # --- Legacy Sardis-native path ---
    try:
        legacy_request = X402VerifyPayloadRequest(**body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid x402 verify body: {exc}",
        )
    return await _verify_x402_payload_legacy(legacy_request)


async def _verify_x402_payload_legacy(request: X402VerifyPayloadRequest) -> X402VerifyPayloadResponse:
    """Legacy Sardis-native /verify (flat payment_id + challenge_header body)."""
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


@router.get("/supported")
async def supported_x402_kinds():
    """Canonical x402 facilitator capability advertisement (spec §7.3).

    Returns ``{kinds:[{x402Version, scheme, network}, ...]}`` for every network
    Sardis can verify (i.e. has a hardcoded EIP-712 USDC domain for).
    """
    from sardis.protocol.x402_canonical import supported_kinds

    return {"kinds": supported_kinds()}


@router.post("/settle")
async def settle_x402_payment(request: Request):
    """Settle an x402 payment. Accepts BOTH wire formats (body-sniffed).

    - Canonical x402 v1: ``{x402Version, paymentPayload, paymentRequirements}``.
      RE-VERIFIES the payload via the EIP-3009 verifier (mandatory, fail-closed)
      then broadcasts on-chain via the existing settler. Returns the canonical
      ``{success, payer, transaction, network, errorReason?}`` (spec §7.2).
    - Sardis-native (legacy): ``{payment_id}`` settles a previously persisted
      VERIFIED record.
    """
    body = await request.json()

    if _is_canonical_body(body):
        return await _settle_canonical(body)

    try:
        legacy_request = X402SettlePaymentRequest(**body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid x402 settle body: {exc}",
        )
    return await _settle_x402_payment_legacy(legacy_request)


async def _settle_canonical(body: dict) -> X402CanonicalSettleResponse:
    """Canonical stateless settle: re-verify (fail-closed) then broadcast on-chain."""
    from sardis.protocol.x402_canonical import X402ErrorCode, X402WireError

    try:
        payload, requirements = _parse_canonical_request(body)
    except X402WireError as exc:
        return X402CanonicalSettleResponse(
            success=False, transaction="", network="", errorReason=exc.code.value
        )
    except (KeyError, TypeError):
        return X402CanonicalSettleResponse(
            success=False, transaction="", network="",
            errorReason=X402ErrorCode.INVALID_PAYLOAD.value,
        )

    # MANDATORY re-verify before any broadcast (fail-closed money-path gate).
    is_valid, invalid_reason, payer = _verify_canonical_payment(payload, requirements)
    if not is_valid:
        return X402CanonicalSettleResponse(
            success=False,
            payer=payer,
            transaction="",
            network=payload.network,
            errorReason=invalid_reason,
        )

    # Broadcast via the existing settlement infra. Construct a verified
    # settlement record from the canonical payload and settle it on-chain.
    try:
        from sardis.chain.executor import ChainExecutor
        from sardis.protocol.x402 import X402Challenge, X402PaymentPayload
        from sardis.protocol.x402_canonical import canonical_network_to_sardis
        from sardis.protocol.x402_settlement import (
            DatabaseSettlementStore,
            X402Settlement,
            X402SettlementStatus,
            X402Settler,
        )
    except ImportError as exc:
        logger.warning("x402 canonical settle: settlement infra unavailable: %s", exc)
        return X402CanonicalSettleResponse(
            success=False, payer=payer, transaction="", network=payload.network,
            errorReason=X402ErrorCode.UNEXPECTED_SETTLE_ERROR.value,
        )

    try:
        sardis_network = canonical_network_to_sardis(payload.network)
        auth = payload.authorization
        challenge = X402Challenge(
            payment_id=f"x402c_{auth.nonce}",
            resource_uri=requirements.resource,
            amount=requirements.max_amount_required,
            currency="USDC",
            payee_address=requirements.pay_to,
            network=sardis_network,
            token_address=requirements.asset,
            expires_at=int(auth.valid_before),
            nonce=auth.nonce,
        )
        native_payload = X402PaymentPayload(
            payment_id=challenge.payment_id,
            payer_address=payer,
            amount=auth.value,
            nonce=auth.nonce,
            signature=payload.signature,
            authorization=auth.to_dict(),
        )
        settlement = X402Settlement(
            payment_id=challenge.payment_id,
            status=X402SettlementStatus.VERIFIED,
            challenge=challenge,
            payload=native_payload,
        )
        store = DatabaseSettlementStore()
        await store.save(settlement)
        settler = X402Settler(store=store, chain_executor=ChainExecutor())
        result = await settler.settle(settlement)
    except Exception as exc:
        logger.warning("x402 canonical settle failed: %s", exc)
        return X402CanonicalSettleResponse(
            success=False, payer=payer, transaction="", network=payload.network,
            errorReason=X402ErrorCode.UNEXPECTED_SETTLE_ERROR.value,
        )

    settled_ok = result.status == X402SettlementStatus.SETTLED
    return X402CanonicalSettleResponse(
        success=settled_ok,
        payer=payer,
        transaction=result.tx_hash or "",
        network=payload.network,
        errorReason=None if settled_ok else (
            result.error or X402ErrorCode.INVALID_TRANSACTION_STATE.value
        ),
    )


async def _settle_x402_payment_legacy(request: X402SettlePaymentRequest) -> X402SettlePaymentResponse:
    """Legacy Sardis-native settle: settle a persisted VERIFIED record by payment_id."""
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
