"""Health-check endpoints: liveness, readiness, and deep component checks.

Endpoint layout
---------------
/              — Root service info
/health        — Deep readiness probe (checks all dependencies)
/health/live   — Shallow liveness probe (process is running)
/ready         — Readiness probe (delegates to app.state.ready + shutdown_state)
/live          — Alias for /health/live (backwards compat)
/api           — API namespace discovery
/api/v2        — Versioned API discovery
/api/v2/health — Lightweight API v2 health
"""
from __future__ import annotations

import logging
import os
import time

from fastapi import APIRouter, Request
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

    # ------------------------------------------------------------------
    # Liveness probes — shallow, confirms the process is running
    # ------------------------------------------------------------------

    @health_router.get("/health/live")
    def health_liveness():
        """Kubernetes liveness probe (shallow).

        Returns 200 as long as the process is alive. Does NOT check
        external dependencies — that is the job of /health (readiness).
        """
        return {"status": "alive"}

    @health_router.get("/live")
    def liveness():
        """Kubernetes liveness probe (legacy alias for /health/live)."""
        return {"status": "alive"}

    # ------------------------------------------------------------------
    # Readiness probe — checks startup flag + shutdown state
    # ------------------------------------------------------------------

    @health_router.get("/ready")
    def readiness(request: Request):
        """Kubernetes readiness probe.

        Returns 503 when the application has not finished starting up
        (app.state.ready is not set) or is shutting down.
        """
        if shutdown_state.is_shutting_down:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "shutting_down",
                    "message": "Service is shutting down",
                },
            )

        app_ready = getattr(request.app.state, "ready", False)
        if not app_ready:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "message": "Application startup has not completed",
                },
            )

        return {"status": "ready"}

    # ------------------------------------------------------------------
    # Deep health check — readiness probe with component details
    # ------------------------------------------------------------------

    @health_router.get("/health")
    async def health_check(request: Request):
        """Deep health check endpoint with component status (readiness probe).

        Checks all critical dependencies: database, Redis, TAP JWKS,
        cache, RPC, contracts, Stripe, Turnkey, etc.

        Returns 503 if the application has not finished startup or if
        any critical component is unhealthy.
        """
        # Gate on startup readiness flag
        app_ready = getattr(request.app.state, "ready", False)
        if not app_ready:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "message": "Application startup has not completed",
                    "components": {},
                    "critical_failures": [],
                    "non_critical_failures": [],
                },
            )

        start_time = time.time()
        startup_time = getattr(request.app.state, "startup_time", None)
        uptime_seconds = int(time.time() - startup_time) if startup_time else 0
        execution_mode = resolve_execution_mode(settings)
        target_chain = _resolve_health_chain(settings)

        components: dict[str, dict] = {
            "api": {"status": "healthy", "uptime_seconds": uptime_seconds},
            "database": {"status": "unknown", "type": "postgresql" if use_postgres else "memory"},
            "chain_executor": {
                "status": "healthy",
                "mode": settings.chain_mode,
                "execution_mode": execution_mode,
            },
            "custody": _resolve_custody_posture(settings),
            "cache": {"status": "unknown", "type": "unknown"},
            "tap_jwks": {"status": "unknown"},
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

        def is_prod_env() -> bool:
            env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
            return env in ("prod", "production", "sandbox")

        def redact_url(url: str) -> str:
            if "://" not in url:
                return url
            scheme, rest = url.split("://", 1)
            host = rest.split("/", 1)[0]
            return f"{scheme}://{host}"

        # Database
        checks_total += 1
        db_start = time.time()
        try:
            if use_postgres:
                import asyncpg
                conn = await asyncpg.connect(database_url, timeout=5)
                await conn.execute("SELECT 1")
                await conn.close()
                db_latency = int((time.time() - db_start) * 1000)
                components["database"]["status"] = "healthy"
                components["database"]["latency_ms"] = db_latency
                checks_passed += 1
            else:
                components["database"]["status"] = "healthy"
                components["database"]["latency_ms"] = 0
                checks_passed += 1
        except (ImportError, OSError, RuntimeError, ValueError) as e:
            logger.warning(f"Database health check failed: {e}")
            components["database"]["status"] = "unhealthy"
            components["database"]["latency_ms"] = int((time.time() - db_start) * 1000)
            components["database"]["error"] = str(e)
            record_failure(
                "database",
                "SARDIS.HEALTH.DATABASE_UNAVAILABLE",
                str(e),
                critical=True,
            )

        # Cache / Redis
        checks_total += 1
        redis_start = time.time()
        try:
            if redis_url:
                import redis.asyncio as aioredis
                r = aioredis.from_url(redis_url, decode_responses=True)
                pong = await r.ping()
                await r.aclose()
                redis_latency = int((time.time() - redis_start) * 1000)
                if pong:
                    components["cache"]["status"] = "healthy"
                    components["cache"]["type"] = "redis"
                    components["cache"]["latency_ms"] = redis_latency
                    checks_passed += 1
                else:
                    components["cache"]["status"] = "degraded"
                    components["cache"]["type"] = "redis"
                    components["cache"]["latency_ms"] = redis_latency
                    record_failure("cache", "SARDIS.HEALTH.REDIS_PING_FAILED", "PING returned falsy", critical=is_prod_env())
            else:
                components["cache"]["status"] = "healthy"
                components["cache"]["type"] = "in_memory"
                components["cache"]["latency_ms"] = 0
                checks_passed += 1
        except (ImportError, OSError, RuntimeError, ValueError) as e:
            logger.warning(f"Redis health check failed: {e}")
            components["cache"]["status"] = "unhealthy"
            components["cache"]["type"] = "redis"
            components["cache"]["latency_ms"] = int((time.time() - redis_start) * 1000)
            components["cache"]["error"] = str(e)
            record_failure(
                "cache",
                "SARDIS.HEALTH.CACHE_UNAVAILABLE",
                str(e),
                critical=is_prod_env(),
            )

        # TAP JWKS availability — mirrors the production guard in lifespan.py
        checks_total += 1
        tap_jwks_url = os.getenv("SARDIS_TAP_JWKS_URL")
        if tap_jwks_url:
            tap_start = time.time()
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(tap_jwks_url)
                    tap_latency = int((time.time() - tap_start) * 1000)
                    if resp.status_code == 200:
                        components["tap_jwks"]["status"] = "healthy"
                        components["tap_jwks"]["latency_ms"] = tap_latency
                        checks_passed += 1
                    else:
                        components["tap_jwks"]["status"] = "degraded"
                        components["tap_jwks"]["latency_ms"] = tap_latency
                        components["tap_jwks"]["http_status"] = resp.status_code
                        record_failure(
                            "tap_jwks",
                            "SARDIS.HEALTH.TAP_JWKS_FETCH_ERROR",
                            f"JWKS endpoint returned http_status={resp.status_code}",
                            critical=is_prod_env(),
                        )
            except (ImportError, OSError, TimeoutError, RuntimeError, ValueError) as e:
                tap_latency = int((time.time() - tap_start) * 1000)
                logger.warning(f"TAP JWKS health check failed: {e}")
                components["tap_jwks"]["status"] = "unhealthy"
                components["tap_jwks"]["latency_ms"] = tap_latency
                components["tap_jwks"]["error"] = str(e)
                record_failure(
                    "tap_jwks",
                    "SARDIS.HEALTH.TAP_JWKS_UNREACHABLE",
                    str(e),
                    critical=is_prod_env(),
                )
        else:
            # No JWKS URL configured
            if is_prod_env():
                components["tap_jwks"]["status"] = "unhealthy"
                record_failure(
                    "tap_jwks",
                    "SARDIS.HEALTH.TAP_JWKS_UNCONFIGURED",
                    "SARDIS_TAP_JWKS_URL not set — required in production",
                    critical=True,
                )
            else:
                components["tap_jwks"]["status"] = "healthy"
                components["tap_jwks"]["detail"] = "not_required_in_dev"
                checks_passed += 1

        # Kill switch
        try:
            from sardis_guardrails.kill_switch import get_kill_switch
            ks = get_kill_switch()
            global_active = await ks.is_active_global()
            components["kill_switch"] = {
                "status": "active" if global_active else "clear",
                "global_active": global_active,
            }
        except Exception as e:
            components["kill_switch"] = {"status": "error", "error": str(e)}

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
                    stripe_latency = int((time.time() - stripe_start) * 1000)
                    if resp.status_code == 200:
                        components["stripe"]["status"] = "healthy"
                        components["stripe"]["latency_ms"] = stripe_latency
                        checks_passed += 1
                    else:
                        components["stripe"]["status"] = "degraded"
                        components["stripe"]["http_status"] = resp.status_code
                        components["stripe"]["latency_ms"] = stripe_latency
                        record_failure(
                            "stripe",
                            "SARDIS.HEALTH.STRIPE_AUTH_ERROR",
                            f"http_status={resp.status_code}",
                            critical=False,
                        )
            except (ImportError, OSError, TimeoutError, RuntimeError, ValueError) as e:
                logger.warning(f"Stripe health check failed: {e}")
                components["stripe"]["status"] = "unhealthy"
                components["stripe"]["latency_ms"] = int((time.time() - stripe_start) * 1000)
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
                    turnkey_latency = int((time.time() - turnkey_start) * 1000)
                    components["turnkey"]["status"] = "healthy"
                    components["turnkey"]["latency_ms"] = turnkey_latency
                    checks_passed += 1
            except (ImportError, OSError, TimeoutError, RuntimeError, ValueError) as e:
                logger.warning(f"Turnkey health check failed: {e}")
                components["turnkey"]["status"] = "unhealthy"
                components["turnkey"]["latency_ms"] = int((time.time() - turnkey_start) * 1000)
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
                "status": "healthy" if rpc_url else "unconfigured",
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
            components["rpc"] = {"status": "unhealthy", "error": str(e)}
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
            from sardis_chain.executor import get_sardis_policy_module

            contract_addr = get_sardis_policy_module(target_chain)
            if contract_addr and contract_addr.startswith("0x") and len(contract_addr) == 42:
                components["contracts"] = {
                    "status": "healthy",
                    "policy_module": contract_addr[:10] + "...",
                    "chain": target_chain,
                }
                checks_passed += 1
            elif contract_addr:
                components["contracts"] = {"status": "degraded", "address": contract_addr}
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
                    f"policy_module not configured for chain={target_chain}",
                    critical=is_live_execution(),
                )
                if not is_live_execution():
                    checks_passed += 1
        except (ImportError, AttributeError, OSError, RuntimeError, ValueError) as e:
            components["contracts"] = {"status": "unhealthy", "error": str(e)}
            record_failure(
                "contracts",
                "SARDIS.HEALTH.CONTRACTS_ERROR",
                str(e),
                critical=is_live_execution(),
            )

        # Webhooks
        checks_total += 1
        components["webhooks"]["status"] = "healthy"
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
                "uptime_seconds": uptime_seconds,
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


def _resolve_custody_posture(settings) -> dict[str, object]:
    chain_mode = str(getattr(settings, "chain_mode", SIMULATED_MODE)).strip().lower()
    configured_mpc = str(os.getenv("SARDIS_MPC__NAME", getattr(settings.mpc, "name", "simulated"))).strip().lower()
    local_key_configured = bool((os.getenv("SARDIS_EOA_PRIVATE_KEY", "") or "").strip())

    if chain_mode != "live":
        return {
            "status": "simulated_or_sandbox",
            "non_custodial": False,
            "details": "chain_mode is not live",
            "configured_mpc": configured_mpc,
        }

    if configured_mpc in {"turnkey", "fireblocks"}:
        return {
            "status": "non_custodial_mpc",
            "non_custodial": True,
            "details": f"MPC provider {configured_mpc} configured for live execution",
            "configured_mpc": configured_mpc,
        }

    if configured_mpc == "local":
        return {
            "status": "custodial_local_signer",
            "non_custodial": False,
            "details": "local signer path stores signing key in environment/memory",
            "configured_mpc": configured_mpc,
            "local_key_configured": local_key_configured,
        }

    return {
        "status": "misconfigured",
        "non_custodial": False,
        "details": "live mode requires turnkey, fireblocks, or local signer configuration",
        "configured_mpc": configured_mpc,
    }
