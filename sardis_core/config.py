"""Configuration for Sardis Core."""

from pydantic_settings import BaseSettings
from decimal import Decimal


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
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
    
    class Config:
        env_prefix = "SARDIS_"
        env_file = ".env"


# Global settings instance
settings = Settings()

