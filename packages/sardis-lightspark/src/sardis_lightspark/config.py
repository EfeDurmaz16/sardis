"""Lightspark Grid configuration."""
from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings


class LightsparkConfig(BaseSettings):
    """Lightspark Grid API configuration."""

    api_key: str = ""
    api_secret: str = ""
    base_url: str = "https://api.lightspark.com/grid/2025-10-13"
    uma_domain: str = "sardis.sh"
    webhook_secret: str = ""
    enabled: bool = False
    environment: Literal["sandbox", "production"] = "sandbox"

    # Feature flags
    fx_enabled: bool = True
    payouts_enabled: bool = True
    uma_enabled: bool = True
    plaid_enabled: bool = False

    class Config:
        env_prefix = "SARDIS_LIGHTSPARK_"
