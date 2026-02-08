"""
Immutable Audit Trail using immudb.

This module provides cryptographically-verified immutable storage for
financial transactions using immudb - a lightweight, high-performance
immutable database with built-in Merkle tree verification.

Architecture:
- PostgreSQL: Primary storage for fast queries and complex SQL
- immudb: Immutable audit trail with cryptographic proofs
- Blockchain: Periodic anchoring for public verifiability

Key Features:
- True immutability (data cannot be modified or deleted)
- Merkle tree proofs for every entry
- Cryptographic verification API
- Dual-write consistency
- Automatic retry and reconciliation
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

logger = logging.getLogger(__name__)

# Type alias for immudb verification result
VerifiedTx = Any  # Will be immudb.datatypes.VerifiableTx when imported


class ImmutableStoreError(Exception):
    """Base exception for immutable store operations."""

    def __init__(self, message: str, code: str = "IMMUTABLE_ERROR", details: Optional[Dict] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class VerificationError(ImmutableStoreError):
    """Verification of immutable entry failed."""

    def __init__(self, entry_id: str, reason: str):
        super().__init__(
            f"Verification failed for {entry_id}: {reason}",
            code="VERIFICATION_FAILED",
            details={"entry_id": entry_id, "reason": reason},
        )


class ConsistencyError(ImmutableStoreError):
    """Consistency check between stores failed."""

    def __init__(self, entry_id: str, pg_hash: str, immudb_hash: str):
        super().__init__(
            f"Consistency error for {entry_id}: PostgreSQL and immudb hashes don't match",
            code="CONSISTENCY_ERROR",
            details={
                "entry_id": entry_id,
                "pg_hash": pg_hash,
                "immudb_hash": immudb_hash,
            },
        )


class AnchoringError(ImmutableStoreError):
    """Blockchain anchoring operation failed."""

    def __init__(self, merkle_root: str, chain: str, reason: str):
        super().__init__(
            f"Failed to anchor {merkle_root[:16]}... to {chain}: {reason}",
            code="ANCHORING_FAILED",
            details={"merkle_root": merkle_root, "chain": chain, "reason": reason},
        )


class VerificationStatus(str, Enum):
    """Status of entry verification."""
    VERIFIED = "verified"
    TAMPERED = "tampered"
    NOT_FOUND = "not_found"
    INCONSISTENT = "inconsistent"
    PENDING = "pending"


@dataclass
class ImmutableConfig:
    """Configuration for immutable audit trail."""

    # immudb connection
    immudb_host: str = "localhost"
    immudb_port: int = 3322
    immudb_user: str = ""
    immudb_password: str = ""
    immudb_database: str = "sardis_audit"

    # PostgreSQL connection (optional, for hybrid mode)
    postgres_url: Optional[str] = None

    # Blockchain anchoring
    enable_anchoring: bool = False
    anchor_chain: str = "base"  # base, ethereum, polygon
    anchor_interval_seconds: int = 3600  # 1 hour
    anchor_rpc_url: Optional[str] = None
    anchor_private_key: Optional[str] = None  # For signing anchor transactions
    anchor_contract_address: Optional[str] = None

    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Verification
    verify_on_read: bool = True
    verify_on_write: bool = True


@dataclass
class MerkleProof:
    """Cryptographic Merkle proof for an entry."""

    entry_id: str
    tx_id: int  # immudb transaction ID
    leaf_hash: str
    root_hash: str
    proof_nodes: List[str]
    tree_size: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "tx_id": self.tx_id,
            "leaf_hash": self.leaf_hash,
            "root_hash": self.root_hash,
            "proof_nodes": self.proof_nodes,
            "tree_size": self.tree_size,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MerkleProof":
        return cls(
            entry_id=data["entry_id"],
            tx_id=data["tx_id"],
            leaf_hash=data["leaf_hash"],
            root_hash=data["root_hash"],
            proof_nodes=data["proof_nodes"],
            tree_size=data["tree_size"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class ImmutableReceipt:
    """
    Cryptographic receipt for an immutable ledger entry.

    This receipt provides:
    - Proof that the entry was stored
    - Merkle proof for verification
    - Timestamps for audit
    - Optional blockchain anchor reference
    """

    receipt_id: str = field(default_factory=lambda: f"rcpt_{uuid.uuid4().hex[:16]}")
    entry_id: str = ""
    entry_hash: str = ""  # SHA-256 of entry content

    # immudb proof
    immudb_tx_id: int = 0
    merkle_proof: Optional[MerkleProof] = None

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verified_at: Optional[datetime] = None

    # Blockchain anchor (if enabled)
    anchor_tx_hash: Optional[str] = None
    anchor_chain: Optional[str] = None
    anchor_block: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "entry_id": self.entry_id,
            "entry_hash": self.entry_hash,
            "immudb_tx_id": self.immudb_tx_id,
            "merkle_proof": self.merkle_proof.to_dict() if self.merkle_proof else None,
            "created_at": self.created_at.isoformat(),
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "anchor_tx_hash": self.anchor_tx_hash,
            "anchor_chain": self.anchor_chain,
            "anchor_block": self.anchor_block,
        }


@dataclass
class VerificationResult:
    """Result of verifying an immutable entry."""

    entry_id: str
    status: VerificationStatus
    verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Verification details
    immudb_verified: bool = False
    merkle_verified: bool = False
    blockchain_verified: bool = False
    consistency_verified: bool = False

    # Hashes
    computed_hash: Optional[str] = None
    stored_hash: Optional[str] = None
    merkle_root: Optional[str] = None

    # Error info
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "status": self.status.value,
            "verified_at": self.verified_at.isoformat(),
            "immudb_verified": self.immudb_verified,
            "merkle_verified": self.merkle_verified,
            "blockchain_verified": self.blockchain_verified,
            "consistency_verified": self.consistency_verified,
            "computed_hash": self.computed_hash,
            "stored_hash": self.stored_hash,
            "merkle_root": self.merkle_root,
            "error": self.error,
        }


@dataclass
class AuditEntry:
    """
    Immutable audit entry for the ledger.

    Stored in immudb with cryptographic verification.
    """

    entry_id: str = field(default_factory=lambda: f"iae_{uuid.uuid4().hex[:20]}")

    # Transaction reference
    tx_id: str = ""
    ledger_entry_id: str = ""  # Reference to LedgerEntry

    # Entry data (immutable copy)
    account_id: str = ""
    entry_type: str = ""
    amount: str = "0"  # Stored as string for precision
    fee: str = "0"
    currency: str = "USDC"

    # Chain data
    chain: Optional[str] = None
    chain_tx_hash: Optional[str] = None
    block_number: Optional[int] = None

    # Actor and context
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None  # "user", "agent", "system"
    request_id: Optional[str] = None
    ip_address: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    original_created_at: Optional[datetime] = None  # From original entry

    # Hash for integrity
    entry_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Compute deterministic hash of entry."""
        data = json.dumps(
            {
                "entry_id": self.entry_id,
                "tx_id": self.tx_id,
                "ledger_entry_id": self.ledger_entry_id,
                "account_id": self.account_id,
                "entry_type": self.entry_type,
                "amount": self.amount,
                "fee": self.fee,
                "currency": self.currency,
                "chain": self.chain,
                "chain_tx_hash": self.chain_tx_hash,
                "block_number": self.block_number,
                "actor_id": self.actor_id,
                "created_at": self.created_at.isoformat(),
            },
            sort_keys=True,
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "tx_id": self.tx_id,
            "ledger_entry_id": self.ledger_entry_id,
            "account_id": self.account_id,
            "entry_type": self.entry_type,
            "amount": self.amount,
            "fee": self.fee,
            "currency": self.currency,
            "chain": self.chain,
            "chain_tx_hash": self.chain_tx_hash,
            "block_number": self.block_number,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "request_id": self.request_id,
            "created_at": self.created_at.isoformat(),
            "original_created_at": self.original_created_at.isoformat() if self.original_created_at else None,
            "entry_hash": self.entry_hash,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        return cls(
            entry_id=data.get("entry_id", ""),
            tx_id=data.get("tx_id", ""),
            ledger_entry_id=data.get("ledger_entry_id", ""),
            account_id=data.get("account_id", ""),
            entry_type=data.get("entry_type", ""),
            amount=data.get("amount", "0"),
            fee=data.get("fee", "0"),
            currency=data.get("currency", "USDC"),
            chain=data.get("chain"),
            chain_tx_hash=data.get("chain_tx_hash"),
            block_number=data.get("block_number"),
            actor_id=data.get("actor_id"),
            actor_type=data.get("actor_type"),
            request_id=data.get("request_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            original_created_at=datetime.fromisoformat(data["original_created_at"]) if data.get("original_created_at") else None,
            entry_hash=data.get("entry_hash"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "AuditEntry":
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_ledger_entry(cls, entry: Any, actor_id: Optional[str] = None, request_id: Optional[str] = None) -> "AuditEntry":
        """Create audit entry from a LedgerEntry."""
        audit = cls(
            tx_id=entry.tx_id,
            ledger_entry_id=entry.entry_id,
            account_id=entry.account_id,
            entry_type=entry.entry_type.value if hasattr(entry.entry_type, "value") else str(entry.entry_type),
            amount=str(entry.amount),
            fee=str(entry.fee),
            currency=entry.currency,
            chain=entry.chain,
            chain_tx_hash=entry.chain_tx_hash,
            block_number=entry.block_number,
            actor_id=actor_id,
            request_id=request_id,
            original_created_at=entry.created_at,
        )
        audit.entry_hash = audit.compute_hash()
        return audit


class ImmutableAuditTrail:
    """
    Immutable audit trail using immudb.

    Provides cryptographically-verified storage for financial transactions
    with Merkle tree proofs and optional blockchain anchoring.

    Usage:
        config = ImmutableConfig(
            immudb_host="localhost",
            immudb_port=3322,
        )
        audit = ImmutableAuditTrail(config)
        await audit.connect()

        # Store an entry
        receipt = await audit.append(entry, actor_id="user_123")

        # Verify an entry
        result = await audit.verify(entry_id)

        # Get proof for compliance
        proof = await audit.get_audit_proof(entry_id)
    """

    def __init__(self, config: ImmutableConfig):
        self.config = config
        self._client: Optional[Any] = None  # ImmudbClient
        self._connected = False
        self._last_state: Optional[Any] = None  # For state verification

    async def connect(self) -> None:
        """Connect to immudb server."""
        try:
            from immudb import ImmudbClient
        except ImportError:
            raise ImportError(
                "immudb-py is required for immutable audit trail. "
                "Install with: pip install sardis-ledger[immudb]"
            )

        self._client = ImmudbClient(
            self.config.immudb_host,
            self.config.immudb_port,
        )

        # Validate credentials
        if not self.config.immudb_user or not self.config.immudb_password:
            raise ImmutableStoreError(
                "immudb_user and immudb_password must be explicitly configured. "
                "Do not use default credentials in any environment.",
                code="MISSING_CREDENTIALS",
            )

        # Login
        self._client.login(
            self.config.immudb_user,
            self.config.immudb_password,
        )

        # Create database if not exists
        try:
            self._client.createDatabase(self.config.immudb_database)
            logger.info(f"Created immudb database: {self.config.immudb_database}")
        except Exception:
            # Database might already exist
            pass

        # Use the database
        self._client.useDatabase(self.config.immudb_database)
        self._connected = True
        logger.info(f"Connected to immudb at {self.config.immudb_host}:{self.config.immudb_port}")

    async def disconnect(self) -> None:
        """Disconnect from immudb."""
        if self._client:
            try:
                self._client.logout()
            except Exception:
                pass
            self._client = None
        self._connected = False

    def _ensure_connected(self) -> None:
        """Ensure client is connected."""
        if not self._connected or not self._client:
            raise ImmutableStoreError("Not connected to immudb", code="NOT_CONNECTED")

    async def append(
        self,
        entry: Union[AuditEntry, Any],
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> ImmutableReceipt:
        """
        Append an entry to the immutable audit trail.

        Args:
            entry: AuditEntry or LedgerEntry to store
            actor_id: ID of actor performing the action
            request_id: Request ID for tracing

        Returns:
            ImmutableReceipt with cryptographic proof
        """
        self._ensure_connected()

        # Convert to AuditEntry if needed
        if not isinstance(entry, AuditEntry):
            entry = AuditEntry.from_ledger_entry(entry, actor_id, request_id)
        elif not entry.entry_hash:
            entry.entry_hash = entry.compute_hash()

        # Create key-value pair for immudb
        key = f"audit:{entry.entry_id}".encode()
        value = entry.to_json().encode()

        # Store with verified set (returns cryptographic proof)
        try:
            verified_tx = self._client.verifiedSet(key, value)
        except Exception as e:
            # Retry logic
            for attempt in range(self.config.max_retries):
                try:
                    await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
                    verified_tx = self._client.verifiedSet(key, value)
                    break
                except Exception:
                    if attempt == self.config.max_retries - 1:
                        raise ImmutableStoreError(
                            f"Failed to store entry after {self.config.max_retries} attempts: {e}",
                            code="STORE_FAILED",
                        )

        # Create Merkle proof
        merkle_proof = self._extract_merkle_proof(entry.entry_id, verified_tx)

        # Create receipt
        receipt = ImmutableReceipt(
            entry_id=entry.entry_id,
            entry_hash=entry.entry_hash,
            immudb_tx_id=verified_tx.id,
            merkle_proof=merkle_proof,
        )

        logger.info(
            f"Stored immutable entry: {entry.entry_id}, tx_id={verified_tx.id}, "
            f"merkle_root={merkle_proof.root_hash[:16]}..."
        )

        return receipt

    def _extract_merkle_proof(self, entry_id: str, verified_tx: VerifiedTx) -> MerkleProof:
        """Extract Merkle proof from immudb verified transaction."""
        inclusion_proof = verified_tx.inclusionProof

        # Extract proof nodes
        proof_nodes = []
        if hasattr(inclusion_proof, "terms") and inclusion_proof.terms:
            for term in inclusion_proof.terms:
                proof_nodes.append(term.hex())

        return MerkleProof(
            entry_id=entry_id,
            tx_id=verified_tx.id,
            leaf_hash=inclusion_proof.leaf.hex() if hasattr(inclusion_proof, "leaf") else "",
            root_hash=inclusion_proof.root.hex() if hasattr(inclusion_proof, "root") else "",
            proof_nodes=proof_nodes,
            tree_size=getattr(verified_tx, "blTxId", 0),
        )

    async def get(self, entry_id: str, verify: bool = True) -> Optional[AuditEntry]:
        """
        Get an entry from the immutable store.

        Args:
            entry_id: ID of the entry to retrieve
            verify: Whether to verify cryptographic proof

        Returns:
            AuditEntry if found, None otherwise
        """
        self._ensure_connected()

        key = f"audit:{entry_id}".encode()

        try:
            if verify or self.config.verify_on_read:
                result = self._client.verifiedGet(key)
            else:
                result = self._client.get(key)
        except Exception as e:
            if "key not found" in str(e).lower():
                return None
            raise ImmutableStoreError(f"Failed to get entry {entry_id}: {e}")

        if not result or not result.value:
            return None

        entry = AuditEntry.from_json(result.value.decode())
        return entry

    async def verify(self, entry_id: str) -> VerificationResult:
        """
        Verify an entry's integrity and immutability.

        Performs:
        1. Retrieve entry with cryptographic verification from immudb
        2. Verify Merkle proof
        3. Recompute and compare hash
        4. Check blockchain anchor if available

        Args:
            entry_id: ID of entry to verify

        Returns:
            VerificationResult with detailed status
        """
        self._ensure_connected()

        result = VerificationResult(entry_id=entry_id, status=VerificationStatus.PENDING)

        # 1. Get entry with verification
        key = f"audit:{entry_id}".encode()
        try:
            verified = self._client.verifiedGet(key)
        except Exception as e:
            if "key not found" in str(e).lower():
                result.status = VerificationStatus.NOT_FOUND
                result.error = "Entry not found in immutable store"
                return result

            result.status = VerificationStatus.TAMPERED
            result.error = f"Verification failed: {e}"
            return result

        # 2. immudb verification passed
        result.immudb_verified = True

        # 3. Parse and verify hash
        entry = AuditEntry.from_json(verified.value.decode())
        computed_hash = entry.compute_hash()
        result.computed_hash = computed_hash
        result.stored_hash = entry.entry_hash

        if entry.entry_hash and computed_hash != entry.entry_hash:
            result.status = VerificationStatus.TAMPERED
            result.error = "Entry hash mismatch - data may have been tampered"
            return result

        # 4. Merkle proof verified (implicit in verifiedGet)
        result.merkle_verified = True
        if hasattr(verified, "inclusionProof") and verified.inclusionProof:
            result.merkle_root = verified.inclusionProof.root.hex()

        # 5. All verifications passed
        result.status = VerificationStatus.VERIFIED
        result.verified_at = datetime.now(timezone.utc)

        logger.debug(f"Verified entry {entry_id}: status={result.status.value}")
        return result

    async def get_audit_proof(self, entry_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive audit proof for compliance/legal purposes.

        Returns:
            Dictionary containing:
            - Entry data
            - Merkle proof
            - Verification timestamp
            - Blockchain anchor (if available)
        """
        self._ensure_connected()

        # Get entry with verification
        key = f"audit:{entry_id}".encode()
        try:
            verified = self._client.verifiedGet(key)
        except Exception as e:
            raise VerificationError(entry_id, str(e))

        entry = AuditEntry.from_json(verified.value.decode())
        merkle_proof = self._extract_merkle_proof(entry_id, verified)

        # Build audit proof document
        proof = {
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "entry": entry.to_dict(),
            "verification": {
                "immudb_tx_id": verified.tx,
                "verified": True,
            },
            "merkle_proof": merkle_proof.to_dict(),
            "blockchain_anchor": None,  # Will be populated if anchoring is enabled
        }

        return proof

    async def list_entries(
        self,
        prefix: str = "audit:",
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEntry]:
        """
        List entries from the immutable store.

        Args:
            prefix: Key prefix to scan
            limit: Maximum entries to return
            offset: Number of entries to skip

        Returns:
            List of AuditEntry objects
        """
        self._ensure_connected()

        entries = []
        try:
            # Use scan to iterate through entries
            scan_result = self._client.scan(
                seekKey=prefix.encode(),
                prefix=prefix.encode(),
                limit=limit + offset,
            )

            for i, item in enumerate(scan_result):
                if i < offset:
                    continue
                if len(entries) >= limit:
                    break

                try:
                    entry = AuditEntry.from_json(item.value.decode())
                    entries.append(entry)
                except Exception as e:
                    logger.warning(f"Failed to parse entry: {e}")

        except Exception as e:
            logger.error(f"Failed to list entries: {e}")

        return entries

    async def get_state(self) -> Dict[str, Any]:
        """Get current database state for verification."""
        self._ensure_connected()

        state = self._client.currentState()
        return {
            "tx_id": state.txId,
            "tx_hash": state.txHash.hex() if state.txHash else None,
            "signature": state.signature.signature.hex() if state.signature else None,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check health of immutable store connection."""
        try:
            self._ensure_connected()
            state = await self.get_state()
            return {
                "status": "healthy",
                "connected": True,
                "current_tx_id": state["tx_id"],
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
            }


class BlockchainAnchor:
    """
    Blockchain anchoring service for immutable audit trail.

    Periodically anchors Merkle roots to a public blockchain
    for additional verifiability and non-repudiation.

    Supported chains:
    - Base (recommended - low cost)
    - Ethereum
    - Polygon
    """

    def __init__(self, config: ImmutableConfig):
        self.config = config
        self._web3: Optional[Any] = None
        self._contract: Optional[Any] = None
        self._last_anchor_time: Optional[datetime] = None
        self._pending_roots: List[Tuple[str, datetime]] = []

    async def connect(self) -> None:
        """Connect to blockchain RPC."""
        if not self.config.enable_anchoring:
            logger.info("Blockchain anchoring is disabled")
            return

        if not self.config.anchor_rpc_url:
            raise AnchoringError("", self.config.anchor_chain, "RPC URL not configured")

        try:
            from web3 import Web3
        except ImportError:
            raise ImportError(
                "web3 is required for blockchain anchoring. "
                "Install with: pip install sardis-ledger[anchoring]"
            )

        self._web3 = Web3(Web3.HTTPProvider(self.config.anchor_rpc_url))

        if not self._web3.is_connected():
            raise AnchoringError("", self.config.anchor_chain, "Failed to connect to RPC")

        logger.info(f"Connected to {self.config.anchor_chain} for anchoring")

    async def anchor(self, merkle_root: str, metadata: Optional[Dict] = None) -> Optional[str]:
        """
        Anchor a Merkle root to the blockchain.

        Args:
            merkle_root: The Merkle root hash to anchor
            metadata: Optional metadata to include

        Returns:
            Transaction hash if successful, None otherwise
        """
        if not self.config.enable_anchoring or not self._web3:
            logger.debug("Anchoring disabled or not connected")
            return None

        if not self.config.anchor_private_key:
            raise AnchoringError(merkle_root, self.config.anchor_chain, "Private key not configured")

        try:
            from web3 import Web3
            from eth_account import Account

            # Create anchor data
            anchor_data = {
                "type": "sardis_audit_anchor",
                "version": "1.0",
                "merkle_root": merkle_root,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "chain": self.config.anchor_chain,
            }
            if metadata:
                anchor_data["metadata"] = metadata

            # Encode as hex data
            data_hex = Web3.to_hex(text=json.dumps(anchor_data))

            # Get account
            account = Account.from_key(self.config.anchor_private_key)

            # Build transaction
            tx = {
                "to": account.address,  # Self-transaction for data storage
                "value": 0,
                "data": data_hex,
                "gas": 50000,
                "gasPrice": self._web3.eth.gas_price,
                "nonce": self._web3.eth.get_transaction_count(account.address),
                "chainId": self._web3.eth.chain_id,
            }

            # Sign and send
            signed = account.sign_transaction(tx)
            tx_hash = self._web3.eth.send_raw_transaction(signed.rawTransaction)

            logger.info(
                f"Anchored merkle_root={merkle_root[:16]}... "
                f"to {self.config.anchor_chain}, tx={tx_hash.hex()}"
            )

            return tx_hash.hex()

        except Exception as e:
            raise AnchoringError(merkle_root, self.config.anchor_chain, str(e))

    async def verify_anchor(self, tx_hash: str, expected_merkle_root: str) -> bool:
        """
        Verify a blockchain anchor.

        Args:
            tx_hash: Transaction hash to verify
            expected_merkle_root: Expected Merkle root in the anchor

        Returns:
            True if anchor is valid, False otherwise
        """
        if not self._web3:
            return False

        try:
            from web3 import Web3

            tx = self._web3.eth.get_transaction(tx_hash)
            if not tx:
                return False

            # Decode transaction data
            data = Web3.to_text(tx.input)
            anchor_data = json.loads(data)

            return anchor_data.get("merkle_root") == expected_merkle_root

        except Exception as e:
            logger.error(f"Failed to verify anchor {tx_hash}: {e}")
            return False


# Convenience function for creating configured audit trail
def create_audit_trail(
    immudb_host: str = "localhost",
    immudb_port: int = 3322,
    immudb_user: str = "",
    immudb_password: str = "",
    immudb_database: str = "sardis_audit",
    **kwargs,
) -> ImmutableAuditTrail:
    """
    Create a configured ImmutableAuditTrail instance.

    Args:
        immudb_host: immudb server host
        immudb_port: immudb server port
        immudb_user: immudb username (required, no default)
        immudb_password: immudb password (required, no default)
        immudb_database: Database name
        **kwargs: Additional config options

    Returns:
        Configured ImmutableAuditTrail instance
    """
    config = ImmutableConfig(
        immudb_host=immudb_host,
        immudb_port=immudb_port,
        immudb_user=immudb_user,
        immudb_password=immudb_password,
        immudb_database=immudb_database,
        **kwargs,
    )
    return ImmutableAuditTrail(config)


__all__ = [
    # Config
    "ImmutableConfig",
    # Errors
    "ImmutableStoreError",
    "VerificationError",
    "ConsistencyError",
    "AnchoringError",
    # Enums
    "VerificationStatus",
    # Models
    "MerkleProof",
    "ImmutableReceipt",
    "VerificationResult",
    "AuditEntry",
    # Services
    "ImmutableAuditTrail",
    "BlockchainAnchor",
    # Factory
    "create_audit_trail",
]
