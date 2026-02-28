"""
Multi-chain stablecoin executor with MPC signing support.

Production-grade blockchain executor with:
- Multi-RPC endpoint support with automatic failover
- Chain ID validation on connection
- Transaction simulation before execution
- Comprehensive gas estimation with safety margins
- Nonce management with stuck transaction handling
- Block confirmation tracking with reorg detection
- Comprehensive logging for all operations
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import PaymentMandate
from sardis_ledger.records import ChainReceipt

# Import new production modules
from .config import (
    get_config,
    get_chain_config,
    validate_chain_id,
    SardisChainConfig,
    ChainConfig,
)
from .rpc_client import (
    ProductionRPCClient,
    get_rpc_client,
    ChainIDMismatchError,
    AllEndpointsFailedError,
)
from .nonce_manager import (
    NonceManager,
    get_nonce_manager,
    TransactionReceiptStatus,
    ReceiptValidation,
    TransactionFailedError,
    StuckTransactionError,
)
from .simulation import (
    TransactionSimulator,
    GasEstimator,
    SimulationAndEstimation,
    SimulationOutput,
    SimulationResult,
    GasEstimation,
    SimulationError,
    get_simulation_service,
)
from .confirmation import (
    ConfirmationTracker,
    get_confirmation_tracker,
    ConfirmationStatus,
    TrackedTransaction,
    ReorgEvent,
    ReorgError,
)
from .logging_utils import (
    ChainLogger,
    get_chain_logger,
    OperationType,
    setup_logging,
)
from .erc4337.bundler_client import BundlerClient, BundlerConfig
from .erc4337.paymaster_client import PaymasterClient, PaymasterConfig
from .erc4337.user_operation import UserOperation, zero_hex
from .erc4337.entrypoint import get_entrypoint_v07
from .erc4337.sponsor_caps import SponsorCapGuard
from .erc4337.proof_artifact import write_erc4337_proof_artifact

logger = logging.getLogger(__name__)


# Chain configurations
CHAIN_CONFIGS = {
    # Base
    "base_sepolia": {
        "chain_id": 84532,
        "rpc_url": "https://sepolia.base.org",
        "explorer": "https://sepolia.basescan.org",
        "native_token": "ETH",
        "block_time": 2,  # seconds
    },
    "base": {
        "chain_id": 8453,
        "rpc_url": "https://mainnet.base.org",
        "explorer": "https://basescan.org",
        "native_token": "ETH",
        "block_time": 2,
    },
    # Polygon
    "polygon_amoy": {
        "chain_id": 80002,
        "rpc_url": "https://rpc-amoy.polygon.technology",
        "explorer": "https://amoy.polygonscan.com",
        "native_token": "MATIC",
        "block_time": 2,
    },
    "polygon": {
        "chain_id": 137,
        "rpc_url": "https://polygon-rpc.com",
        "explorer": "https://polygonscan.com",
        "native_token": "MATIC",
        "block_time": 2,
    },
    # Ethereum
    "ethereum_sepolia": {
        "chain_id": 11155111,
        "rpc_url": "https://rpc.sepolia.org",
        "explorer": "https://sepolia.etherscan.io",
        "native_token": "ETH",
        "block_time": 12,
    },
    "ethereum": {
        "chain_id": 1,
        "rpc_url": "https://eth.llamarpc.com",
        "explorer": "https://etherscan.io",
        "native_token": "ETH",
        "block_time": 12,
    },
    # Arbitrum
    "arbitrum_sepolia": {
        "chain_id": 421614,
        "rpc_url": "https://sepolia-rollup.arbitrum.io/rpc",
        "explorer": "https://sepolia.arbiscan.io",
        "native_token": "ETH",
        "block_time": 1,
    },
    "arbitrum": {
        "chain_id": 42161,
        "rpc_url": "https://arb1.arbitrum.io/rpc",
        "explorer": "https://arbiscan.io",
        "native_token": "ETH",
        "block_time": 1,
    },
    # Optimism
    "optimism_sepolia": {
        "chain_id": 11155420,
        "rpc_url": "https://sepolia.optimism.io",
        "explorer": "https://sepolia-optimism.etherscan.io",
        "native_token": "ETH",
        "block_time": 2,
    },
    "optimism": {
        "chain_id": 10,
        "rpc_url": "https://mainnet.optimism.io",
        "explorer": "https://optimistic.etherscan.io",
        "native_token": "ETH",
        "block_time": 2,
    },
    # Solana (different architecture - requires separate handling)
    # NOTE: Solana support is EXPERIMENTAL and NOT YET IMPLEMENTED
    # Requires Anchor programs instead of Solidity contracts
    "solana_devnet": {
        "chain_id": 0,  # Solana doesn't use chain IDs like EVM
        "rpc_url": "https://api.devnet.solana.com",
        "explorer": "https://explorer.solana.com/?cluster=devnet",
        "native_token": "SOL",
        "block_time": 0.4,
        "is_solana": True,
        "experimental": True,
        "not_implemented": True,
    },
    "solana": {
        "chain_id": 0,
        "rpc_url": "https://api.mainnet-beta.solana.com",
        "explorer": "https://explorer.solana.com",
        "native_token": "SOL",
        "block_time": 0.4,
        "is_solana": True,
        "experimental": True,
        "not_implemented": True,
    },
}

# Stablecoin contract addresses by chain
STABLECOIN_ADDRESSES = {
    # Base
    "base_sepolia": {
        "USDC": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    },
    "base": {
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "EURC": "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42",
    },
    # Polygon
    "polygon_amoy": {
        "USDC": "0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582",
    },
    "polygon": {
        "USDC": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        "EURC": "0x9912af6da4F87Fc2b0Ae0B77A124e9B1B7Ba2F70",
    },
    # Ethereum
    "ethereum_sepolia": {
        "USDC": "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",
    },
    "ethereum": {
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "PYUSD": "0x6c3ea9036406852006290770BEdFcAbA0e23A0e8",
        "EURC": "0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c",
    },
    # Arbitrum
    "arbitrum_sepolia": {
        "USDC": "0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d",
    },
    "arbitrum": {
        "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        # NOTE: EURC not yet available on Arbitrum - will add when Circle deploys
    },
    # Optimism
    "optimism_sepolia": {
        "USDC": "0x5fd84259d66Cd46123540766Be93DFE6D43130D7",
    },
    "optimism": {
        "USDC": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        "USDT": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
    },
    # Solana (SPL token addresses - different format)
    "solana_devnet": {
        "USDC": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",  # Devnet USDC
    },
    "solana": {
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # Mainnet USDC
        "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # Mainnet USDT
        "PYUSD": "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo",  # PYUSD on Solana
    },
}

# Sardis contract addresses by chain (populated after deployment)
#
# Environment variable overrides (format: SARDIS_{CHAIN}_{CONTRACT}_ADDRESS)
# Example: SARDIS_BASE_WALLET_FACTORY_ADDRESS=0x...
#
# Deployment order (testnets first, then mainnets):
#   1. Base Sepolia (primary testnet)  -- DEPLOYED
#   2. Polygon Amoy, Ethereum Sepolia, Arbitrum Sepolia, Optimism Sepolia
#   3. Base mainnet (first production chain)
#   4. Polygon, Arbitrum, Optimism mainnets
#   5. Ethereum mainnet (highest gas, last)
#
# Mainnet deployment note:
#   Contracts are non-custodial (no funds held in contracts themselves).
#   The WalletFactory creates deterministic CREATE2 wallets and the Escrow
#   holds funds only during active agent-to-agent trades (time-bounded).
#   A formal audit is strongly recommended before mainnet deployment but
#   is not strictly required for non-custodial factory/registry contracts.
#   Set env var SARDIS_ALLOW_UNAUDITED_MAINNET=1 to deploy without audit.
SARDIS_CONTRACTS = {
    # Testnets
    "base_sepolia": {
        "wallet_factory": "0x0922f46cbDA32D93691FE8a8bD7271D24E53B3D7",
        "escrow": "0x5cf752B512FE6066a8fc2E6ce555c0C755aB5932",
        "agent_registry": "",
        "smart_account_factory": "",
    },
    "polygon_amoy": {
        "wallet_factory": "",
        "escrow": "",
        "agent_registry": "",
        "smart_account_factory": "",
    },
    "ethereum_sepolia": {
        "wallet_factory": "",
        "escrow": "",
        "agent_registry": "",
        "smart_account_factory": "",
    },
    "arbitrum_sepolia": {
        "wallet_factory": "",
        "escrow": "",
        "agent_registry": "",
        "smart_account_factory": "",
    },
    "optimism_sepolia": {
        "wallet_factory": "",
        "escrow": "",
        "agent_registry": "",
        "smart_account_factory": "",
    },
    # Mainnets - set addresses after deployment via env vars or here
    "base": {
        "wallet_factory": "",
        "escrow": "",
        "agent_registry": "",
        "smart_account_factory": "",
    },
    "polygon": {
        "wallet_factory": "",
        "escrow": "",
        "agent_registry": "",
        "smart_account_factory": "",
    },
    "ethereum": {
        "wallet_factory": "",
        "escrow": "",
        "agent_registry": "",
        "smart_account_factory": "",
    },
    "arbitrum": {
        "wallet_factory": "",
        "escrow": "",
        "agent_registry": "",
        "smart_account_factory": "",
    },
    "optimism": {
        "wallet_factory": "",
        "escrow": "",
        "agent_registry": "",
        "smart_account_factory": "",
    },
    # Solana - requires different contract architecture (Anchor programs)
    # NOTE: Solana integration is EXPERIMENTAL and NOT IMPLEMENTED
    "solana_devnet": {
        "wallet_program": "",
        "escrow_program": "",
        "experimental": True,
        "not_implemented": True,
    },
    "solana": {
        "wallet_program": "",
        "escrow_program": "",
        "experimental": True,
        "not_implemented": True,
    },
}


def get_sardis_contract_address(chain: str, contract_type: str) -> str:
    """
    Get Sardis contract address for a chain with environment variable override.

    Environment variables take precedence over hardcoded addresses.
    Format: SARDIS_{CHAIN}_{CONTRACT}_ADDRESS

    Args:
        chain: Chain name (e.g., "base_sepolia", "polygon_amoy")
        contract_type: Contract type ("wallet_factory" or "escrow")

    Returns:
        Contract address or empty string if not configured

    Raises:
        ValueError: If chain is Solana (not implemented)

    Example:
        >>> os.environ["SARDIS_BASE_SEPOLIA_WALLET_FACTORY_ADDRESS"] = "0x123..."
        >>> get_sardis_contract_address("base_sepolia", "wallet_factory")
        '0x123...'
    """
    chain_config = SARDIS_CONTRACTS.get(chain, {})

    # Check if chain is experimental/not implemented
    if chain_config.get("not_implemented"):
        raise ValueError(f"Chain {chain} is not yet implemented")

    # Build environment variable name
    # e.g., SARDIS_BASE_SEPOLIA_WALLET_FACTORY_ADDRESS
    env_key = f"SARDIS_{chain.upper()}_{contract_type.upper()}_ADDRESS"

    # Environment variable takes precedence
    env_address = os.getenv(env_key, "")
    if env_address:
        return env_address

    # Fall back to hardcoded address
    return chain_config.get(contract_type, "")


def get_sardis_wallet_factory(chain: str) -> str:
    """Get SardisWalletFactory address for a chain."""
    return get_sardis_contract_address(chain, "wallet_factory")


def get_sardis_escrow(chain: str) -> str:
    """Get SardisEscrow address for a chain."""
    return get_sardis_contract_address(chain, "escrow")


def is_chain_configured(chain: str) -> bool:
    """
    Check if a chain has Sardis contracts configured.

    Returns True if either:
    - Environment variables are set for the chain, OR
    - Hardcoded addresses are present in SARDIS_CONTRACTS
    """
    if chain not in SARDIS_CONTRACTS:
        return False

    chain_config = SARDIS_CONTRACTS[chain]

    # Check if not implemented
    if chain_config.get("not_implemented"):
        return False

    # Check for wallet_factory (required)
    wallet_factory = get_sardis_wallet_factory(chain)
    return bool(wallet_factory)


class TransactionStatus(str, Enum):
    """Transaction status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass
class SubmittedTx:
    """A submitted transaction."""
    tx_hash: str
    chain: str
    audit_anchor: str
    status: TransactionStatus = TransactionStatus.SUBMITTED
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GasEstimate:
    """Gas estimation result."""
    gas_limit: int
    gas_price_gwei: Decimal
    max_fee_gwei: Decimal
    max_priority_fee_gwei: Decimal
    estimated_cost_wei: int
    estimated_cost_usd: Optional[Decimal] = None


# ============================================================================
# Gas Price Protection Configuration
# ============================================================================

@dataclass
class GasPriceProtectionConfig:
    """
    Configuration for gas price spike protection.

    CRITICAL SECURITY: These limits protect against executing transactions
    during extreme gas price spikes that could result in significant
    unexpected costs.

    All values are in Gwei.
    """
    # Maximum allowed gas price (base fee + priority fee)
    # Default: 500 Gwei - protects against extreme spikes
    max_gas_price_gwei: Decimal = Decimal("500")

    # Maximum allowed priority fee (tip to miners/validators)
    # Default: 50 Gwei - prevents overpaying for priority
    max_priority_fee_gwei: Decimal = Decimal("50")

    # Maximum total transaction cost in USD
    # Default: $50 - prevents extremely expensive transactions
    max_transaction_cost_usd: Decimal = Decimal("50")

    # Chain-specific overrides (some chains have different gas economics)
    chain_overrides: Dict[str, Dict[str, Decimal]] = field(default_factory=lambda: {
        # Ethereum mainnet - allow higher due to higher typical gas prices
        "ethereum": {
            "max_gas_price_gwei": Decimal("1000"),
            "max_transaction_cost_usd": Decimal("100"),
        },
        # L2s typically have lower gas prices
        "base": {
            "max_gas_price_gwei": Decimal("100"),
            "max_transaction_cost_usd": Decimal("10"),
        },
        "optimism": {
            "max_gas_price_gwei": Decimal("100"),
            "max_transaction_cost_usd": Decimal("10"),
        },
        "arbitrum": {
            "max_gas_price_gwei": Decimal("100"),
            "max_transaction_cost_usd": Decimal("10"),
        },
        "polygon": {
            "max_gas_price_gwei": Decimal("1000"),  # MATIC can spike
            "max_transaction_cost_usd": Decimal("20"),
        },
        # Testnets - more lenient
        "base_sepolia": {
            "max_gas_price_gwei": Decimal("1000"),
            "max_transaction_cost_usd": Decimal("1000"),  # Test tokens
        },
        "ethereum_sepolia": {
            "max_gas_price_gwei": Decimal("1000"),
            "max_transaction_cost_usd": Decimal("1000"),
        },
        "polygon_amoy": {
            "max_gas_price_gwei": Decimal("1000"),
            "max_transaction_cost_usd": Decimal("1000"),
        },
        "arbitrum_sepolia": {
            "max_gas_price_gwei": Decimal("1000"),
            "max_transaction_cost_usd": Decimal("1000"),
        },
        "optimism_sepolia": {
            "max_gas_price_gwei": Decimal("1000"),
            "max_transaction_cost_usd": Decimal("1000"),
        },
    })

    # Grace period multiplier - allows slight overage before hard rejection
    # e.g., 1.1 means 10% grace over the limit triggers warning, not rejection
    grace_multiplier: Decimal = Decimal("1.1")

    # Enable automatic retry with lower gas after spike detection
    enable_retry_on_spike: bool = True

    # Delay before retry (seconds) - allows gas to settle
    retry_delay_seconds: int = 30

    # Maximum retries before giving up
    max_retries: int = 3

    def get_max_gas_price(self, chain: str) -> Decimal:
        """Get maximum gas price for a chain."""
        if chain in self.chain_overrides:
            return self.chain_overrides[chain].get(
                "max_gas_price_gwei", self.max_gas_price_gwei
            )
        return self.max_gas_price_gwei

    def get_max_priority_fee(self, chain: str) -> Decimal:
        """Get maximum priority fee for a chain."""
        if chain in self.chain_overrides:
            return self.chain_overrides[chain].get(
                "max_priority_fee_gwei", self.max_priority_fee_gwei
            )
        return self.max_priority_fee_gwei

    def get_max_transaction_cost(self, chain: str) -> Decimal:
        """Get maximum transaction cost for a chain."""
        if chain in self.chain_overrides:
            return self.chain_overrides[chain].get(
                "max_transaction_cost_usd", self.max_transaction_cost_usd
            )
        return self.max_transaction_cost_usd


class GasPriceSpikeError(Exception):
    """Raised when gas price exceeds configured limits."""

    def __init__(
        self,
        message: str,
        current_gas_price_gwei: Decimal,
        max_gas_price_gwei: Decimal,
        chain: str,
        is_retryable: bool = True,
    ):
        super().__init__(message)
        self.current_gas_price_gwei = current_gas_price_gwei
        self.max_gas_price_gwei = max_gas_price_gwei
        self.chain = chain
        self.is_retryable = is_retryable


class GasPriceProtection:
    """
    Gas price spike protection for blockchain transactions.

    SECURITY: This class prevents executing transactions during gas price
    spikes that could result in unexpectedly high costs.

    Features:
    - Configurable per-chain gas price limits
    - Priority fee limits to prevent overpaying for priority
    - Total transaction cost limits in USD
    - Automatic retry with delay when spikes are detected
    - Grace period to allow slight overages with warnings
    - Comprehensive logging for monitoring
    """

    def __init__(self, config: Optional[GasPriceProtectionConfig] = None):
        self.config = config or GasPriceProtectionConfig()
        from .price_oracle import get_price_oracle
        self._oracle = get_price_oracle()

    async def _get_eth_price_usd(self) -> Decimal:
        """Get current ETH price in USD via centralized price oracle."""
        return await self._oracle.get_price_usd("ETH")

    async def check_gas_price(
        self,
        gas_estimate: "GasEstimate",
        chain: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if gas price is within acceptable limits.

        Args:
            gas_estimate: Gas estimation from RPC
            chain: Target blockchain

        Returns:
            Tuple of (is_acceptable, warning_message)

        Raises:
            GasPriceSpikeError: If gas price exceeds hard limits
        """
        max_gas_price = self.config.get_max_gas_price(chain)
        max_priority_fee = self.config.get_max_priority_fee(chain)
        max_cost_usd = self.config.get_max_transaction_cost(chain)

        # Check gas price (max fee)
        if gas_estimate.max_fee_gwei > max_gas_price * self.config.grace_multiplier:
            logger.error(
                f"SECURITY: Gas price spike detected on {chain}! "
                f"Current: {gas_estimate.max_fee_gwei} Gwei, "
                f"Max allowed: {max_gas_price} Gwei"
            )
            raise GasPriceSpikeError(
                message=(
                    f"Gas price too high on {chain}: "
                    f"{gas_estimate.max_fee_gwei} Gwei exceeds limit of {max_gas_price} Gwei"
                ),
                current_gas_price_gwei=gas_estimate.max_fee_gwei,
                max_gas_price_gwei=max_gas_price,
                chain=chain,
                is_retryable=True,
            )

        # Check priority fee
        if gas_estimate.max_priority_fee_gwei > max_priority_fee * self.config.grace_multiplier:
            logger.error(
                f"SECURITY: Priority fee spike detected on {chain}! "
                f"Current: {gas_estimate.max_priority_fee_gwei} Gwei, "
                f"Max allowed: {max_priority_fee} Gwei"
            )
            raise GasPriceSpikeError(
                message=(
                    f"Priority fee too high on {chain}: "
                    f"{gas_estimate.max_priority_fee_gwei} Gwei exceeds limit of {max_priority_fee} Gwei"
                ),
                current_gas_price_gwei=gas_estimate.max_priority_fee_gwei,
                max_gas_price_gwei=max_priority_fee,
                chain=chain,
                is_retryable=True,
            )

        # Calculate and check total cost in USD
        eth_price = await self._get_eth_price_usd()
        cost_eth = Decimal(gas_estimate.estimated_cost_wei) / Decimal(10**18)
        cost_usd = cost_eth * eth_price

        if cost_usd > max_cost_usd * self.config.grace_multiplier:
            logger.error(
                f"SECURITY: Transaction cost too high on {chain}! "
                f"Estimated: ${cost_usd:.2f}, Max allowed: ${max_cost_usd}"
            )
            raise GasPriceSpikeError(
                message=(
                    f"Transaction cost too high on {chain}: "
                    f"${cost_usd:.2f} exceeds limit of ${max_cost_usd}"
                ),
                current_gas_price_gwei=gas_estimate.max_fee_gwei,
                max_gas_price_gwei=max_gas_price,
                chain=chain,
                is_retryable=True,
            )

        # Generate warnings for values approaching limits
        warnings = []

        if gas_estimate.max_fee_gwei > max_gas_price:
            warnings.append(
                f"Gas price ({gas_estimate.max_fee_gwei} Gwei) is above normal limit "
                f"({max_gas_price} Gwei) but within grace period"
            )

        if gas_estimate.max_priority_fee_gwei > max_priority_fee:
            warnings.append(
                f"Priority fee ({gas_estimate.max_priority_fee_gwei} Gwei) is above normal limit "
                f"({max_priority_fee} Gwei) but within grace period"
            )

        if cost_usd > max_cost_usd:
            warnings.append(
                f"Transaction cost (${cost_usd:.2f}) is above normal limit "
                f"(${max_cost_usd}) but within grace period"
            )

        warning_message = "; ".join(warnings) if warnings else None
        if warning_message:
            logger.warning(f"Gas price warning on {chain}: {warning_message}")

        return True, warning_message

    def cap_gas_price(
        self,
        gas_estimate: "GasEstimate",
        chain: str,
    ) -> "GasEstimate":
        """
        Cap gas price to maximum allowed values.

        Use this to automatically adjust gas prices to stay within limits
        rather than failing the transaction.

        Args:
            gas_estimate: Original gas estimation
            chain: Target blockchain

        Returns:
            New GasEstimate with capped values
        """
        max_gas_price = self.config.get_max_gas_price(chain)
        max_priority_fee = self.config.get_max_priority_fee(chain)

        capped_max_fee = min(gas_estimate.max_fee_gwei, max_gas_price)
        capped_priority_fee = min(gas_estimate.max_priority_fee_gwei, max_priority_fee)

        # Recalculate estimated cost with capped values
        capped_max_fee_wei = int(capped_max_fee * Decimal(10**9))
        capped_cost = gas_estimate.gas_limit * capped_max_fee_wei

        if capped_max_fee < gas_estimate.max_fee_gwei:
            logger.info(
                f"Capped max fee from {gas_estimate.max_fee_gwei} to {capped_max_fee} Gwei on {chain}"
            )

        if capped_priority_fee < gas_estimate.max_priority_fee_gwei:
            logger.info(
                f"Capped priority fee from {gas_estimate.max_priority_fee_gwei} to {capped_priority_fee} Gwei on {chain}"
            )

        return GasEstimate(
            gas_limit=gas_estimate.gas_limit,
            gas_price_gwei=min(gas_estimate.gas_price_gwei, max_gas_price),
            max_fee_gwei=capped_max_fee,
            max_priority_fee_gwei=capped_priority_fee,
            estimated_cost_wei=capped_cost,
            estimated_cost_usd=gas_estimate.estimated_cost_usd,
        )


# Global gas price protection instance
_gas_price_protection: Optional[GasPriceProtection] = None


def get_gas_price_protection() -> GasPriceProtection:
    """Get or create the global gas price protection instance."""
    global _gas_price_protection
    if _gas_price_protection is None:
        _gas_price_protection = GasPriceProtection()
    return _gas_price_protection


@dataclass
class TransactionRequest:
    """A transaction to be signed and submitted."""
    chain: str
    to_address: str
    value: int = 0  # Native token value in wei
    data: bytes = b""
    gas_limit: Optional[int] = None
    max_fee_per_gas: Optional[int] = None
    max_priority_fee_per_gas: Optional[int] = None
    nonce: Optional[int] = None


class MPCSignerPort(ABC):
    """Abstract interface for MPC signing providers."""

    @abstractmethod
    async def sign_transaction(
        self,
        wallet_id: str,
        tx: TransactionRequest,
    ) -> str:
        """Sign a transaction and return the signed tx hex."""
        pass

    @abstractmethod
    async def get_address(self, wallet_id: str, chain: str) -> str:
        """Get the wallet address for a chain."""
        pass

    @abstractmethod
    async def sign_user_operation_hash(self, wallet_id: str, user_op_hash: str) -> str:
        """Sign an ERC-4337 UserOperation hash and return hex signature."""
        pass


class SimulatedMPCSigner(MPCSignerPort):
    """Simulated MPC signer for development."""

    def __init__(self):
        self._wallets: Dict[str, str] = {}

    async def sign_transaction(
        self,
        wallet_id: str,
        tx: TransactionRequest,
    ) -> str:
        """Simulate signing - returns a mock signed transaction."""
        # In simulation, we just return a mock tx hash
        return "0x" + secrets.token_hex(32)

    async def get_address(self, wallet_id: str, chain: str) -> str:
        """Get or generate a simulated address."""
        key = f"{wallet_id}:{chain}"
        if key not in self._wallets:
            self._wallets[key] = "0x" + secrets.token_hex(20)
        return self._wallets[key]

    async def sign_user_operation_hash(self, wallet_id: str, user_op_hash: str) -> str:  # noqa: ARG002
        """Return a deterministic-length mock signature for simulated runs."""
        return "0x" + secrets.token_hex(65)


class FailoverMPCSigner(MPCSignerPort):
    """MPC signer with automatic failover between primary and backup providers.

    Tries the primary signer first. On failure, falls back to the backup signer.
    Tracks consecutive failures and can switch the active primary.
    """

    FAILURE_THRESHOLD = 3  # Switch primary after this many consecutive failures

    def __init__(
        self,
        primary: MPCSignerPort,
        backup: MPCSignerPort,
        *,
        primary_name: str = "primary",
        backup_name: str = "backup",
    ):
        self._primary = primary
        self._backup = backup
        self._primary_name = primary_name
        self._backup_name = backup_name
        self._consecutive_primary_failures = 0
        self._swapped = False

    @property
    def _active(self) -> MPCSignerPort:
        return self._backup if self._swapped else self._primary

    @property
    def _fallback(self) -> MPCSignerPort:
        return self._primary if self._swapped else self._backup

    @property
    def _active_name(self) -> str:
        return self._backup_name if self._swapped else self._primary_name

    @property
    def _fallback_name(self) -> str:
        return self._primary_name if self._swapped else self._backup_name

    def _record_failure(self) -> None:
        self._consecutive_primary_failures += 1
        if self._consecutive_primary_failures >= self.FAILURE_THRESHOLD:
            logger.warning(
                "MPC signer %s hit %d consecutive failures, swapping to %s",
                self._active_name,
                self._consecutive_primary_failures,
                self._fallback_name,
            )
            self._swapped = not self._swapped
            self._consecutive_primary_failures = 0

    def _record_success(self) -> None:
        self._consecutive_primary_failures = 0

    async def sign_transaction(self, wallet_id: str, tx: TransactionRequest) -> str:
        try:
            result = await self._active.sign_transaction(wallet_id, tx)
            self._record_success()
            return result
        except Exception as primary_err:
            logger.warning(
                "MPC %s sign_transaction failed: %s, trying %s",
                self._active_name, primary_err, self._fallback_name,
            )
            self._record_failure()
            try:
                return await self._fallback.sign_transaction(wallet_id, tx)
            except Exception as backup_err:
                raise Exception(
                    f"Both MPC signers failed: {self._active_name}={primary_err}, "
                    f"{self._fallback_name}={backup_err}"
                ) from backup_err

    async def get_address(self, wallet_id: str, chain: str) -> str:
        try:
            result = await self._active.get_address(wallet_id, chain)
            self._record_success()
            return result
        except Exception as primary_err:
            logger.warning(
                "MPC %s get_address failed: %s, trying %s",
                self._active_name, primary_err, self._fallback_name,
            )
            self._record_failure()
            try:
                return await self._fallback.get_address(wallet_id, chain)
            except Exception as backup_err:
                raise Exception(
                    f"Both MPC signers failed: {self._active_name}={primary_err}, "
                    f"{self._fallback_name}={backup_err}"
                ) from backup_err

    async def sign_user_operation_hash(self, wallet_id: str, user_op_hash: str) -> str:
        try:
            result = await self._active.sign_user_operation_hash(wallet_id, user_op_hash)
            self._record_success()
            return result
        except Exception as primary_err:
            logger.warning(
                "MPC %s sign_user_operation_hash failed: %s, trying %s",
                self._active_name, primary_err, self._fallback_name,
            )
            self._record_failure()
            try:
                return await self._fallback.sign_user_operation_hash(wallet_id, user_op_hash)
            except Exception as backup_err:
                raise Exception(
                    f"Both MPC signers failed: {self._active_name}={primary_err}, "
                    f"{self._fallback_name}={backup_err}"
                ) from backup_err


class TurnkeyMPCSigner(MPCSignerPort):
    """
    Turnkey MPC signing integration delegating to the canonical TurnkeyClient.

    Accepts a ``TurnkeyClient`` from sardis-wallet which owns the single HTTP
    connection and P-256 stamp authentication.  This class adds chain-specific
    logic: EIP-1559 RLP encoding, activity polling, and address resolution.
    """

    # Activity polling configuration
    ACTIVITY_POLL_INTERVAL = 0.5  # seconds
    ACTIVITY_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    def __init__(self, turnkey_client):
        """
        Args:
            turnkey_client: A ``TurnkeyClient`` instance from sardis-wallet.
        """
        self._client = turnkey_client
        self._org_id = turnkey_client.organization_id

    async def _make_request(
        self,
        method: str,
        path: str,
        body: Dict[str, Any],
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """Make an API request via the shared TurnkeyClient with retry logic."""
        try:
            return await self._client.post(path, body)
        except Exception as e:
            if retry_count < self.MAX_RETRIES:
                logger.warning(f"Turnkey request failed (attempt {retry_count + 1}): {e}")
                await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                return await self._make_request(method, path, body, retry_count + 1)
            raise

    async def _poll_activity(self, activity_id: str) -> Dict[str, Any]:
        """Poll for activity completion."""
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < self.ACTIVITY_TIMEOUT:
            result = await self._make_request(
                "POST",
                "/public/v1/query/get_activity",
                {
                    "organizationId": self._org_id,
                    "activityId": activity_id,
                },
            )
            
            activity = result.get("activity", {})
            status = activity.get("status", "")
            
            if status == "ACTIVITY_STATUS_COMPLETED":
                return activity
            elif status == "ACTIVITY_STATUS_FAILED":
                failure_reason = activity.get("result", {}).get("failureReason", "Unknown")
                raise Exception(f"Turnkey activity failed: {failure_reason}")
            elif status == "ACTIVITY_STATUS_REJECTED":
                raise Exception("Turnkey activity was rejected")
            
            await asyncio.sleep(self.ACTIVITY_POLL_INTERVAL)
        
        raise TimeoutError(f"Turnkey activity {activity_id} timed out")

    async def sign_transaction(
        self,
        wallet_id: str,
        tx: TransactionRequest,
    ) -> str:
        """Sign transaction via Turnkey API.
        
        Turnkey expects unsigned transaction as RLP-encoded hex string.
        """
        import rlp
        
        chain_config = CHAIN_CONFIGS.get(tx.chain, {})
        chain_id = chain_config.get("chain_id", 1)
        
        # Build EIP-1559 transaction (Type 2)
        # Format: 0x02 || rlp([chainId, nonce, maxPriorityFeePerGas, maxFeePerGas, gasLimit, to, value, data, accessList])
        nonce = tx.nonce if tx.nonce is not None else 0
        max_priority_fee = tx.max_priority_fee_per_gas or 1_000_000_000  # 1 gwei
        max_fee = tx.max_fee_per_gas or 50_000_000_000  # 50 gwei
        gas_limit = tx.gas_limit or 100000
        to_address = bytes.fromhex(tx.to_address[2:]) if tx.to_address.startswith("0x") else bytes.fromhex(tx.to_address)
        value = tx.value
        data = tx.data or b""
        access_list = []  # Empty access list for now
        
        # RLP encode the transaction fields (without signature)
        tx_fields = [
            chain_id,
            nonce,
            max_priority_fee,
            max_fee,
            gas_limit,
            to_address,
            value,
            data,
            access_list,
        ]
        
        # Encode with EIP-1559 type prefix
        rlp_encoded = rlp.encode(tx_fields)
        unsigned_tx_hex = "02" + rlp_encoded.hex()  # 0x02 prefix for EIP-1559
        
        # Turnkey expects signWith to identify the signing account.
        # For EVM wallets, this is typically the Ethereum address.
        sign_with = wallet_id
        try:
            addr = await self.get_address(wallet_id, tx.chain)
            if isinstance(addr, str) and addr.startswith("0x") and len(addr) == 42:
                sign_with = addr
        except Exception:
            # Fall back to the wallet_id if address lookup fails
            pass

        # Create sign transaction activity
        activity_body = {
            "type": "ACTIVITY_TYPE_SIGN_TRANSACTION_V2",
            "organizationId": self._org_id,
            "timestampMs": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
            "parameters": {
                "signWith": sign_with,
                "type": "TRANSACTION_TYPE_ETHEREUM",
                "unsignedTransaction": unsigned_tx_hex,
            },
        }
        
        logger.info(f"Submitting sign transaction activity for wallet {wallet_id}")
        
        # Submit the activity
        result = await self._make_request(
            "POST",
            "/public/v1/submit/sign_transaction",
            activity_body,
        )
        
        activity = result.get("activity", {})
        activity_id = activity.get("id", "")
        status = activity.get("status", "")
        
        # If not immediately completed, poll for completion
        if status != "ACTIVITY_STATUS_COMPLETED":
            logger.info(f"Polling for activity {activity_id} completion")
            activity = await self._poll_activity(activity_id)
        
        # Extract signed transaction (Turnkey returns in signTransactionResult)
        sign_result = activity.get("result", {}).get("signTransactionResult", {})
        signed_tx = sign_result.get("signedTransaction", "")
        
        if not signed_tx:
            # Fallback to old path
            signed_tx = activity.get("result", {}).get("signedTransaction", "")
        
        if not signed_tx:
            raise Exception("No signed transaction returned from Turnkey")
        
        logger.info(f"Transaction signed successfully")
        return signed_tx

    @staticmethod
    def _normalize_signature_hex(value: str) -> str:
        sig = value.strip()
        if not sig:
            return ""
        if not sig.startswith("0x"):
            sig = f"0x{sig}"
        return sig.lower()

    @classmethod
    def _extract_userop_signature(cls, activity: Dict[str, Any]) -> str:
        result = activity.get("result", {}) if isinstance(activity, dict) else {}
        sign_raw = (
            result.get("signRawPayloadResult")
            or result.get("signRawPayload")
            or {}
        )
        if not isinstance(sign_raw, dict):
            sign_raw = {}

        for key in ("signature", "fullSignature", "fullSig"):
            value = sign_raw.get(key) or result.get(key)
            if isinstance(value, str) and value.strip():
                return cls._normalize_signature_hex(value)

        r = sign_raw.get("r")
        s = sign_raw.get("s")
        v = sign_raw.get("v")
        if isinstance(r, str) and isinstance(s, str) and v is not None:
            r_hex = r.removeprefix("0x").zfill(64)
            s_hex = s.removeprefix("0x").zfill(64)
            if isinstance(v, str):
                try:
                    v_int = int(v, 16) if v.startswith("0x") else int(v)
                except ValueError:
                    return ""
            else:
                v_int = int(v)
            if v_int < 27:
                v_int += 27
            return f"0x{r_hex}{s_hex}{v_int:02x}"

        return ""

    async def sign_user_operation_hash(self, wallet_id: str, user_op_hash: str) -> str:
        """Sign ERC-4337 UserOperation hash with Turnkey raw-payload signing."""
        payload_hex = user_op_hash if user_op_hash.startswith("0x") else f"0x{user_op_hash}"
        sign_with = wallet_id
        try:
            address = await self.get_address(wallet_id, "base_sepolia")
            if isinstance(address, str) and address.startswith("0x") and len(address) == 42:
                sign_with = address
        except Exception:
            pass

        activity_body = {
            "type": "ACTIVITY_TYPE_SIGN_RAW_PAYLOAD_V2",
            "organizationId": self._org_id,
            "timestampMs": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
            "parameters": {
                "signWith": sign_with,
                "payload": payload_hex,
                "encoding": "PAYLOAD_ENCODING_HEXADECIMAL",
                "hashFunction": "HASH_FUNCTION_NO_OP",
            },
        }
        result = await self._make_request(
            "POST",
            "/public/v1/submit/sign_raw_payload",
            activity_body,
        )

        activity = result.get("activity", {})
        activity_id = activity.get("id", "")
        status = activity.get("status", "")
        if status != "ACTIVITY_STATUS_COMPLETED" and activity_id:
            activity = await self._poll_activity(activity_id)

        signature = self._extract_userop_signature(activity)
        if not signature:
            raise RuntimeError("Turnkey did not return a usable UserOperation signature")
        return signature

    async def get_address(self, wallet_id: str, chain: str) -> str:
        """Get wallet address from Turnkey."""
        result = await self._make_request(
            "POST",
            "/public/v1/query/list_wallet_accounts",
            {
                "organizationId": self._org_id,
                "walletId": wallet_id,
            },
        )
        
        # Extract address from accounts list
        accounts = result.get("accounts", [])
        for account in accounts:
            address_format = account.get("addressFormat", "")
            if address_format == "ADDRESS_FORMAT_ETHEREUM":
                return account.get("address", "")
        
        raise ValueError(f"No Ethereum address found for wallet {wallet_id}")

    async def create_wallet(self, wallet_name: str) -> Dict[str, str]:
        """
        Create a new wallet in Turnkey.
        
        Returns:
            Dict with 'wallet_id' and 'address' keys
        """
        activity_body = {
            "type": "ACTIVITY_TYPE_CREATE_WALLET",
            "organizationId": self._org_id,
            "timestampMs": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
            "parameters": {
                "walletName": wallet_name,
                "accounts": [
                    {
                        "curve": "CURVE_SECP256K1",
                        "pathFormat": "PATH_FORMAT_BIP32",
                        "path": "m/44'/60'/0'/0/0",
                        "addressFormat": "ADDRESS_FORMAT_ETHEREUM",
                    }
                ],
            },
        }
        
        logger.info(f"Creating new Turnkey wallet: {wallet_name}")
        
        result = await self._make_request(
            "POST",
            "/public/v1/submit/create_wallet",
            activity_body,
        )
        
        activity = result.get("activity", {})
        activity_id = activity.get("id", "")
        status = activity.get("status", "")
        
        if status != "ACTIVITY_STATUS_COMPLETED":
            activity = await self._poll_activity(activity_id)
        
        wallet_result = activity.get("result", {}).get("createWalletResult", {})
        wallet_id = wallet_result.get("walletId", "")
        addresses = wallet_result.get("addresses", [])
        
        address = addresses[0] if addresses else ""
        
        logger.info(f"Created wallet {wallet_id} with address {address}")
        
        return {
            "wallet_id": wallet_id,
            "address": address,
        }

    async def list_wallets(self) -> List[Dict[str, Any]]:
        """List all wallets in the organization."""
        result = await self._make_request(
            "POST",
            "/public/v1/query/list_wallets",
            {
                "organizationId": self._org_id,
            },
        )
        
        return result.get("wallets", [])

    async def close(self):
        """Close HTTP client."""
        client_close = getattr(self._client, "close", None)
        if callable(client_close):
            maybe_awaitable = client_close()
            if asyncio.iscoroutine(maybe_awaitable):
                await maybe_awaitable


class LocalAccountSigner(MPCSignerPort):
    """Local EOA signer for MVP/demo without MPC."""

    def __init__(self, private_key: str, address: str | None = None):
        import os
        from web3 import Web3
        from eth_account import Account

        if not private_key:
            raise ValueError("SARDIS_EOA_PRIVATE_KEY is required for local signer")

        # Warn if used in production environment
        if os.getenv("SARDIS_ENV") == "production":
            logger.warning(
                "LocalAccountSigner stores private keys in memory. "
                "Use TurnkeySigner for production."
            )

        self._w3 = Web3()
        self._account = Account.from_key(private_key)
        self._address = address or self._account.address

    async def sign_transaction(self, wallet_id: str, tx: TransactionRequest) -> str:
        tx_dict = {
            "to": tx.to_address,
            "value": tx.value,
            "data": tx.data if isinstance(tx.data, bytes) else bytes(tx.data or b""),
            "gas": tx.gas_limit or 120000,
            "maxFeePerGas": tx.max_fee_per_gas or 50_000_000_000,
            "maxPriorityFeePerGas": tx.max_priority_fee_per_gas or 1_000_000_000,
            "nonce": tx.nonce or 0,
            "chainId": CHAIN_CONFIGS.get(tx.chain, {}).get("chain_id", 84532),
            "type": 2,
        }
        signed = self._w3.eth.account.sign_transaction(tx_dict, self._account.key)
        return signed.rawTransaction.hex()

    async def get_address(self, wallet_id: str, chain: str) -> str:  # noqa: ARG002
        return self._address

    async def sign_user_operation_hash(self, wallet_id: str, user_op_hash: str) -> str:  # noqa: ARG002
        from eth_account.messages import encode_defunct

        message = encode_defunct(hexstr=user_op_hash)
        signed = self._account.sign_message(message)
        return signed.signature.hex()


@dataclass
class RPCEndpoint:
    """An RPC endpoint with health tracking."""
    url: str
    priority: int = 0  # Lower is higher priority
    healthy: bool = True
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    failure_count: int = 0
    latency_ms: float = 0.0
    
    # Health thresholds
    MAX_FAILURES = 3
    HEALTH_CHECK_INTERVAL = 60  # seconds
    
    def mark_success(self, latency_ms: float) -> None:
        """Mark endpoint as healthy after successful call."""
        self.healthy = True
        self.failure_count = 0
        self.latency_ms = latency_ms
        self.last_check = datetime.now(timezone.utc)
    
    def mark_failure(self) -> None:
        """Mark endpoint as potentially unhealthy after failure."""
        self.failure_count += 1
        if self.failure_count >= self.MAX_FAILURES:
            self.healthy = False
        self.last_check = datetime.now(timezone.utc)
    
    def needs_health_check(self) -> bool:
        """Check if this endpoint needs a health check."""
        if self.healthy:
            return False
        elapsed = (datetime.now(timezone.utc) - self.last_check).total_seconds()
        return elapsed >= self.HEALTH_CHECK_INTERVAL


# Additional fallback RPC URLs for each chain
FALLBACK_RPC_URLS = {
    "base_sepolia": [
        "https://sepolia.base.org",
        "https://base-sepolia-rpc.publicnode.com",
    ],
    "base": [
        "https://mainnet.base.org",
        "https://base-mainnet.public.blastapi.io",
    ],
    "polygon": [
        "https://polygon-rpc.com",
        "https://polygon-mainnet.public.blastapi.io",
    ],
    "polygon_amoy": [
        "https://rpc-amoy.polygon.technology",
    ],
    "ethereum": [
        "https://eth.llamarpc.com",
        "https://ethereum-rpc.publicnode.com",
    ],
    "ethereum_sepolia": [
        "https://rpc.sepolia.org",
        "https://ethereum-sepolia-rpc.publicnode.com",
    ],
    "arbitrum": [
        "https://arb1.arbitrum.io/rpc",
        "https://arbitrum-one-rpc.publicnode.com",
    ],
    "arbitrum_sepolia": [
        "https://sepolia-rollup.arbitrum.io/rpc",
    ],
    "optimism": [
        "https://mainnet.optimism.io",
        "https://optimism-rpc.publicnode.com",
    ],
    "optimism_sepolia": [
        "https://sepolia.optimism.io",
    ],
}


class ChainRPCClient:
    """
    JSON-RPC client with fallback RPC providers and health checking.
    
    Features:
    - Multiple RPC endpoints per chain
    - Automatic failover on errors
    - Health-based endpoint selection
    - Latency-based prioritization
    """

    def __init__(self, rpc_url: str, chain: str = ""):
        self._chain = chain
        self._request_id = 0
        self._http_client = None
        
        # Initialize endpoints with primary and fallbacks
        self._endpoints: List[RPCEndpoint] = [
            RPCEndpoint(url=rpc_url, priority=0)
        ]
        
        # Add fallback endpoints
        if chain in FALLBACK_RPC_URLS:
            for i, url in enumerate(FALLBACK_RPC_URLS[chain]):
                if url != rpc_url:  # Don't duplicate primary
                    self._endpoints.append(RPCEndpoint(url=url, priority=i + 1))

    async def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=30)
        return self._http_client
    
    def _get_healthy_endpoint(self) -> RPCEndpoint:
        """Get the best healthy endpoint based on priority and latency."""
        healthy = [e for e in self._endpoints if e.healthy]
        if not healthy:
            # All unhealthy, return lowest priority one and hope for the best
            return min(self._endpoints, key=lambda e: e.priority)
        
        # Sort by priority, then by latency
        return min(healthy, key=lambda e: (e.priority, e.latency_ms))

    async def _call(self, method: str, params: List[Any] = None) -> Any:
        """Make JSON-RPC call with automatic failover."""
        import time
        
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or [],
        }
        
        # Try endpoints in order of health/priority
        last_error = None
        tried_endpoints = set()
        
        for attempt in range(len(self._endpoints)):
            endpoint = self._get_healthy_endpoint()
            
            # Skip if we've already tried this endpoint
            if endpoint.url in tried_endpoints:
                # Try any untried endpoint
                untried = [e for e in self._endpoints if e.url not in tried_endpoints]
                if not untried:
                    break
                endpoint = untried[0]
            
            tried_endpoints.add(endpoint.url)
            
            try:
                client = await self._get_client()
                start_time = time.time()
                
                response = await client.post(
                    endpoint.url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                
                latency_ms = (time.time() - start_time) * 1000
                response.raise_for_status()
                result = response.json()
                
                if "error" in result:
                    endpoint.mark_failure()
                    last_error = Exception(f"RPC error: {result['error']}")
                    continue
                
                # Success!
                endpoint.mark_success(latency_ms)
                return result.get("result")
                
            except Exception as e:
                endpoint.mark_failure()
                last_error = e
                logger.warning(f"RPC call to {endpoint.url} failed: {e}")
                continue
        
        # All endpoints failed
        raise last_error or Exception("All RPC endpoints failed")
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all endpoints."""
        results = {}
        
        for endpoint in self._endpoints:
            try:
                # Simple block number check
                await self._call_endpoint(endpoint, "eth_blockNumber", [])
                endpoint.healthy = True
                endpoint.failure_count = 0
                results[endpoint.url] = True
            except Exception:
                endpoint.healthy = False
                results[endpoint.url] = False
        
        return results
    
    async def _call_endpoint(self, endpoint: RPCEndpoint, method: str, params: List[Any]) -> Any:
        """Make a call to a specific endpoint."""
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }
        
        client = await self._get_client()
        response = await client.post(
            endpoint.url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        result = response.json()
        
        if "error" in result:
            raise Exception(f"RPC error: {result['error']}")
        
        return result.get("result")
    
    def get_endpoint_stats(self) -> List[Dict[str, Any]]:
        """Get stats for all endpoints."""
        return [
            {
                "url": e.url,
                "priority": e.priority,
                "healthy": e.healthy,
                "failure_count": e.failure_count,
                "latency_ms": e.latency_ms,
            }
            for e in self._endpoints
        ]

    async def get_gas_price(self) -> int:
        """Get current gas price in wei."""
        result = await self._call("eth_gasPrice")
        return int(result, 16)

    async def get_max_priority_fee(self) -> int:
        """Get max priority fee for EIP-1559."""
        try:
            result = await self._call("eth_maxPriorityFeePerGas")
            return int(result, 16)
        except Exception:
            # Fallback for chains that don't support this
            return 1_000_000_000  # 1 gwei

    async def estimate_gas(self, tx: Dict[str, Any]) -> int:
        """Estimate gas for a transaction."""
        result = await self._call("eth_estimateGas", [tx])
        return int(result, 16)

    async def get_nonce(self, address: str) -> int:
        """Get transaction count (nonce) for address."""
        result = await self._call("eth_getTransactionCount", [address, "pending"])
        return int(result, 16)

    async def get_balance(self, address: str) -> int:
        """Get ETH balance for address in wei."""
        result = await self._call("eth_getBalance", [address, "latest"])
        return int(result, 16)

    async def send_raw_transaction(self, signed_tx: str) -> str:
        """Broadcast signed transaction."""
        # Ensure hex prefix
        if not signed_tx.startswith("0x"):
            signed_tx = "0x" + signed_tx
        result = await self._call("eth_sendRawTransaction", [signed_tx])
        return result

    # Alias for backwards compatibility
    async def broadcast_transaction(self, signed_tx: str) -> str:
        """Broadcast signed transaction (alias for send_raw_transaction)."""
        return await self.send_raw_transaction(signed_tx)

    async def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction receipt."""
        return await self._call("eth_getTransactionReceipt", [tx_hash])

    async def get_block_number(self) -> int:
        """Get current block number."""
        result = await self._call("eth_blockNumber")
        return int(result, 16)

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


def encode_erc20_transfer(to_address: str, amount: int) -> bytes:
    """Encode ERC20 transfer function call."""
    # transfer(address,uint256) selector: 0xa9059cbb
    selector = bytes.fromhex("a9059cbb")
    
    # Pad address to 32 bytes
    to_bytes = bytes.fromhex(to_address[2:].lower().zfill(64))
    
    # Pad amount to 32 bytes
    amount_bytes = amount.to_bytes(32, "big")
    
    return selector + to_bytes + amount_bytes


class ChainExecutor:
    """
    Production-ready chain executor with MPC signing support.

    Features:
    - Multi-chain support (Base, Polygon, Ethereum, Arbitrum, Optimism)
    - MPC signing via Turnkey or Fireblocks
    - Multi-RPC endpoint support with automatic failover
    - Chain ID validation on connection (security)
    - Transaction simulation before execution
    - Comprehensive gas estimation with EIP-1559 support and safety margins
    - Nonce management with stuck transaction handling
    - Transaction receipt status verification
    - Block confirmation tracking with reorg detection
    - Simulated mode for development
    - Pre-execution compliance checks (fail-closed)
    - Gas price spike protection (prevents high-cost transactions)
    - Comprehensive logging for all blockchain operations

    SECURITY FEATURES:
    - Chain ID validation prevents connecting to wrong networks
    - Transaction simulation prevents executing failing transactions
    - Receipt verification ensures transaction success on-chain
    - Reorg detection identifies and handles chain reorganizations
    - Nonce management prevents double-spend and stuck transactions
    """

    # Confirmation requirements per chain
    CHAIN_CONFIRMATIONS = {
        "ethereum": 12,
        "base": 3,
        "base_sepolia": 3,
        "polygon": 10,
        "polygon_amoy": 10,
        "arbitrum": 3,
        "optimism": 3,
    }
    CONFIRMATION_TIMEOUT = 120  # seconds
    POLL_INTERVAL = 2  # seconds

    @classmethod
    def get_confirmations_required(cls, chain: str) -> int:
        """Get required confirmations for a chain (safe default: 12)."""
        return cls.CHAIN_CONFIRMATIONS.get(chain.lower(), 12)

    def __init__(self, settings: SardisSettings, turnkey_client=None):
        self._settings = settings
        self._simulated = settings.chain_mode == "simulated"
        self._turnkey_client = turnkey_client
        self._erc4337_enabled = bool(settings.erc4337_enabled)
        self._erc4337_chain_allowlist = settings.erc4337_chain_allowlist_set
        self._erc4337_entrypoint = settings.erc4337_entrypoint_v07_address or get_entrypoint_v07("base_sepolia")

        # Production-grade RPC clients with failover
        self._rpc_clients: Dict[str, ProductionRPCClient] = {}

        # Legacy ChainRPCClient support (for backward compatibility)
        self._legacy_rpc_clients: Dict[str, ChainRPCClient] = {}

        # MPC signer
        self._mpc_signer: Optional[MPCSignerPort] = None

        # Compliance services (fail-closed: None means block all)
        self._compliance_engine = None
        self._sanctions_service = None
        self._init_compliance()

        # Gas price protection (prevents executing during gas spikes)
        self._gas_protection = get_gas_price_protection()

        # Production services
        self._nonce_manager = get_nonce_manager()
        self._simulation_service = get_simulation_service()
        self._chain_logger = get_chain_logger()

        # Confirmation trackers per chain
        self._confirmation_trackers: Dict[str, ConfirmationTracker] = {}
        self._bundler: Optional[BundlerClient] = None
        self._paymaster: Optional[PaymasterClient] = None
        self._erc4337_sponsor_guard: Optional[SponsorCapGuard] = None

        if self._erc4337_enabled:
            self._erc4337_sponsor_guard = SponsorCapGuard(
                stage=settings.erc4337_rollout_stage,
                stage_caps_json=settings.erc4337_sponsor_stage_caps_json,
            )
            self._init_erc4337_clients()

        # Initialize MPC signer based on settings
        if not self._simulated:
            self._init_mpc_signer()

        logger.info(
            f"ChainExecutor initialized (simulated={self._simulated}) with production enhancements"
        )

    def _init_erc4337_clients(self) -> None:
        bundler_url = self._settings.pimlico_bundler_url
        paymaster_url = self._settings.pimlico_paymaster_url
        api_key = self._settings.pimlico_api_key

        if not bundler_url and api_key:
            bundler_url = f"https://api.pimlico.io/v2/base-sepolia/rpc?apikey={api_key}"
        if not paymaster_url and api_key:
            paymaster_url = f"https://api.pimlico.io/v2/base-sepolia/rpc?apikey={api_key}"

        if bundler_url:
            self._bundler = BundlerClient(BundlerConfig(url=bundler_url))
        if paymaster_url:
            self._paymaster = PaymasterClient(PaymasterConfig(url=paymaster_url))

    def _init_compliance(self):
        """Initialize compliance services for pre-execution checks."""
        try:
            from sardis_compliance import ComplianceEngine, create_sanctions_service

            self._compliance_engine = ComplianceEngine(self._settings)

            # Initialize sanctions service from environment
            elliptic_api_key = os.getenv("ELLIPTIC_API_KEY")
            elliptic_api_secret = os.getenv("ELLIPTIC_API_SECRET")
            self._sanctions_service = create_sanctions_service(
                api_key=elliptic_api_key,
                api_secret=elliptic_api_secret,
            )
            logger.info("Compliance services initialized successfully")
        except ImportError:
            logger.warning("sardis_compliance not available, compliance checks will fail-closed")
        except Exception as e:
            logger.error(f"Failed to initialize compliance services: {e}")

    def _init_mpc_signer(self):
        """Initialize MPC signer based on configuration."""
        mpc_config = self._settings.mpc

        # Local EOA signer is opt-in and intended for demo/dev usage only.
        eoa_private_key = os.getenv("SARDIS_EOA_PRIVATE_KEY", "")
        eoa_address = os.getenv("SARDIS_EOA_ADDRESS", "")
        if mpc_config.name == "local":
            try:
                self._mpc_signer = LocalAccountSigner(private_key=eoa_private_key, address=eoa_address)
                logger.info("Initialized local EOA signer for chain execution")
                return
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    "Local MPC signer requested but initialization failed. "
                    "Set SARDIS_EOA_PRIVATE_KEY or switch SARDIS_MPC__NAME to turnkey/fireblocks."
                ) from exc
        elif eoa_private_key:
            logger.warning(
                "SARDIS_EOA_PRIVATE_KEY is set but ignored because SARDIS_MPC__NAME=%s. "
                "Use SARDIS_MPC__NAME=local to enable custodial local signing.",
                mpc_config.name,
            )

        if mpc_config.name == "turnkey":
            if self._turnkey_client is not None:
                # Use the shared TurnkeyClient from sardis-wallet (single connection)
                primary_signer = TurnkeyMPCSigner(self._turnkey_client)
            else:
                # Fallback: create a standalone client (e.g. in tests)
                from sardis_wallet.turnkey_client import TurnkeyClient
                standalone = TurnkeyClient(
                    api_key=os.getenv("TURNKEY_API_PUBLIC_KEY", ""),
                    api_private_key=os.getenv("TURNKEY_API_PRIVATE_KEY", ""),
                    organization_id=mpc_config.credential_id,
                    base_url=mpc_config.api_base or "https://api.turnkey.com",
                )
                primary_signer = TurnkeyMPCSigner(standalone)

            # If Lit Protocol credentials are available, wrap in FailoverMPCSigner
            lit_api_key = os.getenv("LIT_PROTOCOL_API_KEY", "")
            if lit_api_key:
                try:
                    from .lit_signer import LitProtocolSigner
                    lit_signer = LitProtocolSigner(api_key=lit_api_key)
                    self._mpc_signer = FailoverMPCSigner(
                        primary=primary_signer,
                        backup=lit_signer,
                        primary_name="turnkey",
                        backup_name="lit-protocol",
                    )
                    logger.info(
                        "MPC failover enabled: Turnkey (primary) + Lit Protocol (backup)"
                    )
                except Exception as e:
                    logger.warning("Lit Protocol backup init failed, using Turnkey only: %s", e)
                    self._mpc_signer = primary_signer
            else:
                self._mpc_signer = primary_signer
        elif mpc_config.name == "lit":
            from .lit_signer import LitProtocolSigner
            self._mpc_signer = LitProtocolSigner()
        elif mpc_config.name == "fireblocks":
            from .fireblocks_signer import FireblocksSigner
            self._mpc_signer = FireblocksSigner()
        else:
            self._mpc_signer = SimulatedMPCSigner()

    def _get_rpc_client(self, chain: str) -> ProductionRPCClient:
        """
        Get or create production RPC client for chain.

        The production client provides:
        - Multi-endpoint failover
        - Chain ID validation
        - Health-based endpoint selection
        - Automatic retry with exponential backoff
        """
        if chain not in self._rpc_clients:
            config = CHAIN_CONFIGS.get(chain)
            if not config:
                raise ValueError(f"Unknown chain: {chain}")

            # Block Solana chains - not yet implemented
            if config.get("not_implemented") or config.get("is_solana"):
                raise NotImplementedError(
                    f"Chain '{chain}' is not yet supported. "
                    f"Solana integration requires Anchor programs and is planned for a future release. "
                    f"Supported chains: base, polygon, ethereum, arbitrum, optimism (and their testnets)."
                )

            # Use production RPC client with chain ID validation
            try:
                chain_config = get_chain_config(chain)
                self._rpc_clients[chain] = ProductionRPCClient(
                    chain=chain,
                    chain_config=chain_config,
                    validate_chain_id_on_connect=True,
                )
                logger.info(f"Created production RPC client for {chain}")
            except ValueError:
                # Fall back to legacy client if chain config not available
                logger.warning(f"Chain config not found for {chain}, using legacy client")
                return self._get_legacy_rpc_client(chain)

        return self._rpc_clients[chain]

    def _get_legacy_rpc_client(self, chain: str) -> ChainRPCClient:
        """Get or create legacy RPC client for backward compatibility."""
        if chain not in self._legacy_rpc_clients:
            config = CHAIN_CONFIGS.get(chain)
            if not config:
                raise ValueError(f"Unknown chain: {chain}")

            rpc_url = config["rpc_url"]
            for chain_config in self._settings.chains:
                if chain_config.name == chain and chain_config.rpc_url:
                    rpc_url = chain_config.rpc_url
                    break

            self._legacy_rpc_clients[chain] = ChainRPCClient(rpc_url, chain=chain)

        return self._legacy_rpc_clients[chain]

    def _get_confirmation_tracker(self, chain: str) -> ConfirmationTracker:
        """Get or create confirmation tracker for chain."""
        if chain not in self._confirmation_trackers:
            self._confirmation_trackers[chain] = get_confirmation_tracker(chain)
        return self._confirmation_trackers[chain]

    async def estimate_gas(self, mandate: PaymentMandate) -> GasEstimate:
        """
        Estimate gas for a payment mandate using production gas estimator.

        Features:
        - Comprehensive gas estimation with safety margins
        - EIP-1559 base fee and priority fee calculation
        - Gas price spike protection
        - USD cost estimation
        """
        chain = mandate.chain or "base_sepolia"
        rpc = self._get_rpc_client(chain)

        # Ensure RPC is connected with chain ID validation
        await rpc.connect()

        from_address = None
        if not self._simulated and self._mpc_signer:
            try:
                wallet_id = getattr(mandate, "wallet_id", None)
                if wallet_id:
                    from_address = await self._mpc_signer.get_address(wallet_id, chain)
            except Exception:  # noqa: BLE001
                from_address = None

        # Get token contract address
        token_addresses = STABLECOIN_ADDRESSES.get(chain, {})
        token_address = token_addresses.get(mandate.token, "")

        if not token_address:
            raise ValueError(f"Token {mandate.token} not supported on {chain}")

        # Encode transfer data
        amount_minor = int(mandate.amount_minor)
        transfer_data = encode_erc20_transfer(mandate.destination, amount_minor)

        # Build transaction params
        tx_params = {
            "to": token_address,
            "data": "0x" + transfer_data.hex(),
            "value": "0x0",
        }
        if from_address:
            tx_params["from"] = from_address

        # Use production gas estimator
        try:
            gas_estimation = await self._simulation_service.estimator.estimate(
                rpc_client=rpc,
                tx_params=tx_params,
                chain=chain,
                apply_safety_margins=True,
            )

            # Log the estimation
            self._chain_logger.log_gas_estimation(
                chain=chain,
                gas_limit=gas_estimation.gas_limit,
                max_fee_gwei=gas_estimation.max_fee_gwei,
                priority_fee_gwei=gas_estimation.priority_fee_gwei,
                estimated_cost_usd=gas_estimation.estimated_cost_usd,
                is_capped=gas_estimation.is_gas_price_capped,
            )

            # Convert to legacy GasEstimate format for backward compatibility
            return GasEstimate(
                gas_limit=gas_estimation.gas_limit,
                gas_price_gwei=gas_estimation.base_fee_gwei,
                max_fee_gwei=gas_estimation.max_fee_gwei,
                max_priority_fee_gwei=gas_estimation.priority_fee_gwei,
                estimated_cost_wei=gas_estimation.estimated_cost_wei,
                estimated_cost_usd=gas_estimation.estimated_cost_usd,
            )

        except Exception as e:
            env = os.getenv("SARDIS_ENVIRONMENT", "dev")
            if env in ("prod", "production"):
                logger.error(f"Gas estimation failed in production: {e}")
                raise RuntimeError(
                    f"Gas estimation failed: {e}. "
                    "Refusing to proceed with fallback values in production."
                ) from e
            logger.warning(f"Production gas estimation failed, falling back: {e}")
            return await self._legacy_estimate_gas(rpc, tx_params)

    async def _legacy_estimate_gas(
        self,
        rpc: ProductionRPCClient,
        tx_params: Dict[str, Any],
    ) -> GasEstimate:
        """Legacy gas estimation fallback."""
        try:
            gas_limit = await rpc.estimate_gas(tx_params)
            gas_limit = int(gas_limit * 1.2)  # Add 20% buffer
        except Exception as e:
            env = os.getenv("SARDIS_ENVIRONMENT", "dev")
            if env in ("prod", "production"):
                raise RuntimeError(
                    f"Legacy gas estimation failed: {e}. "
                    "Refusing to use hardcoded default in production."
                ) from e
            logger.warning(f"Gas estimation failed: {e}, using default")
            gas_limit = 100000

        # Get gas prices
        gas_price = await rpc.get_gas_price()
        max_priority_fee = await rpc.get_max_priority_fee()
        max_fee = gas_price + max_priority_fee

        estimated_cost = gas_limit * max_fee

        return GasEstimate(
            gas_limit=gas_limit,
            gas_price_gwei=Decimal(gas_price) / Decimal(10**9),
            max_fee_gwei=Decimal(max_fee) / Decimal(10**9),
            max_priority_fee_gwei=Decimal(max_priority_fee) / Decimal(10**9),
            estimated_cost_wei=estimated_cost,
        )

    async def dispatch_payment(self, mandate: PaymentMandate) -> ChainReceipt:
        """
        Execute a payment mandate on-chain.

        NOTE: Compliance checks (preflight and sanctions) are performed by the
        orchestrator in Phase 2 before calling this method. This executor assumes
        compliance has already been verified and focuses on chain execution.

        In simulated mode, returns a mock receipt.
        In live mode, signs and broadcasts the transaction.

        Raises:
            GasPriceSpikeError: If gas price exceeds limits
        """
        chain = mandate.chain or "base_sepolia"
        audit_anchor = f"merkle::{mandate.audit_hash}"
        account_type = getattr(mandate, "account_type", "mpc_v1")

        if self._simulated:
            if self._settings.is_production:
                raise RuntimeError(
                    "Simulated chain execution is disabled in production. "
                    "Set SARDIS_CHAIN_MODE=live and configure MPC signer."
                )
            # Simulated mode - return mock receipt
            tx_hash = f"0x{secrets.token_hex(32)}"
            user_op_hash = f"0x{secrets.token_hex(32)}" if account_type == "erc4337_v2" else None
            logger.info(f"[SIMULATED] Payment {mandate.mandate_id} -> {tx_hash}")
            return ChainReceipt(
                tx_hash=tx_hash,
                chain=chain,
                block_number=0,
                audit_anchor=audit_anchor,
                execution_path="erc4337_userop" if account_type == "erc4337_v2" else "legacy_tx",
                user_op_hash=user_op_hash,
            )

        if account_type == "erc4337_v2":
            return await self._execute_erc4337_payment(mandate, chain, audit_anchor)

        # Live mode - execute real transaction with gas protection
        return await self._execute_live_payment_with_gas_protection(mandate, chain, audit_anchor)

    async def _execute_live_payment_with_gas_protection(
        self,
        mandate: PaymentMandate,
        chain: str,
        audit_anchor: str,
    ) -> ChainReceipt:
        """
        Execute live payment with gas price spike protection.

        This wrapper adds retry logic for gas price spikes.
        """
        retry_count = 0
        max_retries = self._gas_protection.config.max_retries

        while retry_count <= max_retries:
            try:
                return await self._execute_live_payment(mandate, chain, audit_anchor)
            except GasPriceSpikeError as e:
                if not e.is_retryable or retry_count >= max_retries:
                    logger.error(
                        f"Gas price spike on {chain} for mandate {mandate.mandate_id}: "
                        f"{e.current_gas_price_gwei} Gwei (max: {e.max_gas_price_gwei} Gwei). "
                        f"Giving up after {retry_count} retries."
                    )
                    raise

                retry_count += 1
                delay = self._gas_protection.config.retry_delay_seconds

                logger.warning(
                    f"Gas price spike detected on {chain}. "
                    f"Waiting {delay}s before retry {retry_count}/{max_retries}..."
                )

                await asyncio.sleep(delay)

        # Should not reach here, but just in case
        raise RuntimeError("Unexpected error in gas protection retry loop")

    async def _check_compliance_preflight(self, mandate: PaymentMandate) -> None:
        """
        Run compliance preflight check. Fail-closed policy.

        Raises:
            RuntimeError: If compliance check fails or service unavailable
        """
        if self._compliance_engine is None:
            # Fail-closed: no compliance service = block all
            logger.error(f"Compliance service unavailable, blocking mandate {mandate.mandate_id}")
            raise RuntimeError("Compliance service unavailable - transaction blocked (fail-closed policy)")

        result = await self._compliance_engine.preflight(mandate)

        if not result.allowed:
            logger.warning(
                f"Compliance check FAILED for mandate {mandate.mandate_id}: "
                f"reason={result.reason}, rule={result.rule_id}"
            )
            raise RuntimeError(
                f"Compliance check failed: {result.reason} (rule: {result.rule_id})"
            )

        logger.info(f"Compliance check PASSED for mandate {mandate.mandate_id}")

    async def _check_sanctions(self, address: str, chain: str) -> None:
        """
        Run sanctions screening on an address. Fail-closed policy.

        Raises:
            RuntimeError: If address is sanctioned or service unavailable
        """
        if self._sanctions_service is None:
            # Fail-closed: no sanctions service = block all
            logger.error(f"Sanctions service unavailable, blocking address {address}")
            raise RuntimeError("Sanctions service unavailable - transaction blocked (fail-closed policy)")

        result = await self._sanctions_service.screen_address(address, chain)

        if result.should_block:
            logger.warning(
                f"Sanctions check BLOCKED address {address}: "
                f"risk={result.risk_level}, sanctioned={result.is_sanctioned}, "
                f"reason={result.reason}"
            )
            raise RuntimeError(
                f"Sanctions check failed: address {address} is blocked "
                f"(risk: {result.risk_level}, reason: {result.reason})"
            )

        logger.info(f"Sanctions check PASSED for address {address} (risk: {result.risk_level})")

    def _require_erc4337_ready(self, chain: str) -> None:
        if not self._erc4337_enabled:
            raise RuntimeError(
                "ERC-4337 execution requested but disabled. "
                "Set SARDIS_ERC4337_ENABLED=true for erc4337_v2 wallets."
            )
        if chain not in self._erc4337_chain_allowlist:
            raise RuntimeError(
                f"ERC-4337 chain not allowed: {chain}. "
                f"Allowed: {sorted(self._erc4337_chain_allowlist)}"
            )
        if self._bundler is None:
            raise RuntimeError(
                "ERC-4337 bundler is not configured. "
                "Set SARDIS_PIMLICO_BUNDLER_URL or SARDIS_PIMLICO_API_KEY."
            )
        if self._paymaster is None:
            raise RuntimeError(
                "ERC-4337 paymaster is not configured. "
                "Set SARDIS_PIMLICO_PAYMASTER_URL or SARDIS_PIMLICO_API_KEY."
            )

    async def _sign_user_operation_hash(self, wallet_id: str, user_op_hash: str) -> str:
        if not self._mpc_signer:
            raise RuntimeError("No MPC signer configured for ERC-4337 signature.")

        signature = await self._mpc_signer.sign_user_operation_hash(wallet_id, user_op_hash)
        if not isinstance(signature, str) or not signature.strip():
            raise RuntimeError("MPC signer returned empty UserOperation signature.")
        if not signature.startswith("0x"):
            signature = f"0x{signature}"
        return signature

    async def _execute_erc4337_payment(
        self,
        mandate: PaymentMandate,
        chain: str,
        audit_anchor: str,
    ) -> ChainReceipt:
        self._require_erc4337_ready(chain)
        if not self._mpc_signer:
            raise RuntimeError("No signer configured for ERC-4337 flow.")

        wallet_id = getattr(mandate, "wallet_id", None)
        smart_account = getattr(mandate, "smart_account_address", None)
        if not wallet_id:
            raise RuntimeError("PaymentMandate.wallet_id is required for ERC-4337 execution.")
        if not smart_account:
            raise RuntimeError("PaymentMandate.smart_account_address is required for erc4337_v2 execution.")

        token_addresses = STABLECOIN_ADDRESSES.get(chain, {})
        token_address = token_addresses.get(mandate.token, "")
        if not token_address:
            raise ValueError(f"Token {mandate.token} not supported on {chain}")

        amount_minor = int(mandate.amount_minor)
        transfer_data = encode_erc20_transfer(mandate.destination, amount_minor)
        entrypoint = self._erc4337_entrypoint or get_entrypoint_v07(chain)

        user_op = UserOperation(
            sender=smart_account,
            nonce=await self._bundler.get_user_operation_nonce(smart_account, entrypoint),
            init_code=zero_hex(),
            call_data=UserOperation.encode_execute(token_address, 0, transfer_data),
            call_gas_limit=200000,
            verification_gas_limit=250000,
            pre_verification_gas=60000,
            max_fee_per_gas=0,
            max_priority_fee_per_gas=0,
            paymaster_and_data=zero_hex(),
            signature=zero_hex(),
        )

        try:
            gas = await self._bundler.estimate_user_operation_gas(user_op, entrypoint)
            user_op.call_gas_limit = int(gas.get("callGasLimit", user_op.call_gas_limit), 16)
            user_op.verification_gas_limit = int(
                gas.get("verificationGasLimit", user_op.verification_gas_limit), 16
            )
            user_op.pre_verification_gas = int(
                gas.get("preVerificationGas", user_op.pre_verification_gas), 16
            )
        except Exception:
            logger.warning("Failed to estimate ERC-4337 gas, using defaults")

        user_op.max_fee_per_gas = 2_000_000_000
        user_op.max_priority_fee_per_gas = 1_000_000_000

        if self._erc4337_sponsor_guard is not None:
            estimated_cost_wei = self._erc4337_sponsor_guard.estimate_max_cost_wei(user_op)
            self._erc4337_sponsor_guard.reserve(chain=chain, estimated_cost_wei=estimated_cost_wei)
            logger.info(
                "ERC-4337 sponsor cap reserved chain=%s stage=%s estimated_cost_wei=%s",
                chain,
                self._erc4337_sponsor_guard.stage,
                estimated_cost_wei,
            )

        sponsored = await self._paymaster.sponsor_user_operation(
            user_op=user_op,
            entrypoint=entrypoint,
            chain=chain,
            sponsorship_policy_id=(
                f"sardis-{chain}-{self._erc4337_sponsor_guard.stage}"
                if self._erc4337_sponsor_guard is not None
                else f"sardis-{chain}"
            ),
        )
        user_op.paymaster_and_data = sponsored.paymaster_and_data

        user_op_hash = await self._bundler.get_user_operation_hash(user_op, entrypoint)
        user_op.signature = await self._sign_user_operation_hash(wallet_id, user_op_hash)

        submitted_hash = await self._bundler.send_user_operation(user_op, entrypoint)
        receipt = await self._bundler.wait_for_receipt(submitted_hash, timeout_seconds=180)
        tx_hash = receipt.get("receipt", {}).get("transactionHash") or receipt.get("transactionHash")
        block_hex = receipt.get("receipt", {}).get("blockNumber") or receipt.get("blockNumber") or "0x0"

        if not tx_hash:
            raise RuntimeError("Bundler did not return a transaction hash for UserOperation.")

        proof_artifact_path: str | None = None
        proof_artifact_sha256: str | None = None
        artifact_base_dir = os.getenv("SARDIS_ERC4337_PROOF_ARTIFACT_DIR", "artifacts/erc4337")
        try:
            artifact = write_erc4337_proof_artifact(
                base_dir=artifact_base_dir,
                mandate_id=mandate.mandate_id,
                chain=chain,
                wallet_id=wallet_id,
                smart_account=smart_account,
                entrypoint=entrypoint,
                user_operation=user_op.to_rpc(),
                user_op_hash=submitted_hash,
                tx_hash=tx_hash,
                receipt=receipt,
            )
            proof_artifact_path = artifact.path
            proof_artifact_sha256 = artifact.sha256
        except Exception as exc:
            logger.warning("Failed to persist ERC-4337 proof artifact for %s: %s", mandate.mandate_id, exc)

        return ChainReceipt(
            tx_hash=tx_hash,
            chain=chain,
            block_number=int(block_hex, 16) if isinstance(block_hex, str) else int(block_hex or 0),
            audit_anchor=audit_anchor,
            execution_path="erc4337_userop",
            user_op_hash=submitted_hash,
            proof_artifact_path=proof_artifact_path,
            proof_artifact_sha256=proof_artifact_sha256,
        )

    async def _execute_live_payment(
        self,
        mandate: PaymentMandate,
        chain: str,
        audit_anchor: str,
    ) -> ChainReceipt:
        """
        Execute a live payment on-chain with production-grade handling.

        SECURITY FEATURES:
        - Chain ID validation (prevents wrong network)
        - Transaction simulation (prevents failing transactions)
        - Nonce management (prevents double-spend and stuck txs)
        - Receipt verification (confirms success on-chain)
        - Reorg detection (handles chain reorganizations)
        """
        rpc = self._get_rpc_client(chain)

        # Ensure RPC is connected with chain ID validation
        await rpc.connect()

        if not self._mpc_signer:
            raise RuntimeError("No signer configured. Provide SARDIS_EOA_PRIVATE_KEY or configure MPC.")

        # Get token contract address
        token_addresses = STABLECOIN_ADDRESSES.get(chain, {})
        token_address = token_addresses.get(mandate.token, "")

        if not token_address:
            raise ValueError(f"Token {mandate.token} not supported on {chain}")

        # Encode transfer data
        amount_minor = int(mandate.amount_minor)
        transfer_data = encode_erc20_transfer(mandate.destination, amount_minor)

        # Get sender address
        wallet_id = getattr(mandate, "wallet_id", None)
        if not wallet_id:
            raise RuntimeError(
                "PaymentMandate.wallet_id is required for live signing. "
                "Use mandate.subject for agent identity and set wallet_id as the execution hint."
            )
        sender_address = await self._mpc_signer.get_address(wallet_id, chain)

        # Build transaction params for simulation
        tx_params = {
            "from": sender_address,
            "to": token_address,
            "data": "0x" + transfer_data.hex(),
            "value": "0x0",
        }

        # === TRANSACTION SIMULATION ===
        # Simulate before execution to catch failures early
        async with self._chain_logger.operation_context(
            OperationType.SIMULATION, chain, mandate_id=mandate.mandate_id
        ):
            try:
                simulation_output, gas_estimation = await self._simulation_service.prepare_transaction(
                    rpc_client=rpc,
                    tx_params=tx_params,
                    chain=chain,
                    validate=True,
                )
                logger.info(
                    f"Transaction simulation passed for mandate {mandate.mandate_id}"
                )
            except SimulationError as e:
                logger.error(
                    f"Transaction simulation failed for mandate {mandate.mandate_id}: "
                    f"{e.simulation_output.revert_reason if e.simulation_output else str(e)}"
                )
                raise RuntimeError(
                    f"Transaction would fail: {e.simulation_output.revert_reason if e.simulation_output else str(e)}"
                )

        # Convert to legacy GasEstimate for compatibility
        gas_estimate = GasEstimate(
            gas_limit=gas_estimation.gas_limit,
            gas_price_gwei=gas_estimation.base_fee_gwei,
            max_fee_gwei=gas_estimation.max_fee_gwei,
            max_priority_fee_gwei=gas_estimation.priority_fee_gwei,
            estimated_cost_wei=gas_estimation.estimated_cost_wei,
            estimated_cost_usd=gas_estimation.estimated_cost_usd,
        )

        # === GAS PRICE SPIKE PROTECTION ===
        is_acceptable, warning = await self._gas_protection.check_gas_price(
            gas_estimate, chain
        )

        if warning:
            logger.warning(
                f"Gas price warning for mandate {mandate.mandate_id} on {chain}: {warning}"
            )

        # Cap gas price to maximum allowed values (safety net)
        gas_estimate = self._gas_protection.cap_gas_price(gas_estimate, chain)

        # Log gas estimation
        self._chain_logger.log_gas_estimation(
            chain=chain,
            gas_limit=gas_estimate.gas_limit,
            max_fee_gwei=gas_estimate.max_fee_gwei,
            priority_fee_gwei=gas_estimate.max_priority_fee_gwei,
            estimated_cost_usd=gas_estimate.estimated_cost_usd,
            is_capped=True,
        )

        # === NONCE MANAGEMENT ===
        # Use production nonce manager for thread-safe nonce handling
        async with self._chain_logger.operation_context(
            OperationType.NONCE_MANAGEMENT, chain, address=sender_address
        ):
            nonce = await self._nonce_manager.reserve_nonce(sender_address, rpc)
            self._chain_logger.log_nonce_management(
                address=sender_address,
                action="reserved",
                nonce=nonce,
                details={"mandate_id": mandate.mandate_id},
            )

        broadcast_success = False
        try:
            # Build transaction request with capped gas prices
            tx_request = TransactionRequest(
                chain=chain,
                to_address=token_address,
                value=0,
                data=transfer_data,
                gas_limit=gas_estimate.gas_limit,
                max_fee_per_gas=int(gas_estimate.max_fee_gwei * 10**9),
                max_priority_fee_per_gas=int(gas_estimate.max_priority_fee_gwei * 10**9),
                nonce=nonce,
            )

            # Sign transaction via MPC
            logger.info(f"Signing transaction for mandate {mandate.mandate_id}")
            signed_tx = await self._mpc_signer.sign_transaction(wallet_id, tx_request)

            # Broadcast transaction
            logger.info(f"Broadcasting transaction for mandate {mandate.mandate_id}")
            tx_hash = await rpc.send_raw_transaction(signed_tx)
            broadcast_success = True

            logger.info(f"Transaction submitted: {tx_hash}")

            # Register pending transaction for tracking
            data_hash = hashlib.sha256(transfer_data).hexdigest()
            self._nonce_manager.register_pending_transaction(
                tx_hash=tx_hash,
                address=sender_address,
                nonce=nonce,
                chain=chain,
                gas_price=int(gas_estimate.max_fee_gwei * 10**9),
                priority_fee=int(gas_estimate.max_priority_fee_gwei * 10**9),
                data_hash=data_hash,
            )

            # Log transaction submission
            self._chain_logger.log_transaction_submitted(
                tx_hash=tx_hash,
                chain=chain,
                from_address=sender_address,
                to_address=token_address,
                value_wei=0,
                nonce=nonce,
                gas_limit=gas_estimate.gas_limit,
                max_fee_gwei=gas_estimate.max_fee_gwei,
                priority_fee_gwei=gas_estimate.max_priority_fee_gwei,
            )

            # === CONFIRMATION TRACKING ===
            # Wait for confirmation with receipt verification
            receipt_validation = await self._wait_for_confirmation_with_verification(
                rpc, tx_hash, chain, sender_address
            )

            # Log confirmation
            self._chain_logger.log_transaction_confirmed(
                tx_hash=tx_hash,
                block_number=receipt_validation.block_number or 0,
                confirmations=1,  # At least 1 confirmation at this point
                gas_used=receipt_validation.gas_used or 0,
                effective_gas_price=receipt_validation.effective_gas_price,
            )

            return ChainReceipt(
                tx_hash=tx_hash,
                chain=chain,
                block_number=receipt_validation.block_number or 0,
                audit_anchor=audit_anchor,
            )

        except Exception as e:
            # Only release nonce if broadcast failed - if broadcast succeeded, nonce is already consumed on-chain
            if not broadcast_success:
                await self._nonce_manager.release_nonce(sender_address, nonce)
                self._chain_logger.log_nonce_management(
                    address=sender_address,
                    action="released",
                    nonce=nonce,
                    details={"error": str(e)},
                )
            else:
                logger.error(
                    f"Confirmation failed after broadcast. Nonce consumed on-chain. "
                    f"tx_hash={tx_hash}, mandate_id={mandate.mandate_id}"
                )
            raise

    async def _wait_for_confirmation_with_verification(
        self,
        rpc: ProductionRPCClient,
        tx_hash: str,
        chain: str,
        sender_address: str,
    ) -> ReceiptValidation:
        """
        Wait for transaction confirmation with comprehensive receipt verification.

        SECURITY: Verifies:
        - Transaction was included in a block
        - Transaction succeeded (status = 1)
        - Required confirmations reached
        """
        async with self._chain_logger.operation_context(
            OperationType.CONFIRMATION_TRACKING, chain, tx_hash=tx_hash
        ):
            try:
                receipt_validation = await self._nonce_manager.wait_for_receipt(
                    tx_hash=tx_hash,
                    rpc_client=rpc,
                    timeout_seconds=self.CONFIRMATION_TIMEOUT,
                    poll_interval=self.POLL_INTERVAL,
                    required_confirmations=self.get_confirmations_required(chain),
                )

                if not receipt_validation.is_successful:
                    self._chain_logger.log_transaction_failed(
                        tx_hash=tx_hash,
                        error=receipt_validation.error_message or "Transaction failed",
                        revert_reason=receipt_validation.revert_reason,
                    )
                    raise TransactionFailedError(
                        tx_hash=tx_hash,
                        revert_reason=receipt_validation.revert_reason,
                        receipt=receipt_validation,
                    )

                return receipt_validation

            except TimeoutError:
                logger.error(f"Transaction {tx_hash} confirmation timeout")
                raise
            except TransactionFailedError:
                raise
            except Exception as e:
                logger.error(f"Error waiting for confirmation: {e}")
                raise

    async def _wait_for_confirmation(
        self,
        rpc: ChainRPCClient,
        tx_hash: str,
        chain: str,
    ) -> Dict[str, Any]:
        """Wait for transaction confirmation."""
        chain_config = CHAIN_CONFIGS.get(chain, {})
        block_time = chain_config.get("block_time", 2)
        
        start_time = asyncio.get_event_loop().time()
        timeout = self.CONFIRMATION_TIMEOUT
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Transaction {tx_hash} not confirmed after {timeout}s")
            
            receipt = await rpc.get_transaction_receipt(tx_hash)
            
            if receipt:
                # Check if transaction succeeded
                status = int(receipt.get("status", "0x0"), 16)
                if status == 0:
                    raise Exception(f"Transaction {tx_hash} failed on-chain")
                
                # Check confirmations
                tx_block = int(receipt.get("blockNumber", "0x0"), 16)
                current_block = await rpc.get_block_number()
                confirmations = current_block - tx_block + 1
                
                required_confirmations = self.get_confirmations_required(chain)
                if confirmations >= required_confirmations:
                    logger.info(f"Transaction {tx_hash} confirmed with {confirmations} confirmations")
                    return receipt

                logger.debug(f"Transaction {tx_hash} has {confirmations} confirmations, waiting for {required_confirmations}")
            
            await asyncio.sleep(self.POLL_INTERVAL)

    async def get_transaction_status(self, tx_hash: str, chain: str) -> TransactionStatus:
        """Get the status of a transaction."""
        rpc = self._get_rpc_client(chain)
        
        receipt = await rpc.get_transaction_receipt(tx_hash)
        
        if not receipt:
            return TransactionStatus.PENDING
        
        status = int(receipt.get("status", "0x0"), 16)
        if status == 0:
            return TransactionStatus.FAILED
        
        tx_block = int(receipt.get("blockNumber", "0x0"), 16)
        current_block = await rpc.get_block_number()
        confirmations = current_block - tx_block + 1

        if confirmations >= self.get_confirmations_required(chain):
            return TransactionStatus.CONFIRMED

        return TransactionStatus.CONFIRMING

    async def validate_chain_connection(self, chain: str) -> bool:
        """
        Validate connection to a chain including chain ID verification.

        SECURITY: This should be called before any sensitive operations
        to ensure we're connected to the correct network.

        Args:
            chain: Chain name to validate

        Returns:
            True if connection is valid

        Raises:
            ChainIDMismatchError: If chain ID doesn't match expected
        """
        rpc = self._get_rpc_client(chain)
        await rpc.connect()
        return True

    async def get_rpc_health(self, chain: str) -> Dict[str, Any]:
        """
        Get health status of RPC endpoints for a chain.

        Returns:
            Dictionary with endpoint health information
        """
        rpc = self._get_rpc_client(chain)
        return await rpc.health_check()

    async def get_pending_transactions(
        self,
        address: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get list of pending transactions.

        Args:
            address: Optional address to filter by

        Returns:
            List of pending transaction details
        """
        pending = self._nonce_manager.get_all_pending(address)
        return [
            {
                "tx_hash": p.tx_hash,
                "nonce": p.nonce,
                "address": p.address,
                "chain": p.chain,
                "submitted_at": p.submitted_at.isoformat(),
                "is_stuck": p.is_stuck(
                    self._nonce_manager._config.stuck_tx_timeout_seconds
                ),
            }
            for p in pending
        ]

    async def get_stuck_transactions(
        self,
        address: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get list of stuck transactions that may need replacement.

        Args:
            address: Optional address to filter by

        Returns:
            List of stuck transaction details
        """
        stuck = await self._nonce_manager.get_stuck_transactions(address)
        return [
            {
                "tx_hash": p.tx_hash,
                "nonce": p.nonce,
                "address": p.address,
                "chain": p.chain,
                "submitted_at": p.submitted_at.isoformat(),
                "age_seconds": (
                    datetime.now(timezone.utc) - p.submitted_at
                ).total_seconds(),
            }
            for p in stuck
        ]

    async def replace_stuck_transaction(
        self,
        tx_hash: str,
    ) -> str:
        """
        Replace a stuck transaction with a higher-gas version.

        Sends a same-nonce transaction with bumped gas to unstick the address.
        Returns the replacement tx hash.

        Raises:
            RuntimeError: If signer unavailable or replacement fails
            ValueError: If tx_hash not found in pending transactions
        """
        if not self._mpc_signer:
            raise RuntimeError("No signer configured for replacement transaction")

        # Find the stuck pending tx
        pending = self._nonce_manager._pending_txs.get(tx_hash)
        if pending is None:
            raise ValueError(f"Transaction {tx_hash} not found in pending list")

        chain = pending.chain
        rpc = self._get_rpc_client(chain)
        await rpc.connect()

        # Calculate bumped gas
        new_max_fee, new_priority_fee = await self._nonce_manager.calculate_replacement_gas(
            pending, rpc
        )

        # Build a zero-value self-transfer to cancel, or re-send original data
        # Using the original data_hash to replay the same intent
        tx_request = TransactionRequest(
            chain=chain,
            to_address=pending.address,  # self-transfer (cancel tx)
            value=0,
            data=b"",
            gas_limit=21000,  # simple transfer
            max_fee_per_gas=new_max_fee,
            max_priority_fee_per_gas=new_priority_fee,
            nonce=pending.nonce,
        )

        # Sign and broadcast replacement
        wallet_id = pending.address  # best available identifier
        signed_tx = await self._mpc_signer.sign_transaction(wallet_id, tx_request)
        new_tx_hash = await rpc.send_raw_transaction(signed_tx)

        logger.info(
            f"Replaced stuck tx {tx_hash} with {new_tx_hash} "
            f"(nonce={pending.nonce}, max_fee={new_max_fee})"
        )

        # Update tracking: remove old, register new
        self._nonce_manager._pending_txs.pop(tx_hash, None)
        self._nonce_manager.register_pending_transaction(
            tx_hash=new_tx_hash,
            address=pending.address,
            nonce=pending.nonce,
            chain=chain,
            gas_price=new_max_fee,
            priority_fee=new_priority_fee,
            data_hash=pending.data_hash,
        )

        return new_tx_hash

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics from all components.

        Returns:
            Dictionary with RPC, transaction, and tracking metrics
        """
        return {
            "rpc_metrics": self._chain_logger.get_rpc_metrics(),
            "transaction_metrics": self._chain_logger.get_transaction_metrics(),
            "pending_transactions": self._nonce_manager.get_pending_count(None),
            "confirmation_trackers": {
                chain: tracker.get_stats()
                for chain, tracker in self._confirmation_trackers.items()
            },
        }

    async def get_token_balance(self, address: str, chain: str, token: str) -> Decimal:
        """Query ERC20 balance for address on chain. Returns normalized Decimal."""
        from sardis_v2_core.tokens import TokenType, normalize_token_amount

        chain_tokens = STABLECOIN_ADDRESSES.get(chain, {})
        contract = chain_tokens.get(token)
        if not contract:
            return Decimal("0")

        rpc = self._get_rpc_client(chain)
        await rpc.connect()
        padded = "0x70a08231" + address.lower().replace("0x", "").zfill(64)
        result = await rpc.eth_call({"to": contract, "data": padded})
        raw = int(result, 16) if result and result != "0x" else 0
        return normalize_token_amount(TokenType(token), raw)

    async def get_all_balances(
        self,
        address: str,
        chains: list[str] | None = None,
        tokens: list[str] | None = None,
    ) -> list[dict]:
        """Query balances across all chains/tokens in parallel. Returns list of {chain, token, balance, address}."""
        tasks = []
        query_params: list[tuple[str, str]] = []
        target_chains = chains or [
            c for c in STABLECOIN_ADDRESSES
            if "_sepolia" not in c and c != "solana_devnet" and c != "solana"
        ]
        for chain in target_chains:
            chain_tokens = STABLECOIN_ADDRESSES.get(chain, {})
            for token_symbol in chain_tokens:
                if tokens and token_symbol not in tokens:
                    continue
                tasks.append(self.get_token_balance(address, chain, token_symbol))
                query_params.append((chain, token_symbol))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        balances = []
        for (chain, token), result in zip(query_params, results):
            balance = result if isinstance(result, Decimal) else Decimal("0")
            balances.append({
                "chain": chain,
                "token": token,
                "balance": str(balance),
                "address": address,
            })
        return balances

    async def close(self):
        """Close all connections and cleanup resources."""
        # Close production RPC clients
        for client in self._rpc_clients.values():
            await client.close()
        self._rpc_clients.clear()

        # Close legacy RPC clients
        for client in self._legacy_rpc_clients.values():
            await client.close()
        self._legacy_rpc_clients.clear()

        # Stop confirmation trackers
        for tracker in self._confirmation_trackers.values():
            await tracker.stop_monitoring()
        self._confirmation_trackers.clear()

        # Close MPC signer
        if hasattr(self._mpc_signer, "close"):
            await self._mpc_signer.close()

        logger.info("ChainExecutor closed")
