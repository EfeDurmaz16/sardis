"""Onramp provider package (fiat/crypto -> destination wallet).

Three env-gated providers, each behind :class:`server.providers.ports.OnrampPort`:

* **Onramper** — fiat->crypto aggregator widget.  ``pk_…`` API key + optional
  request-signing secret.  Partner-custodied.
* **Transak** — backend-minted single-use widget URL (secret stays server-side,
  two-step token+session flow).  Partner-custodied.
* **Daimo Pay** — any-token/any-chain -> USDC wallet funding via a hosted
  checkout.  Non-custodial.

Each activates only when its env keys are set; otherwise the registry returns
the sandbox :class:`SandboxOnrampPort`.  No adapter authorizes/initiates money —
it normalizes + executes what the orchestrator already authorized.  Money is
integer minor units / ``Decimal``; no secret is hardcoded.

See :mod:`server.providers.onramp.client` for the researched 2026 API facts.
"""

from __future__ import annotations

from .adapter import (
    DaimoOnrampAdapter,
    OnramperOnrampAdapter,
    TransakOnrampAdapter,
)
from .client import (
    DaimoClient,
    DaimoConfig,
    OnramperClient,
    OnramperConfig,
    TransakClient,
    TransakConfig,
)

__all__ = [
    "DaimoClient",
    "DaimoConfig",
    "DaimoOnrampAdapter",
    "OnramperClient",
    "OnramperConfig",
    "OnramperOnrampAdapter",
    "TransakClient",
    "TransakConfig",
    "TransakOnrampAdapter",
]
