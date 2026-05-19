"""Compliance route registration helpers."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from server.routes.compliance import compliance_export, kyc_onboarding, screening


def register_compliance_routes(
    app: FastAPI,
    *,
    kyc_service: Any,
    sanctions_service: Any,
    audit_store: Any,
    kya_service: Any,
    policy_store: Any,
    approval_service: Any,
) -> None:
    """Register compliance screening, KYC/KYA, audit, and provider webhook routes."""
    app.dependency_overrides[screening.get_deps] = lambda: screening.ComplianceDependencies(
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
        audit_store=audit_store,
        kya_service=kya_service,
        policy_store=policy_store,
        approval_service=approval_service,
    )
    app.include_router(screening.router, prefix="/api/v2/compliance", tags=["compliance"])
    if hasattr(screening, "public_router"):
        app.include_router(screening.public_router, prefix="/api/v2/compliance", tags=["compliance"])


def register_kyc_onboarding_routes(app: FastAPI) -> None:
    """Register self-serve KYC initiation, status, webhook, and retry routes."""
    app.include_router(kyc_onboarding.router)


def register_compliance_export_routes(app: FastAPI) -> None:
    """Register audit-ready compliance evidence export routes."""
    app.include_router(compliance_export.router)
