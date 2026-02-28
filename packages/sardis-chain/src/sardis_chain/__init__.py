"""Sardis Chain - Production-grade multi-chain stablecoin executor.

This package provides the blockchain execution layer for stablecoin operations:
- Multi-chain support (Ethereum, Base, Polygon, Arbitrum)
- MPC custody integration (Turnkey, Fireblocks)
- Transaction execution with gas estimation
- Nonce management and confirmation tracking
- MEV protection and deposit monitoring

Version: 0.4.0
"""

from .config import (
    ChainConfig,
    ChainId,
    TokenConfig,
    GasConfig,
    RPCConfig,
    TurnkeyConfig,
    load_chain_config,
)
from .rpc_client import (
    ProductionRPCClient,
    RPCError,
    AllEndpointsFailedError,
    ChainIDMismatchError,
    get_rpc_client,
    close_all_clients,
)
from .nonce_manager import (
    NonceManager,
    NonceConflictError,
    StuckTransactionError,
    TransactionFailedError,
)
from .redis_nonce_manager import RedisNonceManager
from .confirmation import (
    ConfirmationTracker,
    ConfirmationStatus,
)
from .simulation import (
    TransactionSimulator,
    SimulationResult,
    SimulationError,
    GasEstimation,
)
from .executor import (
    ChainExecutor,
    ChainRPCClient,
    TransactionRequest,
    GasEstimate,
    GasPriceProtection,
    GasPriceSpikeError,
    MPCSignerPort,
    FailoverMPCSigner,
    SimulatedMPCSigner,
)
from .deposit_monitor import (
    DepositMonitor,
    Deposit,
    MonitorConfig,
)
from .mev_protection import (
    MEVProtectionService,
    FlashbotsProvider,
    MEVConfig,
)
from .wallet_manager import (
    WalletManager,
    WalletInfo,
)
from .price_oracle import (
    PriceOracle,
    get_price_oracle,
    CHAIN_NATIVE_TOKEN,
)
from .logging_utils import (
    get_chain_logger,
    ChainLogger,
    log_operation,
)
from .erc4337 import (
    ENTRYPOINT_V07_BY_CHAIN,
    get_entrypoint_v07,
    UserOperation,
    BundlerClient,
    BundlerConfig,
    PaymasterClient,
    PaymasterConfig,
    SponsoredUserOperation,
    SponsorCapGuard,
    SponsorCapExceeded,
    StageCaps,
    ERC4337ProofArtifact,
    write_erc4337_proof_artifact,
)
from .gas_optimizer import (
    GasOptimizer,
    GasEstimate as GasOptimizerEstimate,
    ChainRoute,
    get_gas_optimizer,
)

__version__ = "0.4.0"

__all__ = [
    # Version
    "__version__",
    # Config
    "ChainConfig",
    "ChainId",
    "TokenConfig",
    "GasConfig",
    "RPCConfig",
    "TurnkeyConfig",
    "load_chain_config",
    # RPC Client
    "ProductionRPCClient",
    "RPCError",
    "AllEndpointsFailedError",
    "ChainIDMismatchError",
    "get_rpc_client",
    "close_all_clients",
    # Nonce Manager
    "NonceManager",
    "NonceConflictError",
    "StuckTransactionError",
    "TransactionFailedError",
    # Redis Nonce Manager
    "RedisNonceManager",
    # Confirmation
    "ConfirmationTracker",
    "ConfirmationStatus",
    # Simulation
    "TransactionSimulator",
    "SimulationResult",
    "SimulationError",
    "GasEstimation",
    # Executor
    "ChainExecutor",
    "ChainRPCClient",
    "TransactionRequest",
    "GasEstimate",
    "GasPriceProtection",
    "GasPriceSpikeError",
    # MPC Signers
    "MPCSignerPort",
    "FailoverMPCSigner",
    "SimulatedMPCSigner",
    # Deposit Monitor
    "DepositMonitor",
    "Deposit",
    "MonitorConfig",
    # MEV Protection
    "MEVProtectionService",
    "FlashbotsProvider",
    "MEVConfig",
    # Wallet Manager
    "WalletManager",
    "WalletInfo",
    # Price Oracle
    "PriceOracle",
    "get_price_oracle",
    "CHAIN_NATIVE_TOKEN",
    # Logging
    "get_chain_logger",
    "ChainLogger",
    "log_operation",
    # ERC-4337
    "ENTRYPOINT_V07_BY_CHAIN",
    "get_entrypoint_v07",
    "UserOperation",
    "BundlerClient",
    "BundlerConfig",
    "PaymasterClient",
    "PaymasterConfig",
    "SponsoredUserOperation",
    "SponsorCapGuard",
    "SponsorCapExceeded",
    "StageCaps",
    "ERC4337ProofArtifact",
    "write_erc4337_proof_artifact",
    # Gas Optimizer
    "GasOptimizer",
    "GasOptimizerEstimate",
    "ChainRoute",
    "get_gas_optimizer",
]
