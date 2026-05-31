"""Dependency injection container for Sardis API.

Provides centralized dependency management with:
- Fail-fast initialization for required dependencies
- Graceful degradation for optional dependencies
- Lazy initialization with caching
- Type-safe dependency access
"""
from __future__ import annotations

import logging
import os
import warnings
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Mapping, TypeVar

from sardis.core import SardisSettings, load_settings
from sardis.core.exceptions import SardisDependencyNotConfiguredError

logger = logging.getLogger(__name__)

T = TypeVar("T")
_DEFAULT_PROVIDER = object()


@dataclass
class DependencyConfig:
    """Configuration for optional dependencies."""

    # Database
    database_url: str = ""
    use_postgres: bool = False

    # Cache
    redis_url: str | None = None

    # External services
    stripe_enabled: bool = False
    turnkey_enabled: bool = False
    persona_enabled: bool = False
    elliptic_enabled: bool = False
    lithic_enabled: bool = False
    didit_enabled: bool = False

    @classmethod
    def from_environment(cls) -> DependencyConfig:
        """Load configuration from environment variables."""
        database_url = os.getenv("DATABASE_URL", "")
        use_postgres = database_url.startswith(("postgresql://", "postgres://"))

        return cls(
            database_url=database_url,
            use_postgres=use_postgres,
            redis_url=os.getenv("SARDIS_REDIS_URL") or os.getenv("REDIS_URL") or os.getenv("UPSTASH_REDIS_URL"),
            stripe_enabled=bool(os.getenv("STRIPE_SECRET_KEY")),
            turnkey_enabled=bool(os.getenv("TURNKEY_API_PUBLIC_KEY") or os.getenv("TURNKEY_API_KEY")),
            persona_enabled=bool(os.getenv("PERSONA_API_KEY")),
            elliptic_enabled=bool(os.getenv("ELLIPTIC_API_KEY")),
            lithic_enabled=bool(os.getenv("LITHIC_API_KEY")),
            didit_enabled=bool(os.getenv("DIDIT_API_KEY")),
        )


@dataclass(frozen=True)
class StorageBackendConfig:
    """Resolved API storage backend configuration."""

    database_url: str
    use_postgres: bool


@dataclass(frozen=True)
class CacheBackendConfig:
    """Resolved API cache backend configuration."""

    redis_url: str | None


@dataclass(frozen=True)
class LiveExecutionConfig:
    """Resolved live execution signer configuration."""

    chain_mode: str
    mpc_name: str


@dataclass(frozen=True)
class KYCServiceConfig:
    """Resolved KYC service and provider selection metadata."""

    service: Any
    primary_name: str
    fallback_name: str
    mode: str


@dataclass(frozen=True)
class SanctionsServiceConfig:
    """Resolved sanctions service and provider selection metadata."""

    service: Any
    primary_name: str
    fallback_name: str
    mode: str


@dataclass(frozen=True)
class ComplianceServicesConfig:
    """Resolved compliance engine and its backing services."""

    audit_store: Any
    kya_service: Any
    compliance_engine: Any
    kya_liveness_timeout: int


@dataclass(frozen=True)
class CoreServicesConfig:
    """Resolved core API service graph used by route registrars."""

    policy_store: Any
    wallet_repository: Any
    agent_repository: Any
    wallet_manager: Any
    chain_executor: Any
    ledger_store: Any


@dataclass(frozen=True)
class PaymentRuntimeConfig:
    """Resolved payment runtime primitives used by execution routes."""

    archive: Any
    replay_cache: Any
    verifier: Any
    orchestrator: Any
    #: Human-in-the-loop gate wired into the orchestrator (durable signed store
    #: + delivery notifier). Exposed so the ApprovalRequest API can record
    #: decisions against the SAME gate the orchestrator re-executes from.
    approval_gate: Any | None = None
    #: Programmable-recourse engine wired into the orchestrator (durable signed
    #: RecourseHold store + swappable executor). Exposed so the escrow/dispute
    #: API backs holds onto the SAME engine the orchestrator opens them from.
    recourse_engine: Any | None = None


@dataclass(frozen=True)
class MoatPortsConfig:
    """Resolved optional execution-authority ports for the orchestrator.

    These are the "moat" enforcement hooks: spending-mandate revocation lookup,
    KYA, sanctions screening, durable dedup, the settlement advisory lock, and
    the durable reconciliation queue.  When omitted the orchestrator silently
    falls back to inert / in-memory behaviour, so they MUST be wired in
    production.
    """

    kya_service: Any
    sanctions_service: Any
    dedup_store: Any
    spending_mandate_lookup: Any
    settlement_lock: Any | None
    reconciliation_queue: Any | None


@dataclass(frozen=True)
class APISupportServicesConfig:
    """Resolved API support services exposed through app.state."""

    cache_service: Any
    api_key_manager: Any
    redis_url: str | None
    api_key_manager_dsn: str


@dataclass(frozen=True)
class FacilityGateServicesConfig:
    """Resolved Facility Gate repository and execution adapter."""

    repository: Any
    adapter: Any
    dsn: str


@dataclass(frozen=True)
class ProviderRuntimeConfig:
    """Resolved optional provider runtime clients used by payment routes."""

    on_chain_provider: str | None
    coinbase_cdp_provider: Any | None
    circle_gateway_nanopayments_client: Any | None


@dataclass(frozen=True)
class InboundPaymentRuntimeConfig:
    """Resolved inbound payment runtime services."""

    event_bus: Any
    inbound_payment_service: Any


@dataclass(frozen=True)
class RampRuntimeConfig:
    """Resolved fiat ramp/off-ramp services and webhook credentials."""

    offramp_service: Any | None
    onramper_api_key: str
    onramper_webhook_secret: str
    bridge_webhook_secret: str
    fiat_ramp: Any | None


@dataclass(frozen=True)
class TreasuryRuntimeConfig:
    """Resolved treasury repositories and optional Lithic client."""

    treasury_repository: Any
    canonical_ledger_repository: Any
    lithic_treasury_client: Any | None
    lithic_webhook_secret: str


@dataclass(frozen=True)
class CPNRuntimeConfig:
    """Resolved Circle CPN route client and webhook credential."""

    cpn_client: Any | None
    webhook_secret: str


def resolve_storage_backend(
    settings: Any,
    *,
    environ: Mapping[str, str] | None = None,
) -> StorageBackendConfig:
    """Resolve storage backend settings and enforce production durability."""
    env = environ if environ is not None else os.environ
    database_url = (
        env.get("DATABASE_URL")
        or getattr(settings, "database_url", "")
        or getattr(settings, "ledger_dsn", "")
        or ""
    )
    use_postgres = database_url.startswith(("postgresql://", "postgres://"))

    if getattr(settings, "is_production", False):
        if not database_url:
            raise RuntimeError("CRITICAL: DATABASE_URL is required in production.")
        if not use_postgres:
            raise RuntimeError(
                "CRITICAL: Production requires PostgreSQL. "
                "Set DATABASE_URL to a postgres/postgresql URL."
            )

    return StorageBackendConfig(database_url=database_url, use_postgres=use_postgres)


def resolve_cache_backend(
    settings: Any,
    *,
    environ: Mapping[str, str] | None = None,
) -> CacheBackendConfig:
    """Resolve cache backend settings and enforce production Redis durability."""
    env = environ if environ is not None else os.environ
    redis_url = (
        env.get("SARDIS_REDIS_URL")
        or env.get("REDIS_URL")
        or env.get("UPSTASH_REDIS_URL")
        or getattr(settings, "redis_url", None)
        or None
    )

    if getattr(settings, "is_production", False) and not redis_url:
        raise RuntimeError(
            "CRITICAL: Redis is required in production for idempotency, webhook replay protection, "
            "and JWT revocation. Set SARDIS_REDIS_URL (preferred), REDIS_URL, or UPSTASH_REDIS_URL."
        )

    return CacheBackendConfig(redis_url=redis_url)


def validate_live_execution_config(
    settings: Any,
    *,
    turnkey_client: Any | None,
    environ: Mapping[str, str] | None = None,
) -> LiveExecutionConfig:
    """Validate chain execution and signer safety before booting the API."""
    env = environ if environ is not None else os.environ
    chain_mode = str(getattr(settings, "chain_mode", "simulated") or "simulated")

    if getattr(settings, "is_production", False) and chain_mode != "live":
        raise RuntimeError("Production requires SARDIS_CHAIN_MODE=live; simulated execution is disabled")

    mpc_settings = getattr(settings, "mpc", None)
    settings_mpc_name = getattr(mpc_settings, "name", "simulated")
    mpc_name = str(env.get("SARDIS_MPC__NAME", settings_mpc_name) or settings_mpc_name).strip().lower()

    if chain_mode == "live":
        if mpc_name == "simulated":
            raise RuntimeError("Simulated signer is not allowed for live chain mode")
        if mpc_name == "turnkey" and turnkey_client is None:
            raise RuntimeError("Turnkey MPC provider required for live chain mode but not configured")
        if mpc_name == "fireblocks" and not env.get("FIREBLOCKS_API_KEY"):
            raise RuntimeError("Fireblocks MPC provider required for live chain mode but not configured")
        if mpc_name == "local":
            if getattr(settings, "is_production", False):
                raise RuntimeError("Local signer is custodial and not allowed in production live mode")
            if not env.get("SARDIS_EOA_PRIVATE_KEY"):
                raise RuntimeError("SARDIS_MPC__NAME=local requires SARDIS_EOA_PRIVATE_KEY in live mode")

    return LiveExecutionConfig(chain_mode=chain_mode, mpc_name=mpc_name)


def initialize_turnkey_client(
    settings: Any,
    *,
    environ: Mapping[str, str] | None = None,
    client_cls: Any | None = None,
) -> Any | None:
    """Initialize the optional shared Turnkey client when all credentials exist."""
    env = environ if environ is not None else os.environ
    turnkey_settings = getattr(settings, "turnkey", None)
    api_key = (
        env.get("TURNKEY_API_PUBLIC_KEY")
        or env.get("TURNKEY_API_KEY")
        or getattr(turnkey_settings, "api_public_key", "")
    )
    api_private_key = env.get("TURNKEY_API_PRIVATE_KEY") or getattr(
        turnkey_settings,
        "api_private_key",
        "",
    )
    organization_id = env.get("TURNKEY_ORGANIZATION_ID") or getattr(
        turnkey_settings,
        "organization_id",
        "",
    )

    if not (api_key and api_private_key and organization_id):
        return None

    if client_cls is None:
        try:
            from sardis.wallet.turnkey_client import TurnkeyClient
        except ImportError:
            return None
        client_cls = TurnkeyClient

    return client_cls(
        api_key=api_key,
        api_private_key=api_private_key,
        organization_id=organization_id,
    )


def configure_kyc_service(
    settings: Any,
    *,
    environ: Mapping[str, str] | None = None,
    kyc_service_cls: Any | None = None,
    failover_provider_cls: Any | None = None,
    persona_provider_cls: Any | None = None,
    mock_provider_cls: Any | None = None,
    create_kyc_service_fn: Any | None = None,
) -> KYCServiceConfig:
    """Resolve the KYC provider stack and enforce production configuration."""
    env = environ if environ is not None else os.environ
    kyc_environment = "production" if getattr(settings, "is_production", False) else "sandbox"
    primary_name = (env.get("SARDIS_KYC_PRIMARY_PROVIDER", "persona") or "persona").strip().lower()
    fallback_name = (env.get("SARDIS_KYC_FALLBACK_PROVIDER", "") or "").strip().lower()

    if (
        kyc_service_cls is None
        or failover_provider_cls is None
        or persona_provider_cls is None
        or mock_provider_cls is None
        or create_kyc_service_fn is None
    ):
        from sardis.compliance import (
            FailoverKYCProvider,
            KYCService,
            MockKYCProvider,
            PersonaKYCProvider,
            create_kyc_service,
        )

        kyc_service_cls = kyc_service_cls or KYCService
        failover_provider_cls = failover_provider_cls or FailoverKYCProvider
        persona_provider_cls = persona_provider_cls or PersonaKYCProvider
        mock_provider_cls = mock_provider_cls or MockKYCProvider
        create_kyc_service_fn = create_kyc_service_fn or create_kyc_service

    def build_provider(name: str) -> Any | None:
        if not name:
            return None
        if name == "persona":
            persona_api_key = env.get("PERSONA_API_KEY", "")
            persona_template_id = env.get("PERSONA_TEMPLATE_ID", "")
            if not persona_api_key or not persona_template_id:
                return None
            return persona_provider_cls(
                api_key=persona_api_key,
                template_id=persona_template_id,
                webhook_secret=env.get("PERSONA_WEBHOOK_SECRET"),
                environment=kyc_environment,
            )
        if name == "mock":
            return mock_provider_cls()
        return None

    primary_provider = build_provider(primary_name)
    fallback_provider = (
        build_provider(fallback_name)
        if fallback_name and fallback_name != primary_name
        else None
    )

    if primary_provider and fallback_provider:
        return KYCServiceConfig(
            service=kyc_service_cls(
                provider=failover_provider_cls(primary_provider, fallback_provider)
            ),
            primary_name=primary_name,
            fallback_name=fallback_name,
            mode="failover",
        )
    if primary_provider:
        return KYCServiceConfig(
            service=kyc_service_cls(provider=primary_provider),
            primary_name=primary_name,
            fallback_name=fallback_name,
            mode="primary",
        )
    if fallback_provider:
        return KYCServiceConfig(
            service=kyc_service_cls(provider=fallback_provider),
            primary_name=primary_name,
            fallback_name=fallback_name,
            mode="fallback",
        )

    if getattr(settings, "is_production", False):
        raise RuntimeError(
            "Production requires at least one KYC provider. "
            "Configure Persona (PERSONA_API_KEY, PERSONA_TEMPLATE_ID) or "
            "iDenfy (IDENFY_API_KEY, IDENFY_API_SECRET)."
        )

    return KYCServiceConfig(
        service=create_kyc_service_fn(
            api_key=env.get("PERSONA_API_KEY"),
            template_id=env.get("PERSONA_TEMPLATE_ID"),
            webhook_secret=env.get("PERSONA_WEBHOOK_SECRET"),
            environment=kyc_environment,
        ),
        primary_name=primary_name,
        fallback_name=fallback_name,
        mode="factory",
    )


def configure_sanctions_service(
    settings: Any,
    *,
    environ: Mapping[str, str] | None = None,
    sanctions_service_cls: Any | None = None,
    failover_provider_cls: Any | None = None,
    elliptic_provider_cls: Any | None = None,
    scorechain_provider_cls: Any = _DEFAULT_PROVIDER,
    mock_provider_cls: Any | None = None,
    create_sanctions_service_fn: Any | None = None,
) -> SanctionsServiceConfig:
    """Resolve the sanctions provider stack and enforce production configuration."""
    env = environ if environ is not None else os.environ
    primary_name = (
        env.get("SARDIS_SANCTIONS_PRIMARY_PROVIDER", "elliptic") or "elliptic"
    ).strip().lower()
    fallback_name = (env.get("SARDIS_SANCTIONS_FALLBACK_PROVIDER", "") or "").strip().lower()

    if (
        sanctions_service_cls is None
        or failover_provider_cls is None
        or elliptic_provider_cls is None
        or mock_provider_cls is None
        or create_sanctions_service_fn is None
    ):
        from sardis.compliance import (
            EllipticProvider,
            FailoverSanctionsProvider,
            MockSanctionsProvider,
            SanctionsService,
            create_sanctions_service,
        )

        sanctions_service_cls = sanctions_service_cls or SanctionsService
        failover_provider_cls = failover_provider_cls or FailoverSanctionsProvider
        elliptic_provider_cls = elliptic_provider_cls or EllipticProvider
        mock_provider_cls = mock_provider_cls or MockSanctionsProvider
        create_sanctions_service_fn = (
            create_sanctions_service_fn or create_sanctions_service
        )

    if scorechain_provider_cls is _DEFAULT_PROVIDER:
        try:
            from sardis.compliance.providers import ScorechainProvider
        except ImportError:
            scorechain_provider_cls = None
        else:
            scorechain_provider_cls = ScorechainProvider

    def build_provider(name: str) -> Any | None:
        if not name:
            return None
        if name == "elliptic":
            elliptic_api_key = env.get("ELLIPTIC_API_KEY", "")
            elliptic_api_secret = env.get("ELLIPTIC_API_SECRET", "")
            if not elliptic_api_key or not elliptic_api_secret:
                return None
            return elliptic_provider_cls(
                api_key=elliptic_api_key,
                api_secret=elliptic_api_secret,
            )
        if name == "scorechain":
            scorechain_api_key = env.get("SCORECHAIN_API_KEY", "")
            if not scorechain_api_key or scorechain_provider_cls is None:
                return None
            return scorechain_provider_cls(api_key=scorechain_api_key)
        if name == "mock":
            return mock_provider_cls()
        return None

    primary_provider = build_provider(primary_name)
    fallback_provider = (
        build_provider(fallback_name)
        if fallback_name and fallback_name != primary_name
        else None
    )

    if primary_provider and fallback_provider:
        return SanctionsServiceConfig(
            service=sanctions_service_cls(
                provider=failover_provider_cls(primary_provider, fallback_provider)
            ),
            primary_name=primary_name,
            fallback_name=fallback_name,
            mode="failover",
        )
    if primary_provider:
        return SanctionsServiceConfig(
            service=sanctions_service_cls(provider=primary_provider),
            primary_name=primary_name,
            fallback_name=fallback_name,
            mode="primary",
        )
    if fallback_provider:
        return SanctionsServiceConfig(
            service=sanctions_service_cls(provider=fallback_provider),
            primary_name=primary_name,
            fallback_name=fallback_name,
            mode="fallback",
        )

    if getattr(settings, "is_production", False):
        raise RuntimeError(
            "Production requires at least one sanctions provider. "
            "Configure Elliptic (ELLIPTIC_API_KEY, ELLIPTIC_API_SECRET) or "
            "Scorechain (SCORECHAIN_API_KEY)."
        )

    return SanctionsServiceConfig(
        service=create_sanctions_service_fn(
            api_key=env.get("ELLIPTIC_API_KEY"),
            api_secret=env.get("ELLIPTIC_API_SECRET"),
        ),
        primary_name=primary_name,
        fallback_name=fallback_name,
        mode="factory",
    )


def configure_compliance_services(
    settings: Any,
    *,
    database_url: str,
    kyc_service: Any,
    sanctions_service: Any,
    environ: Mapping[str, str] | None = None,
    create_audit_store_fn: Any | None = None,
    create_kya_service_fn: Any | None = None,
    compliance_engine_cls: Any | None = None,
) -> ComplianceServicesConfig:
    """Create the compliance engine and durable compliance support services."""
    env = environ if environ is not None else os.environ

    if (
        create_audit_store_fn is None
        or create_kya_service_fn is None
        or compliance_engine_cls is None
    ):
        from sardis.compliance import create_kya_service
        from sardis.compliance.checks import ComplianceEngine, create_audit_store

        create_audit_store_fn = create_audit_store_fn or create_audit_store
        create_kya_service_fn = create_kya_service_fn or create_kya_service
        compliance_engine_cls = compliance_engine_cls or ComplianceEngine

    liveness_timeout = int(env.get("SARDIS_KYA_LIVENESS_TIMEOUT_SECONDS", "300"))
    audit_store = create_audit_store_fn(dsn=database_url)
    kya_service = create_kya_service_fn(
        liveness_timeout=liveness_timeout,
        dsn=database_url,
    )
    compliance_engine = compliance_engine_cls(
        settings=settings,
        audit_store=audit_store,
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
        kya_service=kya_service,
    )

    return ComplianceServicesConfig(
        audit_store=audit_store,
        kya_service=kya_service,
        compliance_engine=compliance_engine,
        kya_liveness_timeout=liveness_timeout,
    )


def configure_core_services(
    settings: Any,
    *,
    database_url: str,
    use_postgres: bool,
    turnkey_client: Any | None,
    postgres_policy_store_cls: Any | None = None,
    in_memory_policy_store_cls: Any | None = None,
    postgres_wallet_repository_cls: Any | None = None,
    wallet_repository_cls: Any | None = None,
    postgres_agent_repository_cls: Any | None = None,
    agent_repository_cls: Any | None = None,
    wallet_manager_cls: Any | None = None,
    chain_executor_cls: Any | None = None,
    ledger_store_cls: Any | None = None,
) -> CoreServicesConfig:
    """Create the core service graph shared by payment, authority, and wallet routes."""
    if postgres_policy_store_cls is None or in_memory_policy_store_cls is None:
        from sardis.core import InMemoryPolicyStore, PostgresPolicyStore

        postgres_policy_store_cls = postgres_policy_store_cls or PostgresPolicyStore
        in_memory_policy_store_cls = in_memory_policy_store_cls or InMemoryPolicyStore

    if postgres_wallet_repository_cls is None or wallet_repository_cls is None:
        from sardis.core.wallet_repository import WalletRepository
        from sardis.core.wallet_repository_postgres import PostgresWalletRepository

        postgres_wallet_repository_cls = (
            postgres_wallet_repository_cls or PostgresWalletRepository
        )
        wallet_repository_cls = wallet_repository_cls or WalletRepository

    if postgres_agent_repository_cls is None or agent_repository_cls is None:
        from sardis.core.agent_repository_postgres import PostgresAgentRepository
        from sardis.core.agents import AgentRepository

        postgres_agent_repository_cls = postgres_agent_repository_cls or PostgresAgentRepository
        agent_repository_cls = agent_repository_cls or AgentRepository

    if wallet_manager_cls is None:
        from sardis.wallet.manager import WalletManager

        wallet_manager_cls = WalletManager
    if chain_executor_cls is None:
        from sardis.chain.executor import ChainExecutor

        chain_executor_cls = ChainExecutor
    if ledger_store_cls is None:
        from sardis.ledger.records import LedgerStore

        ledger_store_cls = LedgerStore

    policy_store = (
        postgres_policy_store_cls(database_url)
        if use_postgres
        else in_memory_policy_store_cls()
    )
    wallet_repository = (
        postgres_wallet_repository_cls(database_url)
        if use_postgres
        else wallet_repository_cls(dsn="memory://")
    )
    agent_repository = (
        postgres_agent_repository_cls(database_url)
        if use_postgres
        else agent_repository_cls(dsn="memory://")
    )
    wallet_manager = wallet_manager_cls(
        settings=settings,
        turnkey_client=turnkey_client,
        async_policy_store=policy_store,
    )
    chain_executor = chain_executor_cls(settings=settings, turnkey_client=turnkey_client)
    ledger_store = ledger_store_cls(
        dsn=database_url if use_postgres else settings.ledger_dsn
    )

    return CoreServicesConfig(
        policy_store=policy_store,
        wallet_repository=wallet_repository,
        agent_repository=agent_repository,
        wallet_manager=wallet_manager,
        chain_executor=chain_executor,
        ledger_store=ledger_store,
    )


def _build_redis_client(redis_url: str | None) -> Any | None:
    """Construct an async Redis client from a URL, or ``None`` if unavailable.

    Connection is lazy (``redis.asyncio.from_url`` does not connect eagerly), so
    this is safe to call from a synchronous DI accessor.
    """
    if not redis_url:
        return None
    try:
        import redis.asyncio as aioredis

        return aioredis.from_url(redis_url, decode_responses=True)
    except Exception as e:  # pragma: no cover - redis import/url failure
        logger.warning("Redis client unavailable for dedup store: %s", e)
        return None


def build_moat_ports(
    settings: Any,
    *,
    database_url: str,
    use_postgres: bool,
    kya_service: Any,
    sanctions_service: Any,
    redis_url: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> MoatPortsConfig:
    """Construct the orchestrator's execution-authority ("moat") ports.

    Single source of truth shared by ``configure_payment_runtime`` (the prod
    path used by ``create_app``) and ``DependencyContainer.payment_orchestrator``
    so the moat cannot drift inert in one path while being wired in the other.

    - ``spending_mandate_lookup``: DB-backed revocation/scope enforcement.
    - ``dedup_store``: Redis (durable) when a Redis URL is available, else
      in-memory (dev only). Fail-closed in production: a non-durable dedup
      store would leave duplicate-payment protection process-local, so we
      raise rather than silently degrade on a money path.
    - ``settlement_lock`` / ``reconciliation_queue``: Postgres-backed when
      running on Postgres, else ``None`` (dev/in-memory).

    ``redis_url`` is authoritative when explicitly passed (the resolved value
    from ``create_app`` / the container). Only fall back to the environment
    triplet when it was not supplied.
    """
    env = environ if environ is not None else os.environ

    from sardis.core.dedup_store import InMemoryDedupStore, RedisDedupStore
    from sardis.core.spending_mandate_lookup import SpendingMandateLookup

    resolved_redis_url = redis_url if redis_url is not None else (
        env.get("SARDIS_REDIS_URL")
        or env.get("REDIS_URL")
        or env.get("UPSTASH_REDIS_URL")
    )
    redis_client = _build_redis_client(resolved_redis_url)
    dedup_store: Any = (
        RedisDedupStore(redis_client) if redis_client is not None else InMemoryDedupStore()
    )

    # Fail-closed: production/staging MUST use a durable, shared dedup store.
    # A silent InMemoryDedupStore fallback (missing URL OR failed client
    # construction) would make duplicate-payment protection process-local.
    # configure_payment_runtime runs before the cache backend is resolved, so
    # this guard is the moat's own enforcement point.
    if isinstance(dedup_store, InMemoryDedupStore) and getattr(
        settings, "is_production", False
    ):
        raise RuntimeError(
            "CRITICAL: durable Redis dedup store required in production — "
            "set SARDIS_REDIS_URL and install the redis extra "
            "(pip install 'sardis[redis]')."
        )

    # In Postgres mode, wire the DB-backed lookup so revocation/scope/limit
    # enforcement is active.  In dev/in-memory mode the lookup has no table to
    # read and its get_active_mandate ALWAYS returns None — and the orchestrator
    # now fails CLOSED on a None from a configured lookup.  Injecting it in dev
    # would therefore deny EVERY local/in-memory payment as
    # ``no_active_spending_mandate``.  So we leave it unset in dev (mandate
    # enforcement is skipped locally, matching prior dev behavior); production
    # always runs on Postgres and gets the real lookup.
    spending_mandate_lookup: Any | None = (
        SpendingMandateLookup(dsn=database_url) if use_postgres else None
    )

    settlement_lock: Any | None = None
    reconciliation_queue: Any | None = None
    if use_postgres:
        from sardis.core.database import LazyPool
        from sardis.core.reconciliation_queue_postgres import PostgresReconciliationQueue
        from sardis.core.settlement_lock import SettlementLock

        pool = LazyPool()
        settlement_lock = SettlementLock(pool)
        reconciliation_queue = PostgresReconciliationQueue(pool)

    return MoatPortsConfig(
        kya_service=kya_service,
        sanctions_service=sanctions_service,
        dedup_store=dedup_store,
        spending_mandate_lookup=spending_mandate_lookup,
        settlement_lock=settlement_lock,
        reconciliation_queue=reconciliation_queue,
    )


def configure_payment_runtime(
    settings: Any,
    *,
    database_url: str,
    use_postgres: bool,
    identity_registry: Any,
    wallet_manager: Any,
    compliance_engine: Any,
    chain_executor: Any,
    ledger_store: Any,
    mandate_archive_cls: Any | None = None,
    postgres_replay_cache_cls: Any | None = None,
    sqlite_replay_cache_cls: Any | None = None,
    replay_cache_cls: Any | None = None,
    mandate_verifier_cls: Any | None = None,
    payment_orchestrator_cls: Any | None = None,
    kya_service: Any | None = None,
    sanctions_service: Any | None = None,
    group_policy: Any | None = None,
    redis_url: str | None = None,
    notification_port: Any | None = None,
) -> PaymentRuntimeConfig:
    """Create mandate verification and payment orchestration primitives."""
    if (
        mandate_archive_cls is None
        or postgres_replay_cache_cls is None
        or sqlite_replay_cache_cls is None
        or replay_cache_cls is None
    ):
        from sardis.protocol.storage import (
            MandateArchive,
            PostgresReplayCache,
            ReplayCache,
            SqliteReplayCache,
        )

        mandate_archive_cls = mandate_archive_cls or MandateArchive
        postgres_replay_cache_cls = postgres_replay_cache_cls or PostgresReplayCache
        sqlite_replay_cache_cls = sqlite_replay_cache_cls or SqliteReplayCache
        replay_cache_cls = replay_cache_cls or ReplayCache

    if mandate_verifier_cls is None:
        from sardis.protocol.verifier import MandateVerifier

        mandate_verifier_cls = MandateVerifier
    if payment_orchestrator_cls is None:
        from sardis.core.orchestrator import PaymentOrchestrator

        payment_orchestrator_cls = PaymentOrchestrator

    if use_postgres:
        archive = mandate_archive_cls(database_url)
        replay_cache = postgres_replay_cache_cls(database_url)
    else:
        archive = mandate_archive_cls(settings.mandate_archive_dsn)
        replay_cache = (
            sqlite_replay_cache_cls(settings.replay_cache_dsn)
            if settings.replay_cache_dsn.startswith("sqlite:///")
            else replay_cache_cls()
        )

    verifier = mandate_verifier_cls(
        settings=settings,
        replay_cache=replay_cache,
        archive=archive,
        identity_registry=identity_registry,
    )

    if group_policy is None:
        try:
            from sardis.core.agent_groups import AgentGroupRepository
            from sardis.core.group_policy import GroupPolicyEvaluator

            group_repo = AgentGroupRepository(
                dsn=database_url if use_postgres else "memory://"
            )
            group_policy = GroupPolicyEvaluator(group_repo=group_repo)
        except Exception as e:
            logger.warning("Group policy evaluator unavailable: %s", e)
            group_policy = None

    moat = build_moat_ports(
        settings,
        database_url=database_url,
        use_postgres=use_postgres,
        kya_service=kya_service,
        sanctions_service=sanctions_service,
        redis_url=redis_url,
    )

    # ── Human-in-the-loop gate (durable signed store + delivery notifier) ──
    # The gate persists signed ApprovalRequests and relays them to a human via
    # the swappable NotificationPort (real Twilio/Photon when keys are set; a
    # sandbox notifier otherwise — so dev and tests run with NO keys). Delivery
    # NEVER decides the outcome; the orchestrator re-checks policy/mandate at
    # re-execution time. The SAME gate instance is returned on the runtime config
    # so the ApprovalRequest API records decisions the orchestrator reads back.
    approval_gate = None
    try:
        from sardis.core.approval_gate import ApprovalGate
        from sardis.core.approval_request_repository import (
            InMemoryApprovalRequestStore,
            PostgresApprovalRequestStore,
        )

        approval_store: Any = (
            PostgresApprovalRequestStore()
            if use_postgres
            else InMemoryApprovalRequestStore()
        )
        notifier = notification_port
        if notifier is None:
            try:
                from server.providers.registry import ProviderRegistry

                notifier = ProviderRegistry.from_settings(settings).notification()
            except Exception as exc:  # noqa: BLE001 - delivery is optional
                logger.warning("approval_gate: no notification port resolved: %s", exc)
        approval_gate = ApprovalGate(store=approval_store, notifier=notifier)
    except Exception as exc:  # noqa: BLE001 - gate is optional in dev
        logger.warning("approval_gate unavailable, approvals fail-closed: %s", exc)

    # ── Programmable Recourse engine (durable signed holds + swappable exec) ──
    # When a payment carries a policy-defined recourse window, the orchestrator
    # opens a durable, signed RecourseHold after settlement. The executor is
    # env-gated (SARDIS_RECOURSE_MODE): NoopRecourseExecutor in dev/tests and
    # whenever live escrow is not configured (no keys needed). The SAME engine
    # instance backs the escrow/dispute API so its holds and the orchestrator's
    # are one surface.
    recourse_engine = None
    try:
        from sardis.core.recourse_engine import RecourseEngine
        from sardis.core.recourse_executor import resolve_default_executor
        from sardis.core.recourse_hold_repository import (
            InMemoryRecourseHoldStore,
            PostgresRecourseHoldStore,
        )

        recourse_store: Any = (
            PostgresRecourseHoldStore()
            if use_postgres
            else InMemoryRecourseHoldStore()
        )
        recourse_engine = RecourseEngine(
            store=recourse_store,
            executor=resolve_default_executor(),
        )
    except Exception as exc:  # noqa: BLE001 - engine is optional in dev
        logger.warning("recourse_engine unavailable, recourse disabled: %s", exc)

    # ── Guard / RiskEngine (in-house behavioral score + external feeds) ──
    # The RiskEngine reuses the in-house AnomalyEngine for the behavioral score
    # and folds in any configured external FraudSignalPort feeds (Stripe Radar /
    # SEON) resolved from the provider registry.  Env-gated through the registry:
    # with no feed key set, the registry returns the SIMULATED sandbox feed, so
    # the engine runs internal-only (dev/tests).  Sardis owns the decision; feeds
    # only contribute signals.  Optional + fail-closed (a None engine simply
    # skips Phase 1.6; a configured engine never fails open on the money path).
    risk_engine = None
    try:
        from sardis.guardrails.risk_engine import RiskEngine

        from server.providers.registry import ProviderRegistry

        # Combine ALL configured real cross-customer feeds (SEON + Radar); the
        # sandbox fallback adds nothing (the internal AnomalyEngine already
        # covers the no-external-feed case), so it is excluded by the accessor.
        feeds = list(ProviderRegistry.from_settings(settings).fraud_signal_feeds())
        risk_engine = RiskEngine(fraud_feeds=feeds)
    except Exception as exc:  # noqa: BLE001 - engine is optional in dev
        logger.warning("risk_engine unavailable, Guard Phase 1.6 disabled: %s", exc)

    orchestrator = payment_orchestrator_cls(
        wallet_manager=wallet_manager,
        compliance=compliance_engine,
        chain_executor=chain_executor,
        ledger=ledger_store,
        group_policy=group_policy,
        kya_service=moat.kya_service,
        sanctions_service=moat.sanctions_service,
        dedup_store=moat.dedup_store,
        spending_mandate_lookup=moat.spending_mandate_lookup,
        settlement_lock=moat.settlement_lock,
        reconciliation_queue=moat.reconciliation_queue,
        approval_gate=approval_gate,
        recourse_engine=recourse_engine,
        risk_engine=risk_engine,
    )

    return PaymentRuntimeConfig(
        archive=archive,
        replay_cache=replay_cache,
        verifier=verifier,
        orchestrator=orchestrator,
        approval_gate=approval_gate,
        recourse_engine=recourse_engine,
    )


def configure_api_support_services(
    settings: Any,
    *,
    database_url: str,
    use_postgres: bool,
    environ: Mapping[str, str] | None = None,
    create_cache_service_fn: Any | None = None,
    api_key_manager_cls: Any | None = None,
    set_api_key_manager_fn: Any | None = None,
) -> APISupportServicesConfig:
    """Create cache and API-key manager services shared by middleware/routes."""
    if create_cache_service_fn is None:
        from sardis.core.cache import create_cache_service

        create_cache_service_fn = create_cache_service

    if api_key_manager_cls is None or set_api_key_manager_fn is None:
        from .middleware import APIKeyManager, set_api_key_manager

        api_key_manager_cls = api_key_manager_cls or APIKeyManager
        set_api_key_manager_fn = set_api_key_manager_fn or set_api_key_manager

    cache_backend = resolve_cache_backend(settings, environ=environ)
    redis_url = cache_backend.redis_url
    cache_service = create_cache_service_fn(redis_url)
    api_key_manager_dsn = database_url if use_postgres else "memory://"
    api_key_manager = api_key_manager_cls(dsn=api_key_manager_dsn)
    set_api_key_manager_fn(api_key_manager)

    return APISupportServicesConfig(
        cache_service=cache_service,
        api_key_manager=api_key_manager,
        redis_url=redis_url,
        api_key_manager_dsn=api_key_manager_dsn,
    )


def configure_facility_gate_services(
    *,
    database_url: str,
    use_postgres: bool,
    repository_cls: Any | None = None,
    adapter_cls: Any | None = None,
) -> FacilityGateServicesConfig:
    """Create Facility Gate persistence and adapter services."""
    if repository_cls is None:
        from .repositories.facility_gate_repository import FacilityGateRepository

        repository_cls = FacilityGateRepository
    if adapter_cls is None:
        from sardis.core.facility_gate import SimulatedFacilityAdapter

        adapter_cls = SimulatedFacilityAdapter

    dsn = database_url if use_postgres else "memory://"
    repository = repository_cls(dsn=dsn)
    adapter = adapter_cls()

    return FacilityGateServicesConfig(
        repository=repository,
        adapter=adapter,
        dsn=dsn,
    )


def configure_provider_runtime(
    settings: Any,
    *,
    environ: Mapping[str, str] | None = None,
    coinbase_provider_cls: Any = _DEFAULT_PROVIDER,
    circle_gateway_client_cls: Any = _DEFAULT_PROVIDER,
) -> ProviderRuntimeConfig:
    """Create optional payment provider clients for route registrars."""
    env = environ if environ is not None else os.environ
    cards_settings = getattr(settings, "cards", None)
    coinbase_settings = getattr(settings, "coinbase", None)
    circle_gateway_settings = getattr(settings, "circle_gateway", None)

    configured_on_chain_provider = (
        (
            getattr(cards_settings, "on_chain_provider", "")
            or env.get("SARDIS_CARDS_ON_CHAIN_PROVIDER", "")
        )
        .strip()
        .lower()
        or None
    )

    coinbase_cdp_provider = None
    coinbase_enabled = configured_on_chain_provider == "coinbase_cdp" or bool(
        getattr(coinbase_settings, "x402_enabled", False)
    )
    if coinbase_enabled:
        cdp_api_key_name = getattr(coinbase_settings, "api_key_name", "") or env.get(
            "COINBASE_CDP_API_KEY_NAME",
            "",
        )
        cdp_api_key_private_key = getattr(
            coinbase_settings,
            "api_key_private_key",
            "",
        ) or env.get("COINBASE_CDP_API_KEY_PRIVATE_KEY", "")
        cdp_network_id = getattr(coinbase_settings, "network_id", "") or env.get(
            "COINBASE_CDP_NETWORK_ID",
            "base-mainnet",
        )
        if cdp_api_key_name and cdp_api_key_private_key:
            try:
                if coinbase_provider_cls is _DEFAULT_PROVIDER:
                    from sardis_coinbase import CoinbaseCDPProvider

                    coinbase_provider_cls = CoinbaseCDPProvider
                coinbase_cdp_provider = coinbase_provider_cls(
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

    circle_gateway_nanopayments_client = None
    if bool(getattr(circle_gateway_settings, "x402_enabled", False)):
        circle_gateway_api_key = getattr(circle_gateway_settings, "api_key", "") or env.get(
            "CIRCLE_GATEWAY_API_KEY",
            "",
        )
        if circle_gateway_api_key:
            try:
                if circle_gateway_client_cls is _DEFAULT_PROVIDER:
                    from .providers.circle_gateway_nanopayments import (
                        CircleGatewayNanopaymentsClient,
                    )

                    circle_gateway_client_cls = CircleGatewayNanopaymentsClient
                circle_gateway_nanopayments_client = circle_gateway_client_cls(
                    api_key=circle_gateway_api_key,
                    base_url=(
                        getattr(circle_gateway_settings, "base_url", "")
                        or env.get("CIRCLE_GATEWAY_BASE_URL", "")
                    ),
                    timeout_seconds=float(
                        getattr(circle_gateway_settings, "timeout_seconds", 10.0)
                    ),
                )
                logger.info("Circle Gateway nanopayments provider initialized")
            except Exception as exc:
                logger.warning("Circle Gateway nanopayments initialization failed: %s", exc)
        else:
            logger.warning(
                "Circle Gateway x402 is enabled but CIRCLE_GATEWAY_API_KEY is missing"
            )

    return ProviderRuntimeConfig(
        on_chain_provider=configured_on_chain_provider,
        coinbase_cdp_provider=coinbase_cdp_provider,
        circle_gateway_nanopayments_client=circle_gateway_nanopayments_client,
    )


def configure_inbound_payment_runtime(
    *,
    webhook_service: Any,
    ledger_store: Any,
    sanctions_service: Any,
    wallet_repository: Any,
    get_default_bus_fn: Any | None = None,
    inbound_payment_service_cls: Any | None = None,
) -> InboundPaymentRuntimeConfig:
    """Create inbound payment event bus wiring and receive service."""
    if get_default_bus_fn is None:
        from sardis.core.event_bus import get_default_bus

        get_default_bus_fn = get_default_bus
    if inbound_payment_service_cls is None:
        from sardis.core.inbound_payment_service import InboundPaymentService

        inbound_payment_service_cls = InboundPaymentService

    event_bus = get_default_bus_fn()
    event_bus.set_webhook_service(webhook_service)
    inbound_payment_service = inbound_payment_service_cls(
        event_bus=event_bus,
        ledger=ledger_store,
        sanctions_service=sanctions_service,
        wallet_repo=wallet_repository,
    )

    return InboundPaymentRuntimeConfig(
        event_bus=event_bus,
        inbound_payment_service=inbound_payment_service,
    )


def configure_ramp_runtime(
    settings: Any,
    *,
    environ: Mapping[str, str] | None = None,
    bridge_offramp_provider_cls: Any = _DEFAULT_PROVIDER,
    mock_offramp_provider_cls: Any = _DEFAULT_PROVIDER,
    offramp_service_cls: Any = _DEFAULT_PROVIDER,
    fiat_ramp_cls: Any = _DEFAULT_PROVIDER,
) -> RampRuntimeConfig:
    """Create fiat ramp and off-ramp services used by wallet routes."""
    env = environ if environ is not None else os.environ
    is_production = bool(getattr(settings, "is_production", False))
    bridge_api_key = env.get("BRIDGE_API_KEY", "")
    bridge_api_secret = env.get("BRIDGE_API_SECRET", "")
    bridge_environment = "production" if is_production else "sandbox"

    if (
        bridge_offramp_provider_cls is _DEFAULT_PROVIDER
        or mock_offramp_provider_cls is _DEFAULT_PROVIDER
        or offramp_service_cls is _DEFAULT_PROVIDER
    ):
        from sardis.cards.offramp import (
            BridgeOfframpProvider,
            MockOfframpProvider,
            OfframpService,
        )

        bridge_offramp_provider_cls = (
            BridgeOfframpProvider
            if bridge_offramp_provider_cls is _DEFAULT_PROVIDER
            else bridge_offramp_provider_cls
        )
        mock_offramp_provider_cls = (
            MockOfframpProvider
            if mock_offramp_provider_cls is _DEFAULT_PROVIDER
            else mock_offramp_provider_cls
        )
        offramp_service_cls = (
            OfframpService if offramp_service_cls is _DEFAULT_PROVIDER else offramp_service_cls
        )

    offramp_service = None
    if bridge_api_key and bridge_api_secret:
        bridge_provider = bridge_offramp_provider_cls(
            api_key=bridge_api_key,
            api_secret=bridge_api_secret,
            environment=bridge_environment,
        )
        offramp_service = offramp_service_cls(provider=bridge_provider)
        logger.info("OfframpService initialized with Bridge provider")
    elif is_production:
        logger.warning(
            "OfframpService NOT initialized: BRIDGE_API_KEY missing in production. "
            "Off-ramp endpoints will return 503 until BRIDGE_API_KEY is set."
        )
    else:
        offramp_service = offramp_service_cls(provider=mock_offramp_provider_cls())
        logger.info(
            "OfframpService initialized with Mock provider (set BRIDGE_API_KEY for real offramp)"
        )

    fiat_ramp = None
    if bridge_api_key:
        try:
            if fiat_ramp_cls is _DEFAULT_PROVIDER:
                from sardis.ramp.ramp import SardisFiatRamp

                fiat_ramp_cls = SardisFiatRamp
            fiat_ramp = fiat_ramp_cls(
                sardis_key=env.get("SARDIS_API_KEY", ""),
                bridge_api_key=bridge_api_key,
                environment=bridge_environment,
            )
            logger.info("SardisFiatRamp initialized for bank withdrawal/merchant payment")
        except Exception as exc:
            logger.warning("Failed to initialize SardisFiatRamp: %s", exc)

    return RampRuntimeConfig(
        offramp_service=offramp_service,
        onramper_api_key=env.get("ONRAMPER_API_KEY", ""),
        onramper_webhook_secret=env.get("ONRAMPER_WEBHOOK_SECRET", ""),
        bridge_webhook_secret=env.get("BRIDGE_WEBHOOK_SECRET", ""),
        fiat_ramp=fiat_ramp,
    )


def configure_treasury_runtime(
    settings: Any,
    *,
    database_url: str,
    use_postgres: bool,
    environ: Mapping[str, str] | None = None,
    treasury_repository_cls: Any = _DEFAULT_PROVIDER,
    canonical_ledger_repository_cls: Any = _DEFAULT_PROVIDER,
    lithic_treasury_client_cls: Any = _DEFAULT_PROVIDER,
) -> TreasuryRuntimeConfig:
    """Create treasury repositories and the optional Lithic treasury client."""
    env = environ if environ is not None else os.environ
    dsn = database_url if use_postgres else None

    if treasury_repository_cls is _DEFAULT_PROVIDER:
        from .repositories.treasury_repository import TreasuryRepository

        treasury_repository_cls = TreasuryRepository
    if canonical_ledger_repository_cls is _DEFAULT_PROVIDER:
        from .repositories.canonical_ledger_repository import CanonicalLedgerRepository

        canonical_ledger_repository_cls = CanonicalLedgerRepository

    treasury_repository = treasury_repository_cls(dsn=dsn)
    canonical_ledger_repository = canonical_ledger_repository_cls(dsn=dsn)
    lithic_webhook_secret = env.get("LITHIC_WEBHOOK_SECRET", "")
    lithic_treasury_client = None

    lithic_api_key = env.get("LITHIC_API_KEY", "")
    if lithic_api_key:
        if lithic_treasury_client_cls is _DEFAULT_PROVIDER:
            from .providers.lithic_treasury import LithicTreasuryClient

            lithic_treasury_client_cls = LithicTreasuryClient
        try:
            lithic_treasury_client = lithic_treasury_client_cls(
                api_key=lithic_api_key,
                environment=(
                    "production"
                    if getattr(settings, "is_production", False)
                    else "sandbox"
                ),
                webhook_secret=env.get("LITHIC_WEBHOOK_SECRET"),
            )
            logger.info("Treasury initialized with Lithic client")
        except Exception as exc:
            logger.warning("Failed to initialize Lithic treasury client: %s", exc)
    else:
        logger.warning(
            "Treasury enabled without Lithic API key; endpoints will return 503 for provider actions"
        )

    return TreasuryRuntimeConfig(
        treasury_repository=treasury_repository,
        canonical_ledger_repository=canonical_ledger_repository,
        lithic_treasury_client=lithic_treasury_client,
        lithic_webhook_secret=lithic_webhook_secret,
    )


def configure_cpn_runtime(
    settings: Any,
    *,
    environ: Mapping[str, str] | None = None,
    cpn_client_cls: Any = _DEFAULT_PROVIDER,
) -> CPNRuntimeConfig:
    """Create the optional Circle CPN client used by wallet CPN routes."""
    env = environ if environ is not None else os.environ
    circle_cpn_settings = settings.circle_cpn
    api_key = (
        getattr(circle_cpn_settings, "api_key", "")
        or env.get("SARDIS_CIRCLE_CPN__API_KEY", "")
        or env.get("CIRCLE_CPN_API_KEY", "")
    )
    enabled = bool(
        getattr(circle_cpn_settings, "enabled", False)
        or env.get("SARDIS_CIRCLE_CPN__ENABLED", "").strip().lower()
        in {"1", "true", "yes", "on"}
        or env.get("CIRCLE_CPN_ENABLED", "").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    webhook_secret = (
        getattr(circle_cpn_settings, "webhook_secret", "")
        or env.get("SARDIS_CIRCLE_CPN__WEBHOOK_SECRET", "")
        or env.get("CIRCLE_CPN_WEBHOOK_SECRET", "")
    )

    cpn_client = None
    if enabled and api_key:
        if cpn_client_cls is _DEFAULT_PROVIDER:
            from .providers.circle_cpn import CircleCPNClient

            cpn_client_cls = CircleCPNClient
        try:
            cpn_client = cpn_client_cls(
                api_key=api_key,
                base_url=getattr(circle_cpn_settings, "base_url", "")
                or "https://api.circle.com",
                payout_path=getattr(circle_cpn_settings, "payout_path", "")
                or "/v1/cpn/payments",
                collection_path=getattr(circle_cpn_settings, "collection_path", "")
                or "/v1/cpn/collections",
                status_path=getattr(circle_cpn_settings, "status_path", "")
                or "/v1/cpn/payments/{payment_id}",
                auth_style=getattr(circle_cpn_settings, "auth_style", "")
                or "bearer",
                timeout_seconds=float(getattr(circle_cpn_settings, "timeout_seconds", 10.0)),
                program_id=(
                    getattr(circle_cpn_settings, "program_id", "")
                    or env.get("SARDIS_CIRCLE_CPN__PROGRAM_ID", "")
                    or env.get("CIRCLE_CPN_PROGRAM_ID", "")
                ),
            )
        except Exception as exc:
            logger.warning("Circle CPN client init failed for router: %s", exc)
            cpn_client = None

    return CPNRuntimeConfig(cpn_client=cpn_client, webhook_secret=webhook_secret)


def expose_runtime_state(
    app: Any,
    *,
    settings: Any,
    database_url: str,
    use_postgres: bool,
    turnkey_client: Any | None,
    policy_store: Any,
    chain_executor: Any,
    wallet_repository: Any,
    compliance_engine: Any,
    facility_gate_repository: Any,
) -> None:
    """Expose bootstrapped runtime services required by route dependencies."""
    app.state.settings = settings
    app.state.database_url = database_url
    app.state.use_postgres = use_postgres
    app.state.turnkey_client = turnkey_client
    app.state.policy_store = policy_store
    app.state.chain_executor = chain_executor
    app.state.wallet_repo = wallet_repository
    app.state.compliance_engine = compliance_engine
    app.state.facility_gate_repo = facility_gate_repository


def expose_support_services_state(
    app: Any,
    *,
    cache_service: Any,
    api_key_manager: Any,
) -> None:
    """Expose late-bound API support services required by middleware/routes."""
    app.state.cache_service = cache_service
    app.state.api_key_manager = api_key_manager


def expose_provider_runtime_state(app: Any, *, provider_runtime: ProviderRuntimeConfig) -> None:
    """Expose optional payment provider clients required by wallet routes."""
    app.state.coinbase_cdp_provider = provider_runtime.coinbase_cdp_provider
    app.state.on_chain_provider = provider_runtime.on_chain_provider
    app.state.circle_gateway_nanopayments_client = (
        provider_runtime.circle_gateway_nanopayments_client
    )


def expose_inbound_payment_state(
    app: Any,
    *,
    inbound_runtime: InboundPaymentRuntimeConfig,
) -> None:
    """Expose inbound payment runtime services required by wallet routes/lifespan."""
    app.state.inbound_payment_service = inbound_runtime.inbound_payment_service
    app.state.event_bus = inbound_runtime.event_bus


def expose_treasury_runtime_state(
    app: Any,
    *,
    treasury_runtime: TreasuryRuntimeConfig,
) -> None:
    """Expose treasury runtime services required by wallet and ledger routes."""
    app.state.treasury_repo = treasury_runtime.treasury_repository
    app.state.canonical_ledger_repo = treasury_runtime.canonical_ledger_repository
    app.state.lithic_treasury_client = treasury_runtime.lithic_treasury_client


class DependencyContainer:
    """
    Central dependency injection container.

    Provides lazy initialization of all service dependencies with proper
    error handling for missing optional dependencies.

    Usage:
        container = DependencyContainer(settings)

        # Access required dependencies (raises if not available)
        ledger = container.ledger_store

        # Check optional dependencies
        if container.has_stripe:
            stripe = container.stripe_connector
    """

    def __init__(
        self,
        settings: SardisSettings | None = None,
        config: DependencyConfig | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._config = config or DependencyConfig.from_environment()
        self._cache: dict[str, Any] = {}
        self._initialized = False

    @property
    def settings(self) -> SardisSettings:
        """Get application settings."""
        return self._settings

    @property
    def config(self) -> DependencyConfig:
        """Get dependency configuration."""
        return self._config

    @property
    def database_url(self) -> str:
        """Get effective database URL."""
        return self._config.database_url or self._settings.ledger_dsn

    @property
    def use_postgres(self) -> bool:
        """Check if using PostgreSQL."""
        return self._config.use_postgres

    # =========================================================================
    # Core Services (always available)
    # =========================================================================

    @cached_property
    def identity_registry(self) -> Any:
        """Get identity registry (DB-backed in production)."""
        from sardis.core.identity import IdentityRegistry
        dsn = self.database_url if self.use_postgres else None
        return IdentityRegistry(dsn=dsn)

    @cached_property
    def wallet_manager(self) -> Any:
        """Get wallet manager."""
        from sardis.wallet.manager import WalletManager
        return WalletManager(settings=self._settings)

    @cached_property
    def _chain_executor(self) -> Any:
        """Internal — only used by PaymentOrchestrator."""
        from sardis.chain.executor import ChainExecutor
        return ChainExecutor(settings=self._settings)

    @property
    def chain_executor(self) -> Any:
        """Deprecated: use payment_orchestrator instead of accessing chain_executor directly."""
        warnings.warn(
            "DependencyContainer.chain_executor is deprecated. "
            "Use payment_orchestrator for all payment execution.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._chain_executor

    @cached_property
    def ledger_store(self) -> Any:
        """Get ledger store."""
        from sardis.ledger.records import LedgerStore
        dsn = self.database_url if self.use_postgres else self._settings.ledger_dsn
        return LedgerStore(dsn=dsn)

    @cached_property
    def compliance_engine(self) -> Any:
        """Get compliance engine."""
        from sardis.compliance.checks import ComplianceEngine
        return ComplianceEngine(settings=self._settings)

    @cached_property
    def mandate_verifier(self) -> Any:
        """Get mandate verifier."""
        from sardis.protocol.verifier import MandateVerifier
        return MandateVerifier(
            settings=self._settings,
            replay_cache=self.replay_cache,
            archive=self.mandate_archive,
            identity_registry=self.identity_registry,
        )

    @cached_property
    def group_policy(self) -> Any | None:
        """Get group policy evaluator (optional, returns None if deps missing)."""
        try:
            from sardis.core.agent_groups import AgentGroupRepository
            from sardis.core.group_policy import GroupPolicyEvaluator
            dsn = self.database_url if self.use_postgres else "memory://"
            group_repo = AgentGroupRepository(dsn=dsn)
            return GroupPolicyEvaluator(group_repo=group_repo)
        except Exception as e:
            logger.warning("Group policy evaluator unavailable: %s", e)
            return None

    @cached_property
    def sanctions_service(self) -> Any:
        """Get sanctions screening service (fail-fast in production)."""
        return configure_sanctions_service(self._settings).service

    @cached_property
    def kya_service(self) -> Any:
        """Get KYA (know-your-agent) verification service."""
        from sardis.compliance import create_kya_service
        liveness_timeout = int(os.getenv("SARDIS_KYA_LIVENESS_TIMEOUT_SECONDS", "300"))
        dsn = self.database_url if self.use_postgres else "memory://"
        return create_kya_service(liveness_timeout=liveness_timeout, dsn=dsn)

    @cached_property
    def spending_mandate_lookup(self) -> Any:
        """Get DB-backed spending-mandate lookup (revocation/scope enforcement)."""
        from sardis.core.spending_mandate_lookup import SpendingMandateLookup
        dsn = self.database_url if self.use_postgres else "memory://"
        return SpendingMandateLookup(dsn=dsn)

    @cached_property
    def provider_registry(self) -> Any:
        """Unified provider layer: every external money/identity service behind
        a typed capability port.

        Single env-gated construction point.  Real adapters activate only when
        their keys are set; otherwise a SANDBOX impl backs the capability so dev
        and tests run green without live keys (fail-closed in production for
        required capabilities).  Execution routes resolve their capability port
        from this one instance rather than constructing vendor clients ad-hoc,
        so the authority core is never bypassed — adapters only execute what the
        orchestrator already authorized.
        """
        from server.providers.registry import ProviderRegistry

        return ProviderRegistry.from_settings(self._settings)

    @cached_property
    def approval_gate(self) -> Any:
        """Human-in-the-loop ApprovalGate (durable signed store + delivery notifier).

        The gate owns the durable, signed :class:`ApprovalRequest` store and the
        swappable delivery notifier (the provider-layer NotificationPort: real
        Twilio/Photon when keys are set, sandbox otherwise — so dev and tests run
        with NO keys). Delivery NEVER decides the outcome; the orchestrator
        re-checks policy/mandate at re-execution time.
        """
        from sardis.core.approval_gate import ApprovalGate
        from sardis.core.approval_request_repository import (
            InMemoryApprovalRequestStore,
            PostgresApprovalRequestStore,
        )

        store: Any = (
            PostgresApprovalRequestStore()
            if self.use_postgres
            else InMemoryApprovalRequestStore()
        )

        # Resolve the delivery notifier from the unified provider layer. The
        # registry returns a real adapter only when keys are set; otherwise a
        # sandbox notifier — so the loop runs end-to-end with no live keys.
        notifier: Any = None
        try:
            notifier = self.provider_registry.notification()
        except Exception as exc:  # noqa: BLE001 - delivery is optional/best-effort
            logger.warning("approval_gate: no notification port resolved: %s", exc)

        return ApprovalGate(store=store, notifier=notifier)

    @cached_property
    def recourse_engine(self) -> Any:
        """Programmable-recourse engine (durable signed RecourseHold store +
        swappable executor).

        Owns the recourse *decision/policy/evidence* (the moat). The executor is
        env-gated (``SARDIS_RECOURSE_MODE``): NoopRecourseExecutor in dev/tests
        and whenever live escrow is not configured (no keys needed); the vendored
        Circle RefundProtocol wrapper only when ``=live`` with a chain client.
        The escrow/dispute API resolves this SAME engine so its holds and the
        orchestrator-opened holds are one surface.
        """
        from sardis.core.recourse_engine import RecourseEngine
        from sardis.core.recourse_executor import resolve_default_executor
        from sardis.core.recourse_hold_repository import (
            InMemoryRecourseHoldStore,
            PostgresRecourseHoldStore,
        )

        store: Any = (
            PostgresRecourseHoldStore()
            if self.use_postgres
            else InMemoryRecourseHoldStore()
        )
        return RecourseEngine(store=store, executor=resolve_default_executor())

    @cached_property
    def risk_engine(self) -> Any:
        """Guard / RiskEngine: in-house behavioral score + external fraud feeds.

        Sardis owns the risk decision (the moat); external FraudSignalPort feeds
        (Stripe Radar / SEON) only contribute signals.  Env-gated via the
        registry: only a real (non-sandbox) feed is wired, otherwise the engine
        runs internal-only off the in-house AnomalyEngine — so dev/tests run with
        no keys.
        """
        from sardis.guardrails.risk_engine import RiskEngine

        try:
            # ALL configured real feeds (SEON + Radar), not just one — the engine
            # combines every cross-customer signal with its behavioral score.
            feeds = list(self.provider_registry.fraud_signal_feeds())
        except Exception as exc:  # noqa: BLE001 - feed is optional
            logger.warning("risk_engine: no external fraud feed resolved: %s", exc)
            feeds = []
        return RiskEngine(fraud_feeds=feeds)

    @cached_property
    def payment_orchestrator(self) -> Any:
        """Get payment orchestrator with execution-authority ("moat") ports wired."""
        from sardis.core.orchestrator import PaymentOrchestrator

        moat = build_moat_ports(
            self._settings,
            database_url=self.database_url,
            use_postgres=self.use_postgres,
            kya_service=self.kya_service,
            sanctions_service=self.sanctions_service,
            redis_url=self._config.redis_url,
        )

        return PaymentOrchestrator(
            wallet_manager=self.wallet_manager,
            compliance=self.compliance_engine,
            chain_executor=self._chain_executor,
            ledger=self.ledger_store,
            group_policy=self.group_policy,
            kya_service=moat.kya_service,
            sanctions_service=moat.sanctions_service,
            dedup_store=moat.dedup_store,
            spending_mandate_lookup=moat.spending_mandate_lookup,
            settlement_lock=moat.settlement_lock,
            reconciliation_queue=moat.reconciliation_queue,
            approval_gate=self.approval_gate,
            recourse_engine=self.recourse_engine,
            risk_engine=self.risk_engine,
        )

    # =========================================================================
    # Storage (adapts to available backend)
    # =========================================================================

    @cached_property
    def replay_cache(self) -> Any:
        """Get replay cache (PostgreSQL or SQLite/memory)."""
        from sardis.protocol.storage import PostgresReplayCache, ReplayCache, SqliteReplayCache

        if self.use_postgres:
            return PostgresReplayCache(self.database_url)
        elif self._settings.replay_cache_dsn.startswith("sqlite:///"):
            return SqliteReplayCache(self._settings.replay_cache_dsn)
        else:
            return ReplayCache()

    @cached_property
    def mandate_archive(self) -> Any:
        """Get mandate archive."""
        from sardis.protocol.storage import MandateArchive
        dsn = self.database_url if self.use_postgres else self._settings.mandate_archive_dsn
        return MandateArchive(dsn)

    @cached_property
    def holds_repository(self) -> Any:
        """Get holds repository."""
        from sardis.core.holds import HoldsRepository
        dsn = self.database_url if self.use_postgres else "memory://"
        return HoldsRepository(dsn=dsn)

    @cached_property
    def webhook_repository(self) -> Any:
        """Get webhook repository."""
        from sardis.core.webhooks import WebhookRepository
        dsn = self.database_url if self.use_postgres else "memory://"
        return WebhookRepository(dsn=dsn)

    @cached_property
    def webhook_service(self) -> Any:
        """Get webhook service."""
        from sardis.core.webhooks import WebhookService
        return WebhookService(repository=self.webhook_repository)

    @cached_property
    def wallet_repository(self) -> Any:
        """Get wallet repository."""
        from sardis.core.wallet_repository import WalletRepository
        dsn = self.database_url if self.use_postgres else "memory://"
        return WalletRepository(dsn=dsn)

    @cached_property
    def agent_repository(self) -> Any:
        """Get agent repository."""
        from sardis.core.agents import AgentRepository
        dsn = self.database_url if self.use_postgres else "memory://"
        return AgentRepository(dsn=dsn)

    @cached_property
    def marketplace_repository(self) -> Any:
        """Get marketplace repository."""
        from sardis.core.marketplace import MarketplaceRepository
        dsn = self.database_url if self.use_postgres else "memory://"
        return MarketplaceRepository(dsn=dsn)

    @cached_property
    def spending_policy_store(self) -> Any:
        """Get spending policy state store (DB-backed atomic enforcement)."""
        from sardis.core.spending_policy_store import SpendingPolicyStore
        if self.use_postgres:
            return SpendingPolicyStore(dsn=self.database_url)
        return None  # In-memory fallback handled by SpendingPolicy itself

    @cached_property
    def cache_service(self) -> Any:
        """Get cache service (Redis or in-memory)."""
        from sardis.core.cache import create_cache_service
        return create_cache_service(self._config.redis_url)

    @cached_property
    def api_key_manager(self) -> Any:
        """Get API key manager."""
        from .middleware import APIKeyManager
        dsn = self.database_url if self.use_postgres else "memory://"
        return APIKeyManager(dsn=dsn)

    @cached_property
    def mpp_client(self) -> Any | None:
        """Get MPP client for Machine Payments Protocol (optional)."""
        try:
            from sardis_mpp.client import SardisMPPClient
            return SardisMPPClient(methods=[], policy_checker=None)
        except ImportError:
            logger.info("sardis-mpp package not installed, MPP client unavailable")
            return None

    # =========================================================================
    # Optional External Services
    # =========================================================================

    @property
    def has_stripe(self) -> bool:
        """Check if Stripe is configured."""
        return self._config.stripe_enabled

    @property
    def has_turnkey(self) -> bool:
        """Check if Turnkey MPC is configured."""
        return self._config.turnkey_enabled

    @property
    def has_persona(self) -> bool:
        """Check if Persona KYC is configured."""
        return self._config.persona_enabled

    @property
    def has_elliptic(self) -> bool:
        """Check if Elliptic AML is configured."""
        return self._config.elliptic_enabled

    @property
    def has_lithic(self) -> bool:
        """Check if Lithic cards is configured."""
        return self._config.lithic_enabled

    @property
    def has_didit(self) -> bool:
        """Check if Didit KYC is configured."""
        return self._config.didit_enabled

    @cached_property
    def didit_kyc_provider(self) -> Any:
        """Get Didit KYC provider (raises if not configured)."""
        if not self.has_didit:
            raise SardisDependencyNotConfiguredError(
                "didit",
                "Didit KYC is not configured. Set DIDIT_API_KEY environment variable.",
            )
        from sardis.compliance.providers.didit import DiditKYCProvider

        return DiditKYCProvider(
            api_key=os.getenv("DIDIT_API_KEY", ""),
            webhook_secret=os.getenv("DIDIT_WEBHOOK_SECRET", ""),
            workflow_id=os.getenv("DIDIT_WORKFLOW_ID"),
        )

    @cached_property
    def stripe_connector(self) -> Any:
        """Get Stripe connector (raises if not configured)."""
        if not self.has_stripe:
            raise SardisDependencyNotConfiguredError(
                "stripe",
                "Stripe is not configured. Set STRIPE_SECRET_KEY environment variable.",
            )
        from sardis.checkout.connectors.stripe import StripeConnector
        return StripeConnector()

    @cached_property
    def checkout_orchestrator(self) -> Any:
        """Get checkout orchestrator."""
        from sardis.checkout.orchestrator import CheckoutOrchestrator
        orchestrator = CheckoutOrchestrator()

        # Register available connectors
        if self.has_stripe:
            try:
                orchestrator.register_connector("stripe", self.stripe_connector)
            except (SardisDependencyNotConfiguredError, RuntimeError, ValueError, TypeError) as e:
                logger.warning(f"Failed to register Stripe connector: {e}")

        return orchestrator

    # =========================================================================
    # Dependency Getters with Error Handling
    # =========================================================================

    def get_required(self, name: str) -> Any:
        """
        Get a required dependency by name.

        Raises SardisDependencyNotConfiguredError if not available.
        """
        getter = getattr(self, name, None)
        if getter is None:
            raise SardisDependencyNotConfiguredError(
                name,
                f"Unknown dependency: {name}",
            )

        try:
            return getter
        except SardisDependencyNotConfiguredError:
            raise
        except (ImportError, ModuleNotFoundError, RuntimeError, ValueError, TypeError, OSError) as e:
            raise SardisDependencyNotConfiguredError(
                name,
                f"Failed to initialize {name}: {e}",
            ) from e

    def get_optional(self, name: str, default: T | None = None) -> T | None:
        """
        Get an optional dependency by name.

        Returns default if not available.
        """
        try:
            return self.get_required(name)
        except SardisDependencyNotConfiguredError:
            return default


# Global container instance (initialized in create_app)
_container: DependencyContainer | None = None

# Fallback provider registry for when the container is not initialized (tests).
_fallback_provider_registry: Any | None = None


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    if _container is None:
        raise RuntimeError(
            "Dependency container not initialized. "
            "Call init_container() in application startup."
        )
    return _container


def init_container(
    settings: SardisSettings | None = None,
    config: DependencyConfig | None = None,
) -> DependencyContainer:
    """Initialize the global dependency container."""
    global _container
    _container = DependencyContainer(settings=settings, config=config)
    return _container


def reset_container() -> None:
    """Reset the global container (for testing)."""
    global _container, _fallback_provider_registry
    _container = None
    _fallback_provider_registry = None


# ---------------------------------------------------------------------------
# Provider-layer FastAPI dependencies
#
# Execution routes resolve their capability port through these so every
# external money/identity call goes through the one env-gated registry — and
# only AFTER the orchestrator has authorized the movement.  The ports execute;
# they never authorize, initiate, or settle on their own.
# ---------------------------------------------------------------------------


def get_provider_registry() -> Any:
    """Return the singleton :class:`ProviderRegistry`.

    Prefers the global container's instance (the production path).  When the
    container has not been initialized (e.g. an app constructed via
    ``create_app()`` without running the lifespan startup, as in tests), build
    and cache a registry from loaded settings so the provider-layer routes stay
    reachable without coupling to container init order.
    """
    global _fallback_provider_registry
    if _container is not None:
        return _container.provider_registry
    if _fallback_provider_registry is None:
        from server.providers.registry import ProviderRegistry

        _fallback_provider_registry = ProviderRegistry.from_settings(load_settings())
    return _fallback_provider_registry


def get_custody_port() -> Any:
    """CustodyPort (Turnkey MPC / sandbox)."""
    return get_provider_registry().custody()


def get_onramp_port() -> Any:
    """OnrampPort (Conduit / Turnkey / Onramper / Transak / Daimo / sandbox)."""
    return get_provider_registry().onramp()


def get_offramp_port() -> Any:
    """OfframpPort (Circle CPN / Increase / Onramper / Transak / Coinbase / sandbox)."""
    return get_provider_registry().offramp()


def get_fiat_account_port() -> Any:
    """FiatAccountPort (Lithic / Dakota / Increase / sandbox)."""
    return get_provider_registry().fiat_account()


def get_swap_port() -> Any:
    """SwapPort (LI.FI / 0x / Jupiter / sandbox)."""
    return get_provider_registry().swap()


def get_bridge_port() -> Any:
    """BridgePort (Squid / CCTP v2 / sandbox)."""
    return get_provider_registry().bridge()


def get_card_port() -> Any:
    """CardPort (Crossmint / Lithic / Stripe Issuing / sandbox)."""
    return get_provider_registry().card()


def get_kyc_port() -> Any:
    """KycPort (Didit / sandbox)."""
    return get_provider_registry().kyc()


def get_kyt_port() -> Any:
    """KytPort (OpenSanctions / Didit / sandbox)."""
    return get_provider_registry().kyt()
