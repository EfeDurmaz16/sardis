"""Offramp provider package (crypto -> fiat payout to a bank/agent account).

Three env-gated providers, each behind :class:`server.providers.ports.OfframpPort`:

* **Onramper** — crypto->fiat *sell* aggregator (8+ offramps); hosted sell
  intent via ``POST /checkout/intent`` (type=sell).  Partner-custodied.
* **Transak Stream** — address-based programmatic offramp: creates a SELL order
  that yields a unique deposit address; funding that address triggers the
  automatic fiat payout.  Agent-friendly (no widget).  Partner-custodied.
* **Coinbase Offramp** — CDP session-token + sell quote + hosted offramp URL;
  cashout to ACH bank or PayPal.  Partner-custodied.

Each activates only when its env keys are set; otherwise the registry returns
the sandbox :class:`SandboxOfframpPort`.  No adapter authorizes/initiates money —
it normalizes + executes what the orchestrator already authorized.  Money is
integer minor units / ``Decimal``; no secret is hardcoded.

For bank wire/ACH *push* payouts (USD already off-chain) the Increase
fiat-account offramp leg is preferred; these three cover the crypto->fiat
conversion leg.  See :mod:`server.providers.offramp.client` for the researched
2026 API facts and citations.
"""

from __future__ import annotations

from .adapter import (
    CoinbaseOfframpAdapter,
    OnramperOfframpAdapter,
    TransakStreamOfframpAdapter,
)
from .client import (
    CoinbaseOfframpClient,
    CoinbaseOfframpConfig,
    OnramperOfframpClient,
    OnramperOfframpConfig,
    TransakStreamClient,
    TransakStreamConfig,
)

__all__ = [
    "CoinbaseOfframpAdapter",
    "CoinbaseOfframpClient",
    "CoinbaseOfframpConfig",
    "OnramperOfframpAdapter",
    "OnramperOfframpClient",
    "OnramperOfframpConfig",
    "TransakStreamClient",
    "TransakStreamConfig",
    "TransakStreamOfframpAdapter",
]
