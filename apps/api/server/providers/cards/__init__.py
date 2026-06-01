"""Card-issuing provider package.

Three env-gated providers, each behind :class:`server.providers.ports.CardPort`:

* **Crossmint Agentic Cards** (PRIMARY) — Rain-backed, non-custodial dual-key,
  agent-bound single-use virtual credentials; avoids a mandatory Stripe/Lithic
  relationship.  Activated by ``CROSSMINT_API_KEY`` (+ ``CROSSMINT_RAIN_API_KEY``
  for the concrete card surface).
* **Lithic** (FALLBACK) — Sardis's own BIN.  Activated by ``LITHIC_API_KEY``.
* **Stripe Issuing** (FALLBACK) — activated by ``STRIPE_ISSUING_API_KEY``
  (or ``STRIPE_SECRET_KEY``).

Each activates only when its env is set; otherwise the registry returns the
SIMULATED :class:`server.providers.sandbox.SandboxCardPort` (card is NOT a
required-in-production capability, so the sandbox fallback is allowed even in
prod — no money is moved by issuing a card).

No card adapter authorizes/initiates/settles a transaction — each only issues a
card / freezes it / sets a control the orchestrator already authorized.  A real
PAN is never surfaced (tokenized refs only).  Money is integer minor units
(cents); no float, no secret hardcoded.

See :mod:`server.providers.cards.client` for the researched 2026 API facts.
"""

from __future__ import annotations

from .adapter import (
    CrossmintCardAdapter,
    LithicCardAdapter,
    StripeIssuingCardAdapter,
)
from .client import (
    CrossmintCardClient,
    CrossmintConfig,
    IssuedCard,
    LithicCardClient,
    LithicCardConfig,
    StripeIssuingClient,
    StripeIssuingConfig,
)

__all__ = [
    "CrossmintCardAdapter",
    "CrossmintCardClient",
    "CrossmintConfig",
    "IssuedCard",
    "LithicCardAdapter",
    "LithicCardClient",
    "LithicCardConfig",
    "StripeIssuingCardAdapter",
    "StripeIssuingClient",
    "StripeIssuingConfig",
]
