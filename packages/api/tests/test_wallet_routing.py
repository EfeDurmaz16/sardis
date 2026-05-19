from fastapi import FastAPI

from sardis_server.routes.wallets import cpn, funding_capabilities, ramp, treasury, treasury_ops
from sardis_server.routing.wallets import (
    register_cpn_routes,
    register_funding_capability_routes,
    register_ramp_routes,
    register_treasury_routes,
)


def test_register_ramp_routes_wires_dependencies_and_public_routes():
    app = FastAPI()
    wallet_repo = object()
    agent_repo = object()
    offramp_service = object()
    fiat_ramp = object()

    register_ramp_routes(
        app,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        offramp_service=offramp_service,
        onramper_api_key="onramper_key",
        onramper_webhook_secret="onramper_secret",
        bridge_webhook_secret="bridge_secret",
        fiat_ramp=fiat_ramp,
    )

    deps = app.dependency_overrides[ramp.get_deps]()
    assert deps.wallet_repo is wallet_repo
    assert deps.agent_repo is agent_repo
    assert deps.offramp_service is offramp_service
    assert deps.onramper_api_key == "onramper_key"
    assert deps.onramper_webhook_secret == "onramper_secret"
    assert deps.bridge_webhook_secret == "bridge_secret"
    assert deps.fiat_ramp is fiat_ramp

    paths = {route.path for route in app.routes}
    assert "/api/v2/ramp/onramp/widget" in paths
    assert "/api/v2/ramp/onramp/webhook" in paths
    assert "/api/v2/ramp/bridge/webhook" in paths


def test_register_treasury_routes_wires_dependencies_and_public_routes():
    app = FastAPI()
    treasury_repo = object()
    lithic_client = object()
    canonical_repo = object()

    register_treasury_routes(
        app,
        treasury_repo=treasury_repo,
        lithic_treasury_client=lithic_client,
        lithic_webhook_secret="lithic_secret",
        canonical_ledger_repo=canonical_repo,
    )

    treasury_deps = app.dependency_overrides[treasury.get_deps]()
    assert treasury_deps.treasury_repo is treasury_repo
    assert treasury_deps.lithic_client is lithic_client
    assert treasury_deps.lithic_webhook_secret == "lithic_secret"
    assert treasury_deps.canonical_repo is canonical_repo

    treasury_ops_deps = app.dependency_overrides[treasury_ops.get_deps]()
    assert treasury_ops_deps.canonical_repo is canonical_repo

    paths = {route.path for route in app.routes}
    assert "/api/v2/treasury/financial-accounts" in paths
    assert "/api/v2/webhooks/lithic/payments" in paths
    assert "/api/v2/treasury/ops/journeys" in paths


def test_register_cpn_routes_wires_dependencies_and_webhook_route():
    app = FastAPI()
    treasury_repo = object()
    cpn_client = object()

    register_cpn_routes(
        app,
        treasury_repo=treasury_repo,
        cpn_client=cpn_client,
        webhook_secret="cpn_secret",
        environment="sandbox",
    )

    deps = app.dependency_overrides[cpn.get_deps]()
    assert deps.treasury_repo is treasury_repo
    assert deps.cpn_client is cpn_client
    assert deps.webhook_secret == "cpn_secret"
    assert deps.environment == "sandbox"

    paths = {route.path for route in app.routes}
    assert "/api/v2/cpn/payouts" in paths
    assert "/api/v2/webhooks/cpn" in paths


def test_register_funding_capability_routes_wires_dependencies_and_route():
    app = FastAPI()
    settings = object()

    register_funding_capability_routes(app, settings=settings)

    deps = app.dependency_overrides[funding_capabilities.get_deps]()
    assert deps.settings is settings

    paths = {route.path for route in app.routes}
    assert "/api/v2/funding/capabilities" in paths
