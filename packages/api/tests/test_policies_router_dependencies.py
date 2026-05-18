from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, optional_principal, require_principal
from sardis_api.routes.policy import policies


class _Policy:
    policy_id = "pol_123"

    def validate_payment(
        self,
        *,
        amount: Decimal,
        fee: Decimal,
        merchant_id: str | None = None,
        merchant_category: str | None = None,
        mcc_code: str | None = None,
    ) -> tuple[bool, str]:
        if amount > Decimal("100"):
            return False, "per_transaction_limit"
        return True, "OK"


class _PolicyStore:
    async def fetch_policy(self, agent_id: str) -> _Policy | None:
        assert agent_id == "agent_123"
        return _Policy()


class _AgentRepo:
    async def get(self, agent_id: str) -> SimpleNamespace | None:
        if agent_id != "agent_123":
            return None
        return SimpleNamespace(agent_id=agent_id, owner_id="org_demo")


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(policies.router, prefix="/api/v2/policies")
    app.dependency_overrides[require_principal] = (
        lambda: Principal(kind="api_key", organization_id="org_demo", scopes=["*"])
    )
    app.dependency_overrides[optional_principal] = (
        lambda: Principal(kind="api_key", organization_id="org_demo", scopes=["*"])
    )
    return app


def test_policy_check_returns_truthful_503_when_policy_store_is_not_configured() -> None:
    app = _build_app()
    app.state.agent_repo = _AgentRepo()

    with TestClient(app) as client:
        response = client.post(
            "/api/v2/policies/check",
            json={"agent_id": "agent_123", "amount": "25", "currency": "USD", "merchant_id": "aws"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == "policy_store_not_configured"


def test_policy_check_uses_app_state_dependencies_without_dependency_override() -> None:
    app = _build_app()
    app.state.agent_repo = _AgentRepo()
    app.state.policy_store = _PolicyStore()

    with TestClient(app) as client:
        response = client.post(
            "/api/v2/policies/check",
            json={"agent_id": "agent_123", "amount": "25", "currency": "USD", "merchant_id": "aws"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200, response.text
    assert response.json() == {"allowed": True, "reason": "OK", "policy_id": "pol_123"}
