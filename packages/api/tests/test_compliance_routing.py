from fastapi import FastAPI

from sardis_server.routing.compliance import (
    register_compliance_export_routes,
    register_kyc_onboarding_routes,
)


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
