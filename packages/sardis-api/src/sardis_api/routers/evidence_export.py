"""Evidence export bundle endpoint.

Provides a one-click export of all available evidence artifacts for a
transaction: ledger details, policy decision, approval state, execution
receipt, and webhook delivery logs.

Sections that have no data are marked ``{ "status": "not_available" }``
rather than raising an error, so consumers always receive a complete
structural bundle.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

_logger = logging.getLogger("sardis.api.evidence_export")

EVIDENCE_SIGNING_KEY = os.getenv("SARDIS_EVIDENCE_SIGNING_KEY", "sardis-dev-signing-key")

router = APIRouter(dependencies=[Depends(require_principal)])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class EvidenceSection(BaseModel):
    """One section of the evidence bundle."""

    status: str = "available"  # "available" or "not_available"
    data: dict[str, Any] | None = None
    reason: str | None = None


class IntegrityMetadata(BaseModel):
    """HMAC-SHA256 integrity metadata for tamper detection."""

    algorithm: str = "hmac-sha256"
    content_hash: str  # SHA-256 of the canonical JSON sections
    signature: str  # HMAC-SHA256 of content_hash with signing key
    signed_at: str
    signer: str = "sardis-evidence-service"
    version: str = "1.0"


class EvidenceBundle(BaseModel):
    """Complete evidence export bundle for a single transaction."""

    tx_id: str
    exported_at: str
    version: str = "1.0"
    sections: dict[str, EvidenceSection] = Field(default_factory=dict)
    integrity: IntegrityMetadata | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _not_available(reason: str) -> EvidenceSection:
    return EvidenceSection(status="not_available", data=None, reason=reason)


def _available(data: dict[str, Any]) -> EvidenceSection:
    return EvidenceSection(status="available", data=data)


async def _collect_sections(tx_id: str) -> dict[str, EvidenceSection]:
    """Attempt to collect all evidence sections for *tx_id*.

    Each section is fetched independently; failures are caught and surfaced
    as ``not_available`` rather than propagating as HTTP errors.
    """
    sections: dict[str, EvidenceSection] = {}

    # --- Transaction details (ledger) ---
    try:
        # Future: query ledger store / agent_repository for tx_id
        sections["transaction"] = _not_available(
            "Transaction lookup requires ledger query"
        )
    except Exception as exc:  # noqa: BLE001
        _logger.debug("transaction section failed for tx_id=%s: %s", tx_id, exc)
        sections["transaction"] = _not_available(str(exc))

    # --- Policy decision ---
    try:
        # Future: query evidence store for policy decision linked to tx_id
        sections["policy_decision"] = _not_available(
            "Policy decision lookup requires evidence store"
        )
    except Exception as exc:  # noqa: BLE001
        _logger.debug("policy_decision section failed for tx_id=%s: %s", tx_id, exc)
        sections["policy_decision"] = _not_available(str(exc))

    # --- Approval state ---
    try:
        # Future: query approval_service for approval linked to tx_id
        sections["approval"] = _not_available(
            "No approval record found for this transaction"
        )
    except Exception as exc:  # noqa: BLE001
        _logger.debug("approval section failed for tx_id=%s: %s", tx_id, exc)
        sections["approval"] = _not_available(str(exc))

    # --- Execution receipt (chain tx hash, block, confirmations) ---
    try:
        # Future: query chain indexer / receipts store for tx_id
        sections["execution_receipt"] = _not_available(
            "Chain execution receipt requires indexer query"
        )
    except Exception as exc:  # noqa: BLE001
        _logger.debug("execution_receipt section failed for tx_id=%s: %s", tx_id, exc)
        sections["execution_receipt"] = _not_available(str(exc))

    # --- Ledger artifacts ---
    try:
        sections["ledger_artifacts"] = _not_available(
            "Ledger artifact export requires append-only ledger query"
        )
    except Exception as exc:  # noqa: BLE001
        _logger.debug("ledger_artifacts section failed for tx_id=%s: %s", tx_id, exc)
        sections["ledger_artifacts"] = _not_available(str(exc))

    # --- Side effects ---
    try:
        sections["side_effects"] = _not_available(
            "Side-effect export requires downstream execution log query"
        )
    except Exception as exc:  # noqa: BLE001
        _logger.debug("side_effects section failed for tx_id=%s: %s", tx_id, exc)
        sections["side_effects"] = _not_available(str(exc))

    # --- Exception state ---
    try:
        sections["exception_state"] = _not_available(
            "Exception workflow is not yet promoted to a durable store"
        )
    except Exception as exc:  # noqa: BLE001
        _logger.debug("exception_state section failed for tx_id=%s: %s", tx_id, exc)
        sections["exception_state"] = _not_available(str(exc))

    # --- Webhook delivery logs ---
    try:
        # Future: query webhook delivery history for tx_id
        sections["webhook_logs"] = _not_available(
            "Webhook delivery logs require alert history query"
        )
    except Exception as exc:  # noqa: BLE001
        _logger.debug("webhook_logs section failed for tx_id=%s: %s", tx_id, exc)
        sections["webhook_logs"] = _not_available(str(exc))

    return sections


def _compute_integrity(sections: dict[str, EvidenceSection]) -> IntegrityMetadata:
    """Compute HMAC-SHA256 integrity metadata for the given sections."""
    sections_json = json.dumps(
        {k: v.model_dump() for k, v in sections.items()},
        sort_keys=True,
        separators=(",", ":"),
    )
    content_hash = hashlib.sha256(sections_json.encode()).hexdigest()
    signature = hmac.new(
        EVIDENCE_SIGNING_KEY.encode(),
        content_hash.encode(),
        hashlib.sha256,
    ).hexdigest()
    return IntegrityMetadata(
        content_hash=content_hash,
        signature=signature,
        signed_at=datetime.now(UTC).isoformat(),
    )


def _build_bundle(tx_id: str, sections: dict[str, EvidenceSection]) -> EvidenceBundle:
    integrity = _compute_integrity(sections)
    return EvidenceBundle(
        tx_id=tx_id,
        exported_at=datetime.now(UTC).isoformat(),
        sections=sections,
        integrity=integrity,
    )


# ---------------------------------------------------------------------------
# Verification models
# ---------------------------------------------------------------------------


class VerifyRequest(BaseModel):
    """Request body for bundle integrity verification."""

    tx_id: str
    content_hash: str
    signature: str


class VerifyResponse(BaseModel):
    """Result of a bundle integrity check."""

    valid: bool
    message: str
    verified_at: str


# ---------------------------------------------------------------------------
# Endpoints
# NOTE: /verify must be declared before /{tx_id} so FastAPI matches the
#       static path first and does not swallow it as a path parameter.
# ---------------------------------------------------------------------------


@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify the integrity of an exported evidence bundle",
    description=(
        "Re-computes the expected HMAC-SHA256 signature from the supplied "
        "content_hash and compares it against the provided signature using a "
        "constant-time comparison. Returns valid=true only if the signatures "
        "match, indicating the bundle has not been tampered with."
    ),
)
async def verify_evidence_bundle(
    body: VerifyRequest,
    _principal: Principal = Depends(require_principal),
) -> VerifyResponse:
    """Verify the integrity of an exported evidence bundle."""
    _logger.info("evidence verify requested tx_id=%s", body.tx_id)
    expected_sig = hmac.new(
        EVIDENCE_SIGNING_KEY.encode(),
        body.content_hash.encode(),
        hashlib.sha256,
    ).hexdigest()

    valid = hmac.compare_digest(expected_sig, body.signature)

    return VerifyResponse(
        valid=valid,
        message=(
            "Evidence bundle integrity verified"
            if valid
            else "INTEGRITY CHECK FAILED: bundle may have been tampered with"
        ),
        verified_at=datetime.now(UTC).isoformat(),
    )


@router.post(
    "/{tx_id}",
    response_model=EvidenceBundle,
    summary="Export a complete evidence bundle for a transaction",
    description=(
        "Collects all available evidence artifacts for the given transaction ID "
        "and returns them as a structured JSON bundle. Sections that cannot be "
        "fetched are marked ``not_available`` with an explanatory reason."
    ),
)
async def export_evidence_bundle(
    tx_id: str,
    principal: Principal = Depends(require_principal),
) -> EvidenceBundle:
    """Export a complete evidence bundle for *tx_id*."""
    _logger.info(
        "evidence export requested tx_id=%s org_id=%s",
        tx_id,
        principal.org_id,
    )
    sections = await _collect_sections(tx_id)
    bundle = _build_bundle(tx_id, sections)
    return bundle


@router.get(
    "/{tx_id}/download",
    summary="Download evidence bundle as a JSON file",
    description=(
        "Returns the same evidence bundle as POST /{tx_id} but with "
        "Content-Disposition headers set so browsers treat it as a file download. "
        "Actual PDF generation is future work — this endpoint exports JSON."
    ),
)
async def download_evidence_bundle(
    tx_id: str,
    principal: Principal = Depends(require_principal),
) -> JSONResponse:
    """Return the evidence bundle as a downloadable JSON file."""
    _logger.info(
        "evidence download requested tx_id=%s org_id=%s",
        tx_id,
        principal.org_id,
    )
    sections = await _collect_sections(tx_id)
    bundle = _build_bundle(tx_id, sections)
    return JSONResponse(
        content=bundle.model_dump(),
        headers={
            "Content-Disposition": f'attachment; filename="sardis-evidence-{tx_id}.json"',
            "Content-Type": "application/json",
        },
    )
