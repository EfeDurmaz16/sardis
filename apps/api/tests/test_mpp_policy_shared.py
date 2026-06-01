"""Tests for the shared MPP policy engine and demo-endpoint unification.

The MPP demo (/api/v2/demo/paid-data) previously ran a hardcoded parallel policy
($100/tx, $1000/day module-global counter) that could disagree with the real
SpendingPolicy that /api/v2/mpp/evaluate uses. These tests verify the demo now
routes through the SAME engine (services/mpp_policy.evaluate_mpp_policy) and is
fail-closed.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sardis.core.spending_policy import SpendingPolicy

from server.services.mpp_policy import POLICY_CHECK_COUNT, evaluate_mpp_policy


class _FakePolicyStore:
    def __init__(self, policy=None, raises=False):
        self._policy = policy
        self._raises = raises

    async def fetch_policy(self, agent_id):
        if self._raises:
            raise RuntimeError("db down")
        return self._policy


def _policy(limit_per_tx="100", limit_total="1000"):
    return SpendingPolicy(
        agent_id="agent_1",
        limit_per_tx=Decimal(limit_per_tx),
        limit_total=Decimal(limit_total),
        allowed_chains=[],
        allowed_tokens=[],
    )


@pytest.mark.asyncio
class TestSharedEvaluator:
    async def test_allow_within_limits(self):
        d = await evaluate_mpp_policy(
            policy_store=_FakePolicyStore(policy=_policy()),
            agent_id="agent_1", amount=Decimal("50"), merchant="openai.com",
            currency="USDC", network="tempo",
        )
        assert d.allowed is True
        assert d.reason == "OK"
        assert d.checks_passed == d.checks_total == POLICY_CHECK_COUNT

    async def test_deny_over_per_tx_limit(self):
        d = await evaluate_mpp_policy(
            policy_store=_FakePolicyStore(policy=_policy(limit_per_tx="100")),
            agent_id="agent_1", amount=Decimal("500"), merchant="x",
            currency="USDC", network="tempo",
        )
        assert d.allowed is False
        assert d.reason == "per_transaction_limit"
        assert d.checks_passed < d.checks_total

    # --- fail-closed paths ---------------------------------------------------

    async def test_no_agent_id_denies(self):
        d = await evaluate_mpp_policy(
            policy_store=_FakePolicyStore(policy=_policy()),
            agent_id=None, amount=Decimal("1"), merchant="x",
            currency="USDC", network="tempo",
        )
        assert d.allowed is False
        assert d.reason == "agent_id_required_for_policy_evaluation"

    async def test_no_store_denies(self):
        d = await evaluate_mpp_policy(
            policy_store=None,
            agent_id="agent_1", amount=Decimal("1"), merchant="x",
            currency="USDC", network="tempo",
        )
        assert d.allowed is False
        assert d.reason == "policy_store_not_configured"

    async def test_store_error_denies(self):
        d = await evaluate_mpp_policy(
            policy_store=_FakePolicyStore(raises=True),
            agent_id="agent_1", amount=Decimal("1"), merchant="x",
            currency="USDC", network="tempo",
        )
        assert d.allowed is False
        assert d.reason == "policy_lookup_error"

    async def test_no_policy_denies(self):
        d = await evaluate_mpp_policy(
            policy_store=_FakePolicyStore(policy=None),
            agent_id="agent_1", amount=Decimal("1"), merchant="x",
            currency="USDC", network="tempo",
        )
        assert d.allowed is False
        assert d.reason == "no_policy_for_agent"


# ---------------------------------------------------------------------------
# Demo endpoint now uses the real engine (no hardcoded $100/$1000, no global
# counter). Verify demo result == shared-engine result for identical input,
# and demo fails closed when no policy_store is wired.
# ---------------------------------------------------------------------------


def _make_demo_app(policy_store):
    from fastapi import FastAPI

    from server.middleware.mpp_gate import _Mpp402, _mpp_402_handler
    from server.routes.protocol.mpp_demo import router

    app = FastAPI()
    app.add_exception_handler(_Mpp402, _mpp_402_handler)
    app.include_router(router, prefix="/api/v2/demo")
    app.state.policy_store = policy_store
    return app


class TestDemoUsesRealEngine:
    def test_demo_denies_over_per_tx_limit(self, monkeypatch):
        """Demo with a real $100/tx policy denies a $500 eval — the OLD hardcoded
        engine would have used its own $100 constant; now it's the real policy."""
        # Authenticated => gate passes through free, endpoint runs policy.
        app = _make_demo_app(_FakePolicyStore(policy=_policy(limit_per_tx="100")))
        from fastapi.testclient import TestClient

        with TestClient(app) as c:
            r = c.get(
                "/api/v2/demo/paid-data",
                params={"agent_id": "agent_1", "amount": 500, "merchant": "x", "currency": "USDC"},
                headers={"Authorization": "Bearer test"},
            )
        assert r.status_code == 200
        pc = r.json()["policy_check"]
        assert pc["result"] == "DENIED"
        assert pc["reason"] == "per_transaction_limit"

    def test_demo_allows_within_limit(self):
        app = _make_demo_app(_FakePolicyStore(policy=_policy(limit_per_tx="100")))
        from fastapi.testclient import TestClient

        with TestClient(app) as c:
            r = c.get(
                "/api/v2/demo/paid-data",
                params={"agent_id": "agent_1", "amount": 50, "merchant": "openai.com"},
                headers={"Authorization": "Bearer test"},
            )
        assert r.status_code == 200
        assert r.json()["policy_check"]["result"] == "ALLOWED"

    def test_demo_fails_closed_without_store(self):
        """No policy_store wired => DENIED, not a fake ALLOW."""
        app = _make_demo_app(None)
        from fastapi.testclient import TestClient

        with TestClient(app) as c:
            r = c.get(
                "/api/v2/demo/paid-data",
                params={"agent_id": "agent_1", "amount": 10},
                headers={"Authorization": "Bearer test"},
            )
        assert r.status_code == 200
        pc = r.json()["policy_check"]
        assert pc["result"] == "DENIED"
        assert pc["reason"] == "policy_store_not_configured"

    def test_demo_no_agent_id_skips_policy(self):
        """No agent_id => no policy_check block (network data only)."""
        app = _make_demo_app(_FakePolicyStore(policy=_policy()))
        from fastapi.testclient import TestClient

        with TestClient(app) as c:
            r = c.get("/api/v2/demo/paid-data", headers={"Authorization": "Bearer test"})
        assert r.status_code == 200
        assert "policy_check" not in r.json()
