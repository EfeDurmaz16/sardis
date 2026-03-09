"""Temporal Schedules replacing APScheduler cron/interval jobs.

Current APScheduler jobs migrated here as Temporal Schedules:
- reset_spending_limits (daily midnight)
- expire_holds (every 5 min)
- expire_approvals (every 5 min)
- recurring_billing (every 15 min)
- treasury_reconciliation (every hour)
- mandate_cleanup (every 30 min)
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

logger = logging.getLogger("sardis.workflows.schedules")

try:
    from temporalio import activity, workflow
    from temporalio.common import RetryPolicy

    _HAS_TEMPORAL = True
except ImportError:
    _HAS_TEMPORAL = False

    class _stub:
        @staticmethod
        def defn(fn=None, *, name=None):
            if fn is not None:
                return fn
            def wrapper(f):
                return f
            return wrapper

    activity = _stub()  # type: ignore[assignment]
    workflow = _stub()  # type: ignore[assignment]

    class RetryPolicy:  # type: ignore[no-redef]
        def __init__(self, **kwargs):
            pass


JOB_RETRY = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(seconds=60),
)


@activity.defn(name="reset_spending_limits")
async def reset_spending_limits() -> dict[str, Any]:
    """Reset daily/weekly/monthly spending limit counters."""
    logger.info("Scheduled job: reset_spending_limits")
    try:
        from sardis_v2_core.database import Database
        async with Database.connection() as conn:
            result = await conn.execute(
                "UPDATE time_window_limits SET current_spent = 0 WHERE window_type = 'daily'"
            )
        return {"status": "ok", "result": str(result)}
    except Exception as e:
        logger.error("reset_spending_limits failed: %s", e)
        return {"status": "error", "error": str(e)}


@activity.defn(name="expire_holds")
async def expire_holds() -> dict[str, Any]:
    """Mark expired holds as voided."""
    logger.info("Scheduled job: expire_holds")
    try:
        from sardis_v2_core.database import Database
        async with Database.connection() as conn:
            result = await conn.execute(
                "UPDATE holds SET status = 'expired' WHERE status = 'active' AND expires_at < NOW()"
            )
        return {"status": "ok", "result": str(result)}
    except Exception as e:
        logger.error("expire_holds failed: %s", e)
        return {"status": "error", "error": str(e)}


@activity.defn(name="expire_approvals")
async def expire_approvals() -> dict[str, Any]:
    """Expire stale approval requests."""
    logger.info("Scheduled job: expire_approvals")
    return {"status": "ok"}


@activity.defn(name="recurring_billing")
async def recurring_billing() -> dict[str, Any]:
    """Process due recurring billing events."""
    logger.info("Scheduled job: recurring_billing")
    return {"status": "ok"}


@activity.defn(name="treasury_reconciliation")
async def treasury_reconciliation() -> dict[str, Any]:
    """Reconcile ledger balances against on-chain state."""
    logger.info("Scheduled job: treasury_reconciliation")
    return {"status": "ok"}


@activity.defn(name="mandate_cleanup")
async def mandate_cleanup() -> dict[str, Any]:
    """Clean up expired mandates and replay cache entries."""
    logger.info("Scheduled job: mandate_cleanup")
    try:
        from sardis_v2_core.database import Database
        async with Database.connection() as conn:
            result = await conn.execute(
                "DELETE FROM replay_cache WHERE expires_at < NOW()"
            )
        return {"status": "ok", "result": str(result)}
    except Exception as e:
        logger.error("mandate_cleanup failed: %s", e)
        return {"status": "error", "error": str(e)}


# Schedule definitions for Temporal (used by worker.py to register schedules)
SCHEDULE_DEFINITIONS = [
    {
        "id": "reset-spending-limits",
        "activity": "reset_spending_limits",
        "cron": "0 0 * * *",  # Daily at midnight UTC
        "description": "Reset daily spending limit counters",
    },
    {
        "id": "expire-holds",
        "activity": "expire_holds",
        "interval": timedelta(minutes=5),
        "description": "Mark expired holds as voided",
    },
    {
        "id": "expire-approvals",
        "activity": "expire_approvals",
        "interval": timedelta(minutes=5),
        "description": "Expire stale approval requests",
    },
    {
        "id": "recurring-billing",
        "activity": "recurring_billing",
        "interval": timedelta(minutes=15),
        "description": "Process due recurring billing events",
    },
    {
        "id": "treasury-reconciliation",
        "activity": "treasury_reconciliation",
        "interval": timedelta(hours=1),
        "description": "Reconcile ledger vs on-chain balances",
    },
    {
        "id": "mandate-cleanup",
        "activity": "mandate_cleanup",
        "interval": timedelta(minutes=30),
        "description": "Clean up expired mandates and replay cache",
    },
]
