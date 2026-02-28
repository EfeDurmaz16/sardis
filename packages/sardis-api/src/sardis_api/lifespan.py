"""Application lifespan management: startup, shutdown, and graceful drain."""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
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
        except Exception as e:  # noqa: BLE001
            env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
            if env in {"prod", "production"}:
                raise
            logger.warning(f"Could not initialize database schema in non-prod mode: {e}")

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

            async def _recurring_billing_job() -> None:
                from .routers.metrics import background_jobs_total

                runner = getattr(app.state, "recurring_billing_runner", None)
                if runner is None:
                    return
                try:
                    limit = int(os.getenv("SARDIS_RECURRING_BILLING_BATCH_SIZE", "50"))
                    results = await runner(limit=limit)
                    status_value = "warning" if any(r.status == "failed" for r in results) else "success"
                    background_jobs_total.labels(job_name="recurring_billing", status=status_value).inc()
                    if results:
                        logger.info(
                            "Recurring billing job processed=%s charged=%s failed=%s",
                            len(results),
                            sum(1 for item in results if item.status == "charged"),
                            sum(1 for item in results if item.status == "failed"),
                        )
                except Exception as e:
                    background_jobs_total.labels(job_name="recurring_billing", status="error").inc()
                    logger.exception("Recurring billing job failed: %s", e)

            scheduler.add_interval_job(
                _recurring_billing_job,
                job_id="recurring_billing",
                seconds=int(os.getenv("SARDIS_RECURRING_BILLING_INTERVAL_SECONDS", "60")),
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

            async def _canonical_reconciliation_guard_job() -> None:
                from .routers.metrics import background_jobs_total

                canonical_repo = getattr(app.state, "canonical_ledger_repo", None)
                if canonical_repo is None:
                    return
                try:
                    stale_processing_minutes = int(os.getenv("SARDIS_CANONICAL_STALE_PROCESSING_MINUTES", "30"))
                    org_ids: set[str] = set()
                    treasury_repo = getattr(app.state, "treasury_repo", None)
                    if treasury_repo is not None:
                        org_ids.update(await treasury_repo.list_organization_ids())
                    if not org_ids:
                        default_org = os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")
                        org_ids.add(default_org)

                    stale_reviews = 0
                    for org_id in sorted(org_ids):
                        journeys = await canonical_repo.list_journeys(org_id, limit=1000)
                        for journey in journeys:
                            state_value = str(journey.get("canonical_state", "")).lower()
                            if state_value == "settled":
                                expected = int(journey.get("expected_amount_minor", 0) or 0)
                                settled = int(journey.get("settled_amount_minor", 0) or 0)
                                tolerance = int(os.getenv("SARDIS_CANONICAL_DRIFT_TOLERANCE_MINOR", "1000"))
                                if expected > 0 and abs(expected - settled) > tolerance:
                                    await canonical_repo.enqueue_manual_review(
                                        organization_id=org_id,
                                        journey_id=str(journey.get("journey_id")),
                                        reason_code="drift_mismatch",
                                        priority="high",
                                        payload={
                                            "expected_amount_minor": expected,
                                            "settled_amount_minor": settled,
                                            "delta_minor": abs(expected - settled),
                                            "source": "canonical_guard_job",
                                        },
                                    )
                            elif state_value in {"processing", "authorized", "created"}:
                                last_event_at = journey.get("last_event_at")
                                if isinstance(last_event_at, datetime):
                                    age_minutes = (datetime.now(timezone.utc) - last_event_at).total_seconds() / 60.0
                                elif isinstance(last_event_at, str):
                                    try:
                                        parsed = datetime.fromisoformat(last_event_at.replace("Z", "+00:00"))
                                        age_minutes = (datetime.now(timezone.utc) - parsed).total_seconds() / 60.0
                                    except Exception:
                                        age_minutes = 0.0
                                else:
                                    age_minutes = 0.0
                                if age_minutes >= stale_processing_minutes:
                                    created = await canonical_repo.enqueue_manual_review(
                                        organization_id=org_id,
                                        journey_id=str(journey.get("journey_id")),
                                        reason_code="stale_processing",
                                        priority="medium",
                                        payload={
                                            "state": state_value,
                                            "age_minutes": int(age_minutes),
                                            "source": "canonical_guard_job",
                                        },
                                    )
                                    if created:
                                        stale_reviews += 1
                    status_value = "warning" if stale_reviews > 0 else "success"
                    background_jobs_total.labels(job_name="canonical_reconciliation_guard", status=status_value).inc()
                except Exception as e:
                    background_jobs_total.labels(job_name="canonical_reconciliation_guard", status="error").inc()
                    logger.exception("Canonical reconciliation guard job failed: %s", e)

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
            scheduler.add_interval_job(
                _canonical_reconciliation_guard_job,
                job_id="canonical_reconciliation_guard",
                seconds=600,
            )
            await scheduler.start()
            app.state.scheduler = scheduler
            logger.info("Background scheduler started with jobs registered")

    # Deposit monitor (opt-in via SARDIS_ENABLE_DEPOSIT_MONITOR=1)
    enable_deposit_monitor = os.getenv("SARDIS_ENABLE_DEPOSIT_MONITOR", "").lower() in (
        "1", "true", "yes", "on",
    )
    if enable_deposit_monitor:
        try:
            from sardis_chain.deposit_monitor import DepositMonitor, MonitorConfig

            monitor_config = MonitorConfig(
                chains=[c.strip() for c in os.getenv("SARDIS_DEPOSIT_MONITOR_CHAINS", "base_sepolia").split(",") if c.strip()],
                confirmations_required=int(os.getenv("SARDIS_DEPOSIT_CONFIRMATIONS", "1")),
                poll_interval=float(os.getenv("SARDIS_DEPOSIT_POLL_INTERVAL", "5.0")),
            )
            deposit_monitor = DepositMonitor(config=monitor_config)

            inbound_service = getattr(app.state, "inbound_payment_service", None)
            if inbound_service:
                # Wire monitor into service and register callback
                inbound_service._deposit_monitor = deposit_monitor
                deposit_monitor.add_callback(inbound_service.on_deposit_callback)
                # Register all existing wallet addresses
                registered = await inbound_service.register_wallet_addresses()
                logger.info("DepositMonitor: registered %d wallet addresses", registered)

            await deposit_monitor.start()
            app.state.deposit_monitor = deposit_monitor
            logger.info("DepositMonitor started (chains=%s)", monitor_config.chains)
        except ImportError:
            logger.warning("DepositMonitor enabled but sardis_chain.deposit_monitor not available")
        except Exception as e:
            logger.warning("DepositMonitor startup failed: %s", e)

    app.state.startup_time = time.time()
    app.state.ready = True
    logger.info("Sardis API started successfully")

    yield

    # --- Shutdown ---
    logger.info("Shutting down Sardis API...")
    shutdown_state.start_shutdown()
    await shutdown_state.wait_for_requests()

    # Stop deposit monitor
    if hasattr(app.state, "deposit_monitor") and app.state.deposit_monitor:
        try:
            await app.state.deposit_monitor.stop()
            logger.info("DepositMonitor stopped")
        except (RuntimeError, OSError, ValueError, AttributeError) as e:
            logger.warning(f"Error stopping DepositMonitor: {e}")

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
