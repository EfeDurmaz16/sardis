"""Phase 0 Task 4: a2a payments must route through PaymentOrchestrator.execute_chain.

These tests lock in that the deprecated ControlPlane.submit execution path is
retired from a2a, that the single fail-closed orchestrator path is used, and that
upstream verification (identity/trust/agent validation) is still performed BEFORE
any execution is attempted.
"""
from __future__ import annotations

import inspect
import types
from decimal import Decimal

import pytest

import server.routes.protocol.a2a as a2a
from server.routes.protocol.a2a import (
    A2ADependencies,
    A2AMessageRequest,
    _handle_payment_request,
)


# ---------------------------------------------------------------------------
# Source-level guard: ControlPlane.submit path is gone
# ---------------------------------------------------------------------------


def test_a2a_module_does_not_use_control_plane_submit():
    src = inspect.getsource(a2a)
    assert "cp.submit(" not in src and "ControlPlane(" not in src, (
        "a2a must route through execute_chain, not the deprecated ControlPlane.submit"
    )


def test_a2a_module_uses_orchestrator_and_factory():
    src = inspect.getsource(a2a)
    assert "execute_chain(" in src, "a2a must call the orchestrator's execute_chain"
    assert "build_mandate_chain(" in src, "a2a must build the chain via the typed factory"


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _SpyOrchestrator:
    """Records every execute_chain call and returns a canned PaymentResult."""

    def __init__(self):
        self.calls = []

    async def execute_chain(self, chain):
        self.calls.append(chain)
        return types.SimpleNamespace(
            mandate_id=chain.payment.mandate_id,
            ledger_tx_id="ledger_test",
            chain_tx_hash="0xdeadbeef",
            chain=chain.payment.chain,
            audit_anchor="anchor_test",
            status="submitted",
            receipt_id="rcpt_test",
            data={},
        )


class _Agent:
    def __init__(self, agent_id, owner_id, is_active=True):
        self.agent_id = agent_id
        self.owner_id = owner_id
        self.is_active = is_active


class _Wallet:
    def __init__(self, agent_id, wallet_id):
        self.agent_id = agent_id
        self.wallet_id = wallet_id
        self.is_active = True
        self.is_frozen = False

    def get_address(self, chain):
        return "0x" + "11" * 20


class _AgentRepo:
    def __init__(self, agents):
        self._agents = agents

    async def get(self, agent_id):
        return self._agents.get(agent_id)


class _WalletRepo:
    def __init__(self, wallets):
        self._wallets = wallets

    async def get_by_agent(self, agent_id):
        return self._wallets.get(agent_id)


class _Principal:
    def __init__(self, org_id="org_1", is_admin=True):
        self.organization_id = org_id
        self.is_admin = is_admin


def _make_deps(orchestrator, *, agents, wallets):
    deps = A2ADependencies(
        wallet_repo=_WalletRepo(wallets),
        agent_repo=_AgentRepo(agents),
        chain_executor=object(),  # truthy: passes the "executor not available" gate
        wallet_manager=None,
        ledger=None,
        compliance=None,
        identity_registry=None,
        trust_repo=None,
        audit_store=None,
        approval_service=None,
    )
    deps.orchestrator = orchestrator
    return deps


def _msg(sender="agent_sender", recipient="agent_recipient"):
    return A2AMessageRequest(
        message_type="payment_request",
        sender_id=sender,
        recipient_id=recipient,
        payload={
            "sender_agent_id": sender,
            "recipient_agent_id": recipient,
            "amount_minor": 1_000_000,  # 1.0 USDC at 6 decimals
            "token": "USDC",
            "chain": "base_sepolia",
            "destination": "0x" + "22" * 20,
        },
    )


@pytest.fixture(autouse=True)
def _bypass_trust_and_guardrails(monkeypatch):
    """Neutralize trust + guardrail side effects so the test isolates the
    execution-path swap. Verification of the trust gate itself is covered by
    the dedicated a2a trust tests."""

    async def _trust_ok(**_kwargs):
        return True, "ok", None

    monkeypatch.setattr(a2a, "_check_a2a_trust_relation_with_deps", _trust_ok)

    # Allow cross-org so the admin/org gate never short-circuits the path.
    monkeypatch.setattr(a2a, "_allow_cross_org_a2a", lambda: True)


# ---------------------------------------------------------------------------
# Behavioral: a successful payment goes through execute_chain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_payment_request_calls_execute_chain():
    spy = _SpyOrchestrator()
    agents = {
        "agent_sender": _Agent("agent_sender", "org_1"),
        "agent_recipient": _Agent("agent_recipient", "org_1"),
    }
    wallets = {"agent_recipient": _Wallet("agent_recipient", "wal_recipient")}
    deps = _make_deps(spy, agents=agents, wallets=wallets)

    resp = await _handle_payment_request(
        _msg(), request=object(), deps=deps, principal=_Principal()
    )

    assert resp.status == "completed", resp.error
    assert len(spy.calls) == 1, "execute_chain must be called exactly once"
    chain = spy.calls[0]
    # Field mapping sanity: amount in minor units, token, chain, destination.
    assert chain.payment.amount_minor == 1_000_000
    assert chain.payment.token == "USDC"
    assert chain.payment.chain == "base_sepolia"
    assert chain.payment.destination == "0x" + "22" * 20


# ---------------------------------------------------------------------------
# Verification preserved: an unverified/invalid inbound request is rejected
# upstream WITHOUT ever reaching execute_chain.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a2a_unverified_request_rejected_before_execution():
    spy = _SpyOrchestrator()
    # Sender agent does not exist -> upstream validation must reject.
    agents = {"agent_recipient": _Agent("agent_recipient", "org_1")}
    wallets = {"agent_recipient": _Wallet("agent_recipient", "wal_recipient")}
    deps = _make_deps(spy, agents=agents, wallets=wallets)

    resp = await _handle_payment_request(
        _msg(), request=object(), deps=deps, principal=_Principal()
    )

    assert resp.status == "failed"
    assert resp.error_code == "sender_not_found"
    assert spy.calls == [], "execute_chain must NOT run when verification fails"
