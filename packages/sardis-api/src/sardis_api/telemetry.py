"""OpenTelemetry instrumentation for Sardis API.

Auto-instruments FastAPI endpoints and provides manual span helpers
for tracing payment pipeline phases.

Setup:
    pip install opentelemetry-sdk opentelemetry-instrumentation-fastapi \
                opentelemetry-exporter-otlp-proto-http

Environment variables:
    OTEL_EXPORTER_OTLP_ENDPOINT — OTLP endpoint (e.g., https://otlp-gateway-prod-us-east-0.grafana.net/otlp)
    OTEL_EXPORTER_OTLP_HEADERS — Auth headers (e.g., Authorization=Basic ...)
    OTEL_SERVICE_NAME — Service name (default: sardis-api)
    SARDIS_OTEL_ENABLED — Set to "1" to enable (default: disabled)
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

_logger = logging.getLogger(__name__)

_tracer = None
_enabled = False


def init_telemetry(app: Any = None) -> None:
    """Initialize OpenTelemetry instrumentation.

    Call once during app startup. No-op if SARDIS_OTEL_ENABLED != "1".
    """
    global _tracer, _enabled

    if os.getenv("SARDIS_OTEL_ENABLED", "").strip() not in ("1", "true", "yes"):
        _logger.info("OpenTelemetry disabled (set SARDIS_OTEL_ENABLED=1 to enable)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({
            "service.name": os.getenv("OTEL_SERVICE_NAME", "sardis-api"),
            "service.version": "2.0.0",
            "deployment.environment": os.getenv("SARDIS_ENVIRONMENT", "dev"),
        })

        provider = TracerProvider(resource=resource)

        # OTLP exporter (works with Grafana Cloud, Jaeger, etc.)
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            exporter = OTLPSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except ImportError:
            _logger.warning("OTLP exporter not installed, traces will be logged only")

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("sardis-api")
        _enabled = True

        # Auto-instrument FastAPI if app provided
        if app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor.instrument_app(app)
                _logger.info("FastAPI auto-instrumented with OpenTelemetry")
            except ImportError:
                _logger.warning("FastAPI instrumentor not installed")

        _logger.info("OpenTelemetry initialized")

    except ImportError:
        _logger.info("OpenTelemetry SDK not installed, tracing disabled")


@contextmanager
def trace_phase(phase_name: str, **attributes: Any) -> Generator[None, None, None]:
    """Trace a payment pipeline phase.

    Usage:
        with trace_phase("policy_check", agent_id="agent_123", amount=50.0):
            result = await policy_engine.evaluate(...)
    """
    if not _enabled or _tracer is None:
        yield
        return

    with _tracer.start_as_current_span(
        f"sardis.{phase_name}",
        attributes={f"sardis.{k}": str(v) for k, v in attributes.items()},
    ):
        yield


def trace_event(name: str, **attributes: Any) -> None:
    """Record an event on the current span."""
    if not _enabled:
        return

    from opentelemetry import trace
    span = trace.get_current_span()
    if span:
        span.add_event(name, attributes={k: str(v) for k, v in attributes.items()})
