"""HTTP-level tests for the mandates router execute endpoint.

Tests:
  a) POST /mandates/{id}/execute with valid mandate => 200 + tx_hash
  b) POST with nonexistent mandate => 404
  c) POST when policy denies => 403
  d) POST with duplicate execution => 400 (already executed)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis_v2_core.mandates import PaymentMandate, VCProof

# ── Fake DB layer ────────────────────────────────────────────────────

_FAKE_DB: dict[str, Any] = {}


def _make_payment_mandate(mandate_id: str = "mandate_test001") -> PaymentMandate:
    return PaymentMandate(
        mandate_id=mandate_id,
        mandate_type="payment",
        issuer="issuer_1",
        subject="agent_1",
        expires_at=9999999999,
        nonce="nonce_1",
        proof=VCProof(
            verification_method="test#key-1",
            created="2026-01-01T00:00:00Z",
            proof_value="stub",
        ),
        domain="test.example.com",
        purpose="checkout",
        chain="base",
        token="USDC",
        amount_minor=1000,
        destination="0xrecipient",
        audit_hash="abc123",
    )


@dataclass
class FakeOrchestratorResult:
    mandate_id: str = "mandate_test001"
    chain_tx_hash: str = "0xdeadbeef"
    chain: str = "base"
    ledger_tx_id: str = "ltx_001"
    audit_anchor: str = "anchor_001"
    status: str = "submitted"
    execution_time_ms: float = 42.0


@dataclass
class FakeVerification:
    accepted: bool = True
    reason: str = "OK"


@dataclass
class FakePolicyResult:
    allowed: bool = True
    reason: str = "OK"


@dataclass
class FakeComplianceResult:
    allowed: bool = True
    reason: str = "OK"


@dataclass
class FakeAgent:
    agent_id: str = "agent_1"
    owner_id: str = "org_1"


@dataclass
class FakeWallet:
    wallet_id: str = "wal_test001"
    frozen: bool = False
    frozen_reason: str | None = None


def _create_test_app(
    *,
    mandate_exists: bool = True,
    mandate_status: str = "pending",
    policy_allowed: bool = True,
    orchestrator_fail: Exception | None = None,
) -> FastAPI:
    """Create a FastAPI app with the mandates router and mocked deps."""
    from sardis.routes.authority import mandates as mandates_mod

    app = FastAPI()

    # Mock dependencies
    wallet_manager = MagicMock()
    wallet_manager.async_validate_policies = AsyncMock(
        return_value=FakePolicyResult(allowed=policy_allowed)
    )
    wallet_manager.async_record_spend = AsyncMock()

    chain_executor = MagicMock()
    chain_executor.dispatch_payment = AsyncMock()

    verifier = MagicMock()
    verifier.verify = MagicMock(return_value=FakeVerification())

    ledger = MagicMock()
    compliance = MagicMock()
    compliance.preflight = AsyncMock(return_value=FakeComplianceResult())

    wallet_repository = MagicMock()
    wallet_repository.get_by_agent = AsyncMock(return_value=FakeWallet())

    agent_repo = MagicMock()
    agent_repo.get = AsyncMock(return_value=FakeAgent())
    agent_repo.list = AsyncMock(return_value=[FakeAgent()])

    orchestrator = MagicMock()
    if orchestrator_fail:
        orchestrator.execute_chain = AsyncMock(side_effect=orchestrator_fail)
    else:
        orchestrator.execute_chain = AsyncMock(return_value=FakeOrchestratorResult())

    deps = mandates_mod.Dependencies(
        wallet_manager=wallet_manager,
        chain_executor=chain_executor,
        verifier=verifier,
        ledger=ledger,
        compliance=compliance,
        wallet_repository=wallet_repository,
        agent_repo=agent_repo,
        payment_orchestrator=orchestrator,
    )

    # Override dependency
    app.dependency_overrides[mandates_mod.get_deps] = lambda: deps
    app.dependency_overrides[mandates_mod.require_principal] = lambda: MagicMock(
        is_admin=True,
        organization_id="org_1",
    )
    app.dependency_overrides[mandates_mod.require_kill_switch_clear] = lambda: None
    app.dependency_overrides[mandates_mod.enforce_transaction_caps] = lambda: None

    # Build stored mandate in fake DB
    pm = _make_payment_mandate()
    from sardis.routes.authority.mandates import StoredMandate
    stored = StoredMandate(
        mandate_id="mandate_test001",
        mandate=pm,
        status=mandate_status,
    )

    # Mock DB functions
    async def mock_get_mandate(mandate_id: str):
        if mandate_exists and mandate_id == "mandate_test001":
            return stored
        return None

    async def mock_save_mandate(s):
        pass

    # Patch the module-level DB functions and auth
    with_patches = {}
    app.include_router(mandates_mod.router, prefix="/mandates")

    # Store patches for the test to apply
    app._test_patches = {
        "get": mock_get_mandate,
        "save": mock_save_mandate,
    }

    return app


@pytest.fixture
def client_with_mandate():
    """Client with a valid mandate in the fake DB."""
    app = _create_test_app(mandate_exists=True)
    from sardis.routes.authority import mandates as mandates_mod

    # Apply patches and disable auth
    with (
        patch.object(mandates_mod, "_get_mandate", app._test_patches["get"]),
        patch.object(mandates_mod, "_save_mandate", app._test_patches["save"]),
        patch("sardis.routes.authority.mandates.require_principal", lambda: MagicMock(is_admin=True, organization_id="org_1")),
        patch("sardis.routes.authority.mandates.require_kill_switch_clear", lambda: None),
        patch("sardis.routes.authority.mandates.enforce_transaction_caps", lambda: None),
        patch("sardis.routes.authority.mandates.enforce_agent_payment_rate_limit", new_callable=AsyncMock),
        patch.object(mandates_mod, "validate_wallet_not_frozen", return_value=(True, "OK")),
    ):
        yield TestClient(app)


@pytest.fixture
def client_no_mandate():
    """Client with no mandate in the fake DB."""
    app = _create_test_app(mandate_exists=False)
    from sardis.routes.authority import mandates as mandates_mod

    with (
        patch.object(mandates_mod, "_get_mandate", app._test_patches["get"]),
        patch.object(mandates_mod, "_save_mandate", app._test_patches["save"]),
        patch("sardis.routes.authority.mandates.require_principal", lambda: MagicMock(is_admin=True, organization_id="org_1")),
        patch("sardis.routes.authority.mandates.require_kill_switch_clear", lambda: None),
        patch("sardis.routes.authority.mandates.enforce_transaction_caps", lambda: None),
        patch("sardis.routes.authority.mandates.enforce_agent_payment_rate_limit", new_callable=AsyncMock),
    ):
        yield TestClient(app)


@pytest.fixture
def client_policy_deny():
    """Client where orchestrator raises PolicyViolationError."""
    from sardis_v2_core.orchestrator import PolicyViolationError
    app = _create_test_app(orchestrator_fail=PolicyViolationError("per_transaction_limit", mandate_id="mandate_test001"))
    from sardis.routes.authority import mandates as mandates_mod

    with (
        patch.object(mandates_mod, "_get_mandate", app._test_patches["get"]),
        patch.object(mandates_mod, "_save_mandate", app._test_patches["save"]),
        patch("sardis.routes.authority.mandates.require_principal", lambda: MagicMock(is_admin=True, organization_id="org_1")),
        patch("sardis.routes.authority.mandates.require_kill_switch_clear", lambda: None),
        patch("sardis.routes.authority.mandates.enforce_transaction_caps", lambda: None),
        patch("sardis.routes.authority.mandates.enforce_agent_payment_rate_limit", new_callable=AsyncMock),
        patch.object(mandates_mod, "validate_wallet_not_frozen", return_value=(True, "OK")),
    ):
        yield TestClient(app)


@pytest.fixture
def client_already_executed():
    """Client with an already-executed mandate."""
    app = _create_test_app(mandate_exists=True, mandate_status="executed")
    from sardis.routes.authority import mandates as mandates_mod

    with (
        patch.object(mandates_mod, "_get_mandate", app._test_patches["get"]),
        patch.object(mandates_mod, "_save_mandate", app._test_patches["save"]),
        patch("sardis.routes.authority.mandates.require_principal", lambda: MagicMock(is_admin=True, organization_id="org_1")),
        patch("sardis.routes.authority.mandates.require_kill_switch_clear", lambda: None),
        patch("sardis.routes.authority.mandates.enforce_transaction_caps", lambda: None),
        patch("sardis.routes.authority.mandates.enforce_agent_payment_rate_limit", new_callable=AsyncMock),
    ):
        yield TestClient(app)


def test_execute_valid_mandate_returns_200(client_with_mandate):
    resp = client_with_mandate.post("/mandates/mandate_test001/execute")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tx_hash"] == "0xdeadbeef"


def test_execute_nonexistent_mandate_returns_404(client_no_mandate):
    resp = client_no_mandate.post("/mandates/mandate_nonexistent/execute")
    assert resp.status_code == 404


def test_execute_when_policy_denies_returns_403(client_policy_deny):
    resp = client_policy_deny.post("/mandates/mandate_test001/execute")
    assert resp.status_code == 403


def test_execute_already_executed_returns_400(client_already_executed):
    resp = client_already_executed.post("/mandates/mandate_test001/execute")
    assert resp.status_code == 400
    assert "already executed" in resp.json()["detail"].lower()
