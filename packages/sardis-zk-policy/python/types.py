"""Shared types between Python simulation and Noir circuit."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass(slots=True)
class PolicyCircuitInputs:
    """Private inputs to the ZK circuit (witness)."""
    amount: int
    daily_total: int
    merchant_total: int
    mcc_hash: int
    hour: int  # 0-23
    max_per_transaction: int
    daily_limit: int
    per_merchant_limit: int
    window_start: int  # 0-23
    window_end: int  # 0-23
    blocked_mcc_hashes: list[int] = field(default_factory=lambda: [0] * 8)


@dataclass(slots=True)
class PolicyCircuitPublicInputs:
    """Public inputs to the ZK circuit."""
    evidence_hash_high: int  # upper 128 bits of SHA-256
    evidence_hash_low: int  # lower 128 bits of SHA-256


def mcc_to_hash(mcc_code: str) -> int:
    """Hash an MCC code string to a u64 for circuit use."""
    h = hashlib.sha256(mcc_code.encode()).digest()
    return int.from_bytes(h[:8], "big")


def evidence_hash_to_pair(hex_hash: str) -> tuple[int, int]:
    """Split a 64-char hex SHA-256 hash into (high_u128, low_u128)."""
    raw = bytes.fromhex(hex_hash)
    high = int.from_bytes(raw[:16], "big")
    low = int.from_bytes(raw[16:], "big")
    return high, low
