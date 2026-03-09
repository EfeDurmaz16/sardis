"""Tests: Router migration to PaymentOrchestrator gateway.

Verifies that wallets.py, mandates.py, and ap2.py route all payment
execution through PaymentOrchestrator.execute_chain() instead of
calling dispatch_payment, async_validate_policies, compliance.preflight,
or async_record_spend directly from the router code.
"""
from __future__ import annotations

import inspect
import textwrap
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — mock objects used by multiple test classes
# ---------------------------------------------------------------------------


class MockPaymentResult:
    """Mimics orchestrator.PaymentResult returned by execute_chain."""

    def __init__(
        self,
        *,
        mandate_id: str = "mandate_test_001",
        status: str = "submitted",
        tx_hash: str = "0xabc123",
        chain: str = "base",
        audit_anchor: str = "anchor_test",
        ledger_tx_id: str = "ltx_001",
        compliance_provider: str | None = None,
        compliance_rule: str | None = None,
    ):
        self.mandate_id = mandate_id
        self.status = status
        self.tx_hash = tx_hash
        self.chain_tx_hash = tx_hash
        self.chain = chain
        self.audit_anchor = audit_anchor
        self.ledger_tx_id = ledger_tx_id
        self.ledger_entry_id = ledger_tx_id
        self.compliance_provider = compliance_provider
        self.compliance_rule = compliance_rule
        self.success = True
        self.receipt_id = "rcpt_001"
        self.error = ""


def _mock_orchestrator(*, success: bool = True, status: str = "submitted"):
    """Create a mock PaymentOrchestrator with configurable result."""
    orch = AsyncMock()
    if success:
        result = MockPaymentResult(status=status)
    else:
        from sardis_v2_core.orchestrator import ExecutionPhase, PolicyViolationError

        orch.execute_chain = AsyncMock(
            side_effect=PolicyViolationError("policy_denied", mandate_id="test")
        )
        return orch
    orch.execute_chain = AsyncMock(return_value=result)
    return orch


# ---------------------------------------------------------------------------
# Source inspection helpers
# ---------------------------------------------------------------------------


def _wallets_source() -> str:
    from sardis_api.routers import wallets
    return inspect.getsource(wallets)


def _mandates_source() -> str:
    from sardis_api.routers import mandates
    return inspect.getsource(mandates)


def _ap2_source() -> str:
    from sardis_api.routers import ap2
    return inspect.getsource(ap2)


# ===========================================================================
# Test Suite 1: wallets.py — transfer endpoint orchestrator migration
# ===========================================================================


class TestWalletsOrchestratorMigration:
    """wallets.py transfer endpoint uses PaymentOrchestrator."""

    def test_wallets_has_payment_orchestrator_attribute(self):
        """WalletDependencies must expose payment_orchestrator."""
        source = _wallets_source()
        assert "payment_orchestrator" in source, (
            "wallets.py must reference payment_orchestrator in dependencies"
        )

    def test_wallets_calls_execute_chain(self):
        """Transfer endpoint must call payment_orchestrator.execute_chain()."""
        source = _wallets_source()
        assert "execute_chain" in source, (
            "wallets.py transfer must call orchestrator.execute_chain()"
        )

    def test_wallets_no_direct_dispatch_payment_in_transfer(self):
        """Transfer endpoint must NOT call chain_executor.dispatch_payment directly
        (except for fee collection which is domain-specific)."""
        source = _wallets_source()
        # Find the _execute function for the transfer endpoint
        # dispatch_payment should only appear in fee collection context
        # Count occurrences: should be at most 1 (for fee mandate)
        transfer_section = _extract_transfer_function(source)
        if transfer_section:
            dispatch_count = transfer_section.count("dispatch_payment")
            # Only the fee collection should use dispatch_payment directly
            assert dispatch_count <= 1, (
                f"Transfer endpoint calls dispatch_payment {dispatch_count} times; "
                "primary payment should go through orchestrator"
            )

    def test_wallets_no_direct_validate_policies_in_transfer(self):
        """Transfer endpoint must NOT call async_validate_policies directly."""
        source = _wallets_source()
        transfer_section = _extract_transfer_function(source)
        if transfer_section:
            assert "async_validate_policies" not in transfer_section, (
                "Transfer endpoint must not call async_validate_policies directly; "
                "orchestrator handles policy validation"
            )

    def test_wallets_no_direct_compliance_preflight_in_transfer(self):
        """Transfer endpoint must NOT call compliance.preflight() directly."""
        source = _wallets_source()
        transfer_section = _extract_transfer_function(source)
        if transfer_section:
            assert "compliance.preflight" not in transfer_section, (
                "Transfer endpoint must not call compliance.preflight directly; "
                "orchestrator handles compliance"
            )

    def test_wallets_no_direct_record_spend_in_transfer(self):
        """Transfer endpoint must NOT call async_record_spend directly."""
        source = _wallets_source()
        transfer_section = _extract_transfer_function(source)
        if transfer_section:
            assert "async_record_spend" not in transfer_section, (
                "Transfer endpoint must not call async_record_spend directly; "
                "orchestrator handles spend recording"
            )

    def test_wallets_no_migrate_todo(self):
        """No remaining TODO comments about orchestrator migration in transfer."""
        source = _wallets_source()
        transfer_section = _extract_transfer_function(source)
        if transfer_section:
            assert "Migrate to PaymentOrchestrator" not in transfer_section, (
                "wallets.py still has TODO for orchestrator migration"
            )

    def test_wallets_handles_orchestrator_rejection(self):
        """Transfer endpoint must handle PolicyViolationError → 403."""
        source = _wallets_source()
        assert "PolicyViolationError" in source or "ComplianceViolationError" in source, (
            "wallets.py must catch orchestrator exceptions for proper HTTP error mapping"
        )


def _extract_transfer_function(source: str) -> str | None:
    """Extract the transfer endpoint's _execute function from wallets source."""
    # Find the async def transfer_crypto or _execute within it
    marker = 'async def transfer_crypto'
    idx = source.find(marker)
    if idx < 0:
        marker = 'def transfer_crypto'
        idx = source.find(marker)
    if idx < 0:
        return None
    # Get from the transfer function to the next top-level router endpoint
    end_marker = '@router.post("/{wallet_id}/freeze'
    end_idx = source.find(end_marker, idx)
    if end_idx < 0:
        end_idx = len(source)
    return source[idx:end_idx]


# ===========================================================================
# Test Suite 2: mandates.py — execute endpoint orchestrator migration
# ===========================================================================


class TestMandatesOrchestratorMigration:
    """mandates.py execute endpoint uses PaymentOrchestrator."""

    def test_mandates_has_payment_orchestrator(self):
        """Dependencies must expose payment_orchestrator."""
        source = _mandates_source()
        assert "payment_orchestrator" in source, (
            "mandates.py must reference payment_orchestrator"
        )

    def test_mandates_calls_execute_chain(self):
        """Execute endpoint must call payment_orchestrator.execute_chain()."""
        source = _mandates_source()
        assert "execute_chain" in source, (
            "mandates.py must call orchestrator.execute_chain()"
        )

    def test_mandates_no_direct_dispatch_payment_in_execute(self):
        """Execute endpoint must NOT call dispatch_payment directly."""
        source = _mandates_source()
        execute_section = _extract_execute_stored_function(source)
        if execute_section:
            assert "dispatch_payment" not in execute_section, (
                "mandates execute must not call dispatch_payment directly"
            )

    def test_mandates_no_direct_validate_policies_in_execute(self):
        """Execute endpoint must NOT call async_validate_policies directly."""
        source = _mandates_source()
        execute_section = _extract_execute_stored_function(source)
        if execute_section:
            assert "async_validate_policies" not in execute_section, (
                "mandates execute must not call async_validate_policies directly"
            )

    def test_mandates_no_direct_compliance_in_execute(self):
        """Execute endpoint must NOT call compliance.preflight() directly."""
        source = _mandates_source()
        execute_section = _extract_execute_stored_function(source)
        if execute_section:
            assert "compliance.preflight" not in execute_section, (
                "mandates execute must not call compliance.preflight directly"
            )

    def test_mandates_no_direct_record_spend_in_execute(self):
        """Execute endpoint must NOT call async_record_spend directly."""
        source = _mandates_source()
        execute_section = _extract_execute_stored_function(source)
        if execute_section:
            assert "async_record_spend" not in execute_section, (
                "mandates execute must not call async_record_spend directly"
            )

    def test_mandates_no_direct_ledger_append_in_execute(self):
        """Execute endpoint must NOT call ledger.append directly."""
        source = _mandates_source()
        execute_section = _extract_execute_stored_function(source)
        if execute_section:
            # ledger.append should not be called directly — orchestrator handles it
            assert "deps.ledger.append" not in execute_section, (
                "mandates execute must not call ledger.append directly"
            )

    def test_mandates_no_migrate_todo(self):
        """No remaining TODO comments about orchestrator migration."""
        source = _mandates_source()
        execute_section = _extract_execute_stored_function(source)
        if execute_section:
            assert "Migrate to PaymentOrchestrator" not in execute_section, (
                "mandates.py still has TODO for orchestrator migration"
            )

    def test_mandates_handles_orchestrator_rejection(self):
        """Execute endpoint must handle orchestrator exceptions → 403."""
        source = _mandates_source()
        assert "PolicyViolationError" in source or "ComplianceViolationError" in source, (
            "mandates.py must catch orchestrator exceptions"
        )


def _extract_execute_stored_function(source: str) -> str | None:
    """Extract the execute_stored_mandate function from mandates source."""
    marker = 'async def execute_stored_mandate'
    idx = source.find(marker)
    if idx < 0:
        return None
    # End at the next endpoint definition
    end_marker = '@router.post("/{mandate_id}/cancel'
    end_idx = source.find(end_marker, idx)
    if end_idx < 0:
        end_idx = len(source)
    return source[idx:end_idx]


# ===========================================================================
# Test Suite 3: ap2.py — payment endpoint orchestrator migration
# ===========================================================================


class TestAP2OrchestratorMigration:
    """ap2.py payment endpoint uses PaymentOrchestrator."""

    def test_ap2_has_orchestrator(self):
        """Dependencies must expose orchestrator."""
        source = _ap2_source()
        assert "orchestrator" in source, (
            "ap2.py must reference orchestrator in dependencies"
        )

    def test_ap2_calls_execute_chain(self):
        """AP2 endpoint must call orchestrator.execute_chain()."""
        source = _ap2_source()
        assert "execute_chain" in source, (
            "ap2.py must call orchestrator.execute_chain()"
        )

    def test_ap2_no_direct_validate_policies_in_execute(self):
        """AP2 execute must NOT call async_validate_policies directly."""
        source = _ap2_source()
        execute_section = _extract_ap2_execute_function(source)
        if execute_section:
            assert "async_validate_policies" not in execute_section, (
                "ap2 execute must not call async_validate_policies directly; "
                "orchestrator handles policy validation"
            )

    def test_ap2_no_direct_record_spend_in_execute(self):
        """AP2 execute must NOT call async_record_spend directly."""
        source = _ap2_source()
        execute_section = _extract_ap2_execute_function(source)
        if execute_section:
            assert "async_record_spend" not in execute_section, (
                "ap2 execute must not call async_record_spend directly; "
                "orchestrator handles spend recording"
            )

    def test_ap2_no_migrate_todo(self):
        """No remaining TODO comments about orchestrator migration."""
        source = _ap2_source()
        execute_section = _extract_ap2_execute_function(source)
        if execute_section:
            assert "Migrate to PaymentOrchestrator" not in execute_section, (
                "ap2.py still has TODO for orchestrator migration"
            )

    def test_ap2_keeps_audit_enrichment(self):
        """AP2-specific audit enrichment (policy receipts) should be preserved."""
        source = _ap2_source()
        # The policy receipt building and audit appending should stay
        assert "_try_build_policy_receipt" in source or "_append_policy_decision_audit" in source, (
            "ap2.py must retain AP2-specific audit enrichment functions"
        )

    def test_ap2_handles_orchestrator_rejection(self):
        """AP2 endpoint handles PolicyViolationError → 403."""
        source = _ap2_source()
        assert "PolicyViolationError" in source or "ComplianceViolationError" in source, (
            "ap2.py must catch orchestrator exceptions"
        )


def _extract_ap2_execute_function(source: str) -> str | None:
    """Extract the _execute inner function from AP2 payment endpoint."""
    marker = 'async def execute_ap2_payment'
    idx = source.find(marker)
    if idx < 0:
        return None
    # End at the next top-level function/endpoint
    end_marker = 'async def perform_compliance_checks'
    end_idx = source.find(end_marker, idx)
    if end_idx < 0:
        end_idx = len(source)
    return source[idx:end_idx]


# ===========================================================================
# Cross-cutting: no router should call dispatch_payment for primary payments
# ===========================================================================


class TestNoPrimaryDispatchPaymentInRouters:
    """Verify no router calls dispatch_payment for primary payment execution.

    dispatch_payment may still appear in fee collection (wallets.py) which is
    domain-specific and not orchestrated.
    """

    def test_mandates_zero_dispatch_payment(self):
        """mandates.py must have zero dispatch_payment calls."""
        source = _mandates_source()
        execute_section = _extract_execute_stored_function(source)
        if execute_section:
            assert "dispatch_payment" not in execute_section

    def test_ap2_no_direct_dispatch_payment(self):
        """ap2.py must not call dispatch_payment directly."""
        source = _ap2_source()
        execute_section = _extract_ap2_execute_function(source)
        if execute_section:
            # dispatch_payment should not appear — orchestrator / control plane handles it
            assert "deps.chain_executor.dispatch_payment" not in execute_section
            assert "deps.orchestrator.dispatch_payment" not in execute_section
