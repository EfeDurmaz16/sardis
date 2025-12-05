"""Configuration for Sardis Core."""

from decimal import Decimal
from typing import List, Optional

from pydantic import ConfigDict, field_validator
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
    
    # CORS - allowed origins (comma-separated in env)
    allowed_origins: List[str] = []
    
    # Security - NO DEFAULTS for sensitive values
    secret_key: str = ""
    admin_password: str = ""
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v or v == "insecure-secret-key-change-me":
            import os
            if os.getenv("SARDIS_ENVIRONMENT", "dev") != "dev":
                raise ValueError(
                    "SECRET_KEY must be set in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            # Allow empty in dev mode, use a dev-only default
            return "dev-only-secret-key-not-for-production"
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v
    
    # Blockchain
    base_rpc_url: str = "https://sepolia.base.org"
    polygon_rpc_url: str = "https://rpc-amoy.polygon.technology"
    ethereum_rpc_url: str = "https://rpc.sepolia.org"
    
    # Relayer (for gas/testing) - MUST be set via environment variable
    relayer_private_key: str = ""
    
    @field_validator("relayer_private_key")
    @classmethod
    def validate_relayer_key(cls, v: str) -> str:
        import os
        if os.getenv("SARDIS_ENVIRONMENT", "dev") == "dev":
            # In dev mode, allow empty (simulated chain)
            return v or ""
        if not v or v == "0x0000000000000000000000000000000000000000000000000000000000000000":
            raise ValueError(
                "RELAYER_PRIVATE_KEY must be set in production. "
                "Never commit real private keys to code."
            )
        return v
    
    # Stablecoin Settings
    default_currency: str = "USDC"
    
    # Fee Settings
    transaction_fee: Decimal = Decimal("0.10")  # Fixed fee per transaction
    fee_pool_wallet_id: str = "sardis_fee_pool"
    
    # Default Limits
    default_limit_per_tx: Decimal = Decimal("100.00")
    default_limit_total: Decimal = Decimal("1000.00")
    
    # System Settings
    system_wallet_id: str = "wallet_system_treasury"
    fee_pool_wallet_id: str = "wallet_system_fees"
    settlement_wallet_id: str = "wallet_system_settlement"
    
    # Optional integrations (loaded from environment)
    openai_api_key: Optional[str] = None
    
    # Blockchain settings
    settlement_mode: str = "internal_ledger_only"  # internal_ledger_only, chain_write_per_tx, batched_chain_settlement
    
    # Chain RPC endpoints (testnet defaults)
    base_sepolia_rpc: str = "https://sepolia.base.org"
    ethereum_sepolia_rpc: str = "https://ethereum-sepolia.publicnode.com"
    polygon_amoy_rpc: str = "https://rpc-amoy.polygon.technology"
    
    # USDC contract addresses (testnet)
    base_sepolia_usdc: str = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"  # Base Sepolia USDC
    ethereum_sepolia_usdc: str = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"  # Sepolia USDC
    polygon_amoy_usdc: str = "0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582"  # Amoy USDC
    
    # Private key for gas pool wallet (ONLY for testnet - never commit real keys)
    gas_pool_private_key: Optional[str] = None
    
    # Enable real blockchain transactions (False = simulation mode)
    enable_real_blockchain: bool = False
    
    # Smart contract addresses (deployed by Sardis)
    wallet_factory_base: Optional[str] = None
    wallet_factory_polygon: Optional[str] = None
    escrow_base: Optional[str] = None
    escrow_polygon: Optional[str] = None
    
    # Default chain for new wallets
    default_chain: str = "base_sepolia"
    
    # Database settings (for future use)
    # Database settings
    database_url: str = "postgresql+asyncpg://efebarandurmaz@localhost:5432/sardis"
    
    # Stripe/Marqeta for virtual cards (future)
    stripe_api_key: Optional[str] = None
    marqeta_api_key: Optional[str] = None


# Global settings instance
settings = Settings()

