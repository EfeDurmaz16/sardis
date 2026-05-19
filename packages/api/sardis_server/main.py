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

import json
import logging
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .bootstrap import bootstrap_monorepo_sys_path, should_bootstrap_monorepo_sys_path

if should_bootstrap_monorepo_sys_path():
    bootstrap_monorepo_sys_path()

from sardis_chain.executor import ChainExecutor
from sardis_compliance.checks import ComplianceEngine
from sardis_ledger.records import LedgerStore
from sardis_protocol.storage import (
    MandateArchive,
    PostgresReplayCache,
    ReplayCache,
    SqliteReplayCache,
)
from sardis_protocol.verifier import MandateVerifier
from sardis_v2_core import InMemoryPolicyStore, PostgresPolicyStore, SardisSettings, load_settings
from sardis_v2_core.agent_repository_postgres import PostgresAgentRepository
from sardis_v2_core.agents import AgentRepository
from sardis_v2_core.cache import create_cache_service
from sardis_v2_core.facility_gate import SimulatedFacilityAdapter
from sardis_v2_core.identity import IdentityRegistry
from sardis_v2_core.inbound_payment_service import InboundPaymentService
from sardis_v2_core.orchestrator import PaymentOrchestrator
from sardis_v2_core.wallet_repository import WalletRepository
from sardis_v2_core.wallet_repository_postgres import PostgresWalletRepository
from sardis_wallet.manager import WalletManager

from .card_adapter import CardProviderCompatAdapter
from .health import create_health_router

# Extracted modules
from .lifespan import lifespan, shutdown_state
from .middleware import (
    API_VERSION,
    APIKeyManager,
    RateLimitConfig,
    RateLimitMiddleware,
    RequestBodyLimitMiddleware,
    RequestIdMiddleware,
    SecurityConfig,
    SecurityHeadersMiddleware,
    StructuredLoggingMiddleware,
    TapMiddlewareConfig,
    TapVerificationMiddleware,
    register_exception_handlers,
    set_api_key_manager,
    setup_logging,
)
from .openapi_schema import custom_openapi
from .providers.lithic_treasury import LithicTreasuryClient
from .repositories.canonical_ledger_repository import CanonicalLedgerRepository
from .repositories.facility_gate_repository import FacilityGateRepository
from .repositories.treasury_repository import TreasuryRepository
from .routing.accounts import (
    register_account_group_routes,
    register_account_self_service_routes,
    register_auth_routes,
)
from .routing.admin import register_admin_routes
from .routing.agents import register_agent_lifecycle_routes, register_agent_registry_routes
from .routing.authority import (
    register_authority_routes,
    register_credential_routes,
    register_facility_request_routes,
    register_mandate_delegation_routes,
    register_mandate_subscription_routes,
    register_spending_mandate_routes,
)
from .routing.billing import (
    register_billing_routes,
    register_subscription_routes,
    register_usage_routes,
)
from .routing.commerce import (
    register_checkout_routes,
    register_commerce_support_routes,
    register_escrow_dispute_routes,
    register_invoice_routes,
    register_marketplace_routes,
    register_merchant_checkout_routes,
    register_merchant_routes,
    register_secure_checkout_routes,
    register_service_directory_routes,
)
from .routing.compliance import (
    register_compliance_export_routes,
    register_compliance_routes,
    register_kyc_onboarding_routes,
)
from .routing.developer import (
    register_developer_utility_routes,
    register_enterprise_support_routes,
    register_faucet_routes,
    register_notification_routes,
    register_template_routes,
    register_webhook_subscriptions,
)
from .routing.evidence import register_audit_anchor_routes, register_evidence_routes
from .routing.identity import register_agent_auth_routes, register_sso_routes
from .routing.money_movement import (
    register_batch_payment_routes,
    register_bridge_routes,
    register_fx_routes,
    register_hold_routes,
    register_ledger_routes,
    register_pay_endpoint,
    register_payment_object_routes,
    register_receipt_routes,
    register_refund_routes,
    register_settlement_routes,
    register_streaming_payment_routes,
    register_swap_routes,
    register_transaction_routes,
)
from .routing.operations import (
    register_alert_routes,
    register_dashboard_metrics_routes,
    register_exception_routes,
    register_execution_mode_routes,
    register_outcome_reliability_routes,
    register_realtime_operations_routes,
)
from .routing.policy import (
    register_fallback_policy_routes,
    register_policy_analytics_routes,
    register_policy_routes,
    register_policy_simulation_routes,
)
from .routing.protocol import (
    register_a2a_routes,
    register_erc8183_routes,
    register_mpp_routes,
    register_protocol_v1_routes,
    register_x402_routes,
)
from .routing.providers import (
    register_mastercard_webhook_routes,
    register_partner_card_webhook_routes,
    register_provider_integration_routes,
    register_stripe_connect_routes,
    register_stripe_funding_routes,
    register_stripe_webhook_routes,
)
from .routing.wallets import (
    register_card_routes,
    register_cpn_routes,
    register_funding_capability_routes,
    register_funding_routes,
    register_onchain_payment_routes,
    register_ramp_edge_routes,
    register_ramp_routes,
    register_treasury_routes,
    register_wallet_core_routes,
)

# Configure structured logging
setup_logging(
    json_format=os.getenv("SARDIS_ENVIRONMENT", "dev") != "dev",
    level=os.getenv("LOG_LEVEL", "INFO"),
)
logger = logging.getLogger("sardis_server.api")


def create_app(settings: SardisSettings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = settings or load_settings()

    # Initialize Sentry for error monitoring (if configured)
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
            from sentry_sdk.integrations.fastapi import FastApiIntegration

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

    # Initialize OpenTelemetry distributed tracing (alongside Sentry)
    if settings.otel_enabled:
        try:
            from .telemetry import init_telemetry, instrument_asyncpg

            init_telemetry(
                service_name=settings.otel_service_name,
                exporter=settings.otel_exporter,
                endpoint=settings.otel_endpoint,
                sample_rate=settings.otel_sample_rate,
            )
            instrument_asyncpg()
        except Exception as exc:
            logger.warning("OpenTelemetry initialization failed: %s", exc)

    is_production = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower() in ("prod", "production")

    app = FastAPI(
        title="Sardis Stablecoin Execution API",
        version=API_VERSION,
        openapi_url=None if is_production else "/api/v2/openapi.json",
        docs_url=None if is_production else "/api/v2/docs",
        redoc_url=None if is_production else "/api/v2/redoc",
        lifespan=lifespan,
        # Disable trailing-slash 307 redirects. The dashboard proxy on
        # app.sardis.sh forwards JWTs in the Authorization header — when
        # FastAPI redirected /api/v2/merchants → /api/v2/merchants/ we saw
        # the second hop arrive at the auth middleware without the bearer
        # token, surfacing as 401 even though the principal was valid.
        # Routers that defined "/" instead of "" used to depend on this
        # redirect; switching it off means each router declaration must
        # match the path the dashboard actually calls (no trailing slash).
        redirect_slashes=False,
    )

    # Override OpenAPI generation with custom schema
    app.openapi = lambda: custom_openapi(app)

    # Register RFC 7807 exception handlers
    register_exception_handlers(app)

    # Register MPP 402 handler (must come after RFC 7807 handlers so it takes priority)
    from .middleware.mpp_gate import _Mpp402, _mpp_402_handler
    app.add_exception_handler(_Mpp402, _mpp_402_handler)  # type: ignore[arg-type]

    # Instrument FastAPI with OpenTelemetry (after app creation)
    if settings.otel_enabled:
        try:
            from .telemetry import instrument_fastapi

            instrument_fastapi(app)
        except Exception as exc:
            logger.warning("OTEL FastAPI instrumentation failed: %s", exc)

    # Exclude paths for middleware
    health_paths = ["/", "/health", "/health/live", "/api/v2/health", "/ready", "/live"]
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
    tap_default = "enabled" if settings.environment == "prod" else "disabled"
    tap_enforcement = os.getenv("SARDIS_TAP_ENFORCEMENT", tap_default).lower()
    if tap_enforcement == "enabled":
        jwks_url = os.getenv("SARDIS_TAP_JWKS_URL")
        jwks_provider = None
        if jwks_url:
            import httpx
            _jwks_cache: dict[str, tuple[dict, float]] = {}  # kid -> (jwks, fetched_at)
            _jwks_ttl = float(os.getenv("SARDIS_TAP_JWKS_TTL_SECONDS", "3600"))  # 1 hour default
            _jwks_max_stale = float(os.getenv("SARDIS_TAP_JWKS_MAX_STALE_SECONDS", "14400"))  # 4h default

            def _jwks_provider(kid: str) -> dict | None:
                now = time.monotonic()
                cached = _jwks_cache.get(kid)
                if cached and (now - cached[1]) < _jwks_ttl:
                    return cached[0]
                try:
                    with httpx.Client(timeout=5.0) as client:
                        resp = client.get(jwks_url)
                        if resp.status_code == 200:
                            jwks = resp.json()
                            _jwks_cache[kid] = (jwks, now)
                            return jwks
                except (httpx.HTTPError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to fetch JWKS from {jwks_url}: {e}")
                    # Return stale cache only if within max_stale window
                    if cached:
                        stale_age = now - cached[1]
                        if stale_age <= _jwks_max_stale:
                            logger.info("Using stale JWKS cache (age=%.0fs, max=%.0fs)", stale_age, _jwks_max_stale)
                            return cached[0]
                        else:
                            logger.error(
                                "JWKS cache expired beyond max_stale (age=%.0fs, max=%.0fs) — rejecting",
                                stale_age, _jwks_max_stale,
                            )
                            return None
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

    # 6b. x402 payment middleware (feature-flag gated)
    if settings.x402.server_enabled:
        from .middleware.x402 import X402MiddlewareConfig, X402PaymentMiddleware
        x402_config = X402MiddlewareConfig.from_environment()
        app.add_middleware(X402PaymentMiddleware, config=x402_config)
        logger.info("x402 payment middleware enabled")
    else:
        logger.info("x402 payment middleware disabled (set SARDIS_X402_SERVER_ENABLED=true to enable)")

    # 6c. Usage metering middleware (plan enforcement, billing-flag gated)
    from .billing.config import BillingConfig as _BillingConfig
    from .middleware.usage_metering import UsageMeteringMiddleware
    _billing_cfg = _BillingConfig()
    app.add_middleware(UsageMeteringMiddleware, billing_config=_billing_cfg)
    if _billing_cfg.billing_enabled:
        logger.info("Usage metering middleware enabled")
    else:
        logger.info("Usage metering middleware loaded (billing disabled — no-op until SARDIS_BILLING_BILLING_ENABLED=true)")

    # 6d. Activity logger middleware (agent sync Layer 1 — fire-and-forget)
    from .middleware.activity_logger import ActivityLoggerMiddleware
    app.add_middleware(ActivityLoggerMiddleware)
    logger.info("Activity logger middleware enabled")

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
            "PAYMENT-SIGNATURE",
            "X-Sardis-Agent-Id",
            "X-Sardis-Session-Id",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-API-Version",
            "X-Response-Time",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
            "PaymentRequired",
            "PAYMENT-RESPONSE",
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

    if settings.is_production and getattr(settings, "chain_mode", "simulated") != "live":
        logger.error(
            "Production boot attempted with non-live chain mode (%s). "
            "Set SARDIS_CHAIN_MODE=live to disable simulated execution.",
            getattr(settings, "chain_mode", "simulated"),
        )
        raise RuntimeError("Production requires SARDIS_CHAIN_MODE=live; simulated execution is disabled")

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
    from sardis_compliance import (
        EllipticProvider,
        FailoverKYCProvider,
        FailoverSanctionsProvider,
        KYCService,
        MockKYCProvider,
        MockSanctionsProvider,
        PersonaKYCProvider,
        SanctionsService,
        create_kya_service,
        create_kyc_service,
        create_sanctions_service,
    )
    from sardis_compliance.providers import ScorechainProvider

    kyc_environment = "production" if settings.is_production else "sandbox"
    kyc_primary_name = (os.getenv("SARDIS_KYC_PRIMARY_PROVIDER", "persona") or "persona").strip().lower()
    kyc_fallback_name = (os.getenv("SARDIS_KYC_FALLBACK_PROVIDER", "") or "").strip().lower()

    def _build_kyc_provider(name: str):
        if not name:
            return None
        if name == "persona":
            persona_api_key = os.getenv("PERSONA_API_KEY", "")
            persona_template_id = os.getenv("PERSONA_TEMPLATE_ID", "")
            if not persona_api_key or not persona_template_id:
                return None
            return PersonaKYCProvider(
                api_key=persona_api_key,
                template_id=persona_template_id,
                webhook_secret=os.getenv("PERSONA_WEBHOOK_SECRET"),
                environment=kyc_environment,
            )
        if name == "mock":
            return MockKYCProvider()
        return None

    kyc_primary_provider = _build_kyc_provider(kyc_primary_name)
    kyc_fallback_provider = (
        _build_kyc_provider(kyc_fallback_name)
        if kyc_fallback_name and kyc_fallback_name != kyc_primary_name
        else None
    )
    if kyc_primary_provider and kyc_fallback_provider:
        kyc_service = KYCService(provider=FailoverKYCProvider(kyc_primary_provider, kyc_fallback_provider))
        logger.info(
            "KYC service configured with failover primary=%s fallback=%s",
            kyc_primary_name,
            kyc_fallback_name,
        )
    elif kyc_primary_provider:
        kyc_service = KYCService(provider=kyc_primary_provider)
        logger.info("KYC service configured with provider=%s", kyc_primary_name)
    elif kyc_fallback_provider:
        kyc_service = KYCService(provider=kyc_fallback_provider)
        logger.warning(
            "KYC primary provider unavailable; using fallback provider=%s",
            kyc_fallback_name,
        )
    else:
        if settings.is_production:
            raise RuntimeError(
                "Production requires at least one KYC provider. "
                "Configure Persona (PERSONA_API_KEY, PERSONA_TEMPLATE_ID) or "
                "iDenfy (IDENFY_API_KEY, IDENFY_API_SECRET)."
            )
        kyc_service = create_kyc_service(
            api_key=os.getenv("PERSONA_API_KEY"),
            template_id=os.getenv("PERSONA_TEMPLATE_ID"),
            webhook_secret=os.getenv("PERSONA_WEBHOOK_SECRET"),
            environment=kyc_environment,
        )

    sanctions_primary_name = (os.getenv("SARDIS_SANCTIONS_PRIMARY_PROVIDER", "elliptic") or "elliptic").strip().lower()
    sanctions_fallback_name = (os.getenv("SARDIS_SANCTIONS_FALLBACK_PROVIDER", "") or "").strip().lower()

    def _build_sanctions_provider(name: str):
        if not name:
            return None
        if name == "elliptic":
            elliptic_api_key = os.getenv("ELLIPTIC_API_KEY", "")
            elliptic_api_secret = os.getenv("ELLIPTIC_API_SECRET", "")
            if not elliptic_api_key or not elliptic_api_secret:
                return None
            return EllipticProvider(
                api_key=elliptic_api_key,
                api_secret=elliptic_api_secret,
            )
        if name == "scorechain":
            scorechain_api_key = os.getenv("SCORECHAIN_API_KEY", "")
            if not scorechain_api_key or ScorechainProvider is None:
                return None
            return ScorechainProvider(api_key=scorechain_api_key)
        if name == "mock":
            return MockSanctionsProvider()
        return None

    sanctions_primary_provider = _build_sanctions_provider(sanctions_primary_name)
    sanctions_fallback_provider = (
        _build_sanctions_provider(sanctions_fallback_name)
        if sanctions_fallback_name and sanctions_fallback_name != sanctions_primary_name
        else None
    )
    if sanctions_primary_provider and sanctions_fallback_provider:
        sanctions_service = SanctionsService(
            provider=FailoverSanctionsProvider(
                sanctions_primary_provider,
                sanctions_fallback_provider,
            )
        )
        logger.info(
            "Sanctions service configured with failover primary=%s fallback=%s",
            sanctions_primary_name,
            sanctions_fallback_name,
        )
    elif sanctions_primary_provider:
        sanctions_service = SanctionsService(provider=sanctions_primary_provider)
        logger.info("Sanctions service configured with provider=%s", sanctions_primary_name)
    elif sanctions_fallback_provider:
        sanctions_service = SanctionsService(provider=sanctions_fallback_provider)
        logger.warning(
            "Sanctions primary provider unavailable; using fallback provider=%s",
            sanctions_fallback_name,
        )
    else:
        if settings.is_production:
            raise RuntimeError(
                "Production requires at least one sanctions provider. "
                "Configure Elliptic (ELLIPTIC_API_KEY, ELLIPTIC_API_SECRET) or "
                "Scorechain (SCORECHAIN_API_KEY)."
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
    app.state.wallet_repo = wallet_repo
    app.state.compliance_engine = compliance
    facility_gate_repo = FacilityGateRepository(dsn=database_url if use_postgres else "memory://")
    facility_gate_adapter = SimulatedFacilityAdapter()
    app.state.facility_gate_repo = facility_gate_repo

    logger.info(f"API initialized with storage backend: {'PostgreSQL' if use_postgres else 'SQLite/Memory'}")

    # -----------------------------------------------------------------------
    # Router registration
    # -----------------------------------------------------------------------
    approval_service = register_authority_routes(
        app,
        wallet_manager=wallet_mgr,
        chain_executor=chain_exec,
        verifier=verifier,
        ledger=ledger_store,
        compliance=compliance,
        wallet_repository=wallet_repo,
        agent_repo=agent_repo,
        orchestrator=orchestrator,
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
        kya_service=kya_service,
        settings=settings,
        policy_store=policy_store,
        audit_store=audit_store,
        identity_registry=identity_registry,
        dsn=database_url if use_postgres else "memory://",
    )

    register_pay_endpoint(
        app,
        orchestrator=orchestrator,
        chain_mode=settings.chain_mode,
    )

    register_ledger_routes(app, ledger_store=ledger_store)
    register_hold_routes(app, database_url=database_url, use_postgres=use_postgres)

    webhook_service = register_webhook_subscriptions(
        app,
        dsn=database_url if use_postgres else "memory://",
    )

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

    register_transaction_routes(
        app,
        chain_executor=chain_exec,
        canonical_repo=getattr(app.state, "canonical_ledger_repo", None),
    )

    register_marketplace_routes(app, database_url=database_url, use_postgres=use_postgres)

    register_auth_routes(app)

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

    circle_gateway_nanopayments_client = None
    if bool(getattr(settings.circle_gateway, "x402_enabled", False)):
        circle_gateway_api_key = (
            settings.circle_gateway.api_key
            or os.getenv("CIRCLE_GATEWAY_API_KEY", "")
        )
        if circle_gateway_api_key:
            try:
                from .providers.circle_gateway_nanopayments import (
                    CircleGatewayNanopaymentsClient,
                )

                circle_gateway_nanopayments_client = CircleGatewayNanopaymentsClient(
                    api_key=circle_gateway_api_key,
                    base_url=(
                        settings.circle_gateway.base_url
                        or os.getenv("CIRCLE_GATEWAY_BASE_URL", "")
                    ),
                    timeout_seconds=float(settings.circle_gateway.timeout_seconds),
                )
                logger.info("Circle Gateway nanopayments provider initialized")
            except Exception as exc:
                logger.warning("Circle Gateway nanopayments initialization failed: %s", exc)
        else:
            logger.warning(
                "Circle Gateway x402 is enabled but CIRCLE_GATEWAY_API_KEY is missing"
            )
    app.state.circle_gateway_nanopayments_client = circle_gateway_nanopayments_client

    # Inbound payment service (deposit monitoring + receive endpoints)
    from sardis_v2_core.event_bus import get_default_bus
    event_bus = get_default_bus()
    event_bus.set_webhook_service(webhook_service)

    inbound_payment_service = InboundPaymentService(
        event_bus=event_bus,
        ledger=ledger_store,
        sanctions_service=sanctions_service,
        wallet_repo=wallet_repo,
    )
    app.state.inbound_payment_service = inbound_payment_service
    app.state.event_bus = event_bus

    register_wallet_core_routes(
        app,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=chain_exec,
        wallet_manager=wallet_mgr,
        ledger=ledger_store,
        settings=settings,
        compliance=compliance,
        inbound_payment_service=inbound_payment_service,
        circle_nanopayments_client=circle_gateway_nanopayments_client,
    )

    register_bridge_routes(app, wallet_repo=wallet_repo, chain_executor=chain_exec)
    logger.info("Bridge router registered at /api/v2/bridge")

    register_x402_routes(app, facilitator_enabled=settings.x402.facilitator_enabled)
    register_erc8183_routes(app, enabled=settings.erc8183.enabled)

    recurring_billing_service = register_subscription_routes(
        app,
        database_url=database_url,
        use_postgres=use_postgres,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=chain_exec,
        wallet_manager=wallet_mgr,
        compliance=compliance,
        allow_simulated_autofund=settings.chain_mode != "live",
        live_mode=settings.chain_mode == "live",
    )

    register_enterprise_support_routes(
        app,
        database_url=database_url,
        use_postgres=use_postgres,
    )

    register_audit_anchor_routes(
        app,
        chain_executor=chain_exec,
        ledger_store=ledger_store,
    )

    register_onchain_payment_routes(
        app,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        policy_store=policy_store,
        approval_service=approval_service,
        sanctions_service=sanctions_service,
        kya_service=kya_service,
        coinbase_cdp_provider=coinbase_cdp_provider,
        default_on_chain_provider=configured_on_chain_provider,
        audit_store=audit_store,
        settings=settings,
        payment_orchestrator=orchestrator,
    )

    register_refund_routes(app)

    register_a2a_routes(
        app,
        database_url=database_url,
        use_postgres=use_postgres,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=chain_exec,
        wallet_manager=wallet_mgr,
        ledger_store=ledger_store,
        compliance=compliance,
        identity_registry=identity_registry,
        audit_store=audit_store,
        approval_service=approval_service,
    )

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
        if settings.is_production:
            logger.warning(
                "OfframpService NOT initialized: BRIDGE_API_KEY missing in production. "
                "Off-ramp endpoints will return 503 until BRIDGE_API_KEY is set."
            )
            offramp_service = None
        else:
            from sardis_cards.offramp import MockOfframpProvider, OfframpService
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
                sardis_key=os.getenv("SARDIS_API_KEY", ""),
                bridge_api_key=bridge_api_key,
                environment="sandbox" if not settings.is_production else "production",
            )
            logger.info("SardisFiatRamp initialized for bank withdrawal/merchant payment")
        except Exception as e:
            logger.warning("Failed to initialize SardisFiatRamp: %s", e)

    register_ramp_routes(
        app,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        offramp_service=offramp_service,
        onramper_api_key=onramper_api_key,
        onramper_webhook_secret=onramper_webhook_secret,
        bridge_webhook_secret=bridge_webhook_secret,
        fiat_ramp=fiat_ramp,
    )

    register_mpp_routes(app)

    register_faucet_routes(app)

    register_provider_integration_routes(app, settings=settings)

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
    register_treasury_routes(
        app,
        treasury_repo=treasury_repo,
        lithic_webhook_secret=os.getenv("LITHIC_WEBHOOK_SECRET", ""),
        lithic_treasury_client=lithic_treasury_client,
        canonical_ledger_repo=canonical_ledger_repo,
    )
    cpn_client = None
    circle_cpn_api_key_for_router = (
        settings.circle_cpn.api_key
        or os.getenv("SARDIS_CIRCLE_CPN__API_KEY", "")
        or os.getenv("CIRCLE_CPN_API_KEY", "")
    )
    circle_cpn_enabled_for_router = bool(
        settings.circle_cpn.enabled
        or os.getenv("SARDIS_CIRCLE_CPN__ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
        or os.getenv("CIRCLE_CPN_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    )
    if circle_cpn_enabled_for_router and circle_cpn_api_key_for_router:
        try:
            from .providers.circle_cpn import CircleCPNClient

            cpn_client = CircleCPNClient(
                api_key=circle_cpn_api_key_for_router,
                base_url=settings.circle_cpn.base_url or "https://api.circle.com",
                payout_path=settings.circle_cpn.payout_path or "/v1/cpn/payments",
                collection_path=settings.circle_cpn.collection_path or "/v1/cpn/collections",
                status_path=settings.circle_cpn.status_path or "/v1/cpn/payments/{payment_id}",
                auth_style=settings.circle_cpn.auth_style or "bearer",
                timeout_seconds=float(settings.circle_cpn.timeout_seconds),
                program_id=(
                    settings.circle_cpn.program_id
                    or os.getenv("SARDIS_CIRCLE_CPN__PROGRAM_ID", "")
                    or os.getenv("CIRCLE_CPN_PROGRAM_ID", "")
                ),
            )
        except Exception as exc:
            logger.warning("Circle CPN client init failed for router: %s", exc)
            cpn_client = None

    register_cpn_routes(
        app,
        treasury_repo=treasury_repo,
        cpn_client=cpn_client,
        webhook_secret=(
            settings.circle_cpn.webhook_secret
            or os.getenv("SARDIS_CIRCLE_CPN__WEBHOOK_SECRET", "")
            or os.getenv("CIRCLE_CPN_WEBHOOK_SECRET", "")
        ),
        environment=settings.environment,
    )

    # Virtual Card routes (gated behind feature flag)
    card_repo = None
    card_provider = None
    if os.getenv("SARDIS_ENABLE_CARDS", "").lower() in ("1", "true", "yes"):
        from sardis_server.repositories.card_repository import CardRepository

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

                    async def _stripe_policy_evaluator(
                        _wallet_id: str,
                        _amount,
                        _mcc_code: str,
                        _merchant_name: str,
                    ) -> tuple[bool, str]:
                        from decimal import Decimal as _Decimal
                        _amount = _Decimal(str(_amount))
                        if not policy_store or not wallet_repo:
                            return True, "OK"
                        _wallet = await wallet_repo.get(_wallet_id)
                        if not _wallet:
                            return True, "OK"
                        _policy = await policy_store.fetch_policy(_wallet.agent_id)
                        if not _policy:
                            return True, "OK"
                        _merchant_category = None
                        if _mcc_code:
                            from sardis_v2_core.mcc_service import get_mcc_info
                            _mcc_info = get_mcc_info(_mcc_code)
                            if _mcc_info:
                                _merchant_category = _mcc_info.category
                        return _policy.validate_payment(
                            amount=_amount,
                            fee=_Decimal("0"),
                            mcc_code=_mcc_code,
                            merchant_category=_merchant_category,
                        )

                    provider = StripeIssuingProvider(
                        api_key=stripe_api_key,
                        webhook_secret=stripe_webhook_secret or None,
                        policy_evaluator=_stripe_policy_evaluator,
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

        register_card_routes(
            app,
            card_repo=card_repo,
            card_provider=card_provider,
            webhook_secret=webhook_secret,
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
        register_partner_card_webhook_routes(
            app,
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
    else:
        register_card_routes(
            app,
            card_repo=card_repo,
            card_provider=None,
            webhook_secret=None,
            environment=settings.environment,
            offramp_service=offramp_service,
            chain_executor=chain_exec,
            wallet_repo=wallet_repo,
            policy_store=policy_store,
            treasury_repo=treasury_repo,
            agent_repo=agent_repo,
            canonical_repo=canonical_ledger_repo,
        )

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
    circle_cpn_api_key = (
        settings.circle_cpn.api_key
        or os.getenv("SARDIS_CIRCLE_CPN__API_KEY", "")
        or os.getenv("CIRCLE_CPN_API_KEY", "")
    )
    if (
        stripe_api_key
        or circle_cpn_api_key
        or settings.rain.api_key
        or os.getenv("RAIN_API_KEY", "")
        or settings.bridge_cards.api_key
        or os.getenv("BRIDGE_API_KEY", "")
        or settings.coinbase.topup_api_key
        or os.getenv("COINBASE_CDP_TOPUP_API_KEY", "")
        or settings.chain_mode == "live"
    ):
        if stripe_api_key:
            from sardis_v2_core.stripe_treasury import StripeTreasuryProvider

        try:
            if stripe_api_key:
                treasury_provider = StripeTreasuryProvider(
                    stripe_secret_key=stripe_api_key,
                    financial_account_id=stripe_financial_account_id or None,
                    environment="production" if settings.is_production else "sandbox",
                )

            from sardis_v2_core.cpn_funding_adapter import CircleCPNFundingAdapter
            from sardis_v2_core.funding import HttpTopupFundingAdapter, StripeIssuingFundingAdapter

            def _build_funding_adapter(adapter_name: str):
                normalized = (adapter_name or "").strip().lower()
                if not normalized:
                    return None
                if normalized == "stripe":
                    if treasury_provider is None:
                        logger.warning(
                            "Stripe treasury provider unavailable; cannot initialize Stripe funding adapter"
                        )
                        return None
                    return StripeIssuingFundingAdapter(treasury_provider)
                if normalized == "rain":
                    rain_api_key = settings.rain.api_key or os.getenv("RAIN_API_KEY", "")
                    if not rain_api_key:
                        logger.warning("RAIN_API_KEY missing; cannot initialize Rain funding adapter")
                        return None
                    return HttpTopupFundingAdapter(
                        provider="rain",
                        rail="stablecoin",
                        base_url=settings.rain.base_url or "https://api.rain.xyz",
                        api_key=rain_api_key,
                        topup_path=settings.rain.funding_topup_path or "/v1/funding/topups",
                        auth_style="bearer",
                        program_id=settings.rain.program_id or os.getenv("RAIN_PROGRAM_ID", ""),
                    )
                if normalized == "bridge":
                    bridge_api_key = settings.bridge_cards.api_key or os.getenv("BRIDGE_API_KEY", "")
                    if not bridge_api_key:
                        logger.warning("BRIDGE_API_KEY missing; cannot initialize Bridge funding adapter")
                        return None
                    return HttpTopupFundingAdapter(
                        provider="bridge",
                        rail="stablecoin",
                        base_url=settings.bridge_cards.cards_base_url or "https://api.bridge.xyz",
                        api_key=bridge_api_key,
                        api_secret=settings.bridge_cards.api_secret or os.getenv("BRIDGE_API_SECRET", ""),
                        topup_path=settings.bridge_cards.funding_topup_path or "/v1/funding/topups",
                        auth_style="x_api_key",
                        program_id=settings.bridge_cards.program_id or os.getenv("BRIDGE_PROGRAM_ID", ""),
                    )
                if normalized == "coinbase_cdp":
                    coinbase_topup_api_key = (
                        settings.coinbase.topup_api_key
                        or os.getenv("COINBASE_CDP_TOPUP_API_KEY", "")
                    )
                    if not coinbase_topup_api_key:
                        logger.warning(
                            "COINBASE_CDP_TOPUP_API_KEY missing; cannot initialize Coinbase funding adapter"
                        )
                        return None
                    return HttpTopupFundingAdapter(
                        provider="coinbase_cdp",
                        rail="stablecoin",
                        base_url=settings.coinbase.topup_base_url or "https://api.coinbase.com",
                        api_key=coinbase_topup_api_key,
                        topup_path=settings.coinbase.topup_path or "/v1/funding/topups",
                        auth_style="bearer",
                    )
                if normalized == "circle_cpn":
                    if not circle_cpn_api_key:
                        logger.warning("CIRCLE_CPN_API_KEY missing; cannot initialize Circle CPN funding adapter")
                        return None
                    return CircleCPNFundingAdapter(
                        api_key=circle_cpn_api_key,
                        base_url=settings.circle_cpn.base_url or "https://api.circle.com",
                        payout_path=settings.circle_cpn.payout_path or "/v1/cpn/payments",
                        status_path=settings.circle_cpn.status_path or "/v1/cpn/payments/{payment_id}",
                        auth_style=settings.circle_cpn.auth_style or "bearer",
                        timeout_seconds=float(settings.circle_cpn.timeout_seconds),
                        program_id=(
                            settings.circle_cpn.program_id
                            or os.getenv("SARDIS_CIRCLE_CPN__PROGRAM_ID", "")
                            or os.getenv("CIRCLE_CPN_PROGRAM_ID", "")
                        ),
                    )
                logger.warning(
                    "Funding adapter '%s' requested but not wired in this deployment",
                    normalized,
                )
                return None

            configured_primary_adapter = _build_funding_adapter(settings.funding.primary_adapter)
            configured_fallback_adapter = _build_funding_adapter(settings.funding.fallback_adapter or "")
            ordered_funding_adapters = [
                adapter for adapter in (configured_primary_adapter, configured_fallback_adapter) if adapter is not None
            ]

            if ordered_funding_adapters:
                from sardis_v2_core.funding import FundingRequest, execute_funding_with_failover
                from sardis_v2_core.tokens import TokenType, normalize_token_amount

                async def _recurring_autofund_handler(subscription: dict[str, object], amount_minor: int) -> str:
                    token_raw = str(subscription.get("token") or "USDC").upper()
                    try:
                        token_type = TokenType(token_raw)
                    except ValueError as exc:
                        raise ValueError(f"unsupported_autofund_token:{token_raw}") from exc
                    amount = normalize_token_amount(token_type, max(int(amount_minor), 0))
                    if amount <= 0:
                        raise ValueError("autofund_amount_must_be_positive")
                    request = FundingRequest(
                        amount=amount,
                        currency="USD",
                        description=f"Recurring auto-fund for subscription {subscription.get('id', 'unknown')}",
                        metadata={
                            "source": "recurring_billing",
                            "subscription_id": str(subscription.get("id", "")),
                            "wallet_id": str(subscription.get("wallet_id", "")),
                            "chain": str(subscription.get("chain", "")),
                            "token": token_raw,
                        },
                    )
                    transfer, attempts = await execute_funding_with_failover(ordered_funding_adapters, request)
                    logger.info(
                        "Recurring auto-fund routed provider=%s transfer_id=%s attempts=%d",
                        transfer.provider,
                        transfer.transfer_id,
                        len(attempts),
                    )
                    return transfer.transfer_id

                recurring_billing_service.configure_autofund_handler(
                    _recurring_autofund_handler,
                    allow_simulated_fallback=False,
                )
            elif settings.chain_mode == "live":
                recurring_billing_service.configure_autofund_handler(
                    None,
                    allow_simulated_fallback=False,
                )
                logger.warning(
                    "Live recurring auto-fund is enabled but no funding adapters are configured; "
                    "autofund requests will fail closed."
                )

            register_stripe_funding_routes(
                app,
                treasury_provider=treasury_provider,
                funding_adapter=configured_primary_adapter,
                fallback_funding_adapter=configured_fallback_adapter,
                treasury_repo=treasury_repo,
                canonical_repo=canonical_ledger_repo,
                default_connected_account_id=stripe_connected_account_default,
                connected_account_map=connected_account_map,
                funding_strategy=settings.funding.strategy,
                stablecoin_prefund_enabled=settings.funding.stablecoin_prefund_enabled,
                require_connected_account=settings.funding.require_connected_account,
            )
        except Exception as exc:
            logger.warning("Stripe funding router not enabled: %s", exc)

    if stripe_api_key and stripe_webhook_secret and treasury_provider is not None:
        try:
            from sardis_cards.providers.stripe_issuing import StripeIssuingProvider

            async def _stripe_webhooks_policy_evaluator(
                _wallet_id: str,
                _amount,
                _mcc_code: str,
                _merchant_name: str,
            ) -> tuple[bool, str]:
                from decimal import Decimal as _Decimal
                _amount = _Decimal(str(_amount))
                if not policy_store or not wallet_repo:
                    return True, "OK"
                _wallet = await wallet_repo.get(_wallet_id)
                if not _wallet:
                    return True, "OK"
                _policy = await policy_store.fetch_policy(_wallet.agent_id)
                if not _policy:
                    return True, "OK"
                _merchant_category = None
                if _mcc_code:
                    from sardis_v2_core.mcc_service import get_mcc_info
                    _mcc_info = get_mcc_info(_mcc_code)
                    if _mcc_info:
                        _merchant_category = _mcc_info.category
                return _policy.validate_payment(
                    amount=_amount,
                    fee=_Decimal("0"),
                    mcc_code=_mcc_code,
                    merchant_category=_merchant_category,
                )

            issuing_provider = StripeIssuingProvider(
                api_key=stripe_api_key,
                webhook_secret=stripe_webhook_secret,
                policy_evaluator=_stripe_webhooks_policy_evaluator,
            )
            register_stripe_webhook_routes(
                app,
                treasury_provider=treasury_provider,
                issuing_provider=issuing_provider,
            )
        except Exception as exc:
            logger.warning("Stripe webhook router not enabled: %s", exc)
    else:
        logger.info("Stripe webhook router disabled (missing STRIPE API key/webhook secret)")

    register_mastercard_webhook_routes(app)

    register_funding_capability_routes(app, settings=settings)

    register_agent_lifecycle_routes(
        app,
        agent_repo=agent_repo,
        wallet_repo=wallet_repo,
        kya_service=kya_service,
        wallet_manager=wallet_mgr,
        database_url=database_url,
        settings=settings,
    )

    register_account_group_routes(app)

    # Checkout routes (Agentic Checkout - Pivot D)
    from sardis_checkout.connectors.stripe import StripeConnector
    from sardis_checkout.orchestrator import CheckoutOrchestrator

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

    register_checkout_routes(
        app,
        database_url=database_url,
        use_postgres=use_postgres,
        orchestrator=checkout_orchestrator,
    )

    register_secure_checkout_routes(
        app,
        database_url=database_url,
        use_postgres=use_postgres,
        is_production=settings.is_production,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        card_repo=card_repo,
        card_provider=card_provider,
        policy_store=policy_store,
        approval_service=approval_service,
        audit_store=audit_store,
        cache_service=cache_service,
    )

    register_policy_routes(app, policy_store=policy_store, agent_repo=agent_repo)

    register_compliance_routes(
        app,
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
        audit_store=audit_store,
        kya_service=kya_service,
        policy_store=policy_store,
        approval_service=approval_service,
    )

    register_kyc_onboarding_routes(app)

    register_account_self_service_routes(app)

    register_invoice_routes(app)

    register_notification_routes(app)

    register_alert_routes(app)
    register_swap_routes(app)
    register_realtime_operations_routes(app)

    register_admin_routes(app)

    register_billing_routes(app)

    register_spending_mandate_routes(app)

    register_agent_auth_routes(app)

    # Polar.sh billing webhook (pre-incorporation MoR)
    try:
        from sardis_server.routes.providers import polar_webhook as polar_webhook_router
        app.include_router(
            polar_webhook_router.router,
            prefix="/api/v2/billing",
            tags=["billing"],
        )
    except ImportError:
        pass

    register_developer_utility_routes(app, is_production=is_production)

    register_evidence_routes(app)
    register_facility_request_routes(
        app,
        repository=facility_gate_repo,
        adapter=facility_gate_adapter,
        approval_service=approval_service,
    )

    register_sso_routes(app)

    # -----------------------------------------------------------------------
    # Merchant checkout ("Pay with Sardis")
    # -----------------------------------------------------------------------
    from sardis_checkout.connectors.sardis_native import SardisNativeConnector
    from sardis_checkout.merchant_webhooks import MerchantWebhookService
    from sardis_checkout.settlement import SettlementService
    from sardis_v2_core.merchant import MerchantRepository

    merchant_repo = MerchantRepository()
    merchant_webhook_service = MerchantWebhookService(merchant_repo=merchant_repo)

    # Initialize Stripe Connect provider for settlement (optional)
    _stripe_connect_for_settlement = None
    try:
        from sardis_v2_core.stripe_connect import StripeConnectProvider
        _stripe_connect_for_settlement = StripeConnectProvider()
    except (ImportError, ValueError):
        pass  # Stripe not configured, skip

    settlement_service = SettlementService(
        merchant_repo=merchant_repo,
        offramp_service=None,  # Wire Bridge offramp when configured
        merchant_webhook_service=merchant_webhook_service,
        stripe_connect_provider=_stripe_connect_for_settlement,
    )

    sardis_native_connector = SardisNativeConnector(
        chain_executor=chain_exec,
        wallet_manager=wallet_mgr,
        compliance_engine=compliance,
        ledger_store=ledger_store,
        merchant_repo=merchant_repo,
        settlement_service=settlement_service,
        merchant_webhook_service=merchant_webhook_service,
    )

    checkout_orchestrator.register_connector("sardis", sardis_native_connector)

    # Store settlement service on app.state for background jobs
    app.state.settlement_service = settlement_service
    app.state.merchant_webhook_service = merchant_webhook_service

    checkout_base_url = os.getenv("SARDIS_CHECKOUT_BASE_URL", "https://checkout.sardis.sh")
    register_merchant_routes(
        app,
        merchant_repo=merchant_repo,
        wallet_manager=wallet_mgr,
        settlement_service=settlement_service,
        checkout_base_url=checkout_base_url,
    )

    # --- Stripe Connect (Sardis Connect) ---
    try:
        from sardis_v2_core.stripe_connect import StripeConnectProvider
        stripe_connect_provider = StripeConnectProvider()
        register_stripe_connect_routes(
            app,
            merchant_repo=merchant_repo,
            stripe_connect_provider=stripe_connect_provider,
        )
    except (ImportError, ValueError) as e:
        logger.warning("Stripe Connect not configured, skipping: %s", e)

    register_merchant_checkout_routes(
        app,
        merchant_repo=merchant_repo,
        sardis_connector=sardis_native_connector,
        wallet_manager=wallet_mgr,
        checkout_base_url=checkout_base_url,
    )

    # --- Service Directory, Compliance Export, Agent Registry ---
    register_service_directory_routes(app)
    register_compliance_export_routes(app)
    register_agent_registry_routes(app)

    # --- Delegated payment rails routers ---
    register_credential_routes(app)
    register_execution_mode_routes(app)
    register_settlement_routes(app)

    # --- Trust & Evidence Platform routers ---
    register_policy_simulation_routes(app)
    register_receipt_routes(app)
    register_outcome_reliability_routes(app)
    register_policy_analytics_routes(app)
    register_exception_routes(app)
    register_template_routes(app)
    register_fallback_policy_routes(app)
    register_commerce_support_routes(app)
    register_dashboard_metrics_routes(app)

    # Protocol v1.0 routers
    register_payment_object_routes(app)
    register_funding_routes(app)
    register_mandate_delegation_routes(app)
    register_fx_routes(app)
    register_usage_routes(app)
    register_escrow_dispute_routes(app)
    register_batch_payment_routes(app)
    register_mandate_subscription_routes(app)
    register_streaming_payment_routes(app)
    register_protocol_v1_routes(app)
    register_ramp_edge_routes(app)

    # A2A discovery: /.well-known/agent-card.json
    @app.get("/.well-known/agent-card.json", tags=["a2a"])
    async def well_known_agent_card():
        """A2A agent card for discovery (standard .well-known path)."""
        from .routes.protocol.a2a import get_agent_card
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
