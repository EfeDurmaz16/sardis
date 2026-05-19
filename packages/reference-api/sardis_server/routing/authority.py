"""Authority, mandate, and approval route registration helpers."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI

from sardis_server.routes.authority import (
    ap2,
    credentials,
    facility_requests,
    mandates,
    mvp,
    spending_mandates,
)
from sardis_server.routes.authority import approval_config as approval_config_router
from sardis_server.routes.authority import mandate_delegation as mandate_delegation_router
from sardis_server.routes.authority import mandate_subscriptions as mandate_subscriptions_router

try:
    from sardis_server.routes.authority import approvals as approvals_router
except ImportError:
    approvals_router = None  # type: ignore[assignment]

logger = logging.getLogger("sardis_server.api.routing.authority")


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


def register_facility_request_routes(
    app: FastAPI,
    *,
    repository: Any,
    adapter: Any,
    approval_service: Any,
) -> None:
    """Register facility gate request and provider webhook routes."""
    from sardis_server.services.facility_gate_authority import (
        RepositoryBackedFacilityMandateResolver,
        RepositoryBackedFacilityPolicyResolver,
        RepositoryBackedFacilityRecordResolver,
    )

    app.dependency_overrides[facility_requests.get_deps] = lambda: facility_requests.FacilityDependencies(
        repository=repository,
        adapter=adapter,
        approval_service=approval_service,
        mandate_resolver=RepositoryBackedFacilityMandateResolver(
            repository,
            fallback=facility_requests.SnapshotBackedFacilityMandateResolver(),
        ),
        facility_resolver=RepositoryBackedFacilityRecordResolver(
            repository,
            fallback=facility_requests.SnapshotBackedFacilityRecordResolver(
                facility_requests._facility_from_snapshot
            ),
        ),
        policy_resolver=RepositoryBackedFacilityPolicyResolver(repository),
    )
    app.include_router(
        facility_requests.router,
        prefix="/api/v2/facility-requests",
        tags=["facility-gate"],
    )
    app.include_router(
        facility_requests.provider_webhooks_router,
        prefix="/api/v2/provider-webhooks",
        tags=["facility-gate-webhooks"],
    )


def register_credential_routes(app: FastAPI) -> None:
    """Register delegated credential authority routes."""
    app.include_router(credentials.router)


def register_spending_mandate_routes(app: FastAPI) -> None:
    """Register spending mandate CRUD and lifecycle routes."""
    app.include_router(
        spending_mandates.router,
        prefix="/api/v2/spending-mandates",
        tags=["spending-mandates"],
    )


def register_mandate_delegation_routes(app: FastAPI) -> None:
    """Register scoped mandate delegation routes."""
    app.include_router(
        mandate_delegation_router.router,
        prefix="/api/v2",
        tags=["mandate-delegation"],
    )


def register_mandate_subscription_routes(app: FastAPI) -> None:
    """Register recurring mandate subscription routes."""
    app.include_router(
        mandate_subscriptions_router.router,
        prefix="/api/v2",
        tags=["mandate-subscriptions"],
    )
