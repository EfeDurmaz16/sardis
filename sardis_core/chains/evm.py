"""EVM-compatible chain implementation (Base, Ethereum, Polygon)."""

from decimal import Decimal
from typing import Optional
import secrets
import hashlib

from .base import BaseChain, ChainConfig, ChainType, TokenType, OnChainTransaction


class EVMChain(BaseChain):
    """
    Implementation for EVM-compatible blockchains.
    
    Supports Base, Ethereum, and Polygon networks.
    
    Note: This is a simulation layer for the MVP. In production,
    this would use web3.py or similar to interact with real chains.
    """
    
    # ERC-20 token decimals (most stablecoins use 6)
    TOKEN_DECIMALS = {
        TokenType.USDC: 6,
        TokenType.USDT: 6,
        TokenType.PYUSD: 6,
        TokenType.EURC: 6,
    }
    
    def __init__(self, config: ChainConfig):
        """Initialize EVM chain interface."""
        super().__init__(config)
        
        # Simulated balances for MVP (in production, query chain)
        self._simulated_balances: dict[str, dict[TokenType, Decimal]] = {}
        self._simulated_transactions: dict[str, OnChainTransaction] = {}
    
    async def get_balance(
        self,
        address: str,
        token: TokenType = TokenType.USDC
    ) -> Decimal:
        """Get token balance for an address."""
        if not await self.is_valid_address(address):
            raise ValueError(f"Invalid address: {address}")
        
        if not self.supports_token(token):
            raise ValueError(f"Token {token} not supported on {self.chain_type}")
        
        # In production: query ERC-20 balanceOf
        # For MVP: return simulated balance
        address_balances = self._simulated_balances.get(address.lower(), {})
        return address_balances.get(token, Decimal("0"))
    
    async def transfer(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
        token: TokenType = TokenType.USDC,
        private_key: Optional[str] = None
    ) -> OnChainTransaction:
        """Execute a token transfer."""
        # Validate addresses
        if not await self.is_valid_address(from_address):
            raise ValueError(f"Invalid from address: {from_address}")
        if not await self.is_valid_address(to_address):
            raise ValueError(f"Invalid to address: {to_address}")
        
        if not self.supports_token(token):
            raise ValueError(f"Token {token} not supported on {self.chain_type}")
        
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Check balance
        balance = await self.get_balance(from_address, token)
        if balance < amount:
            raise ValueError(f"Insufficient balance: {balance} < {amount}")
        
        # Generate transaction hash
        tx_hash = self._generate_tx_hash()
        
        # Simulate the transfer
        from_addr = from_address.lower()
        to_addr = to_address.lower()
        
        # Update balances
        if from_addr not in self._simulated_balances:
            self._simulated_balances[from_addr] = {}
        if to_addr not in self._simulated_balances:
            self._simulated_balances[to_addr] = {}
        
        self._simulated_balances[from_addr][token] = balance - amount
        to_balance = self._simulated_balances[to_addr].get(token, Decimal("0"))
        self._simulated_balances[to_addr][token] = to_balance + amount
        
        # Create transaction record
        tx = OnChainTransaction(
            tx_hash=tx_hash,
            chain=self.chain_type,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            token=token,
            status="confirmed",
            block_number=self._generate_block_number(),
            gas_used=65000,
            gas_price=1000000000,  # 1 gwei
            confirmations=12
        )
        
        self._simulated_transactions[tx_hash] = tx
        return tx
    
    async def get_transaction(self, tx_hash: str) -> Optional[OnChainTransaction]:
        """Get transaction details by hash."""
        return self._simulated_transactions.get(tx_hash)
    
    async def estimate_gas(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
        token: TokenType = TokenType.USDC
    ) -> Decimal:
        """Estimate gas cost for a transfer."""
        # ERC-20 transfer typically costs ~65,000 gas
        gas_limit = 65000
        
        # Get current gas price (simulated)
        gas_price_gwei = self._get_current_gas_price()
        
        # Calculate cost in ETH
        gas_cost_wei = gas_limit * gas_price_gwei * 1_000_000_000
        gas_cost_eth = Decimal(gas_cost_wei) / Decimal(10**18)
        
        return gas_cost_eth
    
    async def create_wallet(self) -> tuple[str, str]:
        """
        Create a new wallet.
        
        Returns:
            Tuple of (address, private_key)
        """
        # Generate random private key (32 bytes)
        private_key = secrets.token_hex(32)
        
        # Derive address (simplified - in production use proper EC derivation)
        address = self._derive_address(private_key)
        
        # Initialize balances
        self._simulated_balances[address.lower()] = {}
        
        return address, private_key
    
    async def is_valid_address(self, address: str) -> bool:
        """Check if an address is valid for EVM chains."""
        if not address:
            return False
        
        # EVM addresses are 42 characters (0x + 40 hex chars)
        if not address.startswith("0x"):
            return False
        
        if len(address) != 42:
            return False
        
        try:
            int(address, 16)
            return True
        except ValueError:
            return False
    
    async def get_token_info(self, token: TokenType) -> dict:
        """Get token contract information."""
        if not self.supports_token(token):
            raise ValueError(f"Token {token} not supported on {self.chain_type}")
        
        return {
            "name": self._get_token_name(token),
            "symbol": token.value,
            "decimals": self.TOKEN_DECIMALS.get(token, 6),
            "contract_address": self.config.token_addresses.get(token),
            "chain": self.chain_type.value,
        }
    
    def fund_wallet(self, address: str, amount: Decimal, token: TokenType = TokenType.USDC):
        """
        Fund a wallet with tokens (for testing/simulation).
        
        In production, this would be done via on-chain transfers.
        """
        addr = address.lower()
        if addr not in self._simulated_balances:
            self._simulated_balances[addr] = {}
        
        current = self._simulated_balances[addr].get(token, Decimal("0"))
        self._simulated_balances[addr][token] = current + amount
    
    def _generate_tx_hash(self) -> str:
        """Generate a simulated transaction hash."""
        random_bytes = secrets.token_bytes(32)
        return "0x" + random_bytes.hex()
    
    def _generate_block_number(self) -> int:
        """Generate a simulated block number."""
        import time
        # Approximate block number based on time
        base_block = 10000000
        return base_block + int(time.time() / 12)  # ~12 sec per block
    
    def _get_current_gas_price(self) -> int:
        """Get current gas price in gwei (simulated)."""
        # Return reasonable gas prices per chain
        gas_prices = {
            ChainType.BASE: 1,       # Base has very low fees
            ChainType.POLYGON: 30,   # Polygon is cheap
            ChainType.ETHEREUM: 20,  # ETH mainnet
        }
        return gas_prices.get(self.chain_type, 10)
    
    def _derive_address(self, private_key: str) -> str:
        """Derive address from private key (simplified)."""
        # In production, use proper secp256k1 EC derivation
        # This is a simulation for MVP
        hash_bytes = hashlib.sha256(bytes.fromhex(private_key)).digest()
        address_bytes = hashlib.sha256(hash_bytes).digest()[-20:]
        return "0x" + address_bytes.hex()
    
    def _get_token_name(self, token: TokenType) -> str:
        """Get full token name."""
        names = {
            TokenType.USDC: "USD Coin",
            TokenType.USDT: "Tether USD",
            TokenType.PYUSD: "PayPal USD",
            TokenType.EURC: "Euro Coin",
        }
        return names.get(token, token.value)


# Convenience factory functions
def create_base_chain(testnet: bool = False) -> EVMChain:
    """Create a Base chain instance."""
    from .base import DEFAULT_CONFIGS
    config = DEFAULT_CONFIGS[ChainType.BASE]
    config.is_testnet = testnet
    return EVMChain(config)


def create_ethereum_chain(testnet: bool = False) -> EVMChain:
    """Create an Ethereum chain instance."""
    from .base import DEFAULT_CONFIGS
    config = DEFAULT_CONFIGS[ChainType.ETHEREUM]
    config.is_testnet = testnet
    return EVMChain(config)


def create_polygon_chain(testnet: bool = False) -> EVMChain:
    """Create a Polygon chain instance."""
    from .base import DEFAULT_CONFIGS
    config = DEFAULT_CONFIGS[ChainType.POLYGON]
    config.is_testnet = testnet
    return EVMChain(config)

