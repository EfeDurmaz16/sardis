"""Content-addressed hashing for tamper-evident ledger entries.

Ported from agit (Rust): crates/agit-core/src/hash.rs
Pattern: canonical JSON serialization → SHA-256 with type prefix header.
Each entry includes `previous_hash` to form a hash chain.

Usage:
    entry_hash = compute_entry_hash(entry_dict, previous_hash="abc...")
    verify_chain(entries)  # raises if any entry's hash is invalid
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional


def canonical_serialize(value: Any) -> bytes:
    """Serialize a value to canonical JSON with sorted keys.

    Mirrors agit's `canonical_serialize` in `hash.rs`:
    - Object keys are sorted recursively
    - No extra whitespace
    - Deterministic output for identical data
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_hash(obj_type: str, content: bytes) -> str:
    """Compute SHA-256 using git-style header: '<type> <len>\\0<content>'.

    Mirrors agit's `compute_hash` in `hash.rs`.
    """
    header = f"{obj_type} {len(content)}\0".encode("utf-8")
    h = hashlib.sha256()
    h.update(header)
    h.update(content)
    return h.hexdigest()


def compute_entry_hash(
    entry: dict[str, Any],
    previous_hash: Optional[str] = None,
) -> str:
    """Compute a content-addressed hash for a ledger entry.

    The hash covers the canonical fields of the entry plus the previous
    entry's hash, forming a hash chain.

    Args:
        entry: Ledger entry as a dict. Must contain at least:
            entry_id, tx_id, account_id, entry_type, amount, fee,
            currency, chain, chain_tx_hash, created_at
        previous_hash: Hash of the preceding entry (None for genesis).

    Returns:
        64-character hex SHA-256 hash.
    """
    # Build canonical payload with sorted, deterministic fields
    payload = {
        "account_id": entry.get("account_id", ""),
        "amount": str(entry.get("amount", "0")),
        "chain": entry.get("chain") or "",
        "chain_tx_hash": entry.get("chain_tx_hash") or "",
        "created_at": str(entry.get("created_at", "")),
        "currency": entry.get("currency", "USDC"),
        "entry_id": entry.get("entry_id", ""),
        "entry_type": str(entry.get("entry_type", "")),
        "fee": str(entry.get("fee", "0")),
        "previous_hash": previous_hash or "",
        "tx_id": entry.get("tx_id", ""),
    }
    content = canonical_serialize(payload)
    return compute_hash("ledger_entry", content)


def compute_audit_hash(
    audit: dict[str, Any],
    previous_hash: Optional[str] = None,
) -> str:
    """Compute a content-addressed hash for an audit log entry."""
    payload = {
        "action": str(audit.get("action", "")),
        "actor_id": audit.get("actor_id") or "",
        "audit_id": audit.get("audit_id", ""),
        "created_at": str(audit.get("created_at", "")),
        "entity_id": audit.get("entity_id", ""),
        "entity_type": audit.get("entity_type", ""),
        "previous_hash": previous_hash or "",
    }
    content = canonical_serialize(payload)
    return compute_hash("audit_entry", content)


def verify_entry_chain(entries: list[dict[str, Any]]) -> bool:
    """Verify the hash chain integrity of a sequence of ledger entries.

    Args:
        entries: Ordered list of entry dicts, each having 'entry_hash'
                 and optionally 'previous_hash'.

    Returns:
        True if the chain is valid.

    Raises:
        HashChainError: If any entry's hash doesn't match its content.
    """
    prev_hash: Optional[str] = None
    for i, entry in enumerate(entries):
        expected = compute_entry_hash(entry, previous_hash=prev_hash)
        actual = entry.get("entry_hash", "")
        if actual and actual != expected:
            raise HashChainError(
                f"Hash mismatch at index {i} (entry_id={entry.get('entry_id')}): "
                f"expected={expected[:16]}..., actual={actual[:16]}..."
            )
        prev_hash = actual or expected
    return True


class HashChainError(Exception):
    """Raised when hash chain verification fails."""
