"""Authority, mandate, and approval route registration helpers."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI

from sardis_api.routers import ap2, mandates, mvp
from sardis_api.routers import approval_config as approval_config_router

try:
    from sardis_api.routers import approvals as approvals_router
except ImportError:
    approvals_router = None  # type: ignore[assignment]

logger = logging.getLogger("sardis.api.routing.authority")


def register_authority_routes(
    app: FastAPI,
    *,
    wallet_manager: Any,
    chain_executor: Any,
    verifier: Any,
    ledger: Any,
    compliance: Any,
    wallet_repository: Any,
    agent_repo: Any,
    orchestrator: Any,
    kyc_service: Any,
    sanctions_service: Any,
    kya_service: Any,
    settings: Any,
    policy_store: Any,
    audit_store: Any,
    identity_registry: Any,
    dsn: str,
) -> Any | None:
    """Register mandate/AP2/MVP authority routes and return approval service."""
    approval_service = None

    app.dependency_overrides[mandates.get_deps] = lambda: mandates.Dependencies(  # type: ignore[arg-type]
        wallet_manager=wallet_manager,
        chain_executor=chain_executor,
        verifier=verifier,
        ledger=ledger,
        compliance=compliance,
        wallet_repository=wallet_repository,
        agent_repo=agent_repo,
    )
    app.include_router(mandates.router, prefix="/api/v2/mandates")

    app.dependency_overrides[ap2.get_deps] = lambda: ap2.Dependencies(  # type: ignore[arg-type]
        verifier=verifier,
        orchestrator=orchestrator,
        wallet_repo=wallet_repository,
        agent_repo=agent_repo,
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
        kya_service=kya_service,
        approval_service=approval_service,
        settings=settings,
        wallet_manager=wallet_manager,
        policy_store=policy_store,
        audit_store=audit_store,
    )
    app.include_router(ap2.router, prefix="/api/v2/ap2")

    app.dependency_overrides[mvp.get_deps] = lambda: mvp.Dependencies(  # type: ignore[arg-type]
        verifier=verifier,
        ledger=ledger,
        identity_registry=identity_registry,
        settings=settings,
        wallet_repo=wallet_repository,
        agent_repo=agent_repo,
        wallet_manager=wallet_manager,
        compliance=compliance,
        payment_orchestrator=orchestrator,
    )
    app.include_router(mvp.router, prefix="/api/v2/mvp", tags=["mvp"])

    if approvals_router is not None:
        try:
            from sardis_v2_core.approval_repository import ApprovalRepository
            from sardis_v2_core.approval_service import ApprovalService

            approval_repo = ApprovalRepository(dsn=dsn)
            approval_service = ApprovalService(repository=approval_repo)
            app.dependency_overrides[approvals_router.get_deps] = lambda: approvals_router.ApprovalsDependencies(  # type: ignore[arg-type]
                approval_service=approval_service,
                approval_repo=approval_repo,
            )
            app.include_router(approvals_router.router, prefix="/api/v2/approvals", tags=["approvals"])
            app.include_router(
                approval_config_router.router,
                prefix="/api/v2/approvals/config",
                tags=["approval-config"],
            )
            logger.info("Approvals router registered")
        except ImportError as exc:
            logger.warning("Approvals dependencies not available: %s", exc)
    else:
        logger.info("Approvals router not yet available (dependencies not complete)")

    return approval_service
