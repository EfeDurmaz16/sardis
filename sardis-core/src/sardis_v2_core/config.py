"""Canonical configuration surface for Sardis services."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Literal

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class MPCProvider(BaseSettings):
    name: Literal["turnkey", "fireblocks"]
    api_base: str
    credential_id: str


class ChainConfig(BaseSettings):
    name: str
    rpc_url: str
    chain_id: int
    stablecoins: List[str] = Field(default_factory=list)
    settlement_vault: str


class SardisSettings(BaseSettings):
    environment: Literal["dev", "sandbox", "prod"] = "sandbox"
    api_base_url: str = "https://api.sardis.local"
    allowed_domains: List[str] = Field(default_factory=list)
    mandate_ttl_seconds: int = 300
    ledger_dsn: str = "postgresql://localhost/sardis"
    mandate_archive_dsn: str = "sqlite:///./data/mandates.db"
    replay_cache_dsn: str = "sqlite:///./data/replay_cache.db"
    chains: List[ChainConfig]
    mpc: MPCProvider

    class Config:
        env_nested_delimiter = "__"
        env_file = ".env"

    @validator("allowed_domains", each_item=True)
    def strip_domains(cls, value: str) -> str:  # noqa: D401
        """Ensure no trailing slash for deterministic signing."""
        return value.rstrip("/")


@lru_cache
def load_settings(env_file: str | None = None) -> SardisSettings:
    """Load SardisSettings once per process to keep services consistent."""
    env_path = Path(env_file) if env_file else None
    return SardisSettings(_env_file=env_path)
