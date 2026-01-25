"""
Configuration validation for Sardis Core.

This module provides comprehensive validation for service configuration,
ensuring all required settings are present and valid before startup.

Usage:
    from sardis_v2_core.config_validation import (
        SardisConfig,
        validate_config,
        load_config_from_env,
    )

    # Load and validate from environment
    config = load_config_from_env()

    # Or validate an existing config
    config = SardisConfig(
        database_url="postgresql://...",
        turnkey_api_key="tk_live_...",
    )
    validate_config(config)
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Sequence
from urllib.parse import urlparse

from .constants import (
    APIConfig,
    CacheTTL,
    CircuitBreakerDefaults,
    PaymentLimits,
    PoolLimits,
    RetryConfig,
    SecurityConfig,
    Timeouts,
)
from .exceptions import SardisConfigurationError

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Model
# =============================================================================

class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class DatabaseConfig:
    """Database configuration.

    Attributes:
        url: PostgreSQL connection URL
        pool_min_size: Minimum connection pool size
        pool_max_size: Maximum connection pool size
        command_timeout: Timeout for database commands in seconds
        ssl_mode: SSL mode for connections
    """

    url: str = ""
    pool_min_size: int = PoolLimits.DB_POOL_MIN_SIZE
    pool_max_size: int = PoolLimits.DB_POOL_MAX_SIZE
    command_timeout: float = Timeouts.DB_COMMAND
    ssl_mode: str = "prefer"

    def validate(self) -> list[str]:
        """Validate database configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.url:
            errors.append("DATABASE_URL is required")
        elif not self.url.startswith(("postgresql://", "postgres://")):
            errors.append("DATABASE_URL must be a PostgreSQL connection string")

        if self.pool_min_size < 1:
            errors.append("Database pool_min_size must be at least 1")

        if self.pool_max_size < self.pool_min_size:
            errors.append("Database pool_max_size must be >= pool_min_size")

        if self.command_timeout <= 0:
            errors.append("Database command_timeout must be positive")

        return errors


@dataclass
class CacheConfig:
    """Cache configuration.

    Attributes:
        redis_url: Redis/Upstash connection URL (optional)
        default_ttl: Default cache TTL in seconds
        balance_ttl: Balance cache TTL
        wallet_ttl: Wallet cache TTL
    """

    redis_url: Optional[str] = None
    default_ttl: int = CacheTTL.WALLET
    balance_ttl: int = CacheTTL.BALANCE
    wallet_ttl: int = CacheTTL.WALLET

    def validate(self) -> list[str]:
        """Validate cache configuration."""
        errors = []

        if self.redis_url:
            if not self.redis_url.startswith(("redis://", "rediss://")):
                errors.append("REDIS_URL must be a valid Redis URL")

        if self.default_ttl <= 0:
            errors.append("Cache default_ttl must be positive")

        return errors


@dataclass
class TurnkeyConfig:
    """Turnkey MPC configuration.

    Attributes:
        api_key: Turnkey API key
        organization_id: Turnkey organization ID
        base_url: Turnkey API base URL
        timeout: API call timeout in seconds
    """

    api_key: str = ""
    organization_id: str = ""
    base_url: str = "https://api.turnkey.com"
    timeout: float = Timeouts.MPC_SIGNING

    def validate(self) -> list[str]:
        """Validate Turnkey configuration."""
        errors = []

        if not self.api_key:
            errors.append("TURNKEY_API_KEY is required")
        elif not self.api_key.startswith("tk_"):
            errors.append("TURNKEY_API_KEY must start with 'tk_'")

        if not self.organization_id:
            errors.append("TURNKEY_ORGANIZATION_ID is required")

        if not self.base_url.startswith("https://"):
            errors.append("TURNKEY_BASE_URL must use HTTPS")

        return errors


@dataclass
class PersonaConfig:
    """Persona KYC configuration.

    Attributes:
        api_key: Persona API key
        template_id: Persona inquiry template ID
        base_url: Persona API base URL
        webhook_secret: Webhook signature secret
    """

    api_key: str = ""
    template_id: str = ""
    base_url: str = "https://withpersona.com/api/v1"
    webhook_secret: str = ""

    def validate(self) -> list[str]:
        """Validate Persona configuration."""
        errors = []

        if not self.api_key:
            errors.append("PERSONA_API_KEY is required for KYC")

        if not self.template_id:
            errors.append("PERSONA_TEMPLATE_ID is required for KYC")

        return errors


@dataclass
class EllipticConfig:
    """Elliptic sanctions screening configuration.

    Attributes:
        api_key: Elliptic API key
        base_url: Elliptic API base URL
        risk_threshold: Risk score threshold for blocking
    """

    api_key: str = ""
    base_url: str = "https://aml-api.elliptic.co"
    risk_threshold: float = 0.7

    def validate(self) -> list[str]:
        """Validate Elliptic configuration."""
        errors = []

        if not self.api_key:
            errors.append("ELLIPTIC_API_KEY is required for sanctions screening")

        if not 0 <= self.risk_threshold <= 1:
            errors.append("ELLIPTIC_RISK_THRESHOLD must be between 0 and 1")

        return errors


@dataclass
class LithicConfig:
    """Lithic card provider configuration.

    Attributes:
        api_key: Lithic API key
        base_url: Lithic API base URL
        webhook_secret: Webhook signature secret
    """

    api_key: str = ""
    base_url: str = "https://api.lithic.com"
    webhook_secret: str = ""

    def validate(self) -> list[str]:
        """Validate Lithic configuration."""
        errors = []

        if not self.api_key:
            errors.append("LITHIC_API_KEY is required for virtual cards")

        return errors


@dataclass
class ChainConfig:
    """Blockchain configuration.

    Attributes:
        default_chain: Default chain for operations
        rpc_urls: Mapping of chain names to RPC URLs
        confirmation_blocks: Blocks to wait for confirmation
    """

    default_chain: str = "base"
    rpc_urls: dict[str, str] = field(default_factory=dict)
    confirmation_blocks: dict[str, int] = field(default_factory=lambda: {
        "ethereum": 12,
        "polygon": 128,
        "base": 1,
        "arbitrum": 1,
        "optimism": 1,
        "solana": 32,
    })

    def validate(self) -> list[str]:
        """Validate chain configuration."""
        errors = []

        if not self.default_chain:
            errors.append("DEFAULT_CHAIN is required")

        if not self.rpc_urls:
            errors.append("At least one RPC URL must be configured")

        for chain, url in self.rpc_urls.items():
            if not url.startswith(("https://", "wss://")):
                errors.append(f"RPC URL for {chain} must use HTTPS or WSS")

        return errors


@dataclass
class APIServerConfig:
    """API server configuration.

    Attributes:
        host: Server host
        port: Server port
        cors_origins: Allowed CORS origins
        rate_limit: Default rate limit
        rate_window: Rate limit window in seconds
    """

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    rate_limit: int = APIConfig.DEFAULT_RATE_LIMIT
    rate_window: int = APIConfig.DEFAULT_RATE_WINDOW_SECONDS

    def validate(self) -> list[str]:
        """Validate API server configuration."""
        errors = []

        if not 1 <= self.port <= 65535:
            errors.append("API port must be between 1 and 65535")

        if self.rate_limit < 1:
            errors.append("Rate limit must be at least 1")

        return errors


@dataclass
class SardisConfig:
    """Complete Sardis service configuration.

    This is the main configuration class that aggregates all
    service-specific configurations.

    Attributes:
        environment: Current environment (development, staging, production)
        database: Database configuration
        cache: Cache configuration
        turnkey: Turnkey MPC configuration
        persona: Persona KYC configuration
        elliptic: Elliptic sanctions configuration
        lithic: Lithic cards configuration
        chain: Blockchain configuration
        api: API server configuration
        debug: Enable debug mode
    """

    environment: Environment = Environment.DEVELOPMENT
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    turnkey: TurnkeyConfig = field(default_factory=TurnkeyConfig)
    persona: PersonaConfig = field(default_factory=PersonaConfig)
    elliptic: EllipticConfig = field(default_factory=EllipticConfig)
    lithic: LithicConfig = field(default_factory=LithicConfig)
    chain: ChainConfig = field(default_factory=ChainConfig)
    api: APIServerConfig = field(default_factory=APIServerConfig)
    debug: bool = False

    def validate(self, strict: bool = False) -> list[str]:
        """Validate the complete configuration.

        Args:
            strict: If True, require all optional services to be configured

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Always required
        errors.extend(self.database.validate())
        errors.extend(self.cache.validate())
        errors.extend(self.chain.validate())
        errors.extend(self.api.validate())

        # In production, require Turnkey
        if self.environment == Environment.PRODUCTION:
            errors.extend(self.turnkey.validate())

        # In strict mode, validate all services
        if strict:
            errors.extend(self.turnkey.validate())
            errors.extend(self.persona.validate())
            errors.extend(self.elliptic.validate())
            errors.extend(self.lithic.validate())

        return errors

    def is_valid(self, strict: bool = False) -> bool:
        """Check if configuration is valid.

        Args:
            strict: If True, require all optional services

        Returns:
            True if configuration is valid
        """
        return len(self.validate(strict)) == 0

    def get_missing_services(self) -> list[str]:
        """Get list of unconfigured optional services.

        Returns:
            List of service names that are not configured
        """
        missing = []

        if self.turnkey.validate():
            missing.append("turnkey")
        if self.persona.validate():
            missing.append("persona")
        if self.elliptic.validate():
            missing.append("elliptic")
        if self.lithic.validate():
            missing.append("lithic")

        return missing


# =============================================================================
# Configuration Loading
# =============================================================================

def load_config_from_env() -> SardisConfig:
    """Load configuration from environment variables.

    Returns:
        Populated SardisConfig instance

    Environment Variables:
        ENVIRONMENT: Application environment (development, staging, production)
        DATABASE_URL: PostgreSQL connection string
        REDIS_URL: Redis connection string (optional)
        TURNKEY_API_KEY: Turnkey API key
        TURNKEY_ORGANIZATION_ID: Turnkey organization ID
        PERSONA_API_KEY: Persona API key
        PERSONA_TEMPLATE_ID: Persona template ID
        ELLIPTIC_API_KEY: Elliptic API key
        LITHIC_API_KEY: Lithic API key
        DEFAULT_CHAIN: Default blockchain
        RPC_URL_<CHAIN>: RPC URL for specific chain (e.g., RPC_URL_BASE)
        API_HOST: API server host
        API_PORT: API server port
        DEBUG: Enable debug mode
    """
    env_str = os.getenv("ENVIRONMENT", "development").lower()
    try:
        environment = Environment(env_str)
    except ValueError:
        environment = Environment.DEVELOPMENT

    # Load RPC URLs from environment
    rpc_urls = {}
    chains = ["ethereum", "polygon", "base", "arbitrum", "optimism", "solana"]
    for chain in chains:
        url = os.getenv(f"RPC_URL_{chain.upper()}")
        if url:
            rpc_urls[chain] = url

    # CORS origins
    cors_str = os.getenv("CORS_ORIGINS", "*")
    cors_origins = [o.strip() for o in cors_str.split(",")]

    return SardisConfig(
        environment=environment,
        database=DatabaseConfig(
            url=os.getenv("DATABASE_URL", ""),
            pool_min_size=int(os.getenv("DB_POOL_MIN", str(PoolLimits.DB_POOL_MIN_SIZE))),
            pool_max_size=int(os.getenv("DB_POOL_MAX", str(PoolLimits.DB_POOL_MAX_SIZE))),
        ),
        cache=CacheConfig(
            redis_url=os.getenv("REDIS_URL"),
        ),
        turnkey=TurnkeyConfig(
            api_key=os.getenv("TURNKEY_API_KEY", ""),
            organization_id=os.getenv("TURNKEY_ORGANIZATION_ID", ""),
            base_url=os.getenv("TURNKEY_BASE_URL", "https://api.turnkey.com"),
        ),
        persona=PersonaConfig(
            api_key=os.getenv("PERSONA_API_KEY", ""),
            template_id=os.getenv("PERSONA_TEMPLATE_ID", ""),
            webhook_secret=os.getenv("PERSONA_WEBHOOK_SECRET", ""),
        ),
        elliptic=EllipticConfig(
            api_key=os.getenv("ELLIPTIC_API_KEY", ""),
            risk_threshold=float(os.getenv("ELLIPTIC_RISK_THRESHOLD", "0.7")),
        ),
        lithic=LithicConfig(
            api_key=os.getenv("LITHIC_API_KEY", ""),
            webhook_secret=os.getenv("LITHIC_WEBHOOK_SECRET", ""),
        ),
        chain=ChainConfig(
            default_chain=os.getenv("DEFAULT_CHAIN", "base"),
            rpc_urls=rpc_urls,
        ),
        api=APIServerConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            cors_origins=cors_origins,
            rate_limit=int(os.getenv("RATE_LIMIT", str(APIConfig.DEFAULT_RATE_LIMIT))),
        ),
        debug=os.getenv("DEBUG", "").lower() in ("true", "1", "yes"),
    )


def validate_config(
    config: SardisConfig,
    strict: bool = False,
    raise_on_error: bool = True,
) -> list[str]:
    """Validate a configuration object.

    Args:
        config: Configuration to validate
        strict: If True, require all optional services
        raise_on_error: If True, raise exception on validation failure

    Returns:
        List of validation error messages

    Raises:
        SardisConfigurationError: If validation fails and raise_on_error is True
    """
    errors = config.validate(strict)

    if errors:
        logger.error(f"Configuration validation failed: {errors}")
        if raise_on_error:
            raise SardisConfigurationError(
                "Configuration validation failed",
                details={"errors": errors},
            )

    return errors


def require_service_config(
    config: SardisConfig,
    service: str,
) -> None:
    """Ensure a specific service is properly configured.

    Args:
        config: Configuration to check
        service: Service name to require

    Raises:
        SardisConfigurationError: If service is not configured
    """
    service_configs = {
        "database": config.database,
        "cache": config.cache,
        "turnkey": config.turnkey,
        "persona": config.persona,
        "elliptic": config.elliptic,
        "lithic": config.lithic,
        "chain": config.chain,
        "api": config.api,
    }

    if service not in service_configs:
        raise SardisConfigurationError(
            f"Unknown service: {service}",
            details={"valid_services": list(service_configs.keys())},
        )

    service_config = service_configs[service]
    errors = service_config.validate()

    if errors:
        raise SardisConfigurationError(
            f"Service '{service}' is not properly configured",
            details={"errors": errors},
        )


# =============================================================================
# Startup Validation
# =============================================================================

def validate_startup(
    config: Optional[SardisConfig] = None,
    required_services: Optional[Sequence[str]] = None,
) -> SardisConfig:
    """Validate configuration at application startup.

    This function should be called at application startup to ensure
    all required configuration is present and valid.

    Args:
        config: Configuration to validate (loads from env if not provided)
        required_services: List of services that must be configured

    Returns:
        Validated configuration

    Raises:
        SardisConfigurationError: If validation fails

    Example:
        config = validate_startup(required_services=["turnkey", "elliptic"])
    """
    if config is None:
        config = load_config_from_env()

    # Validate base configuration
    errors = config.validate(strict=False)

    # Check required services
    if required_services:
        for service in required_services:
            try:
                require_service_config(config, service)
            except SardisConfigurationError as e:
                errors.append(str(e))

    if errors:
        raise SardisConfigurationError(
            "Application startup failed due to configuration errors",
            details={"errors": errors},
        )

    # Log configuration summary
    logger.info(
        f"Configuration validated successfully. "
        f"Environment: {config.environment.value}, "
        f"Missing services: {config.get_missing_services()}"
    )

    return config


__all__ = [
    # Configuration classes
    "SardisConfig",
    "DatabaseConfig",
    "CacheConfig",
    "TurnkeyConfig",
    "PersonaConfig",
    "EllipticConfig",
    "LithicConfig",
    "ChainConfig",
    "APIServerConfig",
    "Environment",
    # Functions
    "load_config_from_env",
    "validate_config",
    "require_service_config",
    "validate_startup",
]
