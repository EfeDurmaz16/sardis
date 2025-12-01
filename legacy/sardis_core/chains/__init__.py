"""Chain abstraction layer for multi-chain support."""

from .base import BaseChain, ChainType, ChainConfig, TokenType
from .evm import EVMChain
from .solana import SolanaChain
from .router import ChainRouter
from .chain_manager import ChainManager, get_chain_manager, SettlementMode
from .gas_service import GasService, get_gas_service, GasEstimate, GasPriceLevel
from .blockchain_service import BlockchainService, get_blockchain_service, OnChainTransaction

__all__ = [
    "BaseChain",
    "ChainType",
    "ChainConfig",
    "TokenType",
    "EVMChain",
    "SolanaChain",
    "ChainRouter",
    # Settlement
    "ChainManager",
    "get_chain_manager",
    "SettlementMode",
    # Gas
    "GasService",
    "get_gas_service",
    "GasEstimate",
    "GasPriceLevel",
    # Blockchain service
    "BlockchainService",
    "get_blockchain_service",
    "OnChainTransaction",
]

