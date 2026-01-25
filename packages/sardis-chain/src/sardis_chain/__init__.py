"""
Sardis Chain - Production-grade blockchain executor with MPC signing support.

This module provides comprehensive blockchain interaction capabilities with:
- Multi-RPC endpoint support with automatic failover
- Chain ID validation on connection (security)
- Transaction simulation before execution
- Comprehensive gas estimation with safety margins
- Nonce management with stuck transaction handling
- Transaction receipt status verification
- Block confirmation tracking with reorg detection
- Comprehensive logging for all operations

Usage:
    from sardis_chain import ChainExecutor, get_config

    # Create executor with settings
    executor = ChainExecutor(settings)

    # Validate chain connection
    await executor.validate_chain_connection("base_sepolia")

    # Execute payment
    receipt = await executor.dispatch_payment(mandate)
"""

# Core executor and signers
from .executor import (
    ChainExecutor,
    ChainRPCClient,
    TurnkeyMPCSigner,
    SimulatedMPCSigner,
    LocalAccountSigner,
    MPCSignerPort,
    TransactionRequest,
    TransactionStatus,
    GasEstimate,
    SubmittedTx,
    CHAIN_CONFIGS,
    STABLECOIN_ADDRESSES,
    SARDIS_CONTRACTS,
    GasPriceProtection,
    GasPriceSpikeError,
    GasPriceProtectionConfig,
    get_gas_price_protection,
    encode_erc20_transfer,
)

# Wallet management
from .wallet_manager import (
    WalletManager,
    WalletInfo,
    KeyRotationSchedule,
    get_wallet_manager,
)

# Configuration
from .config import (
    SardisChainConfig,
    ChainConfig,
    RPCEndpointConfig,
    NonceManagerConfig,
    GasEstimationConfig,
    TransactionSimulationConfig,
    ReorgDetectionConfig,
    LoggingConfig,
    ChainNetwork,
    get_config,
    set_config,
    get_chain_config,
    build_default_config,
    validate_chain_id,
    CHAIN_ID_MAP,
)

# Production RPC client
from .rpc_client import (
    ProductionRPCClient,
    EndpointHealth,
    EndpointStatus,
    ChainIDMismatchError,
    RPCError,
    AllEndpointsFailedError,
    get_rpc_client,
    close_all_clients,
)

# Nonce management
from .nonce_manager import (
    NonceManager,
    PendingTransaction,
    ReceiptValidation,
    TransactionReceiptStatus,
    NonceConflictError,
    StuckTransactionError,
    TransactionFailedError,
    get_nonce_manager,
)

# Transaction simulation and gas estimation
from .simulation import (
    TransactionSimulator,
    GasEstimator,
    SimulationAndEstimation,
    SimulationOutput,
    SimulationResult,
    GasEstimation,
    SimulationError,
    GasEstimationError,
    get_simulation_service,
)

# Confirmation tracking and reorg detection
from .confirmation import (
    ConfirmationTracker,
    TrackedTransaction,
    ConfirmationStatus,
    ReorgEvent,
    ReorgSeverity,
    BlockInfo,
    ReorgError,
    get_confirmation_tracker,
    close_all_trackers,
)

# Logging utilities
from .logging_utils import (
    ChainLogger,
    OperationType,
    OperationContext,
    RPCCallLog,
    TransactionLog,
    LogLevel,
    get_chain_logger,
    log_operation,
    setup_logging,
)

__all__ = [
    # Core executor
    "ChainExecutor",
    "ChainRPCClient",
    "TurnkeyMPCSigner",
    "SimulatedMPCSigner",
    "LocalAccountSigner",
    "MPCSignerPort",
    "TransactionRequest",
    "TransactionStatus",
    "GasEstimate",
    "SubmittedTx",
    "CHAIN_CONFIGS",
    "STABLECOIN_ADDRESSES",
    "SARDIS_CONTRACTS",
    "GasPriceProtection",
    "GasPriceSpikeError",
    "GasPriceProtectionConfig",
    "get_gas_price_protection",
    "encode_erc20_transfer",
    # Wallet management
    "WalletManager",
    "WalletInfo",
    "KeyRotationSchedule",
    "get_wallet_manager",
    # Configuration
    "SardisChainConfig",
    "ChainConfig",
    "RPCEndpointConfig",
    "NonceManagerConfig",
    "GasEstimationConfig",
    "TransactionSimulationConfig",
    "ReorgDetectionConfig",
    "LoggingConfig",
    "ChainNetwork",
    "get_config",
    "set_config",
    "get_chain_config",
    "build_default_config",
    "validate_chain_id",
    "CHAIN_ID_MAP",
    # Production RPC client
    "ProductionRPCClient",
    "EndpointHealth",
    "EndpointStatus",
    "ChainIDMismatchError",
    "RPCError",
    "AllEndpointsFailedError",
    "get_rpc_client",
    "close_all_clients",
    # Nonce management
    "NonceManager",
    "PendingTransaction",
    "ReceiptValidation",
    "TransactionReceiptStatus",
    "NonceConflictError",
    "StuckTransactionError",
    "TransactionFailedError",
    "get_nonce_manager",
    # Simulation and gas estimation
    "TransactionSimulator",
    "GasEstimator",
    "SimulationAndEstimation",
    "SimulationOutput",
    "SimulationResult",
    "GasEstimation",
    "SimulationError",
    "GasEstimationError",
    "get_simulation_service",
    # Confirmation tracking
    "ConfirmationTracker",
    "TrackedTransaction",
    "ConfirmationStatus",
    "ReorgEvent",
    "ReorgSeverity",
    "BlockInfo",
    "ReorgError",
    "get_confirmation_tracker",
    "close_all_trackers",
    # Logging
    "ChainLogger",
    "OperationType",
    "OperationContext",
    "RPCCallLog",
    "TransactionLog",
    "LogLevel",
    "get_chain_logger",
    "log_operation",
    "setup_logging",
]

# Version
__version__ = "0.2.0"
