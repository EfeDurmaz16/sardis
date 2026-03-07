"""OpenTelemetry distributed tracing setup.

Runs alongside Sentry (not a replacement). Provides trace context propagation
through the 6-phase orchestrator and structured log correlation.

Configuration via SARDIS_OTEL_* env vars (see SardisSettings in config.py).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_TRACER_PROVIDER = None


def init_telemetry(
    service_name: str = "sardis-api",
    exporter: str = "sentry",
    endpoint: str = "",
    sample_rate: float = 0.1,
) -> None:
    """Initialize OpenTelemetry tracing.

    Args:
        service_name: OTEL service name.
        exporter: One of "sentry", "otlp", "console", "none".
        endpoint: OTLP collector endpoint (when exporter="otlp").
        sample_rate: Fraction of traces to sample (0.0-1.0).
    """
    global _TRACER_PROVIDER

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
        from opentelemetry.sdk.resources import Resource
    except ImportError:
        logger.warning("opentelemetry-sdk not installed — tracing disabled")
        return

    if _TRACER_PROVIDER is not None:
        return  # already initialized

    resource = Resource.create({"service.name": service_name})
    sampler = TraceIdRatioBased(sample_rate)
    provider = TracerProvider(resource=resource, sampler=sampler)

    # Configure exporter
    if exporter == "otlp" and endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info("OTEL: OTLP exporter -> %s", endpoint)
        except ImportError:
            logger.warning(
                "opentelemetry-exporter-otlp not installed — OTLP export disabled"
            )
    elif exporter == "console":
        from opentelemetry.sdk.trace.export import (
            ConsoleSpanExporter,
            SimpleSpanProcessor,
        )

        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        logger.info("OTEL: Console exporter enabled")
    elif exporter == "sentry":
        # Sentry's own OTEL integration picks up the TracerProvider automatically.
        # Just setting the provider is enough — Sentry SDK >= 2.x bridges spans.
        logger.info("OTEL: Sentry bridge mode (TracerProvider set, Sentry SDK bridges spans)")
    else:
        logger.info("OTEL: No exporter configured (trace context propagation only)")

    trace.set_tracer_provider(provider)
    _TRACER_PROVIDER = provider

    logger.info(
        "OpenTelemetry initialized: service=%s, exporter=%s, sample_rate=%s",
        service_name,
        exporter,
        sample_rate,
    )


def instrument_fastapi(app) -> None:
    """Auto-instrument a FastAPI app with OTEL."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("OTEL: FastAPI instrumented")
    except ImportError:
        logger.debug("opentelemetry-instrumentation-fastapi not available")


def instrument_asyncpg() -> None:
    """Auto-instrument asyncpg with OTEL."""
    try:
        from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor

        AsyncPGInstrumentor().instrument()
        logger.info("OTEL: asyncpg instrumented")
    except ImportError:
        logger.debug("opentelemetry-instrumentation-asyncpg not available")


def get_tracer(name: str = "sardis"):
    """Get an OTEL tracer for manual span creation.

    Usage in orchestrator phases::

        tracer = get_tracer("sardis.orchestrator")
        with tracer.start_as_current_span("phase.policy_check") as span:
            span.set_attribute("mandate_id", mandate_id)
            ...
    """
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except ImportError:
        return _NoOpTracer()


def get_current_trace_id() -> Optional[str]:
    """Return the current trace ID as a hex string, or None."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id:
            return format(ctx.trace_id, "032x")
    except ImportError:
        pass
    return None


def get_current_span_id() -> Optional[str]:
    """Return the current span ID as a hex string, or None."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.span_id:
            return format(ctx.span_id, "016x")
    except ImportError:
        pass
    return None


class _NoOpTracer:
    """Fallback when OTEL SDK is not installed."""

    class _NoOpSpan:
        def set_attribute(self, key, value):
            pass

        def set_status(self, status):
            pass

        def record_exception(self, exc):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def start_as_current_span(self, name, **kwargs):
        return self._NoOpSpan()

    def start_span(self, name, **kwargs):
        return self._NoOpSpan()
