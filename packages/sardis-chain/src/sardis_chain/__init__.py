"""Sardis Chain - Production-grade multi-chain stablecoin executor.

This package provides the blockchain execution layer for stablecoin operations:
- Multi-chain support (Ethereum, Base, Polygon, Arbitrum)
- MPC custody integration (Turnkey, Lit Protocol, Fireblocks)
- Transaction execution with gas estimation
- Nonce management and confirmation tracking
- MEV protection and deposit monitoring

Version: 0.4.0
"""

from .cctp_forwarding import (
    FUNDING_SOURCE_CHAINS,
    CCTPForwardingService,
    ForwardingAddress,
    ForwardingDeposit,
    ForwardingStatus,
)
from .config import (
    ChainConfig,
    ChainId,
    GasConfig,
    RPCConfig,
    TokenConfig,
    TurnkeyConfig,
    load_chain_config,
)
from .confirmation import (
    ConfirmationStatus,
    ConfirmationTracker,
)
from .deposit_monitor import (
    Deposit,
    DepositMonitor,
    MonitorConfig,
)
from .erc4337 import (
    ENTRYPOINT_V07_BY_CHAIN,
    BundlerClient,
    BundlerConfig,
    ERC4337ProofArtifact,
    PaymasterClient,
    PaymasterConfig,
    SponsorCapExceeded,
    SponsorCapGuard,
    SponsoredUserOperation,
    StageCaps,
    UserOperation,
    get_entrypoint_v07,
    write_erc4337_proof_artifact,
)
from .executor import (
    EAS_ADDRESSES,
    PERMIT2_ADDRESS,
    SAFE_INFRASTRUCTURE,
    ChainExecutor,
    ChainRPCClient,
    FailoverMPCSigner,
    GasEstimate,
    GasPriceProtection,
    GasPriceSpikeError,
    MPCSignerPort,
    SimulatedMPCSigner,
    TransactionRequest,
    get_eas_address,
    get_sardis_contract_address,
    get_sardis_ledger_anchor,
    get_sardis_policy_module,
)
from .gas_optimizer import (
    ChainRoute,
    GasOptimizer,
    get_gas_optimizer,
)
from .gas_optimizer import (
    GasEstimate as GasOptimizerEstimate,
)
from .lit_signer import LitProtocolSigner
from .logging_utils import (
    ChainLogger,
    get_chain_logger,
    log_operation,
)
from .mev_protection import (
    FlashbotsProvider,
    MEVConfig,
    MEVProtectionService,
)
from .nonce_manager import (
    NonceConflictError,
    NonceManager,
    StuckTransactionError,
    TransactionFailedError,
)
from .price_oracle import (
    CHAIN_NATIVE_TOKEN,
    PriceOracle,
    get_price_oracle,
)
from .redis_nonce_manager import RedisNonceManager
from .rpc_client import (
    AllEndpointsFailedError,
    ChainIDMismatchError,
    ProductionRPCClient,
    RPCError,
    close_all_clients,
    get_rpc_client,
)
from .simulation import (
    GasEstimation,
    SimulationError,
    SimulationResult,
    TransactionSimulator,
)
from .wallet_manager import (
    WalletInfo,
    WalletManager,
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
    "LitProtocolSigner",
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
    # CCTP Forwarding
    "CCTPForwardingService",
    "ForwardingAddress",
    "ForwardingDeposit",
    "ForwardingStatus",
    "FUNDING_SOURCE_CHAINS",
]
