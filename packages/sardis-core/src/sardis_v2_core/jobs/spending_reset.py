"""Spending limit reset scheduled job."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("sardis.jobs.spending_reset")


async def reset_spending_limits() -> None:
    """
    Reset spending limits for all wallets based on time window expiration.

    This job runs on a schedule (typically daily at midnight UTC) to reset:
    - Daily spending limits (reset every 24 hours)
    - Weekly spending limits (reset every 7 days)
    - Monthly spending limits (reset every 30 days)

    The TimeWindowLimit class has built-in reset_if_expired() logic,
    so this job primarily triggers the check across all wallets.
    """
    try:
        logger.info("Starting spending limit reset job")

        # Import here to avoid circular dependencies
        from sardis_v2_core.wallet_repository import WalletRepository
        from sardis_v2_core.database import get_database

        # Get database connection (PostgreSQL in production)
        db = get_database()
        repo = WalletRepository(dsn=db.dsn if hasattr(db, 'dsn') else "memory://")

        # Fetch all active wallets
        wallets = await repo.list(is_active=True, limit=10000)

        reset_count = 0
        for wallet in wallets:
            # Check and reset time window limits in spending policy
            if wallet.spending_policy:
                policy = wallet.spending_policy

                # Reset daily limit
                if policy.daily_limit:
                    if policy.daily_limit.reset_if_expired():
                        logger.info(
                            f"Reset daily limit for wallet {wallet.wallet_id} "
                            f"(agent: {wallet.agent_id})"
                        )
                        reset_count += 1

                # Reset weekly limit
                if policy.weekly_limit:
                    if policy.weekly_limit.reset_if_expired():
                        logger.info(
                            f"Reset weekly limit for wallet {wallet.wallet_id} "
                            f"(agent: {wallet.agent_id})"
                        )
                        reset_count += 1

                # Reset monthly limit
                if policy.monthly_limit:
                    if policy.monthly_limit.reset_if_expired():
                        logger.info(
                            f"Reset monthly limit for wallet {wallet.wallet_id} "
                            f"(agent: {wallet.agent_id})"
                        )
                        reset_count += 1

                # Update wallet timestamp
                wallet.updated_at = datetime.now(timezone.utc)

        logger.info(
            f"Spending limit reset job completed: {reset_count} limits reset "
            f"across {len(wallets)} wallets"
        )

    except Exception as e:
        logger.error(f"Spending limit reset job failed: {e}", exc_info=True)
        raise
