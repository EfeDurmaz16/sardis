"""Tests for MPP (Machine Payments Protocol) API endpoints."""
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis.core.mpp import MPPPayment, MPPPaymentStatus, MPPSession, MPPSessionStatus
from sardis.core.spending_policy import SpendingPolicy

from server.authz import Principal, require_principal


class TestMPPSessionModel:
    """Verify MPP session model behavior."""

    def test_session_defaults(self):
        session = MPPSession()
        assert session.status == MPPSessionStatus.ACTIVE
        assert session.method == "tempo"
        assert session.chain == "tempo"
        assert session.currency == "USDC"
        assert session.payment_count == 0

    def test_session_id_prefix(self):
        session = MPPSession()
        assert session.session_id.startswith("mpp_sess_")

    def test_can_spend_within_limit(self):
        session = MPPSession(spending_limit=Decimal("100"), remaining=Decimal("100"))
        assert session.can_spend(Decimal("50")) is True

    def test_cannot_spend_over_limit(self):
        session = MPPSession(spending_limit=Decimal("100"), remaining=Decimal("30"))
        assert session.can_spend(Decimal("50")) is False

    def test_cannot_spend_when_closed(self):
        session = MPPSession(
            spending_limit=Decimal("100"),
            remaining=Decimal("100"),
            status=MPPSessionStatus.CLOSED,
        )
        assert session.can_spend(Decimal("10")) is False

    def test_record_payment_updates_remaining(self):
        session = MPPSession(spending_limit=Decimal("100"), remaining=Decimal("100"))
        session.record_payment(Decimal("40"))
        assert session.remaining == Decimal("60")
        assert session.total_spent == Decimal("40")
        assert session.payment_count == 1

    def test_record_payment_exhausts_session(self):
        session = MPPSession(spending_limit=Decimal("100"), remaining=Decimal("100"))
        session.record_payment(Decimal("100"))
        assert session.status == MPPSessionStatus.EXHAUSTED

    def test_close_session(self):
        session = MPPSession()
        session.close()
        assert session.status == MPPSessionStatus.CLOSED
        assert session.closed_at is not None


class TestMPPPaymentModel:
    """Verify MPP payment model."""

    def test_payment_defaults(self):
        payment = MPPPayment()
        assert payment.status == MPPPaymentStatus.PENDING
        assert payment.chain == "tempo"
        assert payment.tx_hash is None

    def test_payment_id_prefix(self):
        payment = MPPPayment()
        assert payment.payment_id.startswith("mpp_pay_")


class TestMPPRouterImport:
    """Verify MPP router can be imported."""

    def test_router_import(self):
        from server.routes.protocol.mpp import router
        assert router is not None

    def test_router_has_endpoints(self):
        from server.routes.protocol.mpp import router
        paths = [r.path for r in router.routes]
        assert "/sessions" in paths
        assert "/sessions/{session_id}" in paths
        assert "/sessions/{session_id}/execute" in paths
        assert "/sessions/{session_id}/close" in paths
        assert "/evaluate" in paths
        assert "/simulate" in paths


# ---------------------------------------------------------------------------
# /evaluate — real SpendingPolicy engine, fail-closed (no more default-allow)
# ---------------------------------------------------------------------------


class _FakePolicyStore:
    def __init__(self, policy=None, raises=False):
        self._policy = policy
        self._raises = raises

    async def fetch_policy(self, agent_id):
        if self._raises:
            raise RuntimeError("db down")
        return self._policy


def _make_eval_app(*, policy=None, raises=False, owner_id="org_test_001", scopes=None):
    app = FastAPI()
    fake_principal = Principal(
        kind="api_key",
        organization_id="org_test_001",
        scopes=scopes if scopes is not None else ["*"],
    )
    app.dependency_overrides[require_principal] = lambda: fake_principal

    from server.routes.protocol.mpp import router

    app.include_router(router, prefix="/api/v2/mpp")
    app.state.policy_store = _FakePolicyStore(policy=policy, raises=raises)

    class _AgentRepo:
        async def get(self, agent_id):
            return SimpleNamespace(id=agent_id, owner_id=owner_id)

    app.state.agent_repo = _AgentRepo()
    return app


def _policy(limit_per_tx="100", limit_total="1000", allowed_chains=None, allowed_tokens=None):
    return SpendingPolicy(
        agent_id="agent_1",
        limit_per_tx=Decimal(limit_per_tx),
        limit_total=Decimal(limit_total),
        allowed_chains=allowed_chains or [],
        allowed_tokens=allowed_tokens or [],
    )


class TestMPPEvaluateRealPolicy:
    def test_allow_within_limits(self):
        app = _make_eval_app(policy=_policy(limit_per_tx="100"))
        with TestClient(app) as c:
            r = c.post("/api/v2/mpp/evaluate", json={
                "agent_id": "agent_1", "amount": 50, "merchant": "openai.com",
                "currency": "USDC", "network": "tempo",
            })
        assert r.status_code == 200
        body = r.json()
        assert body["allowed"] is True
        assert body["reason"] == "OK"
        assert body["checks_passed"] == body["checks_total"]

    def test_deny_over_per_tx_limit(self):
        """The hardcoded $10k default-allow is gone — real per-tx limit applies."""
        app = _make_eval_app(policy=_policy(limit_per_tx="100"))
        with TestClient(app) as c:
            r = c.post("/api/v2/mpp/evaluate", json={
                "agent_id": "agent_1", "amount": 500, "merchant": "openai.com",
            })
        assert r.status_code == 200
        body = r.json()
        assert body["allowed"] is False
        assert body["reason"] == "per_transaction_limit"
        assert body["checks_passed"] < body["checks_total"]

    def test_deny_over_total_limit(self):
        app = _make_eval_app(policy=_policy(limit_per_tx="2000", limit_total="1000"))
        with TestClient(app) as c:
            r = c.post("/api/v2/mpp/evaluate", json={
                "agent_id": "agent_1", "amount": 1500, "merchant": "x",
            })
        assert r.status_code == 200
        assert r.json()["allowed"] is False
        assert r.json()["reason"] == "total_limit_exceeded"

    def test_deny_chain_not_allowlisted(self):
        app = _make_eval_app(policy=_policy(allowed_chains=["base"]))
        with TestClient(app) as c:
            r = c.post("/api/v2/mpp/evaluate", json={
                "agent_id": "agent_1", "amount": 10, "merchant": "x", "network": "tempo",
            })
        assert r.status_code == 200
        assert r.json()["allowed"] is False
        assert r.json()["reason"] == "chain_not_allowlisted"

    def test_deny_no_agent_id_fail_closed(self):
        """No agent_id => DENY (was: default-allow)."""
        app = _make_eval_app(policy=_policy())
        with TestClient(app) as c:
            r = c.post("/api/v2/mpp/evaluate", json={
                "amount": 10, "merchant": "x",
            })
        assert r.status_code == 200
        assert r.json()["allowed"] is False
        assert r.json()["reason"] == "agent_id_required_for_policy_evaluation"

    def test_deny_no_policy_fail_closed(self):
        app = _make_eval_app(policy=None)
        with TestClient(app) as c:
            r = c.post("/api/v2/mpp/evaluate", json={
                "agent_id": "agent_1", "amount": 10, "merchant": "x",
            })
        assert r.status_code == 200
        assert r.json()["allowed"] is False
        assert r.json()["reason"] == "no_policy_for_agent"

    def test_deny_store_error_fail_closed(self):
        app = _make_eval_app(raises=True)
        with TestClient(app) as c:
            r = c.post("/api/v2/mpp/evaluate", json={
                "agent_id": "agent_1", "amount": 10, "merchant": "x",
            })
        assert r.status_code == 200
        assert r.json()["allowed"] is False
        assert r.json()["reason"] == "policy_lookup_error"

    def test_cross_org_agent_denied(self):
        app = _make_eval_app(policy=_policy(), owner_id="org_other", scopes=["payments:write"])
        with TestClient(app) as c:
            r = c.post("/api/v2/mpp/evaluate", json={
                "agent_id": "agent_1", "amount": 10, "merchant": "x",
            })
        assert r.status_code == 403

    def test_simulate_uses_same_engine(self):
        app = _make_eval_app(policy=_policy(limit_per_tx="100"))
        with TestClient(app) as c:
            r = c.post("/api/v2/mpp/simulate", json={
                "agent_id": "agent_1", "amount": 500, "merchant": "x",
            })
        assert r.status_code == 200
        assert r.json()["allowed"] is False
        assert r.json()["reason"] == "per_transaction_limit"
