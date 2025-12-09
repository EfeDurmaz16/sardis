"""API composition root."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sardis_v2_core import SardisSettings, load_settings
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
from .routers import ledger as ledger_router
from .routers import holds as holds_router
from .routers import webhooks as webhooks_router
from .routers import transactions as transactions_router
from .routers import marketplace as marketplace_router
from .routers import wallets as wallets_router
from .routers import agents as agents_router
from .routers import api_keys as api_keys_router
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
)

# Configure structured logging
setup_logging(
    json_format=os.getenv("SARDIS_ENVIRONMENT", "dev") != "dev",
    level=os.getenv("LOG_LEVEL", "INFO"),
)
logger = logging.getLogger("sardis.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting Sardis API...")
    
    # Initialize database if using PostgreSQL
    database_url = os.getenv("DATABASE_URL", "")
    if database_url and (database_url.startswith("postgresql://") or database_url.startswith("postgres://")):
        try:
            from sardis_v2_core.database import init_database
            await init_database()
            logger.info("Database schema initialized")
        except Exception as e:
            logger.warning(f"Could not initialize database schema: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Sardis API...")


def create_app(settings: SardisSettings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(
        title="Sardis Stablecoin Execution API",
        version="0.1.0",
        openapi_url="/api/v2/openapi.json",
        docs_url="/api/v2/docs",
        lifespan=lifespan,
    )
    
    # Add structured logging middleware (outermost - runs first)
    app.add_middleware(
        StructuredLoggingMiddleware,
        exclude_paths=["/", "/health", "/api/v2/health", "/api/v2/docs", "/api/v2/openapi.json"],
    )
    
    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        config=RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=1000,
            burst_size=20,
        ),
        exclude_paths=["/", "/health", "/api/v2/health", "/api/v2/docs", "/api/v2/openapi.json"],
    )
    
    # Add CORS middleware with settings-based origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-API-Key"],
    )

    # Determine storage backend based on DSN
    database_url = os.getenv("DATABASE_URL", settings.ledger_dsn)
    use_postgres = database_url.startswith("postgresql://") or database_url.startswith("postgres://")
    
    wallet_mgr = WalletManager(settings=settings)
    chain_exec = ChainExecutor(settings=settings)
    ledger_store = LedgerStore(dsn=database_url if use_postgres else settings.ledger_dsn)
    compliance = ComplianceEngine(settings=settings)
    
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
    
    verifier = MandateVerifier(settings=settings, replay_cache=replay_cache, archive=archive)
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
    )
    app.include_router(wallets_router.router, prefix="/api/v2/wallets", tags=["wallets"])

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

    # Health check endpoints
    @app.get("/", tags=["health"])
    async def root():
        """Root endpoint."""
        return {
            "service": "Sardis API",
            "version": "0.1.0",
            "status": "healthy",
            "docs": "/api/v2/docs",
        }

    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint with component status."""
        # TODO: Add actual DB ping when PostgreSQL is wired
        db_status = "connected"
        try:
            # Basic check - in future, ping the database
            pass
        except Exception:
            db_status = "disconnected"
        
        return {
            "status": "healthy",
            "environment": settings.environment,
            "chain_mode": settings.chain_mode,
            "components": {
                "api": "up",
                "database": db_status,
                "chain_executor": "simulated" if settings.chain_mode == "simulated" else "live",
            }
        }

    @app.get("/api/v2/health", tags=["health"])
    async def api_health():
        """API v2 health check."""
        return {
            "status": "ok",
            "version": "v2",
        }

    return app
