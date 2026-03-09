"""Holds (pre-authorization) management with database persistence."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from .exceptions import SardisDatabaseError
from .utils import TTLDict

logger = logging.getLogger(__name__)


@dataclass
class Hold:
    """A pre-authorization hold on funds."""
    hold_id: str
    wallet_id: str
    merchant_id: str | None
    amount: Decimal
    token: str
    status: str = "active"  # active, captured, voided, expired
    purpose: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    captured_amount: Decimal | None = None
    captured_at: datetime | None = None
    capture_tx_id: str | None = None
    voided_at: datetime | None = None

    def is_expired(self) -> bool:
        """Check if the hold has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def can_capture(self) -> bool:
        """Check if the hold can be captured."""
        return self.status == "active" and not self.is_expired()

    def can_void(self) -> bool:
        """Check if the hold can be voided."""
        return self.status == "active"


@dataclass
class HoldResult:
    """Result of a hold operation."""
    success: bool
    hold: Hold | None = None
    error: str | None = None

    @classmethod
    def succeeded(cls, hold: Hold) -> HoldResult:
        return cls(success=True, hold=hold)

    @classmethod
    def failed(cls, error: str) -> HoldResult:
        return cls(success=False, error=error)


class HoldsRepository:
    """Repository for managing holds with database persistence.

    Uses TTLDict for in-memory storage to prevent memory leaks.
    Default TTL is 7 days (matching hold expiration), max 10,000 holds.
    """

    # Default hold expiration (7 days)
    DEFAULT_EXPIRATION_HOURS = 168
    # TTL for in-memory cache (7 days in seconds)
    DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60
    DEFAULT_MAX_ITEMS = 10000

    def __init__(
        self,
        dsn: str,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_items: int = DEFAULT_MAX_ITEMS,
    ):
        self._dsn = dsn
        self._pg_pool = None
        self._use_postgres = dsn.startswith("postgresql://") or dsn.startswith("postgres://")
        # In-memory fallback for dev with TTL to prevent memory leaks
        self._memory_holds: TTLDict[str, Hold] = TTLDict(
            ttl_seconds=ttl_seconds,
            max_items=max_items,
        )

    async def _get_pool(self):
        """Lazy initialization of PostgreSQL pool."""
        if self._pg_pool is None and self._use_postgres:
            from sardis_v2_core.database import Database
            self._pg_pool = await Database.get_pool()
        return self._pg_pool

    async def create(
        self,
        wallet_id: str,
        amount: Decimal,
        token: str = "USDC",
        merchant_id: str | None = None,
        purpose: str | None = None,
        expiration_hours: int | None = None,
    ) -> HoldResult:
        """Create a new hold."""
        if amount <= Decimal("0"):
            return HoldResult.failed("Amount must be positive")

        hold_id = f"hold_{uuid4().hex[:16]}"
        hours = expiration_hours or self.DEFAULT_EXPIRATION_HOURS
        expires_at = datetime.now(UTC) + timedelta(hours=hours)

        hold = Hold(
            hold_id=hold_id,
            wallet_id=wallet_id,
            merchant_id=merchant_id,
            amount=amount,
            token=token,
            purpose=purpose,
            expires_at=expires_at,
        )

        if self._use_postgres:
            try:
                pool = await self._get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO holds (
                            external_id, wallet_id, merchant_id, amount, token,
                            status, purpose, expires_at, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                        """,
                        hold_id,
                        wallet_id,
                        merchant_id,
                        float(amount),
                        token,
                        "active",
                        purpose,
                        expires_at,
                    )
            except Exception as e:
                logger.error(f"Failed to create hold {hold_id}: {e}", exc_info=True)
                raise SardisDatabaseError(
                    f"Failed to create hold: {e}",
                    operation="insert_hold",
                ) from e
        else:
            self._memory_holds[hold_id] = hold

        return HoldResult.succeeded(hold)

    async def get(self, hold_id: str) -> Hold | None:
        """Get a hold by ID."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT external_id, wallet_id, merchant_id, amount, token,
                           status, purpose, expires_at, created_at,
                           captured_amount, captured_at, voided_at
                    FROM holds WHERE external_id = $1
                    """,
                    hold_id,
                )
                if not row:
                    return None
                return self._row_to_hold(row)
        else:
            return self._memory_holds.get(hold_id)

    async def capture(
        self,
        hold_id: str,
        amount: Decimal | None = None,
        tx_id: str | None = None,
    ) -> HoldResult:
        """Capture a hold."""
        hold = await self.get(hold_id)
        if not hold:
            return HoldResult.failed(f"Hold {hold_id} not found")

        if not hold.can_capture():
            if hold.is_expired():
                return HoldResult.failed("Hold has expired")
            return HoldResult.failed(f"Hold is {hold.status}, cannot capture")

        capture_amount = amount if amount is not None else hold.amount
        if capture_amount > hold.amount:
            return HoldResult.failed(
                f"Capture amount {capture_amount} exceeds hold amount {hold.amount}"
            )

        now = datetime.now(UTC)

        if self._use_postgres:
            try:
                pool = await self._get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE holds SET
                            status = 'captured',
                            captured_amount = $2,
                            captured_at = $3,
                            capture_tx_id = $4
                        WHERE external_id = $1
                        """,
                        hold_id,
                        float(capture_amount),
                        now,
                        tx_id,
                    )
            except Exception as e:
                logger.error(f"Failed to capture hold {hold_id}: {e}", exc_info=True)
                raise SardisDatabaseError(
                    f"Failed to capture hold: {e}",
                    operation="update_hold_capture",
                ) from e
        else:
            hold.status = "captured"
            hold.captured_amount = capture_amount
            hold.captured_at = now
            hold.capture_tx_id = tx_id

        hold.status = "captured"
        hold.captured_amount = capture_amount
        hold.captured_at = now
        hold.capture_tx_id = tx_id

        return HoldResult.succeeded(hold)

    async def void(self, hold_id: str) -> HoldResult:
        """Void a hold."""
        hold = await self.get(hold_id)
        if not hold:
            return HoldResult.failed(f"Hold {hold_id} not found")

        if not hold.can_void():
            return HoldResult.failed(f"Hold is {hold.status}, cannot void")

        now = datetime.now(UTC)

        if self._use_postgres:
            try:
                pool = await self._get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE holds SET
                            status = 'voided',
                            voided_at = $2
                        WHERE external_id = $1
                        """,
                        hold_id,
                        now,
                    )
            except Exception as e:
                logger.error(f"Failed to void hold {hold_id}: {e}", exc_info=True)
                raise SardisDatabaseError(
                    f"Failed to void hold: {e}",
                    operation="update_hold_void",
                ) from e
        else:
            hold.status = "voided"
            hold.voided_at = now

        hold.status = "voided"
        hold.voided_at = now

        return HoldResult.succeeded(hold)

    async def list_by_wallet(
        self,
        wallet_id: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Hold]:
        """List holds for a wallet."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                if status:
                    rows = await conn.fetch(
                        """
                        SELECT external_id, wallet_id, merchant_id, amount, token,
                               status, purpose, expires_at, created_at,
                               captured_amount, captured_at, voided_at
                        FROM holds
                        WHERE wallet_id = $1 AND status = $2
                        ORDER BY created_at DESC
                        LIMIT $3
                        """,
                        wallet_id,
                        status,
                        limit,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT external_id, wallet_id, merchant_id, amount, token,
                               status, purpose, expires_at, created_at,
                               captured_amount, captured_at, voided_at
                        FROM holds
                        WHERE wallet_id = $1
                        ORDER BY created_at DESC
                        LIMIT $2
                        """,
                        wallet_id,
                        limit,
                    )
                return [self._row_to_hold(row) for row in rows]
        else:
            holds = [h for h in self._memory_holds.values() if h.wallet_id == wallet_id]
            if status:
                holds = [h for h in holds if h.status == status]
            return sorted(holds, key=lambda h: h.created_at, reverse=True)[:limit]

    async def list_active(self, limit: int = 100) -> list[Hold]:
        """List all active holds."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT external_id, wallet_id, merchant_id, amount, token,
                           status, purpose, expires_at, created_at,
                           captured_amount, captured_at, voided_at
                    FROM holds
                    WHERE status = 'active' AND expires_at > NOW()
                    ORDER BY created_at DESC
                    LIMIT $1
                    """,
                    limit,
                )
                return [self._row_to_hold(row) for row in rows]
        else:
            now = datetime.now(UTC)
            holds = [
                h for h in self._memory_holds.values()
                if h.status == "active" and (h.expires_at is None or h.expires_at > now)
            ]
            return sorted(holds, key=lambda h: h.created_at, reverse=True)[:limit]

    async def expire_old_holds(self) -> int:
        """Mark expired holds as expired. Returns count of expired holds."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE holds SET status = 'expired'
                    WHERE status = 'active' AND expires_at <= NOW()
                    """
                )
                # Parse "UPDATE N" to get count
                return int(result.split()[-1]) if result else 0
        else:
            now = datetime.now(UTC)
            count = 0
            for hold in self._memory_holds.values():
                if hold.status == "active" and hold.expires_at and hold.expires_at <= now:
                    hold.status = "expired"
                    count += 1
            return count

    def _row_to_hold(self, row) -> Hold:
        """Convert a database row to a Hold object."""
        return Hold(
            hold_id=row["external_id"],
            wallet_id=row["wallet_id"],
            merchant_id=row["merchant_id"],
            amount=Decimal(str(row["amount"])),
            token=row["token"],
            status=row["status"],
            purpose=row["purpose"],
            expires_at=row["expires_at"],
            created_at=row["created_at"],
            captured_amount=Decimal(str(row["captured_amount"])) if row["captured_amount"] else None,
            captured_at=row["captured_at"],
            voided_at=row["voided_at"],
        )
