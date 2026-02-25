from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sardis_v2_core.policy_attestation import (
    build_policy_decision_receipt,
    canonicalize_policy_for_hash,
    compute_policy_hash,
)
from sardis_v2_core.spending_policy import SpendingPolicy


def test_policy_hash_ignores_mutable_spend_state():
    policy = SpendingPolicy(
        agent_id="agent_1",
        limit_total=Decimal("1000"),
        limit_per_tx=Decimal("100"),
    )
    policy.spent_total = Decimal("10")
    hash_a = compute_policy_hash(policy)

    policy.spent_total = Decimal("999")
    policy.updated_at = datetime.now(timezone.utc)
    hash_b = compute_policy_hash(policy)

    assert hash_a == hash_b


def test_policy_hash_changes_when_guardrails_change():
    policy = SpendingPolicy(
        agent_id="agent_1",
        limit_total=Decimal("1000"),
    )
    hash_a = compute_policy_hash(policy)
    policy.allowed_destination_addresses = ["0xabc"]
    hash_b = compute_policy_hash(policy)
    assert hash_a != hash_b


def test_build_policy_decision_receipt_has_merkle_anchor():
    policy = SpendingPolicy(agent_id="agent_1", limit_total=Decimal("1000"))
    receipt = build_policy_decision_receipt(
        policy=policy,
        decision="allow",
        reason="OK",
        context={"destination": "0xabc", "chain": "base", "token": "USDC"},
    )

    assert receipt.policy_hash
    assert receipt.context_hash
    assert receipt.decision_hash
    assert receipt.merkle_root
    assert receipt.audit_anchor.startswith("merkle::")


def test_canonical_payload_excludes_runtime_fields():
    policy = SpendingPolicy(agent_id="agent_1", limit_total=Decimal("1000"))
    payload = canonicalize_policy_for_hash(policy)
    assert "spent_total" not in payload
    assert "created_at" not in payload
    assert "updated_at" not in payload
