"""Agent-to-Agent Escrow Management.

This module provides escrow primitives for safe agent-to-agent payments:
- Funds are held in escrow until delivery is confirmed
- Automatic refunds for expired escrows
- Dispute resolution flow
- State machine validation for escrow lifecycle

Escrow States:
    CREATED → FUNDED → DELIVERED → RELEASED
                   ↓→ DISPUTED
                   ↓→ REFUNDED
                   ↓→ EXPIRED → REFUNDED

Usage:
    from sardis_v2_core.a2a_escrow import EscrowManager, EscrowState

    manager = EscrowManager()

    # 1. Create escrow
    escrow = await manager.create_escrow(
        payer="agent_123",
        payee="agent_456",
        amount=Decimal("100.00"),
        token=TokenType.USDC,
        chain="base",
        timeout_hours=24,
    )

    # 2. Fund escrow (after on-chain transaction)
    await manager.fund_escrow(escrow.id, tx_hash="0x...")

    # 3. Confirm delivery
    await manager.confirm_delivery(escrow.id, proof="delivery_hash")

    # 4. Release payment
    await manager.release_escrow(escrow.id)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Literal
from uuid import uuid4

from .database import Database
from .exceptions import (
    SardisNotFoundError,
    SardisValidationError,
    SardisConflictError,
)
from .tokens import TokenType


class EscrowState(str, Enum):
    """Escrow lifecycle states."""
    CREATED = "created"
    FUNDED = "funded"
    DELIVERED = "delivered"
    RELEASED = "released"
    REFUNDED = "refunded"
    DISPUTED = "disputed"
    EXPIRED = "expired"


# Valid state transitions (fail-closed: only explicit transitions allowed)
VALID_TRANSITIONS: dict[EscrowState, set[EscrowState]] = {
    EscrowState.CREATED: {EscrowState.FUNDED, EscrowState.EXPIRED},
    EscrowState.FUNDED: {EscrowState.DELIVERED, EscrowState.REFUNDED, EscrowState.DISPUTED, EscrowState.EXPIRED},
    EscrowState.DELIVERED: {EscrowState.RELEASED, EscrowState.DISPUTED},
    EscrowState.DISPUTED: {EscrowState.RELEASED, EscrowState.REFUNDED},
    EscrowState.RELEASED: set(),  # Terminal state
    EscrowState.REFUNDED: set(),  # Terminal state
    EscrowState.EXPIRED: {EscrowState.REFUNDED},
}


@dataclass(slots=True)
class Escrow:
    """
    Agent-to-agent escrow record.

    Represents funds held in escrow between a payer agent and payee agent,
    with delivery confirmation and dispute resolution capabilities.
    """
    id: str
    payer_agent_id: str
    payee_agent_id: str
    amount: Decimal
    token: str  # TokenType value (e.g., "USDC")
    chain: str
    state: EscrowState
    created_at: datetime
    expires_at: datetime

    # Funding details
    funded_at: Optional[datetime] = None
    funding_tx_hash: Optional[str] = None

    # Delivery confirmation
    delivery_proof: Optional[str] = None
    delivered_at: Optional[datetime] = None

    # Release/refund details
    released_at: Optional[datetime] = None
    release_tx_hash: Optional[str] = None
    refunded_at: Optional[datetime] = None
    refund_tx_hash: Optional[str] = None
    refund_reason: Optional[str] = None

    # Dispute details
    disputed_at: Optional[datetime] = None
    dispute_reason: Optional[str] = None
    dispute_resolution: Optional[str] = None

    # Additional metadata
    metadata: dict = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_expired(self) -> bool:
        """Check if escrow has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def can_transition_to(self, new_state: EscrowState) -> bool:
        """Check if state transition is valid."""
        return new_state in VALID_TRANSITIONS.get(self.state, set())


class EscrowManager:
    """
    Manages agent-to-agent escrow lifecycle.

    Handles escrow creation, funding, delivery confirmation, release,
    refunds, disputes, and automatic expiration cleanup.
    """

    async def create_escrow(
        self,
        payer: str,
        payee: str,
        amount: Decimal,
        token: TokenType,
        chain: str,
        timeout_hours: int = 24,
        metadata: Optional[dict] = None,
    ) -> Escrow:
        """
        Create a new escrow between two agents.

        Args:
            payer: Payer agent ID
            payee: Payee agent ID
            amount: Escrow amount in token units
            token: Token type (USDC, USDT, etc.)
            chain: Blockchain network
            timeout_hours: Hours until escrow expires (default: 24)
            metadata: Optional additional metadata

        Returns:
            Created Escrow instance

        Raises:
            SardisValidationError: If amount <= 0 or payer == payee
        """
        # Validation
        if amount <= 0:
            raise SardisValidationError("Escrow amount must be positive", field="amount")
        if payer == payee:
            raise SardisValidationError("Payer and payee must be different agents")

        escrow_id = f"escrow_{uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=timeout_hours)

        escrow = Escrow(
            id=escrow_id,
            payer_agent_id=payer,
            payee_agent_id=payee,
            amount=amount,
            token=token.value,
            chain=chain,
            state=EscrowState.CREATED,
            created_at=now,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        # Persist to database
        async with Database.connection() as conn:
            await conn.execute(
                """
                INSERT INTO escrows (
                    id, payer_agent_id, payee_agent_id, amount, token, chain,
                    state, created_at, expires_at, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                escrow.id,
                escrow.payer_agent_id,
                escrow.payee_agent_id,
                escrow.amount,
                escrow.token,
                escrow.chain,
                escrow.state.value,
                escrow.created_at,
                escrow.expires_at,
                escrow.metadata,
            )

        return escrow

    async def fund_escrow(self, escrow_id: str, tx_hash: str) -> Escrow:
        """
        Mark escrow as funded after on-chain transaction.

        Args:
            escrow_id: Escrow identifier
            tx_hash: On-chain transaction hash

        Returns:
            Updated Escrow instance

        Raises:
            SardisNotFoundError: If escrow not found
            SardisConflictError: If invalid state transition
        """
        escrow = await self.get_escrow(escrow_id)

        # Validate transition
        if not escrow.can_transition_to(EscrowState.FUNDED):
            raise SardisConflictError(
                f"Cannot fund escrow in state {escrow.state.value}"
            )

        now = datetime.now(timezone.utc)

        # Update database
        async with Database.connection() as conn:
            await conn.execute(
                """
                UPDATE escrows
                SET state = $1, funded_at = $2, funding_tx_hash = $3, updated_at = $4
                WHERE id = $5
                """,
                EscrowState.FUNDED.value,
                now,
                tx_hash,
                now,
                escrow_id,
            )

        escrow.state = EscrowState.FUNDED
        escrow.funded_at = now
        escrow.funding_tx_hash = tx_hash
        escrow.updated_at = now

        return escrow

    async def confirm_delivery(self, escrow_id: str, proof: str) -> Escrow:
        """
        Payee confirms delivery of goods/services.

        Args:
            escrow_id: Escrow identifier
            proof: Delivery proof (hash, receipt, etc.)

        Returns:
            Updated Escrow instance

        Raises:
            SardisNotFoundError: If escrow not found
            SardisConflictError: If invalid state transition
        """
        escrow = await self.get_escrow(escrow_id)

        # Validate transition
        if not escrow.can_transition_to(EscrowState.DELIVERED):
            raise SardisConflictError(
                f"Cannot confirm delivery for escrow in state {escrow.state.value}"
            )

        now = datetime.now(timezone.utc)

        # Update database
        async with Database.connection() as conn:
            await conn.execute(
                """
                UPDATE escrows
                SET state = $1, delivered_at = $2, delivery_proof = $3, updated_at = $4
                WHERE id = $5
                """,
                EscrowState.DELIVERED.value,
                now,
                proof,
                now,
                escrow_id,
            )

        escrow.state = EscrowState.DELIVERED
        escrow.delivered_at = now
        escrow.delivery_proof = proof
        escrow.updated_at = now

        return escrow

    async def release_escrow(self, escrow_id: str, tx_hash: Optional[str] = None) -> Escrow:
        """
        Release escrowed funds to payee.

        Args:
            escrow_id: Escrow identifier
            tx_hash: Optional settlement transaction hash

        Returns:
            Updated Escrow instance

        Raises:
            SardisNotFoundError: If escrow not found
            SardisConflictError: If invalid state transition
        """
        escrow = await self.get_escrow(escrow_id)

        # Validate transition
        if not escrow.can_transition_to(EscrowState.RELEASED):
            raise SardisConflictError(
                f"Cannot release escrow in state {escrow.state.value}"
            )

        now = datetime.now(timezone.utc)

        # Update database
        async with Database.connection() as conn:
            await conn.execute(
                """
                UPDATE escrows
                SET state = $1, released_at = $2, release_tx_hash = $3, updated_at = $4
                WHERE id = $5
                """,
                EscrowState.RELEASED.value,
                now,
                tx_hash,
                now,
                escrow_id,
            )

        escrow.state = EscrowState.RELEASED
        escrow.released_at = now
        escrow.release_tx_hash = tx_hash
        escrow.updated_at = now

        return escrow

    async def refund_escrow(self, escrow_id: str, reason: str, tx_hash: Optional[str] = None) -> Escrow:
        """
        Refund escrowed funds to payer.

        Args:
            escrow_id: Escrow identifier
            reason: Reason for refund
            tx_hash: Optional refund transaction hash

        Returns:
            Updated Escrow instance

        Raises:
            SardisNotFoundError: If escrow not found
            SardisConflictError: If invalid state transition
        """
        escrow = await self.get_escrow(escrow_id)

        # Validate transition
        if not escrow.can_transition_to(EscrowState.REFUNDED):
            raise SardisConflictError(
                f"Cannot refund escrow in state {escrow.state.value}"
            )

        now = datetime.now(timezone.utc)

        # Update database
        async with Database.connection() as conn:
            await conn.execute(
                """
                UPDATE escrows
                SET state = $1, refunded_at = $2, refund_tx_hash = $3,
                    refund_reason = $4, updated_at = $5
                WHERE id = $6
                """,
                EscrowState.REFUNDED.value,
                now,
                tx_hash,
                reason,
                now,
                escrow_id,
            )

        escrow.state = EscrowState.REFUNDED
        escrow.refunded_at = now
        escrow.refund_tx_hash = tx_hash
        escrow.refund_reason = reason
        escrow.updated_at = now

        return escrow

    async def dispute_escrow(self, escrow_id: str, reason: str) -> Escrow:
        """
        Open a dispute for an escrow.

        Args:
            escrow_id: Escrow identifier
            reason: Dispute reason

        Returns:
            Updated Escrow instance

        Raises:
            SardisNotFoundError: If escrow not found
            SardisConflictError: If invalid state transition
        """
        escrow = await self.get_escrow(escrow_id)

        # Validate transition
        if not escrow.can_transition_to(EscrowState.DISPUTED):
            raise SardisConflictError(
                f"Cannot dispute escrow in state {escrow.state.value}"
            )

        now = datetime.now(timezone.utc)

        # Update database
        async with Database.connection() as conn:
            await conn.execute(
                """
                UPDATE escrows
                SET state = $1, disputed_at = $2, dispute_reason = $3, updated_at = $4
                WHERE id = $5
                """,
                EscrowState.DISPUTED.value,
                now,
                reason,
                now,
                escrow_id,
            )

        escrow.state = EscrowState.DISPUTED
        escrow.disputed_at = now
        escrow.dispute_reason = reason
        escrow.updated_at = now

        return escrow

    async def check_expired_escrows(self) -> list[Escrow]:
        """
        Find and mark expired escrows.

        Returns:
            List of expired escrows that were marked
        """
        now = datetime.now(timezone.utc)

        async with Database.connection() as conn:
            # Find escrows that are expired but not yet marked
            rows = await conn.fetch(
                """
                UPDATE escrows
                SET state = $1, updated_at = $2
                WHERE expires_at < $3
                  AND state IN ($4, $5)
                RETURNING id, payer_agent_id, payee_agent_id, amount, token, chain,
                          state, created_at, expires_at, funded_at, funding_tx_hash,
                          delivery_proof, delivered_at, released_at, release_tx_hash,
                          refunded_at, refund_tx_hash, refund_reason, disputed_at,
                          dispute_reason, dispute_resolution, metadata, updated_at
                """,
                EscrowState.EXPIRED.value,
                now,
                now,
                EscrowState.CREATED.value,
                EscrowState.FUNDED.value,
            )

            escrows = []
            for row in rows:
                escrow = self._row_to_escrow(row)
                escrows.append(escrow)

            return escrows

    async def get_escrow(self, escrow_id: str) -> Escrow:
        """
        Get escrow by ID.

        Args:
            escrow_id: Escrow identifier

        Returns:
            Escrow instance

        Raises:
            SardisNotFoundError: If escrow not found
        """
        async with Database.connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, payer_agent_id, payee_agent_id, amount, token, chain,
                       state, created_at, expires_at, funded_at, funding_tx_hash,
                       delivery_proof, delivered_at, released_at, release_tx_hash,
                       refunded_at, refund_tx_hash, refund_reason, disputed_at,
                       dispute_reason, dispute_resolution, metadata, updated_at
                FROM escrows
                WHERE id = $1
                """,
                escrow_id,
            )

            if not row:
                raise SardisNotFoundError("Escrow", escrow_id)

            return self._row_to_escrow(row)

    async def list_escrows(
        self,
        agent_id: str,
        role: Literal["payer", "payee", "any"] = "any",
        state: Optional[EscrowState] = None,
    ) -> list[Escrow]:
        """
        List escrows for an agent.

        Args:
            agent_id: Agent identifier
            role: Filter by role (payer, payee, or any)
            state: Optional state filter

        Returns:
            List of Escrow instances
        """
        query_parts = ["SELECT * FROM escrows WHERE 1=1"]
        params: list = []
        param_idx = 1

        # Role filter
        if role == "payer":
            query_parts.append(f" AND payer_agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1
        elif role == "payee":
            query_parts.append(f" AND payee_agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1
        else:  # any
            query_parts.append(f" AND (payer_agent_id = ${param_idx} OR payee_agent_id = ${param_idx})")
            params.append(agent_id)
            param_idx += 1

        # State filter
        if state:
            query_parts.append(f" AND state = ${param_idx}")
            params.append(state.value)
            param_idx += 1

        query_parts.append(" ORDER BY created_at DESC")
        query = "".join(query_parts)

        async with Database.connection() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_escrow(row) for row in rows]

    @staticmethod
    def _row_to_escrow(row) -> Escrow:
        """Convert database row to Escrow instance."""
        return Escrow(
            id=row["id"],
            payer_agent_id=row["payer_agent_id"],
            payee_agent_id=row["payee_agent_id"],
            amount=row["amount"],
            token=row["token"],
            chain=row["chain"],
            state=EscrowState(row["state"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            funded_at=row.get("funded_at"),
            funding_tx_hash=row.get("funding_tx_hash"),
            delivery_proof=row.get("delivery_proof"),
            delivered_at=row.get("delivered_at"),
            released_at=row.get("released_at"),
            release_tx_hash=row.get("release_tx_hash"),
            refunded_at=row.get("refunded_at"),
            refund_tx_hash=row.get("refund_tx_hash"),
            refund_reason=row.get("refund_reason"),
            disputed_at=row.get("disputed_at"),
            dispute_reason=row.get("dispute_reason"),
            dispute_resolution=row.get("dispute_resolution"),
            metadata=row.get("metadata") or {},
            updated_at=row["updated_at"],
        )
