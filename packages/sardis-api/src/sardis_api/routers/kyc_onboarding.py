"""Self-serve KYC initiation and status endpoints.

Provides developer-facing endpoints for starting iDenfy identity verification
sessions and checking verification status.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sardis_api.authz import Principal, require_principal

router = APIRouter(prefix="/api/v2/kyc", tags=["kyc"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class KYCInitiateResponse(BaseModel):
    redirect_url: str | None = None
    session_token: str | None = None
    provider: str = "idenfy"
    message: str = ""


class KYCStatusResponse(BaseModel):
    status: str  # not_started, pending, approved, rejected, expired
    provider: str | None = None
    verified_at: str | None = None
    expires_at: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/initiate", response_model=KYCInitiateResponse)
async def initiate_kyc(
    principal: Principal = Depends(require_principal),
) -> KYCInitiateResponse:
    """Initiate an iDenfy identity verification session for the caller.

    Returns a redirect_url to send the user to the iDenfy hosted flow.
    Raises 503 if SARDIS_IDENFY_API_KEY is not configured.
    """
    idenfy_key = os.getenv("SARDIS_IDENFY_API_KEY", "").strip()
    if not idenfy_key:
        raise HTTPException(
            status_code=503,
            detail="KYC provider not configured. Set SARDIS_IDENFY_API_KEY.",
        )

    # TODO: call iDenfy API to create a real verification session
    # POST https://ivs.idenfy.com/api/v2/token with basic auth
    actor = principal.user_id
    return KYCInitiateResponse(
        redirect_url=f"https://ivs.idenfy.com/api/v2/redirect?token=placeholder_{actor}",
        session_token=f"placeholder_{actor}",
        provider="idenfy",
        message="Redirect to complete identity verification",
    )


@router.get("/status", response_model=KYCStatusResponse)
async def get_kyc_status(
    principal: Principal = Depends(require_principal),
) -> KYCStatusResponse:
    """Return the KYC verification status for the authenticated caller.

    Possible statuses: not_started, pending, approved, rejected, expired.
    """
    # TODO: query kyc_verifications table keyed by principal.user_id
    return KYCStatusResponse(status="not_started")
