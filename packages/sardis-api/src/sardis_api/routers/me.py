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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger("sardis.api.me")

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

# Canonical step order. Mirrored verbatim in
# apps/dashboard/components/onboarding/onboarding-wizard.tsx — keep
# the two lists in sync when adding/removing steps.
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
    from sardis_v2_core.database import Database

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
    from sardis_v2_core.database import Database

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
