from __future__ import annotations

from fastapi.testclient import TestClient
from sardis_v2_core.config import SardisSettings

from sardis_server.authz import Principal, require_principal
from sardis_server.main import create_app


def test_funding_router_bootstraps_with_bridge_only() -> None:
    settings = SardisSettings(
        environment="dev",
        chain_mode="simulated",
        secret_key="test_secret_key_for_testing_purposes_only_32chars",
        database_url="memory://",
        ledger_dsn="memory://",
        mandate_archive_dsn="memory://",
        replay_cache_dsn="memory://",
        funding={
            "primary_adapter": "bridge",
            "fallback_adapter": None,
        },
        bridge_cards={
            "api_key": "bridge_test_key",
            "cards_base_url": "https://api.bridge.xyz",
        },
    )

    app = create_app(settings=settings)
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["*"],
        api_key=None,
    )
    client = TestClient(app)

    response = client.get("/api/v2/stripe/funding/issuing/topups/routing-plan")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload
    assert payload[0]["provider"] == "bridge"
