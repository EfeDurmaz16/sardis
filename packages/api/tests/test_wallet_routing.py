from fastapi import FastAPI

from sardis_server.routes.wallets import ramp
from sardis_server.routing.wallets import register_ramp_routes


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
