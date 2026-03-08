"""Policy DSL — structured policy definitions that compile to SpendingPolicy.

Provides a JSON-friendly policy definition format for programmatic creation,
versioning, and simulation of spending policies.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from .spending_policy import (
    SpendingPolicy,
    TimeWindowLimit,
    MerchantRule,
    TrustLevel,
    SpendingScope,
    DEFAULT_LIMITS,
)


@dataclass
class PolicyRule:
    """Single policy rule in the DSL."""
    type: str           # Rule type (see RULE_TYPES)
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyDefinition:
    """Complete policy definition in DSL format."""
    version: str = "1.0"
    rules: list[PolicyRule] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)  # name, description, created_by, etc.
    definition_id: str = field(default_factory=lambda: f"pdef_{uuid.uuid4().hex[:16]}")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "definition_id": self.definition_id,
            "version": self.version,
            "rules": [{"type": r.type, "params": r.params} for r in self.rules],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyDefinition":
        rules = [PolicyRule(type=r["type"], params=r.get("params", {})) for r in data.get("rules", [])]
        return cls(
            version=data.get("version", "1.0"),
            rules=rules,
            metadata=data.get("metadata", {}),
            definition_id=data.get("definition_id", f"pdef_{uuid.uuid4().hex[:16]}"),
        )

    def snapshot_hash(self) -> str:
        """Deterministic hash for versioning."""
        raw = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode()).hexdigest()


# Supported rule types mapping to SpendingPolicy fields
RULE_TYPES = {
    "limit_per_tx",
    "limit_total",
    "scope",
    "mcc_block",
    "merchant_allow",
    "merchant_block",
    "time_window",
    "approval_threshold",
    "trust_level",
    "goal_drift_max",
    "kya_required",
    "chain_allowlist",
    "token_allowlist",
    "destination_allowlist",
    "destination_blocklist",
}


def validate_definition(definition: PolicyDefinition) -> list[str]:
    """Validate DSL rules without compiling. Returns list of errors (empty = valid)."""
    errors: list[str] = []

    if not definition.rules:
        errors.append("Policy must have at least one rule")
        return errors

    for i, rule in enumerate(definition.rules):
        prefix = f"Rule {i} ({rule.type})"

        if rule.type not in RULE_TYPES:
            errors.append(f"{prefix}: unknown rule type '{rule.type}'")
            continue

        if rule.type == "limit_per_tx":
            if "amount" not in rule.params:
                errors.append(f"{prefix}: missing 'amount' param")
            elif not _is_positive_number(rule.params["amount"]):
                errors.append(f"{prefix}: 'amount' must be a positive number")

        elif rule.type == "limit_total":
            if "amount" not in rule.params:
                errors.append(f"{prefix}: missing 'amount' param")
            elif not _is_positive_number(rule.params["amount"]):
                errors.append(f"{prefix}: 'amount' must be a positive number")

        elif rule.type == "scope":
            scopes = rule.params.get("allowed", [])
            if not scopes:
                errors.append(f"{prefix}: missing 'allowed' param (list of scopes)")
            else:
                valid_scopes = {s.value for s in SpendingScope}
                for s in scopes:
                    if s not in valid_scopes:
                        errors.append(f"{prefix}: unknown scope '{s}'")

        elif rule.type == "mcc_block":
            categories = rule.params.get("categories", [])
            if not categories:
                errors.append(f"{prefix}: missing 'categories' param")

        elif rule.type in ("merchant_allow", "merchant_block"):
            if not rule.params.get("merchant_id") and not rule.params.get("category"):
                errors.append(f"{prefix}: must specify 'merchant_id' or 'category'")

        elif rule.type == "time_window":
            window = rule.params.get("window")
            if window not in ("daily", "weekly", "monthly"):
                errors.append(f"{prefix}: 'window' must be daily/weekly/monthly")
            if "amount" not in rule.params:
                errors.append(f"{prefix}: missing 'amount' param")

        elif rule.type == "approval_threshold":
            if "amount" not in rule.params:
                errors.append(f"{prefix}: missing 'amount' param")

        elif rule.type == "trust_level":
            level = rule.params.get("level")
            valid_levels = {t.value for t in TrustLevel}
            if level not in valid_levels:
                errors.append(f"{prefix}: 'level' must be one of {valid_levels}")

        elif rule.type == "goal_drift_max":
            threshold = rule.params.get("threshold")
            if threshold is None:
                errors.append(f"{prefix}: missing 'threshold' param")
            elif not (0 <= float(threshold) <= 1):
                errors.append(f"{prefix}: 'threshold' must be between 0 and 1")

    return errors


def compile_policy(definition: PolicyDefinition, agent_id: str) -> SpendingPolicy:
    """Compile DSL definition into executable SpendingPolicy.

    Args:
        definition: Validated PolicyDefinition
        agent_id: Agent ID to attach policy to

    Returns:
        Configured SpendingPolicy

    Raises:
        ValueError: If definition has validation errors
    """
    errors = validate_definition(definition)
    if errors:
        raise ValueError(f"Invalid policy definition: {'; '.join(errors)}")

    policy = SpendingPolicy(agent_id=agent_id)

    for rule in definition.rules:
        _apply_rule(policy, rule)

    return policy


def decompile_policy(policy: SpendingPolicy) -> PolicyDefinition:
    """Reverse: extract DSL from an existing SpendingPolicy."""
    rules: list[PolicyRule] = []

    # Trust level FIRST — so subsequent limit rules can override its defaults
    rules.append(PolicyRule(type="trust_level", params={"level": policy.trust_level.value}))

    # Limit per tx
    rules.append(PolicyRule(type="limit_per_tx", params={"amount": str(policy.limit_per_tx)}))

    # Limit total
    rules.append(PolicyRule(type="limit_total", params={"amount": str(policy.limit_total)}))

    # Scopes
    if policy.allowed_scopes and SpendingScope.ALL not in policy.allowed_scopes:
        rules.append(PolicyRule(type="scope", params={"allowed": [s.value for s in policy.allowed_scopes]}))

    # Blocked MCC categories
    if policy.blocked_merchant_categories:
        rules.append(PolicyRule(type="mcc_block", params={"categories": list(policy.blocked_merchant_categories)}))

    # Merchant rules
    for mr in policy.merchant_rules:
        if mr.rule_type == "allow":
            params: dict[str, Any] = {}
            if mr.merchant_id:
                params["merchant_id"] = mr.merchant_id
            if mr.category:
                params["category"] = mr.category
            if mr.max_per_tx is not None:
                params["max_per_tx"] = str(mr.max_per_tx)
            rules.append(PolicyRule(type="merchant_allow", params=params))
        elif mr.rule_type == "deny":
            params = {}
            if mr.merchant_id:
                params["merchant_id"] = mr.merchant_id
            if mr.category:
                params["category"] = mr.category
            rules.append(PolicyRule(type="merchant_block", params=params))

    # Time windows
    for window in [policy.daily_limit, policy.weekly_limit, policy.monthly_limit]:
        if window is not None:
            rules.append(PolicyRule(
                type="time_window",
                params={"window": window.window_type, "amount": str(window.limit_amount)},
            ))

    # Approval threshold
    if policy.approval_threshold is not None:
        rules.append(PolicyRule(type="approval_threshold", params={"amount": str(policy.approval_threshold)}))

    # Goal drift
    if policy.max_drift_score is not None:
        rules.append(PolicyRule(type="goal_drift_max", params={"threshold": str(policy.max_drift_score)}))

    # Chain/token allowlists
    if policy.allowed_chains:
        rules.append(PolicyRule(type="chain_allowlist", params={"chains": list(policy.allowed_chains)}))
    if policy.allowed_tokens:
        rules.append(PolicyRule(type="token_allowlist", params={"tokens": list(policy.allowed_tokens)}))
    if policy.allowed_destination_addresses:
        rules.append(PolicyRule(type="destination_allowlist", params={"addresses": list(policy.allowed_destination_addresses)}))
    if policy.blocked_destination_addresses:
        rules.append(PolicyRule(type="destination_blocklist", params={"addresses": list(policy.blocked_destination_addresses)}))

    return PolicyDefinition(
        rules=rules,
        metadata={"agent_id": policy.agent_id, "decompiled": True},
    )


def _apply_rule(policy: SpendingPolicy, rule: PolicyRule) -> None:
    """Apply a single DSL rule to a SpendingPolicy."""
    if rule.type == "limit_per_tx":
        policy.limit_per_tx = Decimal(str(rule.params["amount"]))

    elif rule.type == "limit_total":
        policy.limit_total = Decimal(str(rule.params["amount"]))

    elif rule.type == "scope":
        policy.allowed_scopes = [SpendingScope(s) for s in rule.params["allowed"]]

    elif rule.type == "mcc_block":
        for cat in rule.params["categories"]:
            policy.block_merchant_category(cat)

    elif rule.type == "merchant_allow":
        policy.add_merchant_allow(
            merchant_id=rule.params.get("merchant_id"),
            category=rule.params.get("category"),
            max_per_tx=Decimal(str(rule.params["max_per_tx"])) if "max_per_tx" in rule.params else None,
        )

    elif rule.type == "merchant_block":
        policy.add_merchant_deny(
            merchant_id=rule.params.get("merchant_id"),
            category=rule.params.get("category"),
        )

    elif rule.type == "time_window":
        window = TimeWindowLimit(
            window_type=rule.params["window"],
            limit_amount=Decimal(str(rule.params["amount"])),
        )
        if rule.params["window"] == "daily":
            policy.daily_limit = window
        elif rule.params["window"] == "weekly":
            policy.weekly_limit = window
        elif rule.params["window"] == "monthly":
            policy.monthly_limit = window

    elif rule.type == "approval_threshold":
        policy.approval_threshold = Decimal(str(rule.params["amount"]))

    elif rule.type == "trust_level":
        level = TrustLevel(rule.params["level"])
        policy.trust_level = level
        tier = DEFAULT_LIMITS[level]
        policy.limit_per_tx = tier["per_tx"]
        policy.limit_total = tier["total"]
        if tier["daily"]:
            policy.daily_limit = TimeWindowLimit(window_type="daily", limit_amount=tier["daily"])
        if tier["weekly"]:
            policy.weekly_limit = TimeWindowLimit(window_type="weekly", limit_amount=tier["weekly"])
        if tier["monthly"]:
            policy.monthly_limit = TimeWindowLimit(window_type="monthly", limit_amount=tier["monthly"])

    elif rule.type == "goal_drift_max":
        policy.max_drift_score = Decimal(str(rule.params["threshold"]))

    elif rule.type == "kya_required":
        # Sets trust level to MEDIUM minimum (KYA attestation checked at MEDIUM+)
        if policy.trust_level == TrustLevel.LOW:
            policy.trust_level = TrustLevel.MEDIUM

    elif rule.type == "chain_allowlist":
        policy.allowed_chains = list(rule.params.get("chains", []))

    elif rule.type == "token_allowlist":
        policy.allowed_tokens = list(rule.params.get("tokens", []))

    elif rule.type == "destination_allowlist":
        policy.allowed_destination_addresses = list(rule.params.get("addresses", []))

    elif rule.type == "destination_blocklist":
        policy.blocked_destination_addresses = list(rule.params.get("addresses", []))


def _is_positive_number(value: Any) -> bool:
    """Check if value can be interpreted as a positive number."""
    try:
        return Decimal(str(value)) > 0
    except Exception:
        return False
