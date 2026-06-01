"""Unified provider port taxonomy for the Sardis execution path.

Public surface:

* Capability ports (Protocols): :class:`CustodyPort`, :class:`FiatAccountPort`,
  :class:`OnrampPort`, :class:`OfframpPort`, :class:`SwapPort`,
  :class:`BridgePort`, :class:`CardPort`, :class:`KycPort`, :class:`KytPort`.
* Shared types: :class:`CustodyModel`, :class:`ProviderCapability`,
  :class:`ProviderResult`, :class:`NormalizedTxn`, :class:`ProviderError`,
  :class:`ProviderNotConfigured`, :data:`MinorUnits`,
  :func:`to_minor_units`, :func:`from_minor_units`.

The :class:`server.providers.registry.ProviderRegistry` owns construction and
returns the configured implementation per capability (or a sandbox impl when
keys are absent / fails closed in production).
"""

from __future__ import annotations

from .capabilities import (
    BridgePort,
    CapabilityPort,
    CardPort,
    CustodyPort,
    FiatAccountPort,
    FraudSignalPort,
    KycPort,
    KytPort,
    NotificationPort,
    OfframpPort,
    OnrampPort,
    SwapPort,
)
from .types import (
    CustodyModel,
    DeliveryResult,
    MinorUnits,
    NormalizedTxn,
    ProviderCapability,
    ProviderError,
    ProviderNotConfigured,
    ProviderResult,
    RecommendedAction,
    RelayedDecision,
    RiskSignalResult,
    from_minor_units,
    to_minor_units,
)

__all__ = [
    # capability ports
    "CapabilityPort",
    "CustodyPort",
    "FiatAccountPort",
    "OnrampPort",
    "OfframpPort",
    "SwapPort",
    "BridgePort",
    "CardPort",
    "KycPort",
    "KytPort",
    "NotificationPort",
    "FraudSignalPort",
    # types
    "CustodyModel",
    "ProviderCapability",
    "ProviderResult",
    "NormalizedTxn",
    "DeliveryResult",
    "RelayedDecision",
    "RiskSignalResult",
    "RecommendedAction",
    "ProviderError",
    "ProviderNotConfigured",
    "MinorUnits",
    "to_minor_units",
    "from_minor_units",
]
