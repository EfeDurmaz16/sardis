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

    In production, this would be backed by a database with:
    - Write-ahead logging for durability
    - No DELETE capability
    - Cryptographic integrity checks

    For now, uses in-memory storage with bounded size.
    """

    # Maximum entries to keep in memory (older entries should be persisted to DB)
    MAX_ENTRIES = 100_000

    def __init__(self):
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


# Global audit store singleton
_audit_store: Optional[ComplianceAuditStore] = None


def get_audit_store() -> ComplianceAuditStore:
    """Get the global audit store singleton."""
    global _audit_store
    if _audit_store is None:
        _audit_store = ComplianceAuditStore()
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
