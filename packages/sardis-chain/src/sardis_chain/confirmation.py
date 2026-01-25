"""
Block confirmation tracking and chain reorg detection.

Features:
- Transaction confirmation tracking with configurable confirmations
- Chain reorganization detection
- Block history tracking
- Automatic reorg recovery
- Event-based notification system
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .config import ReorgDetectionConfig, get_config, get_chain_config

logger = logging.getLogger(__name__)


class ConfirmationStatus(str, Enum):
    """Status of transaction confirmation."""
    PENDING = "pending"  # Not yet in a block
    CONFIRMING = "confirming"  # In a block, awaiting confirmations
    CONFIRMED = "confirmed"  # Required confirmations reached
    FINALIZED = "finalized"  # Deeply confirmed (very unlikely to reorg)
    REORGED = "reorged"  # Transaction removed from chain by reorg
    DROPPED = "dropped"  # Transaction no longer in mempool


class ReorgSeverity(str, Enum):
    """Severity level of chain reorganization."""
    SHALLOW = "shallow"  # 1-6 blocks - common, usually benign
    MODERATE = "moderate"  # 6-12 blocks - concerning
    DEEP = "deep"  # 12-64 blocks - critical
    CRITICAL = "critical"  # 64+ blocks - catastrophic


@dataclass
class BlockInfo:
    """Information about a block."""
    number: int
    hash: str
    parent_hash: str
    timestamp: int
    transaction_count: int
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_child_of(self, parent: "BlockInfo") -> bool:
        """Check if this block is a child of another."""
        return self.parent_hash == parent.hash


@dataclass
class ReorgEvent:
    """A detected chain reorganization event."""
    chain: str
    detected_at: datetime
    severity: ReorgSeverity
    depth: int  # Number of blocks reorged
    old_head_number: int
    old_head_hash: str
    new_head_number: int
    new_head_hash: str
    common_ancestor_number: int
    affected_transactions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chain": self.chain,
            "detected_at": self.detected_at.isoformat(),
            "severity": self.severity.value,
            "depth": self.depth,
            "old_head": {"number": self.old_head_number, "hash": self.old_head_hash},
            "new_head": {"number": self.new_head_number, "hash": self.new_head_hash},
            "common_ancestor_number": self.common_ancestor_number,
            "affected_transactions": self.affected_transactions,
        }


@dataclass
class TrackedTransaction:
    """A transaction being tracked for confirmation."""
    tx_hash: str
    chain: str
    submitted_at: datetime
    block_number: Optional[int] = None
    block_hash: Optional[str] = None
    confirmations: int = 0
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    required_confirmations: int = 1
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Reorg tracking
    original_block_number: Optional[int] = None
    original_block_hash: Optional[str] = None
    reorg_count: int = 0

    def update_confirmations(self, current_block: int) -> None:
        """Update confirmation count based on current block."""
        if self.block_number is None:
            self.confirmations = 0
            return

        self.confirmations = max(0, current_block - self.block_number + 1)
        self.last_updated = datetime.now(timezone.utc)

        # Update status
        if self.confirmations >= self.required_confirmations:
            self.status = ConfirmationStatus.CONFIRMED
            # Finalized after ~15 minutes of confirmations (varies by chain)
            if self.confirmations >= 64:
                self.status = ConfirmationStatus.FINALIZED
        elif self.block_number is not None:
            self.status = ConfirmationStatus.CONFIRMING


class ReorgError(Exception):
    """Error raised when a critical reorg is detected."""

    def __init__(self, event: ReorgEvent):
        self.event = event
        super().__init__(
            f"Critical chain reorg detected on {event.chain}: "
            f"depth={event.depth}, affected_txs={len(event.affected_transactions)}"
        )


# Type alias for reorg callbacks
ReorgCallback = Callable[[ReorgEvent], None]
ConfirmationCallback = Callable[[TrackedTransaction], None]


class ConfirmationTracker:
    """
    Transaction confirmation tracker with reorg detection.

    SECURITY: This component ensures:
    - Transactions are properly confirmed before being considered final
    - Chain reorganizations are detected and handled
    - Affected transactions are re-validated after reorgs

    Features:
    - Multi-transaction tracking
    - Configurable confirmation requirements
    - Automatic reorg detection via block hash comparison
    - Event callbacks for confirmations and reorgs
    """

    def __init__(
        self,
        chain: str,
        config: Optional[ReorgDetectionConfig] = None,
    ):
        self._chain = chain
        self._config = config or get_config().reorg_detection
        self._chain_config = get_chain_config(chain)

        # Block history for reorg detection
        self._block_history: Dict[int, BlockInfo] = {}
        self._current_head: Optional[BlockInfo] = None
        self._max_history = self._config.max_block_history

        # Transaction tracking
        self._tracked_txs: Dict[str, TrackedTransaction] = {}
        self._tx_by_block: Dict[int, Set[str]] = {}  # block_number -> tx_hashes

        # Callbacks
        self._reorg_callbacks: List[ReorgCallback] = []
        self._confirmation_callbacks: List[ConfirmationCallback] = []

        # Monitoring state
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None

        # Statistics
        self._reorg_count = 0
        self._deepest_reorg = 0

    def add_reorg_callback(self, callback: ReorgCallback) -> None:
        """Register a callback for reorg events."""
        self._reorg_callbacks.append(callback)

    def add_confirmation_callback(self, callback: ConfirmationCallback) -> None:
        """Register a callback for confirmation events."""
        self._confirmation_callbacks.append(callback)

    async def track_transaction(
        self,
        tx_hash: str,
        required_confirmations: Optional[int] = None,
    ) -> TrackedTransaction:
        """
        Start tracking a transaction for confirmation.

        Args:
            tx_hash: Transaction hash to track
            required_confirmations: Number of confirmations required

        Returns:
            TrackedTransaction object
        """
        if required_confirmations is None:
            required_confirmations = self._chain_config.confirmations_required

        tracked = TrackedTransaction(
            tx_hash=tx_hash,
            chain=self._chain,
            submitted_at=datetime.now(timezone.utc),
            required_confirmations=required_confirmations,
        )

        self._tracked_txs[tx_hash] = tracked

        logger.info(
            f"Started tracking transaction {tx_hash} on {self._chain}, "
            f"required confirmations: {required_confirmations}"
        )

        return tracked

    async def update_transaction(
        self,
        tx_hash: str,
        rpc_client: Any,  # ProductionRPCClient
    ) -> TrackedTransaction:
        """
        Update tracking state for a transaction.

        Args:
            tx_hash: Transaction hash
            rpc_client: RPC client

        Returns:
            Updated TrackedTransaction
        """
        tracked = self._tracked_txs.get(tx_hash)
        if not tracked:
            raise ValueError(f"Transaction {tx_hash} is not being tracked")

        # Get current receipt
        receipt = await rpc_client.get_transaction_receipt(tx_hash)

        if receipt is None:
            tracked.status = ConfirmationStatus.PENDING
            return tracked

        # Parse block info
        block_number = (
            int(receipt["blockNumber"], 16)
            if isinstance(receipt.get("blockNumber"), str)
            else receipt.get("blockNumber")
        )
        block_hash = receipt.get("blockHash")

        # Check for reorg
        if tracked.block_hash and tracked.block_hash != block_hash:
            logger.warning(
                f"Transaction {tx_hash} block hash changed: "
                f"{tracked.block_hash} -> {block_hash}"
            )
            tracked.reorg_count += 1

        # Update block info
        if tracked.original_block_number is None:
            tracked.original_block_number = block_number
            tracked.original_block_hash = block_hash

        tracked.block_number = block_number
        tracked.block_hash = block_hash

        # Track by block
        if block_number not in self._tx_by_block:
            self._tx_by_block[block_number] = set()
        self._tx_by_block[block_number].add(tx_hash)

        # Update confirmations
        current_block = await rpc_client.get_block_number()
        tracked.update_confirmations(current_block)

        # Trigger callback if newly confirmed
        if tracked.status == ConfirmationStatus.CONFIRMED:
            await self._notify_confirmed(tracked)

        return tracked

    async def wait_for_confirmation(
        self,
        tx_hash: str,
        rpc_client: Any,
        timeout_seconds: Optional[float] = None,
        poll_interval: Optional[float] = None,
    ) -> TrackedTransaction:
        """
        Wait for a transaction to be confirmed.

        Args:
            tx_hash: Transaction hash
            rpc_client: RPC client
            timeout_seconds: Maximum wait time
            poll_interval: Polling interval

        Returns:
            Confirmed TrackedTransaction

        Raises:
            TimeoutError: If not confirmed within timeout
            ReorgError: If critical reorg affects transaction
        """
        if timeout_seconds is None:
            timeout_seconds = self._chain_config.confirmation_timeout_seconds
        if poll_interval is None:
            poll_interval = self._config.block_poll_interval_seconds

        # Start tracking if not already
        if tx_hash not in self._tracked_txs:
            await self.track_transaction(tx_hash)

        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_seconds:
                tracked = self._tracked_txs.get(tx_hash)
                raise TimeoutError(
                    f"Transaction {tx_hash} not confirmed after {timeout_seconds}s. "
                    f"Current status: {tracked.status.value if tracked else 'unknown'}"
                )

            tracked = await self.update_transaction(tx_hash, rpc_client)

            # Also update block history for reorg detection
            await self._update_block_history(rpc_client)

            if tracked.status in (
                ConfirmationStatus.CONFIRMED,
                ConfirmationStatus.FINALIZED,
            ):
                logger.info(
                    f"Transaction {tx_hash} confirmed with {tracked.confirmations} confirmations"
                )
                return tracked

            if tracked.status == ConfirmationStatus.REORGED:
                logger.warning(f"Transaction {tx_hash} was reorged out of the chain")
                # Transaction might reappear - keep waiting

            if tracked.status == ConfirmationStatus.DROPPED:
                raise Exception(f"Transaction {tx_hash} was dropped from mempool")

            await asyncio.sleep(poll_interval)

    async def _update_block_history(self, rpc_client: Any) -> None:
        """Update block history and check for reorgs."""
        if not self._config.enabled:
            return

        try:
            # Get latest block
            current_block_num = await rpc_client.get_block_number()
            block_data = await rpc_client.get_block(current_block_num, False)

            if not block_data:
                return

            new_block = BlockInfo(
                number=current_block_num,
                hash=block_data.get("hash", ""),
                parent_hash=block_data.get("parentHash", ""),
                timestamp=int(block_data.get("timestamp", "0x0"), 16),
                transaction_count=len(block_data.get("transactions", [])),
            )

            # Check for reorg
            if self._current_head:
                await self._check_for_reorg(new_block, rpc_client)

            # Update history
            self._block_history[new_block.number] = new_block
            self._current_head = new_block

            # Prune old history
            self._prune_history()

        except Exception as e:
            logger.warning(f"Error updating block history: {e}")

    async def _check_for_reorg(
        self,
        new_block: BlockInfo,
        rpc_client: Any,
    ) -> Optional[ReorgEvent]:
        """Check for chain reorganization."""
        if not self._current_head:
            return None

        # Simple case: new block is child of current head
        if new_block.number == self._current_head.number + 1:
            expected_parent = self._current_head.hash
            if new_block.parent_hash == expected_parent:
                return None  # No reorg

        # Check if we already have this block with different hash
        if new_block.number in self._block_history:
            old_block = self._block_history[new_block.number]
            if old_block.hash != new_block.hash:
                # Reorg detected!
                return await self._handle_reorg(
                    old_block, new_block, rpc_client
                )

        return None

    async def _handle_reorg(
        self,
        old_block: BlockInfo,
        new_block: BlockInfo,
        rpc_client: Any,
    ) -> ReorgEvent:
        """Handle detected chain reorganization."""
        # Find common ancestor
        common_ancestor = await self._find_common_ancestor(
            old_block.number, rpc_client
        )

        reorg_depth = old_block.number - common_ancestor

        # Determine severity
        if reorg_depth >= self._config.critical_reorg_depth:
            severity = ReorgSeverity.CRITICAL
        elif reorg_depth >= self._config.deep_reorg_depth:
            severity = ReorgSeverity.DEEP
        elif reorg_depth >= self._config.shallow_reorg_depth:
            severity = ReorgSeverity.MODERATE
        else:
            severity = ReorgSeverity.SHALLOW

        # Find affected transactions
        affected_txs = []
        for block_num in range(common_ancestor + 1, old_block.number + 1):
            if block_num in self._tx_by_block:
                affected_txs.extend(self._tx_by_block[block_num])

        # Create reorg event
        event = ReorgEvent(
            chain=self._chain,
            detected_at=datetime.now(timezone.utc),
            severity=severity,
            depth=reorg_depth,
            old_head_number=old_block.number,
            old_head_hash=old_block.hash,
            new_head_number=new_block.number,
            new_head_hash=new_block.hash,
            common_ancestor_number=common_ancestor,
            affected_transactions=affected_txs,
        )

        # Update statistics
        self._reorg_count += 1
        self._deepest_reorg = max(self._deepest_reorg, reorg_depth)

        # Log the reorg
        logger.warning(
            f"REORG DETECTED on {self._chain}: depth={reorg_depth}, "
            f"severity={severity.value}, affected_txs={len(affected_txs)}"
        )

        # Mark affected transactions
        for tx_hash in affected_txs:
            if tx_hash in self._tracked_txs:
                self._tracked_txs[tx_hash].status = ConfirmationStatus.REORGED

        # Clear invalidated block history
        for block_num in range(common_ancestor + 1, old_block.number + 1):
            if block_num in self._block_history:
                del self._block_history[block_num]

        # Notify callbacks
        await self._notify_reorg(event)

        # Raise for critical reorgs
        if severity == ReorgSeverity.CRITICAL:
            raise ReorgError(event)

        return event

    async def _find_common_ancestor(
        self,
        from_block: int,
        rpc_client: Any,
    ) -> int:
        """Find the common ancestor block after a reorg."""
        # Walk back through history to find matching block
        for block_num in range(from_block, max(0, from_block - self._max_history), -1):
            if block_num in self._block_history:
                # Verify this block still exists on chain
                chain_block = await rpc_client.get_block(block_num, False)
                if chain_block:
                    stored = self._block_history[block_num]
                    if chain_block.get("hash") == stored.hash:
                        return block_num

        # Fallback: assume reorg is limited
        return max(0, from_block - self._max_history)

    def _prune_history(self) -> None:
        """Remove old blocks from history."""
        if not self._current_head:
            return

        cutoff = self._current_head.number - self._max_history
        to_remove = [num for num in self._block_history if num < cutoff]

        for num in to_remove:
            del self._block_history[num]
            if num in self._tx_by_block:
                del self._tx_by_block[num]

    async def _notify_reorg(self, event: ReorgEvent) -> None:
        """Notify reorg callbacks."""
        if not self._config.notify_on_reorg:
            return

        for callback in self._reorg_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in reorg callback: {e}")

    async def _notify_confirmed(self, tracked: TrackedTransaction) -> None:
        """Notify confirmation callbacks."""
        for callback in self._confirmation_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(tracked)
                else:
                    callback(tracked)
            except Exception as e:
                logger.error(f"Error in confirmation callback: {e}")

    async def start_monitoring(self, rpc_client: Any) -> None:
        """Start background monitoring for reorgs."""
        if self._running:
            return

        self._running = True
        self._poll_task = asyncio.create_task(
            self._monitoring_loop(rpc_client)
        )
        logger.info(f"Started block monitoring for {self._chain}")

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped block monitoring for {self._chain}")

    async def _monitoring_loop(self, rpc_client: Any) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await self._update_block_history(rpc_client)

                # Update all tracked transactions
                for tx_hash in list(self._tracked_txs.keys()):
                    try:
                        await self.update_transaction(tx_hash, rpc_client)
                    except Exception as e:
                        logger.debug(f"Error updating transaction {tx_hash}: {e}")

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

            await asyncio.sleep(self._config.block_poll_interval_seconds)

    def get_transaction(self, tx_hash: str) -> Optional[TrackedTransaction]:
        """Get a tracked transaction."""
        return self._tracked_txs.get(tx_hash)

    def get_all_tracked(self) -> List[TrackedTransaction]:
        """Get all tracked transactions."""
        return list(self._tracked_txs.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        return {
            "chain": self._chain,
            "tracked_transactions": len(self._tracked_txs),
            "blocks_in_history": len(self._block_history),
            "current_head": self._current_head.number if self._current_head else None,
            "reorg_count": self._reorg_count,
            "deepest_reorg": self._deepest_reorg,
            "running": self._running,
        }

    def untrack_transaction(self, tx_hash: str) -> bool:
        """Stop tracking a transaction."""
        if tx_hash in self._tracked_txs:
            tracked = self._tracked_txs[tx_hash]
            if tracked.block_number and tracked.block_number in self._tx_by_block:
                self._tx_by_block[tracked.block_number].discard(tx_hash)
            del self._tracked_txs[tx_hash]
            return True
        return False

    def clear_all(self) -> None:
        """Clear all tracked transactions."""
        self._tracked_txs.clear()
        self._tx_by_block.clear()
        self._block_history.clear()
        self._current_head = None


# Global trackers per chain
_trackers: Dict[str, ConfirmationTracker] = {}


def get_confirmation_tracker(
    chain: str,
    config: Optional[ReorgDetectionConfig] = None,
) -> ConfirmationTracker:
    """Get or create a confirmation tracker for a chain."""
    if chain not in _trackers:
        _trackers[chain] = ConfirmationTracker(chain, config)
    return _trackers[chain]


async def close_all_trackers() -> None:
    """Stop and close all trackers."""
    for tracker in _trackers.values():
        await tracker.stop_monitoring()
    _trackers.clear()
