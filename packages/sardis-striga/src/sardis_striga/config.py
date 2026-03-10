"""Striga provider configuration."""
from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings


class StrigaConfig(BaseSettings):
    """Striga EEA banking + card issuance configuration."""

    api_key: str = ""
    api_secret: str = ""
    base_url: str = "https://payment.striga.com/api/v1"
    webhook_secret: str = ""
    enabled: bool = False
    environment: Literal["sandbox", "production"] = "sandbox"

    # Feature sub-flags
    cards_enabled: bool = True
    viban_enabled: bool = True
    lightning_enabled: bool = False
    standing_orders_enabled: bool = False
    kyc_enabled: bool = True

    class Config:
        env_prefix = "SARDIS_STRIGA_"
