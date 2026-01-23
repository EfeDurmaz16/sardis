"""Payment orchestration tying mandates, policies, compliance, and execution.

This module provides the ONLY entry point for payment execution. All payments
MUST flow through PaymentOrchestrator.execute_chain() to ensure:

1. Policy validation (fail-fast)
2. Compliance check (fail-fast)
3. Chain execution (with rollback tracking)
4. Ledger append (with reconciliation queue on failure)

IMPORTANT: Never bypass this orchestrator to execute payments directly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from sardis_v2_core.mandates import MandateChain, PaymentMandate

logger = logging.getLogger(__name__)


# ============ Execution Phases ============


class ExecutionPhase(str, Enum):
    """Phases of payment execution for audit/debugging."""
    POLICY_VALIDATION = "policy_validation"
    COMPLIANCE_CHECK = "compliance_check"
    CHAIN_EXECUTION = "chain_execution"
    LEDGER_APPEND = "ledger_append"
    COMPLETED = "completed"
    FAILED = "failed"


# ============ Result Types ============


@dataclass(slots=True)
class PaymentResult:
    """Result of a successful payment execution."""
    mandate_id: str
    ledger_tx_id: str
    chain_tx_hash: str
    chain: str
    audit_anchor: str
    status: str = "submitted"
    compliance_provider: str | None = None
    compliance_rule: str | None = None
    execution_time_ms: float = 0.0


@dataclass
class ExecutionAuditEntry:
    """Audit entry tracking each phase of execution."""
    mandate_id: str
    phase: ExecutionPhase
    success: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ReconciliationEntry:
    """Entry for failed ledger appends requiring reconciliation."""
    mandate_id: str
    chain_tx_hash: str
    chain: str
    audit_anchor: str
    payment_mandate: Any  # PaymentMandate
    chain_receipt: Any  # ChainReceipt
    error: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    last_retry: Optional[datetime] = None
    resolved: bool = False


# ============ Exceptions ============


class PaymentExecutionError(Exception):
    """Base exception for payment execution failures."""

    def __init__(
        self,
        message: str,
        phase: ExecutionPhase,
        mandate_id: str | None = None,
        details: Dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.phase = phase
        self.mandate_id = mandate_id
        self.details = details or {}


class PolicyViolationError(PaymentExecutionError):
    """Raised when payment violates wallet policy."""

    def __init__(self, message: str, mandate_id: str | None = None, rule_id: str | None = None):
        super().__init__(
            message,
            phase=ExecutionPhase.POLICY_VALIDATION,
            mandate_id=mandate_id,
            details={"rule_id": rule_id},
        )
        self.rule_id = rule_id


class ComplianceViolationError(PaymentExecutionError):
    """Raised when payment fails compliance check."""

    def __init__(
        self,
        message: str,
        mandate_id: str | None = None,
        provider: str | None = None,
        rule_id: str | None = None,
    ):
        super().__init__(
            message,
            phase=ExecutionPhase.COMPLIANCE_CHECK,
            mandate_id=mandate_id,
            details={"provider": provider, "rule_id": rule_id},
        )
        self.provider = provider
        self.rule_id = rule_id


class ChainExecutionError(PaymentExecutionError):
    """Raised when chain execution fails."""

    def __init__(self, message: str, mandate_id: str | None = None, chain: str | None = None):
        super().__init__(
            message,
            phase=ExecutionPhase.CHAIN_EXECUTION,
            mandate_id=mandate_id,
            details={"chain": chain},
        )
        self.chain = chain


class LedgerAppendError(PaymentExecutionError):
    """Raised when ledger append fails (queued for reconciliation)."""

    def __init__(
        self,
        message: str,
        mandate_id: str | None = None,
        chain_tx_hash: str | None = None,
    ):
        super().__init__(
            message,
            phase=ExecutionPhase.LEDGER_APPEND,
            mandate_id=mandate_id,
            details={"chain_tx_hash": chain_tx_hash},
        )
        self.chain_tx_hash = chain_tx_hash


# ============ Protocol Interfaces ============


class WalletPolicyEngine(Protocol):
    def validate_policies(self, mandate: PaymentMandate) -> "PolicyEvaluation": ...


class CompliancePort(Protocol):
    def preflight(self, mandate: PaymentMandate) -> "ComplianceResult": ...


class ChainExecutorPort(Protocol):
    async def dispatch_payment(self, mandate: PaymentMandate) -> "ChainReceipt": ...


class LedgerPort(Protocol):
    def append(self, payment_mandate: PaymentMandate, chain_receipt: "ChainReceipt") -> "Transaction": ...


class ReconciliationQueuePort(Protocol):
    """Interface for reconciliation queue storage."""

    def enqueue(self, entry: ReconciliationEntry) -> str: ...
    def get_pending(self, limit: int = 100) -> List[ReconciliationEntry]: ...
    def mark_resolved(self, mandate_id: str) -> bool: ...
    def increment_retry(self, mandate_id: str) -> bool: ...


# ============ In-Memory Reconciliation Queue ============


class InMemoryReconciliationQueue:
    """
    In-memory reconciliation queue for failed ledger appends.

    In production, this should be replaced with a persistent store
    (database table or message queue) to survive restarts.
    """

    MAX_RETRIES = 5

    def __init__(self):
        self._queue: Dict[str, ReconciliationEntry] = {}

    def enqueue(self, entry: ReconciliationEntry) -> str:
        """Add entry to reconciliation queue."""
        self._queue[entry.mandate_id] = entry
        logger.warning(
            f"Ledger append queued for reconciliation: mandate_id={entry.mandate_id}, "
            f"tx_hash={entry.chain_tx_hash}, error={entry.error}"
        )
        return entry.mandate_id

    def get_pending(self, limit: int = 100) -> List[ReconciliationEntry]:
        """Get pending reconciliation entries."""
        pending = [
            e for e in self._queue.values()
            if not e.resolved and e.retry_count < self.MAX_RETRIES
        ]
        return sorted(pending, key=lambda e: e.created_at)[:limit]

    def mark_resolved(self, mandate_id: str) -> bool:
        """Mark entry as resolved."""
        if mandate_id in self._queue:
            self._queue[mandate_id].resolved = True
            logger.info(f"Reconciliation resolved: mandate_id={mandate_id}")
            return True
        return False

    def increment_retry(self, mandate_id: str) -> bool:
        """Increment retry count for an entry."""
        if mandate_id in self._queue:
            entry = self._queue[mandate_id]
            entry.retry_count += 1
            entry.last_retry = datetime.now(timezone.utc)
            return True
        return False

    def count_pending(self) -> int:
        """Count pending entries."""
        return len([e for e in self._queue.values() if not e.resolved])


# ============ Payment Orchestrator ============


class PaymentOrchestrator:
    """
    Executes verified mandate chains against policies, compliance, and chain executors.

    This is the ONLY authorized entry point for payment execution.

    Execution flow:
    1. Policy validation (fail-fast on violation)
    2. Compliance check (fail-fast on violation)
    3. Chain execution (track for rollback if subsequent steps fail)
    4. Ledger append (queue for reconciliation on failure)

    All execution phases are audited for debugging and regulatory compliance.
    """

    def __init__(
        self,
        *,
        wallet_manager: WalletPolicyEngine,
        compliance: CompliancePort,
        chain_executor: ChainExecutorPort,
        ledger: LedgerPort,
        reconciliation_queue: ReconciliationQueuePort | None = None,
    ) -> None:
        self._wallet_manager = wallet_manager
        self._compliance = compliance
        self._chain_executor = chain_executor
        self._ledger = ledger
        self._reconciliation_queue = reconciliation_queue or InMemoryReconciliationQueue()
        self._audit_log: List[ExecutionAuditEntry] = []

    def _audit(
        self,
        mandate_id: str,
        phase: ExecutionPhase,
        success: bool,
        details: Dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Record an audit entry for execution phase."""
        entry = ExecutionAuditEntry(
            mandate_id=mandate_id,
            phase=phase,
            success=success,
            details=details or {},
            error=error,
        )
        self._audit_log.append(entry)

        if success:
            logger.info(f"[{phase.value}] mandate={mandate_id} SUCCESS")
        else:
            logger.warning(f"[{phase.value}] mandate={mandate_id} FAILED: {error}")

    async def execute_chain(self, chain: MandateChain) -> PaymentResult:
        """
        Execute a verified mandate chain.

        This is the ONLY entry point for payment execution.

        Args:
            chain: Verified mandate chain containing intent, cart, and payment mandates

        Returns:
            PaymentResult on success

        Raises:
            PolicyViolationError: If payment violates wallet policy
            ComplianceViolationError: If payment fails compliance check
            ChainExecutionError: If chain execution fails
            LedgerAppendError: If ledger append fails (payment still executed on-chain)
        """
        import time
        start_time = time.time()

        payment = chain.payment
        mandate_id = payment.mandate_id

        logger.info(f"Starting payment execution: mandate_id={mandate_id}")

        # Phase 1: Policy Validation (fail-fast)
        try:
            policy = self._wallet_manager.validate_policies(payment)
            if not policy.allowed:
                self._audit(mandate_id, ExecutionPhase.POLICY_VALIDATION, False,
                           {"rule_id": getattr(policy, 'rule_id', None)},
                           policy.reason)
                raise PolicyViolationError(
                    policy.reason or "policy_denied",
                    mandate_id=mandate_id,
                    rule_id=getattr(policy, 'rule_id', None),
                )
            self._audit(mandate_id, ExecutionPhase.POLICY_VALIDATION, True,
                       {"rule_id": getattr(policy, 'rule_id', None)})
        except PolicyViolationError:
            raise
        except Exception as e:
            self._audit(mandate_id, ExecutionPhase.POLICY_VALIDATION, False, error=str(e))
            raise PolicyViolationError(f"Policy validation error: {e}", mandate_id=mandate_id)

        # Phase 2: Compliance Check (fail-fast)
        try:
            compliance = self._compliance.preflight(payment)
            if not compliance.allowed:
                self._audit(mandate_id, ExecutionPhase.COMPLIANCE_CHECK, False,
                           {"provider": compliance.provider, "rule_id": compliance.rule_id},
                           compliance.reason)
                raise ComplianceViolationError(
                    compliance.reason or "compliance_denied",
                    mandate_id=mandate_id,
                    provider=compliance.provider,
                    rule_id=compliance.rule_id,
                )
            self._audit(mandate_id, ExecutionPhase.COMPLIANCE_CHECK, True,
                       {"provider": compliance.provider, "rule_id": compliance.rule_id,
                        "audit_id": getattr(compliance, 'audit_id', None)})
        except ComplianceViolationError:
            raise
        except Exception as e:
            self._audit(mandate_id, ExecutionPhase.COMPLIANCE_CHECK, False, error=str(e))
            raise ComplianceViolationError(f"Compliance check error: {e}", mandate_id=mandate_id)

        # Phase 3: Chain Execution
        receipt = None
        try:
            receipt = await self._chain_executor.dispatch_payment(payment)
            self._audit(mandate_id, ExecutionPhase.CHAIN_EXECUTION, True,
                       {"tx_hash": receipt.tx_hash, "chain": receipt.chain,
                        "block_number": receipt.block_number})
        except Exception as e:
            self._audit(mandate_id, ExecutionPhase.CHAIN_EXECUTION, False, error=str(e))
            raise ChainExecutionError(
                f"Chain execution failed: {e}",
                mandate_id=mandate_id,
                chain=payment.chain,
            )

        # Phase 4: Ledger Append (queue for reconciliation on failure)
        ledger_tx = None
        try:
            ledger_tx = self._ledger.append(payment, receipt)
            self._audit(mandate_id, ExecutionPhase.LEDGER_APPEND, True,
                       {"ledger_tx_id": ledger_tx.tx_id})
        except Exception as e:
            # Payment succeeded on-chain but ledger failed
            # Queue for reconciliation - DO NOT fail the payment
            self._audit(mandate_id, ExecutionPhase.LEDGER_APPEND, False,
                       {"tx_hash": receipt.tx_hash}, str(e))

            reconciliation_entry = ReconciliationEntry(
                mandate_id=mandate_id,
                chain_tx_hash=receipt.tx_hash,
                chain=receipt.chain,
                audit_anchor=receipt.audit_anchor,
                payment_mandate=payment,
                chain_receipt=receipt,
                error=str(e),
            )
            self._reconciliation_queue.enqueue(reconciliation_entry)

            logger.error(
                f"Ledger append failed but payment succeeded on-chain. "
                f"mandate_id={mandate_id}, tx_hash={receipt.tx_hash}, error={e}"
            )

            # Return result with warning - payment DID succeed
            execution_time = (time.time() - start_time) * 1000
            return PaymentResult(
                mandate_id=mandate_id,
                ledger_tx_id="PENDING_RECONCILIATION",
                chain_tx_hash=receipt.tx_hash,
                chain=receipt.chain,
                audit_anchor=receipt.audit_anchor,
                status="reconciliation_pending",
                compliance_provider=compliance.provider,
                compliance_rule=compliance.rule_id,
                execution_time_ms=execution_time,
            )

        # Success!
        self._audit(mandate_id, ExecutionPhase.COMPLETED, True)
        execution_time = (time.time() - start_time) * 1000

        return PaymentResult(
            mandate_id=mandate_id,
            ledger_tx_id=ledger_tx.tx_id,
            chain_tx_hash=receipt.tx_hash,
            chain=receipt.chain,
            audit_anchor=receipt.audit_anchor,
            compliance_provider=compliance.provider,
            compliance_rule=compliance.rule_id,
            execution_time_ms=execution_time,
        )

    async def reconcile_pending(self, limit: int = 10) -> int:
        """
        Attempt to reconcile pending ledger entries.

        Returns:
            Number of successfully reconciled entries
        """
        pending = self._reconciliation_queue.get_pending(limit)
        reconciled = 0

        for entry in pending:
            try:
                self._ledger.append(entry.payment_mandate, entry.chain_receipt)
                self._reconciliation_queue.mark_resolved(entry.mandate_id)
                reconciled += 1
                logger.info(f"Reconciled ledger entry: mandate_id={entry.mandate_id}")
            except Exception as e:
                self._reconciliation_queue.increment_retry(entry.mandate_id)
                logger.warning(
                    f"Reconciliation retry failed: mandate_id={entry.mandate_id}, "
                    f"retry={entry.retry_count + 1}, error={e}"
                )

        return reconciled

    def get_pending_reconciliation_count(self) -> int:
        """Get count of pending reconciliation entries."""
        return self._reconciliation_queue.count_pending()

    def get_audit_log(self, mandate_id: str | None = None, limit: int = 100) -> List[ExecutionAuditEntry]:
        """Get audit log entries, optionally filtered by mandate_id."""
        if mandate_id:
            return [e for e in self._audit_log if e.mandate_id == mandate_id][-limit:]
        return self._audit_log[-limit:]
