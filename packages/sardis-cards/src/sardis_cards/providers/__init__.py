"""Card provider implementations."""

from .base import CardProvider
from .issuer_adapter import REQUIRED_ISSUER_METHODS, IssuerAdapterShim, build_issuer_adapter
from .issuer_readiness import IssuerReadiness, evaluate_issuer_readiness
from .issuing_ports import IssuerAdapter
from .mock import MockProvider
from .org_router import OrganizationCardProviderRouter
from .partner_issuers import BridgeCardsProvider, RainCardsProvider
from .router import CardProviderRouter

__all__ = [
    "BridgeCardsProvider",
    "CardProvider",
    "IssuerReadiness",
    "IssuerAdapter",
    "IssuerAdapterShim",
    "REQUIRED_ISSUER_METHODS",
    "MockProvider",
    "CardProviderRouter",
    "OrganizationCardProviderRouter",
    "build_issuer_adapter",
    "RainCardsProvider",
    "evaluate_issuer_readiness",
]

# Lithic provider is optional
try:
    from .lithic import LithicProvider
    __all__.append("LithicProvider")
except ImportError:
    pass

# Stripe Issuing provider is optional
try:
    from .stripe_issuing import StripeIssuingProvider
    __all__.append("StripeIssuingProvider")
except ImportError:
    pass
