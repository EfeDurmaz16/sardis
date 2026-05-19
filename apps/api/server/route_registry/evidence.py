"""Evidence and audit route registration helpers."""
from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI

from server.routes.evidence import attestation, audit_anchors, evidence_export, records

logger = logging.getLogger("server.api.route_registry.evidence")


def register_audit_anchor_routes(
    app: FastAPI,
    *,
    chain_executor: Any,
    ledger_store: Any,
) -> None:
    """Register blockchain audit-anchor routes."""
    try:
        from sardis_ledger.anchor import AnchorChainProvider, AnchorConfig, LedgerAnchor

        anchor_chain = os.getenv("SARDIS_ANCHOR_CHAIN", "base")
        anchor_config = AnchorConfig(chain=anchor_chain)
        chain_provider = None
        if anchor_config.contract_address and chain_executor:
            chain_provider = AnchorChainProvider(
                chain_executor=chain_executor,
                chain=anchor_chain,
            )
            logger.info(
                "Audit anchor chain provider wired: chain=%s, contract=%s",
                anchor_chain,
                anchor_config.contract_address,
            )
        anchor_service = LedgerAnchor(config=anchor_config, chain_provider=chain_provider)
        app.dependency_overrides[audit_anchors.get_anchor_deps] = (
            lambda: audit_anchors.AnchorDependencies(
                anchor_service=anchor_service,
                ledger_store=ledger_store,
            )
        )
        logger.info("Audit anchor service initialized (chain_provider=%s)", "real" if chain_provider else "simulated")
    except ImportError:
        logger.warning("sardis-ledger anchor module not available, audit anchoring disabled")
    app.include_router(audit_anchors.router)


def register_evidence_routes(app: FastAPI) -> None:
    """Register evidence capture, export, and attestation routes."""
    app.include_router(records.router, prefix="/api/v2/evidence", tags=["evidence"])
    app.include_router(evidence_export.router, prefix="/api/v2/evidence/export", tags=["evidence-export"])
    app.include_router(attestation.router, prefix="/api/v2", tags=["attestation"])
