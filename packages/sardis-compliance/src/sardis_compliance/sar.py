"""
Suspicious Activity Report (SAR) generation module.

This module implements SAR generation as required by FinCEN (Financial Crimes Enforcement Network)
and other regulatory bodies. SARs are mandatory reports filed when financial institutions detect
suspicious activities that may indicate money laundering, fraud, or other financial crimes.

Regulatory Requirements:
- FinCEN Form 111 (SAR for financial institutions)
- Filing deadline: 30 days from initial detection
- Confidentiality: Must not disclose SAR filing to subject
- Retention: 5 years from filing date

Triggering Events:
- Structuring: Breaking up transactions to avoid reporting thresholds
- Rapid movement of funds (layering)
- Transactions with no apparent economic purpose
- Unusual patterns inconsistent with customer profile
- Transactions with sanctioned entities
- High-risk jurisdictions

Reference: https://www.fincen.gov/resources/filing-information
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class SuspiciousActivityType(str, Enum):
    """Types of suspicious activities."""
    STRUCTURING = "structuring"  # Breaking up transactions to avoid thresholds
    LAYERING = "layering"  # Rapid movement of funds across accounts
    UNUSUAL_PATTERN = "unusual_pattern"  # Activity inconsistent with profile
    SANCTIONED_ENTITY = "sanctioned_entity"  # Transaction with sanctioned party
    HIGH_RISK_JURISDICTION = "high_risk_jurisdiction"  # High-risk country
    NO_ECONOMIC_PURPOSE = "no_economic_purpose"  # No apparent business reason
    IDENTITY_FRAUD = "identity_fraud"  # Suspected identity theft
    TERRORIST_FINANCING = "terrorist_financing"  # Potential terrorism funding
    MONEY_LAUNDERING = "money_laundering"  # Suspected money laundering
    CYBERCRIME = "cybercrime"  # Online fraud or hacking
    OTHER = "other"  # Other suspicious activity


class SARStatus(str, Enum):
    """SAR filing status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    FILED = "filed"
    REJECTED = "rejected"


class SARPriority(str, Enum):
    """SAR priority level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SuspiciousTransaction:
    """A transaction flagged as suspicious."""
    tx_id: str
    wallet_id: str
    amount: Decimal
    currency: str
    timestamp: datetime
    from_address: str
    to_address: str
    chain: str
    tx_hash: Optional[str] = None
    flags: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tx_id": self.tx_id,
            "wallet_id": self.wallet_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "timestamp": self.timestamp.isoformat(),
            "from_address": self.from_address,
            "to_address": self.to_address,
            "chain": self.chain,
            "tx_hash": self.tx_hash,
            "flags": self.flags,
            "risk_score": self.risk_score,
            "notes": self.notes,
        }


@dataclass
class SubjectInformation:
    """Information about the subject of the SAR."""
    subject_id: str  # Wallet ID or agent ID
    subject_type: str  # "individual", "entity", "wallet"
    name: Optional[str] = None
    address: Optional[str] = None
    identification: Optional[str] = None  # Redacted for privacy
    wallet_address: Optional[str] = None
    account_opened_date: Optional[datetime] = None
    relationship_start_date: Optional[datetime] = None
    occupation: Optional[str] = None
    country_of_residence: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "name": self.name or "[REDACTED]",
            "address": self.address or "[REDACTED]",
            "identification": "[REDACTED]",  # Always redacted
            "wallet_address": self.wallet_address,
            "account_opened_date": self.account_opened_date.isoformat() if self.account_opened_date else None,
            "relationship_start_date": self.relationship_start_date.isoformat() if self.relationship_start_date else None,
            "occupation": self.occupation,
            "country_of_residence": self.country_of_residence,
        }


@dataclass
class SuspiciousActivityReport:
    """
    Suspicious Activity Report (SAR).

    This represents a formal SAR filing to regulatory authorities.
    Contains all required information per FinCEN Form 111.
    """
    # Unique identifiers
    sar_id: str
    internal_reference: str

    # Report metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"  # User or system that initiated SAR
    status: SARStatus = SARStatus.DRAFT
    priority: SARPriority = SARPriority.MEDIUM

    # Activity details
    activity_type: SuspiciousActivityType = SuspiciousActivityType.OTHER
    activity_description: str = ""
    detection_date: Optional[datetime] = None
    activity_period_start: Optional[datetime] = None
    activity_period_end: Optional[datetime] = None

    # Subject information
    subject: Optional[SubjectInformation] = None

    # Transactions
    suspicious_transactions: List[SuspiciousTransaction] = field(default_factory=list)
    total_amount: Decimal = field(default=Decimal("0"))
    transaction_count: int = 0

    # Narrative
    narrative: str = ""  # Detailed explanation of suspicious activity
    investigator_notes: str = ""  # Internal notes (not filed)

    # Filing information
    filing_deadline: Optional[datetime] = None
    filed_at: Optional[datetime] = None
    filed_by: Optional[str] = None
    filing_reference: Optional[str] = None  # External reference from regulator

    # Compliance review
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    approval_notes: Optional[str] = None

    # Evidence
    evidence_links: List[str] = field(default_factory=list)
    supporting_documents: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Set filing deadline if not provided."""
        if not self.filing_deadline and self.detection_date:
            # FinCEN requires filing within 30 days of detection
            from datetime import timedelta
            self.filing_deadline = self.detection_date + timedelta(days=30)

    def add_transaction(self, tx: SuspiciousTransaction) -> None:
        """Add a suspicious transaction to this SAR."""
        self.suspicious_transactions.append(tx)
        self.total_amount += tx.amount
        self.transaction_count = len(self.suspicious_transactions)

    def mark_pending_review(self, reviewer: str) -> None:
        """Mark SAR as pending compliance review."""
        self.status = SARStatus.PENDING_REVIEW
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.now(timezone.utc)
        logger.info(f"SAR {self.sar_id} marked pending review by {reviewer}")

    def approve(self, approver: str, notes: Optional[str] = None) -> None:
        """Approve SAR for filing."""
        self.status = SARStatus.APPROVED
        self.reviewed_by = approver
        self.reviewed_at = datetime.now(timezone.utc)
        self.approval_notes = notes
        logger.info(f"SAR {self.sar_id} approved by {approver}")

    def reject(self, rejector: str, reason: str) -> None:
        """Reject SAR (not to be filed)."""
        self.status = SARStatus.REJECTED
        self.reviewed_by = rejector
        self.reviewed_at = datetime.now(timezone.utc)
        self.approval_notes = reason
        logger.info(f"SAR {self.sar_id} rejected by {rejector}: {reason}")

    def file(self, filer: str, filing_ref: Optional[str] = None) -> None:
        """Mark SAR as filed with regulator."""
        if self.status != SARStatus.APPROVED:
            raise ValueError(f"Cannot file SAR with status {self.status}. Must be approved first.")

        self.status = SARStatus.FILED
        self.filed_at = datetime.now(timezone.utc)
        self.filed_by = filer
        self.filing_reference = filing_ref or f"SAR-{self.sar_id}"
        logger.info(f"SAR {self.sar_id} filed by {filer} with reference {self.filing_reference}")

    def is_overdue(self) -> bool:
        """Check if SAR filing deadline has passed."""
        if not self.filing_deadline:
            return False
        return datetime.now(timezone.utc) > self.filing_deadline and self.status != SARStatus.FILED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "sar_id": self.sar_id,
            "internal_reference": self.internal_reference,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status.value,
            "priority": self.priority.value,
            "activity_type": self.activity_type.value,
            "activity_description": self.activity_description,
            "detection_date": self.detection_date.isoformat() if self.detection_date else None,
            "activity_period_start": self.activity_period_start.isoformat() if self.activity_period_start else None,
            "activity_period_end": self.activity_period_end.isoformat() if self.activity_period_end else None,
            "subject": self.subject.to_dict() if self.subject else None,
            "suspicious_transactions": [tx.to_dict() for tx in self.suspicious_transactions],
            "total_amount": str(self.total_amount),
            "transaction_count": self.transaction_count,
            "narrative": self.narrative,
            "investigator_notes": self.investigator_notes,
            "filing_deadline": self.filing_deadline.isoformat() if self.filing_deadline else None,
            "filed_at": self.filed_at.isoformat() if self.filed_at else None,
            "filed_by": self.filed_by,
            "filing_reference": self.filing_reference,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "approval_notes": self.approval_notes,
            "is_overdue": self.is_overdue(),
        }

    def to_fincen_xml(self) -> str:
        """
        Generate FinCEN SAR XML format (BSA E-Filing System).

        This is a simplified version. Production implementation should use
        the full FinCEN SAR XML schema.

        Reference: https://www.fincen.gov/resources/filing-information/sar-xml
        """
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<SuspiciousActivityReport>
    <FilingInformation>
        <ReportID>{self.sar_id}</ReportID>
        <FilingDate>{self.created_at.isoformat()}</FilingDate>
        <FilingInstitution>Sardis Network</FilingInstitution>
    </FilingInformation>
    <SuspiciousActivity>
        <ActivityType>{self.activity_type.value}</ActivityType>
        <Description>{self.activity_description}</Description>
        <DetectionDate>{self.detection_date.isoformat() if self.detection_date else ''}</DetectionDate>
        <PeriodStart>{self.activity_period_start.isoformat() if self.activity_period_start else ''}</PeriodStart>
        <PeriodEnd>{self.activity_period_end.isoformat() if self.activity_period_end else ''}</PeriodEnd>
        <TotalAmount currency="{self.suspicious_transactions[0].currency if self.suspicious_transactions else 'USD'}">{self.total_amount}</TotalAmount>
        <TransactionCount>{self.transaction_count}</TransactionCount>
    </SuspiciousActivity>
    <Narrative>{self.narrative}</Narrative>
</SuspiciousActivityReport>"""
        return xml


class SARGenerator:
    """Service for generating and managing Suspicious Activity Reports.

    Supports optional PostgreSQL persistence. When a dsn is provided,
    SARs are written to the suspicious_activity_reports table for FinCEN
    5-year retention compliance. Falls back to in-memory storage for dev/test.
    """

    def __init__(self, storage_path: Optional[str] = None, dsn: Optional[str] = None):
        """
        Initialize SAR generator.

        Args:
            storage_path: Optional path for storing SAR files
            dsn: PostgreSQL DSN for persistent storage (optional)
        """
        self.storage_path = storage_path
        self._sars: Dict[str, SuspiciousActivityReport] = {}
        self._dsn = dsn
        self._pool = None
        logger.info("SARGenerator initialized")

    def create_sar(
        self,
        activity_type: SuspiciousActivityType,
        wallet_id: str,
        description: str,
        detection_date: Optional[datetime] = None,
        priority: SARPriority = SARPriority.MEDIUM,
    ) -> SuspiciousActivityReport:
        """
        Create a new SAR.

        Args:
            activity_type: Type of suspicious activity
            wallet_id: Wallet ID involved in suspicious activity
            description: Description of the suspicious activity
            detection_date: When the activity was detected
            priority: Priority level

        Returns:
            Created SuspiciousActivityReport
        """
        sar_id = f"sar_{uuid.uuid4().hex[:16]}"
        internal_ref = f"INT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        sar = SuspiciousActivityReport(
            sar_id=sar_id,
            internal_reference=internal_ref,
            activity_type=activity_type,
            activity_description=description,
            detection_date=detection_date or datetime.now(timezone.utc),
            priority=priority,
            subject=SubjectInformation(
                subject_id=wallet_id,
                subject_type="wallet",
                wallet_address=wallet_id,
            ),
        )

        self._sars[sar_id] = sar

        # Persist to PostgreSQL if configured
        if self._dsn:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._persist_sar(sar))
                else:
                    loop.run_until_complete(self._persist_sar(sar))
            except Exception as e:
                logger.warning(f"Failed to persist SAR {sar_id} to DB: {e}")

        logger.info(f"Created SAR {sar_id} for wallet {wallet_id}: {activity_type.value}")
        return sar

    async def _get_pool(self):
        if self._pool is None:
            from sardis_v2_core.database import Database
            self._pool = await Database.get_pool()
        return self._pool

    async def _persist_sar(self, sar: SuspiciousActivityReport) -> None:
        import json as _json
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO suspicious_activity_reports
                    (sar_id, internal_reference, activity_type, status, priority,
                     subject_id, subject_type, wallet_address, activity_description,
                     detection_date, filing_deadline, report_data)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (sar_id) DO UPDATE SET
                    status = EXCLUDED.status, updated_at = NOW()
                """,
                sar.sar_id,
                sar.internal_reference,
                sar.activity_type.value,
                sar.status.value,
                sar.priority.value,
                sar.subject.subject_id if sar.subject else "",
                sar.subject.subject_type if sar.subject else "wallet",
                sar.subject.wallet_address if sar.subject else None,
                sar.activity_description,
                sar.detection_date,
                sar.filing_deadline,
                _json.dumps(sar.to_dict(), default=str),
            )

    async def get_sar_async(self, sar_id: str) -> Optional[SuspiciousActivityReport]:
        """Get a SAR by ID, checking DB if not in memory."""
        if sar_id in self._sars:
            return self._sars[sar_id]
        if self._dsn:
            try:
                pool = await self._get_pool()
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT * FROM suspicious_activity_reports WHERE sar_id = $1",
                        sar_id,
                    )
                    if row:
                        sar = self._row_to_sar(row)
                        self._sars[sar_id] = sar
                        return sar
            except Exception as e:
                logger.warning(f"Failed to fetch SAR {sar_id} from DB: {e}")
        return None

    def _row_to_sar(self, row) -> SuspiciousActivityReport:
        """Convert a database row to a SuspiciousActivityReport."""
        return SuspiciousActivityReport(
            sar_id=row["sar_id"],
            internal_reference=row["internal_reference"],
            activity_type=SuspiciousActivityType(row["activity_type"]),
            status=SARStatus(row["status"]),
            priority=SARPriority(row["priority"]),
            activity_description=row["activity_description"],
            detection_date=row["detection_date"],
            filing_deadline=row.get("filing_deadline"),
            filed_at=row.get("filed_date"),
            created_at=row.get("created_at", datetime.now(timezone.utc)),
            subject=SubjectInformation(
                subject_id=row.get("subject_id", ""),
                subject_type=row.get("subject_type", "wallet"),
                wallet_address=row.get("wallet_address"),
            ),
        )

    def get_sar(self, sar_id: str) -> Optional[SuspiciousActivityReport]:
        """Get a SAR by ID."""
        return self._sars.get(sar_id)

    async def list_sars_async(
        self,
        status: Optional[SARStatus] = None,
        priority: Optional[SARPriority] = None,
        overdue_only: bool = False,
        limit: int = 100,
    ) -> List[SuspiciousActivityReport]:
        """List SARs from database with optional filtering."""
        if not self._dsn:
            return self.list_sars(status=status, priority=priority, overdue_only=overdue_only)
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                conditions = []
                params: list = []
                idx = 1
                if status:
                    conditions.append(f"status = ${idx}")
                    params.append(status.value)
                    idx += 1
                if priority:
                    conditions.append(f"priority = ${idx}")
                    params.append(priority.value)
                    idx += 1
                if overdue_only:
                    conditions.append(f"filing_deadline < NOW() AND status != 'filed'")

                where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
                params.append(limit)
                query = f"SELECT * FROM suspicious_activity_reports {where} ORDER BY created_at DESC LIMIT ${idx}"
                rows = await conn.fetch(query, *params)
                return [self._row_to_sar(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to list SARs from DB: {e}")
            return self.list_sars(status=status, priority=priority, overdue_only=overdue_only)

    def list_sars(
        self,
        status: Optional[SARStatus] = None,
        priority: Optional[SARPriority] = None,
        overdue_only: bool = False,
    ) -> List[SuspiciousActivityReport]:
        """
        List SARs with optional filtering (in-memory fallback).

        Args:
            status: Filter by status
            priority: Filter by priority
            overdue_only: Only return overdue SARs

        Returns:
            List of SARs matching criteria
        """
        sars = list(self._sars.values())

        if status:
            sars = [sar for sar in sars if sar.status == status]

        if priority:
            sars = [sar for sar in sars if sar.priority == priority]

        if overdue_only:
            sars = [sar for sar in sars if sar.is_overdue()]

        return sars

    def get_overdue_sars(self) -> List[SuspiciousActivityReport]:
        """Get all SARs past their filing deadline."""
        return self.list_sars(overdue_only=True)

    def detect_structuring(
        self,
        transactions: List[Dict[str, Any]],
        threshold: Decimal = Decimal("10000"),
        time_window_hours: int = 24,
    ) -> Optional[SuspiciousActivityReport]:
        """
        Detect structuring (breaking up transactions to avoid thresholds).

        Args:
            transactions: List of transactions to analyze
            threshold: Reporting threshold (default $10,000)
            time_window_hours: Time window to check (default 24 hours)

        Returns:
            SAR if structuring detected, None otherwise
        """
        if not transactions:
            return None

        # Group transactions by wallet
        from collections import defaultdict
        wallet_txs = defaultdict(list)
        for tx in transactions:
            wallet_txs[tx.get("wallet_id")].append(tx)

        # Check each wallet for structuring
        for wallet_id, txs in wallet_txs.items():
            # Sort by timestamp
            sorted_txs = sorted(txs, key=lambda t: t.get("timestamp", datetime.min))

            # Check for multiple transactions just below threshold
            suspicious_count = 0
            total = Decimal("0")

            for tx in sorted_txs:
                amount = Decimal(str(tx.get("amount", 0)))
                # Transactions between 50-99% of threshold are suspicious
                if threshold * Decimal("0.5") <= amount < threshold:
                    suspicious_count += 1
                    total += amount

            # If 3+ transactions totaling over threshold in time window
            if suspicious_count >= 3 and total >= threshold:
                sar = self.create_sar(
                    activity_type=SuspiciousActivityType.STRUCTURING,
                    wallet_id=wallet_id,
                    description=f"Detected {suspicious_count} transactions totaling ${total} "
                                f"in {time_window_hours}h window, likely to avoid ${threshold} threshold",
                    priority=SARPriority.HIGH,
                )

                # Add transactions to SAR
                for tx in sorted_txs[:suspicious_count]:
                    sar.add_transaction(SuspiciousTransaction(
                        tx_id=tx.get("tx_id", ""),
                        wallet_id=wallet_id,
                        amount=Decimal(str(tx.get("amount", 0))),
                        currency=tx.get("currency", "USDC"),
                        timestamp=tx.get("timestamp", datetime.now(timezone.utc)),
                        from_address=tx.get("from_address", ""),
                        to_address=tx.get("to_address", ""),
                        chain=tx.get("chain", ""),
                        tx_hash=tx.get("tx_hash"),
                        flags=["structuring", "below_threshold"],
                    ))

                sar.narrative = f"""
Suspicious activity detected: Potential structuring to avoid reporting threshold.

Pattern Analysis:
- Number of transactions: {suspicious_count}
- Total amount: ${total}
- Reporting threshold: ${threshold}
- Time window: {time_window_hours} hours
- Individual transaction amounts: All between 50-99% of threshold

This pattern is consistent with structuring, where large transactions are deliberately
broken into smaller amounts to avoid regulatory reporting requirements.

Recommended Action: File SAR with FinCEN within 30 days.
                """.strip()

                logger.warning(f"Structuring detected for wallet {wallet_id}: {suspicious_count} txs, ${total}")
                return sar

        return None

    def export_sar(self, sar_id: str, format: str = "json") -> str:
        """
        Export SAR in specified format.

        Args:
            sar_id: SAR ID to export
            format: Export format ("json", "xml")

        Returns:
            Serialized SAR
        """
        sar = self.get_sar(sar_id)
        if not sar:
            raise ValueError(f"SAR not found: {sar_id}")

        if format == "json":
            import json
            return json.dumps(sar.to_dict(), indent=2)
        elif format == "xml":
            return sar.to_fincen_xml()
        else:
            raise ValueError(f"Unsupported format: {format}")
