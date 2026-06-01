#!/usr/bin/env python3
"""Generate golden policy-decision vectors from the Python SpendingPolicy.

GITIGNORED tooling (run once; output committed under __tests__/vectors/).
Drives `SpendingPolicy.validate_payment` / `validate_execution_context` over a
fixed matrix and dumps {policy, spend, expected} in the TS-facing shape so the
@sardis/reference simulator can be asserted decision-for-decision identical.

Money: Python uses Decimal token-major; the TS mirror uses minor units at 2
decimals. This script multiplies token-major by 100 to produce minor units.

MCC checks (Checks 3/4 high-risk) are NOT generated here: the authoritative MCC
data file ships only in the private backend, so the Python MCC path is not
exercisable in the public tree. The TS MCC mirror is tested independently with a
documented static table.

Usage:
    python3 scripts/gen_policy_vectors.py > __tests__/vectors/policy-decisions.json
"""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

# Import the public Python SDK from this monorepo.
_SARDIS_SRC = Path(__file__).resolve().parents[2] / "sardis" / "src"
sys.path.insert(0, str(_SARDIS_SRC))

from sardis.core.spending_policy import (  # noqa: E402
    MerchantRule,
    SpendingPolicy,
    SpendingScope,
    TimeWindowLimit,
)

CURRENCY = "USDC"


def minor(amount: Decimal | str | int) -> int:
    return int((Decimal(str(amount)) * 100).to_integral_value())


def money(amount) -> dict:
    return {"minor": str(minor(amount)), "currency": CURRENCY}


def win(window_type: str, limit: str, spent: str, start_ms: int) -> dict:
    return {
        "windowType": window_type,
        "limit": money(limit),
        "currentSpent": money(spent),
        "windowStartMs": start_ms,
    }


def base_policy_dict(**overrides) -> dict:
    d = {
        "policyId": "policy_test",
        "agentId": "agent_test",
        "trustLevel": "low",
        "limitPerTx": money("100"),
        "limitTotal": money("1000"),
        "spentTotal": money("0"),
        "merchantRules": [],
        "allowedScopes": ["all"],
        "blockedMerchantCategories": [],
        "allowedChains": [],
        "allowedTokens": [],
        "allowedDestinations": [],
        "blockedDestinations": [],
        "maxDriftScore": 0.5,
    }
    d.update(overrides)
    return d


def to_outcome(approved: bool, reason: str) -> str:
    if not approved:
        return "deny"
    if reason == "requires_approval":
        return "requires_approval"
    return "allow"


VECTORS: list[dict] = []


def add(name: str, policy: SpendingPolicy, policy_dict: dict, spend: dict, *, amount, fee="0", now=0, **kw):
    approved, reason = policy.validate_payment(
        Decimal(str(amount)),
        Decimal(str(fee)),
        merchant_id=kw.get("merchant_id"),
        merchant_category=kw.get("merchant_category"),
        scope=kw.get("scope", SpendingScope.ALL),
        drift_score=Decimal(str(kw["drift_score"])) if "drift_score" in kw else None,
    )
    VECTORS.append(
        {
            "name": name,
            "policy": policy_dict,
            "spend": spend,
            "now": now,
            "expected": {"outcome": to_outcome(approved, reason), "reason": reason},
        }
    )


def main() -> None:
    # 1. allow
    p = SpendingPolicy(agent_id="a", limit_per_tx=Decimal("100"), limit_total=Decimal("1000"))
    pd = base_policy_dict()
    add("allow_basic", p, pd, {"amount": money("50")}, amount="50")

    # 2. amount_must_be_positive (use 0 → not >0)
    add("amount_zero", p, pd, {"amount": money("0")}, amount="0")

    # 3. fee_must_be_non_negative
    add("fee_negative", p, pd, {"amount": money("10"), "fee": money("-1")}, amount="10", fee="-1")

    # 4. scope_not_allowed
    p_scope = SpendingPolicy(agent_id="a", limit_per_tx=Decimal("100"), limit_total=Decimal("1000"), allowed_scopes=[SpendingScope.COMPUTE])
    pd_scope = base_policy_dict(allowedScopes=["compute"])
    add("scope_not_allowed", p_scope, pd_scope, {"amount": money("10"), "scope": "retail"}, amount="10", scope=SpendingScope.RETAIL)
    add("scope_allowed", p_scope, pd_scope, {"amount": money("10"), "scope": "compute"}, amount="10", scope=SpendingScope.COMPUTE)

    # 5. per_transaction_limit
    add("per_tx_limit", p, pd, {"amount": money("200")}, amount="200")

    # 6. per_transaction with fee pushing over
    add("per_tx_with_fee", p, pd, {"amount": money("100"), "fee": money("1")}, amount="100", fee="1")

    # 7. total_limit_exceeded (spent_total seeded)
    p_total = SpendingPolicy(agent_id="a", limit_per_tx=Decimal("100"), limit_total=Decimal("1000"), spent_total=Decimal("980"))
    pd_total = base_policy_dict(spentTotal=money("980"))
    add("total_limit_exceeded", p_total, pd_total, {"amount": money("50")}, amount="50")

    # 8. daily_limit_exceeded (window seeded, not expired @ now)
    now_ms = 1_000_000
    p_daily = SpendingPolicy(agent_id="a", limit_per_tx=Decimal("100"), limit_total=Decimal("1000"))
    # window in Python uses datetime; validate_payment uses can_spend which resets if expired.
    # Seed a fresh (non-expired) window via current_spent close to the limit.
    from datetime import UTC, datetime
    p_daily.daily_limit = TimeWindowLimit(window_type="daily", limit_amount=Decimal("100"), current_spent=Decimal("90"), window_start=datetime.now(UTC))
    pd_daily = base_policy_dict(daily=win("daily", "100", "90", now_ms))
    add("daily_limit_exceeded", p_daily, pd_daily, {"amount": money("20")}, amount="20", now=now_ms)

    # 9. merchant_denied
    p_deny = SpendingPolicy(agent_id="a", limit_per_tx=Decimal("100"), limit_total=Decimal("1000"))
    p_deny.merchant_rules = [MerchantRule(rule_id="r1", rule_type="deny", merchant_id="evil.com")]
    pd_deny = base_policy_dict(merchantRules=[{"ruleId": "r1", "ruleType": "deny", "merchantId": "evil.com"}])
    add("merchant_denied", p_deny, pd_deny, {"amount": money("10"), "merchantId": "evil.com"}, amount="10", merchant_id="evil.com")

    # 10. merchant_not_allowlisted
    p_allow = SpendingPolicy(agent_id="a", limit_per_tx=Decimal("100"), limit_total=Decimal("1000"))
    p_allow.merchant_rules = [MerchantRule(rule_id="r2", rule_type="allow", merchant_id="good.com")]
    pd_allow = base_policy_dict(merchantRules=[{"ruleId": "r2", "ruleType": "allow", "merchantId": "good.com"}])
    add("merchant_not_allowlisted", p_allow, pd_allow, {"amount": money("10"), "merchantId": "other.com"}, amount="10", merchant_id="other.com")
    add("merchant_allowlisted", p_allow, pd_allow, {"amount": money("10"), "merchantId": "good.com"}, amount="10", merchant_id="good.com")

    # 11. merchant_cap_exceeded
    p_cap = SpendingPolicy(agent_id="a", limit_per_tx=Decimal("100"), limit_total=Decimal("1000"))
    p_cap.merchant_rules = [MerchantRule(rule_id="r3", rule_type="allow", merchant_id="good.com", max_per_tx=Decimal("20"))]
    pd_cap = base_policy_dict(merchantRules=[{"ruleId": "r3", "ruleType": "allow", "merchantId": "good.com", "maxPerTx": money("20")}])
    add("merchant_cap_exceeded", p_cap, pd_cap, {"amount": money("50"), "merchantId": "good.com"}, amount="50", merchant_id="good.com")

    # 12. category per-tx override (groceries -> grocery match, max 200)
    p_ovr = SpendingPolicy(agent_id="a", limit_per_tx=Decimal("100"), limit_total=Decimal("5000"))
    p_ovr.merchant_rules = [MerchantRule(rule_id="r4", rule_type="allow", category="grocery", max_per_tx=Decimal("200"))]
    pd_ovr = base_policy_dict(limitTotal=money("5000"), merchantRules=[{"ruleId": "r4", "ruleType": "allow", "category": "grocery", "maxPerTx": money("200")}])
    # amount 150 > base 100 but <= override 200; merchant matches allow rule by category
    add("category_per_tx_override_allow", p_ovr, pd_ovr, {"amount": money("150"), "merchantId": "store", "merchantCategory": "groceries"}, amount="150", merchant_id="store", merchant_category="groceries")

    # 13. goal_drift_exceeded
    add("goal_drift_exceeded", p, pd, {"amount": money("10"), "driftScore": 0.9}, amount="10", drift_score=0.9)
    add("goal_drift_ok", p, pd, {"amount": money("10"), "driftScore": 0.3}, amount="10", drift_score=0.3)

    # 14. requires_approval
    p_appr = SpendingPolicy(agent_id="a", limit_per_tx=Decimal("100"), limit_total=Decimal("1000"), approval_threshold=Decimal("80"))
    pd_appr = base_policy_dict(approvalThreshold=money("80"))
    add("requires_approval", p_appr, pd_appr, {"amount": money("90")}, amount="90")
    add("under_approval_threshold", p_appr, pd_appr, {"amount": money("50")}, amount="50")

    json.dump(VECTORS, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
