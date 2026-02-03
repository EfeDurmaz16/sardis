"""Background job scheduler for Sardis."""
from __future__ import annotations

import logging
from typing import Callable, Optional, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

logger = logging.getLogger("sardis.scheduler")


class SardisScheduler:
    """APScheduler wrapper for Sardis background jobs."""

    def __init__(
        self,
        database_url: Optional[str] = None,
        timezone: str = "UTC",
    ):
        # Job store for persistence (survives restarts)
        jobstores = {}
        if database_url:
            jobstores["default"] = SQLAlchemyJobStore(url=database_url)

        # Async executor for FastAPI compatibility
        executors = {
            "default": AsyncIOExecutor(),
        }

        job_defaults = {
            "coalesce": True,      # Combine missed runs into one
            "max_instances": 1,    # Only one instance per job
            "misfire_grace_time": 60 * 5,  # 5 min grace period
        }

        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=timezone,
        )
        self._started = False

    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        *,
        hour: int = 0,
        minute: int = 0,
        day_of_week: str = "*",
        **kwargs: Any,
    ) -> None:
        """Register a cron-style job."""
        self._scheduler.add_job(
            func,
            "cron",
            id=job_id,
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            replace_existing=True,
            **kwargs,
        )
        logger.info(f"Registered cron job: {job_id}")

    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        *,
        seconds: int = 300,
        **kwargs: Any,
    ) -> None:
        """Register an interval job."""
        self._scheduler.add_job(
            func,
            "interval",
            id=job_id,
            seconds=seconds,
            replace_existing=True,
            **kwargs,
        )
        logger.info(f"Registered interval job: {job_id} (every {seconds}s)")

    async def start(self) -> None:
        """Start the scheduler."""
        if not self._started:
            self._scheduler.start()
            self._started = True
            logger.info("Scheduler started")

    async def shutdown(self, wait: bool = True) -> None:
        """Stop the scheduler gracefully."""
        if self._started:
            self._scheduler.shutdown(wait=wait)
            self._started = False
            logger.info("Scheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._started and self._scheduler.running


# Singleton instance
_scheduler: Optional[SardisScheduler] = None


def get_scheduler() -> SardisScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")
    return _scheduler


def init_scheduler(database_url: Optional[str] = None) -> SardisScheduler:
    """Initialize the global scheduler."""
    global _scheduler
    _scheduler = SardisScheduler(database_url=database_url)
    return _scheduler
