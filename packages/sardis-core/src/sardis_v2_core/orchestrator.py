"""
Payment Orchestrator — the single entry point for all payment execution.

Every payment in Sardis flows through this orchestrator.  It enforces a
strict multi-phase pipeline where **policy checks are the first gate**.
If the policy says no, nothing else runs — no compliance check, no
blockchain transaction, no money moves.

Payment execution pipeline:
───────────────────────────

    Agent calls wallet.pay(to="openai.com", amount=25)
        │
        ▼
    ┌─────────────────────────────────────────────────────┐
    │  Phase 0: KYA VERIFICATION (fail-fast)              │
    │                                                     │
    │  → Check agent's KYA level (NONE/BASIC/VERIFIED/    │
    │    ATTESTED) meets minimum requirements             │
    │  → Verify agent liveness (heartbeat not stale)      │
    │  → Optionally verify code hash attestation          │
    │  → If DENIED → raise KYAViolationError, STOP        │
    ├─────────────────────────────────────────────────────┤
    │  Phase 1: POLICY VALIDATION (fail-fast)             │
    │                                                     │
    │  → Fetch the agent's SpendingPolicy                 │
    │  → Run policy.evaluate() or validate_payment()      │
    │  → Check: amount limits, merchant rules, scopes,    │
    │    time windows, MCC codes, drift score             │
    │  → If DENIED → raise PolicyViolationError, STOP     │
    │  → If "requires_approval" → block (fail-closed)     │
    ├─────────────────────────────────────────────────────┤
    │  Phase 1.5: GROUP POLICY (optional, fail-fast)      │
    │                                                     │
    │  → If agent belongs to a group, check group-level   │
    │    budget and merchant restrictions                  │
    │  → DENY wins (most restrictive policy applies)      │
    ├─────────────────────────────────────────────────────┤
    │  Phase 2: COMPLIANCE CHECK (fail-fast)              │
    │                                                     │
    │  → KYC (Persona), sanctions (Elliptic), AML         │
    │  → If DENIED → raise ComplianceViolationError, STOP │
    ├─────────────────────────────────────────────────────┤
    │  Phase 3: CHAIN EXECUTION                           │
    │                                                     │
    │  → Submit the transaction on-chain (Base, Polygon,  │
    │    Ethereum, etc.)                                  │
    │  → If FAILED → raise ChainExecutionError, STOP      │
    ├─────────────────────────────────────────────────────┤
    │  Phase 3.5: POLICY STATE UPDATE (atomic)            │
    │                                                     │
    │  → Record the spend in the database so future       │
    │    policy checks reflect the new cumulative total   │
    │  → Uses SELECT FOR UPDATE to prevent race conditions│
    ├─────────────────────────────────────────────────────┤
    │  Phase 4: LEDGER APPEND                             │
    │                                                     │
    │  → Write to the append-only audit ledger            │
    │  → If FAILED → queue for reconciliation (payment    │
    │    already succeeded on-chain)                      │
    └─────────────────────────────────────────────────────┘
        │
        ▼
    PaymentResult(tx_hash, ledger_tx_id, chain, status)

Key design decisions:
  - **Policy is Phase 1**: Cheapest check runs first; avoids wasting gas on
    transactions that would be denied.
  - **Fail-closed**: Any error in policy/compliance evaluation = denial.
    We never accidentally approve a payment.
  - **Spend recording is mandatory**: If the DB update fails after a successful
    on-chain payment, it's queued for reconciliation so limits stay accurate.

IMPORTANT: Never bypass this orchestrator to execute payments directly.
"""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from sardis_v2_core.mandates import MandateChain, PaymentMandate

logger = logging.getLogger(__name__)


# ============ Execution Phases ============


class ExecutionPhase(str, Enum):
    """Phases of payment execution for audit/debugging."""
    KYA_VERIFICATION = "kya_verification"      # Phase 0: Know Your Agent
    POLICY_VALIDATION = "policy_validation"     # Phase 1
    COMPLIANCE_CHECK = "compliance_check"       # Phase 2
    CHAIN_EXECUTION = "chain_execution"         # Phase 3
    POLICY_STATE_UPDATE = "policy_state_update" # Phase 3.5
    LEDGER_APPEND = "ledger_append"             # Phase 4
    COMPLETED = "completed"
    FAILED = "failed"


# ============ Result Types ============


# ============ Fastpath Constants ============

# Minimum trust score to qualify for fastpath
FASTPATH_MIN_TRUST_SCORE = 0.9
# Maximum amount (in minor units, e.g. cents) for fastpath eligibility
FASTPATH_MAX_AMOUNT_MINOR = 50_000_00  # $50,000
# Required KYA level for fastpath
FASTPATH_REQUIRED_KYA_LEVEL = "attested"


@dataclass(slots=True)
class FastPathResult:
    """Result of fastpath eligibility check for high-trust agents."""
    eligible: bool
    reason: str | None = None
    trust_score: float | None = None
    kya_level: str | None = None
    skipped_checks: list[str] = field(default_factory=list)


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
    fastpath: FastPathResult | None = None


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


class KYAViolationError(PaymentExecutionError):
    """Raised when agent fails KYA (Know Your Agent) verification."""

    def __init__(
        self,
        message: str,
        mandate_id: str | None = None,
        kya_level: str | None = None,
        reason: str | None = None,
    ):
        super().__init__(
            message,
            phase=ExecutionPhase.KYA_VERIFICATION,
            mandate_id=mandate_id,
            details={"kya_level": kya_level, "reason": reason},
        )
        self.kya_level = kya_level
        self.reason = reason


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


class GroupPolicyPort(Protocol):
    """Interface for group-level policy evaluation."""

    async def evaluate(
        self,
        agent_id: str,
        amount: Any,
        fee: Any,
        merchant_id: Optional[str] = None,
        merchant_category: Optional[str] = None,
    ) -> Any: ...

    async def record_spend(self, agent_id: str, amount: Any) -> None: ...


class KYAVerificationPort(Protocol):
    """Interface for KYA (Know Your Agent) verification."""

    async def check_agent(self, agent_id: str, amount: Any = None, merchant_id: str | None = None) -> Any:
        """Check agent KYA status. Returns a KYAResult-like object with .allowed and .reason."""
        ...


class SanctionsScreeningPort(Protocol):
    """Interface for sanctions-only screening (used in fastpath)."""

    async def screen_address(self, address: str, chain: str | None = None) -> Any:
        """Screen an address against sanctions lists. Returns object with .should_block and .reason."""
        ...


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
        import os
        if os.getenv("SARDIS_ENV", "development") == "production":
            logger.critical(
                "InMemoryReconciliationQueue is NOT suitable for production! "
                "Pending reconciliation entries WILL BE LOST on restart. "
                "Set reconciliation_queue= to a persistent implementation."
            )
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
    The ONLY authorized entry point for payment execution.

    Call ``execute_chain(mandate_chain)`` to run a payment.  The orchestrator
    ensures that **every payment passes through policy checks first**, then
    compliance, then chain execution, then ledger recording.

    How policies are enforced here:
      1. The orchestrator calls ``wallet_manager.async_validate_policies(mandate)``
         which fetches the agent's SpendingPolicy and runs all checks.
      2. If the policy returns ``allowed=False``, a ``PolicyViolationError`` is
         raised and the payment is rejected immediately — nothing else runs.
      3. If the policy returns ``requires_approval``, the orchestrator treats
         it as a denial (fail-closed) and the caller should route to human review.
      4. After a successful on-chain payment, ``async_record_spend()`` updates
         the agent's cumulative totals so future policy checks are accurate.

    All phases are audited — you can call ``get_audit_log(mandate_id)`` to see
    exactly which checks passed/failed and why.
    """

    def __init__(
        self,
        *,
        wallet_manager: WalletPolicyEngine,
        compliance: CompliancePort,
        chain_executor: ChainExecutorPort,
        ledger: LedgerPort,
        reconciliation_queue: ReconciliationQueuePort | None = None,
        group_policy: GroupPolicyPort | None = None,
        kya_service: KYAVerificationPort | None = None,
        sanctions_service: SanctionsScreeningPort | None = None,
    ) -> None:
        self._wallet_manager = wallet_manager
        self._compliance = compliance
        self._chain_executor = chain_executor
        self._ledger = ledger
        self._reconciliation_queue = reconciliation_queue or InMemoryReconciliationQueue()
        self._group_policy = group_policy
        self._kya_service = kya_service
        self._sanctions_service = sanctions_service
        self._audit_log: deque[ExecutionAuditEntry] = deque(maxlen=10_000)
        self._executed_mandates: dict[str, PaymentResult] = {}

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

        if mandate_id in self._executed_mandates:
            logger.warning(f"Duplicate execution blocked: mandate_id={mandate_id}")
            return self._executed_mandates[mandate_id]

        logger.info(f"Starting payment execution: mandate_id={mandate_id}")

        # ── Phase 0: KYA Verification (fail-fast) ───────────────────────
        # Before anything else, verify the agent's identity and trust level.
        # KYA checks: agent is active, not suspended/revoked, meets minimum
        # KYA level, liveness heartbeat is fresh, code hash matches attestation.
        # Fail-closed: any error in KYA verification = denial.
        kya_result = None  # Set by Phase 0, used by fastpath determination
        if self._kya_service is not None:
            try:
                agent_id = getattr(payment, 'agent_id', None) or getattr(payment, 'from_agent', None)
                if agent_id:
                    from decimal import Decimal as _Dec
                    pay_amount = getattr(payment, 'amount', None) or getattr(payment, 'amount_minor', 0)
                    merchant_id = getattr(payment, 'merchant_id', None)

                    kya_result = await self._kya_service.check_agent(
                        agent_id=agent_id,
                        amount=_Dec(str(pay_amount)),
                        merchant_id=merchant_id,
                    )
                    if not kya_result.allowed:
                        self._audit(mandate_id, ExecutionPhase.KYA_VERIFICATION, False,
                                   {"agent_id": agent_id,
                                    "kya_level": getattr(kya_result, 'level', None),
                                    "kya_status": getattr(kya_result, 'status', None)},
                                   kya_result.reason)
                        raise KYAViolationError(
                            kya_result.reason or "kya_denied",
                            mandate_id=mandate_id,
                            kya_level=getattr(kya_result, 'level', None),
                            reason=kya_result.reason,
                        )
                    self._audit(mandate_id, ExecutionPhase.KYA_VERIFICATION, True,
                               {"agent_id": agent_id,
                                "kya_level": getattr(kya_result, 'level', None),
                                "trust_score": getattr(kya_result, 'trust_score', None)})
            except KYAViolationError:
                raise
            except Exception as e:
                # Fail-closed: KYA errors = deny
                self._audit(mandate_id, ExecutionPhase.KYA_VERIFICATION, False, error=f"kya_error: {e}")
                raise KYAViolationError(f"KYA verification error: {e}", mandate_id=mandate_id)

        # ── Fastpath Determination ───────────────────────────────────────
        # High-trust agents (ATTESTED + trust_score >= 0.9) on small amounts
        # can skip KYC and basic rule checks.  Sanctions screening is NEVER
        # skipped — it runs regardless of trust level.
        fastpath = FastPathResult(eligible=False, reason="kya_service_not_configured")
        if self._kya_service is not None and kya_result is not None:
            agent_id = getattr(payment, 'agent_id', None) or getattr(payment, 'from_agent', None)
            kya_level = getattr(kya_result, 'level', None)
            trust_score = getattr(kya_result, 'trust_score', None)
            amount_minor = getattr(payment, 'amount_minor', 0)

            if (
                kya_level == FASTPATH_REQUIRED_KYA_LEVEL
                and trust_score is not None
                and trust_score >= FASTPATH_MIN_TRUST_SCORE
                and amount_minor <= FASTPATH_MAX_AMOUNT_MINOR
            ):
                fastpath = FastPathResult(
                    eligible=True,
                    reason="high_trust_agent",
                    trust_score=trust_score,
                    kya_level=kya_level,
                    skipped_checks=["kyc_verification", "basic_rules"],
                )
                logger.info(
                    f"Fastpath ELIGIBLE: mandate={mandate_id}, agent={agent_id}, "
                    f"trust={trust_score:.2f}, kya={kya_level}, amount={amount_minor}"
                )
            else:
                reasons = []
                if kya_level != FASTPATH_REQUIRED_KYA_LEVEL:
                    reasons.append(f"kya_level={kya_level} (need {FASTPATH_REQUIRED_KYA_LEVEL})")
                if trust_score is None or trust_score < FASTPATH_MIN_TRUST_SCORE:
                    reasons.append(f"trust_score={trust_score} (need >={FASTPATH_MIN_TRUST_SCORE})")
                if amount_minor > FASTPATH_MAX_AMOUNT_MINOR:
                    reasons.append(f"amount={amount_minor} (max {FASTPATH_MAX_AMOUNT_MINOR})")
                fastpath = FastPathResult(
                    eligible=False,
                    reason="; ".join(reasons),
                    trust_score=trust_score,
                    kya_level=kya_level,
                )

        # ── Phase 1: Policy Validation (fail-fast) ──────────────────────
        # This is where spending policies are enforced.  The wallet manager
        # fetches the agent's SpendingPolicy and runs all checks (amount
        # limits, merchant rules, time windows, etc.).  If denied, we raise
        # immediately — no compliance check, no chain execution, no money moves.
        try:
            if hasattr(self._wallet_manager, "async_validate_policies"):
                policy = await getattr(self._wallet_manager, "async_validate_policies")(payment)
            else:
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

        # ── Phase 1.5: Group Policy Check (optional, fail-fast) ────────
        # If the agent belongs to a group, the group's budget and merchant
        # restrictions are checked on top of the individual policy.
        # DENY wins — the most restrictive rule across individual + group applies.
        if self._group_policy is not None:
            try:
                agent_id = getattr(payment, 'agent_id', None) or getattr(payment, 'from_agent', None)
                if agent_id:
                    from decimal import Decimal as _Decimal
                    pay_amount = getattr(payment, 'amount', None) or getattr(payment, 'amount_minor', 0)
                    pay_fee = getattr(payment, 'fee', None) or _Decimal("0")
                    merchant_id = getattr(payment, 'merchant_id', None)
                    merchant_category = getattr(payment, 'merchant_category', None)

                    group_result = await self._group_policy.evaluate(
                        agent_id=agent_id,
                        amount=_Decimal(str(pay_amount)),
                        fee=_Decimal(str(pay_fee)),
                        merchant_id=merchant_id,
                        merchant_category=merchant_category,
                    )
                    if not group_result.allowed:
                        self._audit(mandate_id, ExecutionPhase.POLICY_VALIDATION, False,
                                   {"group_id": getattr(group_result, 'group_id', None),
                                    "group_reason": group_result.reason},
                                   f"group_policy_denied: {group_result.reason}")
                        raise PolicyViolationError(
                            f"Group policy denied: {group_result.reason}",
                            mandate_id=mandate_id,
                            rule_id=f"group:{getattr(group_result, 'group_id', 'unknown')}",
                        )
                    self._audit(mandate_id, ExecutionPhase.POLICY_VALIDATION, True,
                               {"group_policy": "passed"})
            except PolicyViolationError:
                raise
            except Exception as e:
                # Fail-closed: group policy errors = deny
                self._audit(mandate_id, ExecutionPhase.POLICY_VALIDATION, False, error=f"group_policy_error: {e}")
                raise PolicyViolationError(f"Group policy error: {e}", mandate_id=mandate_id)

        # Phase 2: Compliance Check (fail-fast)
        # If fastpath eligible, skip full compliance and run sanctions only.
        # Sanctions screening is NEVER skipped regardless of trust level.
        compliance = None
        if fastpath.eligible and self._sanctions_service is not None:
            # ── Fastpath: sanctions-only screening ──────────────────────
            logger.info(f"Fastpath active for mandate={mandate_id}, running sanctions-only")
            try:
                screening = await self._sanctions_service.screen_address(
                    payment.destination, chain=payment.chain,
                )
                if screening.should_block:
                    self._audit(mandate_id, ExecutionPhase.COMPLIANCE_CHECK, False,
                               {"provider": "sanctions", "fastpath": True,
                                "reason": screening.reason},
                               f"sanctions_hit: {screening.reason or 'blocked_address'}")
                    raise ComplianceViolationError(
                        f"sanctions_hit: {screening.reason or 'blocked_address'}",
                        mandate_id=mandate_id,
                        provider=getattr(screening, 'provider', 'sanctions'),
                        rule_id="sanctions_screening",
                    )
                self._audit(mandate_id, ExecutionPhase.COMPLIANCE_CHECK, True,
                           {"provider": "sanctions", "fastpath": True,
                            "skipped": fastpath.skipped_checks})
            except ComplianceViolationError:
                raise
            except Exception as e:
                # Fail-closed: sanctions errors = deny even on fastpath
                self._audit(mandate_id, ExecutionPhase.COMPLIANCE_CHECK, False,
                           error=f"sanctions_fastpath_error: {e}")
                raise ComplianceViolationError(
                    f"Sanctions screening error: {e}", mandate_id=mandate_id)
        else:
            # ── Standard: full compliance check ─────────────────────────
            if fastpath.eligible and self._sanctions_service is None:
                logger.warning(
                    f"Fastpath eligible but no sanctions_service configured for "
                    f"mandate={mandate_id}; falling back to full compliance"
                )
                fastpath = FastPathResult(
                    eligible=False,
                    reason="no_sanctions_service_for_fastpath",
                    trust_score=fastpath.trust_score,
                    kya_level=fastpath.kya_level,
                )
            try:
                compliance = await self._compliance.preflight(payment)
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

        # ── Phase 3.5: Update Policy Spend State (mandatory) ────────────
        # After a successful on-chain payment, we MUST record the spend so
        # the agent's cumulative totals are accurate for future policy checks.
        # Uses SELECT FOR UPDATE in the DB to prevent race conditions.
        # If this fails, the spend is queued for reconciliation — otherwise
        # the agent could exceed its limits by making rapid payments.
        try:
            if hasattr(self._wallet_manager, "async_record_spend"):
                await getattr(self._wallet_manager, "async_record_spend")(payment)
                self._audit(
                    mandate_id,
                    ExecutionPhase.POLICY_STATE_UPDATE,
                    True,
                    {"token": payment.token, "amount_minor": payment.amount_minor},
                )
        except Exception as e:
            self._audit(mandate_id, ExecutionPhase.POLICY_STATE_UPDATE, False, error=str(e))
            logger.error("Policy spend-state update failed for mandate=%s: %s", mandate_id, e)
            # SECURITY: Queue unrecorded spend for reconciliation so limits stay accurate.
            # Without this, successful on-chain payments would not decrement the agent's
            # spending allowance, allowing repeated limit overruns.
            spend_recon = ReconciliationEntry(
                mandate_id=mandate_id,
                chain_tx_hash=receipt.tx_hash,
                chain=receipt.chain,
                audit_anchor=receipt.audit_anchor,
                payment_mandate=payment,
                chain_receipt=receipt,
                error=f"spend_state_update_failed: {e}",
            )
            self._reconciliation_queue.append(spend_recon)
            logger.warning(
                "Queued spend-state reconciliation for mandate=%s tx=%s",
                mandate_id, receipt.tx_hash,
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
            result = PaymentResult(
                mandate_id=mandate_id,
                ledger_tx_id="PENDING_RECONCILIATION",
                chain_tx_hash=receipt.tx_hash,
                chain=receipt.chain,
                audit_anchor=receipt.audit_anchor,
                status="reconciliation_pending",
                compliance_provider=compliance.provider if compliance else ("sanctions_fastpath" if fastpath.eligible else None),
                compliance_rule=compliance.rule_id if compliance else ("fastpath_sanctions_only" if fastpath.eligible else None),
                execution_time_ms=execution_time,
                fastpath=fastpath if fastpath.eligible else None,
            )
            self._executed_mandates[mandate_id] = result
            return result

        # Success!
        self._audit(mandate_id, ExecutionPhase.COMPLETED, True)
        execution_time = (time.time() - start_time) * 1000

        result = PaymentResult(
            mandate_id=mandate_id,
            ledger_tx_id=ledger_tx.tx_id,
            chain_tx_hash=receipt.tx_hash,
            chain=receipt.chain,
            audit_anchor=receipt.audit_anchor,
            compliance_provider=compliance.provider if compliance else ("sanctions_fastpath" if fastpath.eligible else None),
            compliance_rule=compliance.rule_id if compliance else ("fastpath_sanctions_only" if fastpath.eligible else None),
            execution_time_ms=execution_time,
            fastpath=fastpath if fastpath.eligible else None,
        )
        self._executed_mandates[mandate_id] = result
        return result

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
        return list(self._audit_log)[-limit:]
