"""Delegated credential management API endpoints."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/credentials", tags=["credentials"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ProvisionCredentialRequest(BaseModel):
    agent_id: str
    network: str  # stripe_spt, visa_tap, mastercard_agent_pay
    consent_id: str
    max_per_tx: Optional[str] = "500"
    daily_limit: Optional[str] = "2000"
    allowed_mccs: Optional[list[str]] = None
    allowed_merchant_ids: Optional[list[str]] = None


class TightenScopeRequest(BaseModel):
    max_per_tx: Optional[str] = None
    daily_limit: Optional[str] = None
    allowed_mccs: Optional[list[str]] = None
    allowed_merchant_ids: Optional[list[str]] = None


class ReprovisionRequest(BaseModel):
    consent_id: str
    max_per_tx: Optional[str] = "500"
    daily_limit: Optional[str] = "2000"
    allowed_mccs: Optional[list[str]] = None
    allowed_merchant_ids: Optional[list[str]] = None


class RevokeRequest(BaseModel):
    reason: str = "user_revoked"


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def _get_credential_store(request: Request):
    store = getattr(request.app.state, "credential_store", None)
    if store is None:
        raise HTTPException(503, "Credential store not initialized")
    return store


def _get_consent_store(request: Request):
    store = getattr(request.app.state, "consent_store", None)
    if store is None:
        raise HTTPException(503, "Consent store not initialized")
    return store


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("")
async def provision_credential(
    body: ProvisionCredentialRequest,
    request: Request,
    cred_store=Depends(_get_credential_store),
    consent_store=Depends(_get_consent_store),
):
    """Provision a new delegated credential (requires consent)."""
    from sardis_v2_core.delegated_credential import (
        CredentialNetwork,
        CredentialScope,
        CredentialStatus,
        DelegatedCredential,
    )

    # Validate consent exists and is valid
    valid = await consent_store.is_consent_valid(body.consent_id)
    if not valid:
        raise HTTPException(400, "Invalid or expired consent")

    try:
        network = CredentialNetwork(body.network)
    except ValueError:
        raise HTTPException(400, f"Unknown network: {body.network}")

    scope = CredentialScope(
        max_per_tx=Decimal(body.max_per_tx or "500"),
        daily_limit=Decimal(body.daily_limit or "2000"),
        allowed_mccs=body.allowed_mccs or [],
        allowed_merchant_ids=body.allowed_merchant_ids or [],
    )

    # Use mock adapter to provision
    mock_adapter = getattr(request.app.state, "delegated_adapter", None)
    if mock_adapter and hasattr(mock_adapter, "provision_credential"):
        encryption = getattr(request.app.state, "credential_encryption", None)
        cred = await mock_adapter.provision_credential(
            org_id="org_default",  # In production: from require_principal
            agent_id=body.agent_id,
            scope=scope,
            encryption=encryption,
        )
    else:
        cred = DelegatedCredential(
            org_id="org_default",
            agent_id=body.agent_id,
            network=network,
            status=CredentialStatus.ACTIVE,
            token_reference=f"tok_placeholder_{body.network}",
            token_encrypted=b"placeholder",
            scope=scope,
            consent_id=body.consent_id,
        )

    cred.consent_id = body.consent_id
    cred_id = await cred_store.store(cred)
    return {"credential_id": cred_id, "status": cred.status.value}


@router.get("")
async def list_credentials(
    request: Request,
    agent_id: Optional[str] = None,
    cred_store=Depends(_get_credential_store),
):
    """List credentials for org/agent."""
    if agent_id:
        creds = await cred_store.get_for_agent(agent_id)
    else:
        creds = []  # In production: list by org from require_principal
    return {
        "credentials": [c.to_dict() for c in creds],
        "count": len(creds),
    }


@router.get("/{credential_id}")
async def get_credential(
    credential_id: str,
    cred_store=Depends(_get_credential_store),
):
    """Get credential details (masked token)."""
    cred = await cred_store.get(credential_id)
    if cred is None:
        raise HTTPException(404, "Credential not found")
    return cred.to_dict()


@router.patch("/{credential_id}/scope")
async def tighten_scope(
    credential_id: str,
    body: TightenScopeRequest,
    cred_store=Depends(_get_credential_store),
):
    """Tighten scope only (never loosen)."""
    from sardis_v2_core.delegated_credential import CredentialScope

    cred = await cred_store.get(credential_id)
    if cred is None:
        raise HTTPException(404, "Credential not found")

    new_scope = CredentialScope(
        max_per_tx=Decimal(body.max_per_tx) if body.max_per_tx else cred.scope.max_per_tx,
        daily_limit=Decimal(body.daily_limit) if body.daily_limit else cred.scope.daily_limit,
        allowed_mccs=body.allowed_mccs if body.allowed_mccs is not None else cred.scope.allowed_mccs,
        allowed_merchant_ids=(
            body.allowed_merchant_ids
            if body.allowed_merchant_ids is not None
            else cred.scope.allowed_merchant_ids
        ),
        expires_at=cred.scope.expires_at,
    )

    if not new_scope.is_tighter_than(cred.scope):
        raise HTTPException(400, "Scope can only be tightened, not expanded")

    # Apply via reprovision with same consent
    await cred_store.reprovision(credential_id, new_scope, cred.consent_id or "")
    return {"status": "scope_tightened", "credential_id": credential_id}


@router.post("/{credential_id}/rotate")
async def rotate_credential(
    credential_id: str,
    cred_store=Depends(_get_credential_store),
):
    """Rotate token (same authority, new token)."""
    cred = await cred_store.get(credential_id)
    if cred is None:
        raise HTTPException(404, "Credential not found")
    # In production: call provider to issue new token
    new_token = b"rotated_token_placeholder"
    updated = await cred_store.rotate(credential_id, new_token)
    return {"status": "rotated", "credential_id": updated.credential_id}


@router.post("/{credential_id}/reprovision")
async def reprovision_credential(
    credential_id: str,
    body: ReprovisionRequest,
    cred_store=Depends(_get_credential_store),
    consent_store=Depends(_get_consent_store),
):
    """New authority grant (requires new consent)."""
    from sardis_v2_core.delegated_credential import CredentialScope

    valid = await consent_store.is_consent_valid(body.consent_id)
    if not valid:
        raise HTTPException(400, "Invalid or expired consent")

    new_scope = CredentialScope(
        max_per_tx=Decimal(body.max_per_tx or "500"),
        daily_limit=Decimal(body.daily_limit or "2000"),
        allowed_mccs=body.allowed_mccs or [],
        allowed_merchant_ids=body.allowed_merchant_ids or [],
    )

    updated = await cred_store.reprovision(credential_id, new_scope, body.consent_id)
    return {"status": "reprovisioned", "credential_id": updated.credential_id}


@router.post("/{credential_id}/suspend")
async def suspend_credential(
    credential_id: str,
    cred_store=Depends(_get_credential_store),
):
    """Suspend a credential."""
    from sardis_v2_core.delegated_credential import CredentialStatus

    cred = await cred_store.get(credential_id)
    if cred is None:
        raise HTTPException(404, "Credential not found")
    await cred_store.update_status(credential_id, CredentialStatus.SUSPENDED)
    return {"status": "suspended", "credential_id": credential_id}


@router.post("/{credential_id}/revoke")
async def revoke_credential(
    credential_id: str,
    body: RevokeRequest,
    cred_store=Depends(_get_credential_store),
):
    """Revoke a credential permanently."""
    cred = await cred_store.get(credential_id)
    if cred is None:
        raise HTTPException(404, "Credential not found")
    await cred_store.revoke(credential_id, body.reason)
    return {"status": "revoked", "credential_id": credential_id}
