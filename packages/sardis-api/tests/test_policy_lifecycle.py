from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers import policies
from sardis_v2_core import InMemoryPolicyStore
from sardis_v2_core.agit_policy_engine import AgitPolicyEngine
from sardis_v2_core.agents import Agent
from sardis_v2_core.spending_policy import SpendingPolicy, TimeWindowLimit, TrustLevel


class _AgentRepo:
    async def get(self, agent_id: str) -> Agent | None:
        return Agent(agent_id=agent_id, name="Demo Agent", owner_id="org_demo")


class _FakeParser:
    async def parse_and_convert(self, natural_language: str, agent_id: str) -> SpendingPolicy:
        policy = SpendingPolicy(
            agent_id=agent_id,
            trust_level=TrustLevel.MEDIUM,
            limit_per_tx=Decimal("500"),
            limit_total=Decimal("5000"),
            approval_threshold=Decimal("300"),
            blocked_merchant_categories=["gambling", "adult"],
        )
        policy.daily_limit = TimeWindowLimit(window_type="daily", limit_amount=Decimal("2000"))
        policy.weekly_limit = TimeWindowLimit(window_type="weekly", limit_amount=Decimal("4000"))
        policy.monthly_limit = TimeWindowLimit(window_type="monthly", limit_amount=Decimal("10000"))
        return policy


def _build_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = FastAPI()
    app.include_router(policies.router, prefix="/api/v2/policies")

    deps = policies.PolicyDependencies(
        policy_store=InMemoryPolicyStore(),
        agent_repo=_AgentRepo(),
    )
    app.dependency_overrides[policies.get_deps] = lambda: deps
    app.dependency_overrides[require_principal] = (
        lambda: Principal(kind="api_key", organization_id="org_demo", scopes=["*"])
    )

    history_engine = AgitPolicyEngine()
    monkeypatch.setattr("sardis_api.routers.policies._get_policy_history_engine", lambda: history_engine)
    monkeypatch.setattr(
        "sardis_v2_core.nl_policy_parser.create_policy_parser",
        lambda use_llm=True: _FakeParser(),
    )

    return TestClient(app)


def test_policy_lifecycle_records_real_history(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(monkeypatch)

    apply_response = client.post(
        "/api/v2/policies/apply",
        json={
            "agent_id": "agent_demo",
            "natural_language": "Allow up to $500 per transaction and require approval above $300.",
            "confirm": True,
        },
    )

    assert apply_response.status_code == 200

    active_response = client.get("/api/v2/policies/agent_demo")
    assert active_response.status_code == 200
    active_body = active_response.json()
    assert active_body["daily_limit"] == "2000"
    assert active_body["weekly_limit"] == "4000"
    assert active_body["monthly_limit"] == "10000"
    assert active_body["approval_threshold"] == "300"

    history_response = client.get("/api/v2/policies/agent_demo/history")
    assert history_response.status_code == 200
    history_body = history_response.json()
    assert history_body["count"] == 1
    assert len(history_body["commits"]) == 1

    commit_hash = history_body["commits"][0]["commit_hash"]
    detail_response = client.get(f"/api/v2/policies/agent_demo/history/{commit_hash}")
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["policy"]["natural_language"] == (
        "Allow up to $500 per transaction and require approval above $300."
    )
    assert detail_body["policy"]["blocked_merchant_categories"] == ["gambling", "adult"]
