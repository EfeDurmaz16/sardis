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

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from server.authz import Principal, require_principal

logger = logging.getLogger("server.api.kyc_onboarding")

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

    api_key = os.getenv("DIDIT_API_KEY", "").strip()
    webhook_secret = os.getenv("DIDIT_WEBHOOK_SECRET", "").strip()
    workflow_id = os.getenv("DIDIT_WORKFLOW_ID", "").strip() or None

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="KYC provider not configured. Set DIDIT_API_KEY.",
        )

    from sardis_compliance.providers.didit import DiditKYCProvider

    _didit_provider = DiditKYCProvider(
        api_key=api_key,
        webhook_secret=webhook_secret or None,
        workflow_id=workflow_id,
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
    can_retry: bool = False


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
        return KYCStatusResponse(status="not_started", can_retry=True)

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
                    can_retry=new_status in ("declined", "expired"),
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
        can_retry=db_status in ("declined", "expired", "not_started"),
    )


@router.post("/webhook")
async def handle_kyc_webhook(request: Request) -> dict:
    """Receive Didit webhook callbacks.

    This endpoint is **public** (no ``require_principal``) because Didit
    calls it server-to-server.  Authenticity is verified via HMAC-SHA256
    signature in the ``X-Signature-V2`` header.

    Security measures:
    - HMAC-SHA256 signature verification (constant-time comparison)
    - Timestamp freshness check (±300 seconds)
    - Raw body read before JSON parsing
    - Raw body never logged; only a SHA-256 payload hash is logged/stored

    Idempotency:
    - Same (session_id, status) pair is not reprocessed

    On ``Approved`` status the user's ``kyc_status`` is updated in the
    ``ba_user`` table and a production API key is generated.
    """
    # ---- 1. Read raw body BEFORE any parsing ----
    body_bytes = await request.body()
    payload_hash = hashlib.sha256(body_bytes).hexdigest()

    # ---- 2. Verify HMAC-SHA256 signature ----
    webhook_secret = os.getenv("DIDIT_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        logger.error("DIDIT_WEBHOOK_SECRET not configured — rejecting webhook")
        raise HTTPException(status_code=401, detail="Webhook secret not configured.")

    signature = request.headers.get("X-Signature-V2", "")
    if not signature:
        logger.warning(
            "Didit webhook received without X-Signature-V2 header: payload_hash=%s",
            payload_hash,
        )
        raise HTTPException(status_code=401, detail="Missing webhook signature.")

    # ---- 3. Validate timestamp freshness ----
    timestamp_header = request.headers.get("X-Timestamp", "")
    if timestamp_header:
        try:
            ts = int(timestamp_header)
            now = int(time.time())
            if abs(now - ts) > 300:
                logger.warning(
                    "Didit webhook timestamp too old/future: header=%s now=%s delta=%ds",
                    ts, now, abs(now - ts),
                )
                raise HTTPException(
                    status_code=401,
                    detail="Webhook timestamp expired.",
                )
        except ValueError:
            logger.warning("Didit webhook X-Timestamp not a valid integer: %s", timestamp_header)
            raise HTTPException(
                status_code=401,
                detail="Invalid timestamp header.",
            )

    # ---- 4. Compute and compare HMAC-SHA256 (constant-time) ----
    try:
        body_dict = json.loads(body_bytes)
        canonical = json.dumps(
            body_dict,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        expected_sig = hmac.new(
            webhook_secret.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            logger.warning(
                "Didit webhook signature mismatch: payload_hash=%s",
                payload_hash,
            )
            raise HTTPException(status_code=401, detail="Invalid webhook signature.")
    except json.JSONDecodeError as exc:
        logger.error("Didit webhook: invalid JSON body during sig check: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Didit webhook signature verification error: %s", exc)
        raise HTTPException(status_code=401, detail="Signature verification failed.") from exc

    # ---- 5. Parse payload (already parsed during sig verification) ----
    payload = body_dict

    session_id = (
        payload.get("session_id")
        or payload.get("data", {}).get("id")
        or payload.get("verification_id", "")
    )
    status_raw = (
        payload.get("status")
        or payload.get("data", {}).get("status", "")
    )
    vendor_data = (
        payload.get("vendor_data")
        or payload.get("data", {}).get("vendor_data", "")
    )

    if not session_id:
        logger.warning("Didit webhook missing session_id: payload_hash=%s", payload_hash)
        return {"status": "ignored", "reason": "no session_id"}

    logger.info(
        "Didit webhook received: session_id=%s status=%s vendor_data=%s",
        session_id, status_raw, vendor_data,
    )

    # ---- 6. Idempotency check: same session_id + status = skip ----
    already_processed = await _check_idempotency(session_id, status_raw)
    if already_processed:
        logger.info(
            "Didit webhook already processed: session_id=%s status=%s — skipping",
            session_id, status_raw,
        )
        return {"status": "already_processed", "session_id": session_id}

    # ---- 7. Map Didit status and process ----
    mapped_status = _map_didit_webhook_status(status_raw)

    now = datetime.now(UTC)
    verified_at: datetime | None = None
    reason: str | None = None

    if mapped_status == "approved":
        verified_at = now
        # Persist status
        await _update_kyc_status(
            inquiry_id=session_id,
            status="approved",
            verified_at=verified_at,
            reason=None,
            metadata=_safe_webhook_metadata(
                payload_hash=payload_hash,
                status_raw=status_raw,
                vendor_data=vendor_data,
                payload=payload,
            ),
        )
        # Side-effects: update ba_user, generate API key
        reference_id = vendor_data or ""
        if reference_id:
            await _on_kyc_approved(user_id=reference_id, organization_id=None)

    elif mapped_status == "declined":
        reason = payload.get("reason") or payload.get("data", {}).get("reason")
        logger.warning(
            "Didit KYC declined for session %s (vendor_data=%s): reason=%s",
            session_id, vendor_data, reason,
        )
        await _update_kyc_status(
            inquiry_id=session_id,
            status="declined",
            reason=reason,
            metadata=_safe_webhook_metadata(
                payload_hash=payload_hash,
                status_raw=status_raw,
                vendor_data=vendor_data,
                payload=payload,
            ),
        )

    elif mapped_status == "pending_review":
        await _update_kyc_status(
            inquiry_id=session_id,
            status="needs_review",
            metadata=_safe_webhook_metadata(
                payload_hash=payload_hash,
                status_raw=status_raw,
                vendor_data=vendor_data,
                payload=payload,
            ),
        )

    elif mapped_status == "in_progress":
        await _update_kyc_status(
            inquiry_id=session_id,
            status="pending",
            metadata=_safe_webhook_metadata(
                payload_hash=payload_hash,
                status_raw=status_raw,
                vendor_data=vendor_data,
                payload=payload,
            ),
        )

    elif mapped_status == "abandoned":
        logger.info("Didit KYC abandoned for session %s — may trigger reminder", session_id)
        await _update_kyc_status(
            inquiry_id=session_id,
            status="expired",
            reason="Session abandoned by user",
            metadata=_safe_webhook_metadata(
                payload_hash=payload_hash,
                status_raw=status_raw,
                vendor_data=vendor_data,
                payload=payload,
            ),
        )

    elif mapped_status == "expired":
        await _update_kyc_status(
            inquiry_id=session_id,
            status="expired",
            reason="Session expired",
            expires_at=now,
            metadata=_safe_webhook_metadata(
                payload_hash=payload_hash,
                status_raw=status_raw,
                vendor_data=vendor_data,
                payload=payload,
            ),
        )

    else:
        logger.warning("Unhandled Didit webhook status: %s for session %s", status_raw, session_id)
        await _update_kyc_status(
            inquiry_id=session_id,
            status="pending",
            metadata=_safe_webhook_metadata(
                payload_hash=payload_hash,
                status_raw=status_raw,
                vendor_data=vendor_data,
                payload=payload,
            ),
        )

    # ---- 8. Send KYC status email notification (fire-and-forget) ----
    if mapped_status in ("approved", "declined"):
        try:
            user_email = await _resolve_user_email(vendor_data or "")
            if user_email:
                from server.email_templates import send_kyc_status_email
                await send_kyc_status_email(user_email, mapped_status)
        except Exception as exc:
            logger.debug("KYC email notification skipped for %s: %s", vendor_data, exc)

    # ---- 9. Record idempotency marker ----
    await _record_idempotency(session_id, status_raw)

    return {
        "status": "processed",
        "session_id": session_id,
        "kyc_status": mapped_status,
    }


@router.post("/retry", response_model=KYCInitiateResponse)
async def retry_kyc(
    body: KYCInitiateRequest | None = None,
    principal: Principal = Depends(require_principal),
) -> KYCInitiateResponse:
    """Retry KYC verification after a previous attempt was declined or expired.

    Resets the previous verification status and creates a fresh Didit session.
    Returns the same response as ``/initiate`` with a new ``redirect_url``.
    """
    # Check current status — only allow retry if declined, expired, or not_started
    row = await _get_latest_verification(principal.user_id)
    if row is not None:
        current_status = row["status"]
        if current_status in ("pending", "needs_review"):
            raise HTTPException(
                status_code=400,
                detail="KYC verification is already in progress. Check /api/v2/kyc/status for updates.",
            )
        if current_status == "approved":
            raise HTTPException(
                status_code=400,
                detail="KYC is already approved. No retry needed.",
            )
        # For declined/expired — mark old record so we can create a fresh one
        logger.info("KYC retry requested for %s (previous status: %s)", principal.user_id, current_status)

    # Delegate to the initiate flow which handles session creation + DB upsert
    return await initiate_kyc(body=body, principal=principal)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _resolve_user_email(user_id: str) -> str | None:
    """Best-effort email lookup for a user reference (id, email, or name).

    Checks ``ba_user`` first, then ``organizations`` settings.
    Returns ``None`` if the user cannot be resolved.
    """
    if not user_id:
        return None
    # If the reference itself looks like an email, use it directly
    if "@" in user_id:
        return user_id
    try:
        from sardis.core.database import Database

        # Try ba_user table
        row = await Database.fetchrow(
            "SELECT email FROM ba_user WHERE id = $1 OR name = $1 LIMIT 1",
            user_id,
        )
        if row and row.get("email"):
            return row["email"]

        # Fallback: organizations settings JSON
        row = await Database.fetchrow(
            "SELECT settings FROM organizations WHERE external_id = $1 LIMIT 1",
            user_id,
        )
        if row and row.get("settings"):
            settings = row["settings"]
            if isinstance(settings, str):
                settings = json.loads(settings)
            return settings.get("email")
    except Exception:
        pass
    return None


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
        from sardis.core.database import Database

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
        from sardis.core.database import Database

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
    """Fetch the most recent kyc_verifications row for ``user_id``.

    Falls back to checking ``users.kyc_status`` and ``ba_user.kyc_status``
    when no ``kyc_verifications`` row exists (handles the case where the
    webhook updated the user table but no verification row was persisted).
    """
    try:
        from sardis.core.database import Database

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
        if row:
            return dict(row)

        # Fallback: check users table (dashboard users with text IDs like usr_xxx)
        user_row = await Database.fetchrow(
            """
            SELECT kyc_status FROM users
            WHERE id = $1 OR email = $1
            LIMIT 1
            """,
            user_id,
        )
        if user_row and user_row["kyc_status"] not in (None, "not_started"):
            return {
                "inquiry_id": None,
                "provider": "didit",
                "status": user_row["kyc_status"],
                "verified_at": None,
                "expires_at": None,
                "reason": None,
                "metadata": {},
            }

        # Fallback: check ba_user table (better-auth users)
        ba_row = await Database.fetchrow(
            """
            SELECT kyc_status FROM ba_user
            WHERE id = $1 OR email = $1 OR name = $1
            LIMIT 1
            """,
            user_id,
        )
        if ba_row and ba_row["kyc_status"] not in (None, "not_started"):
            return {
                "inquiry_id": None,
                "provider": "didit",
                "status": ba_row["kyc_status"],
                "verified_at": None,
                "expires_at": None,
                "reason": None,
                "metadata": {},
            }

        return None
    except Exception as exc:
        logger.warning("DB lookup for KYC verification failed for %s: %s", user_id, exc)
        return None


def _map_didit_webhook_status(raw_status: str) -> str:
    """Map a raw Didit webhook status string to an internal status key.

    Didit sends Title Case statuses:
    ``Approved``, ``Declined``, ``In Review``, ``In Progress``,
    ``Abandoned``, ``Expired``, ``Kyc Expired``, ``Resubmitted``.
    """
    normalized = raw_status.lower().strip()
    mapping = {
        "approved": "approved",
        "declined": "declined",
        "in review": "pending_review",
        "in progress": "in_progress",
        "not started": "in_progress",
        "resubmitted": "in_progress",
        "abandoned": "abandoned",
        "expired": "expired",
        "kyc expired": "expired",
    }
    return mapping.get(normalized, "unknown")


def _safe_webhook_metadata(
    *,
    payload_hash: str,
    status_raw: str,
    vendor_data: str,
    payload: dict,
) -> dict[str, str | None]:
    """Return non-sensitive Didit webhook metadata for durable storage."""
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    return {
        "provider": "didit",
        "payload_hash": payload_hash,
        "webhook_status": status_raw,
        "vendor_data": vendor_data,
        "session_id": payload.get("session_id") or data.get("id"),
        "workflow_id": payload.get("workflow_id") or data.get("workflow_id"),
        "verification_id": payload.get("verification_id") or data.get("verification_id"),
    }


# In-memory idempotency set for environments without a database.
# In production the DB-backed helpers below are used instead.
_idempotency_cache: set[str] = set()


async def _check_idempotency(session_id: str, status: str) -> bool:
    """Return ``True`` if this (session_id, status) pair was already processed.

    Tries the database first; falls back to an in-memory set so the
    endpoint works even when the DB is unavailable (dev/test).
    """
    key = f"{session_id}:{status}"
    try:
        from sardis.core.database import Database

        row = await Database.fetchrow(
            """
            SELECT 1 FROM kyc_webhook_events
            WHERE session_id = $1 AND status = $2
            LIMIT 1
            """,
            session_id,
            status,
        )
        return row is not None
    except Exception:
        # Table may not exist yet — fall back to in-memory
        return key in _idempotency_cache


async def _record_idempotency(session_id: str, status: str) -> None:
    """Record that this (session_id, status) pair has been processed."""
    key = f"{session_id}:{status}"
    _idempotency_cache.add(key)
    try:
        from sardis.core.database import Database

        await Database.execute(
            """
            INSERT INTO kyc_webhook_events (session_id, status, processed_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (session_id, status) DO NOTHING
            """,
            session_id,
            status,
        )
    except Exception as exc:
        # Non-fatal — in-memory cache is the safety net
        logger.debug("Could not record kyc_webhook_events row: %s", exc)


async def _on_kyc_approved(user_id: str, organization_id: str | None) -> None:
    """Side-effects when a user passes KYC.

    1. Update ``kyc_status`` to ``'approved'`` in all user tables
    2. Generate a production (``sk_live_``) API key for the org
    """
    try:
        from sardis.core.database import Database

        # 1a. Update ba_user kyc_status (better-auth users)
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

    try:
        from sardis.core.database import Database

        # 1b. Update users kyc_status (dashboard users with usr_xxx IDs)
        await Database.execute(
            """
            UPDATE users
            SET kyc_status  = 'approved',
                updated_at  = NOW()
            WHERE id = $1 OR email = $1
            """,
            user_id,
        )
        logger.info("KYC approved: updated users.kyc_status for %s", user_id)
    except Exception as exc:
        logger.warning("Failed to update users.kyc_status for %s: %s", user_id, exc)

    # 2. Generate sk_live_ API key
    if not organization_id:
        # Try to resolve org from the kyc_verifications metadata
        try:
            from sardis.core.database import Database

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

    if not organization_id:
        # Fallback: resolve org from user_org_memberships (dashboard users)
        try:
            from sardis.core.database import Database

            org_row = await Database.fetchrow(
                """
                SELECT org_id FROM user_org_memberships
                WHERE user_id = $1
                ORDER BY created_at
                LIMIT 1
                """,
                user_id,
            )
            if org_row:
                organization_id = org_row["org_id"]
        except Exception:
            pass

    if organization_id:
        try:
            from server.dependencies import get_container

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
            # Notify user about the new live API key
            try:
                user_email = await _resolve_user_email(user_id)
                if user_email:
                    from server.email_templates import send_api_key_generated_email
                    await send_api_key_generated_email(user_email, full_key[:12], "live")
            except Exception:
                pass  # Email must never block KYC approval flow
        except Exception as exc:
            logger.error(
                "Failed to generate production API key for org %s after KYC approval: %s",
                organization_id,
                exc,
            )
