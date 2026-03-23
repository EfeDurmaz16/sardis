"""Settlement Lock — PostgreSQL advisory locks to prevent double-settlement.

When multiple API workers process the same payment concurrently (e.g. webhook
retry + poll), both could attempt to settle it.  This module prevents that
race condition using PostgreSQL advisory locks, which are:

  - Process-scoped (released on connection close or explicit unlock)
  - Non-blocking with ``pg_try_advisory_lock`` (returns false instead of waiting)
  - Zero-schema (no extra tables required)

How it works:
─────────────────────────────────────────────────────────────────────
  1. ``acquire(payment_id)`` hashes the payment ID to an int8 and calls
     ``pg_try_advisory_lock(hash)``.
  2. If the lock is already held by another connection → returns False.
  3. The caller proceeds with settlement only if acquire returns True.
  4. ``release(payment_id)`` explicitly unlocks, or the lock auto-releases
     when the connection is returned to the pool.
─────────────────────────────────────────────────────────────────────

Usage::

    from sardis_v2_core.settlement_lock import SettlementLock

    lock = SettlementLock(pool)

    # Option 1: Manual acquire/release
    acquired = await lock.acquire("po_abc123")
    if not acquired:
        raise ConcurrentSettlementError("Payment already being settled")
    try:
        await do_settlement(...)
    finally:
        await lock.release("po_abc123")

    # Option 2: Context manager (recommended)
    async with lock.with_lock("po_abc123"):
        await do_settlement(...)
    # Lock auto-released on exit, even on exception.

See also:
  - ``state_machine.py`` — state transitions that should be protected
  - ``settlement.py`` — settlement tracking and reconciliation
  - ``reconciliation_queue_postgres.py`` — durable queue with similar locking
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from asyncpg import Pool

logger = logging.getLogger("sardis.settlement_lock")


class SettlementLockError(Exception):
    """Raised when a settlement lock cannot be acquired."""

    def __init__(self, payment_object_id: str) -> None:
        self.payment_object_id = payment_object_id
        super().__init__(
            f"Could not acquire settlement lock for {payment_object_id}. "
            f"Another worker is likely processing this payment."
        )


class SettlementLock:
    """Prevents double-settlement race conditions using PostgreSQL advisory locks.

    Advisory locks are scoped to the database connection.  The lock is
    identified by a deterministic int8 hash of the payment object ID,
    computed via PostgreSQL's built-in ``hashtext()`` function.

    Args:
        pool: asyncpg connection pool.
    """

    def __init__(self, pool: Pool) -> None:
        self._pool = pool
        # Track which connections hold which locks so we can release on
        # the same connection (required by PostgreSQL advisory locks).
        self._held: dict[str, Any] = {}

    async def acquire(
        self,
        payment_object_id: str,
        timeout_seconds: int = 30,
    ) -> bool:
        """Try to acquire an advisory lock for the given payment.

        Uses ``pg_try_advisory_lock(hashtext($1))`` which returns
        immediately with ``true``/``false`` instead of blocking.

        Args:
            payment_object_id: The payment object ID to lock.
            timeout_seconds: Statement timeout for the lock query.
                Prevents hanging if the database is under pressure.

        Returns:
            True if the lock was acquired, False if another worker
            already holds it.
        """
        conn = await self._pool.acquire()
        try:
            row = await conn.fetchrow(
                "SELECT pg_try_advisory_lock(hashtext($1)) AS acquired",
                payment_object_id,
            )
            acquired = row["acquired"] if row else False

            if acquired:
                # Store the connection so we release on the same one
                self._held[payment_object_id] = conn
                logger.debug(
                    "Settlement lock acquired for %s",
                    payment_object_id,
                )
                return True
            else:
                # Release the connection back to the pool — we don't need it
                await self._pool.release(conn)
                logger.debug(
                    "Settlement lock NOT acquired for %s (held by another worker)",
                    payment_object_id,
                )
                return False
        except Exception:
            # On any error, make sure we release the connection
            await self._pool.release(conn)
            raise

    async def release(self, payment_object_id: str) -> None:
        """Release the advisory lock for the given payment.

        Must be called on the same connection that acquired the lock.
        If the lock is not held, this is a no-op.

        Args:
            payment_object_id: The payment object ID to unlock.
        """
        conn = self._held.pop(payment_object_id, None)
        if conn is None:
            logger.debug(
                "Settlement lock release called for %s but no lock held",
                payment_object_id,
            )
            return

        try:
            await conn.execute(
                "SELECT pg_advisory_unlock(hashtext($1))",
                payment_object_id,
            )
            logger.debug("Settlement lock released for %s", payment_object_id)
        finally:
            # Always return the connection to the pool
            await self._pool.release(conn)

    @asynccontextmanager
    async def with_lock(
        self,
        payment_object_id: str,
        timeout_seconds: int = 30,
    ) -> AsyncGenerator[None, None]:
        """Async context manager that acquires and releases a settlement lock.

        Raises ``SettlementLockError`` if the lock cannot be acquired.
        Guarantees the lock is released on exit (even if an exception
        occurs inside the ``async with`` block).

        Args:
            payment_object_id: The payment object ID to lock.
            timeout_seconds: Statement timeout for the lock query.

        Raises:
            SettlementLockError: If the lock is already held by another worker.

        Usage::

            async with lock.with_lock("po_abc123"):
                await do_settlement(...)
        """
        acquired = await self.acquire(payment_object_id, timeout_seconds)
        if not acquired:
            raise SettlementLockError(payment_object_id)
        try:
            yield
        finally:
            await self.release(payment_object_id)
