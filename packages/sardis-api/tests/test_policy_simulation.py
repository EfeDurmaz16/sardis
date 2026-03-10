from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers import policy_simulation


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(policy_simulation.router, prefix="/api/v2/policies")

    def _principal() -> Principal:
        return Principal(kind="api_key", organization_id="org_demo", scopes=["*"])

    app.dependency_overrides[require_principal] = _principal
    return TestClient(app)


def test_policy_simulation_requires_definition() -> None:
    client = _build_client()

    response = client.post(
        "/api/v2/policies/simulate",
        json={"amount": "25", "agent_id": "agent_demo"},
    )

    assert response.status_code == 422
    assert "requires a definition" in response.json()["detail"]


def test_policy_simulation_uses_draft_definition() -> None:
    client = _build_client()

    response = client.post(
        "/api/v2/policies/simulate",
        json={
            "amount": "50",
            "agent_id": "agent_demo",
            "definition": {
                "version": "1.0",
                "rules": [
                    {"type": "limit_per_tx", "params": {"amount": "10"}},
                    {"type": "limit_total", "params": {"amount": "1000"}},
                ],
                "metadata": {"source": "test"},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["would_succeed"] is False
    assert body["failure_reasons"] == ["Policy: per_transaction_limit"]
    assert body["policy_result"]["verdict"] == "denied"
    assert any(step["step"] == "per_tx_limit" and step["result"] == "fail" for step in body["policy_result"]["steps"])


def test_policy_simulation_supports_natural_language_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    from sardis_v2_core.spending_policy import SpendingPolicy

    class FakeParser:
        async def parse_and_convert(self, natural_language: str, agent_id: str) -> SpendingPolicy:
            assert natural_language == "allow up to $10 per transaction"
            policy = SpendingPolicy(agent_id=agent_id)
            policy.limit_per_tx = Decimal("10")
            policy.limit_total = Decimal("1000")
            return policy

    monkeypatch.setattr(
        "sardis_v2_core.nl_policy_parser.create_policy_parser",
        lambda use_llm=True: FakeParser(),
    )

    client = _build_client()
    response = client.post(
        "/api/v2/policies/simulate",
        json={
            "amount": "50",
            "agent_id": "agent_demo",
            "definition": {
                "version": "1.0",
                "rules": [
                    {
                        "type": "natural_language",
                        "params": {"text": "allow up to $10 per transaction"},
                    }
                ],
                "metadata": {"source": "test"},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["would_succeed"] is False
    assert body["failure_reasons"] == ["Policy: per_transaction_limit"]
