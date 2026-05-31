"""End-to-end test of the ApprovalRequest API — the closed human-in-the-loop loop.

Exercises the routes the sardis-cloud Approvals page uses, against the REAL
engine (ApprovalGate + InMemory store) and a REAL PaymentOrchestrator wired with
a mock chain executor / notifier (so no live keys, no network):

* list pending -> the durable signed request appears;
* POST decision approve -> the orchestrator RE-EXECUTES exactly once and a
  receipt comes back through the API;
* revoke the mandate BETWEEN approval and re-execution -> still blocked
  fail-closed (no money moves), surfaced as ``blocked_reason``;
* deny -> recorded, no execution.

The approver is the authenticated principal, not a body field — a forged
decision cannot move money.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis.core.approval_gate import ApprovalGate
from sardis.core.approval_request_repository import InMemoryApprovalRequestStore
from sardis.core.orchestrator import PaymentOrchestrator

from server.authz import Principal, require_principal
from server.routes.authority import approval_requests as ar

# ── Engine scaffold (mirrors the orchestrator loop test) ───────────────


@dataclass
class _FakePayment:
    mandate_id: str = "mdt_api_001"
    agent_id: str | None = "agent_api"
    wallet_id: str | None = "wal_api"
    chain: str = "base"
    token: str = "USDC"
    amount_minor: int = 250_000_000  # 250 USDC
    destination: str = "0x" + "cd" * 20
    merchant_id: str | None = "merch_x"
    merchant_category: str | None = None
    rail: str | None = None
    fee: Any = None
    amount: Any = None


@dataclass
class _FakeChain:
    payment: _FakePayment = field(default_factory=_FakePayment)


@dataclass
class _FakeReceipt:
    tx_hash: str = "0xtx_api"
    chain: str = "base"
    block_number: int = 1
    audit_anchor: str = "0x" + "00" * 32


@dataclass
class _FakeLedgerTx:
    tx_id: str = "ltx_api_001"


@dataclass
class _PolicyOK:
    allowed: bool = True
    reason: str = "OK"
    rule_id: str | None = None
    required_approvals: int = 0


@dataclass
class _ComplianceOK:
    allowed: bool = True
    reason: str = "OK"
    provider: str = "mock"
    rule_id: str = "mock_rule"
    audit_id: str = "audit"


@dataclass
class _MandateCheck:
    approved: bool = True
    reason: str = "OK"
    error_code: str | None = None
    requires_approval: bool = False
    mandate_version: int = 1


class _ApprovalMandate:
    id = "smdt_api_001"
    approval_threshold = Decimal("100")

    def check_payment(self, *, amount: Decimal, **_: Any) -> _MandateCheck:
        if amount > self.approval_threshold:
            return _MandateCheck(approved=True, requires_approval=True)
        return _MandateCheck(approved=True)

    def record_spend(self, amount: Decimal) -> None:  # pragma: no cover - stub
        pass

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id}


class _MockNotifier:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_approval_request(self, **kwargs: Any) -> Any:
        self.sent.append(kwargs)
        return MagicMock(provider="mock", handle="h", channels=(), step_up_issued=False, ok=True)


def _build():
    wallet_mgr = MagicMock()
    wallet_mgr.async_validate_policies = AsyncMock(return_value=_PolicyOK())
    wallet_mgr.async_record_spend = AsyncMock()
    compliance = MagicMock()
    compliance.preflight = AsyncMock(return_value=_ComplianceOK())
    chain_exec = MagicMock()
    chain_exec.dispatch_payment = AsyncMock(return_value=_FakeReceipt())
    ledger = MagicMock()
    ledger.append = MagicMock(return_value=_FakeLedgerTx())
    lookup = MagicMock()
    lookup.get_active_mandate = AsyncMock(return_value=_ApprovalMandate())
    lookup.record_spend = AsyncMock()

    store = InMemoryApprovalRequestStore()
    gate = ApprovalGate(store=store, notifier=_MockNotifier(), signing_secret="test")
    orch = PaymentOrchestrator(
        wallet_manager=wallet_mgr,
        compliance=compliance,
        chain_executor=chain_exec,
        ledger=ledger,
        spending_mandate_lookup=lookup,
        approval_gate=gate,
    )
    return orch, chain_exec, gate, store, lookup


def _client(orch, gate) -> TestClient:
    app = FastAPI()
    ar.set_deps(ar.ApprovalRequestDependencies(gate=gate, orchestrator=orch))
    app.include_router(ar.router, prefix="/api/v2/approval-requests")

    def _fake_principal() -> Principal:
        return Principal(kind="jwt", organization_id="org_demo", scopes=["*"])

    app.dependency_overrides[require_principal] = _fake_principal
    return TestClient(app)


# ── Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_pending_then_approve_executes_once():
    orch, chain_exec, gate, store, _ = _build()
    pending = await orch.execute_chain(_FakeChain())
    assert pending.status == "pending_approval"
    approval_id = pending.approval_id
    chain_exec.dispatch_payment.assert_not_awaited()

    client = _client(orch, gate)

    # List pending — the durable signed request shows up.
    resp = client.get("/api/v2/approval-requests")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["requests"][0]["id"] == approval_id
    assert data["requests"][0]["status"] == "pending"
    assert data["requests"][0]["amount"] == "250"

    # Approve via the decision callback -> re-executes through the engine.
    resp = client.post(
        f"/api/v2/approval-requests/{approval_id}/decision",
        json={"decision": "approve"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["executed"] is True
    assert body["payment_status"] == "submitted"
    assert body["chain_tx_hash"] == "0xtx_api"
    assert body["request"]["status"] == "approved"
    # Decision attributed to the authenticated principal, with signed evidence.
    assert body["request"]["decided_by"] == "org_demo"
    assert body["request"]["evidence"]["signature"]
    chain_exec.dispatch_payment.assert_awaited_once()

    # No longer pending.
    assert client.get("/api/v2/approval-requests").json()["total"] == 0


@pytest.mark.asyncio
async def test_revoke_between_approval_and_reexec_blocks_fail_closed():
    orch, chain_exec, gate, store, lookup = _build()
    pending = await orch.execute_chain(_FakeChain())
    client = _client(orch, gate)

    # Revoke the mandate AFTER the request is pending: the active lookup now
    # returns None (revoked rows are not 'active').
    lookup.get_active_mandate = AsyncMock(return_value=None)

    resp = client.post(
        f"/api/v2/approval-requests/{pending.approval_id}/decision",
        json={"decision": "approve"},
    )
    # Decision recorded, but re-execution blocked fail-closed — no money moved.
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["executed"] is False
    assert body["blocked_reason"]
    assert body["request"]["status"] == "approved"
    chain_exec.dispatch_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_deny_records_and_does_not_execute():
    orch, chain_exec, gate, store, _ = _build()
    pending = await orch.execute_chain(_FakeChain())
    client = _client(orch, gate)

    resp = client.post(
        f"/api/v2/approval-requests/{pending.approval_id}/decision",
        json={"decision": "deny", "reason": "not budgeted"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["executed"] is False
    assert body["request"]["status"] == "denied"
    chain_exec.dispatch_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_approve_does_not_settle_twice():
    orch, chain_exec, gate, store, _ = _build()
    pending = await orch.execute_chain(_FakeChain())
    client = _client(orch, gate)
    aid = pending.approval_id

    first = client.post(
        f"/api/v2/approval-requests/{aid}/decision", json={"decision": "approve"}
    )
    assert first.json()["executed"] is True

    # A second decision on a terminal (approved) request is refused (409); even
    # if it slipped through, the orchestrator would block re-execution.
    second = client.post(
        f"/api/v2/approval-requests/{aid}/decision", json={"decision": "approve"}
    )
    assert second.status_code == 409
    chain_exec.dispatch_payment.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_unknown_request_is_404():
    orch, _, gate, _, _ = _build()
    client = _client(orch, gate)
    assert client.get("/api/v2/approval-requests/apreq_nope").status_code == 404
