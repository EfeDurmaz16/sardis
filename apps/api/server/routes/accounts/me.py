"""Per-user "me" endpoints.

Currently exposes the onboarding wizard state machine used by the
dashboard's first-run wizard. Keyed by ``Principal.organization_id``
since better-auth provisions a 1:1 user/org slug.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from server.authz import Principal, require_principal

logger = logging.getLogger("server.api.me")

router = APIRouter(prefix="/api/v2/me", tags=["me"])


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

OnboardingStep = Literal[
    "profile",
    "api_key",
    "kyc",
    "agent_wallet",
    "spending_policy",
    "sandbox_payment",
    "tour_ready",
]

# Canonical step order. Product clients should mirror this list and keep
# their onboarding UI in sync when adding/removing steps.
ONBOARDING_STEPS: tuple[OnboardingStep, ...] = (
    "profile",
    "api_key",
    "kyc",
    "agent_wallet",
    "spending_policy",
    "sandbox_payment",
    "tour_ready",
)

VALID_STEPS = set(ONBOARDING_STEPS)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class OnboardingState(BaseModel):
    org_id: str
    current_step: OnboardingStep
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    steps: list[OnboardingStep] = Field(default_factory=lambda: list(ONBOARDING_STEPS))


class OnboardingPatchRequest(BaseModel):
    """Patch the onboarding state.

    Any field omitted is left untouched. Setting ``current_step`` to
    ``tour_ready`` (the terminal step) will also stamp ``completed_at``
    to NOW() server-side.
    """

    current_step: OnboardingStep | None = None
    skipped: list[OnboardingStep] | None = None
    metadata_patch: dict[str, Any] | None = None
    mark_complete: bool | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_state(row: dict[str, Any]) -> OnboardingState:
    metadata = row.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return OnboardingState(
        org_id=row["org_id"],
        current_step=row["current_step"],
        completed_at=row.get("completed_at"),
        metadata=metadata,
    )


async def _ensure_row(org_id: str) -> dict[str, Any]:
    """Idempotently insert a default onboarding row and return it."""
    from sardis.core.database import Database

    await Database.execute(
        """
        INSERT INTO user_onboarding (org_id)
        VALUES ($1)
        ON CONFLICT (org_id) DO NOTHING
        """,
        org_id,
    )
    row = await Database.fetchrow(
        "SELECT org_id, current_step, completed_at, metadata FROM user_onboarding WHERE org_id = $1",
        org_id,
    )
    if row is None:
        # Should not happen — INSERT above is idempotent and the row must exist.
        raise HTTPException(status_code=500, detail="Failed to load onboarding row")
    return dict(row)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/onboarding", response_model=OnboardingState)
async def get_onboarding(
    principal: Principal = Depends(require_principal),
) -> OnboardingState:
    row = await _ensure_row(principal.organization_id)
    return _row_to_state(row)


@router.patch("/onboarding", response_model=OnboardingState)
async def patch_onboarding(
    body: OnboardingPatchRequest,
    principal: Principal = Depends(require_principal),
) -> OnboardingState:
    from sardis.core.database import Database

    if body.current_step is not None and body.current_step not in VALID_STEPS:
        raise HTTPException(status_code=422, detail=f"Unknown step: {body.current_step}")
    if body.skipped:
        for step in body.skipped:
            if step not in VALID_STEPS:
                raise HTTPException(status_code=422, detail=f"Unknown step: {step}")

    row = await _ensure_row(principal.organization_id)
    current_metadata = row.get("metadata") or {}
    if isinstance(current_metadata, str):
        try:
            current_metadata = json.loads(current_metadata)
        except json.JSONDecodeError:
            current_metadata = {}

    new_metadata = dict(current_metadata)
    if body.metadata_patch:
        new_metadata.update(body.metadata_patch)
    if body.skipped is not None:
        existing = set(new_metadata.get("skipped") or [])
        existing.update(body.skipped)
        new_metadata["skipped"] = sorted(existing)

    new_step = body.current_step or row["current_step"]
    mark_complete = body.mark_complete or new_step == "tour_ready"

    await Database.execute(
        """
        UPDATE user_onboarding
        SET current_step = $1,
            metadata     = $2::jsonb,
            completed_at = CASE WHEN $3::boolean THEN COALESCE(completed_at, NOW()) ELSE completed_at END,
            updated_at   = NOW()
        WHERE org_id = $4
        """,
        new_step,
        json.dumps(new_metadata, default=str),
        mark_complete,
        principal.organization_id,
    )

    refreshed = await Database.fetchrow(
        "SELECT org_id, current_step, completed_at, metadata FROM user_onboarding WHERE org_id = $1",
        principal.organization_id,
    )
    if refreshed is None:
        raise HTTPException(status_code=500, detail="Failed to reload onboarding row")
    return _row_to_state(dict(refreshed))


# ---------------------------------------------------------------------------
# First-key bootstrap
# ---------------------------------------------------------------------------
#
# The standard POST /api/v2/api-keys endpoint requires an existing API key
# (Depends(require_api_key)), which creates a chicken-and-egg problem for
# brand-new dashboard signups: they have a JWT but no key yet. This route
# is the JWT-authed bootstrap path used exclusively by the onboarding
# wizard. To prevent it from being used as a generic "mint another key"
# bypass, it refuses if the org already owns at least one key.
#
# Pattern mirrors `_on_kyc_approved` in routers/kyc_onboarding.py, which
# also runs server-side and calls `api_key_manager.create_key` directly.


class BootstrapApiKeyRequest(BaseModel):
    name: str = Field(default="Default API key", min_length=1, max_length=120)


class BootstrapApiKeyResponse(BaseModel):
    key: str  # Full plaintext key — only returned once
    key_id: str
    key_prefix: str
    name: str
    mode: str = "test"
    created_at: datetime


@router.post(
    "/api-keys/bootstrap",
    response_model=BootstrapApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bootstrap_first_api_key(
    body: BootstrapApiKeyRequest,
    principal: Principal = Depends(require_principal),
) -> BootstrapApiKeyResponse:
    if principal.kind != "jwt":
        # Bootstrap is for first-time wizard users authenticated via the
        # better-auth session JWT. API-key callers should use the regular
        # POST /api/v2/api-keys endpoint.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap is only available to JWT-authenticated users",
        )

    from server.dependencies import get_container

    container = get_container()
    api_key_mgr = container.api_key_manager

    existing = await api_key_mgr.list_keys(principal.organization_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization already has at least one API key. Use the regular API key endpoints.",
        )

    full_key, record = await api_key_mgr.create_key(
        organization_id=principal.organization_id,
        name=body.name,
        scopes=["read", "write"],
        test=True,  # sk_test_ — onboarding bootstrap is always sandbox
    )
    logger.info(
        "onboarding: bootstrapped first sk_test_ key for org %s (key_id=%s)",
        principal.organization_id,
        record.key_id,
    )

    return BootstrapApiKeyResponse(
        key=full_key,
        key_id=record.key_id,
        key_prefix=record.key_prefix,
        name=record.name,
        created_at=record.created_at,
    )
