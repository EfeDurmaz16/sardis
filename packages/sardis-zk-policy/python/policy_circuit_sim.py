"""Python simulation of the Noir ZK policy circuit.

Mirrors the logic in src/main.nr exactly, so we can test correctness
before deploying the actual Noir prover. When `nargo prove` becomes
available, test_noir_equivalence.py will verify that both produce
identical results for the same inputs.

Usage:
    from sardis_zk_policy.python.policy_circuit_sim import simulate_circuit
    from sardis_zk_policy.python.types import PolicyCircuitInputs, PolicyCircuitPublicInputs

    result = simulate_circuit(private_inputs, public_inputs)
    # result.passed: bool
    # result.failed_check: Optional[str]
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .types import PolicyCircuitInputs, PolicyCircuitPublicInputs


@dataclass(slots=True)
class CircuitResult:
    """Result of simulating the ZK circuit."""
    passed: bool
    failed_check: Optional[str] = None


def check_amount(inputs: PolicyCircuitInputs) -> Optional[str]:
    """Check 1: amount <= max_per_transaction."""
    if inputs.amount > inputs.max_per_transaction:
        return "amount exceeds per-transaction limit"
    return None


def check_daily_limit(inputs: PolicyCircuitInputs) -> Optional[str]:
    """Check 2: daily_total + amount <= daily_limit."""
    if inputs.daily_total + inputs.amount > inputs.daily_limit:
        return "daily limit exceeded"
    return None


def check_mcc(inputs: PolicyCircuitInputs) -> Optional[str]:
    """Check 3: mcc_hash NOT IN blocked_mcc_hashes."""
    for blocked in inputs.blocked_mcc_hashes:
        if blocked != 0 and blocked == inputs.mcc_hash:
            return "merchant category blocked"
    return None


def check_time_window(inputs: PolicyCircuitInputs) -> Optional[str]:
    """Check 4: hour within [window_start, window_end].

    Supports wrap-around windows (e.g., 22:00 to 06:00).
    """
    if inputs.window_start <= inputs.window_end:
        # Normal window
        if inputs.hour < inputs.window_start or inputs.hour > inputs.window_end:
            return "outside time window"
    else:
        # Wrap-around window
        if inputs.hour < inputs.window_start and inputs.hour > inputs.window_end:
            return "outside time window (wrap-around)"
    return None


def check_per_merchant_limit(inputs: PolicyCircuitInputs) -> Optional[str]:
    """Check 5: merchant_total + amount <= per_merchant_limit."""
    if inputs.merchant_total + inputs.amount > inputs.per_merchant_limit:
        return "per-merchant limit exceeded"
    return None


def check_evidence_hash(public: PolicyCircuitPublicInputs) -> Optional[str]:
    """Evidence hash must be non-zero."""
    if public.evidence_hash_high == 0:
        return "evidence hash must be non-zero"
    return None


def simulate_circuit(
    private: PolicyCircuitInputs,
    public: PolicyCircuitPublicInputs,
) -> CircuitResult:
    """Simulate the Noir circuit in Python.

    Runs all 5 policy checks in order, mirroring main.nr exactly.
    Returns CircuitResult with passed=True if all checks pass.
    """
    checks = [
        lambda: check_amount(private),
        lambda: check_daily_limit(private),
        lambda: check_mcc(private),
        lambda: check_time_window(private),
        lambda: check_per_merchant_limit(private),
        lambda: check_evidence_hash(public),
    ]

    for check_fn in checks:
        failure = check_fn()
        if failure is not None:
            return CircuitResult(passed=False, failed_check=failure)

    return CircuitResult(passed=True)


def prepare_circuit_inputs(
    amount: int,
    daily_total: int,
    merchant_total: int,
    mcc_hash: int,
    hour: int,
    max_per_transaction: int,
    daily_limit: int,
    per_merchant_limit: int,
    window_start: int,
    window_end: int,
    blocked_mcc_hashes: list[int],
    evidence_hash: str,
) -> tuple[PolicyCircuitInputs, PolicyCircuitPublicInputs]:
    """Convert Sardis domain values into circuit-ready inputs.

    Args:
        evidence_hash: 64-char hex SHA-256 hash from policy evidence module.

    Returns:
        (private_inputs, public_inputs) ready for simulate_circuit().
    """
    from .types import evidence_hash_to_pair

    # Pad blocked_mcc_hashes to exactly 8 entries
    padded = (blocked_mcc_hashes + [0] * 8)[:8]

    high, low = evidence_hash_to_pair(evidence_hash)

    private = PolicyCircuitInputs(
        amount=amount,
        daily_total=daily_total,
        merchant_total=merchant_total,
        mcc_hash=mcc_hash,
        hour=hour,
        max_per_transaction=max_per_transaction,
        daily_limit=daily_limit,
        per_merchant_limit=per_merchant_limit,
        window_start=window_start,
        window_end=window_end,
        blocked_mcc_hashes=padded,
    )

    public = PolicyCircuitPublicInputs(
        evidence_hash_high=high,
        evidence_hash_low=low,
    )

    return private, public
