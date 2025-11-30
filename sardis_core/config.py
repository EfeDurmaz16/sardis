"""Configuration for Sardis Core."""

from decimal import Decimal
from typing import Optional

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Use Pydantic v2 model_config instead of nested Config class
    # 'extra=ignore' allows extra environment variables without raising errors
    model_config = ConfigDict(
        env_prefix="SARDIS_",
        env_file=".env",
        extra="ignore",
    )
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    
    # Stablecoin Settings
    default_currency: str = "USDC"
    
    # Fee Settings
    transaction_fee: Decimal = Decimal("0.10")  # Fixed fee per transaction
    fee_pool_wallet_id: str = "sardis_fee_pool"
    
    # Default Limits
    default_limit_per_tx: Decimal = Decimal("100.00")
    default_limit_total: Decimal = Decimal("1000.00")
    
    # System Settings
    system_wallet_id: str = "sardis_system"
    
    # Optional integrations (loaded from environment)
    openai_api_key: Optional[str] = None
    
    # Blockchain settings
    settlement_mode: str = "internal_ledger_only"  # internal_ledger_only, chain_write_per_tx, batched_chain_settlement
    
    # Database settings (for future use)
    database_url: Optional[str] = None


# Global settings instance
settings = Settings()

