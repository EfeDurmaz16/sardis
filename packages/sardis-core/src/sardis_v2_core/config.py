"""Canonical configuration surface for Sardis services."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class MPCProvider(BaseSettings):
    """MPC provider configuration (Turnkey or Fireblocks)."""
    name: Literal["turnkey", "fireblocks", "simulated"] = "simulated"
    api_base: str = ""
    credential_id: str = ""


class ChainConfig(BaseSettings):
    """Blockchain network configuration."""
    name: str = "base_sepolia"
    rpc_url: str = "https://sepolia.base.org"
    chain_id: int = 84532
    stablecoins: List[str] = Field(default_factory=lambda: ["USDC"])
    settlement_vault: str = ""


class SardisSettings(BaseSettings):
    """Main Sardis configuration."""
    
    # Environment
    environment: Literal["dev", "sandbox", "prod"] = "dev"
    
    # API
    api_base_url: str = "http://localhost:8000"
    
    # CORS - allowed origins for API
    allowed_origins: List[str] = Field(default_factory=lambda: [
        "http://localhost:3005",
        "http://localhost:5173",
    ])
    
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
    
    # Chain execution mode
    chain_mode: Literal["simulated", "live"] = "simulated"

    class Config:
        env_prefix = "SARDIS_"
        env_nested_delimiter = "__"
        env_file = ".env"
        extra = "ignore"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """Parse comma-separated origins from env var."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        import os
        env = os.getenv("SARDIS_ENVIRONMENT", "dev")
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
        env = os.getenv("SARDIS_ENVIRONMENT", "dev")
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


@lru_cache
def load_settings(env_file: str | None = None) -> SardisSettings:
    """Load SardisSettings once per process to keep services consistent."""
    env_path = Path(env_file) if env_file else None
    return SardisSettings(_env_file=env_path)
