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
import json
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
        "sardis-coinbase",
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
from .routers import onchain_payments as onchain_payments_router
from .routers import agents as agents_router
from .routers import api_keys as api_keys_router
from .routers import cards as cards_router
from .routers import partner_card_webhooks as partner_card_webhooks_router
from .routers import stripe_webhooks as stripe_webhooks_router
from .routers import stripe_funding as stripe_funding_router
from .routers import funding_capabilities as funding_capabilities_router
from .routers import checkout as checkout_router
from .routers import secure_checkout as secure_checkout_router
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
from .repositories.secure_checkout_job_repository import SecureCheckoutJobRepository
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
    from sardis_compliance import create_kyc_service, create_sanctions_service, create_kya_service
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
    kya_service = create_kya_service(
        liveness_timeout=int(os.getenv("SARDIS_KYA_LIVENESS_TIMEOUT_SECONDS", "300")),
        dsn=database_url,
    )
    compliance = ComplianceEngine(
        settings=settings,
        audit_store=audit_store,
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
        kya_service=kya_service,
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
    approval_service = None

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
        kya_service=kya_service,
        approval_service=approval_service,
        settings=settings,
        wallet_manager=wallet_mgr,
        policy_store=policy_store,
        audit_store=audit_store,
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

    configured_on_chain_provider = (
        (settings.cards.on_chain_provider or os.getenv("SARDIS_CARDS_ON_CHAIN_PROVIDER", "")).strip().lower()
        or None
    )
    coinbase_cdp_provider = None
    coinbase_enabled = configured_on_chain_provider == "coinbase_cdp" or settings.coinbase.x402_enabled
    if coinbase_enabled:
        cdp_api_key_name = settings.coinbase.api_key_name or os.getenv("COINBASE_CDP_API_KEY_NAME", "")
        cdp_api_key_private_key = (
            settings.coinbase.api_key_private_key
            or os.getenv("COINBASE_CDP_API_KEY_PRIVATE_KEY", "")
        )
        cdp_network_id = settings.coinbase.network_id or os.getenv("COINBASE_CDP_NETWORK_ID", "base-mainnet")
        if cdp_api_key_name and cdp_api_key_private_key:
            try:
                from sardis_coinbase import CoinbaseCDPProvider

                coinbase_cdp_provider = CoinbaseCDPProvider(
                    api_key_name=cdp_api_key_name,
                    api_key_private_key=cdp_api_key_private_key,
                    network_id=cdp_network_id,
                )
                logger.info("Coinbase CDP provider initialized (network=%s)", cdp_network_id)
            except Exception as exc:
                logger.warning("Coinbase CDP provider initialization failed: %s", exc)
        else:
            logger.warning(
                "Coinbase CDP is enabled but credentials are missing "
                "(COINBASE_CDP_API_KEY_NAME / COINBASE_CDP_API_KEY_PRIVATE_KEY)"
            )
    app.state.coinbase_cdp_provider = coinbase_cdp_provider
    app.state.on_chain_provider = configured_on_chain_provider

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
    app.dependency_overrides[onchain_payments_router.get_deps] = lambda: onchain_payments_router.OnChainPaymentDependencies(
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=chain_exec,
        policy_store=policy_store,
        approval_service=approval_service,
        sanctions_service=sanctions_service,
        kya_service=kya_service,
        coinbase_cdp_provider=coinbase_cdp_provider,
        default_on_chain_provider=configured_on_chain_provider,
        audit_store=audit_store,
    )
    app.include_router(onchain_payments_router.router, prefix="/api/v2/wallets", tags=["wallets"])

    app.dependency_overrides[a2a_router.get_deps] = lambda: a2a_router.A2ADependencies(
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=chain_exec,
        wallet_manager=wallet_mgr,
        ledger=ledger_store,
        compliance=compliance,
        identity_registry=identity_registry,
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
    card_repo = None
    card_provider = None
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
        provider_cache: dict[str, object] = {}

        def _build_provider(provider_name: str):
            cached = provider_cache.get(provider_name)
            if cached is not None:
                return cached
            if provider_name == "lithic":
                if not lithic_api_key:
                    logger.warning("LITHIC_API_KEY missing; cannot initialize Lithic provider")
                    return None
                try:
                    from sardis_cards.providers.lithic import LithicProvider

                    provider = LithicProvider(
                        api_key=lithic_api_key,
                        environment=settings.lithic.environment,
                    )
                    provider_cache[provider_name] = provider
                    return provider
                except Exception as exc:
                    logger.warning("Lithic provider init failed: %s", exc)
                    return None
            if provider_name == "stripe_issuing":
                if not stripe_api_key:
                    logger.warning(
                        "STRIPE_API_KEY/STRIPE_SECRET_KEY missing; cannot initialize Stripe Issuing provider"
                    )
                    return None
                try:
                    from sardis_cards.providers.stripe_issuing import StripeIssuingProvider

                    provider = StripeIssuingProvider(
                        api_key=stripe_api_key,
                        webhook_secret=stripe_webhook_secret or None,
                    )
                    provider_cache[provider_name] = provider
                    return provider
                except Exception as exc:
                    logger.warning("Stripe Issuing provider init failed: %s", exc)
                    return None
            if provider_name == "mock":
                provider = MockProvider()
                provider_cache[provider_name] = provider
                return provider
            if provider_name == "rain":
                rain_api_key = settings.rain.api_key or os.getenv("RAIN_API_KEY", "")
                if not rain_api_key:
                    logger.warning("RAIN_API_KEY missing; cannot initialize Rain provider")
                    return None
                try:
                    from sardis_cards.providers.partner_issuers import RainCardsProvider

                    rain_base_url = settings.rain.base_url or os.getenv("RAIN_BASE_URL", "https://api.rain.xyz")
                    provider = RainCardsProvider(
                        api_key=rain_api_key,
                        base_url=rain_base_url,
                        program_id=settings.rain.program_id or os.getenv("RAIN_PROGRAM_ID", ""),
                        path_map=settings.rain.cards_path_map_json or os.getenv("RAIN_CARDS_PATH_MAP_JSON", ""),
                        method_map=settings.rain.cards_method_map_json or os.getenv("RAIN_CARDS_METHOD_MAP_JSON", ""),
                    )
                    provider_cache[provider_name] = provider
                    return provider
                except Exception as exc:
                    logger.warning("Rain provider init failed: %s", exc)
                    return None
            if provider_name == "bridge_cards":
                bridge_api_key = settings.bridge_cards.api_key or os.getenv("BRIDGE_API_KEY", "")
                if not bridge_api_key:
                    logger.warning("BRIDGE_API_KEY missing; cannot initialize Bridge cards provider")
                    return None
                try:
                    from sardis_cards.providers.partner_issuers import BridgeCardsProvider

                    bridge_base_url = (
                        settings.bridge_cards.cards_base_url
                        or os.getenv("BRIDGE_CARDS_BASE_URL", "https://api.bridge.xyz")
                    )
                    provider = BridgeCardsProvider(
                        api_key=bridge_api_key,
                        api_secret=settings.bridge_cards.api_secret or os.getenv("BRIDGE_API_SECRET", ""),
                        base_url=bridge_base_url,
                        program_id=settings.bridge_cards.program_id or os.getenv("BRIDGE_PROGRAM_ID", ""),
                        path_map=(
                            settings.bridge_cards.cards_path_map_json
                            or os.getenv("BRIDGE_CARDS_PATH_MAP_JSON", "")
                        ),
                        method_map=(
                            settings.bridge_cards.cards_method_map_json
                            or os.getenv("BRIDGE_CARDS_METHOD_MAP_JSON", "")
                        ),
                    )
                    provider_cache[provider_name] = provider
                    return provider
                except Exception as exc:
                    logger.warning("Bridge cards provider init failed: %s", exc)
                    return None
            logger.warning("Unknown card provider configured: %s", provider_name)
            return None

        primary_provider = _build_provider(configured_primary)
        configured_fallback = (settings.cards.fallback_provider or "").strip().lower()
        fallback_provider = None
        if configured_fallback and configured_fallback != configured_primary:
            fallback_provider = _build_provider(configured_fallback)

        if primary_provider is None and fallback_provider is not None:
            provider_impl = fallback_provider
            logger.info(
                "Primary card provider unavailable; using fallback provider=%s",
                configured_fallback,
            )
        elif primary_provider is None:
            provider_impl = MockProvider()
            logger.warning("No card provider could be initialized; using MockProvider")
        elif fallback_provider is not None:
            from sardis_cards.providers.router import CardProviderRouter

            provider_impl = CardProviderRouter(primary=primary_provider, fallback=fallback_provider)
            logger.info(
                "Cards enabled with routed providers primary=%s fallback=%s",
                configured_primary,
                configured_fallback,
            )
        else:
            provider_impl = primary_provider
            logger.info("Cards enabled with provider=%s", configured_primary)

        org_overrides_raw = (
            settings.cards.org_provider_overrides_json
            or os.getenv("SARDIS_CARDS_ORG_PROVIDER_OVERRIDES_JSON", "")
        )
        if org_overrides_raw and wallet_repo and agent_repo:
            try:
                parsed = json.loads(org_overrides_raw)
            except json.JSONDecodeError:
                parsed = {}
                logger.warning("Invalid SARDIS_CARDS_ORG_PROVIDER_OVERRIDES_JSON; ignoring")
            if isinstance(parsed, dict) and parsed:
                org_provider_map: dict[str, object] = {}
                for org_id, provider_name in parsed.items():
                    provider_name_str = str(provider_name).strip().lower()
                    provider_candidate = _build_provider(provider_name_str)
                    if provider_candidate is None:
                        logger.warning(
                            "Could not initialize org-specific provider '%s' for org=%s",
                            provider_name_str,
                            org_id,
                        )
                        continue
                    org_provider_map[str(org_id)] = provider_candidate
                if org_provider_map:
                    from sardis_cards.providers.org_router import OrganizationCardProviderRouter

                    async def _resolve_wallet_org(wallet_id: str) -> str | None:
                        wallet = await wallet_repo.get(wallet_id)
                        if not wallet:
                            return None
                        agent = await agent_repo.get(wallet.agent_id)
                        if not agent or not getattr(agent, "owner_id", None):
                            return None
                        return str(agent.owner_id)

                    provider_impl = OrganizationCardProviderRouter(
                        default_provider=provider_impl,
                        providers_by_org=org_provider_map,  # type: ignore[arg-type]
                        wallet_org_resolver=_resolve_wallet_org,
                    )
                    logger.info(
                        "Cards org provider overrides enabled for %d org(s)",
                        len(org_provider_map),
                    )

        card_provider = CardProviderCompatAdapter(provider_impl, card_repo)
        webhook_secret = settings.lithic.webhook_secret or os.getenv("LITHIC_WEBHOOK_SECRET")
        asa_handler = None
        asa_secret = (
            settings.lithic.asa_webhook_secret
            or os.getenv("LITHIC_ASA_WEBHOOK_SECRET", "")
            or settings.lithic.webhook_secret
            or os.getenv("LITHIC_WEBHOOK_SECRET", "")
        )
        lithic_present = configured_primary == "lithic" or configured_fallback == "lithic"
        if lithic_present and settings.lithic.asa_enabled:
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
        app.dependency_overrides[partner_card_webhooks_router.get_deps] = (
            lambda: partner_card_webhooks_router.PartnerCardWebhookDeps(
                card_repo=card_repo,
                wallet_repo=wallet_repo,
                agent_repo=agent_repo,
                canonical_repo=canonical_ledger_repo,
                treasury_repo=treasury_repo,
                rain_webhook_secret=settings.rain.webhook_secret or os.getenv("RAIN_WEBHOOK_SECRET", ""),
                bridge_webhook_secret=(
                    settings.bridge_cards.webhook_secret
                    or os.getenv("BRIDGE_CARDS_WEBHOOK_SECRET", "")
                ),
                environment=settings.environment,
            )
        )
        app.include_router(partner_card_webhooks_router.router, prefix="/api/v2", tags=["partner-card-webhooks"])
    else:
        app.include_router(cards_router.router, prefix="/api/v2/cards", tags=["cards"])

    # Stripe treasury + funding + inbound webhooks
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
    stripe_connected_account_default = (
        settings.stripe.connected_account_id
        or os.getenv("STRIPE_CONNECTED_ACCOUNT_ID", "")
    )
    connected_account_map_raw = (
        settings.stripe.connected_account_map_json
        or os.getenv("STRIPE_CONNECTED_ACCOUNT_MAP_JSON", "")
    )
    connected_account_map: dict[str, str] = {}
    if connected_account_map_raw:
        try:
            parsed = json.loads(connected_account_map_raw)
            if isinstance(parsed, dict):
                connected_account_map = {
                    str(org_id): str(acct_id)
                    for org_id, acct_id in parsed.items()
                    if str(acct_id).strip()
                }
            else:
                logger.warning("STRIPE_CONNECTED_ACCOUNT_MAP_JSON must be a JSON object")
        except json.JSONDecodeError:
            logger.warning("Invalid STRIPE_CONNECTED_ACCOUNT_MAP_JSON; ignoring")

    treasury_provider = None
    if stripe_api_key:
        from sardis_v2_core.stripe_treasury import StripeTreasuryProvider

        try:
            treasury_provider = StripeTreasuryProvider(
                stripe_secret_key=stripe_api_key,
                financial_account_id=stripe_financial_account_id or None,
                environment="production" if settings.is_production else "sandbox",
            )
            app.dependency_overrides[stripe_funding_router.get_deps] = (
                lambda: stripe_funding_router.StripeFundingDeps(
                    treasury_provider=treasury_provider,
                    treasury_repo=treasury_repo,
                    canonical_repo=canonical_ledger_repo,
                    default_connected_account_id=stripe_connected_account_default,
                    connected_account_map=connected_account_map,
                )
            )
            app.include_router(stripe_funding_router.router, prefix="/api/v2")
            logger.info("Stripe funding router enabled at /api/v2/stripe/funding")
        except Exception as exc:
            logger.warning("Stripe funding router not enabled: %s", exc)

    if stripe_api_key and stripe_webhook_secret and treasury_provider is not None:
        try:
            from sardis_cards.providers.stripe_issuing import StripeIssuingProvider

            issuing_provider = StripeIssuingProvider(
                api_key=stripe_api_key,
                webhook_secret=stripe_webhook_secret,
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
        logger.info("Stripe webhook router disabled (missing STRIPE API key/webhook secret)")

    app.dependency_overrides[funding_capabilities_router.get_deps] = (
        lambda: funding_capabilities_router.FundingCapabilitiesDeps(settings=settings)
    )
    app.include_router(funding_capabilities_router.router, prefix="/api/v2")

    app.dependency_overrides[agents_router.get_deps] = lambda: agents_router.AgentDependencies(  # type: ignore[arg-type]
        agent_repo=agent_repo,
        wallet_repo=wallet_repo,
        kya_service=kya_service,
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

    secure_checkout_store = secure_checkout_router.InMemorySecureCheckoutStore()
    if use_postgres:
        secure_checkout_job_repo = SecureCheckoutJobRepository(dsn=database_url)
        secure_checkout_store = secure_checkout_router.RepositoryBackedSecureCheckoutStore(
            secure_checkout_job_repo,
            cache_service=cache_service,
        )
    secure_checkout_enabled = os.getenv("SARDIS_ENABLE_SECURE_CHECKOUT_EXECUTOR", "1").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if settings.is_production and secure_checkout_enabled and not use_postgres:
        raise RuntimeError("secure_checkout_executor requires PostgreSQL in production")
    app.dependency_overrides[secure_checkout_router.get_deps] = (
        lambda: secure_checkout_router.SecureCheckoutDependencies(
            wallet_repo=wallet_repo,
            agent_repo=agent_repo,
            card_repo=card_repo,
            card_provider=card_provider,
            policy_store=policy_store,
            approval_service=approval_service,
            audit_sink=audit_store,
            cache_service=cache_service,
            store=secure_checkout_store,
        )
    )
    if secure_checkout_enabled:
        app.include_router(
            secure_checkout_router.router,
            prefix="/api/v2/checkout",
            tags=["checkout-secure"],
        )

    app.dependency_overrides[policies_router.get_deps] = lambda: policies_router.PolicyDependencies(  # type: ignore[attr-defined]
        policy_store=policy_store,
        agent_repo=agent_repo,
    )
    app.include_router(policies_router.router, prefix="/api/v2/policies", tags=["policies"])

    app.dependency_overrides[compliance_router.get_deps] = lambda: compliance_router.ComplianceDependencies(
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
        audit_store=audit_store,
        kya_service=kya_service,
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

    # Sandbox/Playground routes - no auth required, for developer onboarding.
    # Default: enabled outside production, disabled in production unless explicitly enabled.
    sandbox_env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
    sandbox_flag = os.getenv("SARDIS_ENABLE_SANDBOX", "").strip().lower()
    sandbox_enabled_explicit = sandbox_flag in ("1", "true", "yes", "on")
    sandbox_disabled_explicit = sandbox_flag in ("0", "false", "no", "off")
    if sandbox_env in ("prod", "production"):
        sandbox_enabled = sandbox_enabled_explicit
    else:
        sandbox_enabled = not sandbox_disabled_explicit

    if sandbox_enabled:
        app.include_router(sandbox_router.router, prefix="/api/v2/sandbox", tags=["sandbox"])
        logger.info("Sandbox/Playground routes enabled")
    else:
        logger.info("Sandbox/Playground routes disabled")

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
