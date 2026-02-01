"""API composition root.

Production-grade Sardis API with:
- Comprehensive security middleware (CSP, HSTS, etc.)
- Request body size limits
- API versioning headers
- RFC 7807 error responses
- Request ID tracking
- Structured logging
- Deep health checks
- Graceful shutdown handling
- OpenAPI security schemes
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from sardis_v2_core import SardisSettings, load_settings
from sardis_v2_core.identity import IdentityRegistry
from sardis_wallet.manager import WalletManager
from sardis_protocol.verifier import MandateVerifier
from sardis_protocol.storage import MandateArchive, SqliteReplayCache, ReplayCache, PostgresReplayCache
from sardis_chain.executor import ChainExecutor
from sardis_ledger.records import LedgerStore
from sardis_compliance.checks import ComplianceEngine
from sardis_v2_core.orchestrator import PaymentOrchestrator
from sardis_v2_core.holds import HoldsRepository
from sardis_v2_core.webhooks import WebhookRepository, WebhookService
from sardis_v2_core.cache import create_cache_service
from .routers import mandates, ap2, auth
from .routers import mvp
from .routers import ledger as ledger_router
from .routers import holds as holds_router
from .routers import webhooks as webhooks_router
from .routers import transactions as transactions_router
from .routers import marketplace as marketplace_router
from .routers import wallets as wallets_router
from .routers import agents as agents_router
from .routers import api_keys as api_keys_router
from .routers import cards as cards_router
from .routers import checkout as checkout_router
from .routers import policies as policies_router
from .routers import compliance as compliance_router
from .routers import admin as admin_router
from .routers import invoices as invoices_router
from sardis_v2_core.marketplace import MarketplaceRepository
from sardis_v2_core.agents import AgentRepository
from sardis_v2_core.wallet_repository import WalletRepository
from .middleware import (
    RateLimitMiddleware,
    RateLimitConfig,
    StructuredLoggingMiddleware,
    setup_logging,
    APIKeyManager,
    set_api_key_manager,
    register_exception_handlers,
    SecurityHeadersMiddleware,
    RequestBodyLimitMiddleware,
    RequestIdMiddleware,
    SecurityConfig,
    API_VERSION,
)

# Configure structured logging
setup_logging(
    json_format=os.getenv("SARDIS_ENVIRONMENT", "dev") != "dev",
    level=os.getenv("LOG_LEVEL", "INFO"),
)
logger = logging.getLogger("sardis.api")

# Graceful shutdown state
_shutdown_event: Optional[asyncio.Event] = None
_active_connections: int = 0


def get_shutdown_event() -> asyncio.Event:
    """Get or create the shutdown event."""
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()
    return _shutdown_event


class GracefulShutdownState:
    """Track state for graceful shutdown."""

    def __init__(self):
        self.is_shutting_down = False
        self.active_requests = 0
        self.shutdown_started_at: Optional[float] = None
        self.max_shutdown_wait_seconds = 30

    def start_shutdown(self):
        """Mark shutdown as started."""
        self.is_shutting_down = True
        self.shutdown_started_at = time.time()
        logger.info(
            "Graceful shutdown initiated",
            extra={
                "active_requests": self.active_requests,
                "max_wait_seconds": self.max_shutdown_wait_seconds,
            }
        )

    def request_started(self):
        """Track a new request starting."""
        self.active_requests += 1

    def request_finished(self):
        """Track a request finishing."""
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


# Global shutdown state
shutdown_state = GracefulShutdownState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info(
        "Starting Sardis API...",
        extra={
            "version": API_VERSION,
            "environment": os.getenv("SARDIS_ENVIRONMENT", "dev"),
            "python_version": sys.version.split()[0],
        }
    )

    # Initialize database if using PostgreSQL
    database_url = os.getenv("DATABASE_URL", "")
    if database_url and (database_url.startswith("postgresql://") or database_url.startswith("postgres://")):
        try:
            from sardis_v2_core.database import init_database
            await init_database()
            logger.info("Database schema initialized")
        except Exception as e:
            logger.warning(f"Could not initialize database schema: {e}")

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def signal_handler(sig):
        logger.info(f"Received signal {sig.name}")
        shutdown_state.start_shutdown()
        get_shutdown_event().set()

    # Only set signal handlers on Unix systems
    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    # Mark startup complete
    app.state.startup_time = time.time()
    app.state.ready = True

    logger.info("Sardis API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Sardis API...")
    shutdown_state.start_shutdown()

    # Wait for active requests to complete
    await shutdown_state.wait_for_requests()

    # Cleanup resources
    if hasattr(app.state, "turnkey_client") and app.state.turnkey_client:
        try:
            await app.state.turnkey_client.close()
        except Exception as e:
            logger.warning(f"Error closing Turnkey client: {e}")

    if hasattr(app.state, "cache_service"):
        try:
            await app.state.cache_service.close()
        except Exception as e:
            logger.warning(f"Error closing cache service: {e}")

    logger.info("Sardis API shutdown complete")


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """Generate custom OpenAPI schema with security schemes."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Sardis Stablecoin Execution API",
        version=API_VERSION,
        description="""
## Overview

The Sardis API provides a comprehensive platform for stablecoin payment execution
with built-in compliance, security, and auditability.

## Authentication

All API endpoints require authentication via API key:

```
X-API-Key: sk_live_your_api_key_here
```

## Rate Limits

- Standard endpoints: 100 requests/minute, 1000 requests/hour
- Admin endpoints: 10 requests/minute
- Burst: Up to 20 requests in quick succession

## Error Responses

All errors follow RFC 7807 Problem Details format:

```json
{
  "type": "https://api.sardis.io/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "One or more fields failed validation",
  "instance": "/api/v2/mandates",
  "request_id": "req_abc123",
  "errors": [...]
}
```

## Versioning

Current API version: v2. The API version is included in all response headers:
`X-API-Version: {version}`
        """,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication. Format: sk_live_xxxxx",
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for dashboard authentication",
        },
        "WebhookSignature": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Sardis-Signature",
            "description": "HMAC-SHA256 webhook signature. Format: t=<timestamp>,v1=<signature>",
        },
    }

    # Apply security globally
    openapi_schema["security"] = [
        {"ApiKeyAuth": []},
    ]

    # Add server URLs
    openapi_schema["servers"] = [
        {
            "url": "https://api.sardis.io",
            "description": "Production server",
        },
        {
            "url": "https://api.staging.sardis.io",
            "description": "Staging server",
        },
        {
            "url": "http://localhost:8000",
            "description": "Local development",
        },
    ]

    # Add contact and license info
    openapi_schema["info"]["contact"] = {
        "name": "Sardis API Support",
        "email": "support@sardis.io",
        "url": "https://docs.sardis.io",
    }
    openapi_schema["info"]["license"] = {
        "name": "Proprietary",
        "url": "https://sardis.io/terms",
    }

    # Add tags with descriptions
    openapi_schema["tags"] = [
        {"name": "health", "description": "Health check endpoints"},
        {"name": "mandates", "description": "Payment mandate management"},
        {"name": "ap2", "description": "Agent-to-Agent Protocol v2"},
        {"name": "mvp", "description": "Minimum Viable Protocol operations"},
        {"name": "ledger", "description": "Ledger and transaction history"},
        {"name": "holds", "description": "Pre-authorization holds"},
        {"name": "webhooks", "description": "Webhook subscription management"},
        {"name": "transactions", "description": "Transaction status and gas estimation"},
        {"name": "marketplace", "description": "A2A service discovery"},
        {"name": "wallets", "description": "Wallet management"},
        {"name": "agents", "description": "AI agent configuration"},
        {"name": "api-keys", "description": "API key management"},
        {"name": "cards", "description": "Virtual card management"},
        {"name": "checkout", "description": "Agentic checkout flow"},
        {"name": "policies", "description": "Natural language policy parsing"},
        {"name": "compliance", "description": "KYC and sanctions screening"},
        {"name": "admin", "description": "Administrative operations"},
        {"name": "auth", "description": "Authentication endpoints"},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app(settings: SardisSettings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = settings or load_settings()

    # Initialize Sentry for error monitoring (if configured)
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.asyncpg import AsyncPGIntegration

            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=settings.environment,
                traces_sample_rate=0.1 if settings.environment == "production" else 1.0,
                profiles_sample_rate=0.1 if settings.environment == "production" else 1.0,
                integrations=[
                    FastApiIntegration(transaction_style="endpoint"),
                    AsyncPGIntegration(),
                ],
                send_default_pii=False,
            )
            logger.info("Sentry monitoring initialized")
        except ImportError:
            logger.warning("SENTRY_DSN is set but sentry-sdk is not installed")

    app = FastAPI(
        title="Sardis Stablecoin Execution API",
        version=API_VERSION,
        openapi_url="/api/v2/openapi.json",
        docs_url="/api/v2/docs",
        redoc_url="/api/v2/redoc",
        lifespan=lifespan,
    )

    # Override OpenAPI generation with custom schema
    app.openapi = lambda: custom_openapi(app)

    # Register RFC 7807 exception handlers
    register_exception_handlers(app)

    # Exclude paths for middleware
    health_paths = ["/", "/health", "/api/v2/health", "/ready", "/live"]
    docs_paths = ["/api/v2/docs", "/api/v2/openapi.json", "/api/v2/redoc"]
    exclude_paths = health_paths + docs_paths

    # Add middleware in order (outermost first)

    # 1. Request ID middleware (outermost - ensures all requests have IDs)
    app.add_middleware(RequestIdMiddleware)

    # 2. Structured logging middleware
    app.add_middleware(
        StructuredLoggingMiddleware,
        exclude_paths=exclude_paths,
    )

    # 3. Security headers middleware
    security_config = SecurityConfig.from_environment()
    app.add_middleware(
        SecurityHeadersMiddleware,
        config=security_config,
    )

    # 4. Request body size limit middleware
    app.add_middleware(
        RequestBodyLimitMiddleware,
        default_limit=10 * 1024 * 1024,  # 10MB default
        path_limits={
            "/api/v2/webhooks": 1 * 1024 * 1024,  # 1MB for webhook callbacks
            "/api/v2/checkout": 512 * 1024,  # 512KB for checkout
            "/api/v2/policies": 64 * 1024,  # 64KB for policy text
        },
        exclude_paths=health_paths,
    )

    # 5. Rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        config=RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=1000,
            burst_size=20,
        ),
        exclude_paths=exclude_paths,
    )

    # 6. CORS middleware with settings-based origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-API-Key",
            "X-Sardis-Signature",
            "X-Sardis-Timestamp",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-API-Version",
            "X-Response-Time",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ],
    )

    # Determine storage backend based on DSN
    database_url = os.getenv("DATABASE_URL", settings.ledger_dsn)
    use_postgres = database_url.startswith("postgresql://") or database_url.startswith("postgres://")

    # Store configuration in app state
    app.state.settings = settings
    app.state.database_url = database_url
    app.state.use_postgres = use_postgres
    app.state.turnkey_client = turnkey_client

    # Initialize Turnkey MPC client if configured
    turnkey_client = None
    if os.getenv("TURNKEY_API_KEY") and os.getenv("TURNKEY_ORGANIZATION_ID"):
        try:
            from sardis_wallet.turnkey_client import TurnkeyClient
            turnkey_client = TurnkeyClient(
                api_key=os.getenv("TURNKEY_API_KEY", ""),
                api_private_key=os.getenv("TURNKEY_API_PRIVATE_KEY", ""),
                organization_id=os.getenv("TURNKEY_ORGANIZATION_ID", ""),
            )
            logger.info("Turnkey MPC client initialized")
        except ImportError:
            logger.warning("Turnkey client module not available")

    wallet_mgr = WalletManager(settings=settings, turnkey_client=turnkey_client)
    chain_exec = ChainExecutor(settings=settings)
    ledger_store = LedgerStore(dsn=database_url if use_postgres else settings.ledger_dsn)
    compliance = ComplianceEngine(settings=settings)
    identity_registry = IdentityRegistry()

    # Use PostgreSQL for mandate archive and replay cache if available
    if use_postgres:
        archive = MandateArchive(database_url)
        replay_cache = PostgresReplayCache(database_url)
    else:
        archive = MandateArchive(settings.mandate_archive_dsn)
        replay_cache = (
            SqliteReplayCache(settings.replay_cache_dsn)
            if settings.replay_cache_dsn.startswith("sqlite:///")
            else ReplayCache()
        )

    verifier = MandateVerifier(
        settings=settings,
        replay_cache=replay_cache,
        archive=archive,
        identity_registry=identity_registry,
    )
    orchestrator = PaymentOrchestrator(
        wallet_manager=wallet_mgr,
        compliance=compliance,
        chain_executor=chain_exec,
        ledger=ledger_store,
    )

    logger.info(f"API initialized with storage backend: {'PostgreSQL' if use_postgres else 'SQLite/Memory'}")

    app.dependency_overrides[mandates.get_deps] = lambda: mandates.Dependencies(  # type: ignore[arg-type]
        wallet_manager=wallet_mgr,
        chain_executor=chain_exec,
        verifier=verifier,
        ledger=ledger_store,
        compliance=compliance,
    )
    app.include_router(mandates.router, prefix="/api/v2/mandates")

    app.dependency_overrides[ap2.get_deps] = lambda: ap2.Dependencies(  # type: ignore[arg-type]
        verifier=verifier,
        orchestrator=orchestrator,
    )
    app.include_router(ap2.router, prefix="/api/v2/ap2")

    # MVP router (TAP issuance, mandate validation, execution, receipts)
    app.dependency_overrides[mvp.get_deps] = lambda: mvp.Dependencies(  # type: ignore[arg-type]
        verifier=verifier,
        chain_executor=chain_exec,
        ledger=ledger_store,
        identity_registry=identity_registry,
        settings=settings,
    )
    app.include_router(mvp.router, prefix="/api/v2/mvp", tags=["mvp"])

    # Ledger routes
    app.dependency_overrides[ledger_router.get_deps] = lambda: ledger_router.LedgerDependencies(  # type: ignore[arg-type]
        ledger=ledger_store,
    )
    app.include_router(ledger_router.router, prefix="/api/v2/ledger")

    # Holds routes (pre-authorization)
    holds_repo = HoldsRepository(dsn=database_url if use_postgres else "memory://")
    app.dependency_overrides[holds_router.get_deps] = lambda: holds_router.HoldsDependencies(  # type: ignore[arg-type]
        holds_repo=holds_repo,
    )
    app.include_router(holds_router.router, prefix="/api/v2/holds")

    # Webhook routes
    webhook_repo = WebhookRepository(dsn=database_url if use_postgres else "memory://")
    webhook_service = WebhookService(repository=webhook_repo)
    app.dependency_overrides[webhooks_router.get_deps] = lambda: webhooks_router.WebhookDependencies(  # type: ignore[arg-type]
        repository=webhook_repo,
        service=webhook_service,
    )
    app.include_router(webhooks_router.router, prefix="/api/v2/webhooks")

    # Store webhook service for event emission
    app.state.webhook_service = webhook_service

    # Initialize cache service
    redis_url = os.getenv("SARDIS_REDIS_URL", settings.redis_url) or None
    cache_service = create_cache_service(redis_url)
    app.state.cache_service = cache_service
    logger.info(f"Cache initialized: {'Redis' if redis_url else 'In-memory'}")

    # Initialize API key manager
    api_key_manager = APIKeyManager(dsn=database_url if use_postgres else "memory://")
    set_api_key_manager(api_key_manager)
    app.state.api_key_manager = api_key_manager

    # Transaction routes (gas estimation, status)
    app.dependency_overrides[transactions_router.get_deps] = lambda: transactions_router.TransactionDependencies(  # type: ignore[arg-type]
        chain_executor=chain_exec,
    )
    app.include_router(transactions_router.router, prefix="/api/v2/transactions")

    # Marketplace routes (A2A service discovery)
    marketplace_repo = MarketplaceRepository(dsn=database_url if use_postgres else "memory://")
    app.dependency_overrides[marketplace_router.get_deps] = lambda: marketplace_router.MarketplaceDependencies(  # type: ignore[arg-type]
        repository=marketplace_repo,
    )
    app.include_router(marketplace_router.router, prefix="/api/v2/marketplace")

    # Auth routes (for dashboard login)
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(auth.router, prefix="/api/v2/auth")

    # Wallet routes
    wallet_repo = WalletRepository(dsn=database_url if use_postgres else "memory://")
    app.dependency_overrides[wallets_router.get_deps] = lambda: wallets_router.WalletDependencies(  # type: ignore[arg-type]
        wallet_repo=wallet_repo,
        chain_executor=chain_exec,
    )
    app.include_router(wallets_router.router, prefix="/api/v2/wallets", tags=["wallets"])

    # Virtual Card routes (pre-loaded cards for fiat on-ramp)
    app.include_router(cards_router.router, prefix="/api/v2/cards", tags=["cards"])

    # Agent routes
    agent_repo = AgentRepository(dsn=database_url if use_postgres else "memory://")
    app.dependency_overrides[agents_router.get_deps] = lambda: agents_router.AgentDependencies(  # type: ignore[arg-type]
        agent_repo=agent_repo,
        wallet_repo=wallet_repo,
    )
    app.include_router(agents_router.router, prefix="/api/v2/agents", tags=["agents"])

    # API Key management routes
    api_key_manager = APIKeyManager(dsn=database_url if use_postgres else "memory://")
    set_api_key_manager(api_key_manager)
    app.include_router(api_keys_router.router, prefix="/api/v2/api-keys", tags=["api-keys"])

    # Checkout routes (Agentic Checkout - Pivot D)
    from sardis_checkout.orchestrator import CheckoutOrchestrator
    from sardis_checkout.connectors.stripe import StripeConnector

    # Initialize PSP connectors
    stripe_connector = StripeConnector() if os.getenv("STRIPE_SECRET_KEY") else None
    checkout_orchestrator = CheckoutOrchestrator()
    if stripe_connector:
        checkout_orchestrator.register_connector("stripe", stripe_connector)

    wallet_repo_for_checkout = WalletRepository(dsn=database_url if use_postgres else "memory://")
    app.dependency_overrides[checkout_router.get_deps] = lambda: checkout_router.CheckoutDependencies(  # type: ignore[arg-type]
        wallet_repo=wallet_repo_for_checkout,
        orchestrator=checkout_orchestrator,
    )
    app.include_router(checkout_router.router, prefix="/api/v2/checkout", tags=["checkout"])

    # Policy routes (Natural Language policy parsing)
    app.include_router(policies_router.router, prefix="/api/v2/policies", tags=["policies"])

    # Compliance routes (KYC and Sanctions)
    from sardis_compliance import create_kyc_service, create_sanctions_service
    kyc_service = create_kyc_service(
        api_key=os.getenv("PERSONA_API_KEY"),
        template_id=os.getenv("PERSONA_TEMPLATE_ID"),
        webhook_secret=os.getenv("PERSONA_WEBHOOK_SECRET"),
        environment="sandbox" if settings.environment != "production" else "production",
    )
    sanctions_service = create_sanctions_service(
        api_key=os.getenv("ELLIPTIC_API_KEY"),
        api_secret=os.getenv("ELLIPTIC_API_SECRET"),
    )
    app.dependency_overrides[compliance_router.get_deps] = lambda: compliance_router.ComplianceDependencies(
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
    )
    app.include_router(compliance_router.router, prefix="/api/v2/compliance", tags=["compliance"])

    # Invoice routes
    app.include_router(invoices_router.router, prefix="/api/v2/invoices", tags=["invoices"])

    # Admin routes (with strict rate limiting)
    # SECURITY: Admin endpoints have much stricter rate limits (10/min vs 100/min)
    app.include_router(admin_router.router, prefix="/api/v2/admin", tags=["admin"])

    # Health check endpoints
    @app.get("/", tags=["health"])
    async def root():
        """Root endpoint with service information."""
        return {
            "service": "Sardis API",
            "version": API_VERSION,
            "status": "healthy",
            "docs": "/api/v2/docs",
            "health": "/health",
        }

    @app.get("/live", tags=["health"])
    async def liveness():
        """
        Kubernetes liveness probe.

        Returns 200 if the process is alive and can handle requests.
        This is a simple check that the process is running.
        """
        return {"status": "alive"}

    @app.get("/ready", tags=["health"])
    async def readiness():
        """
        Kubernetes readiness probe.

        Returns 200 if the service is ready to accept traffic.
        Returns 503 if the service is shutting down or not ready.
        """
        if shutdown_state.is_shutting_down:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "shutting_down",
                    "message": "Service is shutting down",
                }
            )

        if not getattr(app.state, "ready", False):
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "message": "Service is starting up",
                }
            )

        return {"status": "ready"}

    @app.get("/health", tags=["health"])
    async def health_check():
        """
        Deep health check endpoint with component status.

        Returns detailed status of all system components:
        - Database connection
        - Chain executor (simulated/live)
        - External providers (Stripe, Turnkey)
        - Cache service (Redis/in-memory)
        - Webhook service
        - API uptime

        This is a "deep" health check that verifies connectivity to dependencies.
        For lightweight probes, use /live or /ready endpoints.
        """
        start_time = time.time()

        # Calculate uptime
        startup_time = getattr(app.state, "startup_time", time.time())
        uptime_seconds = int(time.time() - startup_time)

        components = {
            "api": {
                "status": "up",
                "uptime_seconds": uptime_seconds,
            },
            "database": {
                "status": "unknown",
                "type": "postgresql" if use_postgres else "memory",
            },
            "chain_executor": {
                "status": "up",
                "mode": settings.chain_mode,
            },
            "cache": {
                "status": "unknown",
                "type": "unknown",
            },
            "stripe": {
                "status": "unconfigured",
            },
            "turnkey": {
                "status": "unconfigured",
            },
            "webhooks": {
                "status": "unknown",
            },
        }
        overall_healthy = True
        checks_passed = 0
        checks_total = 0

        # Database check
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
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            components["database"]["status"] = "disconnected"
            components["database"]["error"] = str(e)
            overall_healthy = False

        # Cache check
        checks_total += 1
        cache_start = time.time()
        try:
            cache = getattr(app.state, "cache_service", None)
            if cache:
                # Try a simple get to verify connectivity
                await cache.get("health_check_probe")
                components["cache"]["status"] = "connected"
                components["cache"]["type"] = "redis" if redis_url else "in_memory"
                components["cache"]["latency_ms"] = int((time.time() - cache_start) * 1000)
                checks_passed += 1
            else:
                components["cache"]["status"] = "disabled"
                components["cache"]["type"] = "none"
                checks_passed += 1
        except Exception as e:
            logger.warning(f"Cache health check failed: {e}")
            components["cache"]["status"] = "error"
            components["cache"]["error"] = str(e)

        # Stripe check (if configured)
        stripe_key = os.getenv("STRIPE_SECRET_KEY")
        if stripe_key:
            checks_total += 1
            stripe_start = time.time()
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        "https://api.stripe.com/v1/balance",
                        headers={"Authorization": f"Bearer {stripe_key}"}
                    )
                    if resp.status_code == 200:
                        components["stripe"]["status"] = "connected"
                        components["stripe"]["latency_ms"] = int((time.time() - stripe_start) * 1000)
                        checks_passed += 1
                    else:
                        components["stripe"]["status"] = "auth_error"
                        components["stripe"]["http_status"] = resp.status_code
                        overall_healthy = False
            except Exception as e:
                logger.warning(f"Stripe health check failed: {e}")
                components["stripe"]["status"] = "unreachable"
                components["stripe"]["error"] = str(e)
                overall_healthy = False

        # Turnkey check (if configured)
        if os.getenv("TURNKEY_API_KEY"):
            components["turnkey"]["status"] = "configured"
        else:
            components["turnkey"]["status"] = "unconfigured"

        # Webhook service check
        checks_total += 1
        try:
            webhook_svc = getattr(app.state, "webhook_service", None)
            if webhook_svc:
                components["webhooks"]["status"] = "up"
                checks_passed += 1
            else:
                components["webhooks"]["status"] = "disabled"
                checks_passed += 1
        except Exception as e:
            components["webhooks"]["status"] = "error"
            components["webhooks"]["error"] = str(e)

        response_time_ms = int((time.time() - start_time) * 1000)

        # Determine overall status
        if shutdown_state.is_shutting_down:
            status = "shutting_down"
        elif not overall_healthy:
            status = "degraded"
        elif checks_passed < checks_total:
            status = "partial"
        else:
            status = "healthy"

        from fastapi.responses import JSONResponse as FastAPIJSONResponse
        status_code = 200 if status in ("healthy", "partial") else 503

        return FastAPIJSONResponse(
            status_code=status_code,
            content={
                "status": status,
                "environment": settings.environment,
                "chain_mode": settings.chain_mode,
                "version": API_VERSION,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "response_time_ms": response_time_ms,
                "checks": {
                    "passed": checks_passed,
                    "total": checks_total,
                },
                "components": components,
            }
        )

    @app.get("/api/v2/health", tags=["health"])
    async def api_health():
        """Lightweight API v2 health check."""
        return {
            "status": "ok",
            "version": API_VERSION,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    return app


# Required import for JSONResponse in readiness check
from fastapi.responses import JSONResponse
