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
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .bootstrap import bootstrap_monorepo_sys_path, should_bootstrap_monorepo_sys_path

if should_bootstrap_monorepo_sys_path():
    bootstrap_monorepo_sys_path()

from sardis.core import SardisSettings, load_settings
from sardis.core.identity import IdentityRegistry

from .card_runtime import configure_card_runtime
from .checkout_runtime import (
    configure_checkout_orchestrator,
    configure_merchant_checkout_runtime,
)
from .dependencies import (
    configure_api_support_services,
    configure_compliance_services,
    configure_core_services,
    configure_cpn_runtime,
    configure_facility_gate_services,
    configure_inbound_payment_runtime,
    configure_kyc_service,
    configure_payment_runtime,
    configure_provider_runtime,
    configure_ramp_runtime,
    configure_sanctions_service,
    configure_treasury_runtime,
    expose_inbound_payment_state,
    expose_provider_runtime_state,
    expose_runtime_state,
    expose_support_services_state,
    expose_treasury_runtime_state,
    initialize_turnkey_client,
    resolve_cache_backend,
    resolve_storage_backend,
    validate_live_execution_config,
)
from .funding_runtime import (
    configure_funding_adapters,
    configure_recurring_autofund_handler,
    configure_stripe_webhook_issuing_provider,
    resolve_stripe_funding_runtime_config,
)
from .lifespan import lifespan, shutdown_state
from .middleware import (
    API_VERSION,
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
    setup_logging,
)
from .openapi_schema import custom_openapi
from .route_registry.accounts import (
    register_account_group_routes,
    register_account_self_service_routes,
    register_auth_routes,
)
from .route_registry.admin import register_admin_routes
from .route_registry.agents import register_agent_lifecycle_routes
from .route_registry.authority import (
    register_authority_routes,
    register_facility_request_routes,
    register_spending_mandate_routes,
)
from .route_registry.billing import (
    register_billing_routes,
    register_subscription_routes,
)
from .route_registry.commerce import (
    register_checkout_routes,
    register_invoice_routes,
    register_marketplace_routes,
    register_merchant_checkout_routes,
    register_merchant_routes,
    register_secure_checkout_routes,
)
from .route_registry.compliance import register_compliance_routes, register_kyc_onboarding_routes
from .route_registry.developer import (
    register_developer_utility_routes,
    register_enterprise_support_routes,
    register_faucet_routes,
    register_notification_routes,
    register_webhook_subscriptions,
)
from .route_registry.evidence import register_audit_anchor_routes
from .route_registry.health import register_health_routes
from .route_registry.identity import register_agent_auth_routes, register_sso_routes
from .route_registry.money_movement import (
    register_bridge_routes,
    register_hold_routes,
    register_ledger_routes,
    register_pay_endpoint,
    register_refund_routes,
    register_swap_routes,
    register_transaction_routes,
)
from .route_registry.operations import (
    register_alert_routes,
    register_realtime_operations_routes,
)
from .route_registry.policy import register_policy_routes
from .route_registry.protocol import (
    register_a2a_routes,
    register_erc8183_routes,
    register_mpp_routes,
    register_x402_routes,
)
from .route_registry.providers import (
    register_mastercard_webhook_routes,
    register_partner_card_webhook_routes,
    register_polar_webhook_routes,
    register_provider_integration_routes,
    register_stripe_connect_routes,
    register_stripe_funding_routes,
    register_stripe_webhook_routes,
)
from .route_registry.static_routes import register_static_public_routes
from .route_registry.wallets import (
    register_card_routes,
    register_cpn_routes,
    register_funding_capability_routes,
    register_onchain_payment_routes,
    register_ramp_routes,
    register_treasury_routes,
    register_wallet_core_routes,
)

# Configure structured logging
setup_logging(
    json_format=os.getenv("SARDIS_ENVIRONMENT", "dev") != "dev",
    level=os.getenv("LOG_LEVEL", "INFO"),
)
logger = logging.getLogger("server.api")


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
    storage_backend = resolve_storage_backend(settings)
    database_url = storage_backend.database_url
    use_postgres = storage_backend.use_postgres

    # -----------------------------------------------------------------------
    # MPC / Turnkey
    # -----------------------------------------------------------------------
    turnkey_client = initialize_turnkey_client(settings)
    if turnkey_client is not None:
        logger.info("Turnkey MPC client initialized")

    live_execution_config = validate_live_execution_config(settings, turnkey_client=turnkey_client)
    if live_execution_config.chain_mode == "live" and live_execution_config.mpc_name == "local":
        logger.warning(
            "SARDIS_MPC__NAME=local enabled in live mode. This is a custodial signer path for dev/sandbox only."
        )

    # -----------------------------------------------------------------------
    # Core services
    # -----------------------------------------------------------------------
    core_services = configure_core_services(
        settings=settings,
        database_url=database_url,
        use_postgres=use_postgres,
        turnkey_client=turnkey_client,
    )
    policy_store = core_services.policy_store

    wallet_repo = core_services.wallet_repository
    agent_repo = core_services.agent_repository
    wallet_mgr = core_services.wallet_manager
    chain_exec = core_services.chain_executor
    ledger_store = core_services.ledger_store

    kyc_config = configure_kyc_service(settings)
    kyc_service = kyc_config.service
    if kyc_config.mode == "failover":
        logger.info(
            "KYC service configured with failover primary=%s fallback=%s",
            kyc_config.primary_name,
            kyc_config.fallback_name,
        )
    elif kyc_config.mode == "primary":
        logger.info("KYC service configured with provider=%s", kyc_config.primary_name)
    elif kyc_config.mode == "fallback":
        logger.warning(
            "KYC primary provider unavailable; using fallback provider=%s",
            kyc_config.fallback_name,
        )

    sanctions_config = configure_sanctions_service(settings)
    sanctions_service = sanctions_config.service
    if sanctions_config.mode == "failover":
        logger.info(
            "Sanctions service configured with failover primary=%s fallback=%s",
            sanctions_config.primary_name,
            sanctions_config.fallback_name,
        )
    elif sanctions_config.mode == "primary":
        logger.info("Sanctions service configured with provider=%s", sanctions_config.primary_name)
    elif sanctions_config.mode == "fallback":
        logger.warning(
            "Sanctions primary provider unavailable; using fallback provider=%s",
            sanctions_config.fallback_name,
        )

    compliance_config = configure_compliance_services(
        settings=settings,
        database_url=database_url,
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
    )
    audit_store = compliance_config.audit_store
    kya_service = compliance_config.kya_service
    compliance = compliance_config.compliance_engine
    identity_registry = IdentityRegistry()

    # Resolve the Redis URL once (single source of truth) and thread it into the
    # moat so it reuses the already-resolved value instead of re-reading env.
    # This runs before configure_api_support_services, which resolves the same
    # backend again (resolve_cache_backend is a pure, idempotent resolver).
    resolved_redis_url = resolve_cache_backend(settings).redis_url

    payment_runtime = configure_payment_runtime(
        settings=settings,
        database_url=database_url,
        use_postgres=use_postgres,
        identity_registry=identity_registry,
        wallet_manager=wallet_mgr,
        compliance_engine=compliance,
        chain_executor=chain_exec,
        ledger_store=ledger_store,
        # Wire execution-authority ("moat") ports: KYA + sanctions enforcement,
        # spending-mandate revocation, durable dedup, and the settlement lock.
        kya_service=kya_service,
        sanctions_service=sanctions_service,
        redis_url=resolved_redis_url,
    )
    verifier = payment_runtime.verifier
    orchestrator = payment_runtime.orchestrator
    facility_gate_services = configure_facility_gate_services(
        database_url=database_url,
        use_postgres=use_postgres,
    )
    facility_gate_repo = facility_gate_services.repository
    facility_gate_adapter = facility_gate_services.adapter
    expose_runtime_state(
        app,
        settings=settings,
        database_url=database_url,
        use_postgres=use_postgres,
        turnkey_client=turnkey_client,
        policy_store=policy_store,
        chain_executor=chain_exec,
        wallet_repository=wallet_repo,
        compliance_engine=compliance,
        facility_gate_repository=facility_gate_repo,
    )

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

    support_services = configure_api_support_services(
        settings,
        database_url=database_url,
        use_postgres=use_postgres,
    )
    cache_service = support_services.cache_service
    redis_url = support_services.redis_url
    expose_support_services_state(
        app,
        cache_service=cache_service,
        api_key_manager=support_services.api_key_manager,
    )
    logger.info(f"Cache initialized: {'Redis' if redis_url else 'In-memory'}")

    register_transaction_routes(
        app,
        chain_executor=chain_exec,
        canonical_repo=getattr(app.state, "canonical_ledger_repo", None),
    )

    register_marketplace_routes(app, database_url=database_url, use_postgres=use_postgres)

    register_auth_routes(app)

    provider_runtime = configure_provider_runtime(settings)
    configured_on_chain_provider = provider_runtime.on_chain_provider
    coinbase_cdp_provider = provider_runtime.coinbase_cdp_provider
    circle_gateway_nanopayments_client = provider_runtime.circle_gateway_nanopayments_client
    expose_provider_runtime_state(app, provider_runtime=provider_runtime)

    inbound_runtime = configure_inbound_payment_runtime(
        webhook_service=webhook_service,
        ledger_store=ledger_store,
        sanctions_service=sanctions_service,
        wallet_repository=wallet_repo,
    )
    inbound_payment_service = inbound_runtime.inbound_payment_service
    expose_inbound_payment_state(app, inbound_runtime=inbound_runtime)

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

    ramp_runtime = configure_ramp_runtime(settings)
    offramp_service = ramp_runtime.offramp_service

    register_ramp_routes(
        app,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        offramp_service=offramp_service,
        onramper_api_key=ramp_runtime.onramper_api_key,
        onramper_webhook_secret=ramp_runtime.onramper_webhook_secret,
        bridge_webhook_secret=ramp_runtime.bridge_webhook_secret,
        fiat_ramp=ramp_runtime.fiat_ramp,
    )

    register_mpp_routes(app)

    register_faucet_routes(app)

    register_provider_integration_routes(app, settings=settings)

    treasury_runtime = configure_treasury_runtime(
        settings,
        database_url=database_url,
        use_postgres=use_postgres,
    )
    treasury_repo = treasury_runtime.treasury_repository
    canonical_ledger_repo = treasury_runtime.canonical_ledger_repository
    lithic_treasury_client = treasury_runtime.lithic_treasury_client
    expose_treasury_runtime_state(app, treasury_runtime=treasury_runtime)
    register_treasury_routes(
        app,
        treasury_repo=treasury_repo,
        lithic_webhook_secret=treasury_runtime.lithic_webhook_secret,
        lithic_treasury_client=lithic_treasury_client,
        canonical_ledger_repo=canonical_ledger_repo,
    )
    cpn_runtime = configure_cpn_runtime(settings)
    register_cpn_routes(
        app,
        treasury_repo=treasury_repo,
        cpn_client=cpn_runtime.cpn_client,
        webhook_secret=cpn_runtime.webhook_secret,
        environment=settings.environment,
    )

    card_runtime = configure_card_runtime(
        settings,
        database_url=database_url,
        use_postgres=use_postgres,
        policy_store=policy_store,
        wallet_repository=wallet_repo,
        agent_repository=agent_repo,
    )
    card_repo = card_runtime.card_repository
    card_provider = card_runtime.card_provider
    register_card_routes(
        app,
        card_repo=card_repo,
        card_provider=card_provider,
        webhook_secret=card_runtime.webhook_secret,
        environment=settings.environment,
        offramp_service=offramp_service,
        chain_executor=chain_exec,
        wallet_repo=wallet_repo,
        policy_store=policy_store,
        treasury_repo=treasury_repo,
        agent_repo=agent_repo,
        canonical_repo=canonical_ledger_repo,
        asa_handler=card_runtime.asa_handler,
    )
    if card_runtime.cards_enabled:
        register_partner_card_webhook_routes(
            app,
            card_repo=card_repo,
            wallet_repo=wallet_repo,
            agent_repo=agent_repo,
            canonical_repo=canonical_ledger_repo,
            treasury_repo=treasury_repo,
            rain_webhook_secret=card_runtime.rain_webhook_secret,
            bridge_webhook_secret=card_runtime.bridge_webhook_secret,
            environment=settings.environment,
        )

    # Stripe treasury + funding + inbound webhooks
    stripe_funding_runtime = resolve_stripe_funding_runtime_config(settings)
    stripe_api_key = stripe_funding_runtime.stripe_api_key
    stripe_webhook_secret = stripe_funding_runtime.stripe_webhook_secret
    treasury_provider = None
    if stripe_funding_runtime.should_configure_funding_runtime:
        if stripe_api_key:
            from sardis.core.stripe_treasury import StripeTreasuryProvider

        try:
            if stripe_api_key:
                treasury_provider = StripeTreasuryProvider(
                    stripe_secret_key=stripe_api_key,
                    financial_account_id=stripe_funding_runtime.stripe_financial_account_id or None,
                    environment="production" if settings.is_production else "sandbox",
                )

            funding_adapter_runtime = configure_funding_adapters(
                settings,
                treasury_provider=treasury_provider,
                stripe_funding_runtime=stripe_funding_runtime,
            )
            configured_primary_adapter = funding_adapter_runtime.primary_adapter
            configured_fallback_adapter = funding_adapter_runtime.fallback_adapter
            ordered_funding_adapters = funding_adapter_runtime.ordered_adapters

            configure_recurring_autofund_handler(
                recurring_billing_service,
                ordered_funding_adapters,
                chain_mode=settings.chain_mode,
            )

            register_stripe_funding_routes(
                app,
                treasury_provider=treasury_provider,
                funding_adapter=configured_primary_adapter,
                fallback_funding_adapter=configured_fallback_adapter,
                treasury_repo=treasury_repo,
                canonical_repo=canonical_ledger_repo,
                default_connected_account_id=stripe_funding_runtime.stripe_connected_account_default,
                connected_account_map=stripe_funding_runtime.connected_account_map,
                funding_strategy=settings.funding.strategy,
                stablecoin_prefund_enabled=settings.funding.stablecoin_prefund_enabled,
                require_connected_account=settings.funding.require_connected_account,
            )
        except Exception as exc:
            logger.warning("Stripe funding router not enabled: %s", exc)

    if stripe_api_key and stripe_webhook_secret and treasury_provider is not None:
        try:
            issuing_provider = configure_stripe_webhook_issuing_provider(
                stripe_api_key=stripe_api_key,
                stripe_webhook_secret=stripe_webhook_secret,
                policy_store=policy_store,
                wallet_repository=wallet_repo,
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

    checkout_runtime = configure_checkout_orchestrator()

    register_checkout_routes(
        app,
        database_url=database_url,
        use_postgres=use_postgres,
        orchestrator=checkout_runtime.orchestrator,
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

    register_polar_webhook_routes(app)

    register_developer_utility_routes(app, is_production=is_production)

    register_facility_request_routes(
        app,
        repository=facility_gate_repo,
        adapter=facility_gate_adapter,
        approval_service=approval_service,
    )

    register_sso_routes(app)

    merchant_checkout_runtime = configure_merchant_checkout_runtime(
        chain_executor=chain_exec,
        wallet_manager=wallet_mgr,
        compliance_engine=compliance,
        ledger_store=ledger_store,
    )
    merchant_repo = merchant_checkout_runtime.merchant_repository
    merchant_webhook_service = merchant_checkout_runtime.merchant_webhook_service
    settlement_service = merchant_checkout_runtime.settlement_service
    sardis_native_connector = merchant_checkout_runtime.sardis_native_connector
    stripe_connect_provider = merchant_checkout_runtime.stripe_connect_provider

    checkout_runtime.orchestrator.register_connector("sardis", sardis_native_connector)

    # Store settlement service on app.state for background jobs
    app.state.settlement_service = settlement_service
    app.state.merchant_webhook_service = merchant_webhook_service

    checkout_base_url = merchant_checkout_runtime.checkout_base_url
    register_merchant_routes(
        app,
        merchant_repo=merchant_repo,
        wallet_manager=wallet_mgr,
        settlement_service=settlement_service,
        checkout_base_url=checkout_base_url,
    )

    if stripe_connect_provider is not None:
        register_stripe_connect_routes(
            app,
            merchant_repo=merchant_repo,
            stripe_connect_provider=stripe_connect_provider,
        )
    else:
        logger.warning("Stripe Connect not configured, skipping")

    register_merchant_checkout_routes(
        app,
        merchant_repo=merchant_repo,
        sardis_connector=sardis_native_connector,
        wallet_manager=wallet_mgr,
        checkout_base_url=checkout_base_url,
    )

    register_static_public_routes(app)

    register_health_routes(
        app,
        shutdown_state=shutdown_state,
        use_postgres=use_postgres,
        database_url=database_url,
        redis_url=redis_url or "",
        settings=settings,
    )

    return app


# Required import for JSONResponse in readiness check
