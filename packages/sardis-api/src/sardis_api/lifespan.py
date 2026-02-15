"""Application lifespan management: startup, shutdown, and graceful drain."""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
import uuid
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

            async def _treasury_reconciliation_job() -> None:
                from .routers.metrics import background_jobs_total

                repo = getattr(app.state, "treasury_repo", None)
                if repo is None:
                    return
                tolerance_minor = int(os.getenv("SARDIS_TREASURY_RECON_TOLERANCE_MINOR", "1000"))
                try:
                    org_ids = await repo.list_organization_ids()
                    mismatches = 0
                    for org_id in org_ids:
                        snapshots = await repo.list_latest_balance_snapshots(org_id)
                        if not snapshots:
                            continue
                        snapshot_total = sum(int(s.get("total_amount_minor", 0) or 0) for s in snapshots)
                        payments = await repo.list_payments_for_reconciliation(
                            org_id,
                            status_filter=["SETTLED", "RELEASED", "RETURNED"],
                            limit=1000,
                        )
                        expected_total = 0
                        for p in payments:
                            status_value = str(p.get("status", "")).upper()
                            amount_minor = int(p.get("amount_minor", 0) or 0)
                            if status_value in {"SETTLED", "RELEASED"}:
                                expected_total += amount_minor
                            elif status_value == "RETURNED":
                                expected_total -= amount_minor
                        delta = abs(snapshot_total - expected_total)
                        if delta > tolerance_minor:
                            mismatches += 1
                            logger.warning(
                                "Treasury reconciliation mismatch org=%s snapshot_total=%s expected_total=%s delta=%s tolerance=%s",
                                org_id,
                                snapshot_total,
                                expected_total,
                                delta,
                                tolerance_minor,
                            )
                    status_value = "warning" if mismatches > 0 else "success"
                    background_jobs_total.labels(job_name="treasury_reconciliation", status=status_value).inc()
                except Exception as e:
                    background_jobs_total.labels(job_name="treasury_reconciliation", status="error").inc()
                    logger.exception("Treasury reconciliation job failed: %s", e)

            async def _treasury_retry_returns_job() -> None:
                from .routers.metrics import background_jobs_total
                from .providers.lithic_treasury import CreatePaymentRequest

                repo = getattr(app.state, "treasury_repo", None)
                lithic_client = getattr(app.state, "lithic_treasury_client", None)
                if repo is None or lithic_client is None:
                    return
                max_batch = int(os.getenv("SARDIS_TREASURY_RETRY_BATCH_SIZE", "20"))
                try:
                    org_ids = await repo.list_organization_ids()
                    retries = 0
                    for org_id in org_ids:
                        retryable = await repo.list_retryable_payments(
                            org_id,
                            max_retry_count=2,
                            limit=max_batch,
                        )
                        for payment in retryable:
                            fa = str(payment.get("financial_account_token", ""))
                            eba = str(payment.get("external_bank_account_token", ""))
                            amount_minor = int(payment.get("amount_minor", 0) or 0)
                            direction = str(payment.get("direction", "COLLECTION")).upper()
                            method = str(payment.get("method", "ACH_NEXT_DAY")).upper()
                            sec_code = str(payment.get("sec_code", "CCD")).upper()
                            if not fa or not eba or amount_minor <= 0:
                                continue
                            try:
                                retried = await lithic_client.create_payment(
                                    CreatePaymentRequest(
                                        financial_account_token=fa,
                                        external_bank_account_token=eba,
                                        payment_type="COLLECTION" if direction == "COLLECTION" else "PAYMENT",
                                        amount=amount_minor,
                                        method="ACH_SAME_DAY" if method == "ACH_SAME_DAY" else "ACH_NEXT_DAY",
                                        sec_code="PPD" if sec_code == "PPD" else ("WEB" if sec_code == "WEB" else "CCD"),
                                        memo=f"retry:{payment.get('payment_token')}",
                                        idempotency_token=str(uuid.uuid4()),
                                        user_defined_id=payment.get("user_defined_id"),
                                    )
                                )
                                await repo.increment_retry_count(org_id, str(payment.get("payment_token")))
                                await repo.upsert_ach_payment(org_id, retried.raw or {})
                                await repo.append_ach_events(org_id, retried.token, retried.events)
                                retries += 1
                            except Exception:
                                logger.exception(
                                    "Treasury retry failed org=%s payment_token=%s",
                                    org_id,
                                    payment.get("payment_token"),
                                )
                    background_jobs_total.labels(job_name="treasury_retry_returns", status="success").inc()
                    if retries:
                        logger.info("Treasury retry job completed retries=%s", retries)
                except Exception as e:
                    background_jobs_total.labels(job_name="treasury_retry_returns", status="error").inc()
                    logger.exception("Treasury retry job failed: %s", e)

            scheduler.add_interval_job(
                _treasury_reconciliation_job,
                job_id="treasury_reconciliation",
                seconds=900,
            )
            scheduler.add_interval_job(
                _treasury_retry_returns_job,
                job_id="treasury_retry_returns",
                seconds=600,
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
