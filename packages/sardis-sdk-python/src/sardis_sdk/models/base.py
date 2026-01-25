"""Base model for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


# Supported blockchain networks
Chain = Literal[
    "base",
    "base_sepolia",
    "polygon",
    "polygon_amoy",
    "ethereum",
    "ethereum_sepolia",
    "arbitrum",
    "arbitrum_sepolia",
    "optimism",
    "optimism_sepolia",
]

# Supported stablecoins
Token = Literal["USDC", "USDT", "PYUSD", "EURC"]

# MPC providers
MPCProvider = Literal["turnkey", "fireblocks", "local"]


class ChainEnum(str, Enum):
    """
    Supported blockchain networks.

    Note: Solana support is planned but NOT YET IMPLEMENTED.
    """

    BASE = "base"
    BASE_SEPOLIA = "base_sepolia"
    POLYGON = "polygon"
    POLYGON_AMOY = "polygon_amoy"
    ETHEREUM = "ethereum"
    ETHEREUM_SEPOLIA = "ethereum_sepolia"
    ARBITRUM = "arbitrum"
    ARBITRUM_SEPOLIA = "arbitrum_sepolia"
    OPTIMISM = "optimism"
    OPTIMISM_SEPOLIA = "optimism_sepolia"


class ExperimentalChain(str, Enum):
    """
    Experimental chains - NOT YET IMPLEMENTED.

    These are planned for future releases. Using them will raise NotImplementedError.
    """

    SOLANA = "solana"
    SOLANA_DEVNET = "solana_devnet"


class SardisModel(BaseModel):
    """Base model with common configuration."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        extra="ignore",
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump(mode="json", exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SardisModel":
        """Create model from dictionary."""
        return cls.model_validate(data)
