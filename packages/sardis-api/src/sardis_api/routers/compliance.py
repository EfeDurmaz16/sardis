"""Compliance API endpoints for KYC and Sanctions screening."""
from __future__ import annotations

import logging
import os
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


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
