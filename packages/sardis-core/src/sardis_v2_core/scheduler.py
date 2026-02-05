"""Background job scheduler for Sardis.

This module prefers APScheduler for production (persistence + cron support),
but provides a minimal asyncio-based fallback for constrained environments.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

try:
    from apscheduler.executors.asyncio import AsyncIOExecutor  # type: ignore
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore  # type: ignore
    from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore

    _HAS_APSCHEDULER = True
except ModuleNotFoundError:  # pragma: no cover (depends on environment)
    AsyncIOScheduler = None  # type: ignore[assignment]
    SQLAlchemyJobStore = None  # type: ignore[assignment]
    AsyncIOExecutor = None  # type: ignore[assignment]
    _HAS_APSCHEDULER = False

logger = logging.getLogger("sardis.scheduler")

JobCallable = Callable[[], Awaitable[object] | object]


@dataclass(slots=True)
class _IntervalJob:
    func: JobCallable
    seconds: int
    task: Optional[asyncio.Task[None]] = None


class SardisScheduler:
    """Background job scheduler with APScheduler + asyncio fallback."""

    def __init__(
        self,
        database_url: Optional[str] = None,
        timezone: str = "UTC",
    ):
        self._database_url = database_url
        self._timezone = timezone
        self._started = False

        self._interval_jobs: dict[str, _IntervalJob] = {}
        self._cron_jobs: dict[str, JobCallable] = {}

        if _HAS_APSCHEDULER:
            jobstores: dict[str, object] = {}
            if database_url:
                jobstores["default"] = SQLAlchemyJobStore(url=database_url)  # type: ignore[misc]

            executors = {"default": AsyncIOExecutor()}  # type: ignore[misc]
            job_defaults = {
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 60 * 5,
            }

            self._scheduler = AsyncIOScheduler(  # type: ignore[misc]
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone=timezone,
            )
        else:
            self._scheduler = None

    def add_cron_job(
        self,
        func: JobCallable,
        job_id: str,
        *,
        hour: int = 0,
        minute: int = 0,
        day_of_week: str = "*",
        **kwargs: Any,
    ) -> None:
        """Register a cron-style job."""
        if self._scheduler is not None:
            self._scheduler.add_job(  # type: ignore[union-attr]
                func,
                "cron",
                id=job_id,
                hour=hour,
                minute=minute,
                day_of_week=day_of_week,
                replace_existing=True,
                **kwargs,
            )
        else:
            # Fallback: store only (cron execution isn't used in tests).
            self._cron_jobs[job_id] = func
            logger.warning(
                "Cron job '%s' registered but will NOT execute (APScheduler not available). "
                "Install apscheduler for cron support.",
                job_id,
            )
        logger.info("Registered cron job: %s", job_id)

    def add_interval_job(
        self,
        func: JobCallable,
        job_id: str,
        *,
        seconds: int = 300,
        **kwargs: Any,
    ) -> None:
        """Register an interval job."""
        if self._scheduler is not None:
            self._scheduler.add_job(  # type: ignore[union-attr]
                func,
                "interval",
                id=job_id,
                seconds=seconds,
                replace_existing=True,
                **kwargs,
            )
            logger.info("Registered interval job: %s (every %ss)", job_id, seconds)
            return

        existing = self._interval_jobs.get(job_id)
        if existing and existing.task:
            existing.task.cancel()
        self._interval_jobs[job_id] = _IntervalJob(func=func, seconds=seconds)
        if self._started:
            self._start_interval_job(job_id)
        logger.info("Registered interval job: %s (every %ss)", job_id, seconds)

    def _start_interval_job(self, job_id: str) -> None:
        job = self._interval_jobs.get(job_id)
        if not job:
            return

        async def _runner() -> None:
            while self._started:
                await asyncio.sleep(job.seconds)
                if not self._started:
                    return
                try:
                    result = job.func()
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error("Scheduler job failed: %s - %s: %s", job_id, type(e).__name__, e)
                    raise

        job.task = asyncio.create_task(_runner())

    async def start(self) -> None:
        """Start the scheduler."""
        if self._started:
            return

        if self._scheduler is not None:
            self._scheduler.start()  # type: ignore[union-attr]
        else:
            for job_id in list(self._interval_jobs.keys()):
                self._start_interval_job(job_id)

        self._started = True
        logger.info("Scheduler started")

    async def shutdown(self, wait: bool = True) -> None:
        """Stop the scheduler gracefully."""
        if not self._started:
            return

        if self._scheduler is not None:
            self._scheduler.shutdown(wait=wait)  # type: ignore[union-attr]
        else:
            for job in self._interval_jobs.values():
                if job.task:
                    job.task.cancel()
            if wait:
                await asyncio.sleep(0)

        self._started = False
        logger.info("Scheduler stopped")

    @property
    def is_running(self) -> bool:
        if self._scheduler is not None:
            return self._started and bool(self._scheduler.running)  # type: ignore[union-attr]
        return self._started


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
