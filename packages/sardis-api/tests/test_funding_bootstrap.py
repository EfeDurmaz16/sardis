from __future__ import annotations

from fastapi.testclient import TestClient

from sardis_api.main import create_app
from sardis_v2_core.config import SardisSettings


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
    client = TestClient(app)

    response = client.get(
        "/api/v2/stripe/funding/issuing/topups/routing-plan",
        headers={"X-API-Key": "test-api-key-placeholder"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload
    assert payload[0]["provider"] == "bridge"
