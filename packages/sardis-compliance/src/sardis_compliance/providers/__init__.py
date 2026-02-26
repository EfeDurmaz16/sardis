"""Alternative compliance providers.

Drop-in replacements for default providers (Persona, Elliptic)
with zero monthly fees and per-transaction pricing.
"""

try:
    from .idenfy import IdenfyKYCProvider
    IDenfyKYCProvider = IdenfyKYCProvider
except ImportError:
    IdenfyKYCProvider = None  # type: ignore[assignment,misc]
    IDenfyKYCProvider = None  # type: ignore[assignment,misc]

try:
    from .scorechain import ScorechainProvider
except ImportError:
    ScorechainProvider = None  # type: ignore[assignment,misc]

__all__ = [
    "IdenfyKYCProvider",
    "IDenfyKYCProvider",
    "ScorechainProvider",
]
