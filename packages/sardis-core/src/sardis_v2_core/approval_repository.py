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

    async def create(
        self,
        *,
        action: str,
        requested_by: str,
        expires_at: datetime,
        urgency: ApprovalUrgency = 'medium',
        status: ApprovalStatus = 'pending',
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
        """Create a new approval request.

        Args:
            action: Type of action requiring approval (payment, create_card, etc.)
            requested_by: Agent ID who requested approval
            expires_at: When the approval request expires
            urgency: Urgency level (low, medium, high)
            status: Initial status (default: pending)
            vendor: Vendor name for payments
            amount: Payment amount
            purpose: Purpose description
            reason: Reason for approval request
            card_limit: Card limit for create_card action
            agent_id: Agent ID for the action
            wallet_id: Wallet ID for the action
            organization_id: Organization ID
            metadata: Additional metadata

        Returns:
            Created Approval object
        """
        approval_id = Approval.generate_id()
        created_at = datetime.now(timezone.utc)

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
            approval_id, action, status, urgency, requested_by,
            created_at, expires_at, vendor, amount, purpose,
            reason, card_limit, agent_id, wallet_id,
            organization_id, metadata or {}
        )

        return Approval(
            id=approval_id,
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
        """Update approval status and reviewer info.

        Args:
            approval_id: Approval ID
            status: New status
            reviewed_by: Reviewer ID/email
            reviewed_at: Review timestamp
            metadata: Updated metadata

        Returns:
            Updated Approval or None if not found
        """
        # Build dynamic UPDATE query
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
            # No updates, just fetch current state
            return await self.get(approval_id)

        # Add approval_id as last parameter
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
