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
from typing import Any, TypeVar

from sardis_v2_core import SardisSettings, load_settings
from sardis_v2_core.exceptions import SardisDependencyNotConfiguredError

logger = logging.getLogger(__name__)

T = TypeVar("T")


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
        from sardis_v2_core.identity import IdentityRegistry
        dsn = self.database_url if self.use_postgres else None
        return IdentityRegistry(dsn=dsn)

    @cached_property
    def wallet_manager(self) -> Any:
        """Get wallet manager."""
        from sardis_wallet.manager import WalletManager
        return WalletManager(settings=self._settings)

    @cached_property
    def _chain_executor(self) -> Any:
        """Internal — only used by PaymentOrchestrator."""
        from sardis_chain.executor import ChainExecutor
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
        from sardis_ledger.records import LedgerStore
        dsn = self.database_url if self.use_postgres else self._settings.ledger_dsn
        return LedgerStore(dsn=dsn)

    @cached_property
    def compliance_engine(self) -> Any:
        """Get compliance engine."""
        from sardis_compliance.checks import ComplianceEngine
        return ComplianceEngine(settings=self._settings)

    @cached_property
    def mandate_verifier(self) -> Any:
        """Get mandate verifier."""
        from sardis_protocol.verifier import MandateVerifier
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
            from sardis_v2_core.agent_groups import AgentGroupRepository
            from sardis_v2_core.group_policy import GroupPolicyEvaluator
            dsn = self.database_url if self.use_postgres else "memory://"
            group_repo = AgentGroupRepository(dsn=dsn)
            return GroupPolicyEvaluator(group_repo=group_repo)
        except Exception as e:
            logger.warning("Group policy evaluator unavailable: %s", e)
            return None

    @cached_property
    def payment_orchestrator(self) -> Any:
        """Get payment orchestrator."""
        from sardis_v2_core.orchestrator import PaymentOrchestrator
        return PaymentOrchestrator(
            wallet_manager=self.wallet_manager,
            compliance=self.compliance_engine,
            chain_executor=self._chain_executor,
            ledger=self.ledger_store,
            group_policy=self.group_policy,
        )

    # =========================================================================
    # Storage (adapts to available backend)
    # =========================================================================

    @cached_property
    def replay_cache(self) -> Any:
        """Get replay cache (PostgreSQL or SQLite/memory)."""
        from sardis_protocol.storage import PostgresReplayCache, ReplayCache, SqliteReplayCache

        if self.use_postgres:
            return PostgresReplayCache(self.database_url)
        elif self._settings.replay_cache_dsn.startswith("sqlite:///"):
            return SqliteReplayCache(self._settings.replay_cache_dsn)
        else:
            return ReplayCache()

    @cached_property
    def mandate_archive(self) -> Any:
        """Get mandate archive."""
        from sardis_protocol.storage import MandateArchive
        dsn = self.database_url if self.use_postgres else self._settings.mandate_archive_dsn
        return MandateArchive(dsn)

    @cached_property
    def holds_repository(self) -> Any:
        """Get holds repository."""
        from sardis_v2_core.holds import HoldsRepository
        dsn = self.database_url if self.use_postgres else "memory://"
        return HoldsRepository(dsn=dsn)

    @cached_property
    def webhook_repository(self) -> Any:
        """Get webhook repository."""
        from sardis_v2_core.webhooks import WebhookRepository
        dsn = self.database_url if self.use_postgres else "memory://"
        return WebhookRepository(dsn=dsn)

    @cached_property
    def webhook_service(self) -> Any:
        """Get webhook service."""
        from sardis_v2_core.webhooks import WebhookService
        return WebhookService(repository=self.webhook_repository)

    @cached_property
    def wallet_repository(self) -> Any:
        """Get wallet repository."""
        from sardis_v2_core.wallet_repository import WalletRepository
        dsn = self.database_url if self.use_postgres else "memory://"
        return WalletRepository(dsn=dsn)

    @cached_property
    def agent_repository(self) -> Any:
        """Get agent repository."""
        from sardis_v2_core.agents import AgentRepository
        dsn = self.database_url if self.use_postgres else "memory://"
        return AgentRepository(dsn=dsn)

    @cached_property
    def marketplace_repository(self) -> Any:
        """Get marketplace repository."""
        from sardis_v2_core.marketplace import MarketplaceRepository
        dsn = self.database_url if self.use_postgres else "memory://"
        return MarketplaceRepository(dsn=dsn)

    @cached_property
    def spending_policy_store(self) -> Any:
        """Get spending policy state store (DB-backed atomic enforcement)."""
        from sardis_v2_core.spending_policy_store import SpendingPolicyStore
        if self.use_postgres:
            return SpendingPolicyStore(dsn=self.database_url)
        return None  # In-memory fallback handled by SpendingPolicy itself

    @cached_property
    def cache_service(self) -> Any:
        """Get cache service (Redis or in-memory)."""
        from sardis_v2_core.cache import create_cache_service
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
        from sardis_compliance.providers.didit import DiditKYCProvider

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
        from sardis_checkout.connectors.stripe import StripeConnector
        return StripeConnector()

    @cached_property
    def checkout_orchestrator(self) -> Any:
        """Get checkout orchestrator."""
        from sardis_checkout.orchestrator import CheckoutOrchestrator
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
    global _container
    _container = None
