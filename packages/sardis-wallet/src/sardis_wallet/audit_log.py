"""
Comprehensive Audit Logging for Sardis Wallets.

Implements tamper-evident audit logging with:
- Immutable log entries with hash chains
- Multiple log levels and categories
- Retention policies
- Search and filtering
- Export capabilities
- Compliance reporting
"""
from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Protocol, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from sardis_v2_core import Wallet, Transaction

logger = logging.getLogger(__name__)


class AuditCategory(str, Enum):
    """Category of audit event."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    TRANSACTION = "transaction"
    POLICY = "policy"
    KEY_MANAGEMENT = "key_management"
    CONFIGURATION = "configuration"
    RECOVERY = "recovery"
    COMPLIANCE = "compliance"
    SECURITY = "security"
    SYSTEM = "system"


class AuditLevel(str, Enum):
    """Severity level of audit event."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditAction(str, Enum):
    """Specific audit actions."""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    MFA_INITIATED = "mfa_initiated"
    MFA_VERIFIED = "mfa_verified"
    MFA_FAILED = "mfa_failed"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    SESSION_REVOKED = "session_revoked"

    # Transactions
    TRANSACTION_INITIATED = "transaction_initiated"
    TRANSACTION_APPROVED = "transaction_approved"
    TRANSACTION_REJECTED = "transaction_rejected"
    TRANSACTION_EXECUTED = "transaction_executed"
    TRANSACTION_FAILED = "transaction_failed"

    # Key Management
    KEY_CREATED = "key_created"
    KEY_ROTATED = "key_rotated"
    KEY_REVOKED = "key_revoked"
    KEY_EXPORTED = "key_exported"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"

    # Policy
    POLICY_CREATED = "policy_created"
    POLICY_UPDATED = "policy_updated"
    POLICY_DELETED = "policy_deleted"
    LIMIT_UPDATED = "limit_updated"
    LIMIT_EXCEEDED = "limit_exceeded"

    # Recovery
    RECOVERY_INITIATED = "recovery_initiated"
    RECOVERY_COMPLETED = "recovery_completed"
    RECOVERY_CANCELLED = "recovery_cancelled"
    GUARDIAN_ADDED = "guardian_added"
    GUARDIAN_REMOVED = "guardian_removed"

    # Security
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    WATCHLIST_HIT = "watchlist_hit"
    IP_BLOCKED = "ip_blocked"
    DEVICE_BLOCKED = "device_blocked"

    # Configuration
    SETTING_CHANGED = "setting_changed"
    SIGNER_ADDED = "signer_added"
    SIGNER_REMOVED = "signer_removed"


@dataclass
class AuditEntry:
    """A single audit log entry."""
    entry_id: str
    timestamp: datetime
    wallet_id: str
    category: AuditCategory
    action: AuditAction
    level: AuditLevel = AuditLevel.INFO

    # Actor information
    actor_id: Optional[str] = None
    actor_type: str = "user"  # "user", "system", "agent", "admin"
    session_id: Optional[str] = None

    # Context
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    user_agent: Optional[str] = None
    geo_location: Optional[str] = None

    # Details
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    old_value: Optional[str] = None  # For changes
    new_value: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    # Result
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # Hash chain for tamper detection
    previous_hash: str = ""
    entry_hash: str = ""

    def compute_hash(self) -> str:
        """Compute hash of this entry."""
        data = {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "wallet_id": self.wallet_id,
            "category": self.category.value,
            "action": self.action.value,
            "actor_id": self.actor_id,
            "resource_id": self.resource_id,
            "success": self.success,
            "previous_hash": self.previous_hash,
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def to_dict(self, include_hash: bool = True) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "wallet_id": self.wallet_id,
            "category": self.category.value,
            "action": self.action.value,
            "level": self.level.value,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "success": self.success,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "details": self.details,
        }

        if include_hash:
            result["entry_hash"] = self.entry_hash

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """Create from dictionary."""
        return cls(
            entry_id=data["entry_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            wallet_id=data["wallet_id"],
            category=AuditCategory(data["category"]),
            action=AuditAction(data["action"]),
            level=AuditLevel(data.get("level", "info")),
            actor_id=data.get("actor_id"),
            actor_type=data.get("actor_type", "user"),
            session_id=data.get("session_id"),
            ip_address=data.get("ip_address"),
            resource_type=data.get("resource_type"),
            resource_id=data.get("resource_id"),
            success=data.get("success", True),
            error_code=data.get("error_code"),
            error_message=data.get("error_message"),
            details=data.get("details", {}),
            previous_hash=data.get("previous_hash", ""),
            entry_hash=data.get("entry_hash", ""),
        )


@dataclass
class AuditQuery:
    """Query parameters for audit log search."""
    wallet_id: Optional[str] = None
    categories: Optional[List[AuditCategory]] = None
    actions: Optional[List[AuditAction]] = None
    levels: Optional[List[AuditLevel]] = None
    actor_id: Optional[str] = None
    resource_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success_only: Optional[bool] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None

    # Pagination
    offset: int = 0
    limit: int = 100

    def matches(self, entry: AuditEntry) -> bool:
        """Check if an entry matches this query."""
        if self.wallet_id and entry.wallet_id != self.wallet_id:
            return False
        if self.categories and entry.category not in self.categories:
            return False
        if self.actions and entry.action not in self.actions:
            return False
        if self.levels and entry.level not in self.levels:
            return False
        if self.actor_id and entry.actor_id != self.actor_id:
            return False
        if self.resource_id and entry.resource_id != self.resource_id:
            return False
        if self.start_time and entry.timestamp < self.start_time:
            return False
        if self.end_time and entry.timestamp > self.end_time:
            return False
        if self.success_only is not None and entry.success != self.success_only:
            return False
        if self.ip_address and entry.ip_address != self.ip_address:
            return False
        if self.session_id and entry.session_id != self.session_id:
            return False
        return True


@dataclass
class AuditStats:
    """Statistics for audit logs."""
    wallet_id: str
    period_start: datetime
    period_end: datetime
    total_entries: int = 0
    entries_by_category: Dict[str, int] = field(default_factory=dict)
    entries_by_action: Dict[str, int] = field(default_factory=dict)
    entries_by_level: Dict[str, int] = field(default_factory=dict)
    success_count: int = 0
    failure_count: int = 0
    unique_actors: int = 0
    unique_sessions: int = 0
    unique_ips: int = 0


@dataclass
class RetentionPolicy:
    """Audit log retention policy."""
    # Retention periods by level
    debug_retention_days: int = 7
    info_retention_days: int = 90
    warning_retention_days: int = 365
    error_retention_days: int = 730  # 2 years
    critical_retention_days: int = 2555  # 7 years

    # Compliance requirements
    min_retention_days: int = 90
    max_retention_days: int = 2555

    # Archive settings
    archive_after_days: int = 90
    compress_archives: bool = True

    def get_retention_days(self, level: AuditLevel) -> int:
        """Get retention days for a level."""
        retention_map = {
            AuditLevel.DEBUG: self.debug_retention_days,
            AuditLevel.INFO: self.info_retention_days,
            AuditLevel.WARNING: self.warning_retention_days,
            AuditLevel.ERROR: self.error_retention_days,
            AuditLevel.CRITICAL: self.critical_retention_days,
        }
        days = retention_map.get(level, self.info_retention_days)
        return max(self.min_retention_days, min(days, self.max_retention_days))


class AuditStorageBackend(Protocol):
    """Protocol for audit log storage backends."""

    async def store(self, entry: AuditEntry) -> bool:
        """Store an audit entry."""
        ...

    async def query(self, query: AuditQuery) -> List[AuditEntry]:
        """Query audit entries."""
        ...

    async def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Get a specific entry."""
        ...

    async def delete_before(self, timestamp: datetime) -> int:
        """Delete entries before timestamp."""
        ...


class InMemoryAuditStorage:
    """In-memory audit storage for testing/development."""

    def __init__(self):
        self._entries: List[AuditEntry] = []
        self._by_wallet: Dict[str, List[int]] = defaultdict(list)
        self._by_id: Dict[str, int] = {}

    async def store(self, entry: AuditEntry) -> bool:
        """Store an audit entry."""
        index = len(self._entries)
        self._entries.append(entry)
        self._by_wallet[entry.wallet_id].append(index)
        self._by_id[entry.entry_id] = index
        return True

    async def query(self, query: AuditQuery) -> List[AuditEntry]:
        """Query audit entries."""
        if query.wallet_id:
            indices = self._by_wallet.get(query.wallet_id, [])
            entries = [self._entries[i] for i in indices]
        else:
            entries = list(self._entries)

        # Filter
        results = [e for e in entries if query.matches(e)]

        # Sort by timestamp descending
        results.sort(key=lambda e: e.timestamp, reverse=True)

        # Paginate
        return results[query.offset:query.offset + query.limit]

    async def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Get a specific entry."""
        index = self._by_id.get(entry_id)
        if index is not None:
            return self._entries[index]
        return None

    async def delete_before(self, timestamp: datetime) -> int:
        """Delete entries before timestamp."""
        # In production, this would actually delete
        # For in-memory, we just count
        count = sum(1 for e in self._entries if e.timestamp < timestamp)
        return count


class AuditLogger:
    """
    Comprehensive audit logging system.

    Features:
    - Tamper-evident hash chains
    - Multiple categories and levels
    - Flexible querying
    - Retention policies
    - Export capabilities
    """

    def __init__(
        self,
        storage: Optional[AuditStorageBackend] = None,
        retention_policy: Optional[RetentionPolicy] = None,
    ):
        self._storage = storage or InMemoryAuditStorage()
        self._retention = retention_policy or RetentionPolicy()

        # Hash chain tracking
        self._last_hash: Dict[str, str] = {}  # wallet_id -> last hash
        self._entry_counter: int = 0

        # Lock for thread safety
        self._lock = asyncio.Lock()

    def _generate_entry_id(self) -> str:
        """Generate a unique entry ID."""
        import secrets
        self._entry_counter += 1
        return f"audit_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(6)}"

    async def log(
        self,
        wallet_id: str,
        category: AuditCategory,
        action: AuditAction,
        level: AuditLevel = AuditLevel.INFO,
        actor_id: Optional[str] = None,
        actor_type: str = "user",
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> AuditEntry:
        """
        Log an audit event.

        Args:
            wallet_id: Wallet identifier
            category: Event category
            action: Specific action
            level: Severity level
            actor_id: Who performed the action
            actor_type: Type of actor
            session_id: Session identifier
            ip_address: Client IP
            device_id: Device identifier
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            old_value: Previous value (for changes)
            new_value: New value (for changes)
            details: Additional details
            success: Whether action succeeded
            error_code: Error code if failed
            error_message: Error message if failed

        Returns:
            Created AuditEntry
        """
        async with self._lock:
            entry_id = self._generate_entry_id()
            timestamp = datetime.now(timezone.utc)

            # Get previous hash for chain
            previous_hash = self._last_hash.get(wallet_id, "genesis")

            entry = AuditEntry(
                entry_id=entry_id,
                timestamp=timestamp,
                wallet_id=wallet_id,
                category=category,
                action=action,
                level=level,
                actor_id=actor_id,
                actor_type=actor_type,
                session_id=session_id,
                ip_address=ip_address,
                device_id=device_id,
                resource_type=resource_type,
                resource_id=resource_id,
                old_value=old_value,
                new_value=new_value,
                details=details or {},
                success=success,
                error_code=error_code,
                error_message=error_message,
                previous_hash=previous_hash,
            )

            # Compute entry hash
            entry.entry_hash = entry.compute_hash()
            self._last_hash[wallet_id] = entry.entry_hash

            # Store
            await self._storage.store(entry)

            # Log to standard logger as well
            log_level = {
                AuditLevel.DEBUG: logging.DEBUG,
                AuditLevel.INFO: logging.INFO,
                AuditLevel.WARNING: logging.WARNING,
                AuditLevel.ERROR: logging.ERROR,
                AuditLevel.CRITICAL: logging.CRITICAL,
            }.get(level, logging.INFO)

            logger.log(
                log_level,
                f"AUDIT [{category.value}] {action.value} - wallet:{wallet_id} actor:{actor_id} success:{success}",
            )

            return entry

    async def log_transaction(
        self,
        wallet_id: str,
        action: AuditAction,
        tx_hash: Optional[str] = None,
        amount: Optional[str] = None,
        token: Optional[str] = None,
        to_address: Optional[str] = None,
        **kwargs,
    ) -> AuditEntry:
        """Convenience method for logging transactions."""
        details = {
            "tx_hash": tx_hash,
            "amount": amount,
            "token": token,
            "to_address": to_address,
        }
        details = {k: v for k, v in details.items() if v is not None}

        return await self.log(
            wallet_id=wallet_id,
            category=AuditCategory.TRANSACTION,
            action=action,
            resource_type="transaction",
            resource_id=tx_hash,
            details=details,
            **kwargs,
        )

    async def log_security_event(
        self,
        wallet_id: str,
        action: AuditAction,
        threat_level: str = "medium",
        **kwargs,
    ) -> AuditEntry:
        """Convenience method for logging security events."""
        level = {
            "low": AuditLevel.WARNING,
            "medium": AuditLevel.ERROR,
            "high": AuditLevel.CRITICAL,
            "critical": AuditLevel.CRITICAL,
        }.get(threat_level, AuditLevel.WARNING)

        details = kwargs.pop("details", {})
        details["threat_level"] = threat_level

        return await self.log(
            wallet_id=wallet_id,
            category=AuditCategory.SECURITY,
            action=action,
            level=level,
            details=details,
            **kwargs,
        )

    async def log_auth_event(
        self,
        wallet_id: str,
        action: AuditAction,
        method: Optional[str] = None,
        **kwargs,
    ) -> AuditEntry:
        """Convenience method for logging authentication events."""
        details = kwargs.pop("details", {})
        if method:
            details["auth_method"] = method

        level = AuditLevel.INFO if kwargs.get("success", True) else AuditLevel.WARNING

        return await self.log(
            wallet_id=wallet_id,
            category=AuditCategory.AUTHENTICATION,
            action=action,
            level=level,
            details=details,
            **kwargs,
        )

    async def query(self, query: AuditQuery) -> List[Dict[str, Any]]:
        """
        Query audit logs.

        Args:
            query: Query parameters

        Returns:
            List of matching entries as dictionaries
        """
        entries = await self._storage.query(query)
        return [e.to_dict() for e in entries]

    async def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific audit entry."""
        entry = await self._storage.get_entry(entry_id)
        return entry.to_dict() if entry else None

    async def verify_chain(self, wallet_id: str) -> Tuple[bool, List[str]]:
        """
        Verify the hash chain integrity for a wallet.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        query = AuditQuery(wallet_id=wallet_id, limit=10000)
        entries = await self._storage.query(query)

        # Sort by timestamp ascending
        entries.sort(key=lambda e: e.timestamp)

        errors = []
        expected_previous = "genesis"

        for entry in entries:
            # Check previous hash
            if entry.previous_hash != expected_previous:
                errors.append(
                    f"Entry {entry.entry_id}: previous hash mismatch "
                    f"(expected {expected_previous[:8]}..., got {entry.previous_hash[:8]}...)"
                )

            # Verify entry hash
            computed_hash = entry.compute_hash()
            if entry.entry_hash != computed_hash:
                errors.append(
                    f"Entry {entry.entry_id}: hash verification failed "
                    f"(stored {entry.entry_hash[:8]}..., computed {computed_hash[:8]}...)"
                )

            expected_previous = entry.entry_hash

        return len(errors) == 0, errors

    async def get_stats(
        self,
        wallet_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> AuditStats:
        """Get statistics for audit logs."""
        if not start_time:
            start_time = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_time:
            end_time = datetime.now(timezone.utc)

        query = AuditQuery(
            wallet_id=wallet_id,
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )
        entries = await self._storage.query(query)

        stats = AuditStats(
            wallet_id=wallet_id,
            period_start=start_time,
            period_end=end_time,
            total_entries=len(entries),
        )

        actors = set()
        sessions = set()
        ips = set()

        for entry in entries:
            # Count by category
            cat = entry.category.value
            stats.entries_by_category[cat] = stats.entries_by_category.get(cat, 0) + 1

            # Count by action
            act = entry.action.value
            stats.entries_by_action[act] = stats.entries_by_action.get(act, 0) + 1

            # Count by level
            lvl = entry.level.value
            stats.entries_by_level[lvl] = stats.entries_by_level.get(lvl, 0) + 1

            # Count success/failure
            if entry.success:
                stats.success_count += 1
            else:
                stats.failure_count += 1

            # Track unique values
            if entry.actor_id:
                actors.add(entry.actor_id)
            if entry.session_id:
                sessions.add(entry.session_id)
            if entry.ip_address:
                ips.add(entry.ip_address)

        stats.unique_actors = len(actors)
        stats.unique_sessions = len(sessions)
        stats.unique_ips = len(ips)

        return stats

    async def export(
        self,
        wallet_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        format: str = "json",
        compress: bool = False,
    ) -> bytes:
        """
        Export audit logs.

        Args:
            wallet_id: Wallet identifier
            start_time: Start of export period
            end_time: End of export period
            format: Export format ("json", "csv")
            compress: Whether to gzip the output

        Returns:
            Exported data as bytes
        """
        query = AuditQuery(
            wallet_id=wallet_id,
            start_time=start_time,
            end_time=end_time,
            limit=100000,
        )
        entries = await self._storage.query(query)

        if format == "json":
            data = json.dumps(
                [e.to_dict() for e in entries],
                indent=2,
                default=str,
            ).encode("utf-8")

        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            if entries:
                writer = csv.DictWriter(output, fieldnames=entries[0].to_dict().keys())
                writer.writeheader()
                for entry in entries:
                    writer.writerow(entry.to_dict())
            data = output.getvalue().encode("utf-8")

        else:
            raise ValueError(f"Unsupported format: {format}")

        if compress:
            data = gzip.compress(data)

        return data

    async def cleanup_old_entries(self) -> int:
        """
        Clean up entries based on retention policy.

        Returns:
            Number of entries deleted
        """
        now = datetime.now(timezone.utc)
        total_deleted = 0

        for level in AuditLevel:
            retention_days = self._retention.get_retention_days(level)
            cutoff = now - timedelta(days=retention_days)

            # Query and delete entries for this level
            # In production, this would be done more efficiently
            deleted = await self._storage.delete_before(cutoff)
            total_deleted += deleted

        logger.info(f"Audit cleanup: deleted {total_deleted} old entries")
        return total_deleted


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger

    if _audit_logger is None:
        _audit_logger = AuditLogger()

    return _audit_logger


__all__ = [
    "AuditCategory",
    "AuditLevel",
    "AuditAction",
    "AuditEntry",
    "AuditQuery",
    "AuditStats",
    "RetentionPolicy",
    "AuditLogger",
    "get_audit_logger",
]
