"""Test that orchestrator audit log is bounded to 10,000 entries."""
import pytest
from unittest.mock import AsyncMock, Mock
from sardis_v2_core.orchestrator import PaymentOrchestrator, ExecutionPhase


@pytest.fixture
def mock_components():
    """Create minimal mock components for orchestrator."""
    return {
        "wallet_manager": Mock(),
        "compliance": Mock(),
        "chain_executor": AsyncMock(),
        "ledger": Mock(),
    }


def test_audit_log_bounded_to_10k(mock_components):
    """Test that audit log only retains last 10,000 entries."""
    orchestrator = PaymentOrchestrator(**mock_components)

    # Add 20,000 entries
    for i in range(20_000):
        orchestrator._audit(
            mandate_id=f"mandate-{i}",
            phase=ExecutionPhase.POLICY_VALIDATION,
            success=True,
            details={"index": i},
        )

    # Should only have 10,000 entries
    assert len(orchestrator._audit_log) == 10_000

    # Should have the most recent 10,000 (entries 10,000-19,999)
    audit_entries = list(orchestrator._audit_log)
    assert audit_entries[0].mandate_id == "mandate-10000"
    assert audit_entries[-1].mandate_id == "mandate-19999"

    # Verify oldest entries were dropped
    assert not any(entry.mandate_id == "mandate-0" for entry in audit_entries)
    assert not any(entry.mandate_id == "mandate-9999" for entry in audit_entries)


def test_audit_log_get_audit_log_respects_limit(mock_components):
    """Test that get_audit_log respects the limit parameter."""
    orchestrator = PaymentOrchestrator(**mock_components)

    # Add 200 entries
    for i in range(200):
        orchestrator._audit(
            mandate_id=f"mandate-{i}",
            phase=ExecutionPhase.COMPLETED,
            success=True,
        )

    # Get last 50 entries
    recent = orchestrator.get_audit_log(limit=50)
    assert len(recent) == 50
    assert recent[0].mandate_id == "mandate-150"
    assert recent[-1].mandate_id == "mandate-199"


def test_audit_log_filter_by_mandate_id(mock_components):
    """Test that get_audit_log can filter by mandate_id."""
    orchestrator = PaymentOrchestrator(**mock_components)

    # Add entries for different mandates
    for i in range(100):
        orchestrator._audit(
            mandate_id="mandate-A" if i % 2 == 0 else "mandate-B",
            phase=ExecutionPhase.POLICY_VALIDATION,
            success=True,
        )

    # Filter by mandate_id
    mandate_a_logs = orchestrator.get_audit_log(mandate_id="mandate-A")
    assert len(mandate_a_logs) == 50
    assert all(entry.mandate_id == "mandate-A" for entry in mandate_a_logs)

    mandate_b_logs = orchestrator.get_audit_log(mandate_id="mandate-B")
    assert len(mandate_b_logs) == 50
    assert all(entry.mandate_id == "mandate-B" for entry in mandate_b_logs)


def test_audit_log_deque_type(mock_components):
    """Test that audit log is a deque with maxlen set."""
    from collections import deque

    orchestrator = PaymentOrchestrator(**mock_components)

    # Verify it's a deque
    assert isinstance(orchestrator._audit_log, deque)

    # Verify maxlen is set to 10,000
    assert orchestrator._audit_log.maxlen == 10_000
