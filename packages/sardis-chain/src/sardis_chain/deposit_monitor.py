"""
Blockchain deposit monitoring for Sardis.

Monitors blockchain for incoming deposits to Sardis receive addresses
and triggers balance updates and card funding flows.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .executor import (
    ChainRPCClient,
    CHAIN_CONFIGS,
    STABLECOIN_ADDRESSES,
)

logger = logging.getLogger(__name__)


class DepositStatus(str, Enum):
    """Status of a detected deposit."""
    DETECTED = "detected"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    CREDITED = "credited"
    FAILED = "failed"


@dataclass
class Deposit:
    """A detected blockchain deposit."""
    deposit_id: str
    tx_hash: str
    chain: str
    token: str
    from_address: str
    to_address: str
    amount_minor: int
    decimals: int = 6
    block_number: int = 0
    confirmations: int = 0
    status: DepositStatus = DepositStatus.DETECTED
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None
    credited_at: Optional[datetime] = None
    agent_id: Optional[str] = None
    
    @property
    def amount_decimal(self) -> Decimal:
        """Get amount as decimal."""
        return Decimal(self.amount_minor) / Decimal(10 ** self.decimals)


@dataclass 
class MonitorConfig:
    """Configuration for deposit monitoring."""
    # Chains to monitor
    chains: List[str] = field(default_factory=lambda: ["base_sepolia"])
    
    # Confirmations required before crediting
    confirmations_required: int = 1
    
    # Poll interval in seconds
    poll_interval: float = 5.0
    
    # Maximum blocks to look back
    max_blocks_back: int = 1000
    
    # Minimum deposit amount (in minor units)
    min_deposit_minor: int = 100000  # 0.1 USDC
    
    # Whether to auto-start monitoring
    auto_start: bool = False


# ERC20 Transfer event signature
TRANSFER_EVENT_SIGNATURE = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


class DepositMonitor:
    """
    Monitors blockchain for deposits to Sardis addresses.
    
    Features:
    - Multi-chain monitoring
    - Confirmation tracking
    - Callback system for deposit events
    - Reconciliation support
    """
    
    def __init__(
        self,
        config: Optional[MonitorConfig] = None,
        receive_addresses: Optional[Dict[str, str]] = None,
    ):
        self._config = config or MonitorConfig()
        self._receive_addresses = receive_addresses or {}
        self._rpc_clients: Dict[str, ChainRPCClient] = {}
        self._deposits: Dict[str, Deposit] = {}
        self._last_blocks: Dict[str, int] = {}
        self._callbacks: List[Callable[[Deposit], None]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Address to agent mapping
        self._address_to_agent: Dict[str, str] = {}
    
    def add_receive_address(
        self,
        address: str,
        agent_id: str,
        chains: Optional[List[str]] = None,
    ) -> None:
        """Add a receive address to monitor."""
        address_lower = address.lower()
        self._address_to_agent[address_lower] = agent_id
        
        # For EVM chains, same address works on all chains
        for chain in chains or self._config.chains:
            if chain not in self._receive_addresses:
                self._receive_addresses[chain] = set()
            self._receive_addresses[chain].add(address_lower)
    
    def add_callback(self, callback: Callable[[Deposit], None]) -> None:
        """Add a callback for deposit events."""
        self._callbacks.append(callback)
    
    async def start(self) -> None:
        """Start the deposit monitor."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Deposit monitor started")
    
    async def stop(self) -> None:
        """Stop the deposit monitor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Deposit monitor stopped")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                for chain in self._config.chains:
                    await self._check_chain(chain)
                
                # Update confirmation counts
                await self._update_confirmations()
                
            except Exception as e:
                logger.error(f"Error in deposit monitor: {e}")
            
            await asyncio.sleep(self._config.poll_interval)
    
    async def _get_rpc_client(self, chain: str) -> ChainRPCClient:
        """Get or create RPC client for chain."""
        if chain not in self._rpc_clients:
            config = CHAIN_CONFIGS.get(chain)
            if not config:
                raise ValueError(f"Unknown chain: {chain}")
            self._rpc_clients[chain] = ChainRPCClient(config["rpc_url"], chain=chain)
        return self._rpc_clients[chain]
    
    async def _check_chain(self, chain: str) -> None:
        """Check a chain for new deposits."""
        rpc = await self._get_rpc_client(chain)
        
        # Get current block
        current_block = await rpc.get_block_number()
        
        # Determine start block
        if chain not in self._last_blocks:
            self._last_blocks[chain] = max(0, current_block - self._config.max_blocks_back)
        
        from_block = self._last_blocks[chain] + 1
        
        if from_block > current_block:
            return
        
        # Query transfer events for stablecoins we care about
        token_addresses = STABLECOIN_ADDRESSES.get(chain, {})
        receive_addresses = self._receive_addresses.get(chain, set())
        
        if not receive_addresses:
            return
        
        for token_symbol, token_address in token_addresses.items():
            await self._check_token_transfers(
                rpc=rpc,
                chain=chain,
                token_address=token_address,
                token_symbol=token_symbol,
                from_block=from_block,
                to_block=current_block,
                receive_addresses=receive_addresses,
            )
        
        self._last_blocks[chain] = current_block
    
    async def _check_token_transfers(
        self,
        rpc: ChainRPCClient,
        chain: str,
        token_address: str,
        token_symbol: str,
        from_block: int,
        to_block: int,
        receive_addresses: set,
    ) -> None:
        """Check for ERC20 transfers to our addresses."""
        try:
            # Build filter for Transfer events to our addresses
            logs = await rpc._call(
                "eth_getLogs",
                [{
                    "address": token_address,
                    "topics": [TRANSFER_EVENT_SIGNATURE],
                    "fromBlock": hex(from_block),
                    "toBlock": hex(to_block),
                }],
            )
            
            for log in logs or []:
                await self._process_transfer_log(
                    log=log,
                    chain=chain,
                    token_symbol=token_symbol,
                    receive_addresses=receive_addresses,
                )
                
        except Exception as e:
            logger.warning(f"Error checking transfers for {token_symbol} on {chain}: {e}")
    
    async def _process_transfer_log(
        self,
        log: Dict[str, Any],
        chain: str,
        token_symbol: str,
        receive_addresses: set,
    ) -> None:
        """Process a single transfer log entry."""
        topics = log.get("topics", [])
        if len(topics) < 3:
            return
        
        # Decode from/to addresses from topics
        from_address = "0x" + topics[1][-40:]
        to_address = "0x" + topics[2][-40:]
        
        # Check if this is to one of our addresses
        if to_address.lower() not in receive_addresses:
            return
        
        # Decode amount from data
        data = log.get("data", "0x")
        amount = int(data, 16)
        
        if amount < self._config.min_deposit_minor:
            return
        
        tx_hash = log.get("transactionHash", "")
        block_number = int(log.get("blockNumber", "0x0"), 16)
        
        # Generate deposit ID
        deposit_id = f"{chain}:{tx_hash}:{log.get('logIndex', '0')}"
        
        if deposit_id in self._deposits:
            return  # Already processed
        
        # Get agent ID for this address
        agent_id = self._address_to_agent.get(to_address.lower())
        
        deposit = Deposit(
            deposit_id=deposit_id,
            tx_hash=tx_hash,
            chain=chain,
            token=token_symbol,
            from_address=from_address,
            to_address=to_address,
            amount_minor=amount,
            block_number=block_number,
            status=DepositStatus.DETECTED,
            agent_id=agent_id,
        )
        
        self._deposits[deposit_id] = deposit
        logger.info(f"Detected deposit: {deposit_id}, {amount} {token_symbol}")
        
        # Trigger callbacks
        await self._trigger_callbacks(deposit)
    
    async def _update_confirmations(self) -> None:
        """Update confirmation counts for pending deposits."""
        for deposit in self._deposits.values():
            if deposit.status not in (DepositStatus.DETECTED, DepositStatus.CONFIRMING):
                continue
            
            try:
                rpc = await self._get_rpc_client(deposit.chain)
                current_block = await rpc.get_block_number()
                
                deposit.confirmations = current_block - deposit.block_number + 1
                
                if deposit.status == DepositStatus.DETECTED:
                    deposit.status = DepositStatus.CONFIRMING
                
                if deposit.confirmations >= self._config.confirmations_required:
                    deposit.status = DepositStatus.CONFIRMED
                    deposit.confirmed_at = datetime.now(timezone.utc)
                    logger.info(f"Deposit confirmed: {deposit.deposit_id}")
                    await self._trigger_callbacks(deposit)
                    
            except Exception as e:
                logger.warning(f"Error updating confirmations for {deposit.deposit_id}: {e}")
    
    async def _trigger_callbacks(self, deposit: Deposit) -> None:
        """Trigger all registered callbacks for a deposit."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(deposit)
                else:
                    callback(deposit)
            except Exception as e:
                logger.error(f"Error in deposit callback: {e}")
    
    def mark_credited(self, deposit_id: str) -> bool:
        """Mark a deposit as credited."""
        deposit = self._deposits.get(deposit_id)
        if not deposit:
            return False
        
        deposit.status = DepositStatus.CREDITED
        deposit.credited_at = datetime.now(timezone.utc)
        return True
    
    def get_pending_deposits(self, agent_id: Optional[str] = None) -> List[Deposit]:
        """Get all pending deposits, optionally filtered by agent."""
        result = []
        for deposit in self._deposits.values():
            if deposit.status in (DepositStatus.DETECTED, DepositStatus.CONFIRMING, DepositStatus.CONFIRMED):
                if agent_id is None or deposit.agent_id == agent_id:
                    result.append(deposit)
        return result
    
    def get_deposit(self, deposit_id: str) -> Optional[Deposit]:
        """Get a specific deposit by ID."""
        return self._deposits.get(deposit_id)
    
    async def reconcile(self, chain: str, from_block: int, to_block: int) -> List[Deposit]:
        """Manually reconcile deposits in a block range."""
        # Store original last block
        original_last_block = self._last_blocks.get(chain, 0)
        
        # Set to reconcile range
        self._last_blocks[chain] = from_block - 1
        
        # Run check
        await self._check_chain(chain)
        
        # Get new deposits
        new_deposits = [
            d for d in self._deposits.values()
            if d.chain == chain and from_block <= d.block_number <= to_block
        ]
        
        # Restore last block
        self._last_blocks[chain] = max(original_last_block, to_block)
        
        return new_deposits
    
    async def close(self) -> None:
        """Close all connections."""
        await self.stop()
        for client in self._rpc_clients.values():
            await client.close()


# Singleton instance
_deposit_monitor: Optional[DepositMonitor] = None


def get_deposit_monitor(
    config: Optional[MonitorConfig] = None,
) -> DepositMonitor:
    """Get the global deposit monitor instance."""
    global _deposit_monitor
    
    if _deposit_monitor is None:
        _deposit_monitor = DepositMonitor(config)
    
    return _deposit_monitor



