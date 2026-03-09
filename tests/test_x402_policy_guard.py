"""Tests for x402 policy guard — control plane integration."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sardis_v2_core.control_plane import ControlPlane
from sardis_v2_core.execution_intent import (
    ExecutionIntent,
    ExecutionResult,
    IntentSource,
    IntentStatus,
    SimulationResult,
)
from sardis_v2_core.x402_policy_guard import X402PolicyDenied, X402PolicyGuard


def _make_challenge(**overrides):
    from sardis_protocol.x402 import X402Challenge
    defaults = {
        "payment_id": "x402_test123",
        "resource_uri": "https://api.example.com/data",
        "amount": "1000000",  # 1 USDC in atomic units
        "currency": "USDC",
        "payee_address": "0x" + "a" * 40,
        "network": "base",
        "token_address": "0x" + "b" * 40,
        "expires_at": 9999999999,
        "nonce": "test_nonce_123",
    }
    defaults.update(overrides)
    return X402Challenge(**defaults)


def _make_control_plane(**kwargs) -> ControlPlane:
    return ControlPlane(**kwargs)


@pytest.mark.asyncio
async def test_x402_through_control_plane():
    """Full pipeline: x402 challenge -> control plane simulate -> approved."""
    policy_eval = AsyncMock(return_value={"allowed": True})
    compliance = AsyncMock(return_value={"allowed": True})
    cp = _make_control_plane(
        policy_evaluator=MagicMock(evaluate=policy_eval),
        compliance_checker=MagicMock(check=compliance),
    )
    guard = X402PolicyGuard(cp)
    challenge = _make_challenge()

    ok, reason = await guard.evaluate(challenge, "agent_1", "org_1", "wal_1")

    assert ok is True
    assert reason == ""
    policy_eval.assert_called_once()
    # Verify the intent was built correctly
    call_args = policy_eval.call_args[0][0]
    assert isinstance(call_args, ExecutionIntent)
    assert call_args.source == IntentSource.X402
    assert call_args.amount == Decimal("1")  # 1000000 / 1000000
    assert call_args.chain == "base"


@pytest.mark.asyncio
async def test_per_tx_limit_applies():
    """Spending policy per-tx limit blocks the x402 payment."""
    policy_eval = AsyncMock(return_value={
        "allowed": False,
        "reason": "per_transaction_limit_exceeded: $1.00 exceeds $0.50 limit",
    })
    cp = _make_control_plane(
        policy_evaluator=MagicMock(evaluate=policy_eval),
    )
    guard = X402PolicyGuard(cp)
    challenge = _make_challenge()

    ok, reason = await guard.evaluate(challenge, "agent_1", "org_1", "wal_1")

    assert ok is False
    assert "per_transaction_limit_exceeded" in reason


@pytest.mark.asyncio
async def test_daily_limit_applies():
    """Time window (daily) limit blocks the x402 payment."""
    policy_eval = AsyncMock(return_value={
        "allowed": False,
        "reason": "daily_limit_exceeded: $100 daily cap reached",
    })
    cp = _make_control_plane(
        policy_evaluator=MagicMock(evaluate=policy_eval),
    )
    guard = X402PolicyGuard(cp)
    challenge = _make_challenge()

    ok, reason = await guard.evaluate(challenge, "agent_1", "org_1", "wal_1")

    assert ok is False
    assert "daily_limit" in reason


@pytest.mark.asyncio
async def test_kill_switch_blocks_x402():
    """Kill switch blocks x402 payments."""
    from sardis_guardrails.kill_switch import KillSwitchError

    kill_switch = AsyncMock()
    kill_switch.check = AsyncMock(side_effect=KillSwitchError("global kill switch active"))
    kill_switch.check_chain = AsyncMock()

    cp = _make_control_plane(kill_switch=kill_switch)
    guard = X402PolicyGuard(cp)
    challenge = _make_challenge()

    result = await guard.submit(challenge, "agent_1", "org_1", "wal_1")

    assert result.success is False
    assert "kill_switch" in result.error


@pytest.mark.asyncio
async def test_anomaly_engine_flags_x402():
    """Anomaly scoring works for x402 payments."""
    from datetime import UTC, datetime

    from sardis_guardrails.anomaly_engine import RiskAction, RiskAssessment, RiskSignal

    anomaly = MagicMock()
    anomaly.assess_risk = MagicMock(return_value=RiskAssessment(
        agent_id="agent_1",
        overall_score=0.95,
        action=RiskAction.FREEZE_AGENT,
        signals=[RiskSignal(signal_type="amount_spike", weight=1.0, score=0.95, description="Unusually high")],
        timestamp=datetime.now(UTC),
    ))

    policy_eval = AsyncMock(return_value={"allowed": True})
    cp = _make_control_plane(
        policy_evaluator=MagicMock(evaluate=policy_eval),
        anomaly_engine=anomaly,
    )
    guard = X402PolicyGuard(cp)
    challenge = _make_challenge()

    result = await guard.submit(challenge, "agent_1", "org_1", "wal_1")

    assert result.success is False
    assert "anomaly" in result.error or "frozen" in result.error


@pytest.mark.asyncio
async def test_dry_run_simulate_only():
    """Simulate (evaluate) doesn't execute on chain."""
    chain_executor = AsyncMock()
    policy_eval = AsyncMock(return_value={"allowed": True})
    compliance = AsyncMock(return_value={"allowed": True})

    cp = _make_control_plane(
        policy_evaluator=MagicMock(evaluate=policy_eval),
        compliance_checker=MagicMock(check=compliance),
        chain_executor=MagicMock(execute=chain_executor),
    )
    guard = X402PolicyGuard(cp)
    challenge = _make_challenge()

    ok, reason = await guard.evaluate(challenge, "agent_1", "org_1", "wal_1")

    assert ok is True
    # Chain executor should NOT have been called (simulate != submit)
    chain_executor.assert_not_called()


@pytest.mark.asyncio
async def test_intent_source_is_x402():
    """Verify the intent source is correctly set to X402."""
    policy_eval = AsyncMock(return_value={"allowed": True})
    cp = _make_control_plane(
        policy_evaluator=MagicMock(evaluate=policy_eval),
    )
    guard = X402PolicyGuard(cp)
    challenge = _make_challenge()

    await guard.evaluate(challenge, "agent_1", "org_1", "wal_1")

    intent: ExecutionIntent = policy_eval.call_args[0][0]
    assert intent.source == IntentSource.X402
    assert intent.metadata["x402_payment_id"] == "x402_test123"
    assert intent.metadata["resource_uri"] == "https://api.example.com/data"
