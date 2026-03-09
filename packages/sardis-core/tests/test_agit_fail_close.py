"""Tests for AGIT fail-close behaviour in the ControlPlane.

Default: AGIT verification errors reject the payment (fail-closed).
Override: SARDIS_AGIT_FAIL_OPEN=true allows the payment to proceed.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from sardis_v2_core.config import SardisSettings
from sardis_v2_core.control_plane import ControlPlane
from sardis_v2_core.execution_intent import ExecutionIntent, IntentSource, IntentStatus


def _make_intent(agent_id: str = "agent_test123") -> ExecutionIntent:
    """Create a minimal ExecutionIntent for testing."""
    return ExecutionIntent(
        source=IntentSource.A2A,
        org_id="org_test",
        agent_id=agent_id,
        amount=Decimal("10.00"),
        currency="USDC",
        chain="base",
    )


def _make_failing_agit_engine(error_msg: str = "AGIT service unavailable") -> MagicMock:
    """Create an AGIT policy engine mock that raises on verify_policy_chain."""
    engine = MagicMock()
    engine.verify_policy_chain.side_effect = RuntimeError(error_msg)
    return engine


@pytest.mark.asyncio
async def test_agit_error_rejects_payment_by_default():
    """When AGIT verification raises and agit_fail_open=False (default), payment is rejected."""
    settings = SardisSettings(agit_fail_open=False)
    agit_engine = _make_failing_agit_engine("connection timeout")

    cp = ControlPlane(
        agit_policy_engine=agit_engine,
        settings=settings,
    )

    intent = _make_intent()
    result = await cp.submit(intent)

    assert result.success is False
    assert result.status == IntentStatus.REJECTED
    assert "AGIT policy verification unavailable" in result.error
    assert "connection timeout" in result.error


@pytest.mark.asyncio
async def test_agit_error_allows_when_fail_open():
    """When AGIT verification raises and agit_fail_open=True, payment proceeds."""
    settings = SardisSettings(agit_fail_open=True)
    agit_engine = _make_failing_agit_engine("connection timeout")

    cp = ControlPlane(
        agit_policy_engine=agit_engine,
        settings=settings,
    )

    intent = _make_intent()
    result = await cp.submit(intent)

    # Should NOT be rejected — pipeline continues past AGIT
    assert result.status != IntentStatus.REJECTED or "AGIT" not in (result.error or "")
    # The intent should have progressed beyond the AGIT step (completed or failed
    # for another reason, but not AGIT-rejected).
    assert result.success is True or "AGIT" not in (result.error or "")


@pytest.mark.asyncio
async def test_agit_fail_open_default_is_false():
    """Verify the SardisSettings default for agit_fail_open is False (safe)."""
    settings = SardisSettings()
    assert settings.agit_fail_open is False


@pytest.mark.asyncio
async def test_agit_success_is_unaffected():
    """When AGIT verification succeeds (valid chain), payment proceeds regardless of flag."""
    settings = SardisSettings(agit_fail_open=False)

    agit_engine = MagicMock()
    verification = MagicMock()
    verification.valid = True
    agit_engine.verify_policy_chain.return_value = verification

    cp = ControlPlane(
        agit_policy_engine=agit_engine,
        settings=settings,
    )

    intent = _make_intent()
    result = await cp.submit(intent)

    # Should not be rejected by AGIT
    assert "AGIT" not in (result.error or "")


@pytest.mark.asyncio
async def test_no_agit_engine_skips_check():
    """When no AGIT engine is configured, the check is skipped entirely."""
    settings = SardisSettings(agit_fail_open=False)

    cp = ControlPlane(
        agit_policy_engine=None,
        settings=settings,
    )

    intent = _make_intent()
    result = await cp.submit(intent)

    # Should complete without AGIT-related errors
    assert "AGIT" not in (result.error or "")
