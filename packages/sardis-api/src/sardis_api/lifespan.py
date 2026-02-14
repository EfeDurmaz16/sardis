"""Application lifespan management: startup, shutdown, and graceful drain."""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI

from sardis_v2_core.jobs.spending_reset import reset_spending_limits
from sardis_v2_core.jobs.hold_expiry import expire_holds
from sardis_v2_core.jobs.approval_expiry import expire_approvals
from .middleware import API_VERSION

logger = logging.getLogger("sardis.api")

# ---------------------------------------------------------------------------
# Shutdown primitives
# ---------------------------------------------------------------------------
_shutdown_event: Optional[asyncio.Event] = None


def get_shutdown_event() -> asyncio.Event:
    """Get or create the shutdown event."""
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()
    return _shutdown_event


class GracefulShutdownState:
    """Track state for graceful shutdown."""

    def __init__(self) -> None:
        self.is_shutting_down = False
        self.active_requests = 0
        self.shutdown_started_at: Optional[float] = None
        self.max_shutdown_wait_seconds = 30

    def start_shutdown(self) -> None:
        self.is_shutting_down = True
        self.shutdown_started_at = time.time()
        logger.info(
            "Graceful shutdown initiated",
            extra={
                "active_requests": self.active_requests,
                "max_wait_seconds": self.max_shutdown_wait_seconds,
            },
        )

    def request_started(self) -> None:
        self.active_requests += 1

    def request_finished(self) -> None:
        self.active_requests = max(0, self.active_requests - 1)

    async def wait_for_requests(self) -> bool:
        """Wait for active requests to complete. Returns True if successful."""
        if self.active_requests == 0:
            return True
        start = time.time()
        while self.active_requests > 0:
            if time.time() - start > self.max_shutdown_wait_seconds:
                logger.warning(
                    f"Shutdown timeout: {self.active_requests} requests still active"
                )
                return False
            await asyncio.sleep(0.1)
        return True


# Module-level singleton
shutdown_state = GracefulShutdownState()


# ---------------------------------------------------------------------------
# Lifespan context manager
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    logger.info(
        "Starting Sardis API...",
        extra={
            "version": API_VERSION,
            "environment": os.getenv("SARDIS_ENVIRONMENT", "dev"),
            "python_version": sys.version.split()[0],
        },
    )

    # Initialize database if using PostgreSQL
    database_url = os.getenv("DATABASE_URL", "")
    if database_url and (
        database_url.startswith("postgresql://") or database_url.startswith("postgres://")
    ):
        try:
            from sardis_v2_core.database import init_database
            await init_database()
            logger.info("Database schema initialized")
        except (ImportError, OSError, RuntimeError, ValueError) as e:
            logger.warning(f"Could not initialize database schema: {e}")

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def signal_handler(sig):
        logger.info(f"Received signal {sig.name}")
        shutdown_state.start_shutdown()
        get_shutdown_event().set()

    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    # Background scheduler (opt-in via SARDIS_ENABLE_SCHEDULER=1)
    enable_scheduler = os.getenv("SARDIS_ENABLE_SCHEDULER", "").lower() in (
        "1", "true", "yes", "on",
    )
    if enable_scheduler:
        try:
            from sardis_v2_core.scheduler import init_scheduler
        except (ImportError, OSError, RuntimeError, ValueError) as e:
            logger.warning("Background scheduler disabled (init failed): %s", e)
        else:
            database_url = os.getenv("DATABASE_URL", "")
            scheduler = init_scheduler(
                database_url=database_url if database_url.startswith("postgresql") else None
            )
            scheduler.add_cron_job(
                reset_spending_limits, job_id="spending_reset_daily", hour=0, minute=0,
            )
            scheduler.add_interval_job(
                expire_holds, job_id="hold_expiry_check", seconds=300,
            )
            scheduler.add_interval_job(
                expire_approvals, job_id="approval_expiry_check", seconds=60,
            )
            await scheduler.start()
            app.state.scheduler = scheduler
            logger.info("Background scheduler started with jobs registered")

    app.state.startup_time = time.time()
    app.state.ready = True
    logger.info("Sardis API started successfully")

    yield

    # --- Shutdown ---
    logger.info("Shutting down Sardis API...")
    shutdown_state.start_shutdown()
    await shutdown_state.wait_for_requests()

    if hasattr(app.state, "scheduler"):
        try:
            await app.state.scheduler.shutdown(wait=True)
        except (RuntimeError, OSError, ValueError, AttributeError) as e:
            logger.warning(f"Error shutting down scheduler: {e}")

    if hasattr(app.state, "turnkey_client") and app.state.turnkey_client:
        try:
            await app.state.turnkey_client.close()
        except (RuntimeError, OSError, ValueError, AttributeError) as e:
            logger.warning(f"Error closing Turnkey client: {e}")

    if hasattr(app.state, "cache_service"):
        try:
            await app.state.cache_service.close()
        except (RuntimeError, OSError, ValueError, AttributeError) as e:
            logger.warning(f"Error closing cache service: {e}")

    logger.info("Sardis API shutdown complete")
