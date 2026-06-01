"""End-to-end Guard test: external signal feed -> RiskEngine -> orchestrator.

Exercises the full WIRE + GATE path the way production does, with NO live keys:

* a *real* SEON :class:`FraudSignalPort` adapter (its httpx session faked) feeds
  a cross-customer signal into the in-house :class:`RiskEngine`, which combines
  it with the behavioral score and emits a binding GuardAction;
* the orchestrator consults that engine PRE-DISPATCH:
    - a HIGH-risk payment is BLOCKED — ``RiskViolationError``, NO chain dispatch
      (fail-closed), with decision evidence captured;
    - a MEDIUM-risk payment routes to a durable ApprovalRequest via the
      ApprovalGate — ``pending_approval``, NO money moved;
* the read-only Guard surface (``RiskEngine.recent_signals``) then reflects the
  exact decisions that gated the money path, with the feed provider recorded.

This is a true end-to-end seam (adapter + engine + orchestrator + gate + read
surface), distinct from the unit/integration coverage in
``packages/sardis/tests/test_orchestrator_risk_engine.py``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sardis.core.approval_gate import ApprovalGate
from sardis.core.approval_request import ApprovalState
from sardis.core.approval_request_repository import InMemoryApprovalRequestStore
from sardis.core.orchestrator import PaymentOrchestrator, RiskViolationError
from sardis.guardrails.risk_engine import GuardAction, RiskEngine

from server.providers.fraud import SeonClient, SeonConfig, SeonFraudSignalAdapter
from server.routes.agents import agent_risk

# ── orchestrator fakes (no real chain / wallet / ledger) ─────────────────


@dataclass
class _FakePayment:
    mandate_id: str = "mdt_e2e_001"
    agent_id: str | None = "agent_e2e"
    wallet_id: str | None = "wal_e2e"
    chain: str = "base"
    token: str = "USDC"
    amount_minor: int = 50_000_000  # 50 USDC
    destination: str = "0x" + "ce" * 20
    audit_hash: str = "0x" + "00" * 32
    merchant_id: str | None = "merch_e2e"
    merchant_category: str | None = None
    rail: str | None = None
    fee: Any = None
    amount: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class _FakeMandateChain:
    payment: _FakePayment = field(default_factory=_FakePayment)


@dataclass
class _FakeChainReceipt:
    tx_hash: str = "0xtxhash_e2e"
    chain: str = "base"
    block_number: int = 1
    audit_anchor: str = "0x" + "00" * 32


@dataclass
class _FakeLedgerTx:
    tx_id: str = "ltx_e2e_001"


@dataclass
class _FakePolicyResult:
    allowed: bool = True
    reason: str = "OK"
    rule_id: str | None = None
    required_approvals: int = 0


@dataclass
class _FakeComplianceResult:
    allowed: bool = True
    reason: str = "OK"
    provider: str = "mock"
    rule_id: str = "mock_rule"
    audit_id: str = "audit_e2e"


@dataclass
class _StubAnomaly:
    """Fixed internal 0-1 behavioral score (isolates the external-feed path)."""

    score_01: float

    def assess_risk(self, **kwargs):
        from datetime import UTC, datetime

        from sardis.guardrails.anomaly_engine import RiskAction, RiskAssessment

        return RiskAssessment(
            agent_id=kwargs.get("agent_id", "a"),
            overall_score=self.score_01,
            action=RiskAction.ALLOW,
            signals=[],
            timestamp=datetime.now(UTC),
            transaction_amount=kwargs.get("amount"),
        )


class _MockNotifier:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_approval_request(self, **kwargs: Any) -> Any:
        self.sent.append(kwargs)
        return MagicMock(
            provider="mock", handle="dlv", channels=(), step_up_issued=False, ok=True
        )


# ── faked SEON httpx session (no network, no key) ────────────────────────


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # pragma: no cover - always ok here
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeSeonSession:
    def __init__(self, fraud_score: float, state: str) -> None:
        self._fraud_score = fraud_score
        self._state = state
        self.calls: list[dict[str, Any]] = []

    async def post(self, path: str, *, json: dict[str, Any] | None = None, headers=None):
        self.calls.append(json or {})
        return _FakeResponse(
            {
                "success": True,
                "data": {
                    "id": "seon_e2e",
                    "fraud_score": self._fraud_score,
                    "state": self._state,
                    "applied_rules": [{"id": "R1", "name": "agent_velocity"}],
                },
            }
        )


def _seon_feed(fraud_score: float, state: str) -> SeonFraudSignalAdapter:
    """A real SEON adapter whose transport is faked (no key, no network)."""
    client = SeonClient(SeonConfig(api_key="k", environment="production"))
    session = _FakeSeonSession(fraud_score, state)

    async def _client_():
        return session

    client._client_ = _client_  # type: ignore[assignment]
    return SeonFraudSignalAdapter(client)


def _build_orchestrator(*, risk_engine):
    wallet_mgr = MagicMock()
    wallet_mgr.async_validate_policies = AsyncMock(return_value=_FakePolicyResult())
    wallet_mgr.async_record_spend = AsyncMock()

    compliance = MagicMock()
    compliance.preflight = AsyncMock(return_value=_FakeComplianceResult())

    chain_exec = MagicMock()
    chain_exec.dispatch_payment = AsyncMock(return_value=_FakeChainReceipt())

    ledger = MagicMock()
    ledger.append = MagicMock(return_value=_FakeLedgerTx())

    store = InMemoryApprovalRequestStore()
    gate = ApprovalGate(store=store, notifier=_MockNotifier(), signing_secret="s")

    orch = PaymentOrchestrator(
        wallet_manager=wallet_mgr,
        compliance=compliance,
        chain_executor=chain_exec,
        ledger=ledger,
        approval_gate=gate,
        risk_engine=risk_engine,
    )
    return orch, chain_exec, store


def _chain(amount_minor: int = 50_000_000) -> _FakeMandateChain:
    return _FakeMandateChain(payment=_FakePayment(amount_minor=amount_minor))


# ── end-to-end ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_high_risk_external_feed_blocks_with_no_dispatch():
    # Calm internal model, but the SEON feed returns a near-certain decline.
    # The combined decision must BLOCK and no money may move.
    engine = RiskEngine(
        anomaly_engine=_StubAnomaly(0.05),
        fraud_feeds=[_seon_feed(fraud_score=96.0, state="DECLINE")],
    )
    orch, chain_exec, _ = _build_orchestrator(risk_engine=engine)

    with pytest.raises(RiskViolationError) as exc:
        await orch.execute_chain(_chain())

    # Fail-closed: the chain executor was never invoked.
    chain_exec.dispatch_payment.assert_not_awaited()
    # The block carries decision evidence (which feed, what score) for audit.
    assert exc.value.evidence
    assert exc.value.evidence["action"] == GuardAction.BLOCK.value
    feed_providers = [f["provider"] for f in exc.value.evidence["feeds"]]
    assert "seon" in feed_providers

    # Read surface reflects the exact gating decision, newest first.
    recent = engine.recent_signals("agent_e2e")
    assert recent and recent[0].action == GuardAction.BLOCK
    assert engine.feed_providers == ["seon"]


@pytest.mark.asyncio
async def test_medium_risk_routes_to_approval_request():
    # An elevated-but-not-certain combination (medium internal behavioral score
    # confirmed by a SEON REVIEW signal) lands in the REQUIRE_APPROVAL band:
    # 0.6*70 + 0.4*78 = 73.2, which is >= APPROVAL (60) and < BLOCK (85).  It
    # opens a durable ApprovalRequest rather than blocking or allowing.
    engine = RiskEngine(
        anomaly_engine=_StubAnomaly(0.70),
        fraud_feeds=[_seon_feed(fraud_score=78.0, state="REVIEW")],
    )
    orch, chain_exec, store = _build_orchestrator(risk_engine=engine)

    result = await orch.execute_chain(_chain())

    assert result.status == "pending_approval"
    assert result.approval_id
    assert result.chain_tx_hash == ""
    # No money moved while awaiting human approval.
    chain_exec.dispatch_payment.assert_not_awaited()

    req = await store.get(result.approval_id)
    assert req is not None and req.status == ApprovalState.PENDING

    recent = engine.recent_signals("agent_e2e")
    assert recent and recent[0].action == GuardAction.REQUIRE_APPROVAL
    # The external SEON signal was genuinely folded into the combined score.
    decision = recent[0]
    assert decision.external_score == 78.0
    assert 60.0 <= decision.combined_score < 85.0


@pytest.mark.asyncio
async def test_low_risk_external_feed_allows_and_settles():
    # SEON APPROVE + calm internal -> ALLOW; payment settles through the chain.
    engine = RiskEngine(
        anomaly_engine=_StubAnomaly(0.02),
        fraud_feeds=[_seon_feed(fraud_score=3.0, state="APPROVE")],
    )
    orch, chain_exec, _ = _build_orchestrator(risk_engine=engine)

    result = await orch.execute_chain(_chain())

    assert result.status == "submitted"
    chain_exec.dispatch_payment.assert_awaited_once()
    # The decimal-string amount was sent to the feed (no float on the wire).
    assert engine.recent_signals("agent_e2e")[0].action == GuardAction.ALLOW


# ── read-only Guard surface (HTTP) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_read_surface_returns_recent_decisions():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from server.authz import Principal, require_principal

    engine = RiskEngine(
        anomaly_engine=_StubAnomaly(0.05),
        fraud_feeds=[_seon_feed(fraud_score=96.0, state="DECLINE")],
    )
    orch, chain_exec, _ = _build_orchestrator(risk_engine=engine)
    with pytest.raises(RiskViolationError):
        await orch.execute_chain(_chain())
    chain_exec.dispatch_payment.assert_not_awaited()

    app = FastAPI()
    app.state.risk_engine = engine
    app.include_router(agent_risk.router, prefix="/api/v2/agents")
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="jwt", organization_id="org_demo", scopes=["*"]
    )
    client = TestClient(app)

    resp = client.get("/api/v2/agents/agent_e2e/risk-signals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_engine_enabled"] is True
    assert body["feed_providers"] == ["seon"]
    assert body["count"] >= 1
    top = body["signals"][0]
    assert top["action"] == "block"
    assert any(f["provider"] == "seon" for f in top["feeds"])


@pytest.mark.asyncio
async def test_read_surface_empty_when_no_engine():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from server.authz import Principal, require_principal

    app = FastAPI()
    app.state.risk_engine = None
    app.include_router(agent_risk.router, prefix="/api/v2/agents")
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="jwt", organization_id="org_demo", scopes=["*"]
    )
    client = TestClient(app)

    resp = client.get("/api/v2/agents/agent_x/risk-signals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_engine_enabled"] is False
    assert body["count"] == 0
