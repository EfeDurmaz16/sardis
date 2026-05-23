"""PolicyExplainer — structured denial output for policy checks.

When a spending policy denies a payment, the explainer produces a
machine-readable and human-readable explanation of what passed, what
failed, and what the caller should do to fix it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

# Map reason codes from SpendingPolicy.evaluate() to human-readable messages
_REASON_DESCRIPTIONS: dict[str, str] = {
    "amount_must_be_positive": "Amount must be greater than zero",
    "fee_must_be_non_negative": "Fee cannot be negative",
    "scope_not_allowed": "Spending category is not permitted by this policy",
    "mcc_blocked": "Merchant category code is blocked",
    "per_transaction_limit": "Amount exceeds per-transaction limit",
    "total_limit_exceeded": "Cumulative spending has reached the lifetime cap",
    "daily_limit_exceeded": "Daily spending limit reached",
    "weekly_limit_exceeded": "Weekly spending limit reached",
    "monthly_limit_exceeded": "Monthly spending limit reached",
    "time_window_limit": "Time-window spending limit reached",
    "insufficient_balance": "Wallet does not have sufficient on-chain balance",
    "merchant_denied": "Merchant is on the blocklist",
    "merchant_not_in_allowlist": "Merchant is not in the allowlist",
    "merchant_per_tx_exceeded": "Amount exceeds per-merchant transaction limit",
    "merchant_daily_limit_exceeded": "Per-merchant daily limit reached",
    "goal_drift_exceeded": "Agent has drifted too far from its stated goal",
    "requires_approval": "Payment requires human approval (above threshold)",
    "requires_approval_first_seen_merchant": "First-seen merchant requires approval",
    "kya_attestation_required": "On-chain KYA attestation is missing or expired",
    "kya_attestation_revoked": "Agent KYA attestation has been revoked",
    "chain_not_allowlisted": "Target chain is not permitted",
    "token_not_allowlisted": "Token is not permitted",
    "destination_blocked": "Destination address is blocked",
    "destination_not_allowlisted": "Destination address is not in allowlist",
    "velocity_exceeded": "Too many transactions in a short period",
}

# Suggested actions for each reason code
_SUGGESTED_ACTIONS: dict[str, str] = {
    "amount_must_be_positive": "Use a positive amount",
    "fee_must_be_non_negative": "Check fee calculation",
    "scope_not_allowed": "Change the spending scope or update the policy",
    "mcc_blocked": "Use a different merchant or update blocked categories",
    "per_transaction_limit": "Reduce the amount or increase the per-tx limit",
    "total_limit_exceeded": "Request a higher lifetime budget",
    "daily_limit_exceeded": "Wait until the daily window resets or increase the limit",
    "weekly_limit_exceeded": "Wait until the weekly window resets or increase the limit",
    "monthly_limit_exceeded": "Wait until the monthly window resets or increase the limit",
    "time_window_limit": "Wait for the time window to reset",
    "insufficient_balance": "Fund the wallet with more tokens",
    "merchant_denied": "Remove the merchant from the blocklist",
    "merchant_not_in_allowlist": "Add the merchant to the allowlist",
    "merchant_per_tx_exceeded": "Reduce amount or update merchant limit",
    "merchant_daily_limit_exceeded": "Wait or update merchant daily limit",
    "goal_drift_exceeded": "Realign the agent to its goal or lower max_drift_score",
    "requires_approval": "Submit for human approval",
    "requires_approval_first_seen_merchant": "Submit for human approval or build merchant trust",
    "kya_attestation_required": "Complete KYA attestation",
    "kya_attestation_revoked": "Re-verify agent identity",
    "chain_not_allowlisted": "Use an allowed chain or update policy",
    "token_not_allowlisted": "Use an allowed token or update policy",
    "destination_blocked": "Use a different destination address",
    "destination_not_allowlisted": "Add destination to the allowlist",
    "velocity_exceeded": "Wait before submitting another transaction",
}

# The 12 checks in order, as named in SpendingPolicy.evaluate()
POLICY_CHECKS = [
    "amount_validation",
    "scope_check",
    "mcc_check",
    "per_tx_limit",
    "cumulative_limit",
    "time_window_limits",
    "on_chain_balance",
    "merchant_rules",
    "goal_drift",
    "merchant_trust",
    "approval_threshold",
    "kya_attestation",
]


@dataclass
class PolicyExplanation:
    """Structured explanation of a policy evaluation result."""

    allowed: bool
    summary: str
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    suggested_action: str | None = None
    reason_code: str | None = None

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "summary": self.summary,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "suggested_action": self.suggested_action,
            "reason_code": self.reason_code,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_text(self) -> str:
        status = "ALLOWED" if self.allowed else "DENIED"
        lines = [f"Policy Decision: {status}", f"Summary: {self.summary}"]
        if self.checks_passed:
            lines.append(f"Checks passed: {', '.join(self.checks_passed)}")
        if self.checks_failed:
            lines.append(f"Checks failed: {', '.join(self.checks_failed)}")
        if self.suggested_action:
            lines.append(f"Suggested action: {self.suggested_action}")
        return "\n".join(lines)


def explain_denial(reason_code: str) -> PolicyExplanation:
    """Build a structured explanation for a policy denial.

    Args:
        reason_code: The reason code from SpendingPolicy.evaluate()

    Returns:
        PolicyExplanation with human-readable summary and suggested action
    """
    # Figure out which check failed based on the reason code
    failed_check = _reason_to_check(reason_code)
    check_index = POLICY_CHECKS.index(failed_check) if failed_check in POLICY_CHECKS else 0
    passed = POLICY_CHECKS[:check_index]

    description = _REASON_DESCRIPTIONS.get(reason_code, f"Policy denied: {reason_code}")
    action = _SUGGESTED_ACTIONS.get(reason_code, "Review the policy configuration")

    return PolicyExplanation(
        allowed=False,
        summary=description,
        checks_passed=passed,
        checks_failed=[failed_check] if failed_check else [reason_code],
        suggested_action=action,
        reason_code=reason_code,
    )


def explain_approval(reason_code: str = "OK") -> PolicyExplanation:
    """Build a structured explanation for a policy approval."""
    if reason_code == "requires_approval":
        return PolicyExplanation(
            allowed=True,
            summary="Payment approved but requires human sign-off",
            checks_passed=POLICY_CHECKS[:10],
            checks_failed=[],
            suggested_action="Submit for human approval",
            reason_code=reason_code,
        )
    return PolicyExplanation(
        allowed=True,
        summary="All policy checks passed",
        checks_passed=list(POLICY_CHECKS),
        checks_failed=[],
        reason_code=reason_code,
    )


def _reason_to_check(reason_code: str) -> str:
    """Map a reason code to the policy check name."""
    mapping = {
        "amount_must_be_positive": "amount_validation",
        "fee_must_be_non_negative": "amount_validation",
        "scope_not_allowed": "scope_check",
        "mcc_blocked": "mcc_check",
        "per_transaction_limit": "per_tx_limit",
        "total_limit_exceeded": "cumulative_limit",
        "daily_limit_exceeded": "time_window_limits",
        "weekly_limit_exceeded": "time_window_limits",
        "monthly_limit_exceeded": "time_window_limits",
        "time_window_limit": "time_window_limits",
        "velocity_exceeded": "time_window_limits",
        "insufficient_balance": "on_chain_balance",
        "merchant_denied": "merchant_rules",
        "merchant_not_in_allowlist": "merchant_rules",
        "merchant_per_tx_exceeded": "merchant_rules",
        "merchant_daily_limit_exceeded": "merchant_rules",
        "goal_drift_exceeded": "goal_drift",
        "requires_approval": "approval_threshold",
        "requires_approval_first_seen_merchant": "merchant_trust",
        "kya_attestation_required": "kya_attestation",
        "kya_attestation_revoked": "kya_attestation",
    }
    return mapping.get(reason_code, reason_code)
