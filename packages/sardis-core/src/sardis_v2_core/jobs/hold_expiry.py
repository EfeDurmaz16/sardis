"""Hold expiration cleanup scheduled job."""
from __future__ import annotations

import logging

logger = logging.getLogger("sardis.jobs.hold_expiry")


async def expire_holds() -> None:
    """
    Mark expired holds as expired in the database.

    This job runs on an interval (typically every 5 minutes) to find active holds
    whose expires_at timestamp has passed and updates their status to 'expired'.

    The HoldsRepository.expire_old_holds() method handles the database query:
    UPDATE holds SET status = 'expired'
    WHERE status = 'active' AND expires_at <= NOW()
    """
    try:
        logger.info("Starting hold expiration job")

        # Import here to avoid circular dependencies
        from sardis_v2_core.holds import HoldsRepository
        from sardis_v2_core.database import get_database

        # Get database connection (PostgreSQL in production)
        db = get_database()
        repo = HoldsRepository(dsn=db.dsn if hasattr(db, 'dsn') else "memory://")

        # Expire old holds
        expired_count = await repo.expire_old_holds()

        if expired_count > 0:
            logger.info(f"Hold expiration job completed: {expired_count} holds expired")
        else:
            logger.debug("Hold expiration job completed: no holds expired")

    except Exception as e:
        logger.error(f"Hold expiration job failed: {e}", exc_info=True)
        raise
