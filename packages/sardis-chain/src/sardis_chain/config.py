"""
Configuration management for sardis-chain.

Provides centralized configuration for:
- RPC endpoints with fallback support
- Chain ID validation
- Timeout values
- Gas estimation parameters
- Nonce management settings
- Logging configuration
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChainNetwork(str, Enum):
    """Supported blockchain networks."""
    # Mainnets
    ETHEREUM = "ethereum"
    BASE = "base"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"

    # Testnets
    ETHEREUM_SEPOLIA = "ethereum_sepolia"
    BASE_SEPOLIA = "base_sepolia"
    POLYGON_AMOY = "polygon_amoy"
    ARBITRUM_SEPOLIA = "arbitrum_sepolia"
    OPTIMISM_SEPOLIA = "optimism_sepolia"


@dataclass
class RPCEndpointConfig:
    """Configuration for a single RPC endpoint."""
    url: str
    priority: int = 0  # Lower is higher priority
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    weight: int = 100  # For weighted round-robin

    # Health check settings
    health_check_interval_seconds: float = 60.0
    max_consecutive_failures: int = 3

    # Rate limiting
    requests_per_second: Optional[float] = None  # None = unlimited


@dataclass
class ChainConfig:
    """Configuration for a blockchain network."""
    chain_id: int
    name: str
    display_name: str

    # RPC endpoints (primary + fallbacks)
    rpc_endpoints: List[RPCEndpointConfig] = field(default_factory=list)

    # Block timing
    block_time_seconds: float = 2.0

    # Confirmation requirements
    confirmations_required: int = 1
    confirmation_timeout_seconds: float = 120.0

    # Gas settings
    gas_limit_buffer_percent: int = 20  # Add 20% to estimated gas
    max_gas_price_gwei: Decimal = Decimal("500")
    max_priority_fee_gwei: Decimal = Decimal("50")
    max_transaction_cost_usd: Decimal = Decimal("50")

    # Nonce management
    nonce_retry_attempts: int = 3
    nonce_retry_delay_seconds: float = 1.0
    pending_tx_timeout_seconds: float = 300.0  # 5 minutes

    # Reorg detection
    reorg_detection_enabled: bool = True
    reorg_max_depth: int = 64  # Maximum reorg depth to track

    # Network type
    is_testnet: bool = False
    native_token: str = "ETH"
    explorer_url: str = ""

    def get_primary_rpc_url(self) -> str:
        """Get the primary (highest priority) RPC URL."""
        if not self.rpc_endpoints:
            raise ValueError(f"No RPC endpoints configured for {self.name}")
        sorted_endpoints = sorted(self.rpc_endpoints, key=lambda e: e.priority)
        return sorted_endpoints[0].url

    def get_all_rpc_urls(self) -> List[str]:
        """Get all RPC URLs in priority order."""
        sorted_endpoints = sorted(self.rpc_endpoints, key=lambda e: e.priority)
        return [e.url for e in sorted_endpoints]


@dataclass
class NonceManagerConfig:
    """Configuration for nonce management."""
    # Cache settings
    cache_ttl_seconds: float = 30.0

    # Stuck transaction handling
    stuck_tx_timeout_seconds: float = 300.0  # 5 minutes
    auto_replace_stuck_tx: bool = True
    replacement_gas_bump_percent: int = 10  # Bump gas by 10% for replacement

    # Retry settings
    max_nonce_retries: int = 3
    nonce_retry_delay_seconds: float = 1.0

    # Gap handling
    auto_fill_nonce_gaps: bool = False  # Dangerous, disabled by default


@dataclass
class GasEstimationConfig:
    """Configuration for gas estimation."""
    # Buffer settings
    gas_limit_buffer_percent: int = 20  # Add 20% to estimated gas
    base_fee_buffer_percent: int = 25  # Buffer for base fee volatility

    # Fallback values
    default_gas_limit: int = 100000
    default_priority_fee_gwei: Decimal = Decimal("1.5")

    # Safety margins
    max_gas_price_multiplier: Decimal = Decimal("2.0")  # Max 2x current price

    # EIP-1559 settings
    use_eip1559: bool = True
    priority_fee_percentile: int = 50  # Use median priority fee


@dataclass
class TransactionSimulationConfig:
    """Configuration for transaction simulation."""
    enabled: bool = True
    timeout_seconds: float = 10.0

    # Simulation providers
    use_eth_call: bool = True
    use_debug_trace: bool = False  # Requires archive node

    # Failure handling
    block_on_simulation_failure: bool = True  # Fail-closed
    allow_simulation_timeout: bool = False


@dataclass
class ReorgDetectionConfig:
    """Configuration for chain reorg detection."""
    enabled: bool = True

    # Block tracking
    max_block_history: int = 128  # Blocks to keep in memory

    # Reorg thresholds
    shallow_reorg_depth: int = 6  # Warning only
    deep_reorg_depth: int = 12  # Block new transactions
    critical_reorg_depth: int = 64  # Halt all operations

    # Polling
    block_poll_interval_seconds: float = 2.0

    # Callbacks
    notify_on_reorg: bool = True


@dataclass
class LoggingConfig:
    """Configuration for blockchain operation logging."""
    # Log levels for different operations
    rpc_call_level: str = "DEBUG"
    transaction_level: str = "INFO"
    confirmation_level: str = "INFO"
    error_level: str = "ERROR"

    # Sensitive data handling
    mask_addresses: bool = False  # Partial masking for privacy
    log_gas_prices: bool = True
    log_nonces: bool = True

    # Performance logging
    log_rpc_latency: bool = True
    log_endpoint_health: bool = True

    # Audit logging
    audit_log_enabled: bool = True
    audit_log_path: Optional[str] = None  # None = use default logger


@dataclass
class SardisChainConfig:
    """
    Master configuration for sardis-chain.

    Supports loading from environment variables with prefix SARDIS_CHAIN_.
    """
    # Chain configurations (populated with defaults or from settings)
    chains: Dict[str, ChainConfig] = field(default_factory=dict)

    # Component configurations
    nonce_manager: NonceManagerConfig = field(default_factory=NonceManagerConfig)
    gas_estimation: GasEstimationConfig = field(default_factory=GasEstimationConfig)
    simulation: TransactionSimulationConfig = field(default_factory=TransactionSimulationConfig)
    reorg_detection: ReorgDetectionConfig = field(default_factory=ReorgDetectionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Global settings
    default_chain: str = "base_sepolia"
    http_timeout_seconds: float = 30.0
    max_concurrent_requests: int = 10

    def get_chain_config(self, chain: str) -> ChainConfig:
        """Get configuration for a specific chain."""
        if chain not in self.chains:
            raise ValueError(f"Unknown chain: {chain}")
        return self.chains[chain]

    def is_chain_supported(self, chain: str) -> bool:
        """Check if a chain is supported."""
        return chain in self.chains


def _get_env(key: str, default: Any = None, prefix: str = "SARDIS_CHAIN_") -> Any:
    """Get environment variable with prefix."""
    return os.getenv(f"{prefix}{key}", default)


def _get_env_list(key: str, default: List[str] = None, prefix: str = "SARDIS_CHAIN_") -> List[str]:
    """Get list environment variable (comma-separated)."""
    value = os.getenv(f"{prefix}{key}")
    if value:
        return [v.strip() for v in value.split(",") if v.strip()]
    return default or []


def _build_chain_config(
    chain_id: int,
    name: str,
    display_name: str,
    default_rpc: str,
    fallback_rpcs: List[str],
    block_time: float,
    native_token: str,
    explorer_url: str,
    is_testnet: bool = False,
) -> ChainConfig:
    """Build a ChainConfig with environment variable overrides."""

    # Check for custom RPC URL from environment
    env_key = f"{name.upper()}_RPC_URL"
    custom_rpc = os.getenv(env_key) or os.getenv(f"SARDIS_{env_key}")

    # Build endpoint list
    endpoints = []

    # Primary endpoint
    primary_url = custom_rpc or default_rpc
    endpoints.append(RPCEndpointConfig(
        url=primary_url,
        priority=0,
        timeout_seconds=30.0,
    ))

    # Fallback endpoints
    for i, url in enumerate(fallback_rpcs):
        if url != primary_url:  # Don't duplicate primary
            endpoints.append(RPCEndpointConfig(
                url=url,
                priority=i + 1,
                timeout_seconds=30.0,
            ))

    # Determine gas limits based on network type
    if is_testnet:
        max_gas_price = Decimal("1000")
        max_tx_cost = Decimal("1000")
    elif name in ("base", "optimism", "arbitrum"):
        max_gas_price = Decimal("100")
        max_tx_cost = Decimal("10")
    elif name == "polygon":
        max_gas_price = Decimal("1000")
        max_tx_cost = Decimal("20")
    else:  # ethereum mainnet
        max_gas_price = Decimal("1000")
        max_tx_cost = Decimal("100")

    return ChainConfig(
        chain_id=chain_id,
        name=name,
        display_name=display_name,
        rpc_endpoints=endpoints,
        block_time_seconds=block_time,
        confirmations_required=1,
        confirmation_timeout_seconds=120.0,
        max_gas_price_gwei=max_gas_price,
        max_transaction_cost_usd=max_tx_cost,
        is_testnet=is_testnet,
        native_token=native_token,
        explorer_url=explorer_url,
    )


def build_default_config() -> SardisChainConfig:
    """Build default configuration with all supported chains."""

    chains = {}

    # Base Sepolia (Primary Testnet)
    chains["base_sepolia"] = _build_chain_config(
        chain_id=84532,
        name="base_sepolia",
        display_name="Base Sepolia",
        default_rpc="https://sepolia.base.org",
        fallback_rpcs=[
            "https://base-sepolia-rpc.publicnode.com",
        ],
        block_time=2.0,
        native_token="ETH",
        explorer_url="https://sepolia.basescan.org",
        is_testnet=True,
    )

    # Base Mainnet
    chains["base"] = _build_chain_config(
        chain_id=8453,
        name="base",
        display_name="Base",
        default_rpc="https://mainnet.base.org",
        fallback_rpcs=[
            "https://base-mainnet.public.blastapi.io",
            "https://base.llamarpc.com",
        ],
        block_time=2.0,
        native_token="ETH",
        explorer_url="https://basescan.org",
    )

    # Polygon Amoy (Testnet)
    chains["polygon_amoy"] = _build_chain_config(
        chain_id=80002,
        name="polygon_amoy",
        display_name="Polygon Amoy",
        default_rpc="https://rpc-amoy.polygon.technology",
        fallback_rpcs=[],
        block_time=2.0,
        native_token="MATIC",
        explorer_url="https://amoy.polygonscan.com",
        is_testnet=True,
    )

    # Polygon Mainnet
    chains["polygon"] = _build_chain_config(
        chain_id=137,
        name="polygon",
        display_name="Polygon",
        default_rpc="https://polygon-rpc.com",
        fallback_rpcs=[
            "https://polygon-mainnet.public.blastapi.io",
            "https://polygon.llamarpc.com",
        ],
        block_time=2.0,
        native_token="MATIC",
        explorer_url="https://polygonscan.com",
    )

    # Ethereum Sepolia (Testnet)
    chains["ethereum_sepolia"] = _build_chain_config(
        chain_id=11155111,
        name="ethereum_sepolia",
        display_name="Ethereum Sepolia",
        default_rpc="https://rpc.sepolia.org",
        fallback_rpcs=[
            "https://ethereum-sepolia-rpc.publicnode.com",
        ],
        block_time=12.0,
        native_token="ETH",
        explorer_url="https://sepolia.etherscan.io",
        is_testnet=True,
    )

    # Ethereum Mainnet
    chains["ethereum"] = _build_chain_config(
        chain_id=1,
        name="ethereum",
        display_name="Ethereum",
        default_rpc="https://eth.llamarpc.com",
        fallback_rpcs=[
            "https://ethereum-rpc.publicnode.com",
            "https://eth.drpc.org",
        ],
        block_time=12.0,
        native_token="ETH",
        explorer_url="https://etherscan.io",
    )

    # Arbitrum Sepolia (Testnet)
    chains["arbitrum_sepolia"] = _build_chain_config(
        chain_id=421614,
        name="arbitrum_sepolia",
        display_name="Arbitrum Sepolia",
        default_rpc="https://sepolia-rollup.arbitrum.io/rpc",
        fallback_rpcs=[],
        block_time=1.0,
        native_token="ETH",
        explorer_url="https://sepolia.arbiscan.io",
        is_testnet=True,
    )

    # Arbitrum Mainnet
    chains["arbitrum"] = _build_chain_config(
        chain_id=42161,
        name="arbitrum",
        display_name="Arbitrum One",
        default_rpc="https://arb1.arbitrum.io/rpc",
        fallback_rpcs=[
            "https://arbitrum-one-rpc.publicnode.com",
            "https://arbitrum.llamarpc.com",
        ],
        block_time=1.0,
        native_token="ETH",
        explorer_url="https://arbiscan.io",
    )

    # Optimism Sepolia (Testnet)
    chains["optimism_sepolia"] = _build_chain_config(
        chain_id=11155420,
        name="optimism_sepolia",
        display_name="Optimism Sepolia",
        default_rpc="https://sepolia.optimism.io",
        fallback_rpcs=[],
        block_time=2.0,
        native_token="ETH",
        explorer_url="https://sepolia-optimism.etherscan.io",
        is_testnet=True,
    )

    # Optimism Mainnet
    chains["optimism"] = _build_chain_config(
        chain_id=10,
        name="optimism",
        display_name="Optimism",
        default_rpc="https://mainnet.optimism.io",
        fallback_rpcs=[
            "https://optimism-rpc.publicnode.com",
            "https://optimism.llamarpc.com",
        ],
        block_time=2.0,
        native_token="ETH",
        explorer_url="https://optimistic.etherscan.io",
    )

    return SardisChainConfig(
        chains=chains,
        default_chain=_get_env("DEFAULT_CHAIN", "base_sepolia"),
    )


# Global configuration instance
_global_config: Optional[SardisChainConfig] = None


def get_config() -> SardisChainConfig:
    """Get the global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = build_default_config()
    return _global_config


def set_config(config: SardisChainConfig) -> None:
    """Set the global configuration instance."""
    global _global_config
    _global_config = config


def get_chain_config(chain: str) -> ChainConfig:
    """Convenience function to get chain configuration."""
    return get_config().get_chain_config(chain)


# Export chain ID mapping for validation
CHAIN_ID_MAP: Dict[str, int] = {
    "ethereum": 1,
    "base": 8453,
    "polygon": 137,
    "arbitrum": 42161,
    "optimism": 10,
    "ethereum_sepolia": 11155111,
    "base_sepolia": 84532,
    "polygon_amoy": 80002,
    "arbitrum_sepolia": 421614,
    "optimism_sepolia": 11155420,
}


def validate_chain_id(chain: str, received_chain_id: int) -> bool:
    """
    Validate that the received chain ID matches expected.

    SECURITY: This prevents connecting to wrong networks which could
    result in loss of funds.
    """
    expected = CHAIN_ID_MAP.get(chain)
    if expected is None:
        logger.warning(f"Unknown chain for validation: {chain}")
        return False

    if received_chain_id != expected:
        logger.error(
            f"SECURITY: Chain ID mismatch for {chain}! "
            f"Expected {expected}, got {received_chain_id}. "
            f"This could indicate connecting to wrong network."
        )
        return False

    return True
