"""Prometheus metrics endpoint for monitoring and observability."""
from __future__ import annotations

import os
import time
from typing import Optional

from fastapi import APIRouter, Depends, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    REGISTRY,
)

from sardis_api.authz import Principal, metrics_auth_required, require_principal

router = APIRouter(tags=["monitoring"])

# Application info
app_info = Info("sardis_app", "Sardis application information")
app_info.info({"version": "2.0.0", "environment": os.getenv("SARDIS_ENVIRONMENT", "dev")})

# Request metrics
http_requests_total = Counter(
    "sardis_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "sardis_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Business metrics
payments_total = Counter(
    "sardis_payments_total",
    "Total payment transactions",
    ["chain", "token", "status"],
)

payment_amount_usd = Histogram(
    "sardis_payment_amount_usd",
    "Payment amounts in USD",
    ["chain", "token"],
    buckets=(1, 10, 50, 100, 500, 1000, 5000, 10000, 50000),
)

# Wallet metrics
wallets_active = Gauge(
    "sardis_wallets_active",
    "Number of active wallets",
)

wallets_frozen = Gauge(
    "sardis_wallets_frozen",
    "Number of frozen wallets",
)

# Policy metrics
policy_checks_total = Counter(
    "sardis_policy_checks_total",
    "Total spending policy checks",
    ["result"],  # "allowed" or "denied"
)

policy_denials_total = Counter(
    "sardis_policy_denials_total",
    "Policy denials by reason",
    ["reason"],
)

# Compliance metrics
compliance_checks_total = Counter(
    "sardis_compliance_checks_total",
    "Total compliance checks",
    ["check_type", "result"],
)

kyc_verifications_total = Counter(
    "sardis_kyc_verifications_total",
    "KYC verification attempts",
    ["provider", "status"],
)

# Approval metrics
approvals_total = Counter(
    "sardis_approvals_total",
    "Total approval requests",
    ["action", "status"],
)

approval_response_time_seconds = Histogram(
    "sardis_approval_response_time_seconds",
    "Time to approve/deny requests",
    ["action"],
    buckets=(60, 300, 900, 1800, 3600, 7200, 14400, 28800, 86400),  # 1min to 1day
)

# Card metrics
card_transactions_total = Counter(
    "sardis_card_transactions_total",
    "Virtual card transactions",
    ["provider", "status"],
)

card_declines_total = Counter(
    "sardis_card_declines_total",
    "Card transaction declines",
    ["reason"],
)

# Chain metrics
chain_rpc_calls_total = Counter(
    "sardis_chain_rpc_calls_total",
    "RPC calls to blockchain nodes",
    ["chain", "method", "result"],
)

chain_gas_used = Histogram(
    "sardis_chain_gas_used",
    "Gas used per transaction",
    ["chain"],
    buckets=(21000, 50000, 100000, 200000, 500000, 1000000),
)

chain_confirmations = Histogram(
    "sardis_chain_confirmations_seconds",
    "Time to transaction confirmation",
    ["chain"],
    buckets=(2, 5, 10, 30, 60, 120, 300, 600),
)

# Database metrics
db_queries_total = Counter(
    "sardis_db_queries_total",
    "Total database queries",
    ["operation", "table"],
)

db_query_duration_seconds = Histogram(
    "sardis_db_query_duration_seconds",
    "Database query duration",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

db_connections_active = Gauge(
    "sardis_db_connections_active",
    "Active database connections",
)

# Cache metrics
cache_operations_total = Counter(
    "sardis_cache_operations_total",
    "Cache operations",
    ["operation", "result"],  # get/set/delete, hit/miss/success/error
)

cache_hit_rate = Gauge(
    "sardis_cache_hit_rate",
    "Cache hit rate (0-1)",
)

# MPC signing metrics
mpc_signing_requests_total = Counter(
    "sardis_mpc_signing_requests_total",
    "MPC signing requests",
    ["provider", "status"],
)

mpc_signing_duration_seconds = Histogram(
    "sardis_mpc_signing_duration_seconds",
    "MPC signing duration",
    ["provider"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

# Webhook metrics
webhooks_received_total = Counter(
    "sardis_webhooks_received_total",
    "Incoming webhooks",
    ["provider", "event_type"],
)

webhooks_sent_total = Counter(
    "sardis_webhooks_sent_total",
    "Outgoing webhooks",
    ["event_type", "status"],
)

# Error metrics
errors_total = Counter(
    "sardis_errors_total",
    "Total errors by type",
    ["error_type", "severity"],
)

# System metrics
api_uptime_seconds = Gauge(
    "sardis_api_uptime_seconds",
    "API uptime in seconds",
)

background_jobs_total = Counter(
    "sardis_background_jobs_total",
    "Background job executions",
    ["job_name", "status"],
)


# Metrics helper functions
def record_payment(chain: str, token: str, amount_usd: float, status: str) -> None:
    """Record a payment transaction metric."""
    payments_total.labels(chain=chain, token=token, status=status).inc()
    if status == "completed":
        payment_amount_usd.labels(chain=chain, token=token).observe(amount_usd)


def record_policy_check(allowed: bool, reason: Optional[str] = None) -> None:
    """Record a policy check metric."""
    result = "allowed" if allowed else "denied"
    policy_checks_total.labels(result=result).inc()
    if not allowed and reason:
        policy_denials_total.labels(reason=reason).inc()


def record_http_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """Record HTTP request metrics."""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def record_approval(action: str, status: str, response_time: Optional[float] = None) -> None:
    """Record approval request metrics."""
    approvals_total.labels(action=action, status=status).inc()
    if response_time and status in ("approved", "denied"):
        approval_response_time_seconds.labels(action=action).observe(response_time)


def record_compliance_check(check_type: str, result: str) -> None:
    """Record compliance check metrics."""
    compliance_checks_total.labels(check_type=check_type, result=result).inc()


def record_chain_rpc(chain: str, method: str, success: bool) -> None:
    """Record chain RPC call metrics."""
    result = "success" if success else "error"
    chain_rpc_calls_total.labels(chain=chain, method=method, result=result).inc()


def record_db_query(operation: str, table: str, duration: float) -> None:
    """Record database query metrics."""
    db_queries_total.labels(operation=operation, table=table).inc()
    db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)


def record_cache_operation(operation: str, hit: bool) -> None:
    """Record cache operation metrics."""
    result = "hit" if hit else "miss"
    cache_operations_total.labels(operation=operation, result=result).inc()


def record_error(error_type: str, severity: str = "error") -> None:
    """Record error metrics."""
    errors_total.labels(error_type=error_type, severity=severity).inc()


if metrics_auth_required():
    @router.get("/metrics")
    async def metrics(_: Principal = Depends(require_principal)) -> Response:
        """
        Expose Prometheus metrics endpoint.

        Returns metrics in Prometheus text exposition format.
        This endpoint should be scraped by Prometheus server.
        """
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )
else:
    @router.get("/metrics")
    async def metrics() -> Response:
        """
        Expose Prometheus metrics endpoint.

        Returns metrics in Prometheus text exposition format.
        This endpoint should be scraped by Prometheus server.
        """
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint for monitoring.

    Returns basic health status without exposing metrics.
    """
    return {
        "status": "healthy",
        "service": "sardis-api",
        "version": "2.0.0",
    }
