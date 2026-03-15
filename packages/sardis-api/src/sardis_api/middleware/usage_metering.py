"""API usage metering middleware with plan enforcement.

Counts API calls per organisation per billing period and enforces
plan-level monthly call limits from PLAN_LIMITS. When an org exceeds
its plan limit the middleware returns HTTP 429 before the request
reaches any route handler.

Usage counters are currently held in-process memory (good enough for a
single-process deployment and testing). Replace ``_usage_counters`` with
a Redis/DB-backed store for multi-replica production deployments.
"""
from __future__ import annotations

import calendar
import logging
import time
from collections import defaultdict
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..billing.config import PLAN_LIMITS, BillingConfig

logger = logging.getLogger("sardis.api.usage_metering")

# Paths that are never subject to usage metering.
EXEMPT_PREFIXES: tuple[str, ...] = (
    "/api/v2/billing",
    "/api/v2/auth",
    "/api/v2/metrics",
    "/health",
    "/api/v2/docs",
    "/sandbox",
)

# In-memory usage counters: org_id -> call count this period.
# TODO: replace with Redis/DB for multi-replica deployments (Task A5).
_usage_counters: dict[str, int] = defaultdict(int)

# TTL cache for org plan lookups: org_id -> (plan_name, timestamp).
# Avoids hitting the DB on every single API request.
_PLAN_CACHE_TTL_SECONDS = 60
_plan_cache: dict[str, tuple[str, float]] = {}


def _period_reset_epoch() -> int:
    """Return the Unix timestamp of the end of the current calendar month (UTC)."""
    now = datetime.now(UTC)
    last_day = calendar.monthrange(now.year, now.month)[1]
    end_of_month = now.replace(
        day=last_day, hour=23, minute=59, second=59, microsecond=0
    )
    return int(end_of_month.timestamp())


async def _lookup_org_plan(org_id: str) -> str:
    """Look up an org's billing plan from the DB with a TTL cache.

    Returns the plan name (free, starter, growth, enterprise).
    Falls back to "free" on any error.
    """
    now = time.monotonic()
    cached = _plan_cache.get(org_id)
    if cached is not None:
        plan, cached_at = cached
        if now - cached_at < _PLAN_CACHE_TTL_SECONDS:
            return plan

    try:
        from sardis_v2_core.database import Database

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT plan FROM billing_subscriptions WHERE org_id = $1 AND status = 'active'",
                org_id,
            )

        plan = row["plan"] if row else "free"
        # Validate the plan name exists in PLAN_LIMITS
        if plan not in PLAN_LIMITS:
            logger.warning("org=%s has unknown plan %r, defaulting to free", org_id, plan)
            plan = "free"

        _plan_cache[org_id] = (plan, now)
        return plan

    except Exception:
        logger.debug("Could not look up plan for org=%s, defaulting to free", org_id, exc_info=True)
        _plan_cache[org_id] = ("free", now)
        return "free"


class UsageMeteringMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that meters API calls and enforces plan limits.

    Behaviour:
    - Skips exempt path prefixes (billing, auth, metrics, health, docs, sandbox).
    - Skips requests with no authenticated org_id on ``request.state``.
    - Returns 429 when the org has consumed all calls for its plan period.
    - Adds ``X-RateLimit-*`` headers to every metered response.
    - Is a complete no-op when billing is not enabled
      (``SARDIS_BILLING_BILLING_ENABLED`` is falsy).
    """

    def __init__(self, app, billing_config: BillingConfig | None = None) -> None:
        super().__init__(app)
        self._billing_config = billing_config or BillingConfig()

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        # No-op when billing feature flag is off.
        if not self._billing_config.billing_enabled:
            return await call_next(request)

        path = request.url.path

        # Exempt paths bypass metering entirely.
        if any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
            return await call_next(request)

        # Org ID is set by auth/RBAC middleware (or absent for public endpoints).
        org_id: str | None = getattr(request.state, "org_id", None)
        if not org_id:
            return await call_next(request)

        plan = await _lookup_org_plan(org_id)
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
        api_limit: int | None = limits.get("api_calls_per_month")

        current = _usage_counters[org_id]

        if api_limit is not None and current >= api_limit:
            logger.warning(
                "org=%s plan=%s hit api call limit (%d/%d)",
                org_id,
                plan,
                current,
                api_limit,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "API rate limit exceeded. Upgrade at sardis.sh/pricing",
                    "plan": plan,
                    "limit": api_limit,
                },
            )

        # Increment before calling downstream so the header reflects actual usage.
        _usage_counters[org_id] += 1
        response: Response = await call_next(request)

        if api_limit is not None:
            remaining = max(0, api_limit - _usage_counters[org_id])
            response.headers["X-RateLimit-Limit"] = str(api_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(_period_reset_epoch())

        return response
