"""Tests for the Python simulation of the Noir ZK policy circuit.

Each test mirrors a specific circuit assertion in main.nr to ensure
the Python simulation produces identical results.
"""
from __future__ import annotations

import pytest
from python.types import (
    PolicyCircuitInputs,
    PolicyCircuitPublicInputs,
    mcc_to_hash,
    evidence_hash_to_pair,
)
from python.policy_circuit_sim import (
    simulate_circuit,
    prepare_circuit_inputs,
    check_amount,
    check_daily_limit,
    check_mcc,
    check_time_window,
    check_per_merchant_limit,
    CircuitResult,
)


# ============ Helpers ============

# A valid evidence hash (any non-zero 256-bit value)
VALID_HASH = "a" * 64
VALID_HIGH, VALID_LOW = evidence_hash_to_pair(VALID_HASH)


def _inputs(**overrides) -> tuple[PolicyCircuitInputs, PolicyCircuitPublicInputs]:
    """Create default all-passing inputs with optional overrides."""
    # Separate public input overrides from private
    pub_high = overrides.pop("evidence_hash_high", VALID_HIGH)
    pub_low = overrides.pop("evidence_hash_low", VALID_LOW)
    defaults = dict(
        amount=100,
        daily_total=500,
        merchant_total=200,
        mcc_hash=12345,
        hour=14,
        max_per_transaction=1000,
        daily_limit=10000,
        per_merchant_limit=5000,
        window_start=9,
        window_end=17,
        blocked_mcc_hashes=[0] * 8,
    )
    defaults.update(overrides)
    private = PolicyCircuitInputs(**defaults)
    public = PolicyCircuitPublicInputs(
        evidence_hash_high=pub_high,
        evidence_hash_low=pub_low,
    )
    return private, public


# ============ All-Pass Tests ============


def test_all_checks_pass():
    private, public = _inputs()
    result = simulate_circuit(private, public)
    assert result.passed is True
    assert result.failed_check is None


def test_exactly_at_per_tx_limit():
    """amount == max_per_transaction should pass (<=)."""
    private, public = _inputs(amount=1000, max_per_transaction=1000)
    result = simulate_circuit(private, public)
    assert result.passed is True


def test_exactly_at_daily_limit():
    """daily_total + amount == daily_limit should pass."""
    private, public = _inputs(amount=500, daily_total=500, daily_limit=1000)
    result = simulate_circuit(private, public)
    assert result.passed is True


def test_exactly_at_merchant_limit():
    """merchant_total + amount == per_merchant_limit should pass."""
    private, public = _inputs(amount=100, merchant_total=900, per_merchant_limit=1000)
    result = simulate_circuit(private, public)
    assert result.passed is True


def test_zero_amount():
    """Zero amount should pass all checks."""
    private, public = _inputs(amount=0)
    result = simulate_circuit(private, public)
    assert result.passed is True


# ============ Individual Check Failure Tests ============


def test_amount_exceeds_limit():
    private, public = _inputs(amount=1001, max_per_transaction=1000)
    result = simulate_circuit(private, public)
    assert result.passed is False
    assert result.failed_check == "amount exceeds per-transaction limit"


def test_daily_limit_exceeded():
    private, public = _inputs(amount=600, daily_total=500, daily_limit=1000)
    result = simulate_circuit(private, public)
    assert result.passed is False
    assert result.failed_check == "daily limit exceeded"


def test_mcc_blocked():
    blocked_hash = mcc_to_hash("7995")  # gambling MCC
    private, public = _inputs(
        mcc_hash=blocked_hash,
        blocked_mcc_hashes=[blocked_hash, 0, 0, 0, 0, 0, 0, 0],
    )
    result = simulate_circuit(private, public)
    assert result.passed is False
    assert result.failed_check == "merchant category blocked"


def test_mcc_not_in_blocked_list():
    blocked_hash = mcc_to_hash("7995")
    safe_hash = mcc_to_hash("5411")  # grocery
    private, public = _inputs(
        mcc_hash=safe_hash,
        blocked_mcc_hashes=[blocked_hash, 0, 0, 0, 0, 0, 0, 0],
    )
    result = simulate_circuit(private, public)
    assert result.passed is True


def test_outside_time_window_before():
    private, public = _inputs(hour=8, window_start=9, window_end=17)
    result = simulate_circuit(private, public)
    assert result.passed is False
    assert "time window" in result.failed_check


def test_outside_time_window_after():
    private, public = _inputs(hour=18, window_start=9, window_end=17)
    result = simulate_circuit(private, public)
    assert result.passed is False
    assert "time window" in result.failed_check


def test_time_window_wraparound_inside():
    """Wrap-around window: 22:00 to 06:00. Hour 23 should pass."""
    private, public = _inputs(hour=23, window_start=22, window_end=6)
    result = simulate_circuit(private, public)
    assert result.passed is True


def test_time_window_wraparound_inside_morning():
    """Wrap-around window: 22:00 to 06:00. Hour 3 should pass."""
    private, public = _inputs(hour=3, window_start=22, window_end=6)
    result = simulate_circuit(private, public)
    assert result.passed is True


def test_time_window_wraparound_outside():
    """Wrap-around window: 22:00 to 06:00. Hour 12 should fail."""
    private, public = _inputs(hour=12, window_start=22, window_end=6)
    result = simulate_circuit(private, public)
    assert result.passed is False
    assert "time window" in result.failed_check


def test_time_window_boundary_start():
    """Exactly at window_start should pass."""
    private, public = _inputs(hour=9, window_start=9, window_end=17)
    result = simulate_circuit(private, public)
    assert result.passed is True


def test_time_window_boundary_end():
    """Exactly at window_end should pass."""
    private, public = _inputs(hour=17, window_start=9, window_end=17)
    result = simulate_circuit(private, public)
    assert result.passed is True


def test_midnight_boundary():
    """Hour 0 in a 0-23 window should pass."""
    private, public = _inputs(hour=0, window_start=0, window_end=23)
    result = simulate_circuit(private, public)
    assert result.passed is True


def test_per_merchant_limit_exceeded():
    private, public = _inputs(amount=200, merchant_total=900, per_merchant_limit=1000)
    result = simulate_circuit(private, public)
    assert result.passed is False
    assert result.failed_check == "per-merchant limit exceeded"


def test_evidence_hash_zero():
    private, public = _inputs(evidence_hash_high=0, evidence_hash_low=0)
    result = simulate_circuit(private, public)
    assert result.passed is False
    assert "evidence hash" in result.failed_check


# ============ Multiple Blocked MCCs ============


def test_multiple_blocked_mccs():
    """Multiple blocked categories — any match should fail."""
    h1 = mcc_to_hash("7995")
    h2 = mcc_to_hash("5813")
    h3 = mcc_to_hash("7273")

    private, public = _inputs(
        mcc_hash=h2,
        blocked_mcc_hashes=[h1, h2, h3, 0, 0, 0, 0, 0],
    )
    result = simulate_circuit(private, public)
    assert result.passed is False

    # Non-blocked MCC
    private2, public2 = _inputs(
        mcc_hash=mcc_to_hash("5411"),
        blocked_mcc_hashes=[h1, h2, h3, 0, 0, 0, 0, 0],
    )
    result2 = simulate_circuit(private2, public2)
    assert result2.passed is True


# ============ prepare_circuit_inputs Tests ============


def test_prepare_circuit_inputs():
    """prepare_circuit_inputs produces valid input pairs."""
    private, public = prepare_circuit_inputs(
        amount=100,
        daily_total=0,
        merchant_total=0,
        mcc_hash=12345,
        hour=12,
        max_per_transaction=500,
        daily_limit=1000,
        per_merchant_limit=500,
        window_start=9,
        window_end=17,
        blocked_mcc_hashes=[],
        evidence_hash=VALID_HASH,
    )

    assert private.amount == 100
    assert len(private.blocked_mcc_hashes) == 8
    assert public.evidence_hash_high == VALID_HIGH
    assert public.evidence_hash_low == VALID_LOW

    result = simulate_circuit(private, public)
    assert result.passed is True


def test_prepare_pads_blocked_mccs():
    """Short blocked list is padded to 8 entries."""
    private, _ = prepare_circuit_inputs(
        amount=0, daily_total=0, merchant_total=0, mcc_hash=0, hour=0,
        max_per_transaction=0, daily_limit=0, per_merchant_limit=0,
        window_start=0, window_end=23,
        blocked_mcc_hashes=[111, 222],
        evidence_hash=VALID_HASH,
    )
    assert len(private.blocked_mcc_hashes) == 8
    assert private.blocked_mcc_hashes[0] == 111
    assert private.blocked_mcc_hashes[1] == 222
    assert private.blocked_mcc_hashes[2] == 0


# ============ Types Tests ============


def test_mcc_to_hash_determinism():
    h1 = mcc_to_hash("5411")
    h2 = mcc_to_hash("5411")
    assert h1 == h2


def test_mcc_to_hash_different():
    h1 = mcc_to_hash("5411")
    h2 = mcc_to_hash("7995")
    assert h1 != h2


def test_evidence_hash_to_pair():
    h = "00" * 16 + "ff" * 16
    high, low = evidence_hash_to_pair(h)
    assert high == 0
    assert low == (2**128 - 1)


def test_evidence_hash_roundtrip():
    """Splitting and reconstructing should give back the original hash."""
    original = "abcdef0123456789" * 4  # 64 hex chars
    high, low = evidence_hash_to_pair(original)
    reconstructed = f"{high:032x}{low:032x}"
    assert reconstructed == original
