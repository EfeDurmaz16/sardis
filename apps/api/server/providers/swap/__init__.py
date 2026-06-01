"""Swap provider package (same-chain / cross-token token swaps).

Three env-gated providers, each behind :class:`server.providers.ports.SwapPort`:

* **LI.FI** — pure-REST DEX + bridge aggregation across EVM and Solana, with an
  ``integrator`` + ``fee`` revenue param.  Optional API key (keyless at low
  rate limits).  Non-custodial.
* **0x Swap API v2** — same-chain EVM best price via the allowance-holder
  endpoint, with ``swapFeeBps`` / ``swapFeeRecipient`` revenue capture.
  Requires ``0x-api-key`` + ``0x-version: v2``.  Non-custodial.
* **Jupiter** — Solana best-price swap with a ``platformFeeBps`` revenue param.
  Keyed host ``api.jup.ag`` when a key is set, else keyless ``lite-api.jup.ag``.
  Non-custodial.

Each activates only when its env keys are set; otherwise the registry returns
the sandbox :class:`SandboxSwapPort`.  No adapter authorizes/initiates/settles
money — it returns a quote and the already-shaped transaction the orchestrator's
CustodyPort signs.  Money is integer minor units / exact strings; no float, no
secret hardcoded.

See :mod:`server.providers.swap.client` for the researched 2026 API facts.
"""

from __future__ import annotations

from .adapter import (
    JupiterSwapAdapter,
    LifiSwapAdapter,
    ZeroExSwapAdapter,
)
from .client import (
    JupiterClient,
    JupiterConfig,
    LifiClient,
    LifiConfig,
    SwapQuote,
    ZeroExClient,
    ZeroExConfig,
)

__all__ = [
    "JupiterClient",
    "JupiterConfig",
    "JupiterSwapAdapter",
    "LifiClient",
    "LifiConfig",
    "LifiSwapAdapter",
    "SwapQuote",
    "ZeroExClient",
    "ZeroExConfig",
    "ZeroExSwapAdapter",
]
