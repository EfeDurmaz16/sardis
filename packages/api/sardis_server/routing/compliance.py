"""Compliance route registration helpers."""
from __future__ import annotations

from fastapi import FastAPI

from sardis_server.routes.compliance import compliance_export, kyc_onboarding


def register_kyc_onboarding_routes(app: FastAPI) -> None:
    """Register self-serve KYC initiation, status, webhook, and retry routes."""
    app.include_router(kyc_onboarding.router)


def register_compliance_export_routes(app: FastAPI) -> None:
    """Register audit-ready compliance evidence export routes."""
    app.include_router(compliance_export.router)
