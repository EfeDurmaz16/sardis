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


def _make_deps(orchestrator, *, agents, wallets, wallet_manager=None):
    deps = A2ADependencies(
        wallet_repo=_WalletRepo(wallets),
        agent_repo=_AgentRepo(agents),
        chain_executor=object(),  # truthy: passes the "executor not available" gate
        wallet_manager=wallet_manager,
        ledger=None,
        compliance=None,
        identity_registry=None,
        trust_repo=None,
        audit_store=None,
        approval_service=None,
    )
    deps.orchestrator = orchestrator
    return deps


class _SpendCountingWalletManager:
    """Counts async_record_spend calls (proxy for policy spend recording)."""

    def __init__(self):
        self.record_calls = 0

    async def async_record_spend(self, _payment):
        self.record_calls += 1


class _SpendRecordingOrchestrator(_SpyOrchestrator):
    """Records spend exactly once via the wallet manager, like Phase 3.5."""

    def __init__(self, wallet_manager):
        super().__init__()
        self._wallet_manager = wallet_manager

    async def execute_chain(self, chain):
        result = await super().execute_chain(chain)
        # Mimic the orchestrator's Phase 3.5 spend recording.
        await self._wallet_manager.async_record_spend(chain.payment)
        return result


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


@pytest.mark.asyncio
async def test_a2a_payment_records_spend_exactly_once(_bypass_a2a_guardrails):
    """P2-7: the orchestrator owns spend recording (Phase 3.5). The a2a handler
    must NOT additionally call async_record_spend or policy totals double-count.
    """
    wm = _SpendCountingWalletManager()
    orch = _SpendRecordingOrchestrator(wm)
    agents = {
        "agent_sender": _Agent("agent_sender", "org_1"),
        "agent_recipient": _Agent("agent_recipient", "org_1"),
    }
    wallets = {"agent_recipient": _Wallet("agent_recipient", "wal_recipient")}
    deps = _make_deps(orch, agents=agents, wallets=wallets, wallet_manager=wm)

    resp = await _handle_payment_request(
        _msg(), request=object(), deps=deps, principal=_Principal()
    )

    assert resp.status == "completed", resp.error
    # Exactly once: the orchestrator recorded it; a2a must not record again.
    assert wm.record_calls == 1


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


# ---------------------------------------------------------------------------
# Orchestrator exception mapping: every deny / exec exception must produce a
# structured response, never a raw 500 / unhandled handler error.
# ---------------------------------------------------------------------------


class _RaisingOrchestrator:
    """execute_chain raises a preconfigured exception."""

    def __init__(self, exc):
        self._exc = exc

    async def execute_chain(self, chain):
        raise self._exc


def _orchestrator_exc(name, **kwargs):
    from sardis.core import orchestrator as orch

    return getattr(orch, name)("denied for test", **kwargs)


@pytest.fixture
def _bypass_a2a_guardrails(monkeypatch):
    """Skip the kill-switch/cap/anomaly guardrails so the test isolates the
    orchestrator exception mapping."""

    async def _noop(**_kwargs):
        return None

    monkeypatch.setattr(a2a, "_run_a2a_guardrails", _noop)


@pytest.mark.asyncio
@pytest.mark.parametrize("exc_name", ["KYAViolationError", "MandateViolationError"])
async def test_a2a_messages_deny_exceptions_map_to_failed_not_500(
    exc_name, _bypass_a2a_guardrails
):
    orch = _RaisingOrchestrator(_orchestrator_exc(exc_name))
    agents = {
        "agent_sender": _Agent("agent_sender", "org_1"),
        "agent_recipient": _Agent("agent_recipient", "org_1"),
    }
    wallets = {"agent_recipient": _Wallet("agent_recipient", "wal_recipient")}
    deps = _make_deps(orch, agents=agents, wallets=wallets)

    # Must NOT raise; must return a structured failed response.
    resp = await _handle_payment_request(
        _msg(), request=object(), deps=deps, principal=_Principal()
    )
    assert resp.status == "failed"
    assert resp.error_code == "policy_denied"


@pytest.mark.asyncio
async def test_a2a_messages_ledger_append_error_maps_to_execution_failed(
    _bypass_a2a_guardrails,
):
    orch = _RaisingOrchestrator(_orchestrator_exc("LedgerAppendError"))
    agents = {
        "agent_sender": _Agent("agent_sender", "org_1"),
        "agent_recipient": _Agent("agent_recipient", "org_1"),
    }
    wallets = {"agent_recipient": _Wallet("agent_recipient", "wal_recipient")}
    deps = _make_deps(orch, agents=agents, wallets=wallets)

    resp = await _handle_payment_request(
        _msg(), request=object(), deps=deps, principal=_Principal()
    )
    assert resp.status == "failed"
    assert resp.error_code == "execution_failed"


# ---- Site 1 (/pay): deny exceptions -> 403 + failure log/webhook ----------


@pytest.fixture
def _site1_neutralized(monkeypatch):
    """Run a2a_pay's inner _execute directly and capture the failure
    log/webhook emissions for the deny-exception assertions."""
    emitted = {"webhooks": [], "log_failed": 0}

    async def _run_idempotent(*_args, fn, **_kwargs):
        return await fn()

    def _idem_key(_request):
        return "idem_test"

    async def _rate_limit(**_kwargs):
        return None

    async def _guardrails(**_kwargs):
        return None

    async def _emit(_request, event, _payload):
        if event == "a2a.payment.failed":
            emitted["webhooks"].append(event)

    def _log(event, **_kwargs):
        if event == "a2a.payment.failed":
            emitted["log_failed"] += 1

    async def _alert(**_kwargs):
        return None

    monkeypatch.setattr(a2a, "run_idempotent", _run_idempotent)
    monkeypatch.setattr(a2a, "get_idempotency_key", _idem_key)
    monkeypatch.setattr(a2a, "enforce_agent_payment_rate_limit", _rate_limit)
    monkeypatch.setattr(a2a, "_run_a2a_guardrails", _guardrails)
    monkeypatch.setattr(a2a, "_emit_a2a_webhook", _emit)
    monkeypatch.setattr(a2a, "log_payment_event", _log)
    monkeypatch.setattr(a2a, "alert_payment_failure", _alert)
    return emitted


@pytest.mark.asyncio
@pytest.mark.parametrize("exc_name", ["KYAViolationError", "MandateViolationError"])
async def test_a2a_pay_deny_exceptions_return_403_with_failure_emission(
    exc_name, _site1_neutralized
):
    from decimal import Decimal

    from fastapi import HTTPException

    from server.routes.protocol.a2a import A2APayRequest, a2a_pay

    orch = _RaisingOrchestrator(_orchestrator_exc(exc_name))
    agents = {
        "agent_sender": _Agent("agent_sender", "org_1"),
        "agent_recipient": _Agent("agent_recipient", "org_1"),
    }
    wallets = {
        "agent_sender": _Wallet("agent_sender", "wal_sender"),
        "agent_recipient": _Wallet("agent_recipient", "wal_recipient"),
    }
    deps = _make_deps(orch, agents=agents, wallets=wallets)

    req = A2APayRequest(
        sender_agent_id="agent_sender",
        recipient_agent_id="agent_recipient",
        amount=Decimal("1.0"),
        token="USDC",
        chain="base_sepolia",
    )

    with pytest.raises(HTTPException) as exc_info:
        await a2a_pay(req, request=object(), deps=deps, principal=_Principal())

    # Deny outcomes are 403, not 500.
    assert exc_info.value.status_code == 403
    # Failure log + webhook still emitted on deny.
    assert _site1_neutralized["log_failed"] == 1
    assert _site1_neutralized["webhooks"] == ["a2a.payment.failed"]
