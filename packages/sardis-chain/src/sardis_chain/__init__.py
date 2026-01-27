"""Sardis Chain - Production-grade multi-chain stablecoin executor.

This package provides the blockchain execution layer for stablecoin operations:
- Multi-chain support (Ethereum, Base, Polygon, Arbitrum)
- MPC custody integration (Turnkey, Fireblocks)
- Transaction execution with gas estimation
- Nonce management and confirmation tracking
- MEV protection and deposit monitoring

Version: 0.2.0
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
    RPCClient,
    RPCError,
    RPCConnectionError,
    RPCTimeoutError,
    create_rpc_client,
)
from .nonce_manager import (
    NonceManager,
    NonceError,
    NonceExhaustedError,
    NonceSyncError,
)
from .confirmation import (
    ConfirmationTracker,
    ConfirmationResult,
    ConfirmationStatus,
    TransactionReceipt,
)
from .simulation import (
    TransactionSimulator,
    SimulationResult,
    SimulationError,
    GasEstimate,
)
from .executor import (
    ChainExecutor,
    ExecutorConfig,
    TransferResult,
    TransactionError,
    InsufficientFundsError,
    GasEstimationError,
)
from .deposit_monitor import (
    DepositMonitor,
    Deposit,
    DepositCallback,
    MonitorConfig,
)
from .mev_protection import (
    MEVProtector,
    FlashbotsProvider,
    PrivateMempoolProvider,
    MEVConfig,
)
from .wallet_manager import (
    WalletManager,
    ManagedWallet,
    WalletCreationError,
)
from .logging_utils import (
    get_chain_logger,
    ChainLogContext,
    log_transaction,
    log_confirmation,
)

__version__ = "0.2.0"

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
    "RPCClient",
    "RPCError",
    "RPCConnectionError",
    "RPCTimeoutError",
    "create_rpc_client",
    # Nonce Manager
    "NonceManager",
    "NonceError",
    "NonceExhaustedError",
    "NonceSyncError",
    # Confirmation
    "ConfirmationTracker",
    "ConfirmationResult",
    "ConfirmationStatus",
    "TransactionReceipt",
    # Simulation
    "TransactionSimulator",
    "SimulationResult",
    "SimulationError",
    "GasEstimate",
    # Executor
    "ChainExecutor",
    "ExecutorConfig",
    "TransferResult",
    "TransactionError",
    "InsufficientFundsError",
    "GasEstimationError",
    # Deposit Monitor
    "DepositMonitor",
    "Deposit",
    "DepositCallback",
    "MonitorConfig",
    # MEV Protection
    "MEVProtector",
    "FlashbotsProvider",
    "PrivateMempoolProvider",
    "MEVConfig",
    # Wallet Manager
    "WalletManager",
    "ManagedWallet",
    "WalletCreationError",
    # Logging
    "get_chain_logger",
    "ChainLogContext",
    "log_transaction",
    "log_confirmation",
]
