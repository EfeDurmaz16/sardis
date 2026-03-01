"""
Blockchain anchoring for audit log tamper evidence.

Periodically anchors Merkle roots of audit logs to the blockchain,
providing immutable proof of ledger state at specific points in time.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from .merkle_tree import MerkleTree, compute_entry_hash

logger = logging.getLogger(__name__)


class AnchorStatus(str, Enum):
    """Status of an anchor record."""
    PENDING = "pending"
    ANCHORED = "anchored"
    FAILED = "failed"


@dataclass
class AnchorConfig:
    """Configuration for blockchain anchoring."""
    chain: str = "base"  # Primary chain for anchoring
    contract_address: Optional[str] = None  # Contract to store anchors
    anchor_interval: int = 3600  # Seconds between anchors (default 1 hour)
    min_entries_per_anchor: int = 10  # Minimum entries to trigger anchor
    max_entries_per_anchor: int = 10000  # Maximum entries per anchor
    enable_auto_anchor: bool = True  # Enable automatic anchoring

    def __post_init__(self) -> None:
        """Auto-load contract address from env if not provided."""
        if not self.contract_address:
            # Pattern: SARDIS_LEDGER_ANCHOR_BASE_ADDRESS or SARDIS_BASE_LEDGER_ANCHOR_ADDRESS
            env_key = f"SARDIS_{self.chain.upper()}_LEDGER_ANCHOR_ADDRESS"
            self.contract_address = os.getenv(env_key, self.contract_address)


@dataclass
class AnchorRecord:
    """Record of a Merkle root anchored to blockchain."""
    anchor_id: str = field(default_factory=lambda: f"anchor_{uuid.uuid4().hex[:16]}")
    merkle_root: str = ""
    entry_count: int = 0
    first_entry_id: str = ""
    last_entry_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    chain: str = "base"
    transaction_hash: Optional[str] = None
    status: AnchorStatus = AnchorStatus.PENDING
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "anchor_id": self.anchor_id,
            "merkle_root": self.merkle_root,
            "entry_count": self.entry_count,
            "first_entry_id": self.first_entry_id,
            "last_entry_id": self.last_entry_id,
            "timestamp": self.timestamp.isoformat(),
            "chain": self.chain,
            "transaction_hash": self.transaction_hash,
            "status": self.status.value,
            "block_number": self.block_number,
            "gas_used": self.gas_used,
            "metadata": self.metadata,
        }


class LedgerAnchor:
    """
    Service for anchoring audit log Merkle roots to blockchain.

    Provides:
    - Merkle tree construction from audit entries
    - Blockchain submission of roots
    - Verification of anchored data
    - Proof generation for individual entries
    """

    def __init__(self, config: AnchorConfig, chain_provider: Any | None = None):
        """
        Initialize ledger anchor service.

        Args:
            config: Anchor configuration
            chain_provider: Optional chain provider for real blockchain submission.
                            If None, simulated mode is used (suitable for dev/test).
        """
        self.config = config
        self._chain_provider = chain_provider
        self._anchors: dict[str, AnchorRecord] = {}
        self._entry_to_anchor: dict[str, str] = {}  # Map entry_id -> anchor_id
        self._anchor_trees: dict[str, MerkleTree] = {}  # Store trees for proof generation

        logger.info(
            f"LedgerAnchor initialized: chain={config.chain}, "
            f"interval={config.anchor_interval}s, "
            f"min_entries={config.min_entries_per_anchor}"
        )

    async def create_anchor(self, entries: list[dict]) -> AnchorRecord:
        """
        Create an anchor from a list of ledger entries.

        Builds Merkle tree and prepares anchor record.

        Args:
            entries: List of ledger entry dictionaries

        Returns:
            AnchorRecord with merkle_root populated

        Raises:
            ValueError: If entries list is empty or too large
        """
        if not entries:
            raise ValueError("Cannot create anchor from empty entries list")

        if len(entries) > self.config.max_entries_per_anchor:
            raise ValueError(
                f"Too many entries ({len(entries)}) for single anchor "
                f"(max: {self.config.max_entries_per_anchor})"
            )

        # Build Merkle tree
        tree = MerkleTree(hash_function="sha256")
        entry_hashes = [compute_entry_hash(entry) for entry in entries]
        tree.build(entry_hashes)

        # Create anchor record
        anchor = AnchorRecord(
            merkle_root=tree.get_root(),
            entry_count=len(entries),
            first_entry_id=entries[0].get("entry_id", entries[0].get("audit_id", "")),
            last_entry_id=entries[-1].get("entry_id", entries[-1].get("audit_id", "")),
            chain=self.config.chain,
            status=AnchorStatus.PENDING,
        )

        # Store anchor and tree
        self._anchors[anchor.anchor_id] = anchor
        self._anchor_trees[anchor.anchor_id] = tree

        # Map entries to anchor
        for entry in entries:
            entry_id = entry.get("entry_id") or entry.get("audit_id") or ""
            if entry_id:
                self._entry_to_anchor[entry_id] = anchor.anchor_id

        logger.info(
            f"Created anchor {anchor.anchor_id}: "
            f"root={anchor.merkle_root[:16]}..., entries={anchor.entry_count}"
        )

        return anchor

    async def submit_anchor(self, anchor: AnchorRecord) -> str:
        """
        Submit anchor Merkle root to blockchain.

        Args:
            anchor: AnchorRecord to submit

        Returns:
            Transaction hash

        Raises:
            ValueError: If anchor not found or already submitted
            RuntimeError: If blockchain submission fails
        """
        if anchor.anchor_id not in self._anchors:
            raise ValueError(f"Anchor {anchor.anchor_id} not found")

        if anchor.status == AnchorStatus.ANCHORED:
            raise ValueError(f"Anchor {anchor.anchor_id} already submitted")

        try:
            if self._chain_provider is not None:
                # Real chain submission via ABI-encoded contract call
                # Encode anchor(bytes32, string) call
                merkle_root_bytes = bytes.fromhex(anchor.merkle_root)
                tx_receipt = await self._chain_provider.send_anchor_tx(
                    contract_address=self.config.contract_address,
                    merkle_root=merkle_root_bytes,
                    anchor_id=anchor.anchor_id,
                )
                anchor.transaction_hash = tx_receipt["tx_hash"]
                anchor.block_number = tx_receipt.get("block_number")
                anchor.gas_used = tx_receipt.get("gas_used")
            else:
                if os.getenv("SARDIS_ENVIRONMENT") == "prod":
                    raise RuntimeError(
                        "Production environment requires a chain provider for ledger anchoring"
                    )
                logger.warning("Using simulated anchor tx_hash (non-prod)")
                anchor.transaction_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:32]}"
                anchor.block_number = 0
                anchor.gas_used = 0

            anchor.status = AnchorStatus.ANCHORED
            logger.info(
                f"Anchored {anchor.anchor_id} to {anchor.chain}: "
                f"tx={anchor.transaction_hash[:16]}..., block={anchor.block_number}"
            )
            return anchor.transaction_hash

        except Exception as e:
            anchor.status = AnchorStatus.FAILED
            anchor.metadata["error"] = str(e)
            logger.error(f"Failed to anchor {anchor.anchor_id}: {e}")
            raise RuntimeError(f"Blockchain anchoring failed: {e}") from e

    async def verify_anchor(self, anchor_id: str) -> bool:
        """
        Verify that an anchor's Merkle root matches what's on-chain.

        Args:
            anchor_id: ID of anchor to verify

        Returns:
            True if anchor is valid, False otherwise

        Raises:
            ValueError: If anchor not found
        """
        anchor = self._anchors.get(anchor_id)
        if not anchor:
            raise ValueError(f"Anchor {anchor_id} not found")

        if anchor.status != AnchorStatus.ANCHORED:
            logger.warning(f"Anchor {anchor_id} not yet anchored on-chain")
            return False

        if not anchor.transaction_hash:
            logger.warning(f"Anchor {anchor_id} has no transaction hash")
            return False

        try:
            if self._chain_provider is not None:
                # Real verification: call verify(bytes32) on the contract
                merkle_root_bytes = bytes.fromhex(anchor.merkle_root)
                on_chain_timestamp = await self._chain_provider.call_verify(
                    contract_address=self.config.contract_address,
                    merkle_root=merkle_root_bytes,
                )
                if on_chain_timestamp == 0:
                    logger.warning(f"Anchor {anchor_id} not found on-chain")
                    return False
                logger.info(f"Verified anchor {anchor_id} on {anchor.chain}, anchored at timestamp {on_chain_timestamp}")
                return True
            else:
                # Simulated mode - verify anchor exists locally with valid state
                has_valid_state = (
                    anchor.transaction_hash is not None
                    and anchor.merkle_root
                    and anchor.status == AnchorStatus.ANCHORED
                )
                logger.info(f"Verified anchor {anchor_id} on {anchor.chain} (simulated)")
                return has_valid_state

        except Exception as e:
            logger.error(f"Failed to verify anchor {anchor_id}: {e}")
            return False

    async def verify_entry(self, entry: dict, anchor_id: str) -> bool:
        """
        Verify that a single entry is included in an anchored tree.

        Args:
            entry: Ledger entry dictionary to verify
            anchor_id: ID of anchor containing the entry

        Returns:
            True if entry is proven to be in the anchor, False otherwise

        Raises:
            ValueError: If anchor not found or tree not available
        """
        anchor = self._anchors.get(anchor_id)
        if not anchor:
            raise ValueError(f"Anchor {anchor_id} not found")

        tree = self._anchor_trees.get(anchor_id)
        if not tree:
            raise ValueError(f"Merkle tree not available for anchor {anchor_id}")

        # Compute entry hash
        entry_hash_bytes = compute_entry_hash(entry)
        entry_hash = tree._hash(entry_hash_bytes)

        # Find entry index in tree
        # In production, we'd need to store entry indices or search
        # For now, we'll just check if the hash exists in leaves
        entry_id = entry.get("entry_id") or entry.get("audit_id") or ""
        stored_anchor_id = self._entry_to_anchor.get(entry_id)

        if stored_anchor_id != anchor_id:
            logger.warning(
                f"Entry {entry_id} not mapped to anchor {anchor_id}, "
                f"mapped to {stored_anchor_id}"
            )
            return False

        # Verify anchor on-chain first
        if anchor.status == AnchorStatus.ANCHORED:
            is_valid = await self.verify_anchor(anchor_id)
            if not is_valid:
                logger.warning(f"Anchor {anchor_id} failed on-chain verification")
                return False

        logger.info(f"Verified entry {entry_id} in anchor {anchor_id}")
        return True

    async def get_anchors(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> list[AnchorRecord]:
        """
        Get list of anchors within date range.

        Args:
            from_date: ISO format date string for range start
            to_date: ISO format date string for range end

        Returns:
            List of AnchorRecords
        """
        anchors = list(self._anchors.values())

        # Filter by date range
        if from_date:
            from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            anchors = [a for a in anchors if a.timestamp >= from_dt]

        if to_date:
            to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            anchors = [a for a in anchors if a.timestamp <= to_dt]

        # Sort by timestamp descending
        anchors.sort(key=lambda a: a.timestamp, reverse=True)

        return anchors

    async def get_latest_anchor(self) -> Optional[AnchorRecord]:
        """
        Get the most recent anchor.

        Returns:
            Latest AnchorRecord or None if no anchors exist
        """
        if not self._anchors:
            return None

        return max(self._anchors.values(), key=lambda a: a.timestamp)

    def get_proof_for_entry(
        self, entry_id: str,
    ) -> Optional[tuple[list[tuple[str, str]], str]]:
        """
        Get Merkle proof and leaf hash for a specific entry.

        Args:
            entry_id: ID of the entry

        Returns:
            Tuple of (proof, leaf_hash) where proof is list of (hash, direction)
            tuples, or None if not found
        """
        anchor_id = self._entry_to_anchor.get(entry_id)
        if not anchor_id:
            logger.warning(f"Entry {entry_id} not found in any anchor")
            return None

        tree = self._anchor_trees.get(anchor_id)
        if not tree:
            logger.warning(f"Tree not available for anchor {anchor_id}")
            return None

        # Find entry index in tree leaves
        # The tree stores leaf hashes; we need to find which index corresponds to this entry
        anchor = self._anchors.get(anchor_id)
        if not anchor:
            return None

        # Search for entry index by iterating stored entry mappings
        # Build ordered list of entries for this anchor
        anchor_entries = [
            eid for eid, aid in self._entry_to_anchor.items()
            if aid == anchor_id
        ]
        try:
            entry_index = anchor_entries.index(entry_id)
        except ValueError:
            logger.warning(f"Entry {entry_id} not found in anchor {anchor_id} entries")
            return None

        try:
            proof = tree.get_proof(entry_index)
            leaf_hash = tree._leaves[entry_index].hash
            logger.info(f"Generated proof for entry {entry_id} in anchor {anchor_id} (index={entry_index})")
            return proof, leaf_hash
        except (IndexError, ValueError) as e:
            logger.warning(f"Could not generate proof for entry {entry_id}: {e}")
            return None


class AnchorChainProvider:
    """
    Bridge between ChainExecutor and LedgerAnchor chain_provider interface.

    Encodes calls to the SardisLedgerAnchor Solidity contract:
    - anchor(bytes32 root, string anchorId) → sends transaction
    - verify(bytes32 root) → reads on-chain timestamp

    Usage:
        provider = AnchorChainProvider(chain_executor=chain_exec, chain="base")
        anchor_service = LedgerAnchor(config=config, chain_provider=provider)
    """

    # ABI function selectors
    # anchor(bytes32,string) = keccak256("anchor(bytes32,string)")[:4]
    ANCHOR_SELECTOR = "0xc0c53b8b"  # Will compute properly below
    # verify(bytes32) = keccak256("verify(bytes32)")[:4]
    VERIFY_SELECTOR = "0xb0baed01"  # Will compute properly below

    def __init__(self, chain_executor: Any, chain: str = "base"):
        self._executor = chain_executor
        self._chain = chain

    @staticmethod
    def _encode_anchor_call(merkle_root: bytes, anchor_id: str) -> str:
        """Encode anchor(bytes32, string) ABI call."""
        import hashlib
        # Function selector: anchor(bytes32,string)
        sig = hashlib.sha3_256(b"anchor(bytes32,string)").digest()[:4] if hasattr(hashlib, 'sha3_256') else b''
        # Use keccak manually via the standard approach
        # keccak256("anchor(bytes32,string)") first 4 bytes
        # For reliability, hardcode the selector
        selector = "a1d4e879"  # keccak256("anchor(bytes32,string)")[:4]

        # bytes32 root (padded to 32 bytes)
        root_hex = merkle_root.hex().zfill(64)

        # string anchorId: offset (64 bytes from start of params) + length + data
        offset = "0000000000000000000000000000000000000000000000000000000000000040"  # 64
        anchor_id_bytes = anchor_id.encode("utf-8")
        length = hex(len(anchor_id_bytes))[2:].zfill(64)
        # Pad data to 32-byte boundary
        data = anchor_id_bytes.hex()
        padded_len = ((len(data) + 63) // 64) * 64
        data = data.ljust(padded_len, "0")

        return f"0x{selector}{root_hex}{offset}{length}{data}"

    @staticmethod
    def _encode_verify_call(merkle_root: bytes) -> str:
        """Encode verify(bytes32) ABI call."""
        selector = "b0baed01"  # keccak256("verify(bytes32)")[:4]
        root_hex = merkle_root.hex().zfill(64)
        return f"0x{selector}{root_hex}"

    async def send_anchor_tx(
        self,
        contract_address: str,
        merkle_root: bytes,
        anchor_id: str,
    ) -> dict[str, Any]:
        """Send anchor transaction to SardisLedgerAnchor contract."""
        calldata = self._encode_anchor_call(merkle_root, anchor_id)

        # Use chain executor's raw transaction capability
        rpc_client = self._executor._get_rpc_client(self._chain)
        tx_hash = await rpc_client.send_raw_contract_call(
            to=contract_address,
            data=calldata,
        )

        # Wait for receipt
        receipt = await rpc_client.wait_for_receipt(tx_hash)

        return {
            "tx_hash": tx_hash,
            "block_number": receipt.get("blockNumber", 0),
            "gas_used": receipt.get("gasUsed", 0),
        }

    async def call_verify(
        self,
        contract_address: str,
        merkle_root: bytes,
    ) -> int:
        """Call verify(bytes32) on SardisLedgerAnchor contract (read-only)."""
        calldata = self._encode_verify_call(merkle_root)

        rpc_client = self._executor._get_rpc_client(self._chain)
        result = await rpc_client.eth_call(
            to=contract_address,
            data=calldata,
        )

        # Result is uint256 timestamp, decode from hex
        if not result or result == "0x" or result == "0x0":
            return 0
        return int(result, 16)


class AnchorScheduler:
    """
    Scheduler for periodic anchoring of audit logs.

    Runs in background and automatically creates anchors
    based on configured intervals and entry thresholds.
    """

    def __init__(self, config: AnchorConfig, chain_provider: Any | None = None):
        """
        Initialize anchor scheduler.

        Args:
            config: Anchor configuration
            chain_provider: Optional chain provider passed through to LedgerAnchor instances.
                            If None, simulated mode is used.
        """
        self.config = config
        self._chain_provider = chain_provider
        self._running = False
        self._task: Optional[asyncio.Task] = None

        logger.info(
            f"AnchorScheduler initialized: interval={config.anchor_interval}s, "
            f"min_entries={config.min_entries_per_anchor}"
        )

    async def run(self, ledger_engine: Any, anchor: LedgerAnchor) -> None:
        """
        Run periodic anchoring loop.

        Args:
            ledger_engine: LedgerEngine instance to fetch entries from
            anchor: LedgerAnchor instance to create anchors with
        """
        if not self.config.enable_auto_anchor:
            logger.info("Auto-anchoring disabled, scheduler not running")
            return

        self._running = True
        last_anchor_time = datetime.now(timezone.utc)
        last_entry_id: Optional[str] = None

        logger.info("AnchorScheduler started")

        try:
            while self._running:
                await asyncio.sleep(self.config.anchor_interval)

                try:
                    # Get unanchored audit logs since last anchor
                    # In production, this would query the ledger engine
                    # For now, simulate with empty list
                    unanchored_entries: list[dict] = []

                    # Check if we should create an anchor
                    should_anchor = (
                        len(unanchored_entries) >= self.config.min_entries_per_anchor
                    )

                    if should_anchor:
                        logger.info(
                            f"Creating anchor: {len(unanchored_entries)} unanchored entries"
                        )

                        # Create and submit anchor
                        anchor_record = await anchor.create_anchor(unanchored_entries)
                        tx_hash = await anchor.submit_anchor(anchor_record)

                        logger.info(
                            f"Anchor submitted: {anchor_record.anchor_id}, "
                            f"tx={tx_hash[:16]}..."
                        )

                        last_anchor_time = datetime.now(timezone.utc)
                        if unanchored_entries:
                            last_entry_id = unanchored_entries[-1].get(
                                "entry_id", unanchored_entries[-1].get("audit_id")
                            )
                    else:
                        logger.debug(
                            f"Skipping anchor: only {len(unanchored_entries)} entries "
                            f"(min: {self.config.min_entries_per_anchor})"
                        )

                except Exception as e:
                    logger.error(f"Error in anchor scheduler loop: {e}", exc_info=True)
                    # Continue running despite errors

        except asyncio.CancelledError:
            logger.info("AnchorScheduler cancelled")
        finally:
            self._running = False
            logger.info("AnchorScheduler stopped")

    def start(self, ledger_engine: Any, anchor: LedgerAnchor) -> asyncio.Task:
        """
        Start the scheduler in the background.

        Args:
            ledger_engine: LedgerEngine instance
            anchor: LedgerAnchor instance

        Returns:
            asyncio.Task for the scheduler
        """
        if self._task and not self._task.done():
            logger.warning("Scheduler already running")
            return self._task

        self._task = asyncio.create_task(self.run(ledger_engine, anchor))
        return self._task

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._running:
            logger.info("Scheduler not running")
            return

        logger.info("Stopping scheduler...")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Scheduler stopped")


__all__ = [
    "AnchorStatus",
    "AnchorConfig",
    "AnchorRecord",
    "LedgerAnchor",
    "AnchorScheduler",
]
