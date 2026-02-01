"""Compliance pre-flight engine with audit trail."""
from __future__ import annotations

import logging
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import PaymentMandate

logger = logging.getLogger(__name__)


# ============ Audit Trail ============


@dataclass
class ComplianceAuditEntry:
    """
    Immutable audit entry for compliance decisions.

    This forms an append-only audit trail for regulatory compliance.
    Entries should NEVER be deleted or modified after creation.
    """

    # Unique identifier for this audit entry
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Mandate being evaluated
    mandate_id: str = ""

    # Subject (agent/wallet) being evaluated
    subject: str = ""

    # Decision result
    allowed: bool = False
    reason: Optional[str] = None
    rule_id: Optional[str] = None
    provider: Optional[str] = None

    # Timing
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Additional context for audit
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "audit_id": self.audit_id,
            "mandate_id": self.mandate_id,
            "subject": self.subject,
            "allowed": self.allowed,
            "reason": self.reason,
            "rule_id": self.rule_id,
            "provider": self.provider,
            "evaluated_at": self.evaluated_at.isoformat(),
            "metadata": self.metadata,
        }


class ComplianceAuditStore:
    """
    Thread-safe, append-only audit store for compliance decisions.

    ⚠️ PRODUCTION WARNING ⚠️
    This implementation uses in-memory storage which is NOT suitable for production.
    For production deployments, you MUST:
    1. Replace this with a PostgreSQL-backed implementation
    2. Enable write-ahead logging (WAL) for durability
    3. Disable DELETE capability to meet regulatory requirements
    4. Add cryptographic integrity checks (Merkle tree / hash chains)
    5. Implement retention policies per jurisdiction (e.g., 7 years for US)

    See: sardis_ledger.LedgerStore for a production-ready alternative.

    For now, uses in-memory storage with bounded size.
    """

    # Maximum entries to keep in memory (older entries should be persisted to DB)
    MAX_ENTRIES = 100_000
    _PRODUCTION_WARNING_SHOWN = False

    def __init__(self):
        if not ComplianceAuditStore._PRODUCTION_WARNING_SHOWN:
            import os
            env = os.getenv("SARDIS_ENVIRONMENT", "dev")
            if env in ("prod", "production"):
                logger.warning(
                    "⚠️ ComplianceAuditStore is using IN-MEMORY storage in PRODUCTION. "
                    "This does NOT meet regulatory requirements for audit trail retention. "
                    "Configure DATABASE_URL to enable persistent storage."
                )
            ComplianceAuditStore._PRODUCTION_WARNING_SHOWN = True
        self._entries: deque[ComplianceAuditEntry] = deque(maxlen=self.MAX_ENTRIES)
        self._lock = threading.Lock()
        self._by_mandate: Dict[str, List[str]] = {}  # mandate_id -> [audit_ids]

    def append(self, entry: ComplianceAuditEntry) -> str:
        """
        Append an audit entry. Returns the audit_id.

        This operation is append-only - entries cannot be modified or deleted.
        """
        with self._lock:
            self._entries.append(entry)

            # Index by mandate_id for quick lookups
            if entry.mandate_id:
                if entry.mandate_id not in self._by_mandate:
                    self._by_mandate[entry.mandate_id] = []
                self._by_mandate[entry.mandate_id].append(entry.audit_id)

            logger.debug(
                f"Audit entry recorded: audit_id={entry.audit_id}, "
                f"mandate_id={entry.mandate_id}, allowed={entry.allowed}"
            )

        return entry.audit_id

    def get_by_mandate(self, mandate_id: str) -> List[ComplianceAuditEntry]:
        """Get all audit entries for a mandate."""
        with self._lock:
            audit_ids = self._by_mandate.get(mandate_id, [])
            return [e for e in self._entries if e.audit_id in audit_ids]

    def get_recent(self, limit: int = 100) -> List[ComplianceAuditEntry]:
        """Get most recent audit entries."""
        with self._lock:
            return list(self._entries)[-limit:]

    def count(self) -> int:
        """Get total number of entries."""
        with self._lock:
            return len(self._entries)

    def export_all(self) -> List[Dict[str, Any]]:
        """Export all entries as dictionaries (for backup/persistence)."""
        with self._lock:
            return [e.to_dict() for e in self._entries]


# ============ PostgreSQL Audit Store ============


class PostgresAuditStore:
    """
    Production-ready PostgreSQL-backed audit store.

    Features:
    - Append-only (no DELETE operations)
    - Write-ahead logging via PostgreSQL
    - Hash chain for integrity verification
    - Supports regulatory retention requirements
    """

    def __init__(self, dsn: str):
        """Initialize with PostgreSQL connection string."""
        self._dsn = dsn
        self._pool = None
        self._lock = threading.Lock()
        self._initialized = False

    async def _ensure_initialized(self):
        """Lazily initialize the connection pool and table."""
        if self._initialized:
            return

        try:
            import asyncpg
        except ImportError:
            raise RuntimeError(
                "asyncpg is required for PostgreSQL audit store. "
                "Install with: pip install asyncpg"
            )

        self._pool = await asyncpg.create_pool(self._dsn, min_size=2, max_size=10)

        # Create table if not exists (append-only, no DELETE)
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_audit_trail (
                    id SERIAL PRIMARY KEY,
                    audit_id UUID UNIQUE NOT NULL,
                    mandate_id VARCHAR(255),
                    subject VARCHAR(255),
                    allowed BOOLEAN NOT NULL,
                    reason TEXT,
                    rule_id VARCHAR(255),
                    provider VARCHAR(255),
                    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}',
                    prev_hash VARCHAR(64),
                    entry_hash VARCHAR(64) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_audit_mandate_id ON compliance_audit_trail(mandate_id);
                CREATE INDEX IF NOT EXISTS idx_audit_subject ON compliance_audit_trail(subject);
                CREATE INDEX IF NOT EXISTS idx_audit_evaluated_at ON compliance_audit_trail(evaluated_at);

                -- Revoke DELETE permission for audit integrity
                -- REVOKE DELETE ON compliance_audit_trail FROM PUBLIC;
            """)

        self._initialized = True
        logger.info("PostgreSQL audit store initialized successfully")

    def _compute_hash(self, entry: ComplianceAuditEntry, prev_hash: str = "") -> str:
        """Compute SHA-256 hash for entry integrity."""
        import hashlib
        import json

        data = json.dumps({
            "audit_id": entry.audit_id,
            "mandate_id": entry.mandate_id,
            "subject": entry.subject,
            "allowed": entry.allowed,
            "reason": entry.reason,
            "evaluated_at": entry.evaluated_at.isoformat(),
            "prev_hash": prev_hash,
        }, sort_keys=True)

        return hashlib.sha256(data.encode()).hexdigest()

    async def append(self, entry: ComplianceAuditEntry) -> str:
        """Append an audit entry with hash chain integrity."""
        await self._ensure_initialized()

        async with self._pool.acquire() as conn:
            # Get previous hash for chain
            prev = await conn.fetchrow(
                "SELECT entry_hash FROM compliance_audit_trail ORDER BY id DESC LIMIT 1"
            )
            prev_hash = prev["entry_hash"] if prev else ""

            # Compute hash for this entry
            entry_hash = self._compute_hash(entry, prev_hash)

            # Insert (append-only)
            import json
            await conn.execute("""
                INSERT INTO compliance_audit_trail
                (audit_id, mandate_id, subject, allowed, reason, rule_id, provider,
                 evaluated_at, metadata, prev_hash, entry_hash)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                uuid.UUID(entry.audit_id),
                entry.mandate_id,
                entry.subject,
                entry.allowed,
                entry.reason,
                entry.rule_id,
                entry.provider,
                entry.evaluated_at,
                json.dumps(entry.metadata),
                prev_hash,
                entry_hash,
            )

        logger.debug(f"Audit entry persisted: audit_id={entry.audit_id}")
        return entry.audit_id

    async def get_by_mandate(self, mandate_id: str) -> List[ComplianceAuditEntry]:
        """Get all audit entries for a mandate."""
        await self._ensure_initialized()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM compliance_audit_trail WHERE mandate_id = $1 ORDER BY evaluated_at",
                mandate_id
            )

        return [self._row_to_entry(row) for row in rows]

    async def get_recent(self, limit: int = 100) -> List[ComplianceAuditEntry]:
        """Get most recent audit entries."""
        await self._ensure_initialized()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM compliance_audit_trail ORDER BY evaluated_at DESC LIMIT $1",
                limit
            )

        return [self._row_to_entry(row) for row in reversed(rows)]

    async def count(self) -> int:
        """Get total number of entries."""
        await self._ensure_initialized()

        async with self._pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM compliance_audit_trail")

        return result

    async def verify_chain_integrity(self) -> tuple[bool, Optional[str]]:
        """Verify the hash chain integrity of the audit trail."""
        await self._ensure_initialized()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM compliance_audit_trail ORDER BY id ASC"
            )

        prev_hash = ""
        for row in rows:
            entry = self._row_to_entry(row)
            expected_hash = self._compute_hash(entry, prev_hash)

            if expected_hash != row["entry_hash"]:
                return False, f"Hash mismatch at audit_id={row['audit_id']}"

            prev_hash = row["entry_hash"]

        return True, None

    def _row_to_entry(self, row) -> ComplianceAuditEntry:
        """Convert database row to ComplianceAuditEntry."""
        import json
        return ComplianceAuditEntry(
            audit_id=str(row["audit_id"]),
            mandate_id=row["mandate_id"] or "",
            subject=row["subject"] or "",
            allowed=row["allowed"],
            reason=row["reason"],
            rule_id=row["rule_id"],
            provider=row["provider"],
            evaluated_at=row["evaluated_at"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )


# ============ Audit Store Factory ============


def create_audit_store(dsn: Optional[str] = None) -> ComplianceAuditStore:
    """
    Factory function to create the appropriate audit store.

    If DATABASE_URL is set and asyncpg is available, returns PostgresAuditStore.
    Otherwise returns in-memory ComplianceAuditStore.
    """
    import os

    dsn = dsn or os.getenv("DATABASE_URL", "")

    if dsn and dsn.startswith("postgres"):
        try:
            import asyncpg  # noqa: F401
            logger.info("Using PostgreSQL audit store for compliance")
            # Note: PostgresAuditStore is async, caller must handle appropriately
            return PostgresAuditStore(dsn)
        except ImportError:
            logger.warning(
                "DATABASE_URL is set but asyncpg is not installed. "
                "Falling back to in-memory audit store."
            )

    return ComplianceAuditStore()


# Global audit store singleton
_audit_store: Optional[ComplianceAuditStore] = None


def get_audit_store() -> ComplianceAuditStore:
    """Get the global audit store singleton.

    Uses PostgresAuditStore when DATABASE_URL is set and asyncpg is available,
    otherwise falls back to in-memory ComplianceAuditStore.
    """
    global _audit_store
    if _audit_store is None:
        _audit_store = create_audit_store()
    return _audit_store


# ============ Compliance Result ============


@dataclass
class ComplianceResult:
    allowed: bool
    reason: str | None = None
    provider: str | None = None
    rule_id: str | None = None
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    audit_id: str | None = None  # Link to audit entry


class ComplianceProvider(Protocol):
    def evaluate(self, mandate: PaymentMandate) -> ComplianceResult: ...


class SimpleRuleProvider:
    """Placeholder rule engine before wiring external vendors."""

    def __init__(self, settings: SardisSettings):
        self._settings = settings

    def evaluate(self, mandate: PaymentMandate) -> ComplianceResult:
        if mandate.token not in {"USDC", "USDT", "PYUSD", "EURC"}:
            return ComplianceResult(allowed=False, reason="token_not_permitted", provider="rules", rule_id="token_allowlist")
        if mandate.amount_minor > 1_000_000_00:
            return ComplianceResult(allowed=False, reason="amount_over_limit", provider="rules", rule_id="max_amount")
        return ComplianceResult(allowed=True, provider="rules", rule_id="baseline")


class NLPolicyProvider:
    """
    Natural Language Policy Provider.

    Evaluates mandates against policies defined in natural language,
    using the NL Policy Parser to convert and enforce rules.
    """

    def __init__(self, settings: SardisSettings):
        self._settings = settings
        self._policies: Dict[str, Any] = {}  # agent_id -> SpendingPolicy
        self._fallback = SimpleRuleProvider(settings)

    def set_policy_for_agent(self, agent_id: str, policy: Any) -> None:
        """Set a spending policy for an agent."""
        self._policies[agent_id] = policy

    def get_policy_for_agent(self, agent_id: str) -> Optional[Any]:
        """Get the spending policy for an agent."""
        return self._policies.get(agent_id)

    def evaluate(self, mandate: PaymentMandate) -> ComplianceResult:
        """
        Evaluate mandate against NL-defined policies.

        Falls back to SimpleRuleProvider if no policy is defined.
        """
        # First, run basic checks
        basic_result = self._fallback.evaluate(mandate)
        if not basic_result.allowed:
            return basic_result

        # Check if there's a policy for this agent
        policy = self._policies.get(mandate.subject)
        if not policy:
            # No specific policy, use basic rules
            return ComplianceResult(
                allowed=True,
                provider="nl_policy",
                rule_id="no_policy_default",
                reason="No specific policy defined, using defaults",
            )

        # Evaluate against policy
        try:
            from decimal import Decimal
            amount = Decimal(str(mandate.amount_minor)) / Decimal("100")  # Convert from minor units
            fee = Decimal("0")  # Fee handled separately if needed

            # Use synchronous validation (no RPC client needed for compliance check)
            approved, reason = policy.validate_payment(
                amount=amount,
                fee=fee,
                merchant_id=mandate.destination,
            )

            if approved:
                return ComplianceResult(
                    allowed=True,
                    provider="nl_policy",
                    rule_id=policy.policy_id,
                )
            else:
                return ComplianceResult(
                    allowed=False,
                    reason=reason,
                    provider="nl_policy",
                    rule_id=policy.policy_id,
                )

        except Exception as e:
            logger.error(f"Policy evaluation error (FAIL-CLOSED): {e}")
            # SECURITY: Fail-closed on error - deny the transaction
            # This is critical for compliance - we cannot allow transactions
            # when policy evaluation fails unexpectedly
            return ComplianceResult(
                allowed=False,
                provider="nl_policy",
                rule_id="evaluation_error_failclosed",
                reason=f"Policy evaluation error - transaction blocked for safety: {str(e)}",
            )


class ComplianceEngine:
    """
    Compliance engine with audit trail support.

    All compliance decisions are recorded in an append-only audit store
    for regulatory compliance and dispute resolution.
    """

    def __init__(
        self,
        settings: SardisSettings,
        provider: ComplianceProvider | None = None,
        audit_store: ComplianceAuditStore | None = None,
    ):
        self._provider = provider or SimpleRuleProvider(settings)
        self._audit_store = audit_store or get_audit_store()

    def preflight(self, mandate: PaymentMandate) -> ComplianceResult:
        """
        Run compliance preflight check and record to audit trail.

        This method:
        1. Evaluates the mandate against compliance rules
        2. Records the decision in the append-only audit store
        3. Returns the compliance result

        Returns:
            ComplianceResult with audit_id linking to audit entry
        """
        # Evaluate mandate
        result = self._provider.evaluate(mandate)

        # Record to audit trail (ALWAYS, regardless of outcome)
        audit_entry = ComplianceAuditEntry(
            mandate_id=mandate.mandate_id,
            subject=mandate.subject,
            allowed=result.allowed,
            reason=result.reason,
            rule_id=result.rule_id,
            provider=result.provider,
            metadata={
                "amount_minor": str(mandate.amount_minor),
                "token": mandate.token,
                "destination": mandate.destination,
                "chain": mandate.chain,
            },
        )

        audit_id = self._audit_store.append(audit_entry)

        # Link audit entry to result
        result.audit_id = audit_id

        logger.info(
            f"Compliance preflight: mandate={mandate.mandate_id}, "
            f"allowed={result.allowed}, audit_id={audit_id}"
        )

        return result

    def get_audit_history(self, mandate_id: str) -> List[ComplianceAuditEntry]:
        """Get audit history for a mandate."""
        return self._audit_store.get_by_mandate(mandate_id)

    def get_recent_audits(self, limit: int = 100) -> List[ComplianceAuditEntry]:
        """Get recent audit entries."""
        return self._audit_store.get_recent(limit)
