"""Canonical configuration surface for Sardis services."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


def _normalize_environment(value: str) -> str:
    """Normalize common environment aliases to SardisSettings.environment values."""
    v = (value or "").strip().lower()
    if v in ("development", "dev", "local"):
        return "dev"
    if v in ("production", "prod"):
        return "prod"
    if v in ("sandbox", "staging"):
        # Sardis currently uses "sandbox" as a pre-prod environment for demos.
        return "sandbox"
    return v


def _normalize_chain_mode(value: str) -> str:
    """Normalize common chain mode aliases to SardisSettings.chain_mode values."""
    v = (value or "").strip().lower()
    if v in ("sim", "simulate", "simulated"):
        return "simulated"
    # Historical/compose aliases: "testnet"/"mainnet" means "live execution"
    if v in ("live", "testnet", "mainnet"):
        return "live"
    return v


class TurnkeyConfig(BaseSettings):
    """Turnkey MPC provider configuration."""
    organization_id: str = ""
    api_public_key: str = ""
    api_private_key: str = ""  # Can be hex-encoded key or path to PEM file
    default_wallet_id: str = ""
    api_base: str = "https://api.turnkey.com"
    
    class Config:
        env_prefix = "TURNKEY_"


class MPCProvider(BaseSettings):
    """MPC provider configuration (Turnkey or Fireblocks)."""
    name: Literal["turnkey", "fireblocks", "local", "simulated"] = "simulated"
    api_base: str = ""
    credential_id: str = ""  # Organization ID for Turnkey


class ChainConfig(BaseSettings):
    """Blockchain network configuration."""
    name: str = "base_sepolia"
    rpc_url: str = "https://sepolia.base.org"
    chain_id: int = 84532
    stablecoins: List[str] = Field(default_factory=lambda: ["USDC"])
    settlement_vault: str = ""


class LithicConfig(BaseSettings):
    """Lithic card issuing configuration."""

    api_key: str = ""
    environment: Literal["sandbox", "production"] = "sandbox"
    webhook_secret: str = ""
    asa_webhook_secret: str = ""
    asa_enabled: bool = False

    class Config:
        env_prefix = "LITHIC_"


class StripeConfig(BaseSettings):
    """Stripe Issuing + Treasury configuration."""

    api_key: str = ""
    webhook_secret: str = ""
    treasury_financial_account_id: str = ""
    connected_account_id: str = ""
    connected_account_map_json: str = ""
    issuing_enabled: bool = True

    class Config:
        env_prefix = "STRIPE_"


class CoinbaseConfig(BaseSettings):
    """Coinbase CDP / x402 configuration."""

    api_key_name: str = ""
    api_key_private_key: str = ""
    topup_api_key: str = ""
    topup_base_url: str = "https://api.coinbase.com"
    topup_path: str = "/v1/funding/topups"
    network_id: str = "base-mainnet"
    x402_enabled: bool = False

    class Config:
        env_prefix = "COINBASE_CDP_"


class RainConfig(BaseSettings):
    """Rain stablecoin card issuing configuration."""

    api_key: str = ""
    program_id: str = ""
    base_url: str = "https://api.rain.xyz"
    webhook_secret: str = ""
    funding_topup_path: str = "/v1/funding/topups"
    cards_path_map_json: str = ""
    cards_method_map_json: str = ""

    class Config:
        env_prefix = "RAIN_"


class BridgeCardsConfig(BaseSettings):
    """Bridge cards issuing configuration."""

    api_key: str = ""
    api_secret: str = ""
    program_id: str = ""
    cards_base_url: str = "https://api.bridge.xyz"
    funding_topup_path: str = "/v1/funding/topups"
    webhook_secret: str = ""
    cards_path_map_json: str = ""
    cards_method_map_json: str = ""

    class Config:
        env_prefix = "BRIDGE_"


class CardStackConfig(BaseSettings):
    """Card stack provider routing configuration."""

    primary_provider: Literal["lithic", "stripe_issuing", "mock", "rain", "bridge_cards"] = "mock"
    fallback_provider: Optional[Literal["lithic", "stripe_issuing", "rain", "bridge_cards"]] = None
    on_chain_provider: Optional[Literal["coinbase_cdp"]] = None
    org_provider_overrides_json: str = ""

    class Config:
        env_prefix = "SARDIS_CARDS_"


class FundingRoutingConfig(BaseSettings):
    """Funding routing strategy for issuer top-ups."""

    strategy: Literal["fiat_first", "stablecoin_first", "hybrid"] = "fiat_first"
    primary_adapter: Literal["stripe", "coinbase_cdp", "rain", "bridge"] = "stripe"
    fallback_adapter: Optional[Literal["stripe", "coinbase_cdp", "rain", "bridge"]] = None
    stablecoin_prefund_enabled: bool = False
    require_connected_account: bool = False

    class Config:
        env_prefix = "SARDIS_FUNDING_"


class SardisSettings(BaseSettings):
    """Main Sardis configuration."""
    
    # Environment
    environment: Literal["dev", "sandbox", "prod"] = "dev"
    
    # API
    api_base_url: str = "http://localhost:8000"
    
    # CORS - allowed origins for API (use str to handle comma-separated env vars)
    allowed_origins: str = "http://localhost:3005,http://localhost:5173"
    # Mandate domain allowlist
    allowed_domains: list[str] = Field(default_factory=lambda: ["sardis.sh", "localhost"])
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Return allowed origins as a list."""
        canonical_prod_origins = [
            "https://sardis.sh",
            "https://www.sardis.sh",
            "https://app.sardis.sh",
        ]

        if not self.allowed_origins:
            if self.environment in {"prod", "sandbox"}:
                return canonical_prod_origins
            return ["http://localhost:3005", "http://localhost:5173"]
        raw = self.allowed_origins.strip()

        # Allow JSON array strings in env files:
        # SARDIS_ALLOWED_ORIGINS=["https://www.sardis.sh","https://app.sardis.sh"]
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    origins = [str(origin).strip() for origin in parsed if str(origin).strip()]
                    if self.environment in {"prod", "sandbox"}:
                        for origin in canonical_prod_origins:
                            if origin not in origins:
                                origins.append(origin)
                    return origins
            except json.JSONDecodeError:
                # Fall through to CSV parsing for malformed values.
                pass

        origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
        if self.environment in {"prod", "sandbox"}:
            for origin in canonical_prod_origins:
                if origin not in origins:
                    origins.append(origin)
        return origins
    
    # Security
    secret_key: str = ""
    
    # Mandate settings
    mandate_ttl_seconds: int = 300
    
    # Database - PostgreSQL for production
    database_url: str = ""
    ledger_dsn: str = ""
    mandate_archive_dsn: str = "sqlite:///./data/mandates.db"
    replay_cache_dsn: str = "sqlite:///./data/replay_cache.db"
    
    # Redis/Upstash for caching (optional)
    redis_url: str = ""
    
    # Chain configuration - defaults for demo
    chains: List[ChainConfig] = Field(default_factory=lambda: [
        ChainConfig(
            name="base_sepolia",
            rpc_url="https://sepolia.base.org",
            chain_id=84532,
            stablecoins=["USDC"],
            settlement_vault="",
        )
    ])
    
    # MPC provider - simulated by default for demo
    mpc: MPCProvider = Field(default_factory=MPCProvider)
    
    # Turnkey configuration (loaded from TURNKEY_* env vars)
    turnkey: TurnkeyConfig = Field(default_factory=TurnkeyConfig)
    lithic: LithicConfig = Field(default_factory=LithicConfig)
    stripe: StripeConfig = Field(default_factory=StripeConfig)
    coinbase: CoinbaseConfig = Field(default_factory=CoinbaseConfig)
    rain: RainConfig = Field(default_factory=RainConfig)
    bridge_cards: BridgeCardsConfig = Field(default_factory=BridgeCardsConfig)
    cards: CardStackConfig = Field(default_factory=CardStackConfig)
    funding: FundingRoutingConfig = Field(default_factory=FundingRoutingConfig)
    
    # Chain execution mode
    chain_mode: Literal["simulated", "live"] = "simulated"
    # ERC-4337 gasless execution (v2 smart wallets)
    erc4337_enabled: bool = False
    erc4337_chain_allowlist: str = "base_sepolia"
    pimlico_api_key: str = ""
    pimlico_bundler_url: str = ""
    pimlico_paymaster_url: str = ""
    erc4337_entrypoint_v07_address: str = "0x0000000071727De22E5E9d8BAf0edAc6f37da032"
    erc4337_rollout_stage: Literal["pilot", "beta", "ga"] = "pilot"
    erc4337_sponsor_stage_caps_json: str = ""
    # Agent payment endpoint limiter (sliding window)
    agent_payment_rate_limit_enabled: bool = True
    agent_payment_rate_limit_max_requests: int = 30
    agent_payment_rate_limit_window_seconds: int = 60

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"
    
    @property
    def turnkey_configured(self) -> bool:
        """Check if Turnkey is properly configured."""
        return bool(
            self.turnkey.organization_id
            and self.turnkey.api_public_key
            and self.turnkey.api_private_key
        )

    @property
    def erc4337_chain_allowlist_set(self) -> set[str]:
        values = [v.strip() for v in self.erc4337_chain_allowlist.split(",")]
        return {v for v in values if v}

    class Config:
        env_prefix = "SARDIS_"
        env_nested_delimiter = "__"
        env_file = ".env"
        extra = "ignore"

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        return _normalize_environment(v)

    @field_validator("chain_mode", mode="before")
    @classmethod
    def normalize_chain_mode(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        return _normalize_chain_mode(v)

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        import os
        env = _normalize_environment(os.getenv("SARDIS_ENVIRONMENT", "dev"))
        if env != "dev" and (not v or len(v) < 32):
            raise ValueError(
                "SECRET_KEY must be at least 32 characters in production. "
                "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return v or "dev-only-secret-key-not-for-production"
    
    @field_validator("database_url", "ledger_dsn", mode="before")
    @classmethod
    def set_database_defaults(cls, v: str, info) -> str:
        """Use DATABASE_URL for ledger_dsn if not set."""
        import os
        import warnings
        
        if not v:
            # Try DATABASE_URL first
            v = os.getenv("DATABASE_URL", "postgresql://localhost/sardis")
        
        # Warn if using SQLite in production
        env = _normalize_environment(os.getenv("SARDIS_ENVIRONMENT", "dev"))
        if env == "prod" and v.startswith("sqlite"):
            warnings.warn(
                "SQLite is not recommended for production. "
                "Please use PostgreSQL by setting DATABASE_URL environment variable.",
                RuntimeWarning,
            )
        
        return v
    
    @field_validator("mandate_archive_dsn", "replay_cache_dsn", mode="before")
    @classmethod
    def set_cache_defaults(cls, v: str, info) -> str:
        """Use DATABASE_URL for archive/cache DSNs if PostgreSQL is available."""
        import os
        
        if not v:
            database_url = os.getenv("DATABASE_URL", "")
            if database_url.startswith(("postgresql://", "postgres://")):
                return database_url
            return v
        
        # Use DATABASE_URL if v is default SQLite and PostgreSQL is available
        if v.startswith("sqlite:") and info.field_name in ("mandate_archive_dsn", "replay_cache_dsn"):
            database_url = os.getenv("DATABASE_URL", "")
            if database_url.startswith(("postgresql://", "postgres://")):
                return database_url
        
        return v


def validate_production_config(settings: SardisSettings) -> list[str]:
    """
    Validate that all required configuration is present for production.

    Returns a list of missing/invalid configuration items.
    """
    import os
    errors = []

    if settings.environment in ("prod", "sandbox"):
        # Required for production
        if not settings.secret_key or len(settings.secret_key) < 32:
            errors.append("SARDIS_SECRET_KEY: Must be at least 32 characters")

        if not os.getenv("JWT_SECRET_KEY"):
            errors.append("JWT_SECRET_KEY: Required for auth (min 32 chars)")

        if not os.getenv("SARDIS_ADMIN_PASSWORD"):
            errors.append("SARDIS_ADMIN_PASSWORD: Required for admin access")

        if not settings.database_url or settings.database_url.startswith("sqlite"):
            errors.append("DATABASE_URL: PostgreSQL required for production")

        # CORS hardening: require explicit HTTPS origins in production-like envs.
        origins = settings.allowed_origins_list
        if not origins:
            errors.append("SARDIS_ALLOWED_ORIGINS: Must define at least one allowed origin")
        if "*" in origins:
            errors.append("SARDIS_ALLOWED_ORIGINS: Wildcard '*' is not allowed with credentials enabled")
        if settings.environment == "prod":
            for origin in origins:
                o = origin.strip().lower()
                if o.startswith(("http://localhost", "http://127.0.0.1", "http://0.0.0.0")):
                    errors.append(f"SARDIS_ALLOWED_ORIGINS: Localhost origin not allowed in production ({origin})")
                if o.startswith("http://") and not o.startswith(("http://localhost", "http://127.0.0.1", "http://0.0.0.0")):
                    errors.append(f"SARDIS_ALLOWED_ORIGINS: Non-HTTPS origin not allowed in production ({origin})")

        if not (os.getenv("REDIS_URL") or os.getenv("SARDIS_REDIS_URL") or os.getenv("UPSTASH_REDIS_URL")):
            errors.append("REDIS_URL: Required for distributed rate limiting (or set SARDIS_REDIS_URL/UPSTASH_REDIS_URL)")

        if settings.environment == "prod" and settings.chain_mode != "live":
            errors.append("SARDIS_CHAIN_MODE: Must be 'live' in production")

        # MPC configuration
        if settings.chain_mode == "live":
            mpc_name = settings.mpc.name
            if mpc_name == "turnkey":
                if not settings.turnkey_configured:
                    errors.append("TURNKEY_*: Turnkey MPC provider not configured for live mode")
            elif mpc_name == "fireblocks":
                if not os.getenv("FIREBLOCKS_API_KEY"):
                    errors.append("FIREBLOCKS_API_KEY: Fireblocks MPC provider not configured for live mode")
            elif mpc_name == "local":
                errors.append(
                    "SARDIS_MPC__NAME: local signer is custodial and not allowed for production live execution"
                )
            else:
                errors.append(
                    "SARDIS_MPC__NAME: simulated signer is not allowed when SARDIS_CHAIN_MODE=live"
                )

            if os.getenv("SARDIS_EOA_PRIVATE_KEY"):
                errors.append(
                    "SARDIS_EOA_PRIVATE_KEY: local signer key is set (custodial path) and should be removed for non-custodial posture"
                )

        # Compliance providers (recommended)
        if not os.getenv("PERSONA_API_KEY"):
            errors.append("PERSONA_API_KEY: KYC provider not configured (recommended)")

        if not os.getenv("ELLIPTIC_API_KEY"):
            errors.append("ELLIPTIC_API_KEY: Sanctions screening not configured (recommended)")

    return errors


@lru_cache
def load_settings(env_file: str | None = None) -> SardisSettings:
    """Load SardisSettings once per process to keep services consistent."""
    import os
    import logging

    logger = logging.getLogger(__name__)
    env_path = Path(env_file) if env_file else None
    settings = SardisSettings(_env_file=env_path)

    # Run production validation
    env = _normalize_environment(os.getenv("SARDIS_ENVIRONMENT", settings.environment))
    if env in ("prod", "sandbox"):
        errors = validate_production_config(settings)
        if errors:
            logger.warning("=" * 60)
            logger.warning("PRODUCTION CONFIGURATION WARNINGS")
            logger.warning("=" * 60)
            for error in errors:
                logger.warning(f"  - {error}")
            logger.warning("=" * 60)

            # In strict mode, raise error for critical missing config
            critical_errors = [e for e in errors if any(k in e for k in
                ["SECRET_KEY", "JWT_SECRET", "ADMIN_PASSWORD", "DATABASE_URL"])]
            if critical_errors and os.getenv("SARDIS_STRICT_CONFIG", "false").lower() == "true":
                raise RuntimeError(
                    f"Critical configuration missing: {', '.join(critical_errors)}. "
                    "Set SARDIS_STRICT_CONFIG=false to bypass (not recommended)."
                )

    return settings
