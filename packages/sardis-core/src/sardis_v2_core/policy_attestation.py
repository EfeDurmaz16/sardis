"""Deterministic policy attestation and decision receipt helpers."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .spending_policy import SpendingPolicy
from .spending_policy_json import spending_policy_to_json


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _merkle_pair(left_hash: str, right_hash: str) -> str:
    left = (left_hash or "").strip().lower()
    right = (right_hash or "").strip().lower()
    combined = left + right if left <= right else right + left
    return _sha256_hex(combined)


def _merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return ""
    level = [(leaf or "").strip().lower() for leaf in leaves if (leaf or "").strip()]
    if not level:
        return ""
    while len(level) > 1:
        nxt: list[str] = []
        for idx in range(0, len(level), 2):
            left = level[idx]
            right = level[idx + 1] if idx + 1 < len(level) else left
            nxt.append(_merkle_pair(left, right))
        level = nxt
    return level[0]


def canonicalize_policy_for_hash(policy: SpendingPolicy) -> dict[str, Any]:
    """
    Return a stable policy payload for attestation hashing.

    Excludes mutable runtime counters/timestamps so hash changes represent
    policy intent changes, not normal spending progression.
    """
    payload = spending_policy_to_json(policy)
    payload.pop("spent_total", None)
    payload.pop("created_at", None)
    payload.pop("updated_at", None)

    for key in ("daily_limit", "weekly_limit", "monthly_limit"):
        tw = payload.get(key)
        if isinstance(tw, dict):
            tw.pop("current_spent", None)
            tw.pop("window_start", None)

    for rule in payload.get("merchant_rules", []) or []:
        if isinstance(rule, dict):
            rule.pop("created_at", None)

    return payload


def compute_policy_hash(policy: SpendingPolicy) -> str:
    canonical = canonicalize_policy_for_hash(policy)
    return _sha256_hex(_stable_json(canonical))


@dataclass(slots=True)
class PolicyDecisionReceipt:
    """Attested policy decision receipt with merkle anchor."""

    decision_id: str = field(default_factory=lambda: f"pdec_{uuid.uuid4().hex[:16]}")
    policy_id: str = ""
    policy_hash: str = ""
    decision: str = ""
    reason: str = "OK"
    context_hash: str = ""
    decision_hash: str = ""
    merkle_root: str = ""
    audit_anchor: str = ""
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "policy_id": self.policy_id,
            "policy_hash": self.policy_hash,
            "decision": self.decision,
            "reason": self.reason,
            "context_hash": self.context_hash,
            "decision_hash": self.decision_hash,
            "merkle_root": self.merkle_root,
            "audit_anchor": self.audit_anchor,
            "issued_at": self.issued_at.isoformat(),
            "context": self.context,
        }


def build_policy_decision_receipt(
    *,
    policy: SpendingPolicy,
    decision: str,
    reason: str,
    context: dict[str, Any],
    decision_id: str | None = None,
) -> PolicyDecisionReceipt:
    policy_hash = compute_policy_hash(policy)
    context_hash = _sha256_hex(_stable_json(context))
    decision_payload = {
        "decision_id": decision_id or "",
        "policy_hash": policy_hash,
        "decision": decision,
        "reason": reason,
        "context_hash": context_hash,
    }
    decision_hash = _sha256_hex(_stable_json(decision_payload))
    merkle_root = _merkle_root([policy_hash, context_hash, decision_hash])
    receipt = PolicyDecisionReceipt(
        decision_id=decision_id or f"pdec_{uuid.uuid4().hex[:16]}",
        policy_id=policy.policy_id,
        policy_hash=policy_hash,
        decision=decision,
        reason=reason,
        context_hash=context_hash,
        decision_hash=decision_hash,
        merkle_root=merkle_root,
        audit_anchor=f"merkle::{merkle_root}",
        context=context,
    )
    return receipt

