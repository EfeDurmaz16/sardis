"""Characterization test: validate_payment() must agree with evaluate().

Task 6 (Phase 0 — Engine Consolidation) collapses ``validate_payment`` onto the
single ``evaluate`` policy core so there is exactly one source of truth for
policy decisions.

Both methods return ``tuple[bool, str]``: (allowed, reason_code). This test
LOCKS the contract that — for the same inputs and with none of evaluate()'s
optional injectables supplied (rpc_client / policy_store / kya_client /
merchant_trust_service / trust_score_override) — the two methods produce the
SAME decision. validate_payment is the sync subset of evaluate where those
injectables are absent, so the decision-relevant (allowed, reason) tuple must
match exactly.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from sardis.core.spending_policy import (
    MerchantRule,
    SpendingPolicy,
    SpendingScope,
    TimeWindowLimit,
    TrustLevel,
)


def _policy(**overrides) -> SpendingPolicy:
    defaults = {
        "agent_id": "agent_char",
        "trust_level": TrustLevel.MEDIUM,
        "limit_per_tx": Decimal("500"),
        "limit_total": Decimal("5000"),
    }
    defaults.update(overrides)
    return SpendingPolicy(**defaults)


# Each case: (label, policy_factory, validate_kwargs)
# validate_kwargs are the args common to BOTH validate_payment and evaluate.
_CASES = [
    # within-limit allow
    (
        "within_limit_allow",
        lambda: _policy(limit_per_tx=Decimal("500")),
        {"amount": Decimal("100"), "fee": Decimal("0")},
    ),
    # at-limit allow (boundary)
    (
        "at_limit_allow",
        lambda: _policy(limit_per_tx=Decimal("100")),
        {"amount": Decimal("100"), "fee": Decimal("0")},
    ),
    # over per-tx limit deny
    (
        "over_per_tx_deny",
        lambda: _policy(limit_per_tx=Decimal("100")),
        {"amount": Decimal("101"), "fee": Decimal("0")},
    ),
    # fee pushes over per-tx limit
    (
        "fee_over_per_tx_deny",
        lambda: _policy(limit_per_tx=Decimal("100")),
        {"amount": Decimal("90"), "fee": Decimal("15")},
    ),
    # non-positive amount deny
    (
        "zero_amount_deny",
        lambda: _policy(),
        {"amount": Decimal("0"), "fee": Decimal("0")},
    ),
    # negative fee deny
    (
        "negative_fee_deny",
        lambda: _policy(),
        {"amount": Decimal("10"), "fee": Decimal("-1")},
    ),
    # over total limit deny
    (
        "over_total_deny",
        lambda: _policy(limit_per_tx=Decimal("5000"), limit_total=Decimal("1000"), spent_total=Decimal("950")),
        {"amount": Decimal("100"), "fee": Decimal("0")},
    ),
    # daily window limit deny
    (
        "daily_window_deny",
        lambda: _policy(
            limit_per_tx=Decimal("5000"),
            daily_limit=TimeWindowLimit(window_type="daily", limit_amount=Decimal("100")),
        ),
        {"amount": Decimal("150"), "fee": Decimal("0")},
    ),
    # approval-threshold: amount above threshold -> requires_approval
    (
        "approval_threshold",
        lambda: _policy(approval_threshold=Decimal("200")),
        {"amount": Decimal("300"), "fee": Decimal("0")},
    ),
    # approval-threshold boundary: at threshold -> allowed (not strictly above)
    (
        "approval_threshold_at",
        lambda: _policy(approval_threshold=Decimal("200")),
        {"amount": Decimal("200"), "fee": Decimal("0")},
    ),
    # scope not allowed deny
    (
        "scope_not_allowed_deny",
        lambda: _policy(allowed_scopes=[SpendingScope.COMPUTE]),
        {"amount": Decimal("50"), "fee": Decimal("0"), "scope": SpendingScope.RETAIL},
    ),
    # scope allowed
    (
        "scope_allowed",
        lambda: _policy(allowed_scopes=[SpendingScope.COMPUTE]),
        {"amount": Decimal("50"), "fee": Decimal("0"), "scope": SpendingScope.COMPUTE},
    ),
    # merchant allowlist: matching merchant allowed
    (
        "merchant_allow_match",
        lambda: _policy(merchant_rules=[MerchantRule(rule_type="allow", merchant_id="m_good")]),
        {"amount": Decimal("50"), "fee": Decimal("0"), "merchant_id": "m_good"},
    ),
    # merchant allowlist: non-matching merchant denied
    (
        "merchant_allow_nomatch_deny",
        lambda: _policy(merchant_rules=[MerchantRule(rule_type="allow", merchant_id="m_good")]),
        {"amount": Decimal("50"), "fee": Decimal("0"), "merchant_id": "m_other"},
    ),
    # merchant blocklist: blocked merchant denied
    (
        "merchant_deny_match",
        lambda: _policy(merchant_rules=[MerchantRule(rule_type="deny", merchant_id="m_bad")]),
        {"amount": Decimal("50"), "fee": Decimal("0"), "merchant_id": "m_bad"},
    ),
    # goal drift exceeded deny
    (
        "goal_drift_deny",
        lambda: _policy(max_drift_score=Decimal("0.5")),
        {"amount": Decimal("50"), "fee": Decimal("0"), "drift_score": Decimal("0.9")},
    ),
    # goal drift within bounds
    (
        "goal_drift_ok",
        lambda: _policy(max_drift_score=Decimal("0.5")),
        {"amount": Decimal("50"), "fee": Decimal("0"), "drift_score": Decimal("0.1")},
    ),
]


@pytest.mark.parametrize("label,factory,kwargs", _CASES, ids=[c[0] for c in _CASES])
@pytest.mark.asyncio
async def test_validate_payment_matches_evaluate(label, factory, kwargs):
    """validate_payment and evaluate must return the same (allowed, reason)."""
    policy_sync = factory()
    policy_async = factory()

    sync_allowed, sync_reason = policy_sync.validate_payment(**kwargs)

    # evaluate() takes the same decision-relevant kwargs plus injectables we
    # leave at their no-op defaults (wallet/token unused without rpc/kya).
    async_allowed, async_reason = await policy_async.evaluate(
        None,  # wallet — unused (no rpc_client / no MEDIUM+HIGH kya_client)
        kwargs["amount"],
        kwargs["fee"],
        chain="base",
        token=None,
        merchant_id=kwargs.get("merchant_id"),
        merchant_category=kwargs.get("merchant_category"),
        mcc_code=kwargs.get("mcc_code"),
        scope=kwargs.get("scope", SpendingScope.ALL),
        drift_score=kwargs.get("drift_score"),
    )

    assert (sync_allowed, sync_reason) == (async_allowed, async_reason), (
        f"[{label}] divergence: validate_payment={(sync_allowed, sync_reason)} "
        f"evaluate={(async_allowed, async_reason)}"
    )
