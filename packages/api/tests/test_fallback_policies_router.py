from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_server.authz import Principal, require_principal
from sardis_server.routes.policy import fallback_policies
from sardis_server.routes.policy.fallback_policies import router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id="org_test_001",
        scopes=["*"],
    )
    app.include_router(router)
    return app


def test_list_fallback_rules_starts_empty_without_seeded_defaults() -> None:
    fallback_policies._fallback_rules.clear()
    fallback_policies._degraded_modes.clear()
    fallback_policies._operator_config_loaded = True

    with TestClient(_make_app()) as client:
        response = client.get("/rules")

    assert response.status_code == 200, response.text
    assert response.json() == []


def test_set_degraded_mode_accepts_allowed_rail_without_seeded_cache() -> None:
    fallback_policies._fallback_rules.clear()
    fallback_policies._degraded_modes.clear()
    fallback_policies._operator_config_loaded = True

    body = {
        "rail": "stablecoin",
        "mode": "degraded",
        "reason": "provider_latency",
        "max_amount_override": 250.0,
        "require_approval": True,
        "updated_at": "",
    }

    with TestClient(_make_app()) as client:
        response = client.put("/degraded-modes/stablecoin", json=body)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["rail"] == "stablecoin"
    assert payload["mode"] == "degraded"
    assert payload["reason"] == "provider_latency"
    assert payload["require_approval"] is True
