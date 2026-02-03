"""Approval request expiration scheduled job."""
from __future__ import annotations

import logging

logger = logging.getLogger("sardis.jobs.approval_expiry")


async def expire_approvals() -> None:
    """
    Mark expired approval requests as expired in the database.

    This job runs on an interval (typically every minute) to find pending approvals
    whose expires_at timestamp has passed and updates their status to 'expired'.

    Database query:
    UPDATE approvals SET status = 'expired'
    WHERE status = 'pending' AND expires_at <= NOW()
    """
    try:
        logger.debug("Starting approval expiration job")

        # Import here to avoid circular dependencies
        from sardis_v2_core.database import get_database

        # Get database connection (PostgreSQL in production)
        db = get_database()

        # Check if we have PostgreSQL connection
        if hasattr(db, 'pool') and db.pool:
            async with db.pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE approvals SET status = 'expired'
                    WHERE status = 'pending' AND expires_at <= NOW()
                    """
                )
                # Parse "UPDATE N" to get count
                expired_count = int(result.split()[-1]) if result else 0

                if expired_count > 0:
                    logger.info(f"Approval expiration job completed: {expired_count} approvals expired")
                else:
                    logger.debug("Approval expiration job completed: no approvals expired")
        else:
            # In-memory fallback for development
            logger.debug("Approval expiration job: PostgreSQL not available, skipping")

    except Exception as e:
        logger.error(f"Approval expiration job failed: {e}", exc_info=True)
        raise
