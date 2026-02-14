"""Health-check endpoints: liveness, readiness, and deep component checks."""
from __future__ import annotations

import logging
import os
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .execution_mode import SIMULATED_MODE, resolve_execution_mode
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
        uptime_seconds = 0
        execution_mode = resolve_execution_mode(settings)
        target_chain = _resolve_health_chain(settings)

        components = {
            "api": {"status": "up", "uptime_seconds": uptime_seconds},
            "database": {"status": "unknown", "type": "postgresql" if use_postgres else "memory"},
            "chain_executor": {
                "status": "up",
                "mode": settings.chain_mode,
                "execution_mode": execution_mode,
            },
            "cache": {"status": "unknown", "type": "unknown"},
            "stripe": {"status": "unconfigured"},
            "turnkey": {"status": "unconfigured"},
            "webhooks": {"status": "unknown"},
            "rpc": {"status": "unknown"},
            "contracts": {"status": "unknown"},
        }

        critical_failures: list[dict[str, str]] = []
        non_critical_failures: list[dict[str, str]] = []
        checks_passed = 0
        checks_total = 0

        def record_failure(component: str, reason_code: str, detail: str, *, critical: bool) -> None:
            entry = {"component": component, "reason_code": reason_code, "detail": detail}
            if critical:
                critical_failures.append(entry)
            else:
                non_critical_failures.append(entry)

        def is_live_execution() -> bool:
            return execution_mode in {"staging_live", "production_live"}

        def redact_url(url: str) -> str:
            if "://" not in url:
                return url
            scheme, rest = url.split("://", 1)
            host = rest.split("/", 1)[0]
            return f"{scheme}://{host}"

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
            record_failure(
                "database",
                "SARDIS.HEALTH.DATABASE_UNAVAILABLE",
                str(e),
                critical=True,
            )

        # Cache
        checks_total += 1
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
            record_failure(
                "cache",
                "SARDIS.HEALTH.CACHE_UNAVAILABLE",
                str(e),
                critical=False,
            )

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
                        record_failure(
                            "stripe",
                            "SARDIS.HEALTH.STRIPE_AUTH_ERROR",
                            f"http_status={resp.status_code}",
                            critical=False,
                        )
            except (ImportError, OSError, TimeoutError, RuntimeError, ValueError) as e:
                logger.warning(f"Stripe health check failed: {e}")
                components["stripe"]["status"] = "unreachable"
                components["stripe"]["error"] = str(e)
                record_failure(
                    "stripe",
                    "SARDIS.HEALTH.STRIPE_UNREACHABLE",
                    str(e),
                    critical=False,
                )

        # Turnkey
        turnkey_key = os.getenv("TURNKEY_API_PUBLIC_KEY") or os.getenv("TURNKEY_API_KEY")
        turnkey_mpc = (os.getenv("SARDIS_MPC__NAME", "simulated") or "simulated").strip().lower() == "turnkey"
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
                record_failure(
                    "turnkey",
                    "SARDIS.HEALTH.TURNKEY_UNREACHABLE",
                    str(e),
                    critical=is_live_execution() and turnkey_mpc,
                )
        else:
            components["turnkey"]["status"] = "unconfigured"
            if is_live_execution() and turnkey_mpc:
                record_failure(
                    "turnkey",
                    "SARDIS.HEALTH.TURNKEY_UNCONFIGURED",
                    "TURNKEY_API_PUBLIC_KEY/TURNKEY_API_KEY is not set",
                    critical=True,
                )

        # RPC
        checks_total += 1
        try:
            from sardis_chain.config import get_chain_config

            chain_cfg = get_chain_config(target_chain)
            rpc_url = chain_cfg.get_primary_rpc_url()
            components["rpc"] = {
                "status": "configured" if rpc_url else "unconfigured",
                "chain": target_chain,
                "endpoint": redact_url(rpc_url) if rpc_url else "",
            }
            checks_passed += 1
            if not rpc_url:
                record_failure(
                    "rpc",
                    "SARDIS.HEALTH.RPC_UNCONFIGURED",
                    f"No RPC endpoint configured for chain={target_chain}",
                    critical=is_live_execution(),
                )
        except (AttributeError, OSError, RuntimeError, ValueError) as e:
            logger.warning(f"RPC health check failed: {e}")
            components["rpc"] = {"status": "error", "error": str(e)}
            record_failure(
                "rpc",
                "SARDIS.HEALTH.RPC_ERROR",
                str(e),
                critical=is_live_execution(),
            )

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
            from sardis_chain.executor import get_sardis_wallet_factory

            contract_addr = get_sardis_wallet_factory(target_chain)
            if contract_addr and contract_addr.startswith("0x") and len(contract_addr) == 42:
                components["contracts"] = {
                    "status": "configured",
                    "wallet_factory": contract_addr[:10] + "...",
                    "chain": target_chain,
                }
                checks_passed += 1
            elif contract_addr:
                components["contracts"] = {"status": "invalid_address", "address": contract_addr}
                record_failure(
                    "contracts",
                    "SARDIS.HEALTH.CONTRACT_ADDRESS_INVALID",
                    f"chain={target_chain} address={contract_addr}",
                    critical=is_live_execution(),
                )
            else:
                components["contracts"] = {"status": "unconfigured", "chain": target_chain}
                record_failure(
                    "contracts",
                    "SARDIS.HEALTH.CONTRACTS_UNCONFIGURED",
                    f"wallet_factory not configured for chain={target_chain}",
                    critical=is_live_execution(),
                )
                if not is_live_execution():
                    checks_passed += 1
        except (ImportError, AttributeError, OSError, RuntimeError, ValueError) as e:
            components["contracts"] = {"status": "error", "error": str(e)}
            record_failure(
                "contracts",
                "SARDIS.HEALTH.CONTRACTS_ERROR",
                str(e),
                critical=is_live_execution(),
            )

        # Webhooks
        checks_total += 1
        components["webhooks"]["status"] = "up"
        checks_passed += 1

        response_time_ms = int((time.time() - start_time) * 1000)

        if shutdown_state.is_shutting_down:
            status = "shutting_down"
        elif critical_failures:
            status = "degraded"
        elif non_critical_failures or checks_passed < checks_total:
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
                "execution_mode": execution_mode,
                "version": API_VERSION,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "response_time_ms": response_time_ms,
                "checks": {"passed": checks_passed, "total": checks_total},
                "critical_failures": critical_failures,
                "non_critical_failures": non_critical_failures,
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


def _resolve_health_chain(settings) -> str:
    explicit = (os.getenv("SARDIS_HEALTH_CHAIN", "") or os.getenv("SARDIS_DEFAULT_CHAIN", "")).strip()
    if explicit:
        return explicit

    chains = getattr(settings, "chains", None)
    if isinstance(chains, list) and chains:
        first = chains[0]
        name = getattr(first, "name", None)
        if isinstance(name, str) and name.strip():
            return name.strip()

    if getattr(settings, "chain_mode", SIMULATED_MODE) == "live":
        return "base"
    return "base_sepolia"
