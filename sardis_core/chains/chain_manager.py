"""
Chain Manager for settlement mode orchestration.

Provides three settlement modes:
1. internal_ledger_only - No blockchain, internal state only (MVP)
2. chain_write_per_tx - Real-time on-chain settlement
3. batched_chain_settlement - Batch settlements every N minutes
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, Callable
import threading
import uuid

from .base import ChainType, TokenType


class SettlementMode(str, Enum):
    """Settlement modes for the chain manager."""
    INTERNAL_LEDGER_ONLY = "internal_ledger_only"      # No blockchain
    CHAIN_WRITE_PER_TX = "chain_write_per_tx"          # Real-time settlement
    BATCHED_CHAIN_SETTLEMENT = "batched_chain_settlement"  # Periodic batches


@dataclass
class PendingSettlement:
    """A transaction pending on-chain settlement."""
    
    settlement_id: str = field(default_factory=lambda: f"stl_{uuid.uuid4().hex[:16]}")
    
    # Transaction details
    ledger_tx_id: str = ""
    from_wallet: str = ""
    to_wallet: str = ""
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    token: TokenType = TokenType.USDC
    chain: ChainType = ChainType.BASE
    
    # Status
    status: str = "pending"  # pending, submitted, confirmed, failed
    
    # On-chain details
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    gas_price: Optional[Decimal] = None
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    
    # Retries
    attempts: int = 0
    last_error: Optional[str] = None


@dataclass
class SettlementBatch:
    """A batch of transactions for batched settlement."""
    
    batch_id: str = field(default_factory=lambda: f"batch_{uuid.uuid4().hex[:12]}")
    
    # Batch configuration
    chain: ChainType = ChainType.BASE
    
    # Settlements in this batch
    settlements: list[PendingSettlement] = field(default_factory=list)
    
    # Batch status
    status: str = "open"  # open, closed, submitting, confirmed, failed
    
    # Aggregated values
    total_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    settlement_count: int = 0
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    
    # On-chain details
    tx_hash: Optional[str] = None
    
    def add_settlement(self, settlement: PendingSettlement):
        """Add a settlement to this batch."""
        self.settlements.append(settlement)
        self.total_amount += settlement.amount
        self.settlement_count += 1
    
    def close(self):
        """Close the batch for submission."""
        self.status = "closed"
        self.closed_at = datetime.now(timezone.utc)


@dataclass
class ChainManagerConfig:
    """Configuration for the chain manager."""
    
    # Settlement mode
    settlement_mode: SettlementMode = SettlementMode.INTERNAL_LEDGER_ONLY
    
    # Default chain for settlements
    default_chain: ChainType = ChainType.BASE
    
    # Batched settlement config
    batch_interval_seconds: int = 300  # 5 minutes
    min_batch_size: int = 5
    max_batch_size: int = 100
    
    # Retry config
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 60
    
    # Gas config
    gas_price_multiplier: float = 1.2  # 20% buffer
    max_gas_price_gwei: float = 100.0


class ChainManager:
    """
    Manages blockchain settlement with configurable modes.
    
    Provides a unified interface for:
    - Recording transactions in internal ledger
    - Submitting to blockchain (per-tx or batched)
    - Tracking settlement status
    - Handling retries and failures
    """
    
    def __init__(
        self,
        config: Optional[ChainManagerConfig] = None,
        ledger_service = None,
        gas_service = None
    ):
        """
        Initialize the chain manager.
        
        Args:
            config: Configuration options
            ledger_service: The internal ledger service
            gas_service: The gas abstraction service
        """
        self.config = config or ChainManagerConfig()
        self._ledger = ledger_service
        self._gas_service = gas_service
        self._lock = threading.RLock()
        
        # Pending settlements
        self._pending: dict[str, PendingSettlement] = {}
        
        # Open batches per chain
        self._batches: dict[ChainType, SettlementBatch] = {}
        
        # Completed settlement history
        self._completed: dict[str, PendingSettlement] = {}
        
        # Batch timer (for batched mode)
        self._batch_timer: Optional[threading.Timer] = None
    
    @property
    def mode(self) -> SettlementMode:
        """Get current settlement mode."""
        return self.config.settlement_mode
    
    def set_mode(self, mode: SettlementMode):
        """Change settlement mode."""
        with self._lock:
            self.config.settlement_mode = mode
            
            # Stop batch timer if moving away from batched mode
            if mode != SettlementMode.BATCHED_CHAIN_SETTLEMENT:
                self._stop_batch_timer()
            elif mode == SettlementMode.BATCHED_CHAIN_SETTLEMENT:
                self._start_batch_timer()
    
    # ==================== Settlement Recording ====================
    
    def record_transfer(
        self,
        ledger_tx_id: str,
        from_wallet: str,
        to_wallet: str,
        amount: Decimal,
        token: TokenType = TokenType.USDC,
        chain: Optional[ChainType] = None
    ) -> PendingSettlement:
        """
        Record a transfer for settlement.
        
        Depending on settlement mode:
        - INTERNAL_LEDGER_ONLY: Just creates the record
        - CHAIN_WRITE_PER_TX: Immediately submits to chain
        - BATCHED_CHAIN_SETTLEMENT: Adds to current batch
        
        Args:
            ledger_tx_id: Internal ledger transaction ID
            from_wallet: Source wallet
            to_wallet: Destination wallet
            amount: Transfer amount
            token: Token type
            chain: Target chain (uses default if not specified)
            
        Returns:
            PendingSettlement record
        """
        target_chain = chain or self.config.default_chain
        
        settlement = PendingSettlement(
            ledger_tx_id=ledger_tx_id,
            from_wallet=from_wallet,
            to_wallet=to_wallet,
            amount=amount,
            token=token,
            chain=target_chain,
        )
        
        with self._lock:
            mode = self.config.settlement_mode
            
            if mode == SettlementMode.INTERNAL_LEDGER_ONLY:
                # Just record, no on-chain action
                settlement.status = "confirmed"
                settlement.confirmed_at = datetime.now(timezone.utc)
                self._completed[settlement.settlement_id] = settlement
                
            elif mode == SettlementMode.CHAIN_WRITE_PER_TX:
                # Submit immediately
                self._pending[settlement.settlement_id] = settlement
                self._submit_settlement(settlement)
                
            elif mode == SettlementMode.BATCHED_CHAIN_SETTLEMENT:
                # Add to batch
                self._pending[settlement.settlement_id] = settlement
                self._add_to_batch(settlement)
        
        return settlement
    
    def _add_to_batch(self, settlement: PendingSettlement):
        """Add settlement to the appropriate batch."""
        chain = settlement.chain
        
        # Get or create batch for this chain
        if chain not in self._batches or self._batches[chain].status != "open":
            self._batches[chain] = SettlementBatch(chain=chain)
        
        batch = self._batches[chain]
        batch.add_settlement(settlement)
        
        # Close batch if it hits max size
        if batch.settlement_count >= self.config.max_batch_size:
            self._close_and_submit_batch(chain)
    
    # ==================== Batch Management ====================
    
    def _start_batch_timer(self):
        """Start the batch submission timer."""
        if self._batch_timer:
            return
        
        self._batch_timer = threading.Timer(
            self.config.batch_interval_seconds,
            self._on_batch_timer
        )
        self._batch_timer.daemon = True
        self._batch_timer.start()
    
    def _stop_batch_timer(self):
        """Stop the batch submission timer."""
        if self._batch_timer:
            self._batch_timer.cancel()
            self._batch_timer = None
    
    def _on_batch_timer(self):
        """Called when batch timer fires."""
        with self._lock:
            for chain in list(self._batches.keys()):
                batch = self._batches.get(chain)
                if batch and batch.status == "open" and batch.settlement_count >= self.config.min_batch_size:
                    self._close_and_submit_batch(chain)
        
        # Restart timer
        self._start_batch_timer()
    
    def _close_and_submit_batch(self, chain: ChainType):
        """Close current batch and submit."""
        batch = self._batches.get(chain)
        if not batch or batch.status != "open":
            return
        
        batch.close()
        self._submit_batch(batch)
    
    def force_submit_batch(self, chain: Optional[ChainType] = None):
        """Force immediate submission of pending batches."""
        with self._lock:
            chains_to_submit = [chain] if chain else list(self._batches.keys())
            
            for c in chains_to_submit:
                batch = self._batches.get(c)
                if batch and batch.status == "open" and batch.settlement_count > 0:
                    self._close_and_submit_batch(c)
    
    # ==================== Chain Submission ====================
    
    def _submit_settlement(self, settlement: PendingSettlement):
        """Submit a single settlement to the chain."""
        settlement.attempts += 1
        settlement.status = "submitting"
        
        try:
            # In production, this would call the actual chain adapter
            # For now, simulate successful submission
            tx_hash = self._simulate_chain_submission(settlement)
            
            settlement.status = "confirmed"
            settlement.tx_hash = tx_hash
            settlement.confirmed_at = datetime.now(timezone.utc)
            
            # Move to completed
            self._completed[settlement.settlement_id] = settlement
            if settlement.settlement_id in self._pending:
                del self._pending[settlement.settlement_id]
                
        except Exception as e:
            settlement.status = "failed"
            settlement.last_error = str(e)
            
            # Schedule retry if attempts remain
            if settlement.attempts < self.config.max_retry_attempts:
                settlement.status = "pending"
                # In production, would schedule a delayed retry
    
    def _submit_batch(self, batch: SettlementBatch):
        """Submit a batch of settlements."""
        batch.status = "submitting"
        batch.submitted_at = datetime.now(timezone.utc)
        
        try:
            # In production, this would aggregate and submit
            tx_hash = self._simulate_batch_submission(batch)
            
            batch.status = "confirmed"
            batch.tx_hash = tx_hash
            batch.confirmed_at = datetime.now(timezone.utc)
            
            # Mark all settlements as confirmed
            for settlement in batch.settlements:
                settlement.status = "confirmed"
                settlement.tx_hash = tx_hash
                settlement.confirmed_at = batch.confirmed_at
                
                self._completed[settlement.settlement_id] = settlement
                if settlement.settlement_id in self._pending:
                    del self._pending[settlement.settlement_id]
                    
        except Exception as e:
            batch.status = "failed"
            for settlement in batch.settlements:
                settlement.status = "failed"
                settlement.last_error = str(e)
    
    def _simulate_chain_submission(self, settlement: PendingSettlement) -> str:
        """Simulate chain submission (demo mode)."""
        # In production, this would use web3/solana SDK
        if settlement.chain == ChainType.SOLANA:
            return f"Demo{uuid.uuid4().hex[:20]}"
        else:
            return f"0x{uuid.uuid4().hex}"
    
    def _simulate_batch_submission(self, batch: SettlementBatch) -> str:
        """Simulate batch submission (demo mode)."""
        if batch.chain == ChainType.SOLANA:
            return f"Demo{uuid.uuid4().hex[:20]}"
        else:
            return f"0x{uuid.uuid4().hex}"
    
    # ==================== Status & Queries ====================
    
    def get_settlement(self, settlement_id: str) -> Optional[PendingSettlement]:
        """Get a settlement by ID."""
        return self._pending.get(settlement_id) or self._completed.get(settlement_id)
    
    def get_pending_settlements(
        self,
        chain: Optional[ChainType] = None
    ) -> list[PendingSettlement]:
        """Get all pending settlements."""
        pending = list(self._pending.values())
        if chain:
            pending = [s for s in pending if s.chain == chain]
        return pending
    
    def get_settlement_by_ledger_tx(self, ledger_tx_id: str) -> Optional[PendingSettlement]:
        """Get settlement by ledger transaction ID."""
        for s in self._pending.values():
            if s.ledger_tx_id == ledger_tx_id:
                return s
        for s in self._completed.values():
            if s.ledger_tx_id == ledger_tx_id:
                return s
        return None
    
    def get_current_batch(self, chain: ChainType) -> Optional[SettlementBatch]:
        """Get the current open batch for a chain."""
        batch = self._batches.get(chain)
        if batch and batch.status == "open":
            return batch
        return None
    
    def get_settlement_stats(self) -> dict:
        """Get settlement statistics."""
        pending_count = len(self._pending)
        completed_count = len(self._completed)
        
        pending_by_chain = {}
        for s in self._pending.values():
            chain = s.chain.value
            pending_by_chain[chain] = pending_by_chain.get(chain, 0) + 1
        
        batch_stats = {}
        for chain, batch in self._batches.items():
            if batch.status == "open":
                batch_stats[chain.value] = {
                    "settlement_count": batch.settlement_count,
                    "total_amount": str(batch.total_amount),
                    "created_at": batch.created_at.isoformat(),
                }
        
        return {
            "mode": self.config.settlement_mode.value,
            "pending_count": pending_count,
            "completed_count": completed_count,
            "pending_by_chain": pending_by_chain,
            "open_batches": batch_stats,
        }


# Global chain manager instance
_chain_manager: Optional[ChainManager] = None


def get_chain_manager() -> ChainManager:
    """Get the global chain manager instance."""
    global _chain_manager
    if _chain_manager is None:
        _chain_manager = ChainManager()
    return _chain_manager

