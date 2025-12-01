"""
Smart Contract Integration Service

This module provides the Python interface to Sardis smart contracts.
It handles wallet deployment, payment execution, and escrow management
on EVM chains.

Architecture:
- Uses web3.py for blockchain interaction
- Supports multiple chains (Base, Polygon, Ethereum)
- Abstracts gas management
- Provides async interface for non-blocking operations
"""

import os
import json
from typing import Optional, Dict, List, Tuple
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncio
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from web3.middleware import geth_poa_middleware

from sardis_core.config import get_settings


class ChainNetwork(Enum):
    """Supported blockchain networks."""
    BASE_SEPOLIA = "base_sepolia"
    POLYGON_AMOY = "polygon_amoy"
    SEPOLIA = "sepolia"
    LOCAL = "local"


@dataclass
class NetworkConfig:
    """Network configuration."""
    chain_id: int
    rpc_url: str
    explorer_url: str
    usdc_address: str
    factory_address: Optional[str] = None
    escrow_address: Optional[str] = None


@dataclass
class WalletInfo:
    """On-chain wallet information."""
    address: str
    agent: str
    limit_per_tx: Decimal
    daily_limit: Decimal
    spent_today: Decimal
    is_paused: bool


@dataclass
class TransactionResult:
    """Result of a blockchain transaction."""
    success: bool
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    error: Optional[str] = None
    explorer_url: Optional[str] = None


# Contract ABIs (simplified, full ABIs would be loaded from compiled contracts)
WALLET_FACTORY_ABI = json.loads('''[
    {"inputs":[{"internalType":"address","name":"agent","type":"address"}],
     "name":"createWallet","outputs":[{"internalType":"address","name":"wallet","type":"address"}],
     "stateMutability":"payable","type":"function"},
    {"inputs":[{"internalType":"address","name":"agent","type":"address"}],
     "name":"getAgentWallets","outputs":[{"internalType":"address[]","name":"","type":"address[]"}],
     "stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"wallet","type":"address"}],
     "name":"verifyWallet","outputs":[{"internalType":"bool","name":"","type":"bool"}],
     "stateMutability":"view","type":"function"},
    {"inputs":[],"name":"getTotalWallets","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
     "stateMutability":"view","type":"function"}
]''')

AGENT_WALLET_ABI = json.loads('''[
    {"inputs":[{"internalType":"address","name":"token","type":"address"},
               {"internalType":"address","name":"to","type":"address"},
               {"internalType":"uint256","name":"amount","type":"uint256"},
               {"internalType":"string","name":"purpose","type":"string"}],
     "name":"pay","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],
     "stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"merchant","type":"address"},
               {"internalType":"address","name":"token","type":"address"},
               {"internalType":"uint256","name":"amount","type":"uint256"},
               {"internalType":"uint256","name":"duration","type":"uint256"}],
     "name":"createHold","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],
     "stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"bytes32","name":"holdId","type":"bytes32"},
               {"internalType":"uint256","name":"captureAmount","type":"uint256"}],
     "name":"captureHold","outputs":[],
     "stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"bytes32","name":"holdId","type":"bytes32"}],
     "name":"voidHold","outputs":[],
     "stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"token","type":"address"}],
     "name":"getBalance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
     "stateMutability":"view","type":"function"},
    {"inputs":[],"name":"getRemainingDailyLimit","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
     "stateMutability":"view","type":"function"},
    {"inputs":[],"name":"limitPerTx","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
     "stateMutability":"view","type":"function"},
    {"inputs":[],"name":"dailyLimit","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
     "stateMutability":"view","type":"function"},
    {"inputs":[],"name":"spentToday","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
     "stateMutability":"view","type":"function"},
    {"inputs":[],"name":"agent","outputs":[{"internalType":"address","name":"","type":"address"}],
     "stateMutability":"view","type":"function"}
]''')

ESCROW_ABI = json.loads('''[
    {"inputs":[{"internalType":"address","name":"seller","type":"address"},
               {"internalType":"address","name":"token","type":"address"},
               {"internalType":"uint256","name":"amount","type":"uint256"},
               {"internalType":"uint256","name":"deadline","type":"uint256"},
               {"internalType":"bytes32","name":"conditionHash","type":"bytes32"},
               {"internalType":"string","name":"description","type":"string"}],
     "name":"createEscrow","outputs":[{"internalType":"uint256","name":"escrowId","type":"uint256"}],
     "stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"escrowId","type":"uint256"}],
     "name":"fundEscrow","outputs":[],
     "stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"escrowId","type":"uint256"}],
     "name":"approveRelease","outputs":[],
     "stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"escrowId","type":"uint256"}],
     "name":"getEscrow","outputs":[{"components":[
        {"internalType":"address","name":"buyer","type":"address"},
        {"internalType":"address","name":"seller","type":"address"},
        {"internalType":"address","name":"token","type":"address"},
        {"internalType":"uint256","name":"amount","type":"uint256"},
        {"internalType":"uint256","name":"fee","type":"uint256"},
        {"internalType":"uint256","name":"createdAt","type":"uint256"},
        {"internalType":"uint256","name":"deadline","type":"uint256"},
        {"internalType":"uint8","name":"state","type":"uint8"},
        {"internalType":"bytes32","name":"conditionHash","type":"bytes32"},
        {"internalType":"bool","name":"buyerApproved","type":"bool"},
        {"internalType":"bool","name":"sellerConfirmed","type":"bool"},
        {"internalType":"string","name":"description","type":"string"}
     ],"internalType":"struct SardisEscrow.Escrow","name":"","type":"tuple"}],
     "stateMutability":"view","type":"function"}
]''')

ERC20_ABI = json.loads('''[
    {"inputs":[{"internalType":"address","name":"spender","type":"address"},
               {"internalType":"uint256","name":"amount","type":"uint256"}],
     "name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],
     "stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],
     "name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
     "stateMutability":"view","type":"function"},
    {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],
     "stateMutability":"view","type":"function"}
]''')


# Network configurations
NETWORKS: Dict[ChainNetwork, NetworkConfig] = {
    ChainNetwork.BASE_SEPOLIA: NetworkConfig(
        chain_id=84532,
        rpc_url=os.getenv("BASE_SEPOLIA_RPC_URL", "https://sepolia.base.org"),
        explorer_url="https://sepolia.basescan.org",
        usdc_address="0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # Base Sepolia USDC
        factory_address=os.getenv("SARDIS_WALLET_FACTORY"),
        escrow_address=os.getenv("SARDIS_ESCROW"),
    ),
    ChainNetwork.POLYGON_AMOY: NetworkConfig(
        chain_id=80002,
        rpc_url=os.getenv("POLYGON_AMOY_RPC_URL", "https://rpc-amoy.polygon.technology"),
        explorer_url="https://amoy.polygonscan.com",
        usdc_address="0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582",  # Polygon Amoy USDC
        factory_address=os.getenv("SARDIS_WALLET_FACTORY_POLYGON"),
        escrow_address=os.getenv("SARDIS_ESCROW_POLYGON"),
    ),
    ChainNetwork.SEPOLIA: NetworkConfig(
        chain_id=11155111,
        rpc_url=os.getenv("SEPOLIA_RPC_URL", "https://rpc.sepolia.org"),
        explorer_url="https://sepolia.etherscan.io",
        usdc_address="0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",  # Sepolia USDC
        factory_address=os.getenv("SARDIS_WALLET_FACTORY_ETH"),
        escrow_address=os.getenv("SARDIS_ESCROW_ETH"),
    ),
    ChainNetwork.LOCAL: NetworkConfig(
        chain_id=31337,
        rpc_url="http://127.0.0.1:8545",
        explorer_url="",
        usdc_address="0x5FbDB2315678afecb367f032d93F642f64180aa3",  # Deployed locally
    ),
}


class ContractService:
    """
    Service for interacting with Sardis smart contracts.
    
    Handles:
    - Wallet factory operations (create, verify)
    - Agent wallet operations (pay, hold, capture)
    - Escrow operations (create, fund, release)
    - Gas estimation and management
    """
    
    def __init__(
        self,
        network: ChainNetwork = ChainNetwork.BASE_SEPOLIA,
        private_key: Optional[str] = None
    ):
        """
        Initialize the contract service.
        
        Args:
            network: Target blockchain network
            private_key: Sardis operator private key for signing transactions
        """
        self.network = network
        self.config = NETWORKS[network]
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
        
        # Add PoA middleware for networks that need it
        if network in [ChainNetwork.POLYGON_AMOY]:
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Set up account
        if private_key:
            self.account = Account.from_key(private_key)
            self.w3.eth.default_account = self.account.address
        else:
            self.account = None
        
        # Initialize contracts
        self._init_contracts()
    
    def _init_contracts(self):
        """Initialize contract instances."""
        if self.config.factory_address:
            self.factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.config.factory_address),
                abi=WALLET_FACTORY_ABI
            )
        else:
            self.factory = None
        
        if self.config.escrow_address:
            self.escrow = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.config.escrow_address),
                abi=ESCROW_ABI
            )
        else:
            self.escrow = None
        
        self.usdc = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.config.usdc_address),
            abi=ERC20_ABI
        )
    
    def is_connected(self) -> bool:
        """Check if connected to the network."""
        try:
            return self.w3.is_connected()
        except:
            return False
    
    def get_network_info(self) -> Dict:
        """Get current network information."""
        return {
            "network": self.network.value,
            "chain_id": self.config.chain_id,
            "connected": self.is_connected(),
            "block_number": self.w3.eth.block_number if self.is_connected() else None,
            "factory_deployed": self.config.factory_address is not None,
            "escrow_deployed": self.config.escrow_address is not None,
        }
    
    # ==================== Wallet Factory ====================
    
    async def create_wallet(self, agent_address: str) -> TransactionResult:
        """
        Create a new on-chain wallet for an agent.
        
        Args:
            agent_address: Ethereum address of the agent
            
        Returns:
            TransactionResult with wallet address
        """
        if not self.factory:
            return TransactionResult(success=False, error="Factory not deployed")
        
        if not self.account:
            return TransactionResult(success=False, error="No signer configured")
        
        try:
            agent = Web3.to_checksum_address(agent_address)
            
            # Build transaction
            tx = self.factory.functions.createWallet(agent).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 2000000,
                'gasPrice': self.w3.eth.gas_price,
            })
            
            # Sign and send
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            # Get wallet address from logs
            wallet_address = None
            for log in receipt['logs']:
                if log['topics'][0].hex() == Web3.keccak(text="WalletCreated(address,address,uint256,uint256)").hex():
                    wallet_address = "0x" + log['topics'][2].hex()[-40:]
            
            return TransactionResult(
                success=receipt['status'] == 1,
                tx_hash=tx_hash.hex(),
                block_number=receipt['blockNumber'],
                gas_used=receipt['gasUsed'],
                explorer_url=f"{self.config.explorer_url}/tx/{tx_hash.hex()}"
            )
            
        except Exception as e:
            return TransactionResult(success=False, error=str(e))
    
    def get_agent_wallets(self, agent_address: str) -> List[str]:
        """Get all wallets for an agent."""
        if not self.factory:
            return []
        
        try:
            agent = Web3.to_checksum_address(agent_address)
            return self.factory.functions.getAgentWallets(agent).call()
        except:
            return []
    
    def verify_wallet(self, wallet_address: str) -> bool:
        """Verify a wallet was created by Sardis factory."""
        if not self.factory:
            return False
        
        try:
            wallet = Web3.to_checksum_address(wallet_address)
            return self.factory.functions.verifyWallet(wallet).call()
        except:
            return False
    
    # ==================== Agent Wallet ====================
    
    def get_wallet_contract(self, wallet_address: str):
        """Get contract instance for an agent wallet."""
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(wallet_address),
            abi=AGENT_WALLET_ABI
        )
    
    def get_wallet_info(self, wallet_address: str) -> Optional[WalletInfo]:
        """Get on-chain wallet information."""
        try:
            wallet = self.get_wallet_contract(wallet_address)
            
            return WalletInfo(
                address=wallet_address,
                agent=wallet.functions.agent().call(),
                limit_per_tx=Decimal(wallet.functions.limitPerTx().call()) / Decimal(10**6),
                daily_limit=Decimal(wallet.functions.dailyLimit().call()) / Decimal(10**6),
                spent_today=Decimal(wallet.functions.spentToday().call()) / Decimal(10**6),
                is_paused=False,  # Would need to add to contract
            )
        except Exception as e:
            print(f"Error getting wallet info: {e}")
            return None
    
    def get_wallet_balance(self, wallet_address: str) -> Decimal:
        """Get USDC balance of a wallet."""
        try:
            wallet = Web3.to_checksum_address(wallet_address)
            balance = self.usdc.functions.balanceOf(wallet).call()
            return Decimal(balance) / Decimal(10**6)  # USDC has 6 decimals
        except:
            return Decimal("0")
    
    async def execute_payment(
        self,
        wallet_address: str,
        to_address: str,
        amount: Decimal,
        purpose: str
    ) -> TransactionResult:
        """
        Execute a payment from an agent wallet.
        
        Args:
            wallet_address: Agent's on-chain wallet
            to_address: Recipient address
            amount: Amount in USDC (decimal)
            purpose: Payment description
            
        Returns:
            TransactionResult
        """
        if not self.account:
            return TransactionResult(success=False, error="No signer configured")
        
        try:
            wallet = self.get_wallet_contract(wallet_address)
            amount_raw = int(amount * Decimal(10**6))  # Convert to 6 decimals
            
            tx = wallet.functions.pay(
                self.config.usdc_address,
                Web3.to_checksum_address(to_address),
                amount_raw,
                purpose
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return TransactionResult(
                success=receipt['status'] == 1,
                tx_hash=tx_hash.hex(),
                block_number=receipt['blockNumber'],
                gas_used=receipt['gasUsed'],
                explorer_url=f"{self.config.explorer_url}/tx/{tx_hash.hex()}"
            )
            
        except Exception as e:
            return TransactionResult(success=False, error=str(e))
    
    async def create_hold(
        self,
        wallet_address: str,
        merchant_address: str,
        amount: Decimal,
        duration_seconds: int = 3600
    ) -> Tuple[TransactionResult, Optional[str]]:
        """
        Create a pre-authorization hold on wallet.
        
        Returns:
            Tuple of (TransactionResult, hold_id)
        """
        if not self.account:
            return TransactionResult(success=False, error="No signer configured"), None
        
        try:
            wallet = self.get_wallet_contract(wallet_address)
            amount_raw = int(amount * Decimal(10**6))
            
            tx = wallet.functions.createHold(
                Web3.to_checksum_address(merchant_address),
                self.config.usdc_address,
                amount_raw,
                duration_seconds
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            # Extract hold_id from logs
            hold_id = None
            for log in receipt['logs']:
                if len(log['topics']) >= 2:
                    hold_id = log['topics'][1].hex()
                    break
            
            return TransactionResult(
                success=receipt['status'] == 1,
                tx_hash=tx_hash.hex(),
                block_number=receipt['blockNumber'],
                gas_used=receipt['gasUsed'],
                explorer_url=f"{self.config.explorer_url}/tx/{tx_hash.hex()}"
            ), hold_id
            
        except Exception as e:
            return TransactionResult(success=False, error=str(e)), None
    
    # ==================== Escrow ====================
    
    async def create_escrow(
        self,
        seller_address: str,
        amount: Decimal,
        deadline_timestamp: int,
        description: str
    ) -> Tuple[TransactionResult, Optional[int]]:
        """
        Create an escrow for agent-to-agent payment.
        
        Returns:
            Tuple of (TransactionResult, escrow_id)
        """
        if not self.escrow or not self.account:
            return TransactionResult(success=False, error="Escrow not configured"), None
        
        try:
            amount_raw = int(amount * Decimal(10**6))
            condition_hash = Web3.keccak(text=description)
            
            tx = self.escrow.functions.createEscrow(
                Web3.to_checksum_address(seller_address),
                self.config.usdc_address,
                amount_raw,
                deadline_timestamp,
                condition_hash,
                description
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price,
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            # Get escrow ID from logs
            escrow_id = None
            for log in receipt['logs']:
                if len(log['topics']) >= 2:
                    escrow_id = int(log['topics'][1].hex(), 16)
                    break
            
            return TransactionResult(
                success=receipt['status'] == 1,
                tx_hash=tx_hash.hex(),
                block_number=receipt['blockNumber'],
                gas_used=receipt['gasUsed'],
                explorer_url=f"{self.config.explorer_url}/tx/{tx_hash.hex()}"
            ), escrow_id
            
        except Exception as e:
            return TransactionResult(success=False, error=str(e)), None
    
    # ==================== Utilities ====================
    
    def estimate_gas(self, amount: Decimal) -> Dict:
        """Estimate gas for a payment transaction."""
        try:
            gas_price = self.w3.eth.gas_price
            gas_limit = 200000  # Typical for ERC20 + wallet logic
            
            gas_cost_wei = gas_price * gas_limit
            gas_cost_eth = Decimal(gas_cost_wei) / Decimal(10**18)
            
            return {
                "gas_limit": gas_limit,
                "gas_price_gwei": float(gas_price / 10**9),
                "estimated_cost_eth": float(gas_cost_eth),
                "estimated_cost_usd": float(gas_cost_eth * Decimal("2000")),  # Rough ETH price
            }
        except:
            return {"error": "Could not estimate gas"}
    
    def get_explorer_url(self, tx_hash: str) -> str:
        """Get block explorer URL for a transaction."""
        return f"{self.config.explorer_url}/tx/{tx_hash}"


# Singleton instance
_contract_service: Optional[ContractService] = None


def get_contract_service(
    network: ChainNetwork = ChainNetwork.BASE_SEPOLIA,
    private_key: Optional[str] = None
) -> ContractService:
    """Get or create the contract service singleton."""
    global _contract_service
    
    if _contract_service is None:
        settings = get_settings()
        pk = private_key or os.getenv("SARDIS_PRIVATE_KEY")
        _contract_service = ContractService(network=network, private_key=pk)
    
    return _contract_service

