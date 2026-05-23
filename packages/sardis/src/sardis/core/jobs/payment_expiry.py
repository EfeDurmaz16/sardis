"""Payment object expiration background job.

Scans for payment objects requiring automatic state transitions and applies
them via the PaymentStateMachine.  Three categories are handled:

  1. **LOCKED + mandate expired** -> EXPIRED
     JOINs payment_objects with spending_mandates to check sm.expires_at.

  2. **ESCROWED + timelock expired** -> AUTO_RELEASING -> RELEASED
     JOINs payment_objects with escrow_holds to check eh.timelock_expires_at.

  3. **ARBITRATING + review deadline passed** -> (log warning only)
     JOINs payment_objects with disputes to check d.review_deadline.

All queries use ``SELECT ... FOR UPDATE SKIP LOCKED`` to avoid conflicts
with other workers or API handlers touching the same rows concurrently.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sardis.core.state_machine import PaymentState, PaymentStateMachine

logger = logging.getLogger("sardis.jobs.payment_expiry")

_ACTOR = "payment_expiry_job"


async def expire_payments() -> None:
    """Run all three payment-expiry sweeps.

    Intended to be invoked on a schedule (e.g. every 60 seconds).
    Each sweep is independent — a failure in one does not block the others.
    """
    logger.debug("Starting payment expiry job")

    expired_locked = await _expire_locked_payments()
    released_escrowed = await _release_escrowed_payments()
    warned_arbitrating = await _warn_overdue_arbitrations()

    total = expired_locked + released_escrowed + warned_arbitrating
    if total > 0:
        logger.info(
            "Payment expiry job completed: "
            "%d locked->expired, %d escrowed->released, %d arbitrating warnings",
            expired_locked,
            released_escrowed,
            warned_arbitrating,
        )
    else:
        logger.debug("Payment expiry job completed: nothing to do")


# ═══════════════════════════════════════════════════════════════════════
# Sweep 1: LOCKED where mandate expired → EXPIRED
# JOIN payment_objects ON spending_mandates via mandate_id
# ═══════════════════════════════════════════════════════════════════════

async def _expire_locked_payments() -> int:
    """Transition LOCKED payments whose mandate has expired to EXPIRED."""
    try:
        from sardis.core.database import get_database

        db = get_database()
        if not (hasattr(db, "pool") and db.pool):
            logger.debug("_expire_locked_payments: PostgreSQL not available, skipping")
            return 0

        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT po.object_id, po.status, sm.expires_at AS mandate_expires_at
                FROM payment_objects po
                JOIN spending_mandates sm ON sm.id = po.mandate_id
                WHERE po.status = 'locked'
                  AND sm.expires_at IS NOT NULL
                  AND sm.expires_at <= NOW()
                FOR UPDATE OF po SKIP LOCKED
                """
            )

            count = 0
            for row in rows:
                po_id = row["object_id"]
                try:
                    machine = PaymentStateMachine(
                        payment_object_id=po_id,
                        current_state=PaymentState.LOCKED,
                    )
                    record = machine.transition(
                        to_state=PaymentState.EXPIRED,
                        actor=_ACTOR,
                        reason="Mandate expired while payment was locked",
                        metadata={"mandate_expires_at": str(row["mandate_expires_at"])},
                    )

                    await conn.execute(
                        """
                        UPDATE payment_objects
                        SET status = $1, updated_at = NOW()
                        WHERE object_id = $2
                        """,
                        PaymentState.EXPIRED.value,
                        po_id,
                    )

                    await _persist_transition(conn, record)
                    count += 1

                    logger.info(
                        "Payment %s transitioned LOCKED -> EXPIRED (mandate expired at %s)",
                        po_id,
                        row["mandate_expires_at"],
                    )
                except Exception as e:
                    logger.error(
                        "Failed to expire locked payment %s: %s", po_id, e, exc_info=True
                    )

            return count

    except Exception as e:
        logger.error("_expire_locked_payments sweep failed: %s", e, exc_info=True)
        return 0


# ═══════════════════════════════════════════════════════════════════════
# Sweep 2: ESCROWED where timelock expired → AUTO_RELEASING → RELEASED
# JOIN payment_objects ON escrow_holds via payment_object_id
# ═══════════════════════════════════════════════════════════════════════

async def _release_escrowed_payments() -> int:
    """Two-step release: ESCROWED → AUTO_RELEASING → RELEASED."""
    try:
        from sardis.core.database import get_database

        db = get_database()
        if not (hasattr(db, "pool") and db.pool):
            logger.debug("_release_escrowed_payments: PostgreSQL not available, skipping")
            return 0

        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT po.object_id, po.status, eh.timelock_expires_at
                FROM payment_objects po
                JOIN escrow_holds eh ON eh.payment_object_id = po.object_id
                WHERE po.status = 'escrowed'
                  AND eh.timelock_expires_at IS NOT NULL
                  AND eh.timelock_expires_at < NOW()
                  AND eh.auto_release = true
                FOR UPDATE OF po SKIP LOCKED
                """
            )

            count = 0
            for row in rows:
                po_id = row["object_id"]
                try:
                    machine = PaymentStateMachine(
                        payment_object_id=po_id,
                        current_state=PaymentState.ESCROWED,
                    )

                    # Step 1: ESCROWED → AUTO_RELEASING
                    record_1 = machine.transition(
                        to_state=PaymentState.AUTO_RELEASING,
                        actor=_ACTOR,
                        reason="Escrow timelock expired",
                        metadata={"timelock_expires_at": str(row["timelock_expires_at"])},
                    )

                    await conn.execute(
                        "UPDATE payment_objects SET status = $1, updated_at = NOW() WHERE object_id = $2",
                        PaymentState.AUTO_RELEASING.value,
                        po_id,
                    )
                    await _persist_transition(conn, record_1)

                    # Step 2: AUTO_RELEASING → RELEASED
                    record_2 = machine.transition(
                        to_state=PaymentState.RELEASED,
                        actor=_ACTOR,
                        reason="Auto-release after timelock expiry",
                    )

                    await conn.execute(
                        "UPDATE payment_objects SET status = $1, updated_at = NOW() WHERE object_id = $2",
                        PaymentState.RELEASED.value,
                        po_id,
                    )
                    await _persist_transition(conn, record_2)

                    # Also update the escrow hold status
                    await conn.execute(
                        """UPDATE escrow_holds
                           SET status = 'auto_released', released_at = NOW(),
                               released_to = merchant_id, released_amount = amount,
                               updated_at = NOW()
                           WHERE payment_object_id = $1 AND status IN ('held', 'confirming')""",
                        po_id,
                    )

                    count += 1
                    logger.info(
                        "Payment %s auto-released: ESCROWED -> RELEASED (timelock expired at %s)",
                        po_id,
                        row["timelock_expires_at"],
                    )
                except Exception as e:
                    logger.error(
                        "Failed to auto-release escrowed payment %s: %s",
                        po_id, e, exc_info=True,
                    )

            return count

    except Exception as e:
        logger.error("_release_escrowed_payments sweep failed: %s", e, exc_info=True)
        return 0


# ═══════════════════════════════════════════════════════════════════════
# Sweep 3: ARBITRATING where review_deadline passed → log warning
# JOIN payment_objects ON disputes via payment_object_id
# ═══════════════════════════════════════════════════════════════════════

async def _warn_overdue_arbitrations() -> int:
    """Log warnings for arbitrations past their review deadline.

    We never auto-resolve disputes — only humans can do that.
    This sweep exists so ops dashboards and alerting can pick up the warnings.
    """
    try:
        from sardis.core.database import get_database

        db = get_database()
        if not (hasattr(db, "pool") and db.pool):
            logger.debug("_warn_overdue_arbitrations: PostgreSQL not available, skipping")
            return 0

        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT po.object_id, d.dispute_id, d.review_deadline
                FROM payment_objects po
                JOIN disputes d ON d.payment_object_id = po.object_id
                WHERE po.status = 'arbitrating'
                  AND d.review_deadline IS NOT NULL
                  AND d.review_deadline < NOW()
                  AND d.status = 'under_review'
                FOR UPDATE OF po SKIP LOCKED
                """
            )

            count = 0
            for row in rows:
                logger.warning(
                    "OVERDUE ARBITRATION: payment %s (dispute %s) review deadline was %s "
                    "(%.1f hours ago) — requires manual resolution",
                    row["object_id"],
                    row["dispute_id"],
                    row["review_deadline"],
                    (datetime.now(UTC) - row["review_deadline"].replace(tzinfo=UTC)).total_seconds() / 3600,
                )
                count += 1

            return count

    except Exception as e:
        logger.error("_warn_overdue_arbitrations sweep failed: %s", e, exc_info=True)
        return 0


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

async def _persist_transition(conn, record) -> None:  # noqa: ANN001
    """Write a StateTransitionRecord to the payment_state_transitions table.

    Best-effort: if the table does not exist yet (e.g. dev environment),
    the error is logged but not re-raised.
    """
    try:
        await conn.execute(
            """
            INSERT INTO payment_state_transitions
                (id, payment_object_id, from_state, to_state,
                 transition_name, actor, reason, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            record.id,
            record.payment_object_id,
            record.from_state.value,
            record.to_state.value,
            record.transition_name,
            record.actor,
            record.reason,
            str(record.metadata),
            record.created_at,
        )
    except Exception as e:
        logger.warning(
            "Could not persist transition record for %s: %s",
            record.payment_object_id,
            e,
        )
