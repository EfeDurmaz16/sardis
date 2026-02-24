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

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sardis_v2_core import SardisSettings, load_settings, InMemoryPolicyStore, PostgresPolicyStore


def _bootstrap_monorepo_sys_path() -> None:
    """
    Make monorepo packages importable without requiring PYTHONPATH.

    This helps local dev commands like:
      `uv run uvicorn sardis_api.main:create_app --factory`

    In a packaged/installed deployment this is a no-op.
    """
    here = Path(__file__).resolve()
    repo_root: Path | None = None
    for parent in here.parents:
        if (parent / "packages").is_dir():
            repo_root = parent
            break
    if repo_root is None:
        return

    packages_dir = repo_root / "packages"
    for pkg in (
        "sardis-core",
        "sardis-wallet",
        "sardis-chain",
        "sardis-protocol",
        "sardis-ledger",
        "sardis-cards",
        "sardis-compliance",
        "sardis-checkout",
    ):
        src = packages_dir / pkg / "src"
        if src.is_dir():
            p = str(src)
            if p not in sys.path:
                sys.path.insert(0, p)

def _should_bootstrap_monorepo_sys_path() -> bool:
    """Keep monorepo import bootstrapping for local dev only."""
    if os.getenv("SARDIS_DISABLE_MONOREPO_BOOTSTRAP", "").strip().lower() in {"1", "true", "yes", "on"}:
        return False
    env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
    return env in {"dev", "development", "sandbox", "staging", "test"}


if _should_bootstrap_monorepo_sys_path():
    _bootstrap_monorepo_sys_path()

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
from .routers import stripe_webhooks as stripe_webhooks_router
from .routers import checkout as checkout_router
from .routers import policies as policies_router
from .routers import compliance as compliance_router
from .routers import admin as admin_router
from .routers import invoices as invoices_router
from .routers import ramp as ramp_router
from .routers import treasury as treasury_router
from .routers import treasury_ops as treasury_ops_router
from .routers import dev as dev_router
from .routers import a2a as a2a_router
from .routers import groups as groups_router
from .routers import alerts as alerts_router
from .routers import ws_alerts as ws_alerts_router
from .routers import analytics as analytics_router
from .routers import sandbox as sandbox_router

# Conditional import for approvals router (may not exist yet)
try:
    from .routers import approvals as approvals_router
except ImportError:
    approvals_router = None  # type: ignore
from sardis_v2_core.marketplace import MarketplaceRepository
from sardis_v2_core.agents import AgentRepository
from sardis_v2_core.agent_groups import AgentGroupRepository
from sardis_v2_core.wallet_repository import WalletRepository
from sardis_v2_core.agent_repository_postgres import PostgresAgentRepository
from sardis_v2_core.wallet_repository_postgres import PostgresWalletRepository
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
    TapVerificationMiddleware,
    TapMiddlewareConfig,
    API_VERSION,
)

# Extracted modules
from .lifespan import lifespan, shutdown_state, get_shutdown_event
from .openapi_schema import custom_openapi
from .health import create_health_router
from .card_adapter import CardProviderCompatAdapter
from .repositories.canonical_ledger_repository import CanonicalLedgerRepository
from .repositories.treasury_repository import TreasuryRepository
from .providers.lithic_treasury import LithicTreasuryClient

# Configure structured logging
setup_logging(
    json_format=os.getenv("SARDIS_ENVIRONMENT", "dev") != "dev",
    level=os.getenv("LOG_LEVEL", "INFO"),
)
logger = logging.getLogger("sardis.api")


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

    # -----------------------------------------------------------------------
    # Middleware stack (outermost first)
    # -----------------------------------------------------------------------

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

    # 6. TAP verification middleware (before CORS, after rate limiting)
    tap_enforcement = os.getenv("SARDIS_TAP_ENFORCEMENT", "disabled").lower()
    if tap_enforcement == "enabled":
        jwks_url = os.getenv("SARDIS_TAP_JWKS_URL")
        jwks_provider = None
        if jwks_url:
            import httpx
            _jwks_cache: dict[str, dict] = {}

            def _jwks_provider(kid: str) -> dict | None:
                if kid in _jwks_cache:
                    return _jwks_cache[kid]
                try:
                    with httpx.Client(timeout=5.0) as client:
                        resp = client.get(jwks_url)
                        if resp.status_code == 200:
                            jwks = resp.json()
                            _jwks_cache[kid] = jwks
                            return jwks
                except (httpx.HTTPError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to fetch JWKS from {jwks_url}: {e}")
                return None

            jwks_provider = _jwks_provider

        tap_config = TapMiddlewareConfig.from_environment()
        tap_config.jwks_provider = jwks_provider
        app.add_middleware(
            TapVerificationMiddleware,
            config=tap_config,
            jwks_provider=jwks_provider,
        )
        logger.info("TAP verification middleware enabled")
    else:
        logger.info("TAP verification middleware disabled (set SARDIS_TAP_ENFORCEMENT=enabled to enable)")

    # 7. CORS middleware with settings-based origins
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
            "Signature-Input",
            "Signature",
            "TAP-Version",
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

    # -----------------------------------------------------------------------
    # Storage backend
    # -----------------------------------------------------------------------
    database_url = (
        os.getenv("DATABASE_URL")
        or settings.database_url
        or settings.ledger_dsn
        or ""
    )
    use_postgres = database_url.startswith("postgresql://") or database_url.startswith("postgres://")
    if settings.is_production:
        if not database_url:
            raise RuntimeError("CRITICAL: DATABASE_URL is required in production.")
        if not use_postgres:
            raise RuntimeError(
                "CRITICAL: Production requires PostgreSQL. "
                "Set DATABASE_URL to a postgres/postgresql URL."
            )

    app.state.settings = settings
    app.state.database_url = database_url
    app.state.use_postgres = use_postgres

    # -----------------------------------------------------------------------
    # MPC / Turnkey
    # -----------------------------------------------------------------------
    turnkey_client = None
    turnkey_api_key = os.getenv("TURNKEY_API_PUBLIC_KEY") or os.getenv("TURNKEY_API_KEY") or settings.turnkey.api_public_key
    turnkey_private_key = os.getenv("TURNKEY_API_PRIVATE_KEY") or settings.turnkey.api_private_key
    turnkey_org_id = os.getenv("TURNKEY_ORGANIZATION_ID") or settings.turnkey.organization_id
    if turnkey_api_key and turnkey_private_key and turnkey_org_id:
        try:
            from sardis_wallet.turnkey_client import TurnkeyClient
            turnkey_client = TurnkeyClient(
                api_key=turnkey_api_key,
                api_private_key=turnkey_private_key,
                organization_id=turnkey_org_id,
            )
            logger.info("Turnkey MPC client initialized")
        except ImportError:
            logger.warning("Turnkey client module not available")

    app.state.turnkey_client = turnkey_client

    if getattr(settings, "chain_mode", "simulated") == "live":
        mpc_name = (os.getenv("SARDIS_MPC__NAME", settings.mpc.name) or settings.mpc.name).strip().lower()
        if mpc_name == "simulated":
            logger.error(
                "SARDIS_CHAIN_MODE=live with MPC=simulated is not allowed. "
                "Use turnkey, fireblocks, or local (dev/sandbox only)."
            )
            raise RuntimeError("Simulated signer is not allowed for live chain mode")
        if mpc_name == "turnkey" and turnkey_client is None:
            logger.error(
                "SARDIS_CHAIN_MODE=live with MPC=turnkey but Turnkey client is not initialized. "
                "Set TURNKEY_API_PUBLIC_KEY, TURNKEY_API_PRIVATE_KEY, and TURNKEY_ORGANIZATION_ID."
            )
            raise RuntimeError("Turnkey MPC provider required for live chain mode but not configured")
        if mpc_name == "fireblocks" and not os.getenv("FIREBLOCKS_API_KEY"):
            logger.error(
                "SARDIS_CHAIN_MODE=live with MPC=fireblocks but FIREBLOCKS_API_KEY is not set."
            )
            raise RuntimeError("Fireblocks MPC provider required for live chain mode but not configured")
        if mpc_name == "local":
            if settings.is_production:
                raise RuntimeError("Local signer is custodial and not allowed in production live mode")
            if not os.getenv("SARDIS_EOA_PRIVATE_KEY"):
                raise RuntimeError(
                    "SARDIS_MPC__NAME=local requires SARDIS_EOA_PRIVATE_KEY in live mode"
                )
            logger.warning(
                "SARDIS_MPC__NAME=local enabled in live mode. This is a custodial signer path for dev/sandbox only."
            )

    # -----------------------------------------------------------------------
    # Core services
    # -----------------------------------------------------------------------
    policy_store = PostgresPolicyStore(database_url) if use_postgres else InMemoryPolicyStore()
    app.state.policy_store = policy_store

    wallet_repo = PostgresWalletRepository(database_url) if use_postgres else WalletRepository(dsn="memory://")
    agent_repo = PostgresAgentRepository(database_url) if use_postgres else AgentRepository(dsn="memory://")
    wallet_mgr = WalletManager(
        settings=settings,
        turnkey_client=turnkey_client,
        async_policy_store=policy_store,
    )
    chain_exec = ChainExecutor(settings=settings, turnkey_client=turnkey_client)
    ledger_store = LedgerStore(dsn=database_url if use_postgres else settings.ledger_dsn)
    from sardis_compliance.checks import create_audit_store
    audit_store = create_audit_store(dsn=database_url)
    from sardis_compliance import create_kyc_service, create_sanctions_service
    kyc_service = create_kyc_service(
        api_key=os.getenv("PERSONA_API_KEY"),
        template_id=os.getenv("PERSONA_TEMPLATE_ID"),
        webhook_secret=os.getenv("PERSONA_WEBHOOK_SECRET"),
        environment="production" if settings.is_production else "sandbox",
    )
    sanctions_service = create_sanctions_service(
        api_key=os.getenv("ELLIPTIC_API_KEY"),
        api_secret=os.getenv("ELLIPTIC_API_SECRET"),
    )
    compliance = ComplianceEngine(
        settings=settings,
        audit_store=audit_store,
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
    )
    identity_registry = IdentityRegistry()

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
    app.state.chain_executor = chain_exec
    app.state.compliance_engine = compliance

    logger.info(f"API initialized with storage backend: {'PostgreSQL' if use_postgres else 'SQLite/Memory'}")

    # -----------------------------------------------------------------------
    # Router registration
    # -----------------------------------------------------------------------
    app.dependency_overrides[mandates.get_deps] = lambda: mandates.Dependencies(  # type: ignore[arg-type]
        wallet_manager=wallet_mgr,
        chain_executor=chain_exec,
        verifier=verifier,
        ledger=ledger_store,
        compliance=compliance,
        wallet_repository=wallet_repo,
        agent_repo=agent_repo,
    )
    app.include_router(mandates.router, prefix="/api/v2/mandates")

    app.dependency_overrides[ap2.get_deps] = lambda: ap2.Dependencies(  # type: ignore[arg-type]
        verifier=verifier,
        orchestrator=orchestrator,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
        settings=settings,
        wallet_manager=wallet_mgr,
    )
    app.include_router(ap2.router, prefix="/api/v2/ap2")

    app.dependency_overrides[mvp.get_deps] = lambda: mvp.Dependencies(  # type: ignore[arg-type]
        verifier=verifier,
        chain_executor=chain_exec,
        ledger=ledger_store,
        identity_registry=identity_registry,
        settings=settings,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        wallet_manager=wallet_mgr,
        compliance=compliance,
    )
    app.include_router(mvp.router, prefix="/api/v2/mvp", tags=["mvp"])

    app.dependency_overrides[ledger_router.get_deps] = lambda: ledger_router.LedgerDependencies(  # type: ignore[arg-type]
        ledger=ledger_store,
    )
    app.include_router(ledger_router.router, prefix="/api/v2/ledger")

    holds_repo = HoldsRepository(dsn=database_url if use_postgres else "memory://")
    app.dependency_overrides[holds_router.get_deps] = lambda: holds_router.HoldsDependencies(  # type: ignore[arg-type]
        holds_repo=holds_repo,
    )
    app.include_router(holds_router.router, prefix="/api/v2/holds")

    if approvals_router is not None:
        try:
            from sardis_v2_core.approval_repository import ApprovalRepository
            from sardis_v2_core.approval_service import ApprovalService
            approval_repo = ApprovalRepository(dsn=database_url if use_postgres else "memory://")
            approval_service = ApprovalService(repository=approval_repo)
            app.dependency_overrides[approvals_router.get_deps] = lambda: approvals_router.ApprovalsDependencies(  # type: ignore[arg-type]
                approval_service=approval_service,
                approval_repo=approval_repo,
            )
            app.include_router(approvals_router.router, prefix="/api/v2/approvals", tags=["approvals"])
            logger.info("Approvals router registered")
        except ImportError as e:
            logger.warning(f"Approvals dependencies not available: {e}")
    else:
        logger.info("Approvals router not yet available (dependencies not complete)")

    webhook_repo = WebhookRepository(dsn=database_url if use_postgres else "memory://")
    webhook_service = WebhookService(repository=webhook_repo)
    app.dependency_overrides[webhooks_router.get_deps] = lambda: webhooks_router.WebhookDependencies(  # type: ignore[arg-type]
        repository=webhook_repo,
        service=webhook_service,
    )
    app.include_router(webhooks_router.router, prefix="/api/v2/webhooks")
    app.state.webhook_service = webhook_service

    redis_url = (
        os.getenv("SARDIS_REDIS_URL")
        or os.getenv("REDIS_URL")
        or os.getenv("UPSTASH_REDIS_URL")
        or settings.redis_url
        or None
    )
    if settings.is_production and not redis_url:
        raise RuntimeError(
            "CRITICAL: Redis is required in production for idempotency, webhook replay protection, "
            "and JWT revocation. Set SARDIS_REDIS_URL (preferred), REDIS_URL, or UPSTASH_REDIS_URL."
        )
    cache_service = create_cache_service(redis_url)
    app.state.cache_service = cache_service
    logger.info(f"Cache initialized: {'Redis' if redis_url else 'In-memory'}")

    api_key_manager = APIKeyManager(dsn=database_url if use_postgres else "memory://")
    set_api_key_manager(api_key_manager)
    app.state.api_key_manager = api_key_manager

    app.dependency_overrides[transactions_router.get_deps] = lambda: transactions_router.TransactionDependencies(  # type: ignore[arg-type]
        chain_executor=chain_exec,
        canonical_repo=getattr(app.state, "canonical_ledger_repo", None),
    )
    app.include_router(transactions_router.router, prefix="/api/v2/transactions")

    marketplace_repo = MarketplaceRepository(dsn=database_url if use_postgres else "memory://")
    app.dependency_overrides[marketplace_router.get_deps] = lambda: marketplace_router.MarketplaceDependencies(  # type: ignore[arg-type]
        repository=marketplace_repo,
    )
    app.include_router(marketplace_router.router, prefix="/api/v2/marketplace")

    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(auth.router, prefix="/api/v2/auth")

    app.dependency_overrides[wallets_router.get_deps] = lambda: wallets_router.WalletDependencies(  # type: ignore[arg-type]
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=chain_exec,
        wallet_manager=wallet_mgr,
        ledger=ledger_store,
        settings=settings,
        canonical_repo=getattr(app.state, "canonical_ledger_repo", None),
        compliance=compliance,
    )
    app.include_router(wallets_router.router, prefix="/api/v2/wallets", tags=["wallets"])

    app.dependency_overrides[a2a_router.get_deps] = lambda: a2a_router.A2ADependencies(
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=chain_exec,
        wallet_manager=wallet_mgr,
        ledger=ledger_store,
        compliance=compliance,
    )
    app.include_router(a2a_router.router, prefix="/api/v2/a2a", tags=["a2a"])
    app.include_router(a2a_router.public_router, prefix="/api/v2/a2a", tags=["a2a"])

    # OfframpService (used by ramp + cards)
    offramp_service = None
    bridge_api_key = os.getenv("BRIDGE_API_KEY")
    bridge_api_secret = os.getenv("BRIDGE_API_SECRET")
    if bridge_api_key and bridge_api_secret:
        from sardis_cards.offramp import BridgeOfframpProvider, OfframpService
        bridge_env = "sandbox" if not settings.is_production else "production"
        bridge_provider = BridgeOfframpProvider(
            api_key=bridge_api_key,
            api_secret=bridge_api_secret,
            environment=bridge_env,
        )
        offramp_service = OfframpService(provider=bridge_provider)
        logger.info("OfframpService initialized with Bridge provider")
    else:
        from sardis_cards.offramp import OfframpService, MockOfframpProvider
        offramp_service = OfframpService(provider=MockOfframpProvider())
        logger.info("OfframpService initialized with Mock provider (set BRIDGE_API_KEY for real offramp)")

    # Ramp routes (fiat on-ramp / off-ramp)
    onramper_api_key = os.getenv("ONRAMPER_API_KEY", "")
    onramper_webhook_secret = os.getenv("ONRAMPER_WEBHOOK_SECRET", "")
    bridge_webhook_secret = os.getenv("BRIDGE_WEBHOOK_SECRET", "")

    # SardisFiatRamp for bank withdrawal and merchant payment
    fiat_ramp = None
    if bridge_api_key:
        try:
            from sardis_ramp.ramp import SardisFiatRamp
            fiat_ramp = SardisFiatRamp(
                sardis_api_key=os.getenv("SARDIS_API_KEY", ""),
                bridge_api_key=bridge_api_key,
                environment="sandbox" if not settings.is_production else "production",
            )
            logger.info("SardisFiatRamp initialized for bank withdrawal/merchant payment")
        except Exception as e:
            logger.warning("Failed to initialize SardisFiatRamp: %s", e)

    app.dependency_overrides[ramp_router.get_deps] = lambda: ramp_router.RampDependencies(
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        offramp_service=offramp_service,
        onramper_api_key=onramper_api_key,
        onramper_webhook_secret=onramper_webhook_secret,
        bridge_webhook_secret=bridge_webhook_secret,
        fiat_ramp=fiat_ramp,
    )
    app.include_router(ramp_router.router, prefix="/api/v2/ramp", tags=["ramp"])
    if hasattr(ramp_router, "public_router"):
        app.include_router(ramp_router.public_router, prefix="/api/v2/ramp", tags=["ramp"])

    # Treasury routes (Lithic financial accounts + ACH payments)
    treasury_repo = TreasuryRepository(dsn=database_url if use_postgres else None)
    canonical_ledger_repo = CanonicalLedgerRepository(dsn=database_url if use_postgres else None)
    lithic_treasury_client = None
    if os.getenv("LITHIC_API_KEY"):
        try:
            lithic_treasury_client = LithicTreasuryClient(
                api_key=os.getenv("LITHIC_API_KEY", ""),
                environment="production" if settings.is_production else "sandbox",
                webhook_secret=os.getenv("LITHIC_WEBHOOK_SECRET"),
            )
            logger.info("Treasury initialized with Lithic client")
        except Exception as exc:
            logger.warning("Failed to initialize Lithic treasury client: %s", exc)
    else:
        logger.warning("Treasury enabled without Lithic API key; endpoints will return 503 for provider actions")

    app.state.treasury_repo = treasury_repo
    app.state.canonical_ledger_repo = canonical_ledger_repo
    app.state.lithic_treasury_client = lithic_treasury_client
    app.dependency_overrides[treasury_router.get_deps] = lambda: treasury_router.TreasuryDependencies(
        treasury_repo=treasury_repo,
        lithic_client=lithic_treasury_client,
        lithic_webhook_secret=os.getenv("LITHIC_WEBHOOK_SECRET", ""),
        canonical_repo=canonical_ledger_repo,
    )
    app.include_router(treasury_router.router, prefix="/api/v2/treasury", tags=["treasury"])
    if hasattr(treasury_router, "public_router"):
        app.include_router(treasury_router.public_router, prefix="/api/v2/webhooks/lithic", tags=["treasury-webhooks"])
    app.dependency_overrides[treasury_ops_router.get_deps] = lambda: treasury_ops_router.TreasuryOpsDependencies(
        canonical_repo=canonical_ledger_repo,
    )
    app.include_router(treasury_ops_router.router, prefix="/api/v2/treasury/ops", tags=["treasury-ops"])

    # Virtual Card routes (gated behind feature flag)
    if os.getenv("SARDIS_ENABLE_CARDS", "").lower() in ("1", "true", "yes"):
        from sardis_api.repositories.card_repository import CardRepository

        card_repo = CardRepository(dsn=database_url if use_postgres else None)
        from sardis_cards.providers.mock import MockProvider

        configured_primary = (settings.cards.primary_provider or "mock").strip().lower()
        lithic_api_key = settings.lithic.api_key or os.getenv("LITHIC_API_KEY", "")
        stripe_api_key = (
            settings.stripe.api_key
            or os.getenv("STRIPE_API_KEY", "")
            or os.getenv("STRIPE_SECRET_KEY", "")
        )
        stripe_webhook_secret = settings.stripe.webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET", "")

        provider_impl = MockProvider()
        if configured_primary == "lithic":
            if lithic_api_key:
                try:
                    from sardis_cards.providers.lithic import LithicProvider

                    provider_impl = LithicProvider(
                        api_key=lithic_api_key,
                        environment=settings.lithic.environment,
                    )
                    logger.info("Cards enabled with Lithic provider")
                except Exception as exc:
                    logger.warning("Lithic provider init failed; using MockProvider: %s", exc)
            else:
                logger.warning(
                    "Primary card provider is lithic but LITHIC_API_KEY is missing; using MockProvider"
                )
        elif configured_primary == "stripe_issuing":
            if stripe_api_key:
                try:
                    from sardis_cards.providers.stripe_issuing import StripeIssuingProvider

                    provider_impl = StripeIssuingProvider(
                        api_key=stripe_api_key,
                        webhook_secret=stripe_webhook_secret or None,
                    )
                    logger.info("Cards enabled with Stripe Issuing provider")
                except Exception as exc:
                    logger.warning("Stripe Issuing provider init failed; using MockProvider: %s", exc)
            else:
                logger.warning(
                    "Primary card provider is stripe_issuing but STRIPE_API_KEY/STRIPE_SECRET_KEY is missing; using MockProvider"
                )
        else:
            logger.info("Cards enabled with MockProvider (SARDIS_CARDS_PRIMARY_PROVIDER=mock)")

        card_provider = CardProviderCompatAdapter(provider_impl, card_repo)
        webhook_secret = settings.lithic.webhook_secret or os.getenv("LITHIC_WEBHOOK_SECRET")
        asa_handler = None
        asa_secret = (
            settings.lithic.asa_webhook_secret
            or os.getenv("LITHIC_ASA_WEBHOOK_SECRET", "")
            or settings.lithic.webhook_secret
            or os.getenv("LITHIC_WEBHOOK_SECRET", "")
        )
        if getattr(provider_impl, "name", "") == "lithic" and settings.lithic.asa_enabled:
            if not asa_secret:
                logger.warning("LITHIC_ASA is enabled but no ASA webhook secret is configured")
            else:
                from sardis_cards.webhooks import ASAHandler, CardWebhookHandler

                async def _lookup_provider_card(card_token: str):
                    if hasattr(provider_impl, "get_card"):
                        return await provider_impl.get_card(card_token)
                    return None

                asa_handler = ASAHandler(
                    webhook_handler=CardWebhookHandler(secret=asa_secret, provider="lithic"),
                    card_lookup=_lookup_provider_card,
                )
                logger.info("Lithic ASA handler enabled")

        injected_router = cards_router.create_cards_router(
            card_repo,
            card_provider,
            webhook_secret,
            environment=settings.environment,
            offramp_service=offramp_service,
            chain_executor=chain_exec,
            wallet_repo=wallet_repo,
            policy_store=policy_store,
            treasury_repo=treasury_repo,
            agent_repo=agent_repo,
            canonical_repo=canonical_ledger_repo,
            asa_handler=asa_handler,
        )
        app.include_router(injected_router, prefix="/api/v2/cards", tags=["cards"])
    else:
        app.include_router(cards_router.router, prefix="/api/v2/cards", tags=["cards"])

    # Stripe inbound webhooks (Treasury + Issuing)
    stripe_api_key = (
        settings.stripe.api_key
        or os.getenv("STRIPE_API_KEY", "")
        or os.getenv("STRIPE_SECRET_KEY", "")
    )
    stripe_webhook_secret = settings.stripe.webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_financial_account_id = (
        settings.stripe.treasury_financial_account_id
        or os.getenv("STRIPE_TREASURY_FINANCIAL_ACCOUNT_ID", "")
    )
    if stripe_api_key and stripe_webhook_secret:
        from sardis_v2_core.stripe_treasury import StripeTreasuryProvider

        try:
            from sardis_cards.providers.stripe_issuing import StripeIssuingProvider

            issuing_provider = StripeIssuingProvider(
                api_key=stripe_api_key,
                webhook_secret=stripe_webhook_secret,
            )
            treasury_provider = StripeTreasuryProvider(
                stripe_secret_key=stripe_api_key,
                financial_account_id=stripe_financial_account_id or None,
                environment="production" if settings.is_production else "sandbox",
            )
            app.dependency_overrides[stripe_webhooks_router.get_deps] = (
                lambda: stripe_webhooks_router.StripeWebhookDeps(
                    treasury_provider=treasury_provider,
                    issuing_provider=issuing_provider,
                )
            )
            app.include_router(stripe_webhooks_router.router)
            logger.info("Stripe webhook router enabled at /stripe/webhooks")
        except Exception as exc:
            logger.warning("Stripe webhook router not enabled: %s", exc)
    else:
        logger.info("Stripe webhook router disabled (missing STRIPE API key or webhook secret)")

    app.dependency_overrides[agents_router.get_deps] = lambda: agents_router.AgentDependencies(  # type: ignore[arg-type]
        agent_repo=agent_repo,
        wallet_repo=wallet_repo,
    )
    app.include_router(agents_router.router, prefix="/api/v2/agents", tags=["agents"])

    group_repo = AgentGroupRepository(dsn="memory://")
    app.dependency_overrides[groups_router.get_deps] = lambda: groups_router.GroupDependencies(  # type: ignore[arg-type]
        group_repo=group_repo,
    )
    app.include_router(groups_router.router, prefix="/api/v2/groups", tags=["groups"])

    app.include_router(api_keys_router.router, prefix="/api/v2/api-keys", tags=["api-keys"])

    # Checkout routes (Agentic Checkout - Pivot D)
    from sardis_checkout.orchestrator import CheckoutOrchestrator
    from sardis_checkout.connectors.stripe import StripeConnector

    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
    stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    stripe_connector = (
        StripeConnector(api_key=stripe_secret_key, webhook_secret=stripe_webhook_secret)
        if stripe_secret_key
        else None
    )
    checkout_orchestrator = CheckoutOrchestrator()
    if stripe_connector:
        checkout_orchestrator.register_connector("stripe", stripe_connector)

    wallet_repo_for_checkout = WalletRepository(dsn=database_url if use_postgres else "memory://")
    app.dependency_overrides[checkout_router.get_deps] = lambda: checkout_router.CheckoutDependencies(  # type: ignore[arg-type]
        wallet_repo=wallet_repo_for_checkout,
        orchestrator=checkout_orchestrator,
    )
    app.include_router(checkout_router.router, prefix="/api/v2/checkout", tags=["checkout"])
    if hasattr(checkout_router, "public_router"):
        app.include_router(checkout_router.public_router, prefix="/api/v2/checkout", tags=["checkout"])

    app.dependency_overrides[policies_router.get_deps] = lambda: policies_router.PolicyDependencies(  # type: ignore[attr-defined]
        policy_store=policy_store,
        agent_repo=agent_repo,
    )
    app.include_router(policies_router.router, prefix="/api/v2/policies", tags=["policies"])

    app.dependency_overrides[compliance_router.get_deps] = lambda: compliance_router.ComplianceDependencies(
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
    )
    app.include_router(compliance_router.router, prefix="/api/v2/compliance", tags=["compliance"])
    if hasattr(compliance_router, "public_router"):
        app.include_router(compliance_router.public_router, prefix="/api/v2/compliance", tags=["compliance"])

    app.include_router(invoices_router.router, prefix="/api/v2/invoices", tags=["invoices"])

    # Alert routes (REST API and WebSocket)
    app.include_router(alerts_router.router, prefix="/api/v2/alerts", tags=["alerts"])
    app.include_router(ws_alerts_router.router, prefix="/api/v2")

    # Analytics routes
    app.include_router(analytics_router.router)

    # SECURITY: Admin endpoints have much stricter rate limits (10/min vs 100/min)
    app.include_router(admin_router.router, prefix="/api/v2/admin", tags=["admin"])

    # Dev/testnet utility routes - NOT available in production
    if os.getenv("SARDIS_ENVIRONMENT", "dev").lower() not in ("prod", "production"):
        app.include_router(dev_router.router, prefix="/api/v2/dev", tags=["dev"])
        logger.info("Dev routes enabled (faucet, etc.)")

    # Sandbox/Playground routes - no auth required, for developer onboarding
    # Available in all environments but should be rate-limited in production
    app.include_router(sandbox_router.router, prefix="/api/v2/sandbox", tags=["sandbox"])
    logger.info("Sandbox/Playground routes enabled")

    # A2A discovery: /.well-known/agent-card.json
    @app.get("/.well-known/agent-card.json", tags=["a2a"])
    async def well_known_agent_card():
        """A2A agent card for discovery (standard .well-known path)."""
        from .routers.a2a import get_agent_card
        return await get_agent_card()

    # -----------------------------------------------------------------------
    # Health endpoints (extracted to health.py)
    # -----------------------------------------------------------------------
    health_router = create_health_router(
        shutdown_state=shutdown_state,
        use_postgres=use_postgres,
        database_url=database_url,
        redis_url=redis_url or "",
        settings=settings,
    )
    app.include_router(health_router)

    return app


# Required import for JSONResponse in readiness check
from fastapi.responses import JSONResponse
