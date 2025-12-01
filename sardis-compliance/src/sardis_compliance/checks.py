"""Compliance pre-flight engine."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import PaymentMandate


@dataclass
class ComplianceResult:
    allowed: bool
    reason: str | None = None
    provider: str | None = None
    rule_id: str | None = None
    reviewed_at: datetime = datetime.now(timezone.utc)


class ComplianceProvider(Protocol):
    def evaluate(self, mandate: PaymentMandate) -> ComplianceResult: ...


class SimpleRuleProvider:
    """Placeholder rule engine before wiring external vendors."""

    def __init__(self, settings: SardisSettings):
        self._settings = settings

    def evaluate(self, mandate: PaymentMandate) -> ComplianceResult:
        if mandate.token not in {"USDC", "USDT", "PYUSD", "EURC"}:
            return ComplianceResult(allowed=False, reason="token_not_permitted", provider="rules", rule_id="token_allowlist")
        if mandate.amount_minor > 1_000_000_00:
            return ComplianceResult(allowed=False, reason="amount_over_limit", provider="rules", rule_id="max_amount")
        return ComplianceResult(allowed=True, provider="rules", rule_id="baseline")


class ComplianceEngine:
    def __init__(self, settings: SardisSettings, provider: ComplianceProvider | None = None):
        self._provider = provider or SimpleRuleProvider(settings)

    def preflight(self, mandate: PaymentMandate) -> ComplianceResult:
        return self._provider.evaluate(mandate)
