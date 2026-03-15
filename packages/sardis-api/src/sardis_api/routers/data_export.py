"""GDPR data export endpoints.

Allows authenticated users to request and download a full export of their
personal data (GDPR Art. 20 — right to data portability).

Implementation notes:
- Exports are generated synchronously (no job queue yet).
- Export content is held in-memory (TODO: write to S3/GCS for large datasets).
- Rate limit: 1 export per 24 h per user (in-memory dict).
"""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from sardis_api.authz import Principal, require_principal

_logger = logging.getLogger("sardis.api.data_export")

router = APIRouter(prefix="/api/v2/account", tags=["account"])

# ---------------------------------------------------------------------------
# In-memory stores (process-local; good enough for single-instance / tests)
# ---------------------------------------------------------------------------

# export_id -> export record dict
_export_store: dict[str, dict[str, Any]] = {}

# user_id -> datetime of last export request
_rate_limit_store: dict[str, datetime.datetime] = {}

_RATE_LIMIT_HOURS = 24
_EXPORT_TTL_DAYS = 7


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ExportResponse(BaseModel):
    export_id: str
    status: str
    expires_at: str | None
    download_url: str | None
    created_at: str


class ExportListItem(BaseModel):
    export_id: str
    status: str
    expires_at: str | None
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_utc() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


def _is_export_expired(record: dict[str, Any]) -> bool:
    expires_at = record.get("expires_at")
    if expires_at is None:
        return False
    if isinstance(expires_at, str):
        expires_at = datetime.datetime.fromisoformat(expires_at)
    return _now_utc() > expires_at


async def _build_export_payload(user_id: str, org_id: str | None) -> dict[str, Any]:
    """Generate the GDPR data export payload by querying real database tables.

    Queries users, agents, ledger, wallets, billing, and compliance data
    for the given user/org. Gracefully returns empty arrays on query failure.
    """
    now = _now_utc().isoformat()
    payload: dict[str, Any] = {
        "export_format_version": "1.0",
        "generated_at": now,
        "user": {"user_id": user_id, "org_id": org_id, "email": None, "name": None},
        "agents": [],
        "transactions": [],
        "wallets": [],
        "kyc": {"status": "unknown"},
        "billing": {"plan": None},
        "api_keys": [],
    }

    try:
        from sardis_v2_core.database import Database
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            # User profile
            user_row = await conn.fetchrow(
                "SELECT email, display_name, email_verified, mfa_enabled, created_at FROM users WHERE id = $1",
                user_id,
            )
            if user_row:
                payload["user"]["email"] = user_row["email"]
                payload["user"]["name"] = user_row["display_name"]
                payload["user"]["email_verified"] = user_row["email_verified"]
                payload["user"]["mfa_enabled"] = user_row["mfa_enabled"]
                payload["user"]["created_at"] = user_row["created_at"].isoformat() if user_row["created_at"] else None

            if org_id:
                # Agents
                agent_rows = await conn.fetch(
                    "SELECT external_id, name, is_active, created_at FROM agents WHERE organization_id = $1 LIMIT 500",
                    org_id,
                )
                payload["agents"] = [
                    {"agent_id": r["external_id"], "name": r["name"], "active": r["is_active"],
                     "created_at": r["created_at"].isoformat() if r["created_at"] else None}
                    for r in agent_rows
                ]

                # Wallets
                wallet_rows = await conn.fetch(
                    "SELECT id, name, chain, token, status, created_at FROM wallets WHERE organization_id = $1 LIMIT 500",
                    org_id,
                )
                payload["wallets"] = [
                    {"wallet_id": r["id"], "name": r["name"], "chain": r["chain"], "token": r["token"],
                     "status": r["status"], "created_at": r["created_at"].isoformat() if r["created_at"] else None}
                    for r in wallet_rows
                ]

                # Transactions (last 1000)
                tx_rows = await conn.fetch(
                    """SELECT tx_id, from_wallet, to_wallet, amount, currency, status, purpose, created_at
                       FROM transactions WHERE organization_id = $1 ORDER BY created_at DESC LIMIT 1000""",
                    org_id,
                )
                payload["transactions"] = [
                    {"tx_id": r["tx_id"], "from": r["from_wallet"], "to": r["to_wallet"],
                     "amount": str(r["amount"]), "currency": r["currency"], "status": r["status"],
                     "purpose": r["purpose"], "created_at": r["created_at"].isoformat() if r["created_at"] else None}
                    for r in tx_rows
                ]

                # Billing
                billing_row = await conn.fetchrow(
                    "SELECT plan, status, current_period_start, current_period_end FROM billing_subscriptions WHERE org_id = $1",
                    org_id,
                )
                if billing_row:
                    payload["billing"] = {
                        "plan": billing_row["plan"],
                        "status": billing_row["status"],
                        "period_start": billing_row["current_period_start"].isoformat() if billing_row["current_period_start"] else None,
                        "period_end": billing_row["current_period_end"].isoformat() if billing_row["current_period_end"] else None,
                    }

            # API keys (prefix only, never full key)
            key_rows = await conn.fetch(
                "SELECT id, key_prefix, name, scopes, created_at, expires_at FROM user_api_keys WHERE user_id = $1 LIMIT 100",
                user_id,
            )
            payload["api_keys"] = [
                {"key_id": r["id"], "prefix": r["key_prefix"], "name": r["name"],
                 "scopes": r["scopes"], "created_at": r["created_at"].isoformat() if r["created_at"] else None}
                for r in key_rows
            ]

    except Exception as exc:
        logger.error("Data export DB query failed for user %s: %s", user_id, exc)
        # Return partial data rather than failing entirely

    return payload


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/export",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ExportResponse,
    summary="Request a GDPR data export",
)
async def create_export(
    principal: Principal = Depends(require_principal),
) -> ExportResponse:
    """Initiate a GDPR data export for the authenticated user.

    Rate-limited to one request per 24 hours per user.
    """
    user_id = principal.user_id
    org_id = principal.org_id
    now = _now_utc()

    # --- rate limit check ---
    last = _rate_limit_store.get(user_id)
    if last is not None:
        elapsed = now - last
        if elapsed < datetime.timedelta(hours=_RATE_LIMIT_HOURS):
            retry_after = int(
                (_RATE_LIMIT_HOURS * 3600) - elapsed.total_seconds()
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Data export already requested. "
                    f"Please wait {retry_after // 3600}h "
                    f"{(retry_after % 3600) // 60}m before requesting again."
                ),
                headers={"Retry-After": str(retry_after)},
            )

    export_id = f"exp_{uuid.uuid4().hex}"
    expires_at = now + datetime.timedelta(days=_EXPORT_TTL_DAYS)

    # Generate export data synchronously (no job queue yet)
    payload = await _build_export_payload(user_id=user_id, org_id=org_id)

    record: dict[str, Any] = {
        "export_id": export_id,
        "user_id": user_id,
        "org_id": org_id,
        "status": "ready",
        "payload": payload,
        "expires_at": expires_at.isoformat(),
        "created_at": now.isoformat(),
    }
    _export_store[export_id] = record
    _rate_limit_store[user_id] = now

    _logger.info("GDPR export created export_id=%s user_id=%s", export_id, user_id)

    return ExportResponse(
        export_id=export_id,
        status="ready",
        expires_at=expires_at.isoformat(),
        download_url=f"/api/v2/account/export/{export_id}",
        created_at=now.isoformat(),
    )


@router.get(
    "/export/{export_id}",
    summary="Download a GDPR data export",
)
async def get_export(
    export_id: str,
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Return the export payload for a ready export.

    Returns 404 if not found or not owned by the caller.
    Returns 410 Gone if the export has expired.
    Returns the status object if still pending/processing.
    """
    record = _export_store.get(export_id)
    if record is None or record["user_id"] != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found.",
        )

    if _is_export_expired(record):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Export has expired and is no longer available.",
        )

    export_status = record["status"]
    if export_status in ("pending", "processing"):
        return {
            "export_id": export_id,
            "status": export_status,
            "expires_at": record.get("expires_at"),
            "created_at": record["created_at"],
        }

    return {
        "export_id": export_id,
        "status": export_status,
        "expires_at": record.get("expires_at"),
        "created_at": record["created_at"],
        "data": record.get("payload"),
    }


@router.get(
    "/exports",
    response_model=list[ExportListItem],
    summary="List GDPR data exports for the authenticated user",
)
async def list_exports(
    principal: Principal = Depends(require_principal),
) -> list[ExportListItem]:
    """Return all export records for the authenticated user, newest first."""
    user_id = principal.user_id
    results = [
        ExportListItem(
            export_id=r["export_id"],
            status=r["status"] if not _is_export_expired(r) else "expired",
            expires_at=r.get("expires_at"),
            created_at=r["created_at"],
        )
        for r in _export_store.values()
        if r["user_id"] == user_id
    ]
    results.sort(key=lambda x: x.created_at, reverse=True)
    return results
