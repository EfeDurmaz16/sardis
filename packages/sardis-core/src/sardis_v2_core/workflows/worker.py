"""Temporal worker startup for Sardis.

Run with:
    python -m sardis_v2_core.workflows.worker

Or in production:
    temporal worker start --task-queue sardis-payments

Falls back to APScheduler when Temporal server is not available.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

logger = logging.getLogger("sardis.workflows.worker")

TASK_QUEUE = "sardis-payments"
NAMESPACE = "default"


async def start_temporal_worker() -> None:
    """Start a Temporal worker that processes Sardis workflows and activities."""
    try:
        from temporalio.client import Client
        from temporalio.worker import Worker
    except ImportError:
        logger.error(
            "temporalio is not installed. Install with: pip install temporalio"
        )
        sys.exit(1)

    from .activities import (
        chain_execution,
        compliance_screening,
        kya_verification,
        ledger_append,
        policy_check,
        webhook_notification,
    )
    from .payment_workflow import PaymentWorkflow
    from .scheduled_jobs import (
        expire_approvals,
        expire_holds,
        mandate_cleanup,
        recurring_billing,
        reset_spending_limits,
        treasury_reconciliation,
    )

    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", NAMESPACE)

    logger.info("Connecting to Temporal at %s (namespace=%s)", temporal_address, namespace)

    client = await Client.connect(temporal_address, namespace=namespace)

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[PaymentWorkflow],
        activities=[
            # Payment workflow activities
            kya_verification,
            policy_check,
            compliance_screening,
            chain_execution,
            ledger_append,
            webhook_notification,
            # Scheduled job activities
            reset_spending_limits,
            expire_holds,
            expire_approvals,
            recurring_billing,
            treasury_reconciliation,
            mandate_cleanup,
        ],
    )

    logger.info("Temporal worker started on task queue '%s'", TASK_QUEUE)
    await worker.run()


async def start_fallback_scheduler() -> None:
    """Start APScheduler-based scheduler as fallback when Temporal is unavailable."""
    from sardis_v2_core.scheduler import init_scheduler

    logger.warning(
        "Temporal not available — falling back to APScheduler. "
        "This does NOT support horizontal scaling."
    )

    scheduler = init_scheduler()
    # Register the same jobs via APScheduler
    from .scheduled_jobs import (
        expire_approvals,
        expire_holds,
        mandate_cleanup,
        recurring_billing,
        reset_spending_limits,
        treasury_reconciliation,
    )

    scheduler.add_cron_job(reset_spending_limits, "reset_spending_limits", hour=0, minute=0)
    scheduler.add_interval_job(expire_holds, "expire_holds", seconds=300)
    scheduler.add_interval_job(expire_approvals, "expire_approvals", seconds=300)
    scheduler.add_interval_job(recurring_billing, "recurring_billing", seconds=900)
    scheduler.add_interval_job(treasury_reconciliation, "treasury_reconciliation", seconds=3600)
    scheduler.add_interval_job(mandate_cleanup, "mandate_cleanup", seconds=1800)

    await scheduler.start()

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        await scheduler.shutdown()


async def main() -> None:
    """Entry point: try Temporal, fall back to APScheduler."""
    use_temporal = os.getenv("SARDIS_USE_TEMPORAL", "").strip().lower() in ("1", "true", "yes")

    if use_temporal:
        await start_temporal_worker()
    else:
        # Check if Temporal is reachable
        try:
            from temporalio.client import Client

            temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
            await Client.connect(temporal_address, namespace=NAMESPACE)
            logger.info("Temporal server reachable — using Temporal worker")
            await start_temporal_worker()
        except Exception:
            await start_fallback_scheduler()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
