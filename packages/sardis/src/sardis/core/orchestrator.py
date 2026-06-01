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
    │  Phase 0.5: MANDATE VALIDATION (optional)           │
    │                                                     │
    │  → Look up active spending mandate for agent/wallet │
    │  → Validate: status, merchant scope, amount limits, │
    │    rail permissions                                 │
    │  → If approval_threshold exceeded → route to human  │
    │  → Record mandate_id on payment result              │
    │  → If no mandate → pass through (backward compat.)  │
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

import inspect
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Protocol

from sardis.core.dedup_store import DedupStorePort, InMemoryDedupStore
from sardis.core.mandates import MandateChain, PaymentMandate
from sardis.core.settlement_lock import SettlementLock, SettlementLockError
from sardis.core.state_handlers import StateHandlerRegistry, register_default_handlers
from sardis.core.state_machine import PaymentState, PaymentStateMachine

logger = logging.getLogger(__name__)

# Module-level handler registry: initialized once, shared by all orchestrator
# instances so that custom handlers registered at app startup apply globally.
_handler_registry = StateHandlerRegistry()
register_default_handlers(_handler_registry)


def _resolve_token_amount(payment: Any) -> Decimal:
    """Resolve a payment's amount in TOKEN (major) units as a ``Decimal``.

    Money correctness: typed :class:`PaymentMandate` objects (factory / a2a /
    ap2 / pay paths) carry money ONLY as integer ``amount_minor``.  Spending
    mandates and policies express their limits in token/major units (e.g. a
    ``$100`` per-tx cap).  Comparing raw ``amount_minor`` (e.g. 50_000_000 for
    50 USDC) against a token-unit limit produces false denials.

    Resolution order:
      1. A major-unit ``amount`` attribute, when present and non-None — already
         in token units (legacy duck-typed payments).
      2. Otherwise ``amount_minor`` converted to token units using the payment
         token's decimals (via the token registry, falling back to 6 decimals
         for unknown symbols — the stablecoins Sardis supports all use 6).
    """
    major = getattr(payment, "amount", None)
    if major is not None:
        return Decimal(str(major))

    amount_minor = int(getattr(payment, "amount_minor", 0) or 0)
    token = getattr(payment, "token", None)
    decimals = 6  # default for the stablecoins Sardis supports
    if token is not None:
        try:
            from sardis.core.tokens import TokenType, get_token_metadata

            decimals = get_token_metadata(TokenType(str(token))).decimals
        except (ValueError, KeyError):
            decimals = 6
    return Decimal(amount_minor) / (Decimal(10) ** decimals)


# ============ Execution Phases ============


class ExecutionPhase(str, Enum):
    """Phases of payment execution for audit/debugging."""
    KYA_VERIFICATION = "kya_verification"      # Phase 0: Know Your Agent
    MANDATE_VALIDATION = "mandate_validation"   # Phase 0.5: Spending Mandate
    POLICY_VALIDATION = "policy_validation"     # Phase 1
    RISK_ASSESSMENT = "risk_assessment"         # Phase 1.6: Guard / RiskEngine
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
    spending_mandate_id: str = ""
    #: Set when execution is paused awaiting human approval.  When non-empty,
    #: ``status == "pending_approval"`` and NO money has moved — the caller must
    #: wait for the approval decision and then re-execute via
    #: ``execute_on_approval(approval_id)``.
    approval_id: str = ""
    #: Set when the payment carried a policy-defined recourse window and a
    #: durable, signed RecourseHold was opened after settlement.  When non-empty,
    #: the money is settled but a time-boxed recourse/dispute window is open;
    #: ``status`` is still the normal success status (money DID move).
    recourse_hold_id: str = ""
    #: The resolved attenuated delegation chain when the payment was made by a
    #: DELEGATEE rather than the root mandate holder — root mandate first, then
    #: every delegation hop, leaf last.  Empty for a direct (non-delegated)
    #: payment.  Each link was re-checked fail-closed at execution time (Phase
    #: 0.5).  Recorded here so it can be bound into the portable
    #: Proof-of-Authority emitted on every authorized execution.
    delegation_chain: list[Any] = field(default_factory=list)
    #: Portable, offline-verifiable Proof-of-Authority emitted on every ALLOWED
    #: execution alongside the ExecutionReceipt.  Self-contained: an
    #: ``AuthorityProof`` (sardis.core.authority_proof) signed with Ed25519 that
    #: a merchant / auditor / regulator can verify with the PUBLISHED public key
    #: — no DB, no live Sardis.  Binds {action id, agent, amount, counterparty,
    #: policy_hash, mandate_hash, delegation_chain, decision=ALLOWED, issued_at,
    #: evaluated inputs}.  None only on the legacy paths where no money moved.
    authority_proof: Any | None = None


@dataclass
class ExecutionAuditEntry:
    """Audit entry tracking each phase of execution."""
    mandate_id: str
    phase: ExecutionPhase
    success: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = field(default_factory=dict)
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
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    retry_count: int = 0
    last_retry: datetime | None = None
    resolved: bool = False


# ============ Exceptions ============


class PaymentExecutionError(Exception):
    """Base exception for payment execution failures."""

    def __init__(
        self,
        message: str,
        phase: ExecutionPhase,
        mandate_id: str | None = None,
        details: dict[str, Any] | None = None,
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


class RiskViolationError(PaymentExecutionError):
    """Raised when the Guard / RiskEngine BLOCKs a payment (fail-closed).

    A blocking risk decision is a hard deny: no money moves.  The full risk
    decision evidence (combined / internal / external scores, feeds, reasons)
    is attached for audit.
    """

    def __init__(
        self,
        message: str,
        mandate_id: str | None = None,
        *,
        score: float | None = None,
        evidence: dict | None = None,
    ):
        super().__init__(
            message,
            phase=ExecutionPhase.RISK_ASSESSMENT,
            mandate_id=mandate_id,
            details={"score": score, "evidence": evidence},
        )
        self.score = score
        self.evidence = evidence or {}


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


class MandateViolationError(PaymentExecutionError):
    """Raised when payment violates a spending mandate."""

    def __init__(
        self,
        message: str,
        mandate_id: str | None = None,
        error_code: str | None = None,
        requires_approval: bool = False,
    ):
        super().__init__(
            message,
            phase=ExecutionPhase.MANDATE_VALIDATION,
            mandate_id=mandate_id,
            details={"error_code": error_code, "requires_approval": requires_approval},
        )
        self.error_code = error_code
        self.requires_approval = requires_approval


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
    def validate_policies(self, mandate: PaymentMandate) -> PolicyEvaluation: ...


class CompliancePort(Protocol):
    def preflight(self, mandate: PaymentMandate) -> ComplianceResult: ...


class ChainExecutorPort(Protocol):
    async def dispatch_payment(self, mandate: PaymentMandate) -> ChainReceipt: ...


class LedgerPort(Protocol):
    def append(self, payment_mandate: PaymentMandate, chain_receipt: ChainReceipt) -> Transaction: ...


class GroupPolicyPort(Protocol):
    """Interface for group-level policy evaluation."""

    async def evaluate(
        self,
        agent_id: str,
        amount: Any,
        fee: Any,
        merchant_id: str | None = None,
        merchant_category: str | None = None,
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


class SpendingMandateLookupPort(Protocol):
    """Interface for looking up active spending mandates.

    Used by the MANDATE_VALIDATION phase to find the spending mandate
    governing a particular agent or wallet.
    """

    async def get_active_mandate(
        self,
        agent_id: str | None = None,
        wallet_id: str | None = None,
        payment: Any | None = None,
    ) -> Any | None:
        """Return the active SpendingMandate for the agent/wallet, or None.

        ``payment`` is the optional in-flight payment context (amount, merchant,
        rail, …).  Plain root-mandate lookups ignore it; a delegation-aware
        lookup needs it to re-check the WHOLE attenuated delegation chain at
        EXECUTION time (every link non-revoked + within cap/scope + non-expired,
        else the lookup returns ``None`` and the orchestrator denies fail-closed).
        """
        ...

    async def record_spend(self, mandate_id: str, amount: Any) -> None:
        """Persist ``amount`` (token units) against the mandate's spent_total.

        Called after a successful settlement so lifetime/window caps reflect
        the new spend.  In-memory implementations may no-op.  A delegation-aware
        lookup ALSO decrements the acting delegatee AND every ancestor delegation
        in the resolved chain (a child spend consumes parent budget).
        """
        ...


class ReconciliationQueuePort(Protocol):
    """Interface for reconciliation queue storage."""

    def enqueue(self, entry: ReconciliationEntry) -> str: ...
    def get_pending(self, limit: int = 100) -> list[ReconciliationEntry]: ...
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
        env = os.getenv("SARDIS_ENVIRONMENT", os.getenv("SARDIS_ENV", "development")).strip().lower()
        if env in ("production", "prod", "staging"):
            raise RuntimeError(
                "InMemoryReconciliationQueue is NOT suitable for production. "
                "Pending reconciliation entries WILL BE LOST on restart. "
                "Set reconciliation_queue= to a persistent implementation."
            )
        logger.warning(
            "Using InMemoryReconciliationQueue — data will be lost on restart. "
            "Not suitable for production."
        )
        self._queue: dict[str, ReconciliationEntry] = {}

    def enqueue(self, entry: ReconciliationEntry) -> str:
        """Add entry to reconciliation queue."""
        self._queue[entry.mandate_id] = entry
        logger.warning(
            f"Ledger append queued for reconciliation: mandate_id={entry.mandate_id}, "
            f"tx_hash={entry.chain_tx_hash}, error={entry.error}"
        )
        return entry.mandate_id

    def get_pending(self, limit: int = 100) -> list[ReconciliationEntry]:
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
            entry.last_retry = datetime.now(UTC)
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
        dedup_store: DedupStorePort | None = None,
        spending_mandate_lookup: SpendingMandateLookupPort | None = None,
        settlement_lock: SettlementLock | None = None,
        approval_gate: Any | None = None,
        recourse_engine: Any | None = None,
        recourse_window_resolver: Any | None = None,
        risk_engine: Any | None = None,
        authority_proof_secret: bytes | str | None = None,
    ) -> None:
        self._wallet_manager = wallet_manager
        self._compliance = compliance
        self._chain_executor = chain_executor
        self._ledger = ledger
        self._reconciliation_queue = reconciliation_queue or InMemoryReconciliationQueue()
        self._group_policy = group_policy
        self._kya_service = kya_service
        self._sanctions_service = sanctions_service
        self._dedup_store: DedupStorePort = dedup_store or InMemoryDedupStore()
        self._spending_mandate_lookup = spending_mandate_lookup
        self._settlement_lock = settlement_lock
        # ApprovalGate collaborator (sardis.core.approval_gate.ApprovalGate).
        # When configured, ``requires_approval`` no longer fails closed with a
        # raise — it creates a durable, signed ApprovalRequest, relays it to a
        # human, and returns a pending PaymentResult (no money moves).  When
        # absent, the legacy fail-closed raise is preserved (back-compat).
        self._approval_gate = approval_gate
        # RecourseEngine collaborator (sardis.core.recourse_engine.RecourseEngine).
        # OPTIONAL + additive: when a payment carries a policy-defined recourse
        # window, after a successful settlement the orchestrator opens a durable,
        # signed RecourseHold (programmable recourse) instead of immediate
        # finality.  No window configured -> unchanged behavior (immediate
        # finality).  ``recourse_window_resolver`` is a callable
        # ``(payment, spending_mandate) -> int | None`` returning the window in
        # seconds (or None for immediate finality); fail-closed: if resolving or
        # opening the hold raises, the payment result is unaffected (money has
        # already moved) but the failure is audited and the hold is not claimed.
        self._recourse_engine = recourse_engine
        self._recourse_window_resolver = recourse_window_resolver
        # RiskEngine collaborator (sardis.guardrails.risk_engine.RiskEngine).
        # OPTIONAL + additive: when configured, the orchestrator runs the Guard
        # fraud/risk assessment as Phase 1.6 (after policy, before compliance)
        # and acts on the binding GuardAction: BLOCK -> deny (fail-closed,
        # audited); REQUIRE_APPROVAL -> open an ApprovalRequest via the
        # ApprovalGate (high-risk becomes a step-up approval; no money moves);
        # FLAG -> allow + record the signal; ALLOW -> proceed.  When absent, the
        # path is unchanged (back-compat) — the a2a route still runs the legacy
        # anomaly guardrail.  This NEVER fails open on a money path.
        self._risk_engine = risk_engine
        # Optional override for the Ed25519 signing key used to mint the portable
        # Proof-of-Authority (sardis.core.authority_proof).  None -> resolved from
        # SARDIS_AUTHORITY_PROOF_PRIVATE_KEY (fail-closed in prod/staging) at sign
        # time.  Tests inject a deterministic 32-byte seed.
        self._authority_proof_secret = authority_proof_secret
        self._audit_log: deque[ExecutionAuditEntry] = deque(maxlen=10_000)

        # Warn when using in-memory audit log in production
        import os as _os
        _env = _os.getenv("SARDIS_ENVIRONMENT", _os.getenv("SARDIS_ENV", "dev")).strip().lower()
        if _env in ("production", "prod", "staging"):
            logger.warning(
                "PaymentOrchestrator audit_log is an in-memory deque (maxlen=10000). "
                "Audit entries will be lost on restart and are limited to 10K entries. "
                "Wire a persistent audit store for production durability."
            )

    def _audit(
        self,
        mandate_id: str,
        phase: ExecutionPhase,
        success: bool,
        details: dict[str, Any] | None = None,
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

    async def _enqueue_reconciliation(self, entry: ReconciliationEntry) -> None:
        """Enqueue a reconciliation entry, awaiting async implementations.

        The in-memory queue's ``enqueue`` is synchronous; the Postgres queue's
        is a coroutine.  Calling the Postgres one without awaiting would return
        an un-awaited coroutine and silently DROP the reconciliation row (a
        successful on-chain payment whose spend/ledger state never reconciles).
        Normalize by awaiting whenever ``enqueue`` returns an awaitable.
        """
        result = self._reconciliation_queue.enqueue(entry)
        if inspect.isawaitable(result):
            await result

    async def evaluate_chain(self, chain: MandateChain) -> None:
        """Run the fail-closed authority *gates* for a mandate chain WITHOUT
        dispatching, recording spend, or appending to the ledger.

        This is the gating-only sibling of :meth:`execute_chain`.  It runs the
        same collaborators in the same fail-closed order:

            Phase 0    KYA verification
            Phase 0.5  spending-mandate lookup + scope/limits (revocation is
                       enforced here — a revoked/absent mandate yields a deny)
            Phase 1    spending-policy validation
            Phase 1.5  group policy
            Phase 1.6  Guard / RiskEngine
            Phase 2    compliance / sanctions

        It is intended for money paths where Sardis is NOT the party that moves
        the funds — e.g. the ACP merchant path, where the buyer's agent has
        ALREADY broadcast an on-chain transfer (crypto) or an external PSP /
        issuer captures the card.  Calling :meth:`execute_chain` there would
        dispatch a SECOND payment (double-spend); this method applies the
        Sardis moat (mandate / policy / Guard / revocation / KYA / compliance)
        without touching the chain.

        Approval-escalation outcomes (mandate / policy / Guard ``require_approval``)
        are treated as denials here (raised), because there is no money path to
        suspend pending a human decision — the order must NOT proceed unless the
        gates pass outright.  Proof of settlement is verified separately by the
        caller (e.g. on-chain receipt verification for crypto).

        Raises
        ------
        KYAViolationError, MandateViolationError, PolicyViolationError,
        ComplianceViolationError, RiskViolationError
            On any deny / fail-closed outcome.  No money moves and nothing is
            recorded.
        """
        payment = chain.payment
        mandate_id = payment.mandate_id
        agent_id = getattr(payment, "agent_id", None) or getattr(payment, "from_agent", None)

        # ── Phase 0: KYA Verification (fail-closed) ─────────────────────────
        if self._kya_service is not None and agent_id:
            try:
                from decimal import Decimal as _Dec
                pay_amount = getattr(payment, "amount", None) or getattr(payment, "amount_minor", 0)
                merchant_id = getattr(payment, "merchant_id", None)
                kya_result = await self._kya_service.check_agent(
                    agent_id=agent_id,
                    amount=_Dec(str(pay_amount)),
                    merchant_id=merchant_id,
                )
                if not kya_result.allowed:
                    self._audit(mandate_id, ExecutionPhase.KYA_VERIFICATION, False,
                               {"agent_id": agent_id, "gate_only": True},
                               kya_result.reason)
                    raise KYAViolationError(
                        kya_result.reason or "kya_denied",
                        mandate_id=mandate_id,
                        kya_level=getattr(kya_result, "level", None),
                        reason=kya_result.reason,
                    )
                self._audit(mandate_id, ExecutionPhase.KYA_VERIFICATION, True,
                           {"agent_id": agent_id, "gate_only": True})
            except KYAViolationError:
                raise
            except Exception as e:
                self._audit(mandate_id, ExecutionPhase.KYA_VERIFICATION, False,
                           {"gate_only": True}, error=f"kya_error: {e}")
                raise KYAViolationError(f"KYA verification error: {e}", mandate_id=mandate_id)

        # ── Phase 0.5: Spending Mandate Validation (fail-closed) ────────────
        if self._spending_mandate_lookup is not None:
            wallet_id = getattr(payment, "wallet_id", None) or getattr(payment, "subject", None)
            try:
                try:
                    spending_mandate = await self._spending_mandate_lookup.get_active_mandate(
                        agent_id=agent_id, wallet_id=wallet_id, payment=payment,
                    )
                except TypeError:
                    spending_mandate = await self._spending_mandate_lookup.get_active_mandate(
                        agent_id=agent_id, wallet_id=wallet_id,
                    )
            except MandateViolationError:
                raise
            except Exception as e:
                self._audit(mandate_id, ExecutionPhase.MANDATE_VALIDATION, False,
                           {"agent_id": agent_id, "wallet_id": wallet_id, "gate_only": True},
                           error=f"mandate_lookup_error: {e}")
                raise PolicyViolationError(
                    f"Spending mandate lookup error (fail-closed): {e}",
                    mandate_id=mandate_id, rule_id="spending_mandate_lookup_error",
                )

            if spending_mandate is None:
                # Revoked / suspended / expired / exhausted / never issued — DENY.
                self._audit(mandate_id, ExecutionPhase.MANDATE_VALIDATION, False,
                           {"agent_id": agent_id, "wallet_id": wallet_id,
                            "reason": "no_active_spending_mandate", "gate_only": True},
                           "No active spending mandate authorizes this payment")
                raise PolicyViolationError(
                    "No active spending mandate authorizes this payment "
                    "(revoked, suspended, expired, or never issued)",
                    mandate_id=mandate_id, rule_id="no_active_spending_mandate",
                )

            pay_amount = _resolve_token_amount(payment)
            merchant_id = getattr(payment, "merchant_id", None) or getattr(payment, "destination", None)
            check = spending_mandate.check_payment(
                amount=pay_amount,
                merchant=merchant_id,
                rail=getattr(payment, "rail", None),
                chain=getattr(payment, "chain", None),
                token=getattr(payment, "token", None),
            )
            if not check.approved:
                self._audit(mandate_id, ExecutionPhase.MANDATE_VALIDATION, False,
                           {"spending_mandate_id": spending_mandate.id,
                            "error_code": check.error_code, "gate_only": True},
                           check.reason)
                raise MandateViolationError(
                    check.reason, mandate_id=mandate_id, error_code=check.error_code,
                )
            if check.requires_approval:
                # No money path to suspend in a gate-only evaluation — deny.
                self._audit(mandate_id, ExecutionPhase.MANDATE_VALIDATION, False,
                           {"spending_mandate_id": spending_mandate.id,
                            "requires_approval": True, "gate_only": True},
                           "Mandate requires human approval (denied in gate-only path)")
                raise MandateViolationError(
                    "Payment requires human approval and cannot be auto-approved "
                    "on this path",
                    mandate_id=mandate_id, error_code="MANDATE_APPROVAL_REQUIRED",
                    requires_approval=True,
                )
            self._audit(mandate_id, ExecutionPhase.MANDATE_VALIDATION, True,
                       {"spending_mandate_id": spending_mandate.id, "gate_only": True})

        # ── Phase 1: Policy Validation (fail-closed) ────────────────────────
        try:
            if hasattr(self._wallet_manager, "async_validate_policies"):
                policy = await self._wallet_manager.async_validate_policies(payment)
            else:
                policy = self._wallet_manager.validate_policies(payment)
            if not policy.allowed:
                self._audit(mandate_id, ExecutionPhase.POLICY_VALIDATION, False,
                           {"rule_id": getattr(policy, "rule_id", None), "gate_only": True},
                           policy.reason)
                raise PolicyViolationError(
                    policy.reason or "policy_denied",
                    mandate_id=mandate_id, rule_id=getattr(policy, "rule_id", None),
                )
            _policy_reason = getattr(policy, "reason", None) or ""
            if "requires_approval" in _policy_reason or getattr(policy, "required_approvals", 0) > 0:
                self._audit(mandate_id, ExecutionPhase.POLICY_VALIDATION, False,
                           {"requires_approval": True, "gate_only": True}, _policy_reason)
                raise PolicyViolationError(
                    "Policy requires human approval for this payment",
                    mandate_id=mandate_id, rule_id="policy_requires_approval",
                )
            self._audit(mandate_id, ExecutionPhase.POLICY_VALIDATION, True,
                       {"rule_id": getattr(policy, "rule_id", None), "gate_only": True})
        except PolicyViolationError:
            raise
        except Exception as e:
            self._audit(mandate_id, ExecutionPhase.POLICY_VALIDATION, False,
                       {"gate_only": True}, error=str(e))
            raise PolicyViolationError(f"Policy validation error: {e}", mandate_id=mandate_id)

        # ── Phase 1.5: Group Policy (fail-closed) ───────────────────────────
        if self._group_policy is not None and agent_id:
            try:
                from decimal import Decimal as _Decimal
                pay_amount = getattr(payment, "amount", None) or getattr(payment, "amount_minor", 0)
                group_result = await self._group_policy.evaluate(
                    agent_id=agent_id,
                    amount=_Decimal(str(pay_amount)),
                    fee=_Decimal(str(getattr(payment, "fee", None) or "0")),
                    merchant_id=getattr(payment, "merchant_id", None),
                    merchant_category=getattr(payment, "merchant_category", None),
                )
                if not group_result.allowed:
                    self._audit(mandate_id, ExecutionPhase.POLICY_VALIDATION, False,
                               {"group_reason": group_result.reason, "gate_only": True},
                               f"group_policy_denied: {group_result.reason}")
                    raise PolicyViolationError(
                        f"Group policy denied: {group_result.reason}",
                        mandate_id=mandate_id,
                        rule_id=f"group:{getattr(group_result, 'group_id', 'unknown')}",
                    )
            except PolicyViolationError:
                raise
            except Exception as e:
                self._audit(mandate_id, ExecutionPhase.POLICY_VALIDATION, False,
                           {"gate_only": True}, error=f"group_policy_error: {e}")
                raise PolicyViolationError(f"Group policy error: {e}", mandate_id=mandate_id)

        # ── Phase 1.6: Guard / Risk Assessment (fail-closed) ────────────────
        if self._risk_engine is not None:
            risk_amount = _resolve_token_amount(payment)
            risk_counterparty = getattr(payment, "merchant_id", None) or getattr(payment, "destination", None)
            try:
                from sardis.guardrails.risk_engine import GuardAction
                meta = getattr(payment, "metadata", None) or {}
                decision = await self._risk_engine.assess(
                    agent_id=str(agent_id or ""),
                    amount=risk_amount,
                    counterparty=risk_counterparty,
                    merchant_category=getattr(payment, "merchant_category", None)
                    or meta.get("merchant_category"),
                    baseline_mean=meta.get("baseline_mean"),
                    baseline_std=meta.get("baseline_std"),
                    recent_tx_count_1h=meta.get("recent_tx_count_1h", 0),
                    is_new_merchant=meta.get("is_new_merchant", False),
                    hour_of_day=meta.get("hour_of_day"),
                    typical_hours=meta.get("typical_hours"),
                    signal_context=meta.get("signal_context"),
                )
            except RiskViolationError:
                raise
            except Exception as e:
                self._audit(mandate_id, ExecutionPhase.RISK_ASSESSMENT, False,
                           {"agent_id": agent_id, "gate_only": True},
                           error=f"risk_engine_error: {e}")
                raise RiskViolationError(f"Risk assessment error: {e}", mandate_id=mandate_id)

            evidence = decision.to_dict()
            # BLOCK and REQUIRE_APPROVAL both deny on the gate-only path (no money
            # path to suspend pending a human decision). FLAG/ALLOW proceed.
            if decision.action in (GuardAction.BLOCK, GuardAction.REQUIRE_APPROVAL):
                self._audit(mandate_id, ExecutionPhase.RISK_ASSESSMENT, False,
                           {"agent_id": agent_id, "action": decision.action.value,
                            "score": decision.combined_score, "evidence": evidence,
                            "gate_only": True},
                           f"guard_denied: score={decision.combined_score:.1f}")
                raise RiskViolationError(
                    f"Payment denied by Guard risk engine "
                    f"(action={decision.action.value}, score={decision.combined_score:.1f}/100)",
                    mandate_id=mandate_id, score=decision.combined_score, evidence=evidence,
                )
            self._audit(mandate_id, ExecutionPhase.RISK_ASSESSMENT, True,
                       {"agent_id": agent_id, "action": decision.action.value,
                        "score": decision.combined_score, "gate_only": True})

        # ── Phase 2: Compliance / Sanctions (fail-closed) ───────────────────
        try:
            compliance = await self._compliance.preflight(payment)
            if not compliance.allowed:
                self._audit(mandate_id, ExecutionPhase.COMPLIANCE_CHECK, False,
                           {"provider": compliance.provider, "rule_id": compliance.rule_id,
                            "gate_only": True},
                           compliance.reason)
                raise ComplianceViolationError(
                    compliance.reason or "compliance_denied",
                    mandate_id=mandate_id, provider=compliance.provider,
                    rule_id=compliance.rule_id,
                )
            self._audit(mandate_id, ExecutionPhase.COMPLIANCE_CHECK, True,
                       {"provider": compliance.provider, "rule_id": compliance.rule_id,
                        "gate_only": True})
        except ComplianceViolationError:
            raise
        except Exception as e:
            self._audit(mandate_id, ExecutionPhase.COMPLIANCE_CHECK, False,
                       {"gate_only": True}, error=str(e))
            raise ComplianceViolationError(f"Compliance check error: {e}", mandate_id=mandate_id)

    async def execute_chain(
        self,
        chain: MandateChain,
        *,
        _approved_request: Any | None = None,
    ) -> PaymentResult:
        """
        Execute a verified mandate chain.

        This is the ONLY entry point for payment execution.

        Args:
            chain: Verified mandate chain containing intent, cart, and payment mandates
            _approved_request: internal — set by ``execute_on_approval`` when
                re-running an already-approved ApprovalRequest.  Satisfies ONLY
                the approval-escalation gate; policy / mandate / compliance /
                revocation are still fully re-evaluated (never trust a stale
                approval).

        Returns:
            PaymentResult on success (or a ``pending_approval`` result when the
            approval gate is engaged and a human decision is still required)

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

        existing = await self._dedup_store.check(mandate_id)
        if existing is not None:
            logger.warning(f"Duplicate execution blocked: mandate_id={mandate_id}")
            return existing

        logger.info(f"Starting payment execution: mandate_id={mandate_id}")

        # ── State Machine: create in ISSUED state ────────────────────────
        # Generate a unique payment_object_id for this execution.
        # Each payment gets its own ID even if sharing the same mandate.
        from uuid import uuid4
        payment_object_id = f"po_{uuid4().hex[:16]}"
        sm = PaymentStateMachine(payment_object_id=payment_object_id)
        # Machine starts in ISSUED (the default initial state).

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

        # ── Phase 0.5: Spending Mandate Validation (FAIL-CLOSED) ─────────
        # If a spending mandate lookup service is configured, the payment MUST
        # be authorized by an *active* spending mandate.  The lookup only
        # returns mandates with ``status = 'active'`` — so revoked, suspended,
        # expired and exhausted mandates yield ``None`` and MUST be denied
        # here (this is the whole point of revocation: authority is removed).
        #
        # FAIL-CLOSED CONTRACT: when a lookup is configured and no active
        # mandate is found, we DENY before compliance / chain / ledger run.
        # We never let a payment through on a missing mandate or a lookup
        # error — the lookup re-raises on DB error and we convert that to a
        # denial rather than swallowing it into an allow.
        #
        # NOTE: the mandate is bound to a distinct local (``spending_mandate``)
        # rather than ``sm`` — ``sm`` is the PaymentStateMachine created above
        # and must not be clobbered, or the later state-machine transitions
        # would break.
        spending_mandate_id = ""
        # Bound to the governing SpendingMandate when a lookup is configured and
        # an active mandate exists; stays None otherwise (no mandate governs this
        # pay).  Read later by the optional recourse hook.
        spending_mandate: Any | None = None
        # Captured for Phase 3.5: after settlement we must persist the mandate
        # spend (lifetime cap accuracy).  None when no mandate governs this pay.
        spending_mandate_spend: Decimal | None = None
        # The resolved attenuated delegation chain (root mandate first, leaf
        # delegation last) when the acting agent is a DELEGATEE rather than the
        # root mandate holder.  Stays empty for a direct (non-delegated) payment.
        # Recorded on the PaymentResult so it can be bound into the portable
        # Proof-of-Authority emitted on every authorized execution.
        delegation_chain: list[Any] = []
        if self._spending_mandate_lookup is not None:
            try:
                agent_id = getattr(payment, 'agent_id', None) or getattr(payment, 'from_agent', None)
                wallet_id = getattr(payment, 'wallet_id', None) or getattr(payment, 'subject', None)
                # Pass the in-flight payment so a delegation-aware lookup can
                # re-check the attenuated chain at EXECUTION time.  Tolerate
                # legacy lookups whose signature predates the ``payment`` kwarg.
                try:
                    spending_mandate = await self._spending_mandate_lookup.get_active_mandate(
                        agent_id=agent_id,
                        wallet_id=wallet_id,
                        payment=payment,
                    )
                except TypeError:
                    spending_mandate = await self._spending_mandate_lookup.get_active_mandate(
                        agent_id=agent_id,
                        wallet_id=wallet_id,
                    )
            except MandateViolationError:
                raise
            except Exception as e:
                # Fail-closed: a lookup error (e.g. DB down) is a DENY, never
                # an allow.  Audit and reject before anything else runs.
                self._audit(mandate_id, ExecutionPhase.MANDATE_VALIDATION, False,
                           {"agent_id": agent_id, "wallet_id": wallet_id},
                           error=f"mandate_lookup_error: {e}")
                raise PolicyViolationError(
                    f"Spending mandate lookup error (fail-closed): {e}",
                    mandate_id=mandate_id,
                    rule_id="spending_mandate_lookup_error",
                )

            if spending_mandate is None:
                # FAIL-CLOSED: no active mandate (revoked / suspended / expired
                # / exhausted / never issued).  Authority is absent — DENY.
                self._audit(
                    mandate_id, ExecutionPhase.MANDATE_VALIDATION, False,
                    {"spending_mandate_id": None,
                     "agent_id": agent_id,
                     "wallet_id": wallet_id,
                     "reason": "no_active_spending_mandate"},
                    "No active spending mandate authorizes this payment "
                    "(revoked, suspended, expired, or never issued)",
                )
                raise PolicyViolationError(
                    "No active spending mandate authorizes this payment "
                    "(revoked, suspended, expired, or never issued)",
                    mandate_id=mandate_id,
                    rule_id="no_active_spending_mandate",
                )

            # An active mandate exists — enforce its scope/limits/approvals.
            # Mandate limits are in TOKEN (major) units; typed PaymentMandates
            # only carry integer minor units.  Normalize so a 50-USDC payment
            # is checked as 50, not 50_000_000, against a $100 cap.
            pay_amount = _resolve_token_amount(payment)
            merchant_id = getattr(payment, 'merchant_id', None) or getattr(payment, 'destination', None)
            rail = getattr(payment, 'rail', None)
            chain_name = getattr(payment, 'chain', None)
            token = getattr(payment, 'token', None)

            check = spending_mandate.check_payment(
                amount=pay_amount,
                merchant=merchant_id,
                rail=rail,
                chain=chain_name,
                token=token,
            )

            if not check.approved:
                self._audit(
                    mandate_id, ExecutionPhase.MANDATE_VALIDATION, False,
                    {"spending_mandate_id": spending_mandate.id,
                     "error_code": check.error_code,
                     "agent_id": agent_id},
                    check.reason,
                )
                raise MandateViolationError(
                    check.reason,
                    mandate_id=mandate_id,
                    error_code=check.error_code,
                )

            if check.requires_approval and _approved_request is None:
                # ── Human-in-the-loop gate ──────────────────────────────
                # If an ApprovalGate is configured, do NOT fail closed: create a
                # durable, signed ApprovalRequest, relay it to a human, and
                # return a PENDING result (no money moves).  Re-execution
                # happens later via execute_on_approval, which re-enters here
                # with _approved_request set so this branch is satisfied — while
                # every other check (mandate/policy/compliance/revocation) is
                # re-run.  With no gate configured, preserve the legacy raise.
                self._audit(
                    mandate_id, ExecutionPhase.MANDATE_VALIDATION, False,
                    {"spending_mandate_id": spending_mandate.id,
                     "requires_approval": True,
                     "agent_id": agent_id},
                    "Mandate requires human approval for this amount",
                )
                if self._approval_gate is not None:
                    pending = await self._open_approval(
                        chain=chain,
                        payment=payment,
                        mandate_id=mandate_id,
                        agent_id=agent_id,
                        amount=pay_amount,
                        counterparty=merchant_id,
                        spending_mandate=spending_mandate,
                        reason=(
                            f"Payment of {pay_amount} requires human approval "
                            f"(threshold: {spending_mandate.approval_threshold})"
                        ),
                        start_time=start_time,
                    )
                    return pending
                raise MandateViolationError(
                    f"Payment of {pay_amount} requires human approval "
                    f"(threshold: {spending_mandate.approval_threshold})",
                    mandate_id=mandate_id,
                    error_code="MANDATE_APPROVAL_REQUIRED",
                    requires_approval=True,
                )

            spending_mandate_id = spending_mandate.id
            # Persist this amount (token units) against the mandate after
            # settlement so lifetime/window caps reflect the new spend.
            spending_mandate_spend = pay_amount
            # ── Capture the resolved attenuated delegation chain ────────────
            # A delegation-aware lookup re-checks the WHOLE chain (every link
            # non-revoked + within cap/scope + non-expired) BEFORE returning the
            # root mandate above — so reaching this point means the chain already
            # authorized fail-closed.  Pull the resolved chain (keyed by the
            # unique per-execution mandate_id) so it can be recorded on the
            # PaymentResult and bound into the Proof-of-Authority.  Direct
            # (non-delegated) payments return an empty chain.
            if hasattr(self._spending_mandate_lookup, "get_resolved_chain"):
                try:
                    delegation_chain = (
                        self._spending_mandate_lookup.get_resolved_chain(mandate_id)
                        or []
                    )
                except Exception:  # pragma: no cover - chain capture is additive
                    delegation_chain = []
            self._audit(
                mandate_id, ExecutionPhase.MANDATE_VALIDATION, True,
                {"spending_mandate_id": spending_mandate.id,
                 "mandate_version": getattr(check, "mandate_version", None),
                 "agent_id": agent_id,
                 "delegation_depth": (len(delegation_chain) - 1) if delegation_chain else 0,
                 "is_delegated": bool(delegation_chain)},
            )

        # ── Phase 1: Policy Validation (fail-fast) ──────────────────────
        # This is where spending policies are enforced.  The wallet manager
        # fetches the agent's SpendingPolicy and runs all checks (amount
        # limits, merchant rules, time windows, etc.).  If denied, we raise
        # immediately — no compliance check, no chain execution, no money moves.
        try:
            if hasattr(self._wallet_manager, "async_validate_policies"):
                policy = await self._wallet_manager.async_validate_policies(payment)
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
            # ── Policy-level approval escalation ────────────────────────
            # SpendingPolicy returns allowed=True with reason "requires_approval"
            # (and/or required_approvals > 0) when a payment is within limits but
            # over the human-approval threshold.  This is NOT a free pass — it is
            # an escalation.  Route it through the same human-in-the-loop gate so
            # money never moves on an un-approved over-threshold payment.
            _policy_reason = (getattr(policy, "reason", None) or "")
            _needs_approval = (
                "requires_approval" in _policy_reason
                or getattr(policy, "required_approvals", 0) > 0
            )
            if _needs_approval and _approved_request is None:
                self._audit(
                    mandate_id, ExecutionPhase.POLICY_VALIDATION, False,
                    {"requires_approval": True, "reason": _policy_reason},
                    "Policy requires human approval for this payment",
                )
                if self._approval_gate is not None:
                    pay_amount = _resolve_token_amount(payment)
                    counterparty = (
                        getattr(payment, "merchant_id", None)
                        or getattr(payment, "destination", None)
                    )
                    return await self._open_approval(
                        chain=chain,
                        payment=payment,
                        mandate_id=mandate_id,
                        agent_id=getattr(payment, "agent_id", None)
                        or getattr(payment, "from_agent", None),
                        amount=pay_amount,
                        counterparty=counterparty,
                        spending_mandate=None,
                        reason=_policy_reason or "policy_requires_approval",
                        start_time=start_time,
                    )
                raise PolicyViolationError(
                    "Policy requires human approval for this payment",
                    mandate_id=mandate_id,
                    rule_id="policy_requires_approval",
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

        # ── Phase 1.6: Guard / Risk Assessment (fail-closed) ────────────
        # Agent-fraud risk scoring: the in-house RiskEngine combines the
        # behavioral AnomalyEngine score with external fraud-signal feeds
        # (Stripe Radar / SEON) and returns a binding GuardAction.  This runs
        # AFTER policy/mandate (so a policy deny short-circuits first) and
        # BEFORE compliance + chain (so a risky payment never reaches the
        # money path).  Action mapping:
        #   BLOCK            -> deny, fail-closed (RiskViolationError), no money.
        #   REQUIRE_APPROVAL -> route to the ApprovalGate (high-risk step-up);
        #                        return a pending result, no money moves.
        #   FLAG             -> allow + record the risk signal as evidence.
        #   ALLOW            -> proceed.
        # Additive: skipped entirely when no risk_engine is configured.  A
        # risk_engine error is itself fail-closed (deny), never a silent allow.
        if self._risk_engine is not None and _approved_request is None:
            agent_id = (
                getattr(payment, "agent_id", None)
                or getattr(payment, "from_agent", None)
                or ""
            )
            risk_amount = _resolve_token_amount(payment)
            risk_counterparty = (
                getattr(payment, "merchant_id", None)
                or getattr(payment, "destination", None)
            )
            try:
                from sardis.guardrails.risk_engine import GuardAction

                meta = getattr(payment, "metadata", None) or {}
                decision = await self._risk_engine.assess(
                    agent_id=str(agent_id),
                    amount=risk_amount,
                    counterparty=risk_counterparty,
                    merchant_category=getattr(payment, "merchant_category", None)
                    or meta.get("merchant_category"),
                    baseline_mean=meta.get("baseline_mean"),
                    baseline_std=meta.get("baseline_std"),
                    recent_tx_count_1h=meta.get("recent_tx_count_1h", 0),
                    is_new_merchant=meta.get("is_new_merchant", False),
                    hour_of_day=meta.get("hour_of_day"),
                    typical_hours=meta.get("typical_hours"),
                    signal_context=meta.get("signal_context"),
                )
            except RiskViolationError:
                raise
            except Exception as e:
                # Fail-closed: a RiskEngine error on a money path = deny.
                self._audit(
                    mandate_id, ExecutionPhase.RISK_ASSESSMENT, False,
                    {"agent_id": agent_id}, error=f"risk_engine_error: {e}",
                )
                raise RiskViolationError(
                    f"Risk assessment error: {e}",
                    mandate_id=mandate_id,
                )

            evidence = decision.to_dict()
            if decision.action == GuardAction.BLOCK:
                self._audit(
                    mandate_id, ExecutionPhase.RISK_ASSESSMENT, False,
                    {"agent_id": agent_id, "action": "block",
                     "score": decision.combined_score, "evidence": evidence},
                    f"guard_blocked: score={decision.combined_score:.1f}",
                )
                raise RiskViolationError(
                    f"Payment blocked by Guard risk engine "
                    f"(score={decision.combined_score:.1f}/100)",
                    mandate_id=mandate_id,
                    score=decision.combined_score,
                    evidence=evidence,
                )

            if decision.action == GuardAction.REQUIRE_APPROVAL:
                self._audit(
                    mandate_id, ExecutionPhase.RISK_ASSESSMENT, False,
                    {"agent_id": agent_id, "action": "require_approval",
                     "score": decision.combined_score, "evidence": evidence},
                    "Guard risk engine requires human approval",
                )
                if self._approval_gate is not None:
                    return await self._open_approval(
                        chain=chain,
                        payment=payment,
                        mandate_id=mandate_id,
                        agent_id=str(agent_id) or None,
                        amount=risk_amount,
                        counterparty=risk_counterparty,
                        spending_mandate=None,
                        reason=(
                            f"High agent-fraud risk "
                            f"(score={decision.combined_score:.1f}/100) requires "
                            f"human approval"
                        ),
                        start_time=start_time,
                    )
                # No ApprovalGate wired: a high-risk payment cannot be silently
                # allowed — fail closed as a block.
                raise RiskViolationError(
                    f"High-risk payment requires approval but no approval gate "
                    f"is configured (score={decision.combined_score:.1f}/100)",
                    mandate_id=mandate_id,
                    score=decision.combined_score,
                    evidence=evidence,
                )

            # FLAG -> allow + record; ALLOW -> proceed (both audited).
            self._audit(
                mandate_id, ExecutionPhase.RISK_ASSESSMENT, True,
                {"agent_id": agent_id, "action": decision.action.value,
                 "score": decision.combined_score,
                 "flagged": decision.action == GuardAction.FLAG,
                 "evidence": evidence},
            )

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

        # ── State Machine: all pre-checks passed → LOCKED ────────────────
        # The payment has survived KYA, mandate, policy, and compliance
        # validation.  Lock funds and prepare for on-chain settlement.
        record = sm.transition(
            PaymentState.PRESENTED, actor="orchestrator",
            reason="Pre-execution checks passed",
        )
        await _handler_registry.fire_on_enter(PaymentState.PRESENTED, sm, record)
        record = sm.transition(
            PaymentState.VERIFIED, actor="orchestrator",
            reason="Policy and compliance verified",
        )
        await _handler_registry.fire_on_enter(PaymentState.VERIFIED, sm, record)
        record = sm.transition(
            PaymentState.LOCKED, actor="orchestrator",
            reason="Funds locked for settlement",
        )
        await _handler_registry.fire_on_enter(PaymentState.LOCKED, sm, record)

        # ── Atomic dedup reservation (BEFORE dispatch) ──────────────────
        # The pre-dispatch ``check()`` above and the post-settlement
        # ``check_and_set()`` are not atomic together: two workers could both
        # pass ``check()`` and both dispatch the same mandate. ``reserve()`` is
        # an atomic check-and-set (Redis ``SET NX``) that lets exactly one
        # worker proceed. This guards duplicate *executions* and is distinct
        # from the SettlementLock, which serializes per payment_object_id (a
        # unique per-execution id) and so cannot dedup across executions of the
        # same mandate. Stores expose ``reserve``; tolerate ones that don't.
        did_reserve = False
        if hasattr(self._dedup_store, "reserve"):
            reserved = await self._dedup_store.reserve(mandate_id)
            did_reserve = reserved
            if not reserved:
                logger.warning(
                    "Duplicate execution blocked at reserve: mandate_id=%s", mandate_id
                )
                # Another worker already reserved/settled. Return its result if
                # available; otherwise reject the concurrent duplicate.
                existing_after = await self._dedup_store.check(mandate_id)
                if existing_after is not None:
                    return existing_after
                raise ChainExecutionError(
                    "Another worker is already settling this payment (duplicate reservation)",
                    mandate_id=mandate_id,
                    chain=payment.chain,
                )

        # Phase 3: Chain Execution (protected by SettlementLock)
        # Acquire a PostgreSQL advisory lock keyed on the payment_object_id
        # (not mandate_id — multiple payments can share one mandate).
        # This prevents a second worker from settling the same payment.
        # If no SettlementLock was injected, proceed without locking (dev mode).
        receipt = None
        try:
            if self._settlement_lock is not None:
                async with self._settlement_lock.with_lock(payment_object_id):
                    receipt = await self._execute_chain_settlement(
                        sm, payment, payment_object_id,
                    )
            else:
                receipt = await self._execute_chain_settlement(
                    sm, payment, payment_object_id,
                )
        except SettlementLockError:
            # Another worker is already settling this payment — reject.
            # Do NOT release the dedup reservation: a sibling worker is
            # legitimately mid-flight on this mandate.
            self._audit(mandate_id, ExecutionPhase.CHAIN_EXECUTION, False,
                       error="settlement_lock_contention")
            raise ChainExecutionError(
                "Another worker is already settling this payment",
                mandate_id=mandate_id,
                chain=payment.chain,
            )
        except Exception:
            # Dispatch failed and NO money moved (settlement raises before/at
            # dispatch). Release the reservation so a legitimate retry of this
            # mandate is not blocked for the full dedup TTL.
            if did_reserve and hasattr(self._dedup_store, "release"):
                try:
                    await self._dedup_store.release(mandate_id)
                except Exception:  # pragma: no cover - best-effort cleanup
                    logger.warning(
                        "Failed to release dedup reservation after dispatch failure: %s",
                        mandate_id,
                    )
            raise

        # ── Phase 3.5: Update Policy Spend State (mandatory) ────────────
        # After a successful on-chain payment, we MUST record the spend so
        # the agent's cumulative totals are accurate for future policy checks.
        # Uses SELECT FOR UPDATE in the DB to prevent race conditions.
        # If this fails, the spend is queued for reconciliation — otherwise
        # the agent could exceed its limits by making rapid payments.
        try:
            if hasattr(self._wallet_manager, "async_record_spend"):
                await self._wallet_manager.async_record_spend(payment)
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
            await self._enqueue_reconciliation(spend_recon)
            logger.warning(
                "Queued spend-state reconciliation for mandate=%s tx=%s",
                mandate_id, receipt.tx_hash,
            )

        # ── Phase 3.5a: Persist Spending-Mandate Spend (lifetime cap) ───
        # The MANDATE_VALIDATION phase validated against ``spending_mandate.
        # spent_total``.  Recording spend only against the policy state (above)
        # would leave the mandate's ``spent_total`` stale, so a lifetime-budget
        # mandate could be exceeded across payments.  Persist the spend here.
        # Fail-safe: a persistence failure AFTER settlement must NOT crash the
        # payment — it is queued for reconciliation instead.
        if (
            self._spending_mandate_lookup is not None
            and spending_mandate_id
            and spending_mandate_spend is not None
            and hasattr(self._spending_mandate_lookup, "record_spend")
        ):
            try:
                await self._spending_mandate_lookup.record_spend(
                    mandate_id=spending_mandate_id,
                    amount=spending_mandate_spend,
                )
                self._audit(
                    mandate_id, ExecutionPhase.POLICY_STATE_UPDATE, True,
                    {"spending_mandate_id": spending_mandate_id,
                     "mandate_spend_recorded": str(spending_mandate_spend)},
                )
            except Exception as e:
                self._audit(
                    mandate_id, ExecutionPhase.POLICY_STATE_UPDATE, False,
                    {"spending_mandate_id": spending_mandate_id},
                    error=f"mandate_spend_record_failed: {e}",
                )
                logger.error(
                    "Spending-mandate spend persistence failed for mandate=%s "
                    "(spending_mandate=%s): %s",
                    mandate_id, spending_mandate_id, e,
                )
                await self._enqueue_reconciliation(ReconciliationEntry(
                    mandate_id=mandate_id,
                    chain_tx_hash=receipt.tx_hash,
                    chain=receipt.chain,
                    audit_anchor=receipt.audit_anchor,
                    payment_mandate=payment,
                    chain_receipt=receipt,
                    error=f"mandate_spend_persistence_failed: {e}",
                ))

        # ── Phase 3.5a-bis: Decrement the attenuated delegation chain ───
        # When a DELEGATEE made this payment, the spend draws down its own
        # delegation cap AND every ancestor delegation's cap (a child spend
        # consumes parent budget — the cardinal attenuation rule, enforced at
        # spend time so the next chain re-check sees the reduced remaining).
        # The root SpendingMandate's spent_total was already recorded in Phase
        # 3.5a above, so this NEVER double-counts the root — it touches only the
        # Delegation hops.  Each hop is decremented atomically (per-row update);
        # a failure is queued for reconciliation, never crashes a settled pay.
        if (
            delegation_chain
            and self._spending_mandate_lookup is not None
            and spending_mandate_spend is not None
            and hasattr(self._spending_mandate_lookup, "record_chain_spend")
        ):
            try:
                await self._spending_mandate_lookup.record_chain_spend(
                    delegation_chain, spending_mandate_spend,
                )
                leaf = delegation_chain[-1]
                self._audit(
                    mandate_id, ExecutionPhase.POLICY_STATE_UPDATE, True,
                    {"delegation_leaf_id": getattr(leaf, "id", None),
                     "delegation_hops_decremented": len(delegation_chain) - 1,
                     "chain_spend_recorded": str(spending_mandate_spend)},
                )
            except Exception as e:
                self._audit(
                    mandate_id, ExecutionPhase.POLICY_STATE_UPDATE, False,
                    {"delegation_leaf_id": getattr(delegation_chain[-1], "id", None)},
                    error=f"delegation_chain_spend_failed: {e}",
                )
                logger.error(
                    "Delegation chain spend persistence failed for mandate=%s: %s",
                    mandate_id, e,
                )
                await self._enqueue_reconciliation(ReconciliationEntry(
                    mandate_id=mandate_id,
                    chain_tx_hash=receipt.tx_hash,
                    chain=receipt.chain,
                    audit_anchor=receipt.audit_anchor,
                    payment_mandate=payment,
                    chain_receipt=receipt,
                    error=f"delegation_chain_spend_persistence_failed: {e}",
                ))

        # ── Phase 3.5b: Update Group Spend State ────────────────────────
        # If the agent belongs to a group, record the spend against all
        # group budgets so future group policy checks are accurate.
        # This is a best-effort update — failure is logged but does not
        # block the payment (it already succeeded on-chain).
        if self._group_policy is not None:
            agent_id = getattr(payment, 'agent_id', None) or getattr(payment, 'from_agent', None)
            if agent_id:
                try:
                    from decimal import Decimal as _Dec
                    pay_amount = getattr(payment, 'amount', None) or getattr(payment, 'amount_minor', 0)
                    await self._group_policy.record_spend(
                        agent_id=agent_id,
                        amount=_Dec(str(pay_amount)),
                    )
                    self._audit(
                        mandate_id,
                        ExecutionPhase.POLICY_STATE_UPDATE,
                        True,
                        {"group_spend_recorded": True, "agent_id": agent_id},
                    )
                except Exception as e:
                    logger.error(
                        "Failed to record group spend for agent=%s mandate=%s: %s",
                        agent_id, mandate_id, e,
                    )
                    self._audit(
                        mandate_id,
                        ExecutionPhase.POLICY_STATE_UPDATE,
                        False,
                        error=f"group_spend_record_failed: {e}",
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
            await self._enqueue_reconciliation(reconciliation_entry)

            logger.error(
                f"Ledger append failed but payment succeeded on-chain. "
                f"mandate_id={mandate_id}, tx_hash={receipt.tx_hash}, error={e}"
            )

            # Return result with warning - payment DID succeed (money moved
            # on-chain), so the action WAS authorized — emit the proof too.
            execution_time = (time.time() - start_time) * 1000
            authority_proof = self._emit_authority_proof(
                payment=payment,
                receipt=receipt,
                mandate_id=mandate_id,
                spending_mandate=spending_mandate,
                spending_mandate_id=spending_mandate_id,
                delegation_chain=delegation_chain,
            )
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
                spending_mandate_id=spending_mandate_id,
                delegation_chain=delegation_chain,
                authority_proof=authority_proof,
            )
            await self._dedup_store.check_and_set(mandate_id, result)
            return result

        # ── State Machine: SETTLED → FULFILLED ────────────────────────────
        record = sm.transition(
            PaymentState.FULFILLED, actor="orchestrator",
            reason="Ledger append complete, payment fulfilled",
            metadata={"ledger_tx_id": ledger_tx.tx_id if ledger_tx else "unknown"},
        )
        await _handler_registry.fire_on_enter(PaymentState.FULFILLED, sm, record)

        # Success!
        self._audit(mandate_id, ExecutionPhase.COMPLETED, True)
        execution_time = (time.time() - start_time) * 1000

        # ── Phase 5: Programmable Recourse (OPTIONAL, additive) ──────────
        # If a recourse engine is configured AND this payment carries a
        # policy-defined recourse window, open a durable, signed RecourseHold
        # so the payment is settled-but-recourse-able for the window instead of
        # immediately final.  No window -> immediate finality (unchanged).
        # Fail-closed/safe: money already moved, so a failure here never crashes
        # the payment — it is audited and the result is returned without a hold.
        recourse_hold_id = ""
        if self._recourse_engine is not None:
            recourse_hold_id = await self._maybe_open_recourse(
                payment=payment,
                mandate_id=mandate_id,
                payment_object_id=payment_object_id,
                spending_mandate=spending_mandate,
            )

        # ── Portable Proof-of-Authority (emitted on every ALLOWED execution) ─
        authority_proof = self._emit_authority_proof(
            payment=payment,
            receipt=receipt,
            mandate_id=mandate_id,
            spending_mandate=spending_mandate,
            spending_mandate_id=spending_mandate_id,
            delegation_chain=delegation_chain,
        )

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
            spending_mandate_id=spending_mandate_id,
            recourse_hold_id=recourse_hold_id,
            delegation_chain=delegation_chain,
            authority_proof=authority_proof,
        )
        await self._dedup_store.check_and_set(mandate_id, result)
        return result

    def _emit_authority_proof(
        self,
        *,
        payment: Any,
        receipt: Any,
        mandate_id: str,
        spending_mandate: Any | None,
        spending_mandate_id: str,
        delegation_chain: list[Any],
    ) -> Any | None:
        """Mint the portable Proof-of-Authority for this ALLOWED execution.

        Emitted alongside the ExecutionReceipt.  Self-contained and signed with
        Ed25519 so any holder of the PUBLISHED public key can verify offline that
        this agent was authorized for this exact action — binding the policy /
        mandate snapshot, the evaluated inputs, and (when delegated) the whole
        attenuated delegation chain.  Fail-closed-but-safe: the money already
        moved, so a failure here is audited and swallowed (never crash a settled
        payment) — but in prod/staging a missing signing key DOES raise at sign
        time, which is the intended fail-closed posture for a credential.
        """
        try:
            from .approval_gate import hash_snapshot
            from .authority_proof import build_authority_proof

            agent = (
                getattr(payment, "agent_id", None)
                or getattr(payment, "from_agent", None)
                or getattr(payment, "subject", None)
                or "unknown_agent"
            )
            # When the action ran under delegation, the acting principal is the
            # leaf delegatee; bind that as the authorized agent.
            if delegation_chain:
                leaf = delegation_chain[-1]
                agent = getattr(leaf, "delegatee", None) or agent

            amount_minor = int(getattr(payment, "amount_minor", 0) or 0)
            token = getattr(payment, "token", None)
            currency = str(token) if token is not None else getattr(payment, "currency", "USDC")
            counterparty = (
                getattr(payment, "merchant_id", None)
                or getattr(payment, "destination", None)
                or getattr(payment, "to_address", None)
                or "unknown_counterparty"
            )
            amount_major = _resolve_token_amount(payment)

            # Policy / mandate snapshot hashes — the same canonical snapshot
            # binding used by the recourse / approval paths.
            mandate_hash = hash_snapshot(spending_mandate) if spending_mandate else ""
            policy_hash = hash_snapshot(
                {
                    "mandate_id": mandate_id,
                    "agent": agent,
                    "amount_minor": amount_minor,
                    "currency": currency,
                    "counterparty": counterparty,
                    "spending_mandate_id": spending_mandate_id,
                }
            )

            inputs = {
                "rail": getattr(payment, "rail", None),
                "chain": getattr(payment, "chain", None) or getattr(receipt, "chain", None),
                "token": str(token) if token is not None else None,
                "category": getattr(payment, "category", None),
                "mcc": getattr(payment, "mcc", None),
                "tx_hash": getattr(receipt, "tx_hash", None),
            }

            proof = build_authority_proof(
                action_id=mandate_id,
                agent=str(agent),
                amount_minor=amount_minor,
                currency=str(currency),
                counterparty=str(counterparty),
                policy_hash=policy_hash,
                mandate_hash=mandate_hash,
                spending_mandate_id=spending_mandate_id,
                amount=amount_major,
                inputs=inputs,
                delegation_chain=delegation_chain,
                secret=self._authority_proof_secret,
            )
            self._audit(
                mandate_id, ExecutionPhase.COMPLETED, True,
                {"authority_proof_id": proof.proof_id,
                 "is_delegated": bool(delegation_chain),
                 "delegation_depth": (len(delegation_chain) - 1) if delegation_chain else 0},
            )
            return proof
        except Exception as e:  # noqa: BLE001 - never crash a settled payment
            self._audit(
                mandate_id, ExecutionPhase.COMPLETED, False,
                error=f"authority_proof_emit_failed: {e}",
            )
            logger.error("Authority proof emission failed for mandate=%s: %s", mandate_id, e)
            return None

    async def _maybe_open_recourse(
        self,
        *,
        payment: Any,
        mandate_id: str,
        payment_object_id: str,
        spending_mandate: Any | None,
    ) -> str:
        """Open a RecourseHold iff a recourse window is configured for this
        payment.  Returns the hold id, or "" for immediate finality.

        Window resolution order (first non-None wins):
          1. ``recourse_window_resolver(payment, spending_mandate)`` if injected;
          2. ``spending_mandate.recourse_window_seconds`` if present;
          3. None -> immediate finality (no hold).

        Fail-closed-but-safe: the money already settled, so any error here is
        audited and swallowed (the caller gets a normal success without a hold)
        — we never crash a settled payment, and we never silently claim a hold
        that did not open.
        """
        try:
            window = None
            if self._recourse_window_resolver is not None:
                window = self._recourse_window_resolver(payment, spending_mandate)
            if window is None and spending_mandate is not None:
                window = getattr(spending_mandate, "recourse_window_seconds", None)
            if not window or int(window) <= 0:
                return ""

            from .approval_gate import hash_snapshot

            amount_minor = int(getattr(payment, "amount_minor", 0) or 0)
            token = getattr(payment, "token", None)
            currency = str(token) if token is not None else "USDC"
            amount = Decimal(amount_minor) / Decimal(10**6)
            payer = (
                getattr(payment, "from_address", None)
                or getattr(payment, "smart_account_address", None)
                or getattr(payment, "wallet_id", None)
                or getattr(payment, "agent_id", None)
                or "unknown_payer"
            )
            recipient = getattr(payment, "destination", None) or "unknown_recipient"
            agent_id = getattr(payment, "agent_id", None) or getattr(payment, "subject", None)
            spending_mandate_id = getattr(spending_mandate, "id", None) if spending_mandate else None

            policy_hash = hash_snapshot(
                {
                    "mandate_id": mandate_id,
                    "agent_id": agent_id,
                    "amount_minor": amount_minor,
                    "currency": currency,
                    "recipient": recipient,
                    "window_seconds": int(window),
                }
            )
            mandate_hash = hash_snapshot(spending_mandate) if spending_mandate else ""

            hold = await self._recourse_engine.open_hold(
                payment_ref=payment_object_id,
                mandate_id=mandate_id,
                agent_id=agent_id,
                amount=amount,
                amount_minor=amount_minor,
                currency=currency,
                payer=str(payer),
                recipient=str(recipient),
                window_seconds=int(window),
                policy_hash=policy_hash,
                mandate_hash=mandate_hash,
                metadata={"spending_mandate_id": spending_mandate_id},
            )
            self._audit(
                mandate_id, ExecutionPhase.COMPLETED, True,
                {"recourse_hold_id": hold.id, "window_seconds": int(window),
                 "amount_minor": amount_minor},
            )
            return hold.id
        except Exception as e:  # noqa: BLE001 - never crash a settled payment
            self._audit(
                mandate_id, ExecutionPhase.COMPLETED, False,
                error=f"recourse_open_failed: {e}",
            )
            logger.error("Recourse hold open failed for mandate=%s: %s", mandate_id, e)
            return ""

    async def _open_approval(
        self,
        *,
        chain: MandateChain,
        payment: PaymentMandate,
        mandate_id: str,
        agent_id: str | None,
        amount: Decimal,
        counterparty: str | None,
        spending_mandate: Any | None,
        reason: str,
        start_time: float,
    ) -> PaymentResult:
        """Create a durable, signed ApprovalRequest, relay it to a human, and
        return a PENDING PaymentResult.  NO money moves here.

        The bound policy/mandate hashes snapshot the state in effect now so the
        later re-execution can detect drift; the chain snapshot is the verified
        chain needed to re-run ``execute_chain`` after approval.
        """
        import time as _time

        from .approval_gate import hash_snapshot

        token = getattr(payment, "token", None)
        currency = str(token) if token is not None else "USDC"
        spending_mandate_id = getattr(spending_mandate, "id", "") if spending_mandate else ""
        mandate_hash = hash_snapshot(spending_mandate) if spending_mandate else ""
        # Policy snapshot: the immutable identity of what is being authorized.
        policy_hash = hash_snapshot(
            {
                "mandate_id": mandate_id,
                "agent_id": agent_id,
                "amount": str(amount),
                "currency": currency,
                "counterparty": counterparty,
            }
        )

        request = await self._approval_gate.open_request(
            agent_id=agent_id,
            mandate_id=mandate_id,
            amount=amount,
            currency=currency,
            counterparty=counterparty,
            reason=reason,
            spending_mandate_id=spending_mandate_id or None,
            policy_hash=policy_hash,
            mandate_hash=mandate_hash,
            chain_snapshot=chain,
        )

        logger.info(
            "Payment %s paused for human approval: approval_id=%s amount=%s %s",
            mandate_id, request.id, amount, currency,
        )

        execution_time = (_time.time() - start_time) * 1000
        return PaymentResult(
            mandate_id=mandate_id,
            ledger_tx_id="",
            chain_tx_hash="",
            chain=getattr(payment, "chain", "") or "",
            audit_anchor="",
            status="pending_approval",
            execution_time_ms=execution_time,
            spending_mandate_id=spending_mandate_id,
            approval_id=request.id,
        )

    async def execute_on_approval(self, approval_id: str) -> PaymentResult:
        """Re-execute a payment that a human has APPROVED — idempotently.

        Fail-closed contract:
          * the request must exist, be ``approved``, and not yet re-executed;
          * ``denied`` / ``expired`` / ``pending`` -> blocked (no money moves);
          * the original chain is re-run through the FULL ``execute_chain`` path,
            so mandate / policy / compliance / revocation are ALL re-evaluated at
            execution time — a mandate revoked AFTER approval still fails closed;
          * the ``reexecuted`` flag is flipped *before* dispatch so a duplicate
            approve callback cannot trigger a second settlement.
        """
        if self._approval_gate is None:
            raise PolicyViolationError(
                "execute_on_approval called but no approval_gate is configured",
                mandate_id=None,
                rule_id="no_approval_gate",
            )

        request = await self._approval_gate.get(approval_id)
        if request is None:
            raise PolicyViolationError(
                f"approval request {approval_id} not found",
                mandate_id=None,
                rule_id="approval_not_found",
            )

        # Fail-closed on any non-approved or already-spent state.
        from .approval_gate import ApprovalGate

        if not ApprovalGate.is_approved_and_unspent(request):
            self._audit(
                request.mandate_id or approval_id,
                ExecutionPhase.MANDATE_VALIDATION,
                False,
                {"approval_id": approval_id, "approval_status": request.status.value,
                 "reexecuted": request.reexecuted},
                f"approval not executable (status={request.status.value}, "
                f"reexecuted={request.reexecuted})",
            )
            raise PolicyViolationError(
                f"approval {approval_id} is not executable "
                f"(status={request.status.value}, reexecuted={request.reexecuted})",
                mandate_id=request.mandate_id,
                rule_id="approval_not_executable",
            )

        chain = request.chain_snapshot
        if chain is None:
            raise PolicyViolationError(
                f"approval {approval_id} has no chain snapshot to re-execute",
                mandate_id=request.mandate_id,
                rule_id="approval_missing_chain",
            )

        # Idempotency: flip BEFORE dispatch so a concurrent/duplicate callback
        # cannot settle twice.  A subsequent execute_chain failure leaves the
        # request approved-but-reexecuted; a retry would be blocked here, which
        # is the safe (fail-closed) default — re-approval is the recovery path.
        await self._approval_gate.mark_reexecuted(request)

        logger.info(
            "Re-executing approved payment: approval_id=%s mandate=%s",
            approval_id, request.mandate_id,
        )
        # _approved_request satisfies ONLY the approval-escalation gate; every
        # other check is re-run (never trust a stale approval).
        return await self.execute_chain(chain, _approved_request=request)

    async def _execute_chain_settlement(
        self,
        sm: PaymentStateMachine,
        payment: PaymentMandate,
        mandate_id: str,
    ) -> Any:
        """Execute on-chain settlement with state machine transitions.

        Extracted so it can be called both with and without a SettlementLock
        context manager while keeping the lock scope tight around the
        actual chain interaction.

        Returns:
            The chain receipt from ``dispatch_payment``.

        Raises:
            ChainExecutionError: If chain dispatch or confirmation fails.
        """
        try:
            # ── State Machine: LOCKED → SETTLING ─────────────────────────
            record = sm.transition(
                PaymentState.SETTLING, actor="orchestrator",
                reason="Chain execution started",
                metadata={"chain": payment.chain},
            )
            await _handler_registry.fire_on_enter(PaymentState.SETTLING, sm, record)

            receipt = await self._chain_executor.dispatch_payment(payment)
            self._audit(mandate_id, ExecutionPhase.CHAIN_EXECUTION, True,
                       {"tx_hash": receipt.tx_hash, "chain": receipt.chain,
                        "block_number": receipt.block_number})

            # ── State Machine: SETTLING → SETTLED ────────────────────────
            record = sm.transition(
                PaymentState.SETTLED, actor="orchestrator",
                reason="On-chain settlement confirmed",
                metadata={"tx_hash": receipt.tx_hash, "chain": receipt.chain},
            )
            await _handler_registry.fire_on_enter(PaymentState.SETTLED, sm, record)
            return receipt
        except SettlementLockError:
            raise
        except Exception as e:
            self._audit(mandate_id, ExecutionPhase.CHAIN_EXECUTION, False, error=str(e))
            # ── State Machine: SETTLING → FAILED ─────────────────────────
            if sm.can_transition(PaymentState.FAILED):
                fail_rec = sm.transition(
                    PaymentState.FAILED, actor="orchestrator",
                    reason=f"Chain execution failed: {e}",
                    metadata={"error": str(e)},
                )
                await _handler_registry.fire_on_enter(PaymentState.FAILED, sm, fail_rec)
            raise ChainExecutionError(
                f"Chain execution failed: {e}",
                mandate_id=mandate_id,
                chain=payment.chain,
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

    def get_audit_log(self, mandate_id: str | None = None, limit: int = 100) -> list[ExecutionAuditEntry]:
        """Get audit log entries, optionally filtered by mandate_id."""
        if mandate_id:
            return [e for e in self._audit_log if e.mandate_id == mandate_id][-limit:]
        return list(self._audit_log)[-limit:]
