"""Self-serve KYC onboarding endpoints backed by the Didit provider.

Provides developer-facing endpoints for:
- Starting a Didit identity verification session
- Checking verification status
- Receiving Didit webhook callbacks (signature-verified)

On KYC approval the user's ``ba_user.kyc_status`` is updated and a
production (``sk_live_``) API key is generated so they can start
transacting on mainnet.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger("sardis.api.kyc_onboarding")

router = APIRouter(prefix="/api/v2/kyc", tags=["kyc"])


# ---------------------------------------------------------------------------
# Singleton Didit provider (lazy-init, cached)
# ---------------------------------------------------------------------------
_didit_provider = None


def _get_didit_provider():
    """Return a cached DiditKYCProvider instance.

    Raises ``HTTPException(503)`` when the required env vars are missing.
    """
    global _didit_provider
    if _didit_provider is not None:
        return _didit_provider

    client_id = os.getenv("DIDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("DIDIT_CLIENT_SECRET", "").strip()
    webhook_secret = os.getenv("DIDIT_WEBHOOK_SECRET", "").strip()
    environment = os.getenv("SARDIS_ENVIRONMENT", "sandbox").strip().lower()
    didit_env = "production" if environment in ("prod", "production") else "sandbox"

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail=(
                "KYC provider not configured. "
                "Set DIDIT_CLIENT_ID and DIDIT_CLIENT_SECRET."
            ),
        )

    from sardis_compliance.providers.didit import DiditKYCProvider

    _didit_provider = DiditKYCProvider(
        client_id=client_id,
        client_secret=client_secret,
        webhook_secret=webhook_secret or None,
        environment=didit_env,
    )
    return _didit_provider


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class KYCInitiateRequest(BaseModel):
    """Optional user details to prefill the verification form."""
    name_first: str | None = None
    name_last: str | None = None
    email: str | None = None
    phone: str | None = None


class KYCInitiateResponse(BaseModel):
    redirect_url: str | None = None
    session_token: str | None = None
    inquiry_id: str | None = None
    provider: str = "didit"
    message: str = ""


class KYCStatusResponse(BaseModel):
    status: str  # not_started, pending, approved, declined, expired, needs_review
    provider: str | None = None
    inquiry_id: str | None = None
    verified_at: str | None = None
    expires_at: str | None = None
    reason: str | None = None


class KYCApprovalResult(BaseModel):
    kyc_status: str
    api_key: str | None = None
    message: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/initiate", response_model=KYCInitiateResponse)
async def initiate_kyc(
    body: KYCInitiateRequest | None = None,
    principal: Principal = Depends(require_principal),
) -> KYCInitiateResponse:
    """Create a Didit identity verification session for the authenticated user.

    Returns a ``redirect_url`` to send the user into the Didit hosted flow
    and the ``inquiry_id`` needed to poll status later.
    """
    provider = _get_didit_provider()

    from sardis_compliance.kyc import VerificationRequest

    request_body = body or KYCInitiateRequest()

    verification_request = VerificationRequest(
        reference_id=principal.user_id,
        name_first=request_body.name_first,
        name_last=request_body.name_last,
        email=request_body.email,
        phone=request_body.phone,
        metadata={
            "organization_id": principal.organization_id,
            "initiated_by": principal.user_id,
        },
    )

    try:
        session = await provider.create_inquiry(verification_request)
    except Exception as exc:
        logger.error("Didit create_inquiry failed for %s: %s", principal.user_id, exc)
        raise HTTPException(
            status_code=502,
            detail="Failed to create verification session with KYC provider.",
        ) from exc

    # Persist the pending inquiry so we can look it up later
    await _upsert_kyc_verification(
        user_id=principal.user_id,
        inquiry_id=session.inquiry_id,
        provider="didit",
        status="pending",
        metadata={
            "organization_id": principal.organization_id,
            "session_token": session.session_token,
        },
    )

    return KYCInitiateResponse(
        redirect_url=session.redirect_url,
        session_token=session.session_token,
        inquiry_id=session.inquiry_id,
        provider="didit",
        message="Redirect user to complete identity verification.",
    )


@router.get("/status", response_model=KYCStatusResponse)
async def get_kyc_status(
    principal: Principal = Depends(require_principal),
) -> KYCStatusResponse:
    """Return the KYC verification status for the authenticated caller.

    First checks the local database.  If an inquiry exists and is still
    ``pending``, it also fetches live status from Didit and persists any
    changes.
    """
    # 1. Look up the most recent verification in our DB
    row = await _get_latest_verification(principal.user_id)

    if row is None:
        return KYCStatusResponse(status="not_started")

    db_status = row["status"]
    inquiry_id = row["inquiry_id"]
    provider_name = row["provider"] or "didit"

    # 2. If still pending, refresh from Didit
    if db_status in ("pending", "needs_review") and inquiry_id:
        try:
            provider = _get_didit_provider()
            result = await provider.get_inquiry_status(inquiry_id)

            new_status = result.status.value

            # Persist if status changed
            if new_status != db_status:
                verified_at = result.verified_at.isoformat() if result.verified_at else None
                expires_at = result.expires_at.isoformat() if result.expires_at else None

                await _update_kyc_status(
                    inquiry_id=inquiry_id,
                    status=new_status,
                    verified_at=result.verified_at,
                    expires_at=result.expires_at,
                    reason=result.reason,
                    metadata=result.metadata,
                )

                # If newly approved, run the approval side-effects
                if new_status == "approved":
                    await _on_kyc_approved(principal.user_id, principal.organization_id)

                return KYCStatusResponse(
                    status=new_status,
                    provider=provider_name,
                    inquiry_id=inquiry_id,
                    verified_at=verified_at,
                    expires_at=expires_at,
                    reason=result.reason,
                )
        except HTTPException:
            # 503 from _get_didit_provider — provider not configured, fall through to DB data
            pass
        except Exception as exc:
            logger.warning("Failed to refresh status from Didit for %s: %s", inquiry_id, exc)

    # 3. Return DB-sourced status
    verified_at_str = row["verified_at"].isoformat() if row.get("verified_at") else None
    expires_at_str = row["expires_at"].isoformat() if row.get("expires_at") else None

    return KYCStatusResponse(
        status=db_status,
        provider=provider_name,
        inquiry_id=inquiry_id,
        verified_at=verified_at_str,
        expires_at=expires_at_str,
        reason=row.get("reason"),
    )


@router.post("/webhook")
async def handle_kyc_webhook(request: Request) -> dict:
    """Receive Didit webhook callbacks.

    This endpoint is **public** (no ``require_principal``) because Didit
    calls it server-to-server.  Authenticity is verified via HMAC-SHA256
    signature in the ``X-Didit-Signature`` header.

    On ``approved`` status the user's ``kyc_status`` is updated in the
    ``ba_user`` table and a production API key is generated.
    """
    provider = _get_didit_provider()

    # ---- Signature verification ----
    body_bytes = await request.body()
    signature = request.headers.get("X-Didit-Signature", "")

    if not signature:
        logger.warning("Didit webhook received without signature header")
        raise HTTPException(status_code=401, detail="Missing webhook signature.")

    sig_valid = await provider.verify_webhook(body_bytes, signature)
    if not sig_valid:
        logger.warning("Didit webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    # ---- Parse payload ----
    try:
        payload = json.loads(body_bytes)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Didit webhook: invalid JSON body: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc

    event_type = payload.get("type", payload.get("event", ""))
    verification_id = (
        payload.get("data", {}).get("id")
        or payload.get("verification_id", "")
    )

    if not verification_id:
        logger.warning("Didit webhook missing verification_id: %s", event_type)
        return {"status": "ignored", "reason": "no verification_id"}

    logger.info("Didit webhook received: type=%s id=%s", event_type, verification_id)

    # ---- Fetch latest status from Didit ----
    try:
        result = await provider.get_inquiry_status(verification_id)
    except Exception as exc:
        logger.error("Didit get_inquiry_status failed for %s: %s", verification_id, exc)
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch verification status from provider.",
        ) from exc

    new_status = result.status.value
    reference_id = result.metadata.get("reference_id", "")

    # ---- Persist status ----
    await _update_kyc_status(
        inquiry_id=verification_id,
        status=new_status,
        verified_at=result.verified_at,
        expires_at=result.expires_at,
        reason=result.reason,
        metadata=result.metadata,
    )

    # ---- Side-effects on approval ----
    if new_status == "approved" and reference_id:
        await _on_kyc_approved(user_id=reference_id, organization_id=None)

    return {
        "status": "processed",
        "verification_id": verification_id,
        "kyc_status": new_status,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _upsert_kyc_verification(
    *,
    user_id: str,
    inquiry_id: str,
    provider: str,
    status: str,
    metadata: dict | None = None,
) -> None:
    """Insert or update a row in ``kyc_verifications``.

    Uses a transaction with an existence check rather than ``ON CONFLICT``
    so that the code works regardless of whether the ``inquiry_id`` column
    carries a unique constraint.
    """
    try:
        from sardis_v2_core.database import Database

        meta_json = json.dumps(metadata or {}, default=str)

        async with Database.transaction() as conn:
            existing = await conn.fetchrow(
                "SELECT id FROM kyc_verifications WHERE inquiry_id = $1",
                inquiry_id,
            )
            if existing:
                await conn.execute(
                    """
                    UPDATE kyc_verifications
                    SET status     = $1,
                        metadata   = $2::jsonb,
                        updated_at = NOW()
                    WHERE inquiry_id = $3
                    """,
                    status,
                    meta_json,
                    inquiry_id,
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO kyc_verifications
                        (agent_id, inquiry_id, provider, status, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5::jsonb, NOW(), NOW())
                    """,
                    user_id,
                    inquiry_id,
                    provider,
                    status,
                    meta_json,
                )
    except Exception as exc:
        logger.warning("Failed to upsert kyc_verifications for %s: %s", user_id, exc)


async def _update_kyc_status(
    *,
    inquiry_id: str,
    status: str,
    verified_at: datetime | None = None,
    expires_at: datetime | None = None,
    reason: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Update an existing verification row with new status from provider."""
    try:
        from sardis_v2_core.database import Database

        await Database.execute(
            """
            UPDATE kyc_verifications
            SET status     = $1,
                verified_at = $2,
                expires_at  = $3,
                reason      = $4,
                metadata    = COALESCE($5::jsonb, metadata),
                updated_at  = NOW()
            WHERE inquiry_id = $6
            """,
            status,
            verified_at,
            expires_at,
            reason,
            json.dumps(metadata or {}, default=str),
            inquiry_id,
        )
    except Exception as exc:
        logger.warning("Failed to update kyc_verifications for %s: %s", inquiry_id, exc)


async def _get_latest_verification(user_id: str) -> dict | None:
    """Fetch the most recent kyc_verifications row for ``user_id``."""
    try:
        from sardis_v2_core.database import Database

        row = await Database.fetchrow(
            """
            SELECT inquiry_id, provider, status, verified_at, expires_at, reason, metadata
            FROM kyc_verifications
            WHERE agent_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user_id,
        )
        return dict(row) if row else None
    except Exception as exc:
        logger.warning("DB lookup for KYC verification failed for %s: %s", user_id, exc)
        return None


async def _on_kyc_approved(user_id: str, organization_id: str | None) -> None:
    """Side-effects when a user passes KYC.

    1. Update ``ba_user.kyc_status`` to ``'approved'``
    2. Generate a production (``sk_live_``) API key for the org
    """
    try:
        from sardis_v2_core.database import Database

        # 1. Update ba_user kyc_status
        await Database.execute(
            """
            UPDATE ba_user
            SET kyc_status  = 'approved',
                updated_at  = NOW()
            WHERE id = $1 OR email = $1 OR name = $1
            """,
            user_id,
        )
        logger.info("KYC approved: updated ba_user.kyc_status for %s", user_id)
    except Exception as exc:
        logger.warning("Failed to update ba_user.kyc_status for %s: %s", user_id, exc)

    # 2. Generate sk_live_ API key
    if not organization_id:
        # Try to resolve org from the kyc_verifications metadata
        try:
            from sardis_v2_core.database import Database

            row = await Database.fetchrow(
                """
                SELECT metadata
                FROM kyc_verifications
                WHERE agent_id = $1 AND status = 'approved'
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                user_id,
            )
            if row and row["metadata"]:
                meta = row["metadata"]
                if isinstance(meta, str):
                    meta = json.loads(meta)
                organization_id = meta.get("organization_id")
        except Exception:
            pass

    if organization_id:
        try:
            from sardis_api.dependencies import get_container

            container = get_container()
            api_key_mgr = container.api_key_manager

            full_key, _api_key_record = await api_key_mgr.create_key(
                organization_id=organization_id,
                name="Production key (auto-generated on KYC approval)",
                scopes=["read", "write"],
                test=False,  # generates sk_live_
            )
            logger.info(
                "KYC approved: generated sk_live_ key for org %s (prefix: %s)",
                organization_id,
                full_key[:12],
            )
        except Exception as exc:
            logger.error(
                "Failed to generate production API key for org %s after KYC approval: %s",
                organization_id,
                exc,
            )
