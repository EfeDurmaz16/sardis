"""Compliance API endpoints for KYC and Sanctions screening."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Optional, List

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_admin_principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])
public_router = APIRouter()


# ============================================================================
# Webhook Security Configuration
# ============================================================================

class WebhookSecurityConfig:
    """
    Configuration for webhook signature verification.

    CRITICAL SECURITY: Webhook signature verification is mandatory.
    Unverified webhooks MUST be rejected to prevent spoofing attacks.
    """

    # Persona webhook settings
    PERSONA_SIGNATURE_HEADER = "Persona-Signature"
    PERSONA_TIMESTAMP_HEADER = "Persona-Signature-Timestamp"

    # Maximum age for webhook timestamps (5 minutes)
    MAX_TIMESTAMP_AGE_SECONDS = 300

    # Minimum webhook secret length
    MIN_SECRET_LENGTH = 32


def get_persona_webhook_secret() -> Optional[str]:
    """
    Get Persona webhook secret from environment.

    Returns None if not configured, which will cause webhooks to be rejected.
    """
    secret = os.getenv("PERSONA_WEBHOOK_SECRET")
    if secret and len(secret) < WebhookSecurityConfig.MIN_SECRET_LENGTH:
        logger.error(
            f"SECURITY: Persona webhook secret is too short "
            f"(minimum {WebhookSecurityConfig.MIN_SECRET_LENGTH} characters)"
        )
        return None
    return secret


def verify_persona_webhook_signature(
    payload: bytes,
    signature: str,
    timestamp: str,
    secret: str,
) -> tuple[bool, Optional[str]]:
    """
    Verify Persona webhook signature using HMAC-SHA256.

    Persona signs webhooks using the format:
    HMAC-SHA256(timestamp + "." + payload, secret)

    The signature header contains: t=timestamp,v1=signature

    Args:
        payload: Raw request body
        signature: Value of Persona-Signature header
        timestamp: Value of Persona-Signature-Timestamp header (or from signature)
        secret: Webhook secret

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Parse signature header (format: t=timestamp,v1=signature)
        sig_parts = {}
        for part in signature.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                sig_parts[key.strip()] = value.strip()

        # Extract timestamp and signature value
        sig_timestamp = sig_parts.get("t") or timestamp
        sig_value = sig_parts.get("v1", "")

        if not sig_timestamp:
            return False, "Missing timestamp in signature"

        if not sig_value:
            return False, "Missing signature value"

        # Validate timestamp freshness to prevent replay attacks
        try:
            ts = int(sig_timestamp)
            current_time = int(time.time())
            age = current_time - ts

            if age > WebhookSecurityConfig.MAX_TIMESTAMP_AGE_SECONDS:
                logger.warning(
                    f"Persona webhook rejected: timestamp too old ({age} seconds)"
                )
                return False, f"Webhook timestamp too old ({age} seconds)"

            if age < -60:  # Allow 1 minute clock skew
                logger.warning(
                    f"Persona webhook rejected: timestamp in future ({-age} seconds)"
                )
                return False, "Webhook timestamp is in the future"

        except ValueError:
            return False, "Invalid timestamp format"

        # Compute expected signature
        # Persona format: timestamp.payload
        signed_payload = f"{sig_timestamp}.".encode() + payload
        expected_signature = hmac.new(
            secret.encode(),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(sig_value, expected_signature):
            logger.warning("Persona webhook signature verification failed")
            return False, "Invalid signature"

        return True, None

    except Exception as e:
        logger.error(f"Error verifying Persona webhook signature: {e}")
        return False, f"Signature verification error: {str(e)}"


async def verify_persona_webhook(
    request: Request,
    persona_signature: Optional[str] = Header(None, alias="Persona-Signature"),
    persona_timestamp: Optional[str] = Header(None, alias="Persona-Signature-Timestamp"),
) -> bytes:
    """
    FastAPI dependency to verify Persona webhook signature.

    SECURITY: This dependency MUST be used for all Persona webhook endpoints.
    It will reject any request without a valid HMAC signature.

    Raises:
        HTTPException 401: If signature is missing or invalid
        HTTPException 500: If webhook secret is not configured
    """
    # Get webhook secret
    secret = get_persona_webhook_secret()
    if not secret:
        logger.error(
            "SECURITY: Persona webhook received but PERSONA_WEBHOOK_SECRET not configured"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook verification not configured",
        )

    # Check for signature header
    if not persona_signature:
        logger.warning("Persona webhook rejected: missing signature header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature",
        )

    # Read raw body for signature verification
    body = await request.body()

    # Verify signature
    is_valid, error_msg = verify_persona_webhook_signature(
        payload=body,
        signature=persona_signature,
        timestamp=persona_timestamp or "",
        secret=secret,
    )

    if not is_valid:
        logger.warning(f"Persona webhook signature invalid: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg or "Invalid webhook signature",
        )

    logger.info("Persona webhook signature verified successfully")
    return body


# ============================================================================
# Request/Response Models
# ============================================================================

class KYCVerificationRequest(BaseModel):
    """Request to create a KYC verification."""

    agent_id: str = Field(..., description="Agent ID to verify")
    name_first: Optional[str] = Field(None, description="First name")
    name_last: Optional[str] = Field(None, description="Last name")
    email: Optional[str] = Field(None, description="Email address")


class KYCStatusResponse(BaseModel):
    """KYC verification status response."""

    agent_id: str
    status: str
    verification_id: Optional[str] = None
    is_verified: bool
    verified_at: Optional[str] = None
    expires_at: Optional[str] = None
    provider: str
    warning: Optional[str] = None


class KYCInquiryResponse(BaseModel):
    """Response when creating a KYC inquiry."""

    inquiry_id: str
    session_token: str
    redirect_url: Optional[str] = None
    status: str


class SanctionsScreenRequest(BaseModel):
    """Request to screen an address for sanctions."""

    address: str = Field(..., description="Wallet address to screen")
    chain: str = Field(default="ethereum", description="Blockchain network")


class SanctionsScreenResponse(BaseModel):
    """Sanctions screening response."""

    address: str
    chain: str
    risk_level: str
    is_sanctioned: bool
    should_block: bool
    provider: str
    matches: List[dict] = []
    reason: Optional[str] = None


class TransactionScreenRequest(BaseModel):
    """Request to screen a transaction for sanctions."""

    tx_hash: str
    chain: str
    from_address: str
    to_address: str
    amount: str
    token: str = "USDC"


# ============================================================================
# Dependency Injection
# ============================================================================

class ComplianceDependencies:
    """Dependencies for compliance endpoints."""

    def __init__(self, kyc_service, sanctions_service):
        self.kyc_service = kyc_service
        self.sanctions_service = sanctions_service


def get_deps() -> ComplianceDependencies:
    """Get compliance dependencies (override in main.py)."""
    raise NotImplementedError("Dependency override required")


# ============================================================================
# KYC Endpoints
# ============================================================================

@router.post("/kyc/verify", response_model=KYCInquiryResponse)
async def create_kyc_verification(
    request: KYCVerificationRequest,
    deps: ComplianceDependencies = Depends(get_deps),
):
    """
    Create a new KYC verification inquiry for an agent.

    This initiates the KYC flow. The returned session_token and redirect_url
    can be used to embed the verification in your frontend.
    """
    try:
        session = await deps.kyc_service.create_verification(
            agent_id=request.agent_id,
            name_first=request.name_first,
            name_last=request.name_last,
            email=request.email,
        )

        return KYCInquiryResponse(
            inquiry_id=session.inquiry_id,
            session_token=session.session_token,
            redirect_url=session.redirect_url,
            status=session.status.value,
        )

    except Exception as e:
        logger.error(f"Failed to create KYC verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create KYC verification: {str(e)}",
        )


@router.get("/kyc/{agent_id}", response_model=KYCStatusResponse)
async def get_kyc_status(
    agent_id: str,
    force_refresh: bool = False,
    deps: ComplianceDependencies = Depends(get_deps),
):
    """
    Get the KYC verification status for an agent.

    Returns the current verification status, including any warnings
    about upcoming expiration.
    """
    try:
        result = await deps.kyc_service.check_verification(
            agent_id=agent_id,
            force_refresh=force_refresh,
        )

        # Check for expiration warning
        warning = await deps.kyc_service.get_expiration_warning(agent_id)

        return KYCStatusResponse(
            agent_id=agent_id,
            status=result.effective_status.value,
            verification_id=result.verification_id,
            is_verified=result.is_verified,
            verified_at=result.verified_at.isoformat() if result.verified_at else None,
            expires_at=result.expires_at.isoformat() if result.expires_at else None,
            provider=result.provider,
            warning=warning,
        )

    except Exception as e:
        logger.error(f"Failed to get KYC status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get KYC status: {str(e)}",
        )


@router.get("/kyc/{agent_id}/required")
async def check_kyc_required(
    agent_id: str,
    amount_minor: int,
    deps: ComplianceDependencies = Depends(get_deps),
):
    """
    Check if KYC is required for a transaction.

    Returns whether the agent needs to complete KYC verification
    before proceeding with the transaction.
    """
    required = await deps.kyc_service.is_kyc_required(agent_id, amount_minor)

    return {
        "agent_id": agent_id,
        "amount_minor": amount_minor,
        "kyc_required": required,
        "message": "KYC verification required before transaction" if required else "KYC not required",
    }


# ============================================================================
# Sanctions Screening Endpoints
# ============================================================================

@router.post("/sanctions/screen", response_model=SanctionsScreenResponse)
async def screen_address(
    request: SanctionsScreenRequest,
    deps: ComplianceDependencies = Depends(get_deps),
):
    """
    Screen a wallet address for sanctions.

    Checks the address against OFAC, EU, UN, and other sanctions lists.
    """
    try:
        result = await deps.sanctions_service.screen_address(
            address=request.address,
            chain=request.chain,
        )

        return SanctionsScreenResponse(
            address=request.address,
            chain=request.chain,
            risk_level=result.risk_level.value,
            is_sanctioned=result.is_sanctioned,
            should_block=result.should_block,
            provider=result.provider,
            matches=result.matches,
            reason=result.reason,
        )

    except Exception as e:
        logger.error(f"Failed to screen address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to screen address: {str(e)}",
        )


@router.post("/sanctions/screen-transaction", response_model=SanctionsScreenResponse)
async def screen_transaction(
    request: TransactionScreenRequest,
    deps: ComplianceDependencies = Depends(get_deps),
):
    """
    Screen a transaction for sanctions compliance.

    Checks both the sender and recipient addresses.
    """
    try:
        from decimal import Decimal

        result = await deps.sanctions_service.screen_transaction(
            tx_hash=request.tx_hash,
            chain=request.chain,
            from_address=request.from_address,
            to_address=request.to_address,
            amount=Decimal(request.amount),
            token=request.token,
        )

        return SanctionsScreenResponse(
            address=f"{request.from_address} -> {request.to_address}",
            chain=request.chain,
            risk_level=result.risk_level.value,
            is_sanctioned=result.is_sanctioned,
            should_block=result.should_block,
            provider=result.provider,
            matches=result.matches,
            reason=result.reason,
        )

    except Exception as e:
        logger.error(f"Failed to screen transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to screen transaction: {str(e)}",
        )


@router.get("/sanctions/check/{address}")
async def check_address_blocked(
    address: str,
    chain: str = "ethereum",
    deps: ComplianceDependencies = Depends(get_deps),
):
    """
    Quick check if an address is blocked.

    Faster than full screening for simple allow/block decisions.
    """
    is_blocked = await deps.sanctions_service.is_blocked(address, chain)

    return {
        "address": address,
        "chain": chain,
        "is_blocked": is_blocked,
        "message": "Address is blocked by sanctions" if is_blocked else "Address is not blocked",
    }


@router.post("/sanctions/block")
async def block_address(
    address: str,
    reason: str,
    deps: ComplianceDependencies = Depends(get_deps),
):
    """
    Add an address to the internal blocklist.

    This is for manual blocking based on internal risk assessment.
    """
    success = await deps.sanctions_service.block_address(address, reason)

    if success:
        return {
            "success": True,
            "address": address,
            "message": f"Address blocked: {reason}",
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to block address",
        )


# ============================================================================
# Compliance Status Endpoint
# ============================================================================

@router.get("/status")
async def get_compliance_status(
    deps: ComplianceDependencies = Depends(get_deps),
):
    """
    Get overall compliance system status.

    Shows which providers are configured and their status.
    """
    return {
        "kyc": {
            "provider": deps.kyc_service._provider.__class__.__name__,
            "is_mock": "Mock" in deps.kyc_service._provider.__class__.__name__,
            "threshold": deps.kyc_service._require_kyc_above,
        },
        "sanctions": {
            "provider": deps.sanctions_service._provider.__class__.__name__,
            "is_mock": "Mock" in deps.sanctions_service._provider.__class__.__name__,
            "cache_ttl": deps.sanctions_service._cache_ttl,
        },
        "environment": os.getenv("SARDIS_ENVIRONMENT", "development"),
        "message": (
            "Using production providers"
            if not ("Mock" in deps.kyc_service._provider.__class__.__name__)
            else "Using mock providers for development"
        ),
    }


# ============================================================================
# Persona Webhook Endpoints (with HMAC verification)
# ============================================================================

class PersonaWebhookPayload(BaseModel):
    """Persona webhook event payload."""
    data: dict
    included: Optional[List[dict]] = None


@public_router.post("/webhooks/persona")
async def handle_persona_webhook(
    request: Request,
    verified_body: bytes = Depends(verify_persona_webhook),
    deps: ComplianceDependencies = Depends(get_deps),
):
    """
    Handle Persona KYC webhook events.

    SECURITY: This endpoint verifies the HMAC signature before processing.
    Unsigned or invalid webhooks are rejected with 401.

    Supported events:
    - inquiry.completed: KYC verification completed
    - inquiry.expired: KYC verification expired
    - inquiry.failed: KYC verification failed
    - inquiry.approved: KYC verification approved
    - inquiry.declined: KYC verification declined

    Persona Webhook Docs: https://docs.withpersona.com/docs/webhooks
    """
    try:
        # Parse the verified payload
        payload = json.loads(verified_body)
        event_type = payload.get("data", {}).get("attributes", {}).get("name", "")
        inquiry_data = payload.get("data", {})
        inquiry_id = inquiry_data.get("id", "")

        logger.info(
            f"Persona webhook received: event={event_type}, inquiry={inquiry_id}"
        )

        # Process based on event type
        if event_type in ("inquiry.completed", "inquiry.approved"):
            # KYC completed successfully
            await deps.kyc_service.handle_webhook(
                event_type="inquiry.completed",
                payload=payload,
            )
            logger.info(f"KYC inquiry {inquiry_id} completed successfully")

        elif event_type == "inquiry.expired":
            # KYC verification expired
            await deps.kyc_service.handle_webhook(
                event_type="inquiry.expired",
                payload=payload,
            )
            logger.info(f"KYC inquiry {inquiry_id} expired")

        elif event_type in ("inquiry.failed", "inquiry.declined"):
            # KYC verification failed
            await deps.kyc_service.handle_webhook(
                event_type="inquiry.completed",
                payload=payload,
            )
            logger.warning(f"KYC inquiry {inquiry_id} failed/declined")

        elif event_type == "inquiry.created":
            # New inquiry created - just log
            logger.info(f"KYC inquiry {inquiry_id} created")

        else:
            # Unknown event type - log but don't fail
            logger.warning(f"Unknown Persona webhook event: {event_type}")

        return {
            "success": True,
            "event": event_type,
            "inquiry_id": inquiry_id,
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Persona webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )
    except Exception as e:
        logger.error(f"Error processing Persona webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing error: {str(e)}",
        )


@router.get("/webhooks/persona/verify")
async def verify_persona_webhook_config(
    _: Principal = Depends(require_admin_principal),
):
    """
    Check if Persona webhook verification is properly configured.

    Returns the configuration status without exposing the secret.
    """
    secret = get_persona_webhook_secret()
    is_configured = secret is not None

    return {
        "configured": is_configured,
        "signature_header": WebhookSecurityConfig.PERSONA_SIGNATURE_HEADER,
        "max_timestamp_age_seconds": WebhookSecurityConfig.MAX_TIMESTAMP_AGE_SECONDS,
        "message": (
            "Persona webhook verification is configured"
            if is_configured
            else "WARNING: PERSONA_WEBHOOK_SECRET not set - webhooks will be rejected"
        ),
    }
