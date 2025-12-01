"""Blockchain service for real on-chain transactions.

This module provides blockchain connectivity for Sardis payments.
It supports both simulation mode (for development) and real blockchain mode.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
import secrets
import logging

from sardis_core.config import settings

# Optional web3 import - gracefully handle if not installed
try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    from eth_account import Account
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class OnChainTransaction:
    """Record of an on-chain transaction."""
    internal_tx_id: str  # Sardis internal transaction ID
    chain: str
    tx_hash: str
    from_address: str
    to_address: str
    amount: Decimal
    token_symbol: str
    status: str  # pending, confirmed, failed
    block_number: Optional[int] = None
    block_hash: Optional[str] = None
    gas_used: Optional[int] = None
    explorer_url: Optional[str] = None
    created_at: datetime = None
    confirmed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class BlockchainService:
    """
    Service for managing blockchain transactions.
    
    Supports multiple modes:
    - simulation: No real blockchain interaction (default for development)
    - testnet: Real transactions on testnets (Base Sepolia, etc.)
    - mainnet: Real transactions on mainnets (requires proper configuration)
    
    Usage:
        service = BlockchainService(mode="testnet")
        
        # Submit a payment to the blockchain
        result = await service.submit_payment(
            internal_tx_id="tx_123",
            from_wallet="0x...",
            to_wallet="0x...",
            amount=Decimal("10.00"),
            token_symbol="USDC",
            private_key="0x..."  # In production, use secure key management
        )
        
        # Check transaction status
        status = await service.get_transaction_status(result.tx_hash)
    """
    
    # Chain configurations
    CHAINS = {
        "base_sepolia": {
            "chain_id": 84532,
            "rpc_url": settings.base_sepolia_rpc,
            "usdc_address": settings.base_sepolia_usdc,
            "explorer": "https://sepolia.basescan.org",
        },
        "ethereum_sepolia": {
            "chain_id": 11155111,
            "rpc_url": settings.ethereum_sepolia_rpc,
            "usdc_address": settings.ethereum_sepolia_usdc,
            "explorer": "https://sepolia.etherscan.io",
        },
        "polygon_amoy": {
            "chain_id": 80002,
            "rpc_url": settings.polygon_amoy_rpc,
            "usdc_address": settings.polygon_amoy_usdc,
            "explorer": "https://amoy.polygonscan.com",
        },
    }
    
    # ERC-20 transfer ABI
    ERC20_TRANSFER_ABI = [
        {
            "constant": False,
            "inputs": [
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        },
    ]
    
    def __init__(
        self,
        mode: str = "simulation",
        default_chain: str = "base_sepolia"
    ):
        """
        Initialize blockchain service.
        
        Args:
            mode: Operation mode - "simulation", "testnet", or "mainnet"
            default_chain: Default chain for transactions
        """
        self.mode = mode
        self.default_chain = default_chain
        self._transactions: Dict[str, OnChainTransaction] = {}
        self._web3_instances: Dict[str, Any] = {}
        
        # Initialize Web3 connections if available and not in simulation mode
        if mode != "simulation" and WEB3_AVAILABLE:
            self._init_web3_connections()
        elif mode != "simulation" and not WEB3_AVAILABLE:
            logger.warning("web3.py not installed - falling back to simulation mode")
            self.mode = "simulation"
    
    def _init_web3_connections(self):
        """Initialize Web3 connections to configured chains."""
        for chain_name, config in self.CHAINS.items():
            try:
                w3 = Web3(Web3.HTTPProvider(config["rpc_url"]))
                
                # Polygon needs POA middleware
                if "polygon" in chain_name:
                    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
                if w3.is_connected():
                    self._web3_instances[chain_name] = w3
                    logger.info(f"Connected to {chain_name}")
                else:
                    logger.warning(f"Could not connect to {chain_name}")
            except Exception as e:
                logger.error(f"Error connecting to {chain_name}: {e}")
    
    @property
    def is_real_blockchain(self) -> bool:
        """Check if service is configured for real blockchain transactions."""
        return self.mode in ["testnet", "mainnet"] and len(self._web3_instances) > 0
    
    async def submit_payment(
        self,
        internal_tx_id: str,
        from_address: str,
        to_address: str,
        amount: Decimal,
        token_symbol: str = "USDC",
        private_key: Optional[str] = None,
        chain: Optional[str] = None
    ) -> OnChainTransaction:
        """
        Submit a payment to the blockchain.
        
        Args:
            internal_tx_id: Sardis internal transaction ID
            from_address: Sender wallet address
            to_address: Recipient wallet address
            amount: Amount to send (in token units, e.g., 10.00 USDC)
            token_symbol: Token to send (default: USDC)
            private_key: Sender's private key (required for real transactions)
            chain: Chain to use (default: base_sepolia)
            
        Returns:
            OnChainTransaction with status and hash
        """
        chain = chain or self.default_chain
        
        if self.mode == "simulation":
            return await self._simulate_transaction(
                internal_tx_id, from_address, to_address, amount, token_symbol, chain
            )
        else:
            return await self._real_transaction(
                internal_tx_id, from_address, to_address, amount, 
                token_symbol, private_key, chain
            )
    
    async def _simulate_transaction(
        self,
        internal_tx_id: str,
        from_address: str,
        to_address: str,
        amount: Decimal,
        token_symbol: str,
        chain: str
    ) -> OnChainTransaction:
        """Simulate a blockchain transaction."""
        # Generate fake transaction hash
        tx_hash = "0x" + secrets.token_hex(32)
        
        chain_config = self.CHAINS.get(chain, self.CHAINS[self.default_chain])
        
        tx = OnChainTransaction(
            internal_tx_id=internal_tx_id,
            chain=chain,
            tx_hash=tx_hash,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            token_symbol=token_symbol,
            status="confirmed",  # Simulation always succeeds immediately
            block_number=1234567,
            block_hash="0x" + secrets.token_hex(32),
            gas_used=65000,
            explorer_url=f"{chain_config['explorer']}/tx/{tx_hash}",
            confirmed_at=datetime.now(timezone.utc)
        )
        
        self._transactions[tx_hash] = tx
        logger.info(f"Simulated transaction: {tx_hash}")
        return tx
    
    async def _real_transaction(
        self,
        internal_tx_id: str,
        from_address: str,
        to_address: str,
        amount: Decimal,
        token_symbol: str,
        private_key: str,
        chain: str
    ) -> OnChainTransaction:
        """Execute a real blockchain transaction."""
        if chain not in self._web3_instances:
            raise ValueError(f"Chain {chain} not connected")
        
        if not private_key:
            raise ValueError("Private key required for real transactions")
        
        w3 = self._web3_instances[chain]
        chain_config = self.CHAINS[chain]
        
        # Get USDC contract
        usdc_address = chain_config["usdc_address"]
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(usdc_address),
            abi=self.ERC20_TRANSFER_ABI
        )
        
        # Convert amount to token units (USDC has 6 decimals)
        amount_units = int(amount * Decimal("1000000"))
        
        # Build transaction
        account = Account.from_key(private_key)
        nonce = w3.eth.get_transaction_count(account.address)
        gas_price = w3.eth.gas_price
        
        tx = contract.functions.transfer(
            Web3.to_checksum_address(to_address),
            amount_units
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': gas_price,
            'chainId': chain_config["chain_id"]
        })
        
        # Sign and send
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hash_hex = tx_hash.hex()
        
        # Create pending record
        on_chain_tx = OnChainTransaction(
            internal_tx_id=internal_tx_id,
            chain=chain,
            tx_hash=tx_hash_hex,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            token_symbol=token_symbol,
            status="pending",
            explorer_url=f"{chain_config['explorer']}/tx/{tx_hash_hex}"
        )
        
        self._transactions[tx_hash_hex] = on_chain_tx
        logger.info(f"Submitted transaction: {tx_hash_hex}")
        
        # Wait for confirmation in background
        asyncio.create_task(self._wait_for_confirmation(tx_hash_hex, chain))
        
        return on_chain_tx
    
    async def _wait_for_confirmation(
        self,
        tx_hash: str,
        chain: str,
        timeout_seconds: int = 120
    ):
        """Wait for transaction confirmation."""
        w3 = self._web3_instances.get(chain)
        if not w3:
            return
        
        start_time = datetime.now(timezone.utc)
        
        while True:
            try:
                receipt = w3.eth.get_transaction_receipt(tx_hash)
                
                if receipt:
                    tx = self._transactions.get(tx_hash)
                    if tx:
                        tx.status = "confirmed" if receipt["status"] == 1 else "failed"
                        tx.block_number = receipt["blockNumber"]
                        tx.block_hash = receipt["blockHash"].hex()
                        tx.gas_used = receipt["gasUsed"]
                        tx.confirmed_at = datetime.now(timezone.utc)
                        
                        logger.info(f"Transaction {tx_hash} confirmed: {tx.status}")
                    return
                    
            except Exception as e:
                logger.debug(f"Waiting for confirmation: {e}")
            
            # Check timeout
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed > timeout_seconds:
                tx = self._transactions.get(tx_hash)
                if tx:
                    tx.status = "timeout"
                logger.warning(f"Transaction {tx_hash} confirmation timeout")
                return
            
            await asyncio.sleep(2)
    
    async def get_transaction_status(self, tx_hash: str) -> Optional[OnChainTransaction]:
        """Get transaction status by hash."""
        return self._transactions.get(tx_hash)
    
    async def get_on_chain_balance(
        self,
        address: str,
        token_symbol: str = "USDC",
        chain: Optional[str] = None
    ) -> Decimal:
        """
        Get on-chain token balance.
        
        Args:
            address: Wallet address
            token_symbol: Token symbol
            chain: Chain to query
            
        Returns:
            Balance as Decimal
        """
        chain = chain or self.default_chain
        
        if self.mode == "simulation":
            # Return mock balance
            return Decimal("1000.00")
        
        if chain not in self._web3_instances:
            raise ValueError(f"Chain {chain} not connected")
        
        w3 = self._web3_instances[chain]
        chain_config = self.CHAINS[chain]
        
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(chain_config["usdc_address"]),
            abi=self.ERC20_TRANSFER_ABI
        )
        
        balance_units = contract.functions.balanceOf(
            Web3.to_checksum_address(address)
        ).call()
        
        return Decimal(balance_units) / Decimal("1000000")
    
    async def get_gas_estimate(
        self,
        chain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get current gas estimate for a chain.
        
        Returns:
            Dict with gas price and estimated cost
        """
        chain = chain or self.default_chain
        
        if self.mode == "simulation" or chain not in self._web3_instances:
            # Return mock estimate
            return {
                "chain": chain,
                "gas_price_gwei": 0.001,
                "estimated_gas": 65000,
                "estimated_cost_native": "0.000065",
                "estimated_cost_usd": "0.00015"  # Approximate
            }
        
        w3 = self._web3_instances[chain]
        gas_price = w3.eth.gas_price
        gas_price_gwei = gas_price / 10**9
        estimated_gas = 65000
        estimated_cost = (gas_price * estimated_gas) / 10**18
        
        return {
            "chain": chain,
            "gas_price_gwei": gas_price_gwei,
            "estimated_gas": estimated_gas,
            "estimated_cost_native": str(estimated_cost),
            "estimated_cost_usd": str(estimated_cost * 2500)  # Rough ETH price
        }
    
    def get_transactions_for_internal_id(
        self,
        internal_tx_id: str
    ) -> List[OnChainTransaction]:
        """Get all on-chain transactions for an internal transaction ID."""
        return [
            tx for tx in self._transactions.values()
            if tx.internal_tx_id == internal_tx_id
        ]
    
    def get_explorer_url(self, tx_hash: str) -> Optional[str]:
        """Get block explorer URL for a transaction."""
        tx = self._transactions.get(tx_hash)
        return tx.explorer_url if tx else None


# Global instance
_blockchain_service: Optional[BlockchainService] = None


def get_blockchain_service() -> BlockchainService:
    """Get or create the blockchain service instance."""
    global _blockchain_service
    
    if _blockchain_service is None:
        # Determine mode from settings
        if settings.enable_real_blockchain:
            mode = "testnet"  # Default to testnet for safety
        else:
            mode = "simulation"
        
        _blockchain_service = BlockchainService(mode=mode)
    
    return _blockchain_service

