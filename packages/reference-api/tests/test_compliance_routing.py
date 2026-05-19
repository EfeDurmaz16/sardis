from fastapi import FastAPI

from server.routes.compliance import compliance
from server.routing.compliance import (
    register_compliance_export_routes,
    register_compliance_routes,
    register_kyc_onboarding_routes,
)


def test_register_compliance_routes_mounts_core_and_public_paths_with_dependencies() -> None:
    app = FastAPI()
    kyc_service = object()
    sanctions_service = object()
    audit_store = object()
    kya_service = object()
    policy_store = object()
    approval_service = object()

    register_compliance_routes(
        app,
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
        audit_store=audit_store,
        kya_service=kya_service,
        policy_store=policy_store,
        approval_service=approval_service,
    )

    paths = {route.path for route in app.routes}
    assert "/api/v2/compliance/kyc/verify" in paths
    assert "/api/v2/compliance/sanctions/screen" in paths
    assert "/api/v2/compliance/audit/recent" in paths
    assert "/api/v2/compliance/webhooks/persona" in paths

    deps = app.dependency_overrides[compliance.get_deps]()
    assert deps.kyc_service is kyc_service
    assert deps.sanctions_service is sanctions_service
    assert deps.audit_store is audit_store
    assert deps.kya_service is kya_service
    assert deps.policy_store is policy_store
    assert deps.approval_service is approval_service


def test_register_kyc_onboarding_routes_mounts_public_kyc_paths() -> None:
    app = FastAPI()

    register_kyc_onboarding_routes(app)

    paths = {route.path for route in app.routes}
    assert "/api/v2/kyc/initiate" in paths
    assert "/api/v2/kyc/status" in paths
    assert "/api/v2/kyc/webhook" in paths
    assert "/api/v2/kyc/retry" in paths


def test_register_compliance_export_routes_mounts_export_path() -> None:
    app = FastAPI()

    register_compliance_export_routes(app)

    paths = {route.path for route in app.routes}
    assert "/api/v2/compliance/export" in paths
