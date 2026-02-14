"""Health-check endpoints: liveness, readiness, and deep component checks."""
from __future__ import annotations

import logging
import os
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .middleware import API_VERSION

logger = logging.getLogger("sardis.api")

router = APIRouter(tags=["health"])


def create_health_router(
    *,
    shutdown_state,
    use_postgres: bool,
    database_url: str,
    redis_url: str,
    settings,
) -> APIRouter:
    """Build a health-check router closed over runtime dependencies."""

    health_router = APIRouter(tags=["health"])

    @health_router.get("/")
    def root():
        """Root endpoint with service information."""
        return {
            "service": "Sardis API",
            "version": API_VERSION,
            "status": "healthy",
            "docs": "/api/v2/docs",
            "health": "/health",
        }

    @health_router.get("/live")
    def liveness():
        """Kubernetes liveness probe."""
        return {"status": "alive"}

    @health_router.get("/ready")
    def readiness():
        """Kubernetes readiness probe."""
        from fastapi import Request

        if shutdown_state.is_shutting_down:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "shutting_down",
                    "message": "Service is shutting down",
                },
            )
        return {"status": "ready"}

    @health_router.get("/health")
    async def health_check():
        """Deep health check endpoint with component status."""
        start_time = time.time()

        startup_time = time.time()  # fallback
        uptime_seconds = 0

        components = {
            "api": {"status": "up", "uptime_seconds": uptime_seconds},
            "database": {"status": "unknown", "type": "postgresql" if use_postgres else "memory"},
            "chain_executor": {"status": "up", "mode": settings.chain_mode},
            "cache": {"status": "unknown", "type": "unknown"},
            "stripe": {"status": "unconfigured"},
            "turnkey": {"status": "unconfigured"},
            "webhooks": {"status": "unknown"},
        }
        overall_healthy = True
        checks_passed = 0
        checks_total = 0

        # Database
        checks_total += 1
        try:
            if use_postgres:
                import asyncpg
                conn = await asyncpg.connect(database_url, timeout=5)
                await conn.execute("SELECT 1")
                await conn.close()
                components["database"]["status"] = "connected"
                components["database"]["latency_ms"] = int((time.time() - start_time) * 1000)
                checks_passed += 1
            else:
                components["database"]["status"] = "in_memory"
                checks_passed += 1
        except (ImportError, OSError, RuntimeError, ValueError) as e:
            logger.warning(f"Database health check failed: {e}")
            components["database"]["status"] = "disconnected"
            components["database"]["error"] = str(e)
            overall_healthy = False

        # Cache
        checks_total += 1
        cache_start = time.time()
        try:
            # Cache service is not directly available here; report based on config
            if redis_url:
                components["cache"]["status"] = "configured"
                components["cache"]["type"] = "redis"
            else:
                components["cache"]["status"] = "in_memory"
                components["cache"]["type"] = "in_memory"
            checks_passed += 1
        except (OSError, RuntimeError, ValueError) as e:
            logger.warning(f"Cache health check failed: {e}")
            components["cache"]["status"] = "error"
            components["cache"]["error"] = str(e)

        # Stripe
        stripe_key = os.getenv("STRIPE_SECRET_KEY")
        if stripe_key:
            checks_total += 1
            stripe_start = time.time()
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        "https://api.stripe.com/v1/balance",
                        headers={"Authorization": f"Bearer {stripe_key}"},
                    )
                    if resp.status_code == 200:
                        components["stripe"]["status"] = "connected"
                        components["stripe"]["latency_ms"] = int(
                            (time.time() - stripe_start) * 1000
                        )
                        checks_passed += 1
                    else:
                        components["stripe"]["status"] = "auth_error"
                        components["stripe"]["http_status"] = resp.status_code
                        overall_healthy = False
            except (ImportError, OSError, TimeoutError, RuntimeError, ValueError) as e:
                logger.warning(f"Stripe health check failed: {e}")
                components["stripe"]["status"] = "unreachable"
                components["stripe"]["error"] = str(e)
                overall_healthy = False

        # Turnkey
        turnkey_key = os.getenv("TURNKEY_API_KEY")
        if turnkey_key:
            checks_total += 1
            turnkey_start = time.time()
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        "https://api.turnkey.com/public/v1/query/get_whoami",
                        headers={"X-Stamp-WebAuthn": ""},
                        json={"organizationId": os.getenv("TURNKEY_ORGANIZATION_ID", "")},
                    )
                    components["turnkey"]["status"] = "reachable"
                    components["turnkey"]["latency_ms"] = int(
                        (time.time() - turnkey_start) * 1000
                    )
                    checks_passed += 1
            except (ImportError, OSError, TimeoutError, RuntimeError, ValueError) as e:
                logger.warning(f"Turnkey health check failed: {e}")
                components["turnkey"]["status"] = "unreachable"
                components["turnkey"]["error"] = str(e)
                overall_healthy = False
        else:
            components["turnkey"]["status"] = "unconfigured"

        # RPC
        checks_total += 1
        try:
            chain_name = (
                settings.chain_mode if settings.chain_mode != "simulated" else "base_sepolia"
            )
            components["rpc"] = {"status": "not_initialized"}
            checks_passed += 1
        except (AttributeError, OSError, RuntimeError, ValueError) as e:
            logger.warning(f"RPC health check failed: {e}")
            components["rpc"] = {"status": "error", "error": str(e)}
            overall_healthy = False

        # Compliance
        try:
            env = os.getenv("SARDIS_ENVIRONMENT", "dev")
            if env in ("prod", "production"):
                components["compliance"] = {"status": "check_required"}
            else:
                components["compliance"] = {"status": "disabled_dev_mode"}
        except (OSError, RuntimeError, ValueError) as e:
            components["compliance"] = {"status": "error", "error": str(e)}

        # Smart contracts
        checks_total += 1
        try:
            from sardis_v2_core.config import get_chain_config

            chain_cfg = get_chain_config(
                settings.chain_mode if settings.chain_mode != "simulated" else "base_sepolia"
            )
            contract_addr = getattr(chain_cfg, "wallet_factory_address", None) or os.getenv(
                "SARDIS_WALLET_FACTORY_ADDRESS"
            )
            if contract_addr and contract_addr.startswith("0x") and len(contract_addr) == 42:
                components["contracts"] = {
                    "status": "configured",
                    "wallet_factory": contract_addr[:10] + "...",
                }
                checks_passed += 1
            elif contract_addr:
                components["contracts"] = {"status": "invalid_address", "address": contract_addr}
                overall_healthy = False
            else:
                components["contracts"] = {"status": "unconfigured"}
                checks_passed += 1
        except (ImportError, AttributeError, OSError, RuntimeError, ValueError) as e:
            components["contracts"] = {"status": "error", "error": str(e)}

        # Webhooks
        checks_total += 1
        components["webhooks"]["status"] = "up"
        checks_passed += 1

        response_time_ms = int((time.time() - start_time) * 1000)

        if shutdown_state.is_shutting_down:
            status = "shutting_down"
        elif not overall_healthy:
            status = "degraded"
        elif checks_passed < checks_total:
            status = "partial"
        else:
            status = "healthy"

        status_code = 200 if status in ("healthy", "partial") else 503

        return JSONResponse(
            status_code=status_code,
            content={
                "status": status,
                "environment": settings.environment,
                "chain_mode": settings.chain_mode,
                "version": API_VERSION,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "response_time_ms": response_time_ms,
                "checks": {"passed": checks_passed, "total": checks_total},
                "components": components,
            },
        )

    @health_router.get("/api")
    async def api_root():
        """API namespace discovery endpoint."""
        return {
            "service": "Sardis API",
            "version": API_VERSION,
            "status": "ok",
            "latest": "/api/v2",
            "docs": "/api/v2/docs",
            "openapi": "/api/v2/openapi.json",
            "health": "/api/v2/health",
        }

    @health_router.get("/api/v2")
    async def api_v2_root():
        """Versioned API discovery endpoint."""
        return {
            "service": "Sardis API",
            "version": API_VERSION,
            "status": "ok",
            "docs": "/api/v2/docs",
            "openapi": "/api/v2/openapi.json",
            "health": "/api/v2/health",
        }

    @health_router.get("/api/v2/health")
    def api_health():
        """Lightweight API v2 health check."""
        return {
            "status": "ok",
            "version": API_VERSION,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    return health_router
