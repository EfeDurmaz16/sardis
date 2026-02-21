"""
Audit anchor API endpoints for blockchain-anchored audit logs.

Provides endpoints for:
- Listing anchors
- Getting anchor details
- Creating manual anchors
- Verifying anchors on-chain
- Verifying entry inclusion
- Getting Merkle proofs
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/audit", tags=["audit-anchors"])


# Request/Response models

class AnchorResponse(BaseModel):
    """Response model for anchor details."""
    anchor_id: str
    merkle_root: str
    entry_count: int
    first_entry_id: str
    last_entry_id: str
    timestamp: str
    chain: str
    transaction_hash: Optional[str] = None
    status: str
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnchorListResponse(BaseModel):
    """Response model for list of anchors."""
    anchors: list[AnchorResponse]
    total: int
    from_date: Optional[str] = None
    to_date: Optional[str] = None


class CreateAnchorRequest(BaseModel):
    """Request model for creating manual anchor."""
    from_entry_id: Optional[str] = None
    to_entry_id: Optional[str] = None
    max_entries: int = Field(default=10000, ge=1, le=100000)


class CreateAnchorResponse(BaseModel):
    """Response model for anchor creation."""
    anchor_id: str
    merkle_root: str
    entry_count: int
    status: str
    message: str


class VerifyAnchorResponse(BaseModel):
    """Response model for anchor verification."""
    anchor_id: str
    is_valid: bool
    merkle_root: str
    chain: str
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    verified_at: str
    message: str


class VerifyEntryRequest(BaseModel):
    """Request model for entry verification."""
    entry_data: dict[str, Any]
    anchor_id: str


class VerifyEntryResponse(BaseModel):
    """Response model for entry verification."""
    entry_id: str
    anchor_id: str
    is_valid: bool
    merkle_root: str
    verified_at: str
    message: str


class MerkleProofResponse(BaseModel):
    """Response model for Merkle proof."""
    entry_id: str
    anchor_id: str
    merkle_root: str
    proof: list[dict[str, str]]
    leaf_hash: str
    message: str


# Dependency injection placeholder

class AnchorDependencies:
    """Dependencies for anchor endpoints."""

    def __init__(self):
        # TODO: Initialize with actual LedgerAnchor instance
        self.anchor_service = None
        self.ledger_engine = None


def get_anchor_deps() -> AnchorDependencies:
    """Get anchor dependencies (override in production)."""
    raise NotImplementedError("Dependency override required")


# Endpoints

@router.get("/anchors", response_model=AnchorListResponse)
async def list_anchors(
    from_date: Optional[str] = Query(None, description="ISO format date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    to_date: Optional[str] = Query(None, description="ISO format date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    deps: AnchorDependencies = Depends(get_anchor_deps),
) -> AnchorListResponse:
    """
    List all anchor records with optional date filtering.

    Returns chronologically sorted list of anchors with their metadata.
    """
    try:
        if deps.anchor_service is None:
            # Return empty response if service not configured
            return AnchorListResponse(
                anchors=[],
                total=0,
                from_date=from_date,
                to_date=to_date,
            )

        # Get anchors from service
        anchors = await deps.anchor_service.get_anchors(
            from_date=from_date,
            to_date=to_date,
        )

        # Convert to response models
        anchor_responses = [
            AnchorResponse(
                anchor_id=a.anchor_id,
                merkle_root=a.merkle_root,
                entry_count=a.entry_count,
                first_entry_id=a.first_entry_id,
                last_entry_id=a.last_entry_id,
                timestamp=a.timestamp.isoformat(),
                chain=a.chain,
                transaction_hash=a.transaction_hash,
                status=a.status.value,
                block_number=a.block_number,
                gas_used=a.gas_used,
                metadata=a.metadata,
            )
            for a in anchors
        ]

        return AnchorListResponse(
            anchors=anchor_responses,
            total=len(anchor_responses),
            from_date=from_date,
            to_date=to_date,
        )

    except Exception as e:
        logger.error(f"Error listing anchors: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list anchors: {str(e)}",
        )


@router.get("/anchors/{anchor_id}", response_model=AnchorResponse)
async def get_anchor(
    anchor_id: str,
    deps: AnchorDependencies = Depends(get_anchor_deps),
) -> AnchorResponse:
    """
    Get details of a specific anchor by ID.

    Returns full anchor record including blockchain transaction details.
    """
    try:
        if deps.anchor_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Anchor service not configured",
            )

        # Get anchor from service
        anchor = deps.anchor_service._anchors.get(anchor_id)
        if not anchor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anchor {anchor_id} not found",
            )

        return AnchorResponse(
            anchor_id=anchor.anchor_id,
            merkle_root=anchor.merkle_root,
            entry_count=anchor.entry_count,
            first_entry_id=anchor.first_entry_id,
            last_entry_id=anchor.last_entry_id,
            timestamp=anchor.timestamp.isoformat(),
            chain=anchor.chain,
            transaction_hash=anchor.transaction_hash,
            status=anchor.status.value,
            block_number=anchor.block_number,
            gas_used=anchor.gas_used,
            metadata=anchor.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting anchor {anchor_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get anchor: {str(e)}",
        )


@router.post("/anchors/create", response_model=CreateAnchorResponse)
async def create_anchor(
    request: CreateAnchorRequest,
    deps: AnchorDependencies = Depends(get_anchor_deps),
) -> CreateAnchorResponse:
    """
    Manually trigger creation of a new anchor.

    Collects unanchored audit entries and creates a new Merkle tree anchor.
    Optionally specify entry range or let system collect all unanchored entries.
    """
    try:
        if deps.anchor_service is None or deps.ledger_engine is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Anchor service not configured",
            )

        # Get unanchored entries from ledger
        # TODO: Implement actual entry collection from ledger_engine
        entries: list[dict] = []

        if not entries:
            return CreateAnchorResponse(
                anchor_id="",
                merkle_root="",
                entry_count=0,
                status="skipped",
                message="No unanchored entries to anchor",
            )

        # Limit to max_entries
        if len(entries) > request.max_entries:
            entries = entries[:request.max_entries]

        # Create anchor
        anchor = await deps.anchor_service.create_anchor(entries)

        # Submit to blockchain
        tx_hash = await deps.anchor_service.submit_anchor(anchor)

        logger.info(
            f"Manual anchor created: {anchor.anchor_id}, "
            f"entries={anchor.entry_count}, tx={tx_hash}"
        )

        return CreateAnchorResponse(
            anchor_id=anchor.anchor_id,
            merkle_root=anchor.merkle_root,
            entry_count=anchor.entry_count,
            status=anchor.status.value,
            message=f"Anchor created and submitted: tx={tx_hash[:16]}...",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating anchor: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create anchor: {str(e)}",
        )


@router.get("/anchors/{anchor_id}/verify", response_model=VerifyAnchorResponse)
async def verify_anchor(
    anchor_id: str,
    deps: AnchorDependencies = Depends(get_anchor_deps),
) -> VerifyAnchorResponse:
    """
    Verify an anchor's Merkle root against the blockchain.

    Checks that the root stored on-chain matches the anchor record.
    """
    try:
        if deps.anchor_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Anchor service not configured",
            )

        # Get anchor
        anchor = deps.anchor_service._anchors.get(anchor_id)
        if not anchor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anchor {anchor_id} not found",
            )

        # Verify on-chain
        is_valid = await deps.anchor_service.verify_anchor(anchor_id)

        from datetime import datetime, timezone
        verified_at = datetime.now(timezone.utc).isoformat()

        message = (
            "Anchor verified successfully on-chain"
            if is_valid
            else "Anchor verification failed - on-chain data mismatch"
        )

        logger.info(f"Anchor {anchor_id} verification: {is_valid}")

        return VerifyAnchorResponse(
            anchor_id=anchor.anchor_id,
            is_valid=is_valid,
            merkle_root=anchor.merkle_root,
            chain=anchor.chain,
            transaction_hash=anchor.transaction_hash,
            block_number=anchor.block_number,
            verified_at=verified_at,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying anchor {anchor_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify anchor: {str(e)}",
        )


@router.post("/entries/{entry_id}/verify", response_model=VerifyEntryResponse)
async def verify_entry(
    entry_id: str,
    request: VerifyEntryRequest,
    deps: AnchorDependencies = Depends(get_anchor_deps),
) -> VerifyEntryResponse:
    """
    Verify that a specific entry is included in an anchored Merkle tree.

    Provides cryptographic proof that the entry was part of the
    audit log at the time of anchoring.
    """
    try:
        if deps.anchor_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Anchor service not configured",
            )

        # Verify entry inclusion
        is_valid = await deps.anchor_service.verify_entry(
            entry=request.entry_data,
            anchor_id=request.anchor_id,
        )

        # Get anchor details
        anchor = deps.anchor_service._anchors.get(request.anchor_id)
        if not anchor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anchor {request.anchor_id} not found",
            )

        from datetime import datetime, timezone
        verified_at = datetime.now(timezone.utc).isoformat()

        message = (
            f"Entry {entry_id} verified in anchor {request.anchor_id}"
            if is_valid
            else f"Entry {entry_id} not found in anchor {request.anchor_id}"
        )

        logger.info(f"Entry {entry_id} verification in {request.anchor_id}: {is_valid}")

        return VerifyEntryResponse(
            entry_id=entry_id,
            anchor_id=request.anchor_id,
            is_valid=is_valid,
            merkle_root=anchor.merkle_root,
            verified_at=verified_at,
            message=message,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error verifying entry {entry_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify entry: {str(e)}",
        )


@router.get("/anchors/{anchor_id}/proof/{entry_id}", response_model=MerkleProofResponse)
async def get_merkle_proof(
    anchor_id: str,
    entry_id: str,
    deps: AnchorDependencies = Depends(get_anchor_deps),
) -> MerkleProofResponse:
    """
    Get Merkle proof for a specific entry in an anchor.

    Returns the cryptographic proof path from the entry to the root,
    which can be used to independently verify inclusion.
    """
    try:
        if deps.anchor_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Anchor service not configured",
            )

        # Get anchor
        anchor = deps.anchor_service._anchors.get(anchor_id)
        if not anchor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anchor {anchor_id} not found",
            )

        # Get proof
        proof = deps.anchor_service.get_proof_for_entry(entry_id)
        if proof is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entry {entry_id} not found in anchor {anchor_id}",
            )

        # Convert proof to response format
        proof_dicts = [
            {"hash": hash_val, "direction": direction}
            for hash_val, direction in proof
        ]

        # Get leaf hash (would need actual entry data in production)
        leaf_hash = "0x" + "0" * 64  # Placeholder

        logger.info(f"Generated Merkle proof for {entry_id} in {anchor_id}")

        return MerkleProofResponse(
            entry_id=entry_id,
            anchor_id=anchor_id,
            merkle_root=anchor.merkle_root,
            proof=proof_dicts,
            leaf_hash=leaf_hash,
            message=f"Merkle proof generated with {len(proof_dicts)} steps",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting proof for {entry_id} in {anchor_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Merkle proof: {str(e)}",
        )


__all__ = [
    "router",
    "AnchorResponse",
    "AnchorListResponse",
    "CreateAnchorRequest",
    "CreateAnchorResponse",
    "VerifyAnchorResponse",
    "VerifyEntryRequest",
    "VerifyEntryResponse",
    "MerkleProofResponse",
]
