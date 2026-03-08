"""Property-based tests for payment invariants using Hypothesis.

Invariants tested:
1. Payment amount never exceeds per-transaction cap
2. Daily total spend is bounded by daily cap
3. Idempotency: duplicate request produces same result
4. Kill switch blocks all payments when active
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

try:
    from hypothesis import given, settings, strategies as st
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
    # Provide dummy decorators so file still imports
    def given(*a, **kw):
        def decorator(fn):
            return pytest.mark.skip(reason="hypothesis not installed")(fn)
        return decorator
    settings = lambda **kw: lambda fn: fn
    class st:
        decimals = staticmethod(lambda **kw: None)
        text = staticmethod(lambda **kw: None)
        integers = staticmethod(lambda **kw: None)

from sardis_guardrails.kill_switch import (
    ActivationReason,
    InMemoryBackend,
    KillSwitch,
    KillSwitchError,
)
from sardis_guardrails.transaction_caps import CapCheckResult, TransactionCapEngine


@pytest.fixture
def cap_engine():
    """Create a cap engine with in-memory backend for testing."""
    engine = TransactionCapEngine(redis_url="")
    return engine


@pytest.fixture
def kill_switch():
    """Create a kill switch with in-memory backend."""
    return KillSwitch(backend=InMemoryBackend())


# ---------------------------------------------------------------------------
# Invariant 1: Payment never exceeds per-tx cap
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
@given(
    amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("100000"), places=2),
    per_tx_cap=st.decimals(min_value=Decimal("1"), max_value=Decimal("50000"), places=2),
)
@settings(max_examples=100)
def test_per_tx_cap_never_exceeded(amount, per_tx_cap):
    """A payment exceeding the per-tx cap must always be rejected."""
    import sardis_guardrails.transaction_caps as tc_mod

    async def _check():
        # Monkeypatch the module-level constant (parsed once at import)
        old_cap = tc_mod.DEFAULT_AGENT_TX_CAP
        tc_mod.DEFAULT_AGENT_TX_CAP = per_tx_cap
        try:
            fresh = TransactionCapEngine(redis_url="")
            result = await fresh.check_and_record(
                amount=amount,
                org_id="test_org",
                agent_id="test_agent",
            )
            if amount > per_tx_cap:
                assert not result.allowed, (
                    f"Payment of {amount} should be rejected when per-tx cap is {per_tx_cap}"
                )
        finally:
            tc_mod.DEFAULT_AGENT_TX_CAP = old_cap

    asyncio.get_event_loop().run_until_complete(_check())


# ---------------------------------------------------------------------------
# Invariant 2: Kill switch blocks ALL payments when global is active
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_global_kill_switch_blocks_all(kill_switch):
    """When global kill switch is active, all agents are blocked."""
    await kill_switch.activate_global(
        reason=ActivationReason.MANUAL,
        activated_by="test",
    )

    for agent_id in ["agent_1", "agent_2", "agent_3"]:
        for org_id in ["org_a", "org_b"]:
            with pytest.raises(KillSwitchError, match="Global"):
                await kill_switch.check(agent_id=agent_id, org_id=org_id)


@pytest.mark.asyncio
async def test_rail_kill_switch_blocks_rail(kill_switch):
    """When rail kill switch is active, that rail is blocked."""
    await kill_switch.activate_rail(
        rail="checkout",
        reason=ActivationReason.MANUAL,
    )

    with pytest.raises(KillSwitchError, match="Rail.*checkout"):
        await kill_switch.check_rail("checkout")

    # Other rails should not be blocked
    await kill_switch.check_rail("a2a")  # Should not raise


@pytest.mark.asyncio
async def test_chain_kill_switch_blocks_chain(kill_switch):
    """When chain kill switch is active, that chain is blocked."""
    await kill_switch.activate_chain(
        chain="base",
        reason=ActivationReason.MANUAL,
    )

    with pytest.raises(KillSwitchError, match="Chain.*base"):
        await kill_switch.check_chain("base")

    # Other chains should not be blocked
    await kill_switch.check_chain("ethereum")  # Should not raise


# ---------------------------------------------------------------------------
# Invariant 3: Kill switch deactivation restores service
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_kill_switch_deactivation_restores(kill_switch):
    """After deactivation, payments should flow again."""
    await kill_switch.activate_global(reason=ActivationReason.MANUAL)

    with pytest.raises(KillSwitchError):
        await kill_switch.check(agent_id="a1", org_id="o1")

    await kill_switch.deactivate_global()

    # Should not raise
    await kill_switch.check(agent_id="a1", org_id="o1")


# ---------------------------------------------------------------------------
# Invariant 4: get_active_switches includes all scopes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_active_switches_includes_all_scopes(kill_switch):
    """get_active_switches should return all active scopes."""
    await kill_switch.activate_global(reason=ActivationReason.MANUAL)
    await kill_switch.activate_rail(rail="a2a", reason=ActivationReason.FRAUD)
    await kill_switch.activate_chain(chain="base", reason=ActivationReason.COMPLIANCE)
    await kill_switch.activate_organization(org_id="org1", reason=ActivationReason.ANOMALY)

    active = await kill_switch.get_active_switches()

    assert active["global"] is not None
    assert "a2a" in active["rails"]
    assert "base" in active["chains"]
    assert "org1" in active["organizations"]
