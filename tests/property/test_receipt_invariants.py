"""Property-based tests for execution receipt invariants.

Invariants tested:
1. Receipt signature is deterministic (same inputs → same signature)
2. Receipt verification detects tampering
3. Receipt with different secret fails verification
"""
from __future__ import annotations

import pytest

try:
    from hypothesis import given, settings, strategies as st
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
    def given(*a, **kw):
        def decorator(fn):
            return pytest.mark.skip(reason="hypothesis not installed")(fn)
        return decorator
    settings = lambda **kw: lambda fn: fn
    class st:
        text = staticmethod(lambda **kw: None)

from sardis_v2_core.execution_receipt import ExecutionReceipt, build_receipt, hash_artifact


def test_receipt_signature_deterministic():
    """Same inputs must produce the same signature."""
    r1 = build_receipt(
        intent={"amount": "100"},
        tx_hash="0xabc",
        chain="base",
        org_id="org1",
        agent_id="agent1",
        amount="100",
        currency="USDC",
    )
    r2 = ExecutionReceipt(
        receipt_id=r1.receipt_id,
        timestamp=r1.timestamp,
        intent_hash=r1.intent_hash,
        policy_snapshot_hash=r1.policy_snapshot_hash,
        compliance_result_hash=r1.compliance_result_hash,
        tx_hash="0xabc",
        chain="base",
        org_id="org1",
        agent_id="agent1",
        amount="100",
        currency="USDC",
    ).sign()

    assert r1.signature == r2.signature


def test_receipt_tamper_detection():
    """Modifying any field must invalidate the signature."""
    receipt = build_receipt(
        intent={"amount": "100"},
        tx_hash="0xabc",
        chain="base",
        org_id="org1",
        amount="100",
        currency="USDC",
    )

    assert receipt.verify()

    # Tamper with amount
    receipt.amount = "200"
    assert not receipt.verify(), "Tampered receipt should fail verification"


def test_receipt_wrong_secret_fails():
    """Verification with a different secret must fail."""
    receipt = build_receipt(
        intent={"amount": "100"},
        tx_hash="0xdef",
        chain="base",
        org_id="org1",
        amount="100",
        currency="USDC",
    )
    # Sign with one secret
    receipt.sign("secret_one")

    # Verify with different secret
    assert not receipt.verify("secret_two")


def test_hash_artifact_consistency():
    """Same data must produce same hash."""
    data = {"key": "value", "amount": 100}
    h1 = hash_artifact(data)
    h2 = hash_artifact(data)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_production_guard_in_memory_session():
    """InMemorySessionStore must reject production."""
    import os
    old = os.environ.get("SARDIS_ENVIRONMENT")
    os.environ["SARDIS_ENVIRONMENT"] = "production"
    try:
        from sardis_checkout.sessions import InMemorySessionStore
        with pytest.raises(RuntimeError, match="CRITICAL"):
            InMemorySessionStore()
    finally:
        if old is not None:
            os.environ["SARDIS_ENVIRONMENT"] = old
        elif "SARDIS_ENVIRONMENT" in os.environ:
            del os.environ["SARDIS_ENVIRONMENT"]
