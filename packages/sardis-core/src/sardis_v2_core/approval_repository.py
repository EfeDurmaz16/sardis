"""Approval repository for PostgreSQL CRUD operations."""
from __future__ import annotations

import secrets
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Literal
from dataclasses import dataclass, field

from .database import Database


ApprovalStatus = Literal['pending', 'approved', 'denied', 'expired', 'cancelled']
ApprovalUrgency = Literal['low', 'medium', 'high']


@dataclass
class Approval:
    """Approval request model matching PostgreSQL schema."""

    # Primary key
    id: str

    # Core fields
    action: str
    status: ApprovalStatus
    urgency: ApprovalUrgency
    requested_by: str

    # Timestamps
    created_at: datetime
    expires_at: datetime
    reviewed_at: Optional[datetime] = None

    # Optional fields
    reviewed_by: Optional[str] = None
    vendor: Optional[str] = None
    amount: Optional[Decimal] = None
    purpose: Optional[str] = None
    reason: Optional[str] = None
    card_limit: Optional[Decimal] = None

    # Foreign keys (soft references)
    agent_id: Optional[str] = None
    wallet_id: Optional[str] = None
    organization_id: Optional[str] = None

    # Metadata
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def generate_id() -> str:
        """Generate approval ID: appr_<timestamp_base36>_<random>."""
        timestamp = int(time.time())
        timestamp_b36 = _to_base36(timestamp)
        random_suffix = secrets.token_hex(4)
        return f"appr_{timestamp_b36}_{random_suffix}"


class ApprovalRepository:
    """PostgreSQL repository for approval CRUD operations."""

    def __init__(self, dsn: str = "memory://"):
        """Initialize approval repository.

        Args:
            dsn: Database connection string (postgresql:// or memory://)
        """
        self.dsn = dsn
        # Note: For production, use actual database connection pool
        # For now, we'll rely on the Database singleton

    async def create(
        self,
        *,
        action: str,
        status: ApprovalStatus = 'pending',
        urgency: ApprovalUrgency = 'medium',
        requested_by: str,
        created_at: Optional[datetime] = None,
        expires_at: datetime,
        vendor: Optional[str] = None,
        amount: Optional[Decimal] = None,
        purpose: Optional[str] = None,
        reason: Optional[str] = None,
        card_limit: Optional[Decimal] = None,
        agent_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Approval:
        """Create a new approval request (alternative signature).

        This overload accepts individual fields instead of an Approval object.
        """
        if created_at is None:
            created_at = datetime.now(timezone.utc)

        approval = Approval(
            id=Approval.generate_id(),
            action=action,
            status=status,
            urgency=urgency,
            requested_by=requested_by,
            created_at=created_at,
            expires_at=expires_at,
            vendor=vendor,
            amount=amount,
            purpose=purpose,
            reason=reason,
            card_limit=card_limit,
            agent_id=agent_id,
            wallet_id=wallet_id,
            organization_id=organization_id,
            metadata=metadata or {},
        )
        return await self._create_approval(approval)

    async def _create_approval(self, approval: Approval) -> Approval:
        """Create a new approval request.

        Args:
            approval: Approval object to create

        Returns:
            Created Approval object
        """
        query = """
            INSERT INTO approvals (
                id, action, status, urgency, requested_by,
                created_at, expires_at, vendor, amount, purpose,
                reason, card_limit, agent_id, wallet_id,
                organization_id, metadata
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8, $9, $10,
                $11, $12, $13, $14,
                $15, $16
            )
        """

        await Database.execute(
            query,
            approval.id, approval.action, approval.status, approval.urgency,
            approval.requested_by, approval.created_at, approval.expires_at,
            approval.vendor, approval.amount, approval.purpose, approval.reason,
            approval.card_limit, approval.agent_id, approval.wallet_id,
            approval.organization_id, approval.metadata or {}
        )

        return approval

    async def get(self, approval_id: str) -> Optional[Approval]:
        """Get approval by ID.

        Args:
            approval_id: Approval ID

        Returns:
            Approval object or None if not found
        """
        query = """
            SELECT id, action, status, urgency, requested_by, reviewed_by,
                   created_at, reviewed_at, expires_at, vendor, amount,
                   purpose, reason, card_limit, agent_id, wallet_id,
                   organization_id, metadata
            FROM approvals
            WHERE id = $1
        """

        row = await Database.fetchrow(query, approval_id)
        if not row:
            return None

        return _row_to_approval(row)

    async def update(
        self,
        approval_id: str,
        *,
        status: Optional[ApprovalStatus] = None,
        reviewed_by: Optional[str] = None,
        reviewed_at: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[Approval]:
        """Update approval with new state.

        Args:
            approval_id: Approval ID to update
            status: New status (optional)
            reviewed_by: Reviewer email/ID (optional)
            reviewed_at: Review timestamp (optional)
            metadata: Updated metadata (optional)

        Returns:
            Updated Approval or None if not found
        """
        # Get current approval first
        current = await self.get(approval_id)
        if not current:
            return None

        # Build update query dynamically based on provided fields
        updates = []
        values = []
        param_idx = 1

        if status is not None:
            updates.append(f"status = ${param_idx}")
            values.append(status)
            param_idx += 1

        if reviewed_by is not None:
            updates.append(f"reviewed_by = ${param_idx}")
            values.append(reviewed_by)
            param_idx += 1

        if reviewed_at is not None:
            updates.append(f"reviewed_at = ${param_idx}")
            values.append(reviewed_at)
            param_idx += 1

        if metadata is not None:
            updates.append(f"metadata = ${param_idx}")
            values.append(metadata)
            param_idx += 1

        if not updates:
            return current  # No updates requested

        values.append(approval_id)

        query = f"""
            UPDATE approvals
            SET {', '.join(updates)}
            WHERE id = ${param_idx}
            RETURNING id, action, status, urgency, requested_by, reviewed_by,
                      created_at, reviewed_at, expires_at, vendor, amount,
                      purpose, reason, card_limit, agent_id, wallet_id,
                      organization_id, metadata
        """

        row = await Database.fetchrow(query, *values)

        if not row:
            return None

        return _row_to_approval(row)

    async def list(
        self,
        *,
        status: Optional[ApprovalStatus] = None,
        action: Optional[str] = None,
        agent_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        requested_by: Optional[str] = None,
        urgency: Optional[ApprovalUrgency] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Approval]:
        """List approvals with optional filters.

        Args:
            status: Filter by status
            action: Filter by action type
            agent_id: Filter by agent ID
            wallet_id: Filter by wallet ID
            organization_id: Filter by organization ID
            requested_by: Filter by requester
            urgency: Filter by urgency level
            limit: Max results to return
            offset: Pagination offset

        Returns:
            List of Approval objects
        """
        conditions = []
        values = []
        param_idx = 1

        if status is not None:
            conditions.append(f"status = ${param_idx}")
            values.append(status)
            param_idx += 1

        if action is not None:
            conditions.append(f"action = ${param_idx}")
            values.append(action)
            param_idx += 1

        if agent_id is not None:
            conditions.append(f"agent_id = ${param_idx}")
            values.append(agent_id)
            param_idx += 1

        if wallet_id is not None:
            conditions.append(f"wallet_id = ${param_idx}")
            values.append(wallet_id)
            param_idx += 1

        if organization_id is not None:
            conditions.append(f"organization_id = ${param_idx}")
            values.append(organization_id)
            param_idx += 1

        if requested_by is not None:
            conditions.append(f"requested_by = ${param_idx}")
            values.append(requested_by)
            param_idx += 1

        if urgency is not None:
            conditions.append(f"urgency = ${param_idx}")
            values.append(urgency)
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Add limit and offset
        values.append(limit)
        limit_param = f"${param_idx}"
        param_idx += 1

        values.append(offset)
        offset_param = f"${param_idx}"

        query = f"""
            SELECT id, action, status, urgency, requested_by, reviewed_by,
                   created_at, reviewed_at, expires_at, vendor, amount,
                   purpose, reason, card_limit, agent_id, wallet_id,
                   organization_id, metadata
            FROM approvals
            {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit_param} OFFSET {offset_param}
        """

        rows = await Database.fetch(query, *values)
        return [_row_to_approval(row) for row in rows]

    async def get_expired_pending(self, as_of: Optional[datetime] = None) -> List[Approval]:
        """Get all pending approvals that have expired.

        Args:
            as_of: Check expiry as of this timestamp (default: now)

        Returns:
            List of expired pending approvals
        """
        if as_of is None:
            as_of = datetime.now(timezone.utc)

        query = """
            SELECT id, action, status, urgency, requested_by, reviewed_by,
                   created_at, reviewed_at, expires_at, vendor, amount,
                   purpose, reason, card_limit, agent_id, wallet_id,
                   organization_id, metadata
            FROM approvals
            WHERE status = 'pending' AND expires_at < $1
            ORDER BY expires_at ASC
        """

        rows = await Database.fetch(query, as_of)
        return [_row_to_approval(row) for row in rows]


def _row_to_approval(row) -> Approval:
    """Convert database row to Approval object."""
    return Approval(
        id=row['id'],
        action=row['action'],
        status=row['status'],
        urgency=row['urgency'],
        requested_by=row['requested_by'],
        reviewed_by=row['reviewed_by'],
        created_at=row['created_at'],
        reviewed_at=row['reviewed_at'],
        expires_at=row['expires_at'],
        vendor=row['vendor'],
        amount=row['amount'],
        purpose=row['purpose'],
        reason=row['reason'],
        card_limit=row['card_limit'],
        agent_id=row['agent_id'],
        wallet_id=row['wallet_id'],
        organization_id=row['organization_id'],
        metadata=row['metadata'] or {},
    )


def _to_base36(num: int) -> str:
    """Convert integer to base36 string."""
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if num == 0:
        return "0"
    result = []
    while num:
        num, remainder = divmod(num, 36)
        result.append(chars[remainder])
    return ''.join(reversed(result))
