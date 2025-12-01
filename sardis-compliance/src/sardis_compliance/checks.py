"""Compliance pre-flight engine."""
from __future__ import annotations

from dataclasses import dataclass

from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import PaymentMandate


@dataclass
class ComplianceResult:
    allowed: bool
    reason: str | None = None


class ComplianceEngine:
    def __init__(self, settings: SardisSettings):
        self._settings = settings

    def preflight(self, mandate: PaymentMandate) -> ComplianceResult:
        # TODO: integrate with Persona, Elliptic, etc.
        if mandate.token not in {"USDC", "USDT", "PYUSD", "EURC"}:
            return ComplianceResult(False, "token_not_permitted")
        return ComplianceResult(True)
