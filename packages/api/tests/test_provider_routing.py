from types import SimpleNamespace

from fastapi import FastAPI

from sardis_server.routes.providers import (
    partner_card_webhooks,
    stripe_connect,
    stripe_funding,
    stripe_webhooks,
)
from sardis_server.routing.providers import (
    register_mastercard_webhook_routes,
    register_partner_card_webhook_routes,
    register_provider_integration_routes,
    register_stripe_connect_routes,
    register_stripe_funding_routes,
    register_stripe_webhook_routes,
)


def test_register_provider_integration_routes_mounts_enabled_provider_routes():
    app = FastAPI()
    settings = SimpleNamespace(
        striga=SimpleNamespace(enabled=True),
        lightspark=SimpleNamespace(enabled=True),
    )

    register_provider_integration_routes(app, settings=settings)

    paths = {route.path for route in app.routes}
    assert "/api/v2/striga/vibans" in paths
    assert "/api/v2/grid/uma/create" in paths
    assert "/api/v2/fiat-rails/payout" in paths
    assert "/api/v2/currency/convert" in paths


def test_register_provider_integration_routes_skips_disabled_provider_routes():
    app = FastAPI()
    settings = SimpleNamespace(
        striga=SimpleNamespace(enabled=False),
        lightspark=SimpleNamespace(enabled=False),
    )

    register_provider_integration_routes(app, settings=settings)

    paths = {route.path for route in app.routes}
    assert "/api/v2/striga/vibans" not in paths
    assert "/api/v2/grid/uma/create" not in paths
    assert "/api/v2/fiat-rails/payout" not in paths
    assert "/api/v2/currency/convert" not in paths


def test_register_mastercard_webhook_routes_mounts_public_route():
    app = FastAPI()

    register_mastercard_webhook_routes(app)

    paths = {route.path for route in app.routes}
    assert "/mastercard/webhooks" in paths


def test_register_partner_card_webhook_routes_wires_dependencies_and_routes():
    app = FastAPI()
    card_repo = object()
    wallet_repo = object()
    agent_repo = object()
    canonical_repo = object()
    treasury_repo = object()

    register_partner_card_webhook_routes(
        app,
        card_repo=card_repo,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        canonical_repo=canonical_repo,
        treasury_repo=treasury_repo,
        rain_webhook_secret="rain_secret",
        bridge_webhook_secret="bridge_secret",
        environment="prod",
    )

    deps = app.dependency_overrides[partner_card_webhooks.get_deps]()
    assert deps.card_repo is card_repo
    assert deps.wallet_repo is wallet_repo
    assert deps.agent_repo is agent_repo
    assert deps.canonical_repo is canonical_repo
    assert deps.treasury_repo is treasury_repo
    assert deps.rain_webhook_secret == "rain_secret"
    assert deps.bridge_webhook_secret == "bridge_secret"
    assert deps.environment == "prod"

    paths = {route.path for route in app.routes}
    assert "/api/v2/webhooks/cards/rain" in paths
    assert "/api/v2/webhooks/cards/bridge" in paths


def test_register_stripe_funding_routes_wires_dependencies_and_routes():
    app = FastAPI()
    treasury_provider = object()
    funding_adapter = object()
    fallback_funding_adapter = object()
    treasury_repo = object()
    canonical_repo = object()

    register_stripe_funding_routes(
        app,
        treasury_provider=treasury_provider,
        funding_adapter=funding_adapter,
        fallback_funding_adapter=fallback_funding_adapter,
        treasury_repo=treasury_repo,
        canonical_repo=canonical_repo,
        default_connected_account_id="acct_default",
        connected_account_map={"org_demo": "acct_org"},
        funding_strategy="stablecoin_first",
        stablecoin_prefund_enabled=True,
        require_connected_account=True,
    )

    deps = app.dependency_overrides[stripe_funding.get_deps]()
    assert deps.treasury_provider is treasury_provider
    assert deps.funding_adapter is funding_adapter
    assert deps.fallback_funding_adapter is fallback_funding_adapter
    assert deps.treasury_repo is treasury_repo
    assert deps.canonical_repo is canonical_repo
    assert deps.default_connected_account_id == "acct_default"
    assert deps.connected_account_map == {"org_demo": "acct_org"}
    assert deps.funding_strategy == "stablecoin_first"
    assert deps.stablecoin_prefund_enabled is True
    assert deps.require_connected_account is True

    paths = {route.path for route in app.routes}
    assert "/api/v2/stripe/funding/issuing/topups" in paths
    assert "/api/v2/stripe/funding/issuing/topups/strategy" in paths


def test_register_stripe_connect_routes_wires_dependencies_and_routes():
    app = FastAPI()
    merchant_repo = object()
    stripe_connect_provider = object()

    register_stripe_connect_routes(
        app,
        merchant_repo=merchant_repo,
        stripe_connect_provider=stripe_connect_provider,
    )

    deps = app.dependency_overrides[stripe_connect.get_deps]()
    assert deps.merchant_repo is merchant_repo
    assert deps.stripe_connect_provider is stripe_connect_provider

    paths = {route.path for route in app.routes}
    assert "/api/v2/merchants/{merchant_id}/connect" in paths
    assert "/api/v2/merchants/{merchant_id}/connect/status" in paths
    assert "/api/v2/webhooks/stripe-connect/webhooks" in paths


def test_register_stripe_webhook_routes_wires_dependencies_and_route():
    app = FastAPI()
    treasury_provider = object()
    issuing_provider = object()

    register_stripe_webhook_routes(
        app,
        treasury_provider=treasury_provider,
        issuing_provider=issuing_provider,
    )

    deps = app.dependency_overrides[stripe_webhooks.get_deps]()
    assert deps.treasury_provider is treasury_provider
    assert deps.issuing_provider is issuing_provider

    paths = {route.path for route in app.routes}
    assert "/stripe/webhooks" in paths
