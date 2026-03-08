"""Noir equivalence tests — placeholder for when `nargo prove` is available.

These tests document the expected equivalence between the Python
simulation and the Noir circuit. When Noir tooling matures, uncomment
the nargo-based tests to verify that both produce identical proofs
for the same inputs.

Status: SCAFFOLD — Python simulation tests only.
TODO: Enable when nargo CLI is available in CI.
"""
from __future__ import annotations

import pytest
from python.types import PolicyCircuitInputs, PolicyCircuitPublicInputs, evidence_hash_to_pair
from python.policy_circuit_sim import simulate_circuit


VALID_HASH = "a" * 64
VALID_HIGH, VALID_LOW = evidence_hash_to_pair(VALID_HASH)


# ============ Equivalence Test Cases ============
# Each case defines inputs and expected outcome.
# When Noir is available, run the same inputs through `nargo prove`
# and verify that:
#   - Python sim passes  <=> Noir proof succeeds
#   - Python sim fails   <=> Noir proof fails (constraint violation)

EQUIVALENCE_CASES = [
    {
        "name": "all_pass",
        "private": PolicyCircuitInputs(
            amount=100, daily_total=0, merchant_total=0,
            mcc_hash=12345, hour=12,
            max_per_transaction=500, daily_limit=10000,
            per_merchant_limit=5000, window_start=9, window_end=17,
            blocked_mcc_hashes=[0] * 8,
        ),
        "public": PolicyCircuitPublicInputs(evidence_hash_high=VALID_HIGH, evidence_hash_low=VALID_LOW),
        "expected_pass": True,
    },
    {
        "name": "amount_overflow",
        "private": PolicyCircuitInputs(
            amount=1000, daily_total=0, merchant_total=0,
            mcc_hash=12345, hour=12,
            max_per_transaction=500, daily_limit=10000,
            per_merchant_limit=5000, window_start=9, window_end=17,
            blocked_mcc_hashes=[0] * 8,
        ),
        "public": PolicyCircuitPublicInputs(evidence_hash_high=VALID_HIGH, evidence_hash_low=VALID_LOW),
        "expected_pass": False,
    },
    {
        "name": "daily_overflow",
        "private": PolicyCircuitInputs(
            amount=100, daily_total=9950, merchant_total=0,
            mcc_hash=12345, hour=12,
            max_per_transaction=500, daily_limit=10000,
            per_merchant_limit=5000, window_start=9, window_end=17,
            blocked_mcc_hashes=[0] * 8,
        ),
        "public": PolicyCircuitPublicInputs(evidence_hash_high=VALID_HIGH, evidence_hash_low=VALID_LOW),
        "expected_pass": False,
    },
    {
        "name": "mcc_blocked",
        "private": PolicyCircuitInputs(
            amount=100, daily_total=0, merchant_total=0,
            mcc_hash=99999, hour=12,
            max_per_transaction=500, daily_limit=10000,
            per_merchant_limit=5000, window_start=9, window_end=17,
            blocked_mcc_hashes=[99999, 0, 0, 0, 0, 0, 0, 0],
        ),
        "public": PolicyCircuitPublicInputs(evidence_hash_high=VALID_HIGH, evidence_hash_low=VALID_LOW),
        "expected_pass": False,
    },
    {
        "name": "outside_window",
        "private": PolicyCircuitInputs(
            amount=100, daily_total=0, merchant_total=0,
            mcc_hash=12345, hour=20,
            max_per_transaction=500, daily_limit=10000,
            per_merchant_limit=5000, window_start=9, window_end=17,
            blocked_mcc_hashes=[0] * 8,
        ),
        "public": PolicyCircuitPublicInputs(evidence_hash_high=VALID_HIGH, evidence_hash_low=VALID_LOW),
        "expected_pass": False,
    },
]


@pytest.mark.parametrize(
    "case",
    EQUIVALENCE_CASES,
    ids=[c["name"] for c in EQUIVALENCE_CASES],
)
def test_python_simulation(case):
    """Verify Python simulation produces expected result."""
    result = simulate_circuit(case["private"], case["public"])
    assert result.passed == case["expected_pass"], (
        f"Case '{case['name']}': expected passed={case['expected_pass']}, "
        f"got passed={result.passed} (failed_check={result.failed_check})"
    )


# ============ Noir Prover Tests (DISABLED) ============
# Uncomment when `nargo` CLI is available in the CI environment.
#
# import subprocess
# import json
# import tempfile
#
# @pytest.mark.parametrize("case", EQUIVALENCE_CASES, ids=[c["name"] for c in EQUIVALENCE_CASES])
# def test_noir_equivalence(case):
#     """Verify Noir circuit matches Python simulation."""
#     # Write Prover.toml with case inputs
#     # Run: nargo prove
#     # If expected_pass=True: assert proof succeeded
#     # If expected_pass=False: assert proof failed with constraint violation
#     pytest.skip("Noir tooling not yet available in CI")
