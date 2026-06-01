"""Observability bootstrap helpers.

Focused setup for error monitoring (Sentry) and distributed tracing
(OpenTelemetry). Extracted from the API composition root so ``main.py``
stays a thin wiring file — these helpers are pure side-effecting setup with
no money-path logic.
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from sardis.core import SardisSettings

logger = logging.getLogger("server.api")


def init_sentry(settings: SardisSettings) -> None:
    """Initialize Sentry error monitoring if ``SENTRY_DSN`` is configured.

    No-op when the DSN is unset or the SDK is not installed.
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    if not sentry_dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1 if settings.is_production else 1.0,
            profiles_sample_rate=0.1 if settings.is_production else 1.0,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                AsyncPGIntegration(),
            ],
            send_default_pii=False,
        )
        logger.info("Sentry monitoring initialized")
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed")


def init_otel(settings: SardisSettings) -> None:
    """Initialize OpenTelemetry tracing + asyncpg instrumentation.

    No-op unless ``settings.otel_enabled``. Failures are logged and swallowed
    so observability problems never block API startup.
    """
    if not settings.otel_enabled:
        return
    try:
        from .telemetry import init_telemetry, instrument_asyncpg

        init_telemetry(
            service_name=settings.otel_service_name,
            exporter=settings.otel_exporter,
            endpoint=settings.otel_endpoint,
            sample_rate=settings.otel_sample_rate,
        )
        instrument_asyncpg()
    except Exception as exc:
        logger.warning("OpenTelemetry initialization failed: %s", exc)


def instrument_app(app: FastAPI, settings: SardisSettings) -> None:
    """Instrument the FastAPI app with OpenTelemetry after app creation.

    No-op unless ``settings.otel_enabled``. Failures are logged and swallowed.
    """
    if not settings.otel_enabled:
        return
    try:
        from .telemetry import instrument_fastapi

        instrument_fastapi(app)
    except Exception as exc:
        logger.warning("OTEL FastAPI instrumentation failed: %s", exc)
