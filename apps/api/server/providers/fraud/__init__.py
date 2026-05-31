"""External fraud-signal feeds for the in-house Guard / RiskEngine.

These adapters implement :class:`server.providers.ports.FraudSignalPort`.  They
buy *cross-customer* signals Sardis cannot self-generate — Stripe Radar's
network fraud model, SEON's device / email / IP intelligence — and normalize
them into a :class:`RiskSignalResult`.  They NEVER decide allow/deny: the
in-house ``RiskEngine`` owns the binding decision (the moat).

Env-gated: each adapter activates only when its API key is set.  With no keys
the registry falls back to the SIMULATED sandbox feed so dev + tests run green.
"""

from __future__ import annotations

from .adapter import (
    SeonFraudSignalAdapter,
    StripeRadarFraudSignalAdapter,
)
from .client import (
    SeonClient,
    SeonConfig,
    StripeRadarClient,
    StripeRadarConfig,
)

__all__ = [
    "StripeRadarFraudSignalAdapter",
    "SeonFraudSignalAdapter",
    "StripeRadarClient",
    "StripeRadarConfig",
    "SeonClient",
    "SeonConfig",
]
